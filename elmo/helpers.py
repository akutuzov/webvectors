#!/usr/bin/python3
# coding: utf-8

import numpy as np
from numpy import float32 as real
from smart_open import open

def any2utf8(text, errors='strict', encoding='utf8'):
    if isinstance(text, str):
        return text.encode('utf8')
    # do bytestring -> unicode -> utf8 full circle, to ensure valid utf8
    return str(text, encoding, errors=errors).encode('utf8')


def save_word2vec_format(fname, vocab, vectors, binary=False):
    """Store the input-hidden weight matrix in the same format used by the original
        C word2vec-tool, for compatibility.
        Parameters
        ----------
        fname : str
            The file path used to save the vectors in
        vocab : list
            The vocabulary of words sorted by frequency
        vectors : numpy.array
            The vectors to be stored
        binary : bool
            If True, the data wil be saved in binary word2vec format, else in plain text.
        """
    if not (vocab or vectors):
        raise RuntimeError('no input')
    total_vec = len(vocab)
    vector_size = vectors.shape[1]
    print('storing %dx%d projection weights into %s' % (total_vec, vector_size, fname))
    assert (len(vocab), vector_size) == vectors.shape
    with open(fname, 'wb') as fout:
        fout.write(any2utf8('%s %s\n' % (total_vec, vector_size)))
        position = 0
        for element in vocab:
            row = vectors[position]
            if binary:
                row = row.astype(real)
                fout.write(any2utf8(element) + b" " + row.tostring())
            else:
                fout.write(any2utf8('%s %s\n' % (element, ' '.join(repr(val) for val in row))))
            position += 1


