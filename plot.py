#!/bin/python
# coding: utf-8
import matplotlib, sys
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pylab as Plot
import numpy as np
from matplotlib import font_manager
from tsne import tsne
import hashlib

import ConfigParser
config = ConfigParser.RawConfigParser()
config.read('webvectors.cfg')

root = config.get('Files and directories', 'root')
path = config.get('Files and directories', 'font')
font = font_manager.FontProperties(fname=path)

def singularplot(word, modelname, vector):
    xlocations = np.array(range(len(vector)))
    plt.bar(xlocations, vector)
    plot_title = word.split('_')[0] + '\n' + modelname + u' model'
    plt.title(plot_title, fontproperties=font)
    m = hashlib.md5()
    name = word.encode('ascii', 'backslashreplace')
    m.update(name)
    fname = m.hexdigest()
    plt.savefig(root + 'static/singleplots/' + modelname + '_' + fname + '.png', dpi=150, bbox_inches='tight')
    plt.close()


def embed(words, matrix, usermodel):
    perplexity = 5.0
    dimensionality = matrix.shape[1]
    Y = tsne(matrix, 2, dimensionality, perplexity)
    print >> sys.stderr, '2-d embedding finished'
    Plot.scatter(Y[:, 0], Y[:, 1], 20, marker='.')
    for label, x, y in zip(words, Y[:, 0], Y[:, 1]):
        Plot.annotate(label.split('_')[0], xy=(x - 20, y), size='x-large', weight='bold', fontproperties=font)
    m = hashlib.md5()
    name = '_'.join(words).encode('ascii', 'backslashreplace')
    m.update(name)
    fname = m.hexdigest()
    Plot.savefig(root + 'static/tsneplots/' + usermodel + '_' + fname + '.png', dpi=150, bbox_inches='tight')
    Plot.close()
