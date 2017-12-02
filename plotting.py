#!/usr/bin/python
# coding: utf-8
import sys
import matplotlib
matplotlib.use('Agg')
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
    plot.bar(xlocations, vector)
    plot_title = word.split('_')[0] + '\n' + modelname + u' model'
    plot.title(plot_title, fontproperties=font)
    plot.xlabel('Vector components')
    plot.ylabel('Components values')
    m = hashlib.md5()
    name = word.encode('ascii', 'backslashreplace')
    m.update(name)
    fname = m.hexdigest()
    plot.savefig(root + 'data/images/singleplots/' + modelname + '_' + fname + '.png', dpi=150, bbox_inches='tight')
    plot.close()


def embed(words, matrix, classes, usermodel, fname):
    perplexity = 5.0  # Should be smaller than the number of points!
    dimensionality = matrix.shape[1]
    y = tsne(matrix, 2, dimensionality, perplexity)

    print >> sys.stderr, '2-d embedding finished'

    class_set = [c for c in set(classes)]
    colors = plot.cm.rainbow(np.linspace(0, 1, len(class_set)))

    class2color = [colors[class_set.index(w)] for w in classes]

    xpositions = y[:, 0]
    ypositions = y[:, 1]
    seen = set()

    for color, word, class_label, x, y in zip(class2color, words, classes, xpositions, ypositions):
        plot.scatter(x, y, 20, marker='.', color=color, label=class_label if class_label not in seen else "")
        seen.add(class_label)

        lemma = word.split('_')[0].replace('::', ' ')
        mid = len(lemma) / 2
        mid *= 10  # TODO Should really think about how to adapt this variable to the real plot size
        plot.annotate(lemma, xy=(x - mid, y), size='x-large', weight='bold', fontproperties=font, color=color)

    plot.tick_params(axis='x', which='both', bottom='off', top='off', labelbottom='off')
    plot.tick_params(axis='y', which='both', left='off', right='off', labelleft='off')
    plot.legend(loc='best')

    plot.savefig(root + 'data/images/tsneplots/' + usermodel + '_' + fname + '.png', dpi=150, bbox_inches='tight')
    plot.close()
