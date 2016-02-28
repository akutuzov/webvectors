#!/usr/bin/python2
# coding: utf-8

# This script launches a service which loads word2vec models and responds to socket queries (port defined below).

import socket
import sys, datetime
from thread import *
import sys, gensim, logging

root = 'YOUR ROOT DIRECTORY HERE' # Directory where WebVectors resides
HOST = 'localhost'  # Symbolic name meaning all available interfaces
PORT = 12666  # Arbitrary non-privileged port

logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)

# Loading models

our_models = {}
for line in open(root + 'models.csv', 'r').readlines():
    if line.startswith("#"):
        continue
    res = line.strip().split('\t')
    (identifier, description, path, string) = res
    our_models[identifier] = path

models_dic = {}

for m in our_models:
    if our_models[m].endswith('.bin.gz'):
        models_dic[m] = gensim.models.Word2Vec.load_word2vec_format(our_models[m], binary=True)
    else:
        models_dic[m] = gensim.models.Word2Vec.load(our_models[m])
    models_dic[m].init_sims(replace=True)
    print "Model", m, "from file", our_models[m], "loaded successfully."

# Vector functions

def find_synonyms(query):
    (q, pos, usermodel) = query
    results = []
    qf = q
    model = models_dic[usermodel]
    if not qf in model:
        candidates_set = set()
        candidates_set.add(q.split('_')[0] + '_UNKN')
        candidates_set.add(q.upper())
        candidates_set.add(q.split('_')[0].lower() + '_' + q.split('_')[1])
        candidates_set.add(q.split('_')[0].capitalize() + '_' + q.split('_')[1])
        noresults = True
        for candidate in candidates_set:
            if candidate in model:
                qf = candidate
                noresults = False
                break
        if noresults == True:
            results.append(q + " is unknown to the model")
            return results
    if pos == 'ALL':
        for i in model.most_similar(positive=qf, topn=10):
            results.append(i[0] + "#" + str(i[1]))
    else:
        counter = 0
        for i in model.most_similar(positive=qf, topn=20):
            if counter == 10:
                break
            if i[0].split('_')[-1] == pos:
                results.append(i[0] + "#" + str(i[1]))
                counter += 1
    if len(results) == 0:
        results.append('No results')
        return results
    vector = model[qf]
    results.append(vector)
    return results


def find_similarity(query):
    (q, usermodel) = query
    model = models_dic[usermodel]
    results = []
    for pair in q.split(','):
        (q1, q2) = pair.split()
        qf1 = q1
        qf2 = q2
        if not q1 in model:
            candidates_set = set()
            candidates_set.add(q1.split('_')[0] + '_UNKN')
            candidates_set.add(q1.upper())
            candidates_set.add(q1.lower())
            candidates_set.add(q1.split('_')[0].capitalize() + '_' + q1.split('_')[1])
            noresults = True
            for candidate in candidates_set:
                if candidate in model:
                    qf1 = candidate
                    noresults = False
                    break
            if noresults == True:
                return ["The model does not know the word %s" % q1]
        if not q2 in model:
            candidates_set = set()
            candidates_set.add(q2.split('_')[0] + '_UNKN')
            candidates_set.add(q2.upper())
            candidates_set.add(q2.lower())
            candidates_set.add(q2.split('_')[0].capitalize() + '_' + q2.split('_')[1])
            noresults = True
            for candidate in candidates_set:
                if candidate in model:
                    qf2 = candidate
                    noresults = False
                    break
            if noresults == True:
                return ["The model does not know the word %s" % q2]
        pair2 = (qf1, qf2)
        result = model.similarity(qf1, qf2)
        results.append('#'.join(pair2) + "#" + str(result))
    return results


def scalculator(query):
    (q, pos, usermodel) = query
    model = models_dic[usermodel]
    results = []
    positive_list = q.split("&")[0].split(',')
    negative_list = q.split("&")[1].split(',')
    plist = []
    nlist = []
    for word in positive_list:
        if word in model:
            plist.append(word)
            continue
        elif not word in model:
            candidates_set = set()
            candidates_set.add(word.split('_')[0] + '_UNKN')
            candidates_set.add(word.upper())
            candidates_set.add(word.lower())
            candidates_set.add(word.split('_')[0].capitalize() + '_' + word.split('_')[1])
            noresults = True
            for candidate in candidates_set:
                if candidate in model:
                    q = candidate
                    noresults = False
                    break
            if noresults == True:
                return ["The model does not know the word %s" % word]
            else:
                plist.append(q)
    for word in negative_list:
        if len(word) < 2:
            continue
        if word in model:
            nlist.append(word)
            continue
        elif not word in model:
            candidates_set = set()
            candidates_set.add(word.split('_')[0] + '_UNKN')
            candidates_set.add(word.upper())
            candidates_set.add(word.lower())
            candidates_set.add(word.split('_')[0].capitalize() + '_' + word.split('_')[1])
            noresults = True
            for candidate in candidates_set:
                if candidate in model:
                    q = candidate
                    noresults = False
                    break
            if noresults == True:
                return ["The model does not know the word %s" % word]
            else:
                nlist.append(q)
    if pos == "ALL":
        for w in model.most_similar(positive=plist, negative=nlist, topn=5):
            results.append(w[0] + "#" + str(w[1]))
    else:
        for w in model.most_similar(positive=plist, negative=nlist, topn=30):
            if w[0].split('_')[-1] == pos:
                results.append(w[0] + "#" + str(w[1]))
            if len(results) == 5:
                break
	if len(results) == 0:
	    results.append("No results")
    return results


def vector(query):
    (q, usermodel) = query
    qf = q
    model = models_dic[usermodel]
    if not q in model:
        candidates_set = set()
        candidates_set.add(q.split('_')[0] + '_UNKN')
        candidates_set.add(q.upper())
        candidates_set.add(q.lower())
        candidates_set.add(q.split('_')[0].capitalize() + '_' + q.split('_')[1])
        noresults = True
        for candidate in candidates_set:
            if candidate in model:
                qf = candidate
                noresults = False
                break
        if noresults == True:
            return q + " is unknown to the model"
    vector = model[qf]
    vector = vector.tolist()
    str_vector = ','.join([str(e) for e in vector])
    return str_vector


operations = {'1': find_synonyms, '2': find_similarity, '3': scalculator, '4': vector}

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
print 'Socket created'

# Bind socket to local host and port
try:
    s.bind((HOST, PORT))
except socket.error, msg:
    print 'Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1]
    sys.exit()

print 'Socket bind complete'

#Start listening on socket
s.listen(100)
print 'Socket now listening on port', PORT

#Function for handling connections. This will be used to create threads
def clientthread(conn, addr):
    #Sending message to connected client
    conn.send('word2vec model server')  #send only takes string

    #infinite loop so that function do not terminate and thread do not end.
    while True:
        #Receiving from client
        data = conn.recv(1024)
        data = data.decode("utf-8")
        query = data.split(";")
        output = operations[query[0]]((query[1:]))
        if not data:
            break
        now = datetime.datetime.now()
        print now.strftime("%Y-%m-%d %H:%M"), '\t', addr[0] + ':' + str(addr[1]), '\t', data
        if query[0] == "1" and not 'unknown to the' in output[0] and not "No results" in output[0]:
            reply = ' '.join(output[:-1])
            vector = output[-1].tolist()
            str_vector = ','.join([str(e) for e in vector])
            conn.sendall(reply.encode('utf-8') + "&" + str_vector)
        elif query[0] == "4":
            reply = output
            conn.sendall(reply.encode('utf-8'))
        else:
            reply = ' '.join(output)
            conn.sendall(reply.encode('utf-8'))

        break

    #came out of loop
    conn.close()

#now keep talking with the client
while 1:
    #wait to accept a connection - blocking call
    conn, addr = s.accept()

    #start new thread takes 1st argument as a function name to be run, second is the tuple of arguments to the function.
    start_new_thread(clientthread, (conn, addr))

s.close()
