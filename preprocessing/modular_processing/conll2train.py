#! python3
# coding: utf-8

import logging
import sys
from helpers import extract_proper, bigrammer, convert, check_word, num_replace
from gensim.utils import smart_open

logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)

SOURCE_FILE = sys.argv[1]  # Must be *.conllu.gz

TEMPFILE0_NAME = SOURCE_FILE.replace('.conllu', '.txt')

processed = extract_proper(SOURCE_FILE, TEMPFILE0_NAME)  # Can turn off sentence breaks

print('Processed %d lines' % processed, file=sys.stderr)

BIGRAMMED_FILE_NAME = TEMPFILE0_NAME.replace('.txt', '_bigrams.txt')

nr_bigrams = bigrammer(TEMPFILE0_NAME, BIGRAMMED_FILE_NAME) # Can tune threshold and mincount

print('Found %d bigrams' % nr_bigrams, file=sys.stderr)

print('Fixing POS in bigrams...', file=sys.stderr)
bigram_file = smart_open(BIGRAMMED_FILE_NAME, 'r')
CONV_BIGRAM_FILE_NAME = BIGRAMMED_FILE_NAME.replace('_bigrams.txt', '_conv_bigrams.txt')
conv_bigram_file = smart_open(CONV_BIGRAM_FILE_NAME, 'a')

for line in bigram_file:
    res = line.strip().split()
    newwords = []
    for word in res:
        if ':::' in word:
            newword = convert(word)
        else:
            newword = word
        newwords.append(newword)
    conv_bigram_file.write(' '.join(newwords))
    conv_bigram_file.write('\n')
bigram_file.close()
conv_bigram_file.close()
print('Fixed bigrams written to %s...' % CONV_BIGRAM_FILE_NAME, file=sys.stderr)

print('Filtering the corpus...', file=sys.stderr)

# STOPWORDS_FILE = 'stopwords_ru'
# stopwords = set([w.strip().lower() for w in smart_open(STOPWORDS_FILE,'r').readlines()])
functional = set('ADP AUX CCONJ DET PART PRON SCONJ PUNCT'.split())
SKIP_1_WORD = True

corpus_file = smart_open(CONV_BIGRAM_FILE_NAME, 'r')
FILTERED_CORPUS_FILE_NAME = CONV_BIGRAM_FILE_NAME.replace('_conv_bigrams.', '_filtered.')
filtered = smart_open(FILTERED_CORPUS_FILE_NAME, 'a')

for line in corpus_file:
    res = line.strip().split()
    good = []
    for w in res:
        # try:
        (token, pos) = w.split('_')
        # except:
        #    print('Weird token:', w, file=sys.stderr)
        #    continue
        checked_word = check_word(token, pos, nofunc=functional)   # Can feed stopwords list
        if not checked_word:
            continue
        if pos == 'NUM' and token.isdigit():  # Replacing numbers with xxxxx of the same length
            checked_word = num_replace(checked_word)
        good.append(checked_word)
    if SKIP_1_WORD:  # May be, you want to filter out one-word sentences
        if len(good) < 2:
            continue
    filtered.write(' '.join(good))
    filtered.write('\n')

corpus_file.close()
filtered.close()
print('Final training corpus:', FILTERED_CORPUS_FILE_NAME)
