#!/bin/python
#coding: utf-8
import matplotlib
matplotlib.use('Agg') 
import pylab as Plot
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as font_manager
path = '/home/sites/ling.go.mail.ru/static/fonts/google-droid/DroidSans-Bold.ttf'
font = font_manager.FontProperties(fname=path)
from tsne import tsne
import hashlib

root = '/home/sites/ling.go.mail.ru/quazy-synonyms/'


def singularplot(word,modelname,vector):
    xlocations = np.array(range(len(vector)))
    plt.bar(xlocations,vector)
    plot_title = word.split('_')[0]+'\n'+u'модель '+modelname
    plt.title(plot_title,fontproperties=font)
    plt.savefig(root+'static/singleplots/'+modelname+'_'+word.encode('ascii','backslashreplace')+'.png',dpi=150,bbox_inches='tight')
    plt.close()



def embed(words,matrix,usermodel):
    Y = tsne(matrix,2,300,5.0)
    print '2-d embedding finished'
    Plot.scatter(Y[:,0], Y[:,1], 20,marker='.')
    for label, x, y in zip(words, Y[:, 0], Y[:, 1]):
	Plot.annotate(label.split('_')[0], xy = (x-20, y),size = 'x-large', weight = 'bold',fontproperties=font)
    m = hashlib.md5()
    name = '_'.join(words).encode('ascii','backslashreplace')
    m.update(name)
    fname = m.hexdigest()
    Plot.savefig(root+'static/tsneplots/'+usermodel+'_'+fname+'.png',dpi=150,bbox_inches='tight')
    Plot.close()
