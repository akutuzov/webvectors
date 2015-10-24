#!/usr/bin/python2
# coding: utf-8

import sys, gensim, logging,codecs,os
import time


logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)

argument = sys.argv[1]
filename = argument.split('/')[-1]

args = filename.split('.')[0].split('__')
(urlhash,algo,vectorsize,windowsize) = args

if algo == "skipgram":
    skipgram = 1
else:
    skipgram = 0

data = gensim.models.word2vec.LineSentence(argument)


model = gensim.models.Word2Vec(data,size=int(vectorsize),min_count=2,window=int(windowsize),sg=skipgram,workers=2,iter=5)
model.init_sims(replace=True)
model.save_word2vec_format('/home/sites/ling.go.mail.ru/trained/'+filename.split('.')[0].split('__')[0]+'.model', binary=True)
os.remove('/home/sites/ling.go.mail.ru/tmp/'+filename.split('.')[0].split('__')[0])
