#!/usr/bin/python
# coding: utf-8

from __future__ import print_function
from future import standard_library
standard_library.install_aliases()
from builtins import str
import socket
import datetime
from _thread import *
import sys
import gensim
import logging
import json
import configparser

config = configparser.RawConfigParser()
config.read('webvectors.cfg')

root = config.get('Files and directories', 'root')
HOST = config.get('Sockets', 'host')  # Symbolic name meaning all available interfaces
PORT = config.getint('Sockets', 'port')  # Arbitrary non-privileged port
tags = config.getboolean('Tags', 'use_tags')

logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)

# Loading models

our_models = {}
for line in open(root + config.get('Files and directories', 'models'), 'r').readlines():
    if line.startswith("#"):
        continue
    res = line.strip().split('\t')
    (identifier, description, path, string, default) = res
    our_models[identifier] = path

models_dic = {}

for m in our_models:
    if our_models[m].endswith('.bin.gz'):
        models_dic[m] = gensim.models.KeyedVectors.load_word2vec_format(our_models[m], binary=True)
    else:
        models_dic[m] = gensim.models.Word2Vec.load(our_models[m])
    models_dic[m].init_sims(replace=True)
    print("Model", m, "from file", our_models[m], "loaded successfully.", file=sys.stderr)


# Vector functions

def find_synonyms(query):
    q = query['query']
    pos = query['pos']
    usermodel = query['model']
    results = []
    qf = q
    model = models_dic[usermodel]
    if qf not in model:
        candidates_set = set()
        candidates_set.add(q.upper())
        if tags:
            candidates_set.add(q.split('_')[0] + '_X')
            candidates_set.add(q.split('_')[0].lower() + '_' + q.split('_')[1])
            candidates_set.add(q.split('_')[0].capitalize() + '_' + q.split('_')[1])
        else:
            candidates_set.add(q.lower())
            candidates_set.add(q.capitalize())
        noresults = True
        for candidate in candidates_set:
            if candidate in model:
                qf = candidate
                noresults = False
                break
        if noresults:
            results.append(q + " is unknown to the model")
            return results
    if pos == 'ALL':
        for i in model.most_similar(positive=qf, topn=10):
            results.append(i)
    else:
        counter = 0
        for i in model.most_similar(positive=qf, topn=20):
            if counter == 10:
                break
            if i[0].split('_')[-1] == pos:
                results.append(i)
                counter += 1
    if len(results) == 0:
        results.append('No results')
        return results
    raw_vector = model[qf]
    results.append(raw_vector.tolist())
    return results


def find_similarity(query):
    q = query['query']
    usermodel = query['model']
    model = models_dic[usermodel]
    results = []
    for pair in q:
        (q1, q2) = pair
        qf1 = q1
        qf2 = q2
        if q1 not in model:
            candidates_set = set()
            candidates_set.add(q1.upper())
            if tags:
                candidates_set.add(q1.split('_')[0] + '_X')
                candidates_set.add(q1.split('_')[0].lower() + '_' + q1.split('_')[1])
                candidates_set.add(q1.split('_')[0].capitalize() + '_' + q1.split('_')[1])
            else:
                candidates_set.add(q1.lower())
                candidates_set.add(q1.capitalize())
            noresults = True
            for candidate in candidates_set:
                if candidate in model:
                    qf1 = candidate
                    noresults = False
                    break
            if noresults:
                results.append(q1 + " is unknown to the model")
                return results
        if q2 not in model:
            candidates_set = set()
            candidates_set.add(q2.upper())
            if tags:
                candidates_set.add(q2.split('_')[0] + '_X')
                candidates_set.add(q2.split('_')[0].lower() + '_' + q2.split('_')[1])
                candidates_set.add(q2.split('_')[0].capitalize() + '_' + q2.split('_')[1])
            else:
                candidates_set.add(q2.lower())
                candidates_set.add(q2.capitalize())
            noresults = True
            for candidate in candidates_set:
                if candidate in model:
                    qf2 = candidate
                    noresults = False
                    break
            if noresults:
                results.append(q2 + " is unknown to the model")
                return results
        pair2 = (qf1, qf2)
        result = model.similarity(qf1, qf2)
        results.append((pair2, result))
    return results


def scalculator(query):
    q = query['query']
    pos = query['pos']
    usermodel = query['model']
    model = models_dic[usermodel]
    results = []
    positive_list = q[0]
    negative_list = q[1]
    plist = []
    nlist = []
    for word in positive_list:
        if word in model:
            plist.append(word)
            continue
        elif word not in model:
            candidates_set = set()
            candidates_set.add(word.upper())
            if tags:
                candidates_set.add(word.split('_')[0] + '_X')
                candidates_set.add(word.split('_')[0].lower() + '_' + word.split('_')[1])
                candidates_set.add(word.split('_')[0].capitalize() + '_' + word.split('_')[1])
            else:
                candidates_set.add(word.lower())
                candidates_set.add(word.capitalize())
            noresults = True
            for candidate in candidates_set:
                if candidate in model:
                    q = candidate
                    noresults = False
                    break
            if noresults:
                results.append(word + " is unknown to the model")
                return results
            else:
                plist.append(q)
    for word in negative_list:
        if len(word) < 2:
            continue
        if word in model:
            nlist.append(word)
            continue
        elif word not in model:
            candidates_set = set()
            candidates_set.add(word.upper())
            if tags:
                candidates_set.add(word.split('_')[0] + '_X')
                candidates_set.add(word.split('_')[0].lower() + '_' + word.split('_')[1])
                candidates_set.add(word.split('_')[0].capitalize() + '_' + word.split('_')[1])
            else:
                candidates_set.add(word.lower())
                candidates_set.add(word.capitalize())
            noresults = True
            for candidate in candidates_set:
                if candidate in model:
                    q = candidate
                    noresults = False
                    break
            if noresults:
                results.append(word + " is unknown to the model")
                return results
            else:
                nlist.append(q)
    if pos == "ALL":
        for w in model.most_similar(positive=plist, negative=nlist, topn=5):
            results.append(w)
    else:
        for w in model.most_similar(positive=plist, negative=nlist, topn=30):
            if w[0].split('_')[-1] == pos:
                results.append(w)
            if len(results) == 5:
                break
    if len(results) == 0:
        results.append("No results")
    return results


def vector(query):
    q = query['query']
    usermodel = query['model']
    qf = q
    model = models_dic[usermodel]
    if q not in model:
        candidates_set = set()
        candidates_set.add(q.upper())
        if tags:
            candidates_set.add(q.split('_')[0] + '_X')
            candidates_set.add(q.split('_')[0].lower() + '_' + q.split('_')[1])
            candidates_set.add(q.split('_')[0].capitalize() + '_' + q.split('_')[1])
        else:
            candidates_set.add(q.lower())
            candidates_set.add(q.capitalize())
        noresults = True
        for candidate in candidates_set:
            if candidate in model:
                qf = candidate
                noresults = False
                break
        if noresults:
            return [q + " is unknown to the model"]
    raw_vector = model[qf]
    raw_vector = raw_vector.tolist()
    return raw_vector


operations = {'1': find_synonyms, '2': find_similarity, '3': scalculator, '4': vector}

# Bind socket to local host and port

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
print('Socket created', file=sys.stderr)

try:
    s.bind((HOST, PORT))
except socket.error as msg:
    print('Bind failed. Message ' + str(msg), file=sys.stderr)
    sys.exit()

print('Socket bind complete', file=sys.stderr)

# Start listening on socket
s.listen(100)
print('Socket now listening on port', PORT, file=sys.stderr)


# Function for handling connections. This will be used to create threads
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
        print(now.strftime("%Y-%m-%d %H:%M"), '\t', addres[0] + ':' + str(addres[1]), '\t', data, file=sys.stderr)
        reply = json.dumps(output, ensure_ascii=False)
        connect.sendall(reply.encode('utf-8'))
        break

    # came out of loop
    connect.close()


# now keep talking with the client
while 1:
    # wait to accept a connection - blocking call
    conn, addr = s.accept()

    # start new thread takes 1st argument as a function name to be run, 2nd is the tuple of arguments to the function.
    start_new_thread(clientthread, (conn, addr))
