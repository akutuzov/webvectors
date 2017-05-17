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
    perplexity = 5.0  # Should be smaller than the number of points!
    dimensionality = matrix.shape[1]
    y = tsne(matrix, 2, dimensionality, perplexity)

    classes = [word.split('_')[-1] for word in words]
    classet = [c for c in set(classes)]
    colors = plot.cm.rainbow(np.linspace(0, 1, len(classet)))
    pos2color = [colors[classet.index(w)] for w in classes]

    print >> sys.stderr, '2-d embedding finished'

    xpositions = y[:, 0]
    ypositions = y[:, 1]
    for color, word, x, y in zip(pos2color, words, xpositions, ypositions):
        lemma = word.split('_')[0]
        mid = len(lemma) / 2
        mid *= 8  # TODO Should really think about how to adapt this variable to the real plot size
        plot.scatter(x, y, 20, marker='.', color=color)
        plot.annotate(lemma, xy=(x - mid, y), size='x-large', weight='bold', fontproperties=font, color=color)

    m = hashlib.md5()
    name = '_'.join(words).encode('ascii', 'backslashreplace')
    m.update(name)
    fname = m.hexdigest()
    plot.savefig(root + 'data/images/tsneplots/' + usermodel + '_' + fname + '.png', dpi=150, bbox_inches='tight')
    plot.close()
