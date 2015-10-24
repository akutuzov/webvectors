#!/usr/local/python/bin/python
# coding: utf-8

# test comment
import codecs, logging, urllib, hashlib, os, sys

from flask import render_template, Blueprint, redirect
from flask import request, url_for
from flask import current_app
from string import Template

from lemmatizer import freeling_lemmatizer
from flask import g

#from plot import singularplot

import socket #for sockets

# import strings data from respective module
from strings_reader import language_dicts

# Establishing connection to model server
host = 'localhost';
port = 12666;
try:
    remote_ip = socket.gethostbyname( host )
except socket.gaierror:
    #could not resolve
    print 'Hostname could not be resolved. Exiting'
    sys.exit()

def serverquery(message):
    #create an INET, STREAMing socket
    try:
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except socket.error:
	print 'Failed to create socket'
	return None

    #Connect to remote server
    s.connect((remote_ip , port))
    #Now receive data
    reply = s.recv(1024)

    #Send some data to remote server
    try :
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


postags = set("S A NUM A-NUM V ADV PRAEDIC PARENTH S-PRO A-PRO ADV-PRO PRAEDIC-PRO PR CONJ PART INTJ UNKN".split())

our_models = set("news ruscorpora ruwikiruscorpora web".split())

logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)


synonyms = Blueprint('synonyms', __name__, template_folder='templates')

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
	    if userquery.split("_")[-1] in postags:
		query = userquery
		if userquery[0].isupper():
		    query = userquery[0].lower()+userquery[1:]
	    else:
		return "Incorrect PoS!"
	else:
	    pos_tag = freeling_lemmatizer(userquery)
	    if pos_tag == "A" and userquery.endswith(u'о'):
		pos_tag = "ADV"
	    query = userquery.lower()+'_'+pos_tag
	return query

def download_corpus(url,urlhash,algo,vectorsize,windowsize):
    print url
    if url.endswith('/'):
	url = url[:-1]
    fname = urlhash+'__'+algo+'__'+str(vectorsize)+'__'+str(windowsize)+'.gz'
    a = urllib.urlretrieve(url.strip(),'/home/sites/ling.go.mail.ru/tmp/'+fname)
    x = '/home/sites/ling.go.mail.ru/tmp/'+fname.split('__')[0]
    open(x, 'a').close()
    return a

# @synonyms.route('/',methods=['GET', 'POST'])
# def home_nolang():
#     lang="en"
#     g.lang=lang
#     g.strings=language_dicts[lang]
#     return render_template('home.html')

@synonyms.route('/<lang:lang>/',methods=['GET', 'POST'])
def home(lang):

    # pass all required variables to template
    # repeated within each @synonyms.route function
    g.lang=lang
    g.strings=language_dicts[lang]

    if request.method == 'POST':
        list_data = 'dummy'
        try:
            list_data = request.form['list_query']
        except:
            pass
        if list_data != 'dummy' and list_data.replace('_','').isalnum():
	    query = process_query(list_data)
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
            message = "1;"+query+";"+pos+";"+model
            result = serverquery(message)
            associates_list = []
            if "unknown to the" in result:
        	return render_template('home.html', error = result.decode('utf-8'))
            else:
		output = result.split('&')
        	associates = output[0]
                vector = output[1]
		for word in associates.split():
		    w = word.split("#")
                    associates_list.append((w[0].decode('utf-8'),float(w[1])))

        	return render_template('home.html', list_value=associates_list, word=query, model=model)
        else:
            error_value = u"Incorrect query!"
            return render_template("home.html", error=error_value)
    return render_template('home.html')

@synonyms.route('/<lang:lang>/upload',methods=['GET', 'POST'])
def upload_page(lang):

    g.lang=lang
    g.strings=language_dicts[lang]

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
		download_corpus(corpus_url,urlhash,algo,vectorsize,windowsize)
        	return response
	    return render_template('upload.html',url = corpus_url, hash = urlhash)
	
    return render_template('upload.html')


@synonyms.route('/<lang:lang>/usermodel/<hash>')
def usermodel_page(lang, hash):

    g.lang=lang
    g.strings=language_dicts[lang]

    modelfilename = hash.strip()+'.model'
    if os.path.isfile('/home/sites/ling.go.mail.ru/static/models/'+modelfilename):
	return render_template('usermodel.html',model = modelfilename)
    elif os.path.isfile('/home/sites/ling.go.mail.ru/training/'+hash+'.gz.training') or os.path.isfile('/home/sites/ling.go.mail.ru/tmp/'+hash):
	return render_template('usermodel.html',queue = hash)
	
    return render_template('usermodel.html')

@synonyms.route('/<lang:lang>/publications')
def publications_page(lang):

    g.lang=lang
    g.strings=language_dicts[lang]

    return render_template('%s/publications.html' % lang)

@synonyms.route('/<lang:lang>/contacts')
def contacts_page(lang):

    g.lang=lang
    g.strings=language_dicts[lang]

    return render_template('%s/contacts.html' % lang)

@synonyms.route('/<lang:lang>/models')
def models_page(lang):

    g.lang=lang
    g.strings=language_dicts[lang]

    return render_template('%s/models.html' % lang)

@synonyms.route('/<lang:lang>/about')
def about_page(lang):

    g.lang=lang
    g.strings=language_dicts[lang]
    
    return render_template('%s/about.html' % lang)

@synonyms.route('/<lang:lang>/similar',methods=['GET', 'POST'])
def similar_page(lang):

    g.lang=lang
    g.strings=language_dicts[lang]
    
    if request.method == 'POST':
        list_data = 'dummy'
        try:
            list_data = request.form['list_query']
        except:
            pass
        if list_data != 'dummy' and list_data.replace('_','').isalnum():
            list_data = list_data.split()[0].strip()
            query = process_query(list_data)
            
            pos_value = request.form.getlist('pos')
            model_value = request.form.getlist('model')
            if len(pos_value) < 1:
                pos = query.split('_')[-1]
            else:
                pos = pos_value[0]
            if query == "Incorrect PoS!":
		return render_template('similar.html', list_value=[query], word = list_data,model=model)
            
            if len(model_value) < 1:
                model = "news"
            else:
            #    model = model_value[0]
        	models_row = {}
		for model in model_value:
		    if not model.strip() in our_models:
			return render_template('home.html')
        	    
        	    message = "1;"+query+";"+pos+";"+model
        	    result = serverquery(message)
        	    associates_list = []
        	    if "unknown to the" in result or "No results" in result:
        		return render_template('similar.html', error = result.decode('utf-8'))
        	    else:
			output = result.split('&')
        		associates = output[0]
			if len(associates) > 1:
			    vector = output[1:]
			for word in associates.split():
			    w = word.split("#")
                	    associates_list.append((w[0].decode('utf-8'),float(w[1])))
            		models_row[model] = associates_list
		return render_template('similar.html', list_value=models_row, word=query,pos=pos,number=len(model_value))
        else:
            error_value = "Incorrect query!"
            return render_template("similar.html", error=error_value)
    return render_template('similar.html')

@synonyms.route('/<lang:lang>/calculator', methods=['GET', 'POST'])
def finder(lang):

    g.lang=lang
    g.strings=language_dicts[lang]
    
    if request.method == 'POST':
        input_data = 'dummy'
        positive_data = 'dummy'
        negative_data = 'dummy'
        try:
            input_data = request.form['query']
        except:
            pass
        try:
            positive_data = request.form['positive']
            negative_data = request.form['negative']
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
			if w.replace('_','').isalnum():
			    w = process_query(w)
			    if "Incorrect PoS!" in w:
				return render_template('calculator.html', value=["Incorrect PoS!"])
        		    words.append(w.strip())
                    if len(words) == 2:
                	cleared_data.append(words[0].strip()+" "+words[1].strip())
                if len(cleared_data) == 0:
		    error_value = "Incorrect query!"
		    return render_template("calculator.html", error_sim=error_value)
                message = "2;"+",".join(cleared_data)+";"+model
                results = []
                result = serverquery(message)
                if 'does not know the word' in result:
		    return render_template("calculator.html", error_sim=result.strip())
                for word in result.split():
		    w = word.split("#")
                    results.append((w[0].decode('utf-8'),w[1].decode('utf-8'),float(w[2])))
                return render_template('calculator.html', value=results, model=model, query = cleared_data)
            else:
		error_value = "Incorrect query!"
		return render_template("calculator.html", error_sim=error_value)
            
        if negative_data != 'dummy' and positive_data != 'dummy':
	    negative_list = [process_query(w) for w in negative_data.split() if len(w) > 1 and w.replace('_','').isalnum()][:10]
	    positive_list = [process_query(w) for w in positive_data.split() if len(w) > 1 and w.replace('_','').isalnum()][:10]
            if len(positive_list) == 0:
		error_value = "Incorrect query!"
		return render_template("calculator.html", error=error_value)
            if "Incorrect PoS!" in negative_list or "Incorrect PoS!" in positive_list:
		return render_template('calculator.html', calc_value=["Incorrect PoS!"])
            calcpos_value = request.form.getlist('calcpos')
            if len(calcpos_value) < 1:
                pos = "S"
            else:
                pos = calcpos_value[0]

            calcmodel_value = request.form.getlist('calcmodel')
            if len(calcmodel_value) < 1:
                model = "ruscorpora"
            else:
                #model = calcmodel_value[0]
		models_row = {}
		for model in calcmodel_value:
		    if not model.strip() in our_models:
			return render_template('home.html')
        	    message = "3;"+",".join(positive_list)+"&"+','.join(negative_list)+";"+pos+";"+model
        	    result = serverquery(message)
        	    results = []
        	    if len(result) == 0:
        		results.append("No similar words of this part of speech.")
        		return render_template('calculator.html', calc_value=results, pos=pos, model=model, plist = positive_list, nlist = negative_list)
        	    if "does not know" in result:
        		results.append(result)
        		return render_template('calculator.html', calc_value=results, pos=pos, model=model, plist = positive_list, nlist = negative_list)
        	    for word in result.split():
        		w = word.split("#")
        		results.append((w[0].decode('utf-8'),float(w[1])))
        	    models_row[model] = results
            return render_template('calculator.html', calc_value=models_row, pos=pos, plist = positive_list, nlist = negative_list)
        else:
            error_value = "Incorrect query!"
            return render_template("calculator.html", error=error_value)
    return render_template("calculator.html")

@synonyms.route('/<lang:lang>/<model>/<userquery>/', methods=['GET', 'POST'])
def raw_finder(lang, model, userquery):

    g.lang=lang
    g.strings=language_dicts[lang]

    model = model.strip()
    if not model.strip() in our_models:
	return render_template('home.html')
    if userquery.strip().replace('_','').isalnum():
        query = process_query(userquery.strip())
        pos_tag = query.split('_')[-1]
        
        message = "1;"+query+";"+pos_tag+";"+model
        result = serverquery(message)
        associates_list = []
        if "unknown to the" in result or "No results" in result:
        	return render_template('synonyms_raw.html', error = result.decode('utf-8'))
        else:
		output = result.split('&')
        	associates = output[0]
		if len(associates) > 1:
		    vector = ','.join(output[1:])
		for word in associates.split():
		    w = word.split("#")
                    associates_list.append((w[0].decode('utf-8'),float(w[1])))
		#singularplot(word,vector)
		return render_template('synonyms_raw.html', list_value=associates_list, word=query, model=model,pos=pos_tag,vector=vector)
    else:
        error_value = u'Incorrect query: %s' % userquery
        return render_template("synonyms_raw.html", error=error_value)

    return render_template("synonyms_raw.html")

# redirecting requests with no lang:
@synonyms.route('/about', methods=['GET', 'POST'])
@synonyms.route('/calculator', methods=['GET', 'POST'])
@synonyms.route('/similar', methods=['GET', 'POST'])
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
