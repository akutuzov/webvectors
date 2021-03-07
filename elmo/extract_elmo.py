# python3
# coding: utf-8

import argparse
import numpy as np
from smart_open import open
from simple_elmo import ElmoModel
import logging
from collections import Counter
import time
from helpers import save_word2vec_format

logging.basicConfig(
    format="%(asctime)s : %(levelname)s : %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    arg = parser.add_argument
    arg("--input", "-i", help="Path to the input corpus", required=True)
    arg("--elmo", "-e", help="Path to ELMo model", required=True)
    arg("--outfile", "-o", help="Output file to save type embeddings",
        default="type_embeddings.vec.gz")
    arg("--vocab", "-v", help="Path to frequency dictionary file. "
                              "Format: tab-separated, with word in the first column and absolute "
                              "frequency in the second column. "
                              "One word per line, sorted by decreasing frequency."
                              "Corpus size in word tokens must be given in the first line "
                              "(without tabs). "
                              "If vocabulary is not provided, "
                              "it will be inferred from the input corpus. ")
    arg("--vocab_size", "-vs", help="How many top frequent words to create type embeddings for",
        type=int, default=10000)
    arg("--batch", "-b", help="ELMo batch size", default=256, type=int)
    arg(
        "--layers",
        "-l",
        help="What layers to use",
        default="top",
        choices=["top", "average", "all"],
    )
    arg(
        "--warmup",
        "-w",
        help="Warmup before extracting?",
        default="yes",
        choices=["yes", "no"],
    )

    args = parser.parse_args()
    data_path = args.input
    batch_size = args.batch
    if args.vocab:
        vocab_path = args.vocab
    else:
        vocab_path = None
    WORD_LIMIT = 400

    word_list = []
    if vocab_path:
        with open(vocab_path, "r") as f:
            for line in f.readlines():
                word, frequency = line.strip().split("\t")
                if word.isdigit():
                    continue
                if len(word) < 2:
                    continue
                word_list.append(word)
                if len(word_list) == args.vocab_size:
                    break

    else:
        logger.info("No vocabulary provided; inferring it from the corpus.")
        inferred_voc = Counter()
        total_word_count = 0
        with open(data_path, "r") as corpus:
            for line in corpus:
                tokenized = line.strip().split()
                total_word_count += len(tokenized)
                inferred_voc.update(tokenized)
        top_frequent = inferred_voc.most_common(args.vocab_size)
        for w in top_frequent:
            if len(w[0]) > 2:
                word_list.append(w[0])
        logger.info("Vocabulary inferred.")
        outvocab = "freq_vocab.tsv.gz"
        all_words = inferred_voc.most_common(len(inferred_voc))
        with open(outvocab, "w") as f:
            f.write(f"{total_word_count}\n")
            for w in all_words:
                if w[1] > 1:
                    f.write(f"{w[0]}\t{w[1]}\n")
        logger.info(f"Inferred vocabulary saved to {outvocab}. Use it in the WebVectors config.")

    logger.info(f"Words to test: {len(word_list)}")

    # Loading a pre-trained ELMo model:
    model = ElmoModel()
    model.load(args.elmo, max_batch_size=batch_size)

    vect_dict = np.zeros((len(word_list), model.vector_size))
    target_words = {w: word_list.index(w) for w in word_list}

    counters = {w: 0 for w in target_words}

    # Actually producing ELMo embeddings for our data:
    start = time.time()

    CACHE = 5120

    lines_processed = 0
    lines_cache = []
    with open(data_path, "r") as dataset:
        for line in dataset:
            res = line.strip().split()[:WORD_LIMIT]
            if target_words.keys() & set(res):
                lines_cache.append(res)
                lines_processed += 1
            if len(lines_cache) == CACHE:
                elmo_vectors = model.get_elmo_vectors(lines_cache, layers=args.layers)
                for sent, matrix in zip(lines_cache, elmo_vectors):
                    for word, vector in zip(sent, matrix):
                        if word in target_words:
                            vect_dict[target_words[word], :] += vector
                            counters[word] += 1
                lines_cache = []
                if lines_processed % 2560 == 0:
                    logger.info(f"{data_path}; Lines processed: {lines_processed}")
        if lines_cache:
            elmo_vectors = model.get_elmo_vectors(lines_cache, layers=args.layers)
            for sent, matrix in zip(lines_cache, elmo_vectors):
                for word, vector in zip(sent, matrix):
                    if word in target_words:
                        vect_dict[target_words[word], :] += vector
                        counters[word] += 1
    end = time.time()
    processing_time = int(end - start)
    logger.info(f"ELMo embeddings for your input are ready in {processing_time} seconds")
    logger.info("Normalizing...")

    for row in range(len(vect_dict)):
        vect_dict[row] = vect_dict[row] / np.linalg.norm(vect_dict[row])

    logger.info("Saving...")

    np.savez_compressed("type_vectors.npz", vect_dict)

    a = save_word2vec_format(args.outfile, word_list, vect_dict, binary=False)
    binary_file = args.outfile.split(".")[0] + ".bin"
    b = save_word2vec_format(binary_file, word_list, vect_dict, binary=True)

    logger.info(f"Vectors saved to {args.outfile} and {binary_file}")

