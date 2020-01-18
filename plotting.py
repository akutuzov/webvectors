#!/usr/bin/env python
# coding: utf-8

import sys
import matplotlib
matplotlib.use('Agg')
import pylab as plot
import numpy as np
from matplotlib import font_manager
from sklearn.manifold import TSNE
import configparser

config = configparser.RawConfigParser()
config.read('webvectors.cfg')

root = config.get('Files and directories', 'root')
path = config.get('Files and directories', 'font')
font = font_manager.FontProperties(fname=path)


def singularplot(word, modelname, vector, fname):
    xlocations = np.array(list(range(len(vector))))
    plot.clf()
    plot.bar(xlocations, vector)
    plot_title = word.split('_')[0].replace('::', ' ') + '\n' + modelname + u' model'
    plot.title(plot_title, fontproperties=font)
    plot.xlabel('Vector components')
    plot.ylabel('Components values')
    plot.savefig(root + 'data/images/singleplots/' + modelname + '_' + fname + '.png', dpi=150,
                 bbox_inches='tight')
    plot.close()
    plot.clf()


def embed(words, matrix, classes, usermodel, fname):
    perplexity = int(len(words) ** 0.5)  # We set perplexity to a square root of the words number
    embedding = TSNE(n_components=2, perplexity=perplexity, metric='cosine', n_iter=500, init='pca')
    y = embedding.fit_transform(matrix)

    print('2-d embedding finished', file=sys.stderr)

    class_set = [c for c in set(classes)]
    colors = plot.cm.rainbow(np.linspace(0, 1, len(class_set)))

    class2color = [colors[class_set.index(w)] for w in classes]

    xpositions = y[:, 0]
    ypositions = y[:, 1]
    seen = set()

    plot.clf()

    for color, word, class_label, x, y in zip(class2color, words, classes, xpositions, ypositions):
        plot.scatter(x, y, 20, marker='.', color=color,
                     label=class_label if class_label not in seen else "")
        seen.add(class_label)

        lemma = word.split('_')[0].replace('::', ' ')
        mid = len(lemma) / 2
        mid *= 4  # TODO Should really think about how to adapt this variable to the real plot size
        plot.annotate(lemma, xy=(x - mid, y), size='x-large', weight='bold', fontproperties=font,
                      color=color)

    plot.tick_params(axis='x', which='both', bottom=False, top=False, labelbottom=False)
    plot.tick_params(axis='y', which='both', left=False, right=False, labelleft=False)
    plot.legend(loc='best')

    plot.savefig(root + 'data/images/tsneplots/' + usermodel + '_' + fname + '.png', dpi=150,
                 bbox_inches='tight')
    plot.close()
    plot.clf()
