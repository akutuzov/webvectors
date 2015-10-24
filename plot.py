#!/bin/python
#coding: utf-8
import pylab
import numpy as np
import matplotlib.pyplot as plt
import numpy.numarray as na
from pylab import *
import matplotlib.font_manager as font_manager
path = '/home/sites/ling.go.mail.ru/static/fonts/google-droid/DroidSans-Bold.ttf'
font = font_manager.FontProperties(fname=path)


def singularplot(word,vector):
    xlocations = na.array(range(len(vector)))
    plt.bar(xlocations,vector)
    plt.title(word,fontproperties=font)
    plt.gca().get_xaxis().tick_bottom()
    plt.gca().get_yaxis().tick_left()
    plt.savefig('/home/sites/ling.go.mail.ru/quazy-synonyms/static/'+word+'.png',dpi=150,bbox_inches='tight')
    plt.close()