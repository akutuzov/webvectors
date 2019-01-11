#!/usr/bin/env python
# coding: utf-8

from __future__ import print_function
from __future__ import division
from future import standard_library

standard_library.install_aliases()
from builtins import str
import socket
import datetime
import threading
import sys
import gensim
import logging
import json
import configparser
import csv


class WebVectorsThread(threading.Thread):
    def __init__(self, connect, address):
        threading.Thread.__init__(self)
        self.connect = connect
        self.address = address

    def run(self):
        clientthread(self.connect, self.address)


def clientthread(connect, addres):
    # Sending message to connected client
    connect.send(bytes(b'word2vec model server'))

    # infinite loop so that function do not terminate and thread do not end.
    while True:
        # Receiving from client
        data = connect.recv(1024)
        if not data:
            break
        query = json.loads(data.decode('utf-8'))
        output = operations[query['operation']](query)
        now = datetime.datetime.now()
        print(now.strftime("%Y-%m-%d %H:%M"), '\t', addres[0] + ':' + str(addres[1]), '\t',
              data.decode('utf-8'), file=sys.stderr)
        reply = json.dumps(output, ensure_ascii=False)
        connect.sendall(reply.encode('utf-8'))
        break

    # came out of loop
    connect.close()


config = configparser.RawConfigParser()
config.read('webvectors.cfg')

root = config.get('Files and directories', 'root')
HOST = config.get('Sockets', 'host')  # Symbolic name meaning all available interfaces
PORT = config.getint('Sockets', 'port')  # Arbitrary non-privileged port
tags = config.getboolean('Tags', 'use_tags')

logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)

# Loading models

our_models = {}
with open(root + config.get('Files and directories', 'models'), 'r') as csvfile:
    reader = csv.DictReader(csvfile, delimiter='\t')
    for row in reader:
        our_models[row['identifier']] = {}
        our_models[row['identifier']]['path'] = row['path']
        our_models[row['identifier']]['default'] = row['default']
        our_models[row['identifier']]['tags'] = row['tags']
        our_models[row['identifier']]['algo'] = row['algo']
        our_models[row['identifier']]['corpus_size'] = int(row['size'])

models_dic = {}

for m in our_models:
    modelfile = our_models[m]['path']
    our_models[m]['vocabulary'] = True
    if our_models[m]['algo'] == 'fasttext':
        models_dic[m] = gensim.models.KeyedVectors.load(modelfile)
    else:
        if modelfile.endswith('.bin.gz'):
            models_dic[m] = gensim.models.KeyedVectors.load_word2vec_format(modelfile, binary=True)
            our_models[m]['vocabulary'] = False
        elif modelfile.endswith('.vec.gz'):
            models_dic[m] = gensim.models.KeyedVectors.load_word2vec_format(modelfile, binary=False)
            our_models[m]['vocabulary'] = False
        else:
            models_dic[m] = gensim.models.KeyedVectors.load(modelfile)
    models_dic[m].init_sims(replace=True)
    print("Model", m, "from file", modelfile, "loaded successfully.", file=sys.stderr)


# Vector functions

def frequency(word, model):
    corpus_size = our_models[model]['corpus_size']
    if word not in models_dic[model].wv.vocab:
        return 0, 'low'
    if not our_models[model]['vocabulary']:
        return 0, 'mid'
    wordfreq = models_dic[model].wv.vocab[word].count
    relative = wordfreq / corpus_size
    tier = 'mid'
    if relative > 0.00001:
        tier = 'high'
    elif relative < 0.0000005:
        tier = 'low'
    return wordfreq, tier


def find_synonyms(query):
    q = query['query']
    pos = query['pos']
    usermodel = query['model']
    results = {'frequencies': {}}
    qf = q
    results['frequencies'][q] = frequency(q, usermodel)
    model = models_dic[usermodel]
    if qf not in model.wv.vocab:
        candidates_set = set()
        candidates_set.add(q.upper())
        if tags and our_models[usermodel]['tags'] == 'True':
            candidates_set.add(q.split('_')[0] + '_X')
            candidates_set.add(q.split('_')[0].lower() + '_' + q.split('_')[1])
            candidates_set.add(q.split('_')[0].capitalize() + '_' + q.split('_')[1])
        else:
            candidates_set.add(q.lower())
            candidates_set.add(q.capitalize())
        noresults = True
        for candidate in candidates_set:
            if candidate in model.wv.vocab:
                qf = candidate
                noresults = False
                break
        if noresults:
            if our_models[usermodel]['algo'] == 'fasttext' and model.wv.__contains__(qf):
                results['inferred'] = True
            else:
                results[q + " is unknown to the model"] = True
                return results
    results['neighbors'] = []
    if pos == 'ALL':
        for i in model.wv.most_similar(positive=qf, topn=10):
            results['neighbors'].append(i)
    else:
        counter = 0
        for i in model.wv.most_similar(positive=qf, topn=30):
            if counter == 10:
                break
            if i[0].split('_')[-1] == pos:
                results['neighbors'].append(i)
                counter += 1
    if len(results) == 0:
        results['No results'] = True
        return results
    for res in results['neighbors']:
        freq, tier = frequency(res[0], usermodel)
        results['frequencies'][res[0]] = (freq, tier)
    raw_vector = model[qf]
    results['vector'] = raw_vector.tolist()
    return results


def find_similarity(query):
    q = query['query']
    usermodel = query['model']
    model = models_dic[usermodel]
    results = {'similarities': [], 'frequencies': {}}
    for pair in q:
        (q1, q2) = pair
        qf1 = q1
        qf2 = q2
        results['frequencies'][q1] = frequency(q1, usermodel)
        results['frequencies'][q2] = frequency(q2, usermodel)
        if q1 not in model.wv.vocab:
            candidates_set = set()
            candidates_set.add(q1.upper())
            if tags and our_models[usermodel]['tags'] == 'True':
                candidates_set.add(q1.split('_')[0] + '_X')
                candidates_set.add(q1.split('_')[0].lower() + '_' + q1.split('_')[1])
                candidates_set.add(q1.split('_')[0].capitalize() + '_' + q1.split('_')[1])
            else:
                candidates_set.add(q1.lower())
                candidates_set.add(q1.capitalize())
            noresults = True
            for candidate in candidates_set:
                if candidate in model.wv.vocab:
                    qf1 = candidate
                    noresults = False
                    break
            if noresults:
                if our_models[usermodel]['algo'] == 'fasttext':
                    results['inferred'] = True
                else:
                    results["Unknown to the model"] = q1
                    return results
        if q2 not in model.wv.vocab:
            candidates_set = set()
            candidates_set.add(q2.upper())
            if tags and our_models[usermodel]['tags'] == 'True':
                candidates_set.add(q2.split('_')[0] + '_X')
                candidates_set.add(q2.split('_')[0].lower() + '_' + q2.split('_')[1])
                candidates_set.add(q2.split('_')[0].capitalize() + '_' + q2.split('_')[1])
            else:
                candidates_set.add(q2.lower())
                candidates_set.add(q2.capitalize())
            noresults = True
            for candidate in candidates_set:
                if candidate in model.wv.vocab:
                    qf2 = candidate
                    noresults = False
                    break
            if noresults:
                if our_models[usermodel]['algo'] == 'fasttext':
                    results['inferred'] = True
                else:
                    results["Unknown to the model"] = q2
                    return results
        pair2 = (qf1, qf2)
        result = float(model.similarity(qf1, qf2))
        results['similarities'].append((pair2, result))
    return results


def scalculator(query):
    q = query['query']
    pos = query['pos']
    usermodel = query['model']
    model = models_dic[usermodel]
    results = {'neighbors': [], 'frequencies': {}}
    positive_list = q[0]
    negative_list = q[1]
    plist = []
    nlist = []
    for word in positive_list:
        if len(word) < 2:
            continue
        if word in model.wv.vocab:
            plist.append(word)
            continue
        else:
            candidates_set = set()
            candidates_set.add(word.upper())
            if tags and our_models[usermodel]['tags'] == 'True':
                candidates_set.add(word.split('_')[0] + '_X')
                candidates_set.add(word.split('_')[0].lower() + '_' + word.split('_')[1])
                candidates_set.add(word.split('_')[0].capitalize() + '_' + word.split('_')[1])
            else:
                candidates_set.add(word.lower())
                candidates_set.add(word.capitalize())
            noresults = True
            for candidate in candidates_set:
                if candidate in model.wv.vocab:
                    q = candidate
                    noresults = False
                    break
            if noresults:
                if our_models[usermodel]['algo'] == 'fasttext':
                    results['inferred'] = True
                else:
                    results["Unknown to the model"] = word
                    return results
            else:
                plist.append(q)
    for word in negative_list:
        if len(word) < 2:
            continue
        if word in model.wv.vocab:
            nlist.append(word)
            continue
        else:
            candidates_set = set()
            candidates_set.add(word.upper())
            if tags and our_models[usermodel]['tags'] == 'True':
                candidates_set.add(word.split('_')[0] + '_X')
                candidates_set.add(word.split('_')[0].lower() + '_' + word.split('_')[1])
                candidates_set.add(word.split('_')[0].capitalize() + '_' + word.split('_')[1])
            else:
                candidates_set.add(word.lower())
                candidates_set.add(word.capitalize())
            noresults = True
            for candidate in candidates_set:
                if candidate in model.wv.vocab:
                    q = candidate
                    noresults = False
                    break
            if noresults:
                if our_models[usermodel]['algo'] == 'fasttext':
                    results['inferred'] = True
                else:
                    results["Unknown to the model"] = word
                    return results
            else:
                nlist.append(q)
    if pos == "ALL":
        for w in model.wv.most_similar(positive=plist, negative=nlist, topn=5):
            results['neighbors'].append(w)
    else:
        for w in model.wv.most_similar(positive=plist, negative=nlist, topn=30):
            if w[0].split('_')[-1] == pos:
                results['neighbors'].append(w)
            if len(results['neighbors']) == 5:
                break
    if len(results['neighbors']) == 0:
        results['No results'] = True
        return results
    for res in results['neighbors']:
        freq, tier = frequency(res[0], usermodel)
        results['frequencies'][res[0]] = (freq, tier)
    return results


def vector(query):
    q = query['query']
    usermodel = query['model']
    results = {}
    qf = q
    results['frequencies'] = {}
    results['frequencies'][q] = frequency(q, usermodel)
    model = models_dic[usermodel]
    if q not in model.wv.vocab:
        candidates_set = set()
        candidates_set.add(q.upper())
        if tags and our_models[usermodel]['tags'] == 'True':
            candidates_set.add(q.split('_')[0] + '_X')
            candidates_set.add(q.split('_')[0].lower() + '_' + q.split('_')[1])
            candidates_set.add(q.split('_')[0].capitalize() + '_' + q.split('_')[1])
        else:
            candidates_set.add(q.lower())
            candidates_set.add(q.capitalize())
        noresults = True
        for candidate in candidates_set:
            if candidate in model.wv.vocab:
                qf = candidate
                noresults = False
                break
        if noresults:
            if our_models[usermodel]['algo'] == 'fasttext':
                results['inferred'] = True
            else:
                results[q + " is unknown to the model"] = True
                return results
    raw_vector = model[qf]
    raw_vector = raw_vector.tolist()
    results['vector'] = raw_vector
    return results


operations = {'1': find_synonyms, '2': find_similarity, '3': scalculator, '4': vector}

# Bind socket to local host and port

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
print('Socket created', file=sys.stderr)

try:
    s.bind((HOST, PORT))
except socket.error as msg:
    print('Bind failed. Error Code and message: ' + str(msg), file=sys.stderr)
    sys.exit()

print('Socket bind complete', file=sys.stderr)

# Start listening on socket
s.listen(100)
print('Socket now listening on port', PORT, file=sys.stderr)

# now keep talking with the client
while 1:
    # wait to accept a connection - blocking call
    conn, addr = s.accept()

    # start new thread takes 1st argument as a function name to be run,
    # 2nd is the tuple of arguments to the function.
    thread = WebVectorsThread(conn, addr)
    thread.start()
