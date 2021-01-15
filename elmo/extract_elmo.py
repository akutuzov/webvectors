# python3
# coding: utf-8

import argparse
import numpy as np
from smart_open import open
from simple_elmo import ElmoModel
import logging
import json
import time
from helpers import save_word2vec_format

logging.basicConfig(
    format="%(asctime)s : %(levelname)s : %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    arg = parser.add_argument
    arg("--input", "-i", help="Path to input text", required=True)
    arg("--elmo", "-e", help="Path to ELMo model", required=True)
    arg("--outfile", "-o", help="Output file to save embeddings", default="type_embeddings.vec.gz")
    arg("--outvocab", help="Where to store real vocabulary", required=True),
    arg("--vocab", "-v", help="Path to vocabulary file", required=True)
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
    vocab_path = args.vocab
    WORD_LIMIT = 400

    word_list = []
    with open(vocab_path, "r") as f:
        for line in f.readlines():
            word = line.strip()
            if word.isdigit():
                continue
            if len(word) < 2:
                continue
            word_list.append(word)

    logger.info(f"Words to test: {len(word_list)}")

    with open(args.outvocab, "w") as f:
        out = json.dumps(word_list, ensure_ascii=False)
        f.write(out)

    # Loading a pre-trained ELMo model:
    model = ElmoModel()
    model.load(args.elmo, max_batch_size=batch_size)

    vect_dict = np.zeros((len(word_list), model.vector_size))
    target_words = {w: word_list.index(w) for w in word_list}

    counters = {w: 0 for w in target_words}

    # Actually producing ELMo embeddings for our data:
    start = time.time()

    CACHE = 12800

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
    
    logger.info(f"Vectors saved to {args.outfile}")

