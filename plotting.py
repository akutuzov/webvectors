#!/usr/bin/python
# coding: utf-8
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pylab as plot
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
    plt.savefig(root + 'data/images/singleplots/' + modelname + '_' + fname + '.png', dpi=150, bbox_inches='tight')
    plt.close()


def embed(words, matrix, usermodel):
    perplexity = 5.0 # Should be smaller than the number of points!
    dimensionality = matrix.shape[1]
    y = tsne(matrix, 2, dimensionality, perplexity)
    print >> sys.stderr, '2-d embedding finished'
    plot.scatter(y[:, 0], y[:, 1], 20, marker='.')
    for label, x, y in zip(words, y[:, 0], y[:, 1]):
        plot.annotate(label.split('_')[0], xy=(x - 20, y), size='x-large', weight='bold', fontproperties=font)
    m = hashlib.md5()
    name = '_'.join(words).encode('ascii', 'backslashreplace')
    m.update(name)
    fname = m.hexdigest()
    plot.savefig(root + 'data/images/tsneplots/' + usermodel + '_' + fname + '.png', dpi=150, bbox_inches='tight')
    plot.close()
