#!/usr/bin/python2
# coding: utf-8

# This is the main WebVectors code.
# This script defines the behavior of all web pages and queries word2vec service (word2vec_server.py).

import codecs, logging, urllib, hashlib, os, sys

from flask import render_template, Blueprint, redirect, Response
from flask import request, url_for
from flask import current_app
from string import Template
import numpy as np
from lemmatizer import freeling_lemmatizer
from flask import g
import hashlib

from plot import singularplot
from plot import embed
from sparql import getdbpediaimage

import socket  # for sockets

# import strings data from respective module
from strings_reader import language_dicts

root = 'YOUR ROOT DIRECTORY HERE' # Directory where WebVectores resides
postags = set("S A NUM ANUM V ADV SPRO APRO ADVPRO PR CONJ PART INTJ UNKN".split()) # Define the list of valid parts of speech, if we need it.

# Establishing connection to model server
host = 'localhost';
port = 12666;
try:
    remote_ip = socket.gethostbyname(host)
except socket.gaierror:
    # could not resolve
    print 'Hostname could not be resolved. Exiting'
    sys.exit()

synonyms = Blueprint('synonyms', __name__, template_folder='templates')

def serverquery(message):
    # create an INET, STREAMing socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except socket.error:
        print 'Failed to create socket'
        return None

    #Connect to remote server
    s.connect((remote_ip, port))
    #Now receive data
    reply = s.recv(1024)

    #Send some data to remote server
    try:
        s.sendall(message.encode('utf-8'))
    except socket.error:
        #Send failed
        print 'Send failed'
        s.close()
        return None
    #Now receive data
    reply = s.recv(32768)
    s.close()
    return reply


# Loading models list
logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)
our_models = {}
for line in open(root + 'models.csv', 'r').readlines():
    if line.startswith("#"):
        continue
    res = line.strip().split('\t')
    (identifier, description, path, string) = res
    our_models[identifier] = string


def after_this_request(func):
    if not hasattr(g, 'call_after_request'):
        g.call_after_request = []
    g.call_after_request.append(func)
    return func


@synonyms.after_request
def per_request_callbacks(response):
    for func in getattr(g, 'call_after_request', ()):
        response = func(response)
    return response


def process_query(userquery):
    userquery = userquery.strip().replace(u'ё', u'е')
    if "_" in userquery:
        query_split = userquery.split("_")
        if query_split[-1] in postags:
            query = ''.join(query_split[:-1]).lower() + '_' + query_split[-1]
        else:
            return "Incorrect POS!"
    else:
        pos_tag = freeling_lemmatizer(userquery)
        if pos_tag == "A" and userquery.endswith(u'о'):
            pos_tag = "ADV"
        query = userquery.lower() + '_' + pos_tag
    return query


def download_corpus(url, urlhash, algo, vectorsize, windowsize):
    print url
    if url.endswith('/'):
        url = url[:-1]
    fname = urlhash + '__' + algo + '__' + str(vectorsize) + '__' + str(windowsize) + '.gz'
    a = urllib.urlretrieve(url.strip(), root+'/tmp/' + fname)
    x = root+'/tmp/' + fname.split('__')[0]
    open(x, 'a').close()
    return a


# Start defining functions for particular pages...

@synonyms.route('/<lang:lang>/', methods=['GET', 'POST'])
def home(lang):
    # pass all required variables to template
    # repeated within each @synonyms.route function
    g.lang = lang
    g.strings = language_dicts[lang]

    if request.method == 'POST':
        list_data = 'dummy'
        try:
            list_data = request.form['list_query']
        except:
            pass
        if list_data != 'dummy' and list_data.replace('_', '').replace('-', '').isalnum():
            query = process_query(list_data)
            if query == "Incorrect POS!":
                return render_template('home.html', error=query)
            pos_value = request.form.getlist('pos')
            model_value = request.form.getlist('model')
            if len(pos_value) < 1:
                pos = query.split('_')[-1]
            else:
                pos = pos_value[0]
            if len(model_value) < 1:
                model = "ruscorpora"
            else:
                model = model_value[0]
            message = "1;" + query + ";" + 'ALL' + ";" + model
            result = serverquery(message)
            associates_list = []
            if "unknown to the" in result or "No result" in result:
                return render_template('home.html', error=result.decode('utf-8'))
            else:
                output = result.split('&')
                associates = output[0]
                for word in associates.split():
                    w = word.split("#")
                    associates_list.append((w[0].decode('utf-8'), float(w[1])))

                return render_template('home.html', list_value=associates_list, word=query, model=model)
        else:
            error_value = u"Incorrect query!"
            return render_template("home.html", error=error_value)
    return render_template('home.html')


@synonyms.route('/<lang:lang>/upload', methods=['GET', 'POST'])
def upload_page(lang):
    g.lang = lang
    g.strings = language_dicts[lang]

    if request.method == 'POST':
        corpus_url = "dummy"
        try:
            corpus_url = request.form['training_corpus_url']
            vectorsize = request.form['vectorsize']
            algo = request.form['algo']
            windowsize = request.form['windowsize']
        except:
            pass
        if corpus_url != "dummy" and corpus_url.endswith('gz'):
            m = hashlib.md5()
            m.update(corpus_url)
            urlhash = m.hexdigest()

            @after_this_request
            def train(response):
                download_corpus(corpus_url, urlhash, algo, vectorsize, windowsize)
                return response

            return render_template('upload.html', url=corpus_url, hash=urlhash)

    return render_template('upload.html')


@synonyms.route('/<lang:lang>/usermodel/<hash>')
def usermodel_page(lang, hash):
    g.lang = lang
    g.strings = language_dicts[lang]

    modelfilename = hash.strip() + '.model'
    if os.path.isfile(root+'/static/models/' + modelfilename):
        return render_template('usermodel.html', model=modelfilename)
    elif os.path.isfile(root+'/training/' + hash + '.gz.training') or os.path.isfile(
                    root+'/tmp/' + hash):
        return render_template('usermodel.html', queue=hash)

    return render_template('usermodel.html')


@synonyms.route('/<lang:lang>/similar', methods=['GET', 'POST'])
def similar_page(lang):
    g.lang = lang
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
        if input_data != 'dummy':
            if ' ' in input_data.strip():
                input_data = input_data.replace(u'ё', u'е').strip()
                if input_data.endswith(','):
                    input_data = input_data[:-1]
                cleared_data = []
                model_value = request.form.getlist('simmodel')
                if len(model_value) < 1:
                    model = "news"
                else:
                    model = model_value[0]
                if not model.strip() in our_models:
                    return render_template('home.html')
                for query in input_data.split(','):
                    if not ' ' in query.strip():
                        continue
                    query = query.split()
                    words = []
                    for w in query[:2]:
                        if w.replace('_', '').replace('-', '').isalnum():
                            w = process_query(w)
                            if "Incorrect POS!" in w:
                                return render_template('similar.html', value=["Incorrect PoS!"], models=our_models)
                            words.append(w.strip())
                    if len(words) == 2:
                        cleared_data.append(words[0].strip() + " " + words[1].strip())
                if len(cleared_data) == 0:
                    error_value = "Incorrect query!"
                    return render_template("similar.html", error_sim=error_value)
                message = "2;" + ",".join(cleared_data) + ";" + model
                results = []
                result = serverquery(message)
                if 'does not know the word' in result:
                    return render_template("similar.html", error_sim=result.strip())
                for word in result.split():
                    w = word.split("#")
                    results.append((w[0].decode('utf-8'), w[1].decode('utf-8'), float(w[2])))
                return render_template('similar.html', value=results, model=model, query=cleared_data,
                                       models=our_models)
            else:
                error_value = "Incorrect query!"
                return render_template("similar.html", error_sim=error_value, models=our_models)

        if list_data != 'dummy' and list_data.replace('_', '').replace('-', '').isalnum():
            list_data = list_data.split()[0].strip()
            query = process_query(list_data)

            pos_value = request.form.getlist('pos')
            model_value = request.form.getlist('model')
            if len(model_value) < 1:
                model_value = ["news"]
            if len(pos_value) < 1 or pos_value[0] == 'Q':
                pos = query.split('_')[-1]
            else:
                pos = pos_value[0]
            if query == "Incorrect POS!":
                return render_template('similar.html', error=query, word=list_data, models=our_models)

            else:
                models_row = {}
                for model in model_value:
                    if not model.strip() in our_models:
                        return render_template('home.html')
                    message = "1;" + query + ";" + pos + ";" + model
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
                        output = result.split('&')
                        associates = output[0]
                        if len(associates) > 1:
                            vector = output[1:]
                        for word in associates.split():
                            w = word.split("#")
                            associates_list.append((w[0].decode('utf-8'), float(w[1])))
                        models_row[model] = associates_list
                return render_template('similar.html', list_value=models_row, word=query, pos=pos,
                                       number=len(model_value), model=model, models=our_models)
        else:
            error_value = "Incorrect query!"
            return render_template("similar.html", error=error_value, models=our_models)
    return render_template('similar.html', models=our_models)


@synonyms.route('/<lang:lang>/visual', methods=['GET', 'POST'])
def visual_page(lang):
    g.lang = lang
    g.strings = language_dicts[lang]

    if request.method == 'POST':
        list_data = 'dummy'
        try:
            list_data = request.form['list_query']
        except:
            pass
        if list_data != 'dummy':
            querywords = set([process_query(w) for w in list_data.split() if
                              len(w) > 1 and w.replace('_', '').replace('-', '').isalnum()][:20])
            if len(querywords) < 4:
                error_value = "Too few words!"
                return render_template("visual.html", error=error_value, models=our_models)

            model_value = request.form.getlist('model')
            if "Incorrect POS!" in querywords:
                return render_template('visual.html', list_value=[query], word=list_data, model=model,
                                       models=our_models)

            if len(model_value) < 1:
                model_value = ["ruscorpora"]
            unknown = {}
            models_row = {}
            for model in model_value:
                if not model.strip() in our_models:
                    return render_template('home.html')
                print 'Embedding!'
                unknown[model] = set()
                words2vis = querywords
                m = hashlib.md5()
                name = '_'.join(words2vis).encode('ascii', 'backslashreplace')
                m.update(name)
                fname = m.hexdigest()
                plotfile = model + '_' + fname + '.png'
                models_row[model] = plotfile
                labels = []
                if os.access(root + '/static/tsneplots/' + plotfile, os.F_OK) == False:
                    print 'No previous image found'
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
                        plotfile = model + '_' + fname + '.png'
                        models_row[model] = plotfile
                    else:
                        models_row[model] = "Too few words!"

            return render_template('visual.html', visual=models_row, words=querywords, number=len(model_value),
                                   models=our_models, unknown=unknown)
        else:
            error_value = "Incorrect query!"
            return render_template("visual.html", error=error_value, models=our_models)
    return render_template('visual.html', models=our_models)


@synonyms.route('/<lang:lang>/calculator', methods=['GET', 'POST'])
def finder(lang):
    g.lang = lang
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
        if negative_data != '' and positive_data != '' and positive2_data != '':
            negative_data = negative_data.split()[0].split()
            positive_data = positive_data.split()[0]
            positive2_data = positive2_data.split()[0]
            positive_data_list = [positive_data, positive2_data]
            negative_list = [process_query(w) for w in negative_data if
                             len(w) > 1 and w.replace('_', '').replace('-', '').isalnum()]
            positive_list = [process_query(w) for w in positive_data_list if
                             len(w) > 1 and w.replace('_', '').replace('-', '').isalnum()]
            if len(positive_list) < 2 or len(negative_list) == 0:
                error_value = "Incorrect query!"
                return render_template("calculator.html", error=error_value, models=our_models)
            if "Incorrect POS!" in negative_list or "Incorrect POS!" in positive_list:
                return render_template('calculator.html', calc_value=["Incorrect PoS!"], models=our_models)
            calcpos_value = request.form.getlist('calcpos')
            if len(calcpos_value) < 1:
                pos = "S"
            else:
                pos = calcpos_value[0]

            calcmodel_value = request.form.getlist('calcmodel')
            if len(calcmodel_value) < 1:
                calcmodel_value = ["ruscorpora"]
            models_row = {}
            unknown_words = False
            for model in calcmodel_value:
                if not model.strip() in our_models:
                    return render_template('home.html')
                message = "3;" + ",".join(positive_list) + "&" + ','.join(negative_list) + ";" + pos + ";" + model
                result = serverquery(message)
                results = []
                if len(result) == 0 or 'No results' in result:
                    results.append("No similar words of this part of speech.")
                    models_row[model] = results
                    continue
                if "does not know" in result:
                    results.append(result)
                    unknown_words = True
                    models_row[model] = results
                    continue
                for word in result.split():
                    w = word.split("#")
                    results.append((w[0].decode('utf-8'), float(w[1])))
                models_row[model] = results
            return render_template('calculator.html', analogy_value=models_row, pos=pos, plist=positive_list,
                                   nlist=negative_list, models=our_models)

        if positive1_data != '':
            negative_list = [process_query(w) for w in negative1_data.split() if len(w) > 1 and w.replace('_','').replace('-', '').isalnum()][:10]
            positive_list = [process_query(w) for w in positive1_data.split() if len(w) > 1 and w.replace('_','').replace('-', '').isalnum()][:10]
            if len(positive_list) == 0:
                error_value = "Incorrect query!"
                return render_template("calculator.html", error=error_value)
            if "Incorrect POS!" in negative_list or "Incorrect POS!" in positive_list:
                return render_template('calculator.html', calc_value=["Incorrect PoS!"])
            calcpos_value = request.form.getlist('calcpos')
            if len(calcpos_value) < 1:
                pos = "S"
            else:
                pos = calcpos_value[0]
            calcmodel_value = request.form.getlist('calcmodel')
            if len(calcmodel_value) < 1:
                calcmodel_value = ["ruscorpora"]
            models_row = {}
            for model in calcmodel_value:
                if not model.strip() in our_models:
                    return render_template('home.html')
                message = "3;"+",".join(positive_list)+"&"+','.join(negative_list)+";"+pos+";"+model
                result = serverquery(message)
                results = []
                if len(result) == 0:
                    results.append("No similar words of this part of speech.")
                    models_row[model] = results
                    continue
                if "does not know" in result:
                    results.append(result)
                    unknown_words = True
                    models_row[model] = results
                    continue
                for word in result.split():
                    w = word.split("#")
                    results.append((w[0].decode('utf-8'),float(w[1])))
                models_row[model] = results
            return render_template('calculator.html', calc_value=models_row, pos=pos, plist2 = positive_list,
                                   nlist2 = negative_list, models=our_models)

        else:
            error_value = "Incorrect query!"
            return render_template("calculator.html", calc_error=error_value, models=our_models)
    return render_template("calculator.html", models=our_models)


@synonyms.route('/<lang:lang>/<model>/<userquery>/', methods=['GET', 'POST'])
def raw_finder(lang, model, userquery):
    g.lang = lang
    g.strings = language_dicts[lang]

    model = model.strip()
    if not model.strip() in our_models:
        return render_template('home.html')
    if userquery.strip().replace('_', '').replace('-', '').isalnum():
        query = process_query(userquery.strip())
        if len(query.split('_')) < 2:
            return render_template('synonyms_raw.html', error=query)
        pos_tag = query.split('_')[-1]
        message = "1;" + query + ";" + pos_tag + ";" + model
        result = serverquery(message)
        associates_list = []
        if "unknown to the" in result or "No results" in result:
            return render_template('synonyms_raw.html', error=result.decode('utf-8'))
        else:
            output = result.split('&')
            associates = output[0]
            if len(associates) > 1:
                vector = ','.join(output[1:])
            for word in associates.split():
                w = word.split("#")
                associates_list.append((w[0].decode('utf-8'), float(w[1])))
            m = hashlib.md5()
            name = query.encode('ascii', 'backslashreplace')
            m.update(name)
            fname = m.hexdigest()
            plotfile = root + 'static/singleplots/' + model + '_' + fname + '.png'
            if os.access(plotfile, os.F_OK) == False:
                vector2 = output[1].split(',')
                vector2 = [float(a) for a in vector2]
                singularplot(query, model, vector2)
            image = getdbpediaimage(query.split('_')[0].encode('utf-8'))
            return render_template('synonyms_raw.html', list_value=associates_list, word=query, model=model,
                                   pos=pos_tag, vector=vector, image=image, vectorvis=fname)
    else:
        error_value = u'Incorrect query: %s' % userquery
        return render_template("synonyms_raw.html", error=error_value)

    return render_template("synonyms_raw.html")


@synonyms.route('/<model>/<word>/api', methods=['GET'])
def api(model, word):
    model = model.strip()

    def generate(word, model):
        if not word.strip().replace('_', '').replace('-', '').isalnum():
            yield query.strip() + '\t' + model.strip() + '\t' + 'Word error!'
        else:
            query = process_query(word.strip())
        if len(query.split('_')) < 2 or not model.strip() in our_models:
            yield query.strip() + '\t' + model.strip() + '\t' + 'Error!'
        else:
            if not model.strip() in our_models:
                yield query.strip() + '\t' + model.strip() + '\t' + 'Model error!'
            else:
                #pos_tag = query.split('_')[-1]
                message = "1;" + query + ";" + 'ALL' + ";" + model
                result = serverquery(message)
                associates_list = []
                if "unknown to the" in result or "No results" in result:
                    yield query + '\t' + result.decode('utf-8')
                else:
                    output = result.split('&')
                    associates = output[0]
                    if len(associates) > 1:
                        vector = ','.join(output[1:])
                    for word in associates.split():
                        w = word.split("#")
                        associates_list.append((w[0].decode('utf-8'), float(w[1])))
                    yield model + '\n'
                    yield query + '\n'
                    for associate in associates_list:
                        yield associate[0] + '\t' + str(associate[1]) + '\n'

    return Response(generate(word, model), mimetype='text/csv',
                    headers={"Content-Disposition": "attachment;filename=%s.csv" % word.encode('utf-8')})


@synonyms.route('/<lang:lang>/publications')
def publications_page(lang):
    g.lang = lang
    g.strings = language_dicts[lang]

    return render_template('%s/about.html' % lang)


@synonyms.route('/<lang:lang>/contacts')
def contacts_page(lang):
    g.lang = lang
    g.strings = language_dicts[lang]

    return render_template('%s/contacts.html' % lang)


@synonyms.route('/<lang:lang>/models')
def models_page(lang):
    g.lang = lang
    g.strings = language_dicts[lang]

    return render_template('%s/about.html' % lang)


@synonyms.route('/<lang:lang>/about')
def about_page(lang):
    g.lang = lang
    g.strings = language_dicts[lang]

    return render_template('%s/about.html' % lang)

# redirecting requests with no language:
@synonyms.route('/about', methods=['GET', 'POST'])
@synonyms.route('/calculator', methods=['GET', 'POST'])
@synonyms.route('/similar', methods=['GET', 'POST'])
@synonyms.route('/visual', methods=['GET', 'POST'])
@synonyms.route('/models', methods=['GET', 'POST'])
@synonyms.route('/upload', methods=['GET', 'POST'])
@synonyms.route('/publications', methods=['GET', 'POST'])
@synonyms.route('/contacts', methods=['GET', 'POST'])
@synonyms.route('/', methods=['GET', 'POST'])
def redirect_main():
    return redirect(request.script_root + '/en' + request.path)

@synonyms.route('/usermodel/<hash>', methods=['GET', 'POST'])
def redirect_usermodel(hash):
    return redirect(request.script_root + '/en' + request.path)
