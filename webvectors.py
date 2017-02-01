#!/usr/bin/python
# coding: utf-8

import logging
import hashlib
import os
import codecs
import sys
import json
from flask import render_template, Blueprint, redirect, Response
from flask import request
import numpy as np

from flask import g
from collections import OrderedDict

from plotting import singularplot
from plotting import embed
from sparql import getdbpediaimage
from timeout import timeout

import socket  # for sockets

import ConfigParser

# import strings data from respective module
from strings_reader import language_dicts

languages = '/'.join(language_dicts.keys()).upper()

config = ConfigParser.RawConfigParser()
config.read('webvectors.cfg')

root = config.get('Files and directories', 'root')
modelsfile = config.get('Files and directories', 'models')
cachefile = config.get('Files and directories', 'image_cache')
temp = config.get('Files and directories', 'temp')
tags = config.getboolean('Tags', 'use_tags')

url = config.get('Other', 'url')

lemmatize = config.getboolean('Other', 'lemmatize')
dbpedia = config.getboolean('Other', 'dbpedia_images')
languages_list = config.get('Languages', 'interface_languages').split(',')

if lemmatize:
    from lemmatizer import tagword

# Establishing connection to model server
host = config.get('Sockets', 'host')
port = config.getint('Sockets', 'port')
try:
    remote_ip = socket.gethostbyname(host)
except socket.gaierror:
    # could not resolve
    print >> sys.stderr, 'Hostname could not be resolved. Exiting'
    sys.exit()


def serverquery(message):
    # create an INET, STREAMing socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except socket.error:
        print >> sys.stderr, 'Failed to create socket'
        return None

    # Connect to remote server
    s.connect((remote_ip, port))
    # Now receive initial data
    initial_reply = s.recv(1024)

    # Send some data to remote server
    try:
        s.sendall(message.encode('utf-8'))
    except socket.error:
        # Send failed
        print >> sys.stderr, 'Send failed'
        s.close()
        return None
    # Now receive data
    reply = s.recv(32768)
    s.close()
    return reply


taglist = set(config.get('Tags', 'tags_list').split())
defaulttag = config.get('Tags', 'default_tag')

our_models = {}
for line in open(root + modelsfile, 'r').readlines():
    if line.startswith("#"):
        continue
    res = line.strip().split('\t')
    (identifier, description, path, string, default) = res
    if default == 'True':
        defaultmodel = identifier
    our_models[identifier] = string

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
                query = userquery + '_' + pos_tag
            else:
                return 'Incorrect tag!'
    else:
        query = userquery
    return query


@timeout(3)
def get_images(images):
    imagecache = {}
    imagedata = codecs.open(root + cachefile, 'r', 'utf-8')
    for line in imagedata:
        res = line.strip().split('\t')
        if len(res) == 2:
            (word, image) = res
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
        if list_data != 'dummy' and list_data.replace('_', '').replace('-', '').replace('::', '').isalnum():
            query = process_query(list_data)
            if query == "Incorrect tag!":
                return render_template('home.html', error=query, other_lang=other_lang, languages=languages, url=url)
            model_value = request.form.getlist('model')
            if len(model_value) < 1:
                model = defaultmodel
            else:
                model = model_value[0]
            images = {query.split('_')[0]: None}
            message = "1;" + query + ";" + 'ALL' + ";" + model
            result = serverquery(message)
            associates_list = []
            if "unknown to the" in result or "No result" in result:
                return render_template('home.html', error=result.decode('utf-8'), other_lang=other_lang,
                                       languages=languages, url=url)
            else:
                output = result.split('&&&')
                associates = output[0]
                for word in associates.split():
                    w = word.split("#")
                    associates_list.append((w[0].decode('utf-8'), float(w[-1])))
                    images[w[0].split('_')[0].decode('utf-8')] = None
                try:
                    images = get_images(images)
                except:
                    pass
                return render_template('home.html', list_value=associates_list, word=query, wordimages=images,
                                       model=model, tags=tags, other_lang=other_lang, languages=languages, url=url)
        else:
            error_value = u"Incorrect query!"
            return render_template("home.html", error=error_value, tags=tags, other_lang=other_lang,
                                   languages=languages, url=url)
    return render_template('home.html', tags=tags, other_lang=other_lang, languages=languages, url=url)


@wvectors.route(url + '<lang:lang>/similar', methods=['GET', 'POST'])
def similar_page(lang):
    g.lang = lang
    s = set()
    s.add(lang)
    other_lang = list(set(language_dicts.keys()) - s)[0]  # works only for two languages
    g.strings = language_dicts[lang]

    if request.method == 'POST':
        input_data = 'dummy'
        list_data = 'dummy'
        try:
            input_data = request.form['query']
        except:
            pass
        try:
            list_data = request.form['list_query']
        except:
            pass
        # Similarity queries
        if input_data != 'dummy':
            if ' ' in input_data.strip():
                input_data = input_data.strip()
                if input_data.endswith(','):
                    input_data = input_data[:-1]
                cleared_data = []
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
                                return render_template('similar.html', value=["Incorrect tag!"], models=our_models,
                                                       other_lang=other_lang, languages=languages, url=url,
                                                       usermodels=model_value)
                            words.append(w.strip())
                    if len(words) == 2:
                        cleared_data.append(words[0].strip() + " " + words[1].strip())
                if len(cleared_data) == 0:
                    error_value = "Incorrect query!"
                    return render_template("similar.html", error_sim=error_value, other_lang=other_lang,
                                           languages=languages, url=url, usermodels=model_value)
                message = "2;" + ",".join(cleared_data) + ";" + model
                results = []
                result = serverquery(message)
                if 'does not know the word' in result:
                    return render_template("similar.html", error_sim=result.strip(), other_lang=other_lang,
                                           languages=languages, models=our_models,
                                           tags=tags, query=cleared_data, url=url, usermodels=model_value)
                for word in result.split():
                    w = word.split("#")
                    results.append((w[0].decode('utf-8'), w[1].decode('utf-8'), float(w[-1])))
                return render_template('similar.html', value=results, model=model, query=cleared_data,
                                       models=our_models, tags=tags, other_lang=other_lang,
                                       languages=languages, url=url, usermodels=model_value)
            else:
                error_value = "Incorrect query!"
                return render_template("similar.html", error_sim=error_value, models=our_models, tags=tags,
                                       other_lang=other_lang, languages=languages, url=url, usermodels=[defaultmodel])

        # Nearest associates queries
        if list_data != 'dummy' and list_data.replace('_', '').replace('-', '').replace('::', '').isalnum():
            list_data = list_data.split()[0].strip()
            query = process_query(list_data)

            model_value = request.form.getlist('model')
            if len(model_value) < 1:
                model_value = [defaultmodel]

            if query == "Incorrect tag!":
                return render_template('similar.html', error=query, word=list_data, models=our_models,
                                       other_lang=other_lang, languages=languages, url=url, usermodels=model_value)
            if tags:
                pos_value = request.form.getlist('pos')
                if len(pos_value) < 1 or pos_value[0] == 'Q':
                    pos = query.split('_')[-1]
                else:
                    pos = pos_value[0]
            else:
                pos = 'All PoS'

            images = {query.split('_')[0]: None}
            models_row = {}
            for model in model_value:
                if not model.strip() in our_models:
                    return render_template('home.html', other_lang=other_lang, languages=languages, url=url,
                                           usermodels=model_value)
                if tags:
                    message = "1;" + query + ";" + pos + ";" + model
                else:
                    message = "1;" + query + ";" + 'ALL' + ";" + model
                result = serverquery(message)
                associates_list = []
                if "unknown to the" in result:
                    models_row[model] = "Unknown!"
                    continue
                elif "No results" in result:
                    associates_list.append(result)
                    models_row[model] = associates_list
                    continue
                else:
                    output = result.split('&&&')
                    associates = output[0]
                    for word in associates.split():
                        w = word.split("#")
                        associates_list.append((w[0].decode('utf-8'), float(w[1])))
                        images[w[0].split('_')[0].decode('utf-8')] = None
                    models_row[model] = associates_list
                    try:
                        images = get_images(images)
                    except:
                        pass
            return render_template('similar.html', list_value=models_row, word=query, pos=pos,
                                   number=len(model_value), wordimages=images, models=our_models, tags=tags,
                                   other_lang=other_lang, languages=languages,
                                   url=url, usermodels=model_value)
        else:
            error_value = "Incorrect query!"
            return render_template("similar.html", error=error_value, models=our_models, tags=tags, url=url,
                                   usermodels=[defaultmodel])
    return render_template('similar.html', models=our_models, tags=tags, other_lang=other_lang,
                           languages=languages, url=url, usermodels=[defaultmodel])


@wvectors.route(url + '<lang:lang>/visual', methods=['GET', 'POST'])
def visual_page(lang):
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
        if list_data != 'dummy':

            model_value = request.form.getlist('model')
            if len(model_value) < 1:
                model_value = [defaultmodel]

            querywords = set([process_query(w) for w in list_data.split() if
                              len(w) > 1 and w.replace('_', '').replace('-', '').replace('::', '').isalnum()][:30])
            if len(querywords) < 7:
                error_value = "Too few words!"
                return render_template("visual.html", error=error_value, models=our_models, other_lang=other_lang,
                                       languages=languages, url=url, usermodels=model_value)

            if "Incorrect tag!" in querywords:
                return render_template('visual.html', word=list_data, models=our_models, other_lang=other_lang,
                                       languages=languages, url=url, usermodels=model_value)

            unknown = {}
            models_row = {}
            for model in model_value:
                if not model.strip() in our_models:
                    return render_template('home.html', other_lang=other_lang, languages=languages, url=url,
                                           usermodels=model_value)
                unknown[model] = set()
                words2vis = querywords
                m = hashlib.md5()
                name = '_'.join(words2vis).encode('ascii', 'backslashreplace')
                m.update(name)
                fname = m.hexdigest()
                plotfile = "%s_%s.png" % (model, fname)
                models_row[model] = plotfile
                labels = []
                if not os.path.exists(root + 'data/images/tsneplots'):
                    os.makedirs(root + 'data/images/tsneplots')
                if not os.access(root + 'data/images/tsneplots/' + plotfile, os.F_OK):
                    print >> sys.stderr, 'No previous image found'
                    vectors = []
                    for w in words2vis:
                        message = "4;" + w + ";" + model
                        result = serverquery(message)
                        if 'is unknown' in result:
                            unknown[model].add(w)
                            continue
                        vector = np.array(result.split(','))
                        vectors.append(vector)
                        labels.append(w)
                    if len(vectors) > 1:
                        matrix2vis = np.vstack(([v for v in vectors]))
                        embed(labels, matrix2vis.astype('float64'), model)
                        m = hashlib.md5()
                        name = '_'.join(labels).encode('ascii', 'backslashreplace')
                        m.update(name)
                        fname = m.hexdigest()
                        plotfile = "%s_%s.png" % (model, fname)
                        models_row[model] = plotfile
                    else:
                        models_row[model] = "Too few words!"

            return render_template('visual.html', visual=models_row, words=querywords, number=len(model_value),
                                   models=our_models, unknown=unknown, url=url, usermodels=model_value)
        else:
            error_value = "Incorrect query!"
            return render_template("visual.html", error=error_value, models=our_models, other_lang=other_lang,
                                   languages=languages, url=url, usermodels=[defaultmodel])
    return render_template('visual.html', models=our_models, other_lang=other_lang, languages=languages,
                           url=url, usermodels=[defaultmodel])


@wvectors.route(url + '<lang:lang>/calculator', methods=['GET', 'POST'])
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
            negative_data = negative_data.split()[0].split()
            positive_data = positive_data.split()[0]
            positive2_data = positive2_data.split()[0]
            positive_data_list = [positive_data, positive2_data]
            negative_list = [process_query(w) for w in negative_data if
                             len(w) > 1 and w.replace('_', '').replace('-', '').replace('::', '').isalnum()]
            positive_list = [process_query(w) for w in positive_data_list if
                             len(w) > 1 and w.replace('_', '').replace('-', '').replace('::', '').isalnum()]

            calcmodel_value = request.form.getlist('calcmodel')
            if len(calcmodel_value) < 1:
                calcmodel_value = [defaultmodel]

            if len(positive_list) < 2 or len(negative_list) == 0:
                error_value = "Incorrect query!"
                return render_template("calculator.html", error=error_value, models=our_models, other_lang=other_lang,
                                       languages=languages, url=url, usermodels=calcmodel_value)
            if "Incorrect tag!" in negative_list or "Incorrect tag!" in positive_list:
                return render_template('calculator.html', calc_value=["Incorrect tag!"], models=our_models,
                                       other_lang=other_lang, languages=languages, url=url, usermodels=calcmodel_value)
            if tags:
                calcpos_value = request.form.getlist('calcpos')
                if len(calcpos_value) < 1:
                    pos = defaulttag
                else:
                    pos = calcpos_value[0]
            else:
                pos = 'All PoS'

            models_row = {}
            images = {}
            for model in calcmodel_value:
                if not model.strip() in our_models:
                    return render_template('home.html', other_lang=other_lang, languages=languages,
                                           models=our_models, url=url, usermodels=calcmodel_value)
                if tags:
                    message = "3;" + ",".join(positive_list) + "&" + ','.join(negative_list) + ";" + pos + ";" + model
                else:
                    message = "3;" + ",".join(positive_list) + "&" + ','.join(negative_list) + ";" + 'ALL' + ";" + model
                result = serverquery(message)
                results = []
                if len(result) == 0 or 'No results' in result:
                    results.append("No similar words with this tag.")
                    models_row[model] = results
                    continue
                if "does not know" in result:
                    results.append(result)
                    models_row[model] = results
                    continue
                for word in result.split():
                    w = word.split("#")
                    results.append((w[0].decode('utf-8'), float(w[1])))
                    images[w[0].split('_')[0].decode('utf-8')] = None
                models_row[model] = results
                try:
                    images = get_images(images)
                except:
                    pass
            return render_template('calculator.html', analogy_value=models_row, pos=pos, plist=positive_list,
                                   nlist=negative_list, wordimages=images, models=our_models, tags=tags,
                                   other_lang=other_lang, languages=languages, url=url, usermodels=calcmodel_value)

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
                return render_template("calculator.html", error=error_value, other_lang=other_lang,
                                       languages=languages, models=our_models, url=url, usermodels=calcmodel_value)
            if "Incorrect tag!" in negative_list or "Incorrect tag!" in positive_list:
                return render_template('calculator.html', calc_value=["Incorrect tag!"], other_lang=other_lang,
                                       languages=languages, models=our_models, url=url, usermodels=calcmodel_value)
            if tags:
                calcpos_value = request.form.getlist('calcpos')
                if len(calcpos_value) < 1:
                    pos = defaulttag
                else:
                    pos = calcpos_value[0]
            else:
                pos = 'ALL'

            models_row = {}
            images = {}
            for model in calcmodel_value:
                if not model.strip() in our_models:
                    return render_template('home.html', other_lang=other_lang, languages=languages,
                                           models=our_models, url=url, usermodels=calcmodel_value)
                message = "3;" + ",".join(positive_list) + "&" + ','.join(negative_list) + ";" + pos + ";" + model
                result = serverquery(message)
                results = []
                if len(result) == 0:
                    results.append("No similar words with this tag.")
                    models_row[model] = results
                    continue
                if "does not know" in result:
                    results.append(result)
                    models_row[model] = results
                    continue
                for word in result.split():
                    w = word.split("#")
                    results.append((w[0].decode('utf-8'), float(w[1])))
                    images[w[0].split('_')[0].decode('utf-8')] = None
                models_row[model] = results
                try:
                    images = get_images(images)
                except:
                    pass
            return render_template('calculator.html', calc_value=models_row, pos=pos, plist2=positive_list,
                                   nlist2=negative_list, wordimages=images, models=our_models, tags=tags,
                                   other_lang=other_lang, languages=languages, url=url, usermodels=calcmodel_value)

        else:
            error_value = "Incorrect query!"
            return render_template("calculator.html", calc_error=error_value, models=our_models, tags=tags,
                                   other_lang=other_lang, languages=languages, url=url, usermodels=[defaultmodel])
    return render_template("calculator.html", models=our_models, tags=tags, other_lang=other_lang,
                           languages=languages, url=url, usermodels=[defaultmodel])


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
                return render_template('wordpage.html', error=query, other_lang=other_lang,
                                       languages=languages, url=url)
            pos_tag = query.split('_')[-1]
        else:
            pos_tag = 'ALL'
        message = "1;" + query + ";" + pos_tag + ";" + model
        result = serverquery(message)
        associates_list = []
        if "unknown to the" in result or "No results" in result:
            return render_template('wordpage.html', error=result.decode('utf-8'), other_lang=other_lang,
                                   languages=languages, url=url)
        else:
            output = result.split('&&&')
            associates = output[0]
            if len(associates) > 1:
                vector = ','.join(output[1:])
            else:
                vector = ''
            for word in associates.split():
                w = word.split("#")
                associates_list.append((w[0].decode('utf-8'), float(w[1])))
            m = hashlib.md5()
            name = query.encode('ascii', 'backslashreplace')
            m.update(name)
            fname = m.hexdigest()
            plotfile = root + 'data/images/singleplots/' + model + '_' + fname + '.png'
            if not os.access(plotfile, os.F_OK):
                vector2 = output[1].split(',')
                vector2 = [float(a) for a in vector2]
                singularplot(query, model, vector2)
            if dbpedia:
                imagecache = {}
                imagedata = codecs.open(root + cachefile, 'r', 'utf-8')
                for line in imagedata:
                    res = line.strip().split('\t')
                    if len(res) == 2:
                        (word, image) = res
                        image = image.strip()
                        if image == 'None':
                            image = None
                        imagecache[word.strip()] = image
                    else:
                        continue
                imagedata.close()
                image = getdbpediaimage(query.split('_')[0].encode('utf-8'), imagecache)
            else:
                image = None
            return render_template('wordpage.html', list_value=associates_list, word=query, model=model,
                                   pos=pos_tag, vector=vector, image=image, vectorvis=fname, tags=tags,
                                   other_lang=other_lang, languages=languages, url=url)
    else:
        error_value = u'Incorrect query: %s' % userquery
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
            message = "1;" + query + ";" + 'ALL' + ";" + model
            result = serverquery(message)
            associates_list = []

            # handle cases when the server returned that the word is unknown to the model,
            # or for some other reason the associates list is empty
            if "unknown to the" in result or "No results" in result:
                yield query + '\t' + result.decode('utf-8')
            else:
                output = result.split('&&&')
                associates = output[0]

                # take the associates and their similarity measures
                for word in associates.split():
                    w = word.split("#")
                    associates_list.append((w[0].decode('utf-8'), float(w[1])))

                # return result in csv
                if api_format == 'csv':
                    yield model + '\n'
                    yield query + '\n'
                    for associate in associates_list:
                        yield "%s\t%s\n" % (associate[0], str(associate[1]))

                # return result in json
                elif api_format == 'json':
                    associates = OrderedDict()
                    for associate in associates_list:
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
    cleanword0 = ''.join([char for char in wordpair[0] if char.isalnum() or char == '_' or char == '::'])
    cleanword1 = ''.join([char for char in wordpair[1] if char.isalnum() or char == '_' or char == '::'])
    cleanword0 = process_query(cleanword0)
    cleanword1 = process_query(cleanword1)
    message = "2;" + " ".join([cleanword0, cleanword1]) + ";" + model

    result = serverquery(message)
    if 'does not know the word' in result:
        return 'Unknown'
    w = result.split("#")
    return str(w[2]) + '\t' + cleanword0 + '\t' + cleanword1 + '\t' + model


@wvectors.route(url + '<lang:lang>/models')
def models_page(lang):
    g.lang = lang
    s = set()
    s.add(lang)
    other_lang = list(set(language_dicts.keys()) - s)[0]  # works only for two languages
    g.strings = language_dicts[lang]
    return render_template('%s/about.html' % lang, other_lang=other_lang, languages=languages, url=url)


@wvectors.route(url + '<lang:lang>/about')
def about_page(lang):
    g.lang = lang
    s = set()
    s.add(lang)
    other_lang = list(set(language_dicts.keys()) - s)[0]  # works only for two languages
    g.strings = language_dicts[lang]

    return render_template('%s/about.html' % lang, other_lang=other_lang, languages=languages, url=url)


# redirecting requests with no lang:
@wvectors.route(url + 'about', methods=['GET', 'POST'])
@wvectors.route(url + 'calculator', methods=['GET', 'POST'])
@wvectors.route(url + 'similar', methods=['GET', 'POST'])
@wvectors.route(url + 'visual', methods=['GET', 'POST'])
@wvectors.route(url, methods=['GET', 'POST'])
def redirect_main():
    return redirect(url + 'en' + request.path.split('/')[-1])
