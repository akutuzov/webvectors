#!/usr/bin/python
# coding: utf-8

from __future__ import print_function
from future import standard_library
standard_library.install_aliases()
from builtins import zip
from builtins import map
from builtins import str

import configparser
import codecs
import hashlib
import json
import logging
import os
import socket  # for sockets
import sys
from collections import OrderedDict

import numpy as np
from flask import g
from flask import render_template, Blueprint, redirect, Response
from flask import request

from plotting import embed
from plotting import singularplot
from sparql import getdbpediaimage
# import strings data from respective module
from strings_reader import language_dicts
from timeout import timeout

languages = '/'.join(list(language_dicts.keys())).upper()

config = configparser.RawConfigParser()
config.read('/home/lizaku/PycharmProjects/webvectors/webvectors.cfg')

root = config.get('Files and directories', 'root')
modelsfile = config.get('Files and directories', 'models')
cachefile = config.get('Files and directories', 'image_cache')
temp = config.get('Files and directories', 'temp')

url = config.get('Other', 'url')

lemmatize = config.getboolean('Tags', 'lemmatize')
dbpedia = config.getboolean('Other', 'dbpedia_images')
languages_list = config.get('Languages', 'interface_languages').split(',')

if lemmatize:
    from lemmatizer import tagword

tensorflow_integration = config.getboolean('Other', 'tensorflow_projector')
if tensorflow_integration:
    from simplegist import Simplegist
    git_username = config.get('Other', 'git_username')
    git_token = config.get('Other', 'git_token')
    ghGist = Simplegist(username=git_username, api_token=git_token)

# Establishing connection to model server
host = config.get('Sockets', 'host')
port = config.getint('Sockets', 'port')
try:
    remote_ip = socket.gethostbyname(host)
except socket.gaierror:
    # could not resolve
    print('Hostname could not be resolved. Exiting', file=sys.stderr)
    sys.exit()


def serverquery(message):
    # create an INET, STREAMing socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except socket.error:
        print('Failed to create socket', file=sys.stderr)
        return None

    # Connect to remote server
    s.connect((remote_ip, port))
    # Now receive initial data
    initial_reply = s.recv(1024)

    # Send some data to remote server
    d_message = json.dumps(message, ensure_ascii=False)
    try:
        s.sendall(d_message.encode('utf-8'))
    except socket.error:
        # Send failed
        print('Send failed', file=sys.stderr)
        s.close()
        return None
    # Now receive data
    reply = s.recv(32768)
    s.close()
    return reply


tags = config.getboolean('Tags', 'use_tags')
exposed_tags = {}
if tags:
    taglist = set(config.get('Tags', 'tags_list').split())
    exposed_tag_file = config.get('Tags', 'exposed_tags_list')

    for line in open(root + exposed_tag_file, 'r').readlines():
        if line.startswith("#"):
            continue
        res = line.strip().split('\t')
        (tag, string, default) = res
        if default == 'True':
            defaulttag = tag
        exposed_tags[tag] = string

defaultsearchengine = config.get('Other', 'default_search')

our_models = {}
for line in open(root + modelsfile, 'r').readlines():
    if line.startswith("#"):
        continue
    res = line.strip().split('\t')
    (id_string, description, path, string, default) = res
    if default == 'True':
        defaultmodel = id_string
    our_models[id_string] = string

logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)

wvectors = Blueprint('wvectors', __name__, template_folder='templates')


def after_this_request(func):
    if not hasattr(g, 'call_after_request'):
        g.call_after_request = []
    g.call_after_request.append(func)
    return func


@wvectors.after_request
def per_request_callbacks(response):
    for func in getattr(g, 'call_after_request', ()):
        response = func(response)
    return response


def process_query(userquery):
    userquery = userquery.strip()
    query = userquery
    if tags:
        if '_' in userquery:
            query_split = userquery.split('_')
            if query_split[-1] in taglist:
                query = ''.join(query_split[:-1]) + '_' + query_split[-1]
            else:
                return 'Incorrect tag!'
        else:
            if lemmatize:
                poses = tagword(userquery)
                if len(poses) == 1:
                    pos_tag = poses[0]
                else:
                    pos_tag = poses[-1]
                query = userquery.replace(' ', '::') + '_' + pos_tag
            else:
                return 'Incorrect tag!'
    return query


@timeout(10)
def get_images(images):
    imagecache = {}
    imagedata = codecs.open(root + cachefile, 'r', 'utf-8')
    for LINE in imagedata:
        result = LINE.strip().split('\t')
        if len(result) == 2:
            (word, image) = result
            image = image.strip()
            if image == 'None':
                image = None
            imagecache[word.strip()] = image
        else:
            continue
    imagedata.close()
    for w in images:
        image = getdbpediaimage(w.encode('utf-8'), imagecache)
        if image:
            images[w] = image
    return images


def word2vec2tensor(alias, vectorlist, wordlist, classes):
    outfiletsv = alias + '_tensor.tsv'
    outfiletsvmeta = alias + '_metadata.tsv'
    tensortext = ''
    metadatatext = ''
    metadatatext += 'word' + '\t' + 'Class' + '\n'
    for word, vector, group in zip(wordlist, vectorlist, classes):
        (lemma, pos) = word.split('_')
        metadatatext += lemma + '\t' + str(group) + '\n'
        vector_row = '\t'.join(map(str, vector))
        tensortext += vector_row + '\n'
    a = ghGist.create(name=outfiletsv, description='Tensors', public=True, content=tensortext)
    b = ghGist.create(name=outfiletsvmeta, description='Metadata', public=True, content=metadatatext)
    datadic = {"embeddings": [{"tensorName": 'WebVectors', "tensorShape": [len(vectorlist[0]), len(wordlist)],
                               "tensorPath": a['files'][outfiletsv]['raw_url'],
                               "metadataPath": b['files'][outfiletsvmeta]['raw_url']}]}
    c = ghGist.create(name=alias + '_config.json', description='WebVectors', public=True,
                      content=json.dumps(datadic))
    link2config = c['files'][alias + '_config.json']['raw_url']
    outputfile = open(root + 'data/images/tsneplots/' + alias + '.url', 'w')
    outputfile.write(link2config)
    outputfile.close()
    return link2config


@wvectors.route(url + '<lang:lang>/', methods=['GET', 'POST'])
def home(lang):
    # pass all required variables to template
    # repeated within each @wvectors.route function
    g.lang = lang
    s = set()
    s.add(lang)
    other_lang = list(set(language_dicts.keys()) - s)[0]  # works only for two languages
    g.strings = language_dicts[lang]

    if request.method == 'POST':
        list_data = 'dummy'
        try:
            list_data = request.form['list_query']
        except:
            pass
        if list_data != 'dummy' and \
                list_data.replace('_', '').replace('-', '').replace('::', '').replace(' ', '').isalnum():
            query = process_query(list_data)
            if query == "Incorrect tag!":
                error_value = "Incorrect tag!"
                return render_template('home.html', error=error_value, other_lang=other_lang, languages=languages,
                                       url=url)
            model_value = request.form.getlist('model')
            if len(model_value) < 1:
                model = defaultmodel
            else:
                model = model_value[0]
            images = {query.split('_')[0]: None}
            message = {'operation': '1', 'query': query, 'pos': 'ALL', 'model': model}
            result = json.loads(serverquery(message).decode('utf-8'))
            if "unknown to the" in result[0]:
                return render_template('home.html', error=result[0], other_lang=other_lang,
                                       languages=languages, url=url, word=query)
            else:
                for word in result[:-1]:
                    images[word[0].split('_')[0]] = None
                if dbpedia:
                    try:
                        images = get_images(images)
                    except:
                        pass
                return render_template('home.html', list_value=result[:-1], word=query, wordimages=images,
                                       model=model, tags=tags, other_lang=other_lang, languages=languages, url=url)
        else:
            error_value = "Incorrect query!"
            return render_template("home.html", error=error_value, tags=tags, other_lang=other_lang,
                                   languages=languages, url=url)
    return render_template('home.html', tags=tags, other_lang=other_lang, languages=languages, url=url)

@wvectors.route(url + '<lang:lang>/misc/', methods=['GET', 'POST'])
def misc_page(lang):
    g.lang = lang
    s = set()
    s.add(lang)
    other_lang = list(set(language_dicts.keys()) - s)[0]  # works only for two languages
    g.strings = language_dicts[lang]
    
    if request.method == 'POST':
        input_data = 'dummy'
        try:
            input_data = request.form['query']
        except:
            pass
        
        # Similarity queries
        if input_data != 'dummy':
            if ' ' in input_data.strip():
                input_data = input_data.strip()
                if input_data.endswith(','):
                    input_data = input_data[:-1]
                cleared_data = []

                sim_history = request.form['sim_history']
                if not sim_history.strip():
                    sim_history = []
                else:
                    sim_history = json.loads(sim_history)

                model_value = request.form.getlist('simmodel')
                if len(model_value) < 1:
                    model = defaultmodel
                else:
                    model = model_value[0]
                if not model.strip() in our_models:
                    return render_template('home.html', other_lang=other_lang, languages=languages, url=url,
                                           usermodels=model_value)
                for query in input_data.split(','):
                    if '' not in query.strip():
                        continue
                    query = query.split()
                    words = []
                    for w in query[:2]:
                        if w.replace('_', '').replace('-', '').replace('::', '').isalnum():
                            w = process_query(w)
                            if "Incorrect tag!" in w:
                                error_value = "Incorrect tag!"
                                return render_template('similar.html', error_sim=error_value, models=our_models,
                                                       other_lang=other_lang, languages=languages, url=url,
                                                       usermodels=model_value, tags2show=exposed_tags)
                            words.append(w.strip())
                    if len(words) == 2:
                        cleared_data.append((words[0].strip(), words[1].strip()))
                if len(cleared_data) == 0:
                    error_value = "Incorrect query!"
                    return render_template("similar.html", error_sim=error_value, other_lang=other_lang,
                                           languages=languages, url=url, usermodels=model_value, tags2show=exposed_tags)
                message = {'operation': '2', 'query': cleared_data, 'model': model}
                result = json.loads(serverquery(message).decode('utf-8'))
                cleared_data = [' '.join(el) for el in cleared_data]
                if "unknown to the" in result[0]:
                    return render_template("similar.html", error_sim=result[0], other_lang=other_lang,
                                           languages=languages, models=our_models, tags2show=exposed_tags,
                                           tags=tags, query=cleared_data, url=url, usermodels=model_value)
                sim_history.append(result)
                if len(sim_history) > 10:
                    sim_history = sim_history[-10:]
                str_sim_history = (json.dumps(sim_history, ensure_ascii=False))
                return render_template('similar.html', value=result, model=model, query=cleared_data,
                                       models=our_models, tags=tags, other_lang=other_lang, tags2show=exposed_tags,
                                       languages=languages, url=url, usermodels=model_value, sim_hist=sim_history,
                                       str_sim_history=str_sim_history)
            else:
                error_value = "Incorrect query!"
                return render_template("similar.html", error_sim=error_value, models=our_models, tags=tags,
                                       tags2show=exposed_tags,
                                       other_lang=other_lang, languages=languages, url=url, usermodels=[defaultmodel])
    return render_template('similar.html', models=our_models, tags=tags, other_lang=other_lang, tags2show=exposed_tags,
                           languages=languages, url=url, usermodels=[defaultmodel])



@wvectors.route(url + '<lang:lang>/similar/', methods=['GET', 'POST'])
def similar_page(lang):
    g.lang = lang
    s = set()
    s.add(lang)
    other_lang = list(set(language_dicts.keys()) - s)[0]  # works only for two languages
    g.strings = language_dicts[lang]

    if request.method == 'POST':
        list_data = 'dummy'
        try:
            list_data = request.form['list_query']
        except:
            pass
        
        # Nearest associates queries
        if list_data != 'dummy' and \
                list_data.replace('_', '').replace('-', '').replace('::', '').replace(' ', '').isalnum():
            list_data = list_data.strip()
            query = process_query(list_data)

            model_value = request.form.getlist('model')
            if len(model_value) < 1:
                model_value = [defaultmodel]

            if query == "Incorrect tag!":
                error_value = "Incorrect tag!"
                return render_template('similar.html', error=error_value, word=list_data, models=our_models,
                                       tags2show=exposed_tags,
                                       other_lang=other_lang, languages=languages, url=url, usermodels=model_value)
            userpos = []
            if tags:
                pos_value = request.form.getlist('pos')
                if len(pos_value) < 1:
                    pos = query.split('_')[-1]
                else:
                    pos = pos_value[0]
                if pos != 'ALL':
                    userpos.append(pos)
                if pos == 'Q':
                    pos = query.split('_')[-1]
            else:
                pos = 'ALL'

            images = {query.split('_')[0]: None}
            models_row = {}
            for model in model_value:
                if not model.strip() in our_models:
                    return render_template('home.html', other_lang=other_lang, languages=languages, url=url,
                                           usermodels=model_value)
                message = {'operation': '1', 'query': query, 'pos': pos, 'model': model}
                result = json.loads(serverquery(message).decode('utf-8'))
                if "unknown to the" in result[0]:
                    models_row[model] = "Unknown!"
                    continue
                elif "No results" in result[0]:
                    models_row[model] = 'No results!'
                    continue
                else:
                    for word in result[:-1]:
                        images[word[0].split('_')[0]] = None
                    models_row[model] = result[:-1]
                    if dbpedia:
                        try:
                            images = get_images(images)
                        except:
                            pass
            return render_template('associates.html', list_value=models_row, word=query, pos=pos, userpos=userpos,
                                   number=len(model_value), wordimages=images, models=our_models, tags=tags,
                                   other_lang=other_lang, languages=languages, tags2show=exposed_tags,
                                   url=url, usermodels=model_value)
        else:
            error_value = "Incorrect query!"
            return render_template("asociates.html", error=error_value, models=our_models, tags=tags, url=url,
                                   usermodels=[defaultmodel], tags2show=exposed_tags)
    return render_template('associates.html', models=our_models, tags=tags, other_lang=other_lang, tags2show=exposed_tags,
                           languages=languages, url=url, usermodels=[defaultmodel])


@wvectors.route(url + '<lang:lang>/visual/', methods=['GET', 'POST'])
def visual_page(lang):
    g.lang = lang
    s = set()
    s.add(lang)
    other_lang = list(set(language_dicts.keys()) - s)[0]  # works only for two languages
    g.strings = language_dicts[lang]

    if request.method == 'POST':
        list_data = request.form.getlist('list_query')
        if list_data:
            model_value = request.form.getlist('model')
            if len(model_value) < 1:
                model_value = [defaultmodel]

            groups = []
            for inputform in list_data[:10]:
                group = set([process_query(w) for w in inputform.split(',') if len(w) > 1
                             and w.replace('_', '').replace('-', '').replace('::', '').replace(' ', '').isalnum()][:30])
                groups.append(group)

            querywords = [word for group in groups for word in group]
            if len(set(querywords)) != len(querywords):
                error_value = "Words must be unique!"
                return render_template("visual.html", error=error_value, models=our_models, other_lang=other_lang,
                                       languages=languages, url=url, usermodels=model_value)
            if len(querywords) < 7:
                error_value = "Too few words!"
                return render_template("visual.html", error=error_value, models=our_models, other_lang=other_lang,
                                       languages=languages, url=url, usermodels=model_value)

            if "Incorrect tag!" in querywords:
                error_value = "Incorrect tag!"
                return render_template('visual.html', error=error_value, models=our_models, other_lang=other_lang,
                                       languages=languages, url=url, usermodels=model_value)

            classes = []
            for word in querywords:
                for group in groups:
                    if word in group:
                        classes.append(groups.index(group))

            unknown = {}
            models_row = {}
            links_row = {}
            for model in model_value:
                if not model.strip() in our_models:
                    return render_template('home.html', other_lang=other_lang, languages=languages, url=url,
                                           usermodels=model_value)
                unknown[model] = set()
                words2vis = querywords
                m = hashlib.md5()
                name = ':::'.join(['__'.join(group) for group in groups])
                name = name.encode('ascii', 'backslashreplace')
                m.update(name)
                fname = m.hexdigest()
                plotfile = "%s_%s.png" % (model, fname)
                identifier = plotfile[:-4]
                models_row[model] = plotfile
                labels = []
                if not os.path.exists(root + 'data/images/tsneplots'):
                    os.makedirs(root + 'data/images/tsneplots')
                if not os.access(root + 'data/images/tsneplots/' + plotfile, os.F_OK):
                    print('No previous image found', root + 'data/images/tsneplots/' + plotfile, file=sys.stderr)
                    vectors = []
                    for w in words2vis:
                        message = {'operation': '4', 'query': w, 'model': model}
                        result = json.loads(serverquery(message).decode('utf-8'))
                        if len(result) == 1:
                            if 'is unknown' in result[0]:
                                unknown[model].add(w)
                                continue
                        vector = np.array(result)
                        vectors.append(vector)
                        labels.append(w)
                    if len(vectors) > 5:
                        if len(list_data) == 1:
                            classes = [word.split('_')[-1] for word in labels]
                        matrix2vis = np.vstack(([v for v in vectors]))
                        embed(labels, matrix2vis.astype('float64'), classes, model, fname)
                        models_row[model] = plotfile
                        if tensorflow_integration:
                            l2c = word2vec2tensor(identifier, vectors, labels, classes)
                        else:
                            l2c = None
                        links_row[model] = l2c
                    else:
                        models_row[model] = "Too few words!"
                else:
                    if tensorflow_integration:
                        links_row[model] = open(root + 'data/images/tsneplots/' + identifier + '.url', 'r').read()
                    else:
                        links_row[model] = None
            return render_template('visual.html', languages=languages, visual=models_row, words=groups,
                                   number=len(model_value), models=our_models, unknown=unknown, url=url,
                                   usermodels=model_value, l2c=links_row, qwords=querywords)
        else:
            error_value = "Incorrect query!"
            return render_template("visual.html", error=error_value, models=our_models, other_lang=other_lang,
                                   languages=languages, url=url, usermodels=[defaultmodel])
    return render_template('visual.html', models=our_models, other_lang=other_lang, languages=languages,
                           url=url, usermodels=[defaultmodel])


@wvectors.route(url + '<lang:lang>/calculator/', methods=['GET', 'POST'])
def finder(lang):
    g.lang = lang
    s = set()
    s.add(lang)
    other_lang = list(set(language_dicts.keys()) - s)[0]  # works only for two languages
    g.strings = language_dicts[lang]

    if request.method == 'POST':
        positive_data = ''
        positive2_data = ''
        negative_data = ''
        positive1_data = ''
        negative1_data = ''
        try:
            positive_data = request.form['positive']
            positive2_data = request.form['positive2']
            negative_data = request.form['negative']
        except:
            pass
        try:
            positive1_data = request.form['positive1']
            negative1_data = request.form['negative1']
        except:
            pass
        # Analogical inference
        if negative_data != '' and positive_data != '' and positive2_data != '':
            positive_data_list = [positive_data, positive2_data]
            negative_list = []
            if len(negative_data.strip()) > 1:
                if negative_data.strip().replace('_', '').replace('-', '').replace('::', '').replace(' ', '').isalnum():
                    negative_list = [process_query(negative_data)]

            positive_list = []
            for w in positive_data_list:
                if len(w) > 1 and w.replace('_', '').replace('-', '').replace('::', '').replace(' ', '').isalnum():
                    positive_list.append(process_query(w))

            calcmodel_value = request.form.getlist('calcmodel')
            if len(calcmodel_value) < 1:
                calcmodel_value = [defaultmodel]

            if len(positive_list) < 2 or len(negative_list) == 0:
                error_value = "Incorrect query!"
                return render_template("calculator.html", error=error_value, models=our_models, other_lang=other_lang,
                                       languages=languages, url=url, usermodels=calcmodel_value, tags2show=exposed_tags)
            if "Incorrect tag!" in negative_list or "Incorrect tag!" in positive_list:
                error_value = "Incorrect tag!"
                return render_template('calculator.html', error=error_value, models=our_models, tags2show=exposed_tags,
                                       other_lang=other_lang, languages=languages, url=url, usermodels=calcmodel_value)
            userpos = []
            if tags:
                calcpos_value = request.form.getlist('pos')
                if len(calcpos_value) < 1:
                    pos = defaulttag
                else:
                    pos = calcpos_value[0]
                if pos != 'ALL':
                    userpos.append(pos)
            else:
                pos = 'ALL'

            models_row = {}
            images = {}
            for model in calcmodel_value:
                if not model.strip() in our_models:
                    return render_template('home.html', other_lang=other_lang, languages=languages,
                                           models=our_models, url=url, usermodels=calcmodel_value)
                message = {'operation': '3', 'query': [positive_list, negative_list], 'pos': pos, 'model': model}
                result = json.loads(serverquery(message).decode('utf-8'))
                if len(result) == 0 or 'No results' in result[0]:
                    models_row[model] = ["No similar words with this tag."]
                    continue
                if "is unknown" in result[0]:
                    models_row[model] = result[0]
                    continue
                for word in result:
                    images[word[0].split('_')[0]] = None
                models_row[model] = result
                if dbpedia:
                    try:
                        images = get_images(images)
                    except:
                        pass
            return render_template('calculator.html', analogy_value=models_row, pos=pos, plist=positive_list,
                                   userpos=userpos, nlist=negative_list, wordimages=images, models=our_models,
                                   tags=tags, other_lang=other_lang, languages=languages, url=url,
                                   usermodels=calcmodel_value, tags2show=exposed_tags)

        # Calculator
        if positive1_data != '':
            negative_list = [process_query(w) for w in negative1_data.split() if
                             len(w) > 1 and w.replace('_', '').replace('-', '').replace('::', '').isalnum()][:10]
            positive_list = [process_query(w) for w in positive1_data.split() if
                             len(w) > 1 and w.replace('_', '').replace('-', '').replace('::', '').isalnum()][:10]

            calcmodel_value = request.form.getlist('calcmodel')
            if len(calcmodel_value) < 1:
                calcmodel_value = [defaultmodel]

            if len(positive_list) == 0:
                error_value = "Incorrect query!"
                return render_template("calculator.html", calc_error=error_value, other_lang=other_lang,
                                       tags2show=exposed_tags,
                                       languages=languages, models=our_models, url=url, usermodels=calcmodel_value)
            if "Incorrect tag!" in negative_list or "Incorrect tag!" in positive_list:
                error_value = "Incorrect tag!"
                return render_template('calculator.html', calc_error=error_value, other_lang=other_lang,
                                       tags2show=exposed_tags,
                                       languages=languages, models=our_models, url=url, usermodels=calcmodel_value)
            userpos = []
            if tags:
                calcpos_value = request.form.getlist('calcpos')
                if len(calcpos_value) < 1:
                    pos = defaulttag
                else:
                    pos = calcpos_value[0]
                if pos != 'ALL':
                    userpos.append(pos)
            else:
                pos = 'ALL'

            models_row = {}
            images = {}
            for model in calcmodel_value:
                if not model.strip() in our_models:
                    return render_template('home.html', other_lang=other_lang, languages=languages,
                                           models=our_models, url=url, usermodels=calcmodel_value)
                message = {'operation': '3', 'query': [positive_list, negative_list], 'pos': pos, 'model': model}
                result = json.loads(serverquery(message).decode('utf-8'))
                if len(result) == 0 or "No results" in result[0]:
                    models_row[model] = ["No similar words with this tag."]
                    continue
                if "is unknown" in result[0]:
                    models_row[model] = result[0]
                    continue
                for word in result:
                    images[word[0].split('_')[0]] = None
                models_row[model] = result
                if dbpedia:
                    try:
                        images = get_images(images)
                    except:
                        pass
            return render_template('calculator.html', calc_value=models_row, pos=pos, plist2=positive_list,
                                   tags2show=exposed_tags, nlist2=negative_list, wordimages=images, models=our_models,
                                   tags=tags, userpos=userpos, other_lang=other_lang, languages=languages, url=url,
                                   usermodels=calcmodel_value)

        else:
            error_value = "Incorrect query!"
            return render_template("calculator.html", error=error_value, models=our_models, tags=tags,
                                   tags2show=exposed_tags,
                                   other_lang=other_lang, languages=languages, url=url, usermodels=[defaultmodel])
    return render_template("calculator.html", models=our_models, tags=tags, other_lang=other_lang,
                           languages=languages, url=url, usermodels=[defaultmodel], tags2show=exposed_tags)


@wvectors.route(url + '<lang:lang>/<model>/<userquery>/', methods=['GET', 'POST'])
def raw_finder(lang, model, userquery):
    g.lang = lang
    s = set()
    s.add(lang)
    other_lang = list(set(language_dicts.keys()) - s)[0]  # works only for two languages
    g.strings = language_dicts[lang]

    model = model.strip()
    if not model.strip() in our_models:
        return render_template('home.html', other_lang=other_lang, languages=languages, url=url)
    if userquery.strip().replace('_', '').replace('-', '').replace('::', '').isalnum():
        query = process_query(userquery.strip())
        if tags:
            if len(query.split('_')) < 2:
                error_value = "Incorrect tag!"
                return render_template('wordpage.html', error=error_value, other_lang=other_lang,
                                       languages=languages, url=url)
            pos_tag = query.split('_')[-1]
        else:
            pos_tag = 'ALL'
        images = {query.split('_')[0]: None}
        image = None
        message = {'operation': '1', 'query': query, 'pos': pos_tag, 'model': model}
        result = json.loads(serverquery(message).decode('utf-8'))
        if "unknown to the" in result[0] or "No results" in result[0]:
            return render_template('wordpage.html', error=result[0], other_lang=other_lang,
                                   languages=languages, url=url, word=query, models=our_models, model=model)
        else:
            vector = result[-1]
            for word in result[:-1]:
                images[word[0].split('_')[0]] = None
            m = hashlib.md5()
            name = query.encode('ascii', 'backslashreplace')
            m.update(name)
            fname = m.hexdigest()
            plotfile = root + 'data/images/singleplots/' + model + '_' + fname + '.png'
            if not os.access(plotfile, os.F_OK):
                singularplot(query, model, vector, fname)
            if dbpedia:
                try:
                    images = get_images(images)
                    image = images[query.split('_')[0]]
                except:
                    pass
            return render_template('wordpage.html', list_value=result[:-1], word=query, model=model, pos=pos_tag,
                                   vector=vector, image=image, wordimages=images, vectorvis=fname, tags=tags,
                                   other_lang=other_lang, languages=languages, url=url, search=defaultsearchengine,
                                   models=our_models)
    else:
        error_value = 'Incorrect query!'
        return render_template("wordpage.html", error=error_value, tags=tags, other_lang=other_lang,
                               languages=languages, url=url)


def generate(word, model, api_format):
    """
    yields result of the query
    :param model: name of a model to be queried
    :param word: query word
    :param api_format: format of the output - csv or json
    """

    formats = {'csv', 'json'}

    # check the sanity of the query word: no punctuation marks, not an empty string
    if not word.strip().replace('_', '').replace('-', '').replace('::', '').isalnum():
        word = ''.join([char for char in word if char.isalnum()])
        yield word.strip() + '\t' + model.strip() + '\t' + 'Word error!'
    else:
        query = process_query(word.strip())

        # if tags are used, check whether the word is tagged
        if tags:
            if len(query.split('_')) < 2:
                yield query.strip() + '\t' + model.strip() + '\t' + 'Error!'

        # check whether the format is correct
        if api_format not in formats:
            yield api_format + '\t' + 'Output format error!'

        # if all is OK...
        # check that the model exists
        if not model.strip() in our_models:
            yield query.strip() + '\t' + model.strip() + '\t' + 'Model error!'
        else:
            # form the query and get the result from the server
            message = {'operation': '1', 'query': query, 'pos': 'ALL', 'model': model}
            result = json.loads(serverquery(message).decode('utf-8'))

            # handle cases when the server returned that the word is unknown to the model,
            # or for some other reason the associates list is empty
            if "unknown to the" in result[0] or "No results" in result[0]:
                yield query + '\t' + result[0]
            else:
                # return result in csv
                if api_format == 'csv':
                    yield model + '\n'
                    yield query + '\n'
                    for associate in result[:-1]:
                        yield "%s\t%s\n" % (associate[0], str(associate[1]))

                # return result in json
                elif api_format == 'json':
                    associates = OrderedDict()
                    for associate in result[:-1]:
                        associates[associate[0]] = associate[1]
                    result = {model: {query: associates}}
                    yield json.dumps(result, ensure_ascii=False)


@wvectors.route(url + '<model>/<word>/api/<api_format>', methods=['GET'])
def api(model, word, api_format):
    """
    provides a list of neighbors for a given word in downloadable form: csv or json
    :param model: a name of a model to be queried
    :param word: a query word
    :param api_format: a format of the output - csv or json
    :return: generated file with neighbors in the requested format
    all function arguments are strings
    """
    model = model.strip()

    # define mime type
    if api_format == 'csv':
        mime = 'text/csv'
    else:
        mime = 'application/json'

    cleanword = ''.join([char for char in word if char.isalnum()])
    return Response(generate(word, model, api_format), mimetype=mime,
                    headers={"Content-Disposition": "attachment;filename=%s.%s" % (cleanword.encode('utf-8'),
                                                                                   api_format.encode('utf-8'))})


@wvectors.route(url + '<model>/<wordpair>/api/similarity/', methods=['GET'])
def similarity_api(model, wordpair):
    """
    provides a similarity value for a given word pair
    :param model: a name of a model to be queried
    :param wordpair: a query word pair separated by __ (2 underscores)
    :return: similarity value as a string
    all function arguments are strings
    """
    model = model.strip()
    wordpair = wordpair.split('__')
    if not model.strip() in our_models:
        return 'The model ' + model.strip() + ' is unknown'
    cleanword0 = ''.join([char for char in wordpair[0] if char.isalnum() or char == '_' or char == '::' or char == '-'])
    cleanword1 = ''.join([char for char in wordpair[1] if char.isalnum() or char == '_' or char == '::' or char == '-'])
    cleanword0 = process_query(cleanword0)
    cleanword1 = process_query(cleanword1)
    message = {'operation': '2', 'query': [[cleanword0, cleanword1]], 'model': model}
    result = json.loads(serverquery(message).decode('utf-8'))
    if 'is unknown' in result[0]:
        return 'Unknown'
    sim = result[0][-1]
    return str(sim) + '\t' + cleanword0 + '\t' + cleanword1 + '\t' + model


@wvectors.route(url + '<lang:lang>/models/')
def models_page(lang):
    g.lang = lang
    s = set()
    s.add(lang)
    other_lang = list(set(language_dicts.keys()) - s)[0]  # works only for two languages
    g.strings = language_dicts[lang]
    return render_template('%s/about.html' % lang, other_lang=other_lang, languages=languages, url=url)


@wvectors.route(url + '<lang:lang>/about/')
def about_page(lang):
    g.lang = lang
    s = set()
    s.add(lang)
    other_lang = list(set(language_dicts.keys()) - s)[0]  # works only for two languages
    g.strings = language_dicts[lang]

    return render_template('%s/about.html' % lang, other_lang=other_lang, languages=languages, url=url)


# redirecting requests with no lang:
@wvectors.route(url + 'about/', methods=['GET', 'POST'])
@wvectors.route(url + 'calculator/', methods=['GET', 'POST'])
@wvectors.route(url + 'similar/', methods=['GET', 'POST'])
@wvectors.route(url + 'visual/', methods=['GET', 'POST'])
@wvectors.route(url, methods=['GET', 'POST'])
def redirect_main():
    req = request.path.split('/')[-1]
    if len(req) == 0:
        req = '/'
    else:
        if req[-1] != '/':
            req += '/'
    return redirect(url + 'en' + req)
