#!/usr/bin/env python3
# coding: utf-8

import configparser
import csv
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
import config_path

languages = "/".join(list(language_dicts.keys())).upper()

config = configparser.RawConfigParser()
config.read(config_path.CONFIG)

root = config.get("Files and directories", "root")
modelsfile = config.get("Files and directories", "models")
contextual_modelsfile = config.get("Files and directories", "contextualized_models")
cachefile = config.get("Files and directories", "image_cache")
temp = config.get("Files and directories", "temp")
url = config.get("Other", "url")
vocabfile = config.get("Files and directories", "vocab")

if vocabfile:
    default_vocab = json.loads(open(os.path.join(root, vocabfile)).read())
else:
    default_vocab = None

detect_tag = config.getboolean("Tags", "detect_tag")
dbpedia = config.getboolean("Other", "dbpedia_images")
languages_list = config.get("Languages", "interface_languages").split(",")

if detect_tag:
    from lemmatizer import tagword, tag_ud

    tagger_port = config.getint("Sockets", "tagger_port")

tensorflow_integration = config.getboolean("Other", "tensorflow_projector")
if tensorflow_integration:
    from simplegist import Simplegist

    git_username = config.get("Other", "git_username")
    git_token = config.get("Other", "git_token")
    ghGist = Simplegist(username=git_username, api_token=git_token)

# Establishing connection to model server
host = config.get("Sockets", "host")
port = config.getint("Sockets", "port")
try:
    remote_ip = socket.gethostbyname(host)
except socket.gaierror:
    # could not resolve
    print("Hostname could not be resolved. Exiting", file=sys.stderr)
    sys.exit()

# Contextualized models:
contextual = config.getboolean("Token", "use_contextualized")


def serverquery(d_message):
    # create an INET, STREAMing socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except socket.error:
        print("Failed to create socket", file=sys.stderr)
        return None

    # Connect to remote server
    s.connect((remote_ip, port))
    # Now receive initial data
    _ = s.recv(1024)

    # Send some data to remote server
    d_message = json.dumps(d_message, ensure_ascii=False)
    try:
        s.sendall(d_message.encode("utf-8"))
    except socket.error:
        # Send failed
        print("Send failed", file=sys.stderr)
        s.close()
        return None
    # Now receive data
    reply = b""
    while True:
        data = s.recv(32768)
        if not data:
            break
        reply += data

    s.close()
    return reply


tags = config.getboolean("Tags", "use_tags")
taglist = set(config.get("Tags", "tags_list").split())
exposed_tag_file = config.get("Tags", "exposed_tags_list")

exposed_tags = {}

if tags:
    with open(root + exposed_tag_file, "r") as csvfile:
        reader = csv.DictReader(csvfile, delimiter="\t")
        for row in reader:
            exposed_tags[row["tag"]] = row["string"]
            if row["default"] == "True":
                defaulttag = row["tag"]

our_models = {}
model_props = {}
with open(modelsfile, "r") as csvfile:
    reader = csv.DictReader(csvfile, delimiter="\t")
    for row in reader:
        our_models[row["identifier"]] = row["string"]
        model_props[row["identifier"]] = {}
        model_props[row["identifier"]]["algo"] = row["algo"]
        model_props[row["identifier"]]["tags"] = row["tags"]
        model_props[row["identifier"]]["default"] = row["default"]
        model_props[row["identifier"]]["lang"] = row["lang"]
        if row["default"] == "True":
            defaultmodel = row["identifier"]

contextual_models = {}
contextual_model_props = {}
with open(contextual_modelsfile, "r") as csvfile:
    reader = csv.DictReader(csvfile, delimiter="\t")
    for row in reader:
        contextual_models[row["identifier"]] = row["string"]
        contextual_model_props[row["identifier"]] = {}
        contextual_model_props[row["identifier"]]["algo"] = row["algo"]
        contextual_model_props[row["identifier"]]["ref_static"] = row["ref_static"]
        contextual_model_props[row["identifier"]]["default"] = row["default"]
        contextual_model_props[row["identifier"]]["lang"] = row["lang"]
        if row["default"] == "True":
            contextual_defaultmodel = row["identifier"]

defaultsearchengine = config.get("Other", "default_search")

logging.basicConfig(
    format="%(asctime)s : %(levelname)s : %(message)s", level=logging.INFO
)

wvectors = Blueprint("wvectors", __name__, template_folder="templates")


def after_this_request(func):
    if not hasattr(g, "call_after_request"):
        g.call_after_request = []
    g.call_after_request.append(func)
    return func


@wvectors.after_request
def per_request_callbacks(response):
    for func in getattr(g, "call_after_request", ()):
        response = func(response)
    return response


def process_query(userquery, language="english"):
    userquery = userquery.strip()
    query = userquery
    if tags:
        if "_" in userquery:
            query_split = userquery.split("_")
            if not query_split[-1] in taglist:
                return "Incorrect tag!"
        else:
            if detect_tag:
                # Tagging with UDPipe
                tokens, lemmas, poses = tag_ud(tagger_port, userquery, lang=language)
                # poses = tagword(userquery)  # We tag using Stanford CoreNLP
                if len(poses) == 1:
                    pos_tag = poses[0]
                else:
                    pos_tag = poses[-1]
                query = userquery.replace(" ", "::") + "_" + pos_tag
    return query


def get_images(images):
    imagecache = {}
    imagedata = open(root + cachefile, "r")
    for LINE in imagedata:
        result = LINE.strip().split("\t")
        if len(result) == 2:
            (word, image) = result
            image = image.strip()
            if image == "None":
                image = None
            imagecache[word.strip()] = image
        else:
            continue
    imagedata.close()
    for w in images:
        image = getdbpediaimage(w, imagecache)
        if image:
            images[w] = image
    return images


def word2vec2tensor(alias, vectorlist, wordlist, classes):
    outfiletsv = alias + "_tensor.tsv"
    outfiletsvmeta = alias + "_metadata.tsv"
    tensortext = ""
    metadatatext = ""
    metadatatext += "word" + "\t" + "Class" + "\n"
    for word, vector, group in zip(wordlist, vectorlist, classes):
        try:
            (lemma, pos) = word.split("_")
        except ValueError:
            lemma = word
        metadatatext += lemma + "\t" + str(group) + "\n"
        vector_row = "\t".join(map(str, vector))
        tensortext += vector_row + "\n"
    a = ghGist.create(
        name=outfiletsv, description="Tensors", public=True, content=tensortext
    )
    b = ghGist.create(
        name=outfiletsvmeta, description="Metadata", public=True, content=metadatatext
    )
    datadic = {
        "embeddings": [
            {
                "tensorName": "WebVectors",
                "tensorShape": [len(vectorlist[0]), len(wordlist)],
                "tensorPath": a["files"][outfiletsv]["raw_url"],
                "metadataPath": b["files"][outfiletsvmeta]["raw_url"],
            }
        ]
    }
    c = ghGist.create(
        name=alias + "_config.json",
        description="WebVectors",
        public=True,
        content=json.dumps(datadic),
    )
    link2config = c["files"][alias + "_config.json"]["raw_url"]
    outputfile = open(root + "data/images/tsneplots/" + alias + ".url", "w")
    outputfile.write(link2config)
    outputfile.close()
    return link2config


@wvectors.route(url + "<lang:lang>/", methods=["GET", "POST"])
def home(lang):
    # pass all required variables to template
    # repeated within each @wvectors.route function
    g.lang = lang
    s = set()
    s.add(lang)
    other_lang = list(set(language_dicts.keys()) - s)[0]  # works only for two languages
    g.strings = language_dicts[lang]

    if request.method == "POST":
        list_data = request.form["list_query"]
        if (
                list_data.replace("_", "")
                        .replace("-", "")
                        .replace("::", "")
                        .replace(" ", "")
                        .isalnum()
        ):
            model_value = request.form.getlist("model")
            if len(model_value) < 1:
                model = defaultmodel
            else:
                model = model_value[0]
            language = model_props[model]["lang"]
            query = process_query(list_data, language=language)
            if query == "Incorrect tag!":
                error_value = "Incorrect tag!"
                return render_template(
                    "home.html",
                    error=error_value,
                    other_lang=other_lang,
                    languages=languages,
                    url=url, vocab=default_vocab
                )
            images = {query.split("_")[0]: None}
            models_row = {}
            frequencies = {}
            edges = {}
            if model_props[model]["tags"] == "False":
                query = query.split("_")[0]
                pos = "ALL"
            else:
                pos = query.split("_")[-1]
            message = {
                "operation": "1",
                "query": query,
                "pos": pos,
                "model": model,
                "nr_neighbors": 30,
            }
            result = json.loads(serverquery(message).decode("utf-8"))
            frequencies[model] = result["frequencies"]
            if query + " is unknown to the model" in result:
                return render_template(
                    "home.html",
                    error=query + " is unknown to the model",
                    other_lang=other_lang,
                    languages=languages,
                    url=url,
                    word=query, vocab=default_vocab
                )
            else:
                inferred = set()
                for word in result["neighbors"]:
                    images[word[0].split("_")[0]] = None
                models_row[model] = result["neighbors"]
                if dbpedia:
                    images = get_images(images)
                if "inferred" in result:
                    inferred.add(model)
                edges[model] = result["edges"]

                return render_template(
                    "home.html",
                    list_value=models_row,
                    word=query,
                    wordimages=images,
                    models=our_models,
                    model=model,
                    tags=tags,
                    other_lang=other_lang,
                    languages=languages,
                    url=url,
                    inferred=inferred,
                    frequencies=frequencies,
                    visible_neighbors=10,
                    edges=edges, vocab=default_vocab
                )
        else:
            error_value = "Incorrect query!"
            return render_template(
                "home.html",
                error=error_value,
                tags=tags,
                other_lang=other_lang,
                languages=languages,
                url=url, vocab=default_vocab
            )
    return render_template(
        "home.html", tags=tags, other_lang=other_lang, languages=languages, url=url,
        vocab=default_vocab
    )


@wvectors.route(url + "<lang:lang>/misc/", methods=["GET", "POST"])
def misc_page(lang):
    g.lang = lang
    s = set()
    s.add(lang)
    other_lang = list(set(language_dicts.keys()) - s)[0]  # works only for two languages
    g.strings = language_dicts[lang]

    if request.method == "POST":
        input_data = request.form["query"]

        # Similarity queries
        if input_data != "dummy":
            if " " in input_data.strip():
                input_data = input_data.strip()
                if input_data.endswith(","):
                    input_data = input_data[:-1]
                cleared_data = []
                sim_history = request.form["sim_history"]
                if not sim_history.strip():
                    sim_history = []
                else:
                    sim_history = json.loads(sim_history)
                model_value = request.form.getlist("simmodel")
                if len(model_value) < 1:
                    model = defaultmodel
                else:
                    model = model_value[0]
                language = model_props[model]["lang"]
                if not model.strip() in our_models:
                    return render_template(
                        "home.html",
                        other_lang=other_lang,
                        languages=languages,
                        url=url,
                        usermodels=model_value,
                    )
                for query in input_data.split(","):
                    if "" not in query.strip():
                        continue
                    query = query.split()
                    words = []
                    for w in query[:2]:
                        if (
                                w.replace("_", "")
                                        .replace("-", "")
                                        .replace("::", "")
                                        .isalnum()
                        ):
                            w = process_query(w, language=language)
                            if "Incorrect tag!" in w:
                                error_value = "Incorrect tag!"
                                return render_template(
                                    "similar.html",
                                    error_sim=error_value,
                                    models=our_models,
                                    other_lang=other_lang,
                                    languages=languages,
                                    url=url,
                                    usermodels=model_value,
                                    tags2show=exposed_tags,
                                )
                            if model_props[model]["tags"] == "False":
                                words.append(w.split("_")[0].strip())
                            else:
                                words.append(w.strip())
                    if len(words) == 2:
                        cleared_data.append((words[0].strip(), words[1].strip()))
                if len(cleared_data) == 0:
                    error_value = "Incorrect query!"
                    return render_template(
                        "similar.html",
                        error_sim=error_value,
                        other_lang=other_lang,
                        languages=languages,
                        url=url,
                        usermodels=model_value,
                        tags2show=exposed_tags,
                    )
                message = {"operation": "2", "query": cleared_data, "model": model}
                result = json.loads(serverquery(message).decode("utf-8"))
                cleared_data = [" ".join(el) for el in cleared_data]
                if "Unknown to the model" in result:
                    return render_template(
                        "similar.html",
                        error_sim=result["Unknown to the model"],
                        other_lang=other_lang,
                        languages=languages,
                        models=our_models,
                        tags2show=exposed_tags,
                        tags=tags,
                        query=cleared_data,
                        url=url,
                        usermodels=model_value,
                    )
                sim_history.append(result["similarities"])
                if len(sim_history) > 10:
                    sim_history = sim_history[-10:]
                str_sim_history = json.dumps(sim_history, ensure_ascii=False)
                return render_template(
                    "similar.html",
                    value=result["similarities"],
                    model=model,
                    query=cleared_data,
                    models=our_models,
                    tags=tags,
                    other_lang=other_lang,
                    tags2show=exposed_tags,
                    languages=languages,
                    url=url,
                    usermodels=model_value,
                    sim_hist=sim_history,
                    str_sim_history=str_sim_history,
                    frequencies=result["frequencies"],
                )
            else:
                error_value = "Incorrect query!"
                return render_template(
                    "similar.html",
                    error_sim=error_value,
                    models=our_models,
                    tags=tags,
                    tags2show=exposed_tags,
                    other_lang=other_lang,
                    languages=languages,
                    url=url,
                    usermodels=[defaultmodel],
                )
    return render_template(
        "similar.html",
        models=our_models,
        tags=tags,
        other_lang=other_lang,
        languages=languages,
        url=url,
        usermodels=[defaultmodel],
        tags2show=exposed_tags,
    )


@wvectors.route(url + "<lang:lang>/associates/", methods=["GET", "POST"])
@wvectors.route(url + "<lang:lang>/similar/", methods=["GET", "POST"])
def associates_page(lang):
    g.lang = lang
    s = set()
    s.add(lang)
    other_lang = list(set(language_dicts.keys()) - s)[0]  # works only for two languages
    g.strings = language_dicts[lang]
    if request.method == "POST":
        list_data = request.form["list_query"]

        # Nearest associates queries
        if (
                list_data != "dummy"
                and list_data.replace("_", "")
                .replace("-", "")
                .replace("::", "")
                .replace(" ", "")
                .isalnum()
        ):
            model_value = request.form.getlist("model")
            if len(model_value) < 1:
                model_value = [defaultmodel]
            model_langs = set([model_props[el]["lang"] for el in model_value])
            if len(model_langs) > 1:
                language = model_props[defaultmodel]["lang"]
            else:
                language = list(model_langs)[0]
            list_data = list_data.strip()
            query = process_query(list_data, language)

            if query == "Incorrect tag!":
                error_value = "Incorrect tag!"
                return render_template(
                    "associates.html",
                    error=error_value,
                    word=list_data,
                    models=our_models,
                    tags2show=exposed_tags,
                    other_lang=other_lang,
                    languages=languages,
                    url=url,
                    usermodels=model_value,
                )
            userpos = []
            if tags:
                pos_value = request.form.getlist("pos")
                if len(pos_value) < 1:
                    pos = query.split("_")[-1]
                else:
                    pos = pos_value[0]
                if pos != "ALL":
                    userpos.append(pos)
                if pos == "Q":
                    pos = query.split("_")[-1]
            else:
                pos = "ALL"

            images = {query.split("_")[0]: None}
            models_row = {}
            inferred = set()
            frequencies = {}
            for model in model_value:
                if not model.strip() in our_models:
                    return render_template(
                        "home.html",
                        other_lang=other_lang,
                        languages=languages,
                        url=url,
                        usermodels=model_value,
                    )
                if model_props[model]["tags"] == "False":
                    model_query = query.split("_")[0]
                    message = {
                        "operation": "1",
                        "query": model_query,
                        "pos": "ALL",
                        "model": model,
                        "nr_neighbors": 30,
                    }
                else:
                    model_query = query
                    message = {
                        "operation": "1",
                        "query": model_query,
                        "pos": pos,
                        "model": model,
                        "nr_neighbors": 30,
                    }
                result = json.loads(serverquery(message).decode("utf-8"))
                frequencies[model] = result["frequencies"]
                if model_query != query:
                    frequencies[model][query] = frequencies[model][model_query]
                if model_query + " is unknown to the model" in result:
                    models_row[model] = "Unknown!"
                    continue
                elif "No results" in result:
                    models_row[model] = "No results!"
                    continue
                else:
                    for word in result["neighbors"]:
                        images[word[0].split("_")[0]] = None
                    models_row[model] = result["neighbors"]
                    if dbpedia:
                        images = get_images(images)
                    if "inferred" in result:
                        inferred.add(model)

            return render_template(
                "associates.html",
                list_value=models_row,
                word=query,
                pos=pos,
                number=len(model_value),
                wordimages=images,
                models=our_models,
                tags=tags,
                other_lang=other_lang,
                languages=languages,
                tags2show=exposed_tags,
                url=url,
                usermodels=model_value,
                userpos=userpos,
                inferred=inferred,
                frequencies=frequencies,
                visible_neighbors=10,
            )
        else:
            error_value = "Incorrect query!"
            return render_template(
                "associates.html",
                error=error_value,
                models=our_models,
                tags=tags,
                url=url,
                usermodels=[defaultmodel],
                tags2show=exposed_tags,
            )
    return render_template(
        "associates.html",
        models=our_models,
        tags=tags,
        other_lang=other_lang,
        languages=languages,
        url=url,
        usermodels=[defaultmodel],
        tags2show=exposed_tags,
    )


@wvectors.route(url + "<lang:lang>/visual/", methods=["GET", "POST"])
def visual_page(lang):
    g.lang = lang
    s = set()
    s.add(lang)
    other_lang = list(set(language_dicts.keys()) - s)[0]  # works only for two languages
    g.strings = language_dicts[lang]

    if request.method == "POST":
        list_data = request.form.getlist("list_query")
        viz_method = request.form.getlist("viz_method")[0]
        if list_data:
            model_value = request.form.getlist("model")
            if len(model_value) < 1:
                model_value = [defaultmodel]
            language = model_props[defaultmodel]["lang"]
            groups = []
            for inputform in list_data[:10]:
                group = set(
                    [
                        process_query(w, language)
                        for w in inputform.split(",")
                        if len(w) > 1
                           and w.replace("_", "")
                               .replace("-", "")
                               .replace("::", "")
                               .replace(" ", "")
                               .isalnum()
                    ][:30]
                )
                groups.append(group)

            querywords = [word for group in groups for word in group]
            if len(set(querywords)) != len(querywords):
                error_value = "Words must be unique!"
                return render_template(
                    "visual.html",
                    error=error_value,
                    models=our_models,
                    other_lang=other_lang,
                    languages=languages,
                    url=url,
                    usermodels=model_value,
                )
            if len(querywords) < 7:
                error_value = "Too few words!"
                return render_template(
                    "visual.html",
                    error=error_value,
                    models=our_models,
                    other_lang=other_lang,
                    languages=languages,
                    url=url,
                    usermodels=model_value,
                )

            if "Incorrect tag!" in querywords:
                error_value = "Incorrect tag!"
                return render_template(
                    "visual.html",
                    error=error_value,
                    models=our_models,
                    other_lang=other_lang,
                    languages=languages,
                    url=url,
                    usermodels=model_value,
                )

            classes = []
            for word in querywords:
                for group in groups:
                    if word in group:
                        classes.append(groups.index(group))

            unknown = {}
            models_row = {}
            links_row = {}
            frequencies = {}
            for model in model_value:
                if not model.strip() in our_models:
                    return render_template(
                        "home.html",
                        other_lang=other_lang,
                        languages=languages,
                        url=url,
                        usermodels=model_value,
                    )
                frequencies[model] = {}
                unknown[model] = set()
                words2vis = querywords
                m = hashlib.md5()
                name = ":::".join(["__".join(group) for group in groups])
                name = name.encode("ascii", "backslashreplace")
                m.update(name)
                fname = m.hexdigest()
                plotfile = f"{model}_{fname}_{viz_method}.png"
                identifier = plotfile[:-4]
                models_row[model] = plotfile
                labels = []
                if not os.path.exists(root + "data/images/tsneplots"):
                    os.makedirs(root + "data/images/tsneplots")
                if not os.access(root + "data/images/tsneplots/" + plotfile, os.F_OK):
                    print(
                        f"No previous image found: {root}data/images/tsneplots/{plotfile}",
                        file=sys.stderr,
                    )
                    vectors = []
                    for w in words2vis:
                        if model_props[model]["tags"] == "False":
                            message = {
                                "operation": "4",
                                "query": w.split("_")[0],
                                "model": model,
                            }
                        else:
                            message = {"operation": "4", "query": w, "model": model}
                        result = json.loads(serverquery(message).decode("utf-8"))
                        frequencies[model].update(result["frequencies"])
                        if (
                                w.split("_")[0] in frequencies[model]
                                and w not in frequencies[model]
                        ):
                            frequencies[model][w] = frequencies[model][w.split("_")[0]]
                        if w + " is unknown to the model" in result:
                            unknown[model].add(w)
                            continue
                        vector = np.array(result["vector"])
                        vectors.append(vector)
                        labels.append(w)
                    if len(vectors) > 5:
                        if len(list_data) == 1 and model_props[model]["tags"] == "True":
                            classes = [word.split("_")[-1] for word in labels]
                        print(f"Embedding with {viz_method}...", file=sys.stderr)
                        matrix2vis = np.vstack(([v for v in vectors]))
                        embed(
                            labels,
                            matrix2vis.astype("float64"),
                            classes,
                            model,
                            fname,
                            method=viz_method,
                        )
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
                        links_row[model] = open(
                            f"{root}data/images/tsneplots/{identifier}.url", "r"
                        ).read()
                    else:
                        links_row[model] = None
            return render_template(
                "visual.html",
                languages=languages,
                visual=models_row,
                words=groups,
                number=len(model_value),
                models=our_models,
                unknown=unknown,
                url=url,
                usermodels=model_value,
                l2c=links_row,
                qwords=querywords,
                frequencies=frequencies,
                other_lang=other_lang,
                viz_method=viz_method,
            )
        else:
            error_value = "Incorrect query!"
            return render_template(
                "visual.html",
                error=error_value,
                models=our_models,
                other_lang=other_lang,
                languages=languages,
                url=url,
                usermodels=[defaultmodel],
            )
    return render_template(
        "visual.html",
        models=our_models,
        other_lang=other_lang,
        languages=languages,
        url=url,
        usermodels=[defaultmodel],
    )


@wvectors.route(url + "<lang:lang>/calculator/", methods=["GET", "POST"])
def finder(lang):
    g.lang = lang
    s = set()
    s.add(lang)
    other_lang = list(set(language_dicts.keys()) - s)[0]  # works only for two languages
    g.strings = language_dicts[lang]

    if request.method == "POST":
        positive_data = ""
        positive2_data = ""
        negative_data = ""
        positive1_data = ""
        negative1_data = ""
        try:
            positive_data = request.form["positive"]
            positive2_data = request.form["positive2"]
            negative_data = request.form["negative"]
        except:
            pass
        try:
            positive1_data = request.form["positive1"]
            negative1_data = request.form["negative1"]
        except:
            pass
        # Analogical inference
        if negative_data != "" and positive_data != "" and positive2_data != "":
            calcmodel_value = request.form.getlist("calcmodel")
            if len(calcmodel_value) < 1:
                calcmodel_value = [defaultmodel]
            language = model_props[defaultmodel]["lang"]
            positive_data_list = [positive_data, positive2_data]
            negative_list = []
            if len(negative_data.strip()) > 1:
                if (
                        negative_data.strip()
                                .replace("_", "")
                                .replace("-", "")
                                .replace("::", "")
                                .replace(" ", "")
                                .isalnum()
                ):
                    negative_list = [process_query(negative_data, language)]

            positive_list = []
            for w in positive_data_list:
                if (
                        len(w) > 1
                        and w.replace("_", "")
                        .replace("-", "")
                        .replace("::", "")
                        .replace(" ", "")
                        .isalnum()
                ):
                    positive_list.append(process_query(w, language))

            if len(positive_list) < 2 or len(negative_list) == 0:
                error_value = "Incorrect query!"
                return render_template(
                    "calculator.html",
                    error=error_value,
                    models=our_models,
                    other_lang=other_lang,
                    languages=languages,
                    url=url,
                    usermodels=calcmodel_value,
                    tags2show=exposed_tags,
                )
            if "Incorrect tag!" in negative_list or "Incorrect tag!" in positive_list:
                error_value = "Incorrect tag!"
                return render_template(
                    "calculator.html",
                    error=error_value,
                    models=our_models,
                    tags2show=exposed_tags,
                    other_lang=other_lang,
                    languages=languages,
                    url=url,
                    usermodels=calcmodel_value,
                )
            userpos = []
            if tags:
                calcpos_value = request.form.getlist("pos")
                if len(calcpos_value) < 1:
                    pos = defaulttag
                else:
                    pos = calcpos_value[0]
                if pos != "ALL":
                    userpos.append(pos)
            else:
                pos = "ALL"

            models_row = {}
            images = {}
            frequencies = {}
            for model in calcmodel_value:
                if not model.strip() in our_models:
                    return render_template(
                        "home.html",
                        other_lang=other_lang,
                        languages=languages,
                        models=our_models,
                        url=url,
                        usermodels=calcmodel_value,
                    )
                if model_props[model]["tags"] == "False":
                    message = {
                        "operation": "3",
                        "query": [
                            [w.split("_")[0] for w in positive_list],
                            [w.split("_")[0] for w in negative_list],
                        ],
                        "pos": "ALL",
                        "model": model,
                        "nr_neighbors": 30,
                    }
                else:
                    message = {
                        "operation": "3",
                        "query": [positive_list, negative_list],
                        "pos": pos,
                        "model": model,
                        "nr_neighbors": 30,
                    }
                result = json.loads(serverquery(message).decode("utf-8"))
                frequencies[model] = result["frequencies"]
                if "No results" in result:
                    models_row[model] = ["No similar words with this tag."]
                    continue
                if "Unknown to the model" in result:
                    models_row[model] = [
                        result["Unknown to the model"] + " is unknown to the model"
                    ]
                    continue
                for word in result["neighbors"]:
                    images[word[0].split("_")[0]] = None
                models_row[model] = result["neighbors"]
                if dbpedia:
                    images = get_images(images)
            return render_template(
                "calculator.html",
                analogy_value=models_row,
                pos=pos,
                plist=positive_list,
                userpos=userpos,
                nlist=negative_list,
                wordimages=images,
                models=our_models,
                tags=tags,
                tags2show=exposed_tags,
                other_lang=other_lang,
                languages=languages,
                url=url,
                usermodels=calcmodel_value,
                frequencies=frequencies,
                visible_neighbors=5,
            )

        # Calculator
        if positive1_data != "":
            calcmodel_value = request.form.getlist("calcmodel")
            if len(calcmodel_value) < 1:
                calcmodel_value = [defaultmodel]
            language = model_props[defaultmodel]["lang"]
            negative_list = [
                                process_query(w, language)
                                for w in negative1_data.split()
                                if len(w) > 1
                                   and w.replace("_", "").replace("-", "").replace("::",
                                                                                   "").isalnum()
                            ][:10]
            positive_list = [
                                process_query(w, language)
                                for w in positive1_data.split()
                                if len(w) > 1
                                   and w.replace("_", "").replace("-", "").replace("::",
                                                                                   "").isalnum()
                            ][:10]

            if len(positive_list) == 0:
                error_value = "Incorrect query!"
                return render_template(
                    "calculator.html",
                    calc_error=error_value,
                    other_lang=other_lang,
                    tags2show=exposed_tags,
                    languages=languages,
                    models=our_models,
                    url=url,
                    usermodels=calcmodel_value,
                )
            if "Incorrect tag!" in negative_list or "Incorrect tag!" in positive_list:
                error_value = "Incorrect tag!"
                return render_template(
                    "calculator.html",
                    calc_error=error_value,
                    other_lang=other_lang,
                    tags2show=exposed_tags,
                    languages=languages,
                    models=our_models,
                    url=url,
                    usermodels=calcmodel_value,
                )
            userpos = []
            if tags:
                calcpos_value = request.form.getlist("calcpos")
                if len(calcpos_value) < 1:
                    pos = defaulttag
                else:
                    pos = calcpos_value[0]
                if pos != "ALL":
                    userpos.append(pos)
            else:
                pos = "ALL"

            models_row = {}
            images = {}
            frequencies = {}
            for model in calcmodel_value:
                if not model.strip() in our_models:
                    return render_template(
                        "home.html",
                        other_lang=other_lang,
                        languages=languages,
                        models=our_models,
                        url=url,
                        usermodels=calcmodel_value,
                    )
                if model_props[model]["tags"] == "False":
                    message = {
                        "operation": "3",
                        "query": [
                            [w.split("_")[0] for w in positive_list],
                            [w.split("_")[0] for w in negative_list],
                        ],
                        "pos": "ALL",
                        "model": model,
                        "nr_neighbors": 30,
                    }
                else:
                    message = {
                        "operation": "3",
                        "query": [positive_list, negative_list],
                        "pos": pos,
                        "model": model,
                        "nr_neighbors": 30,
                    }
                result = json.loads(serverquery(message).decode("utf-8"))
                frequencies[model] = result["frequencies"]
                if "No results" in result:
                    models_row[model] = ["No similar words with this tag."]
                    continue
                if "Unknown to the model" in result:
                    models_row[model] = [
                        result["Unknown to the model"] + "is unknown to the model"
                    ]
                    continue
                for word in result["neighbors"]:
                    images[word[0].split("_")[0]] = None
                models_row[model] = result["neighbors"]
                if dbpedia:
                    images = get_images(images)
            return render_template(
                "calculator.html",
                calc_value=models_row,
                pos=pos,
                plist2=positive_list,
                tags2show=exposed_tags,
                nlist2=negative_list,
                wordimages=images,
                models=our_models,
                tags=tags,
                userpos=userpos,
                other_lang=other_lang,
                languages=languages,
                url=url,
                usermodels=calcmodel_value,
                frequencies=frequencies,
                visible_neighbors=5,
            )

        else:
            error_value = "Incorrect query!"
            return render_template(
                "calculator.html",
                error=error_value,
                models=our_models,
                tags=tags,
                tags2show=exposed_tags,
                other_lang=other_lang,
                languages=languages,
                url=url,
                usermodels=[defaultmodel],
            )
    return render_template(
        "calculator.html",
        models=our_models,
        tags=tags,
        other_lang=other_lang,
        tags2show=exposed_tags,
        languages=languages,
        url=url,
        usermodels=[defaultmodel],
    )


@wvectors.route(url + "<lang:lang>/contextual/", methods=["GET", "POST"])
def contextual_page(lang):
    g.lang = lang
    s = set()
    s.add(lang)
    other_lang = list(set(language_dicts.keys()) - s)[0]  # works only for two languages
    g.strings = language_dicts[lang]

    all_layers = ["top", "average"]

    if request.method == "POST":
        sentence = request.form["input_sentence"]
        elmo_history = request.form["elmo_history"]
        if not elmo_history.strip():
            elmo_history = []
        else:
            elmo_history = json.loads(elmo_history)
        layers_value = request.form.getlist("elmo_layers")
        if len(layers_value) < 1:
            layer = "top"
        else:
            layer = layers_value[0]
        model_value = request.form.getlist("elmo_models")
        if len(model_value) < 1:
            model = contextual_defaultmodel
        else:
            model = model_value[0]
        images = {}
        results = {}
        table_results = {}
        header = []
        sims = []
        model_indv_wordpage = contextual_model_props[model]["ref_static"]
        language = contextual_model_props[model]["lang"]
        tokens, lemmas, poses = tag_ud(tagger_port, sentence, lang=language)  # For UDPipe
        # tokens, lemmas, poses = tagword(sentence, return_tokens=True)  # For CoreNLP
        if len(sentence) > 2:
            message = {
                "operation": "5",
                "query": tokens,
                "layers": layer,
                "model": model,
                "nr_neighbors": 10,
            }
            result = json.loads(serverquery(message).decode("utf-8"))
            frequencies = result["frequencies"]
            for word in result["neighbors"]:
                for n in word:
                    images[n[0].split("_")[0]] = None
            for num, word, neighbors, tag in zip(
                    range(len(tokens)), tokens, result["neighbors"], poses
            ):
                if word in ".,!?-\"':;":
                    continue
                sims += [x[1] for x in neighbors]
                results[(word, tag, num)] = neighbors
            max_sim, min_sim = max(sims), min(sims)
            sim_range = max_sim - min_sim
            sim_tier = sim_range / 5
            font_tiers = {
                (max_sim, max_sim - sim_tier): "16",
                (max_sim - sim_tier, max_sim - 2 * sim_tier): "14",
                (max_sim - 2 * sim_tier, max_sim - 3 * sim_tier): "12",
                (max_sim - 3 * sim_tier, max_sim - 4 * sim_tier): "10",
                (max_sim - 4 * sim_tier, min_sim): "8",
            }
            for word in results:
                for neighbor in results[word]:
                    for tier in font_tiers:
                        if tier[0] >= neighbor[1] > tier[1]:
                            font_size = font_tiers[tier]
                            neighbor.append(font_size)
            for word in results:
                header.append(word)
                for substitute in range(len(results[word])):
                    # here we determine how many neighbors we want to be shown in the results:
                    if substitute > 4:
                        break
                    neighbor = results[word][substitute]
                    if len(word[0]) < 2 or word[1] in [
                        "ADP",
                        "CCONJ",
                        "PRON",
                        "AUX",
                        "DET",
                        "SCONJ",
                        "PART",
                    ]:
                        neighbor = (word[0], "None")
                    if str(substitute) in table_results:
                        table_results[str(substitute)].append(neighbor)
                    else:
                        table_results[str(substitute)] = [neighbor]
            elmo_history.append([header, table_results, contextual_models[model]])
            if len(elmo_history) > 5:
                elmo_history = elmo_history[-5:]
            str_elmo_history = json.dumps(elmo_history, ensure_ascii=False)
            return render_template(
                "contextual.html",
                results=table_results,
                header=header,
                tags=tags,
                sentence=sentence,
                other_lang=other_lang,
                languages=languages,
                frequencies=frequencies,
                static_model=model_indv_wordpage,
                model=model,
                elmo_models=contextual_models,
                url=url,
                user_layer=layer,
                all_layers=all_layers,
                elmo_hist=elmo_history,
                str_elmo_history=str_elmo_history,
            )
        else:
            error_value = "Incorrect query!"
            return render_template(
                "contextual.html",
                error=error_value,
                other_lang=other_lang,
                languages=languages,
                url=url,
                elmo_models=contextual_models,
                all_layers=all_layers,
            )
    if not contextual:
        return render_template(
            "contextual.html",
            error="misconfiguration",
            other_lang=other_lang,
            languages=languages,
            url=url,
        )
    return render_template(
        "contextual.html",
        other_lang=other_lang,
        languages=languages,
        url=url,
        elmo_models=contextual_models,
        all_layers=all_layers,
    )


@wvectors.route(url + "<lang:lang>/<model>/<userquery>/", methods=["GET", "POST"])
def raw_finder(lang, model, userquery):
    g.lang = lang
    s = set()
    s.add(lang)
    other_lang = list(set(language_dicts.keys()) - s)[0]  # works only for two languages
    g.strings = language_dicts[lang]

    model = model.strip()
    if not model.strip() in our_models:
        return redirect(url + lang + "/", code=303)
    language = model_props[model]["lang"]
    if userquery.strip().replace("_", "").replace("-", "").replace("::", "").isalnum():
        query = process_query(userquery.strip(), language)
        if tags:
            if query == "Incorrect tag!":
                error_value = "Incorrect tag!"
                return render_template(
                    "wordpage.html",
                    error=error_value,
                    other_lang=other_lang,
                    languages=languages,
                    url=url,
                )
            pos_tag = query.split("_")[-1]
        else:
            pos_tag = "ALL"
        images = {query.split("_")[0]: None}
        image = None
        models_row = {}
        frequencies = {}
        edges = {}
        if model_props[model]["tags"] == "False":
            query = query.split("_")[0]
            pos_tag = "ALL"
        message = {
            "operation": "1",
            "query": query,
            "pos": pos_tag,
            "model": model,
            "nr_neighbors": 30,
        }
        result = json.loads(serverquery(message).decode("utf-8"))
        frequencies[model] = result["frequencies"]
        if query + " is unknown to the model" in result or "No results" in result:
            return render_template(
                "wordpage.html",
                error=list(result)[0],
                other_lang=other_lang,
                languages=languages,
                url=url,
                word=query,
                models=our_models,
                model=model,
            )
        else:
            inferred = set()
            if "inferred" in result:
                inferred.add(model)
            vector = result["vector"]
            for word in result["neighbors"]:
                images[word[0].split("_")[0]] = None
            m = hashlib.md5()
            name = query.encode("ascii", "backslashreplace")
            m.update(name)
            fname = m.hexdigest()
            plotfile = root + "data/images/singleplots/" + model + "_" + fname + ".png"
            if not os.access(plotfile, os.F_OK):
                singularplot(query, model, vector, fname)
            models_row[model] = result["neighbors"]
            if dbpedia:
                images = get_images(images)
                image = images[query.split("_")[0]]

            edges[model] = result["edges"]

            return render_template(
                "wordpage.html",
                list_value=models_row,
                word=query,
                model=model,
                pos=pos_tag,
                vector=vector,
                image=image,
                wordimages=images,
                vectorvis=fname,
                tags=tags,
                other_lang=other_lang,
                languages=languages,
                url=url,
                search=defaultsearchengine,
                models=our_models,
                inferred=inferred,
                frequencies=frequencies,
                visible_neighbors=10,
                edges=edges,
            )
    else:
        error_value = "Incorrect query!"
        return render_template(
            "wordpage.html",
            error=error_value,
            tags=tags,
            other_lang=other_lang,
            languages=languages,
            url=url,
        )


def generate(word, model, api_format):
    """
    yields result of the query
    :param model: name of a model to be queried
    :param word: query word
    :param api_format: format of the output - csv or json
    """

    formats = {"csv", "json"}
    language = model_props[model]["lang"]
    # check the sanity of the query word: no punctuation marks, not an empty string
    if not word.strip().replace("_", "").replace("-", "").replace("::", "").isalnum():
        word = "".join([char for char in word if char.isalnum()])
        yield word.strip() + "\t" + model.strip() + "\t" + "Word error!"
    else:
        query = process_query(word.strip(), language)

        # if tags are used, check whether the word is tagged
        if tags:
            if len(query.split("_")) < 2:
                yield query.strip() + "\t" + model.strip() + "\t" + "Error!"

        # check whether the format is correct
        if api_format not in formats:
            yield api_format + "\t" + "Output format error!"

        # if all is OK...
        # check that the model exists
        if not model.strip() in our_models:
            yield query.strip() + "\t" + model.strip() + "\t" + "Model error!"
        else:
            # form the query and get the result from the server
            if model_props[model]["tags"] == "False":
                message = {
                    "operation": "1",
                    "query": query.split("_")[0],
                    "pos": "ALL",
                    "model": model,
                    "nr_neighbors": 10,
                }
            else:
                message = {
                    "operation": "1",
                    "query": query,
                    "pos": "ALL",
                    "model": model,
                    "nr_neighbors": 10,
                }
            result = json.loads(serverquery(message).decode("utf-8"))

            # handle cases when the server returned that the word is unknown to the model,
            # or for some other reason the associates list is empty
            if query + " is unknown to the model" in result or "No results" in result:
                yield query + "\t" + list(result)[0]
            else:

                # return result in csv
                if api_format == "csv":
                    yield model + "\n"
                    yield query + "\n"
                    for associate in result["neighbors"]:
                        yield "%s\t%s\n" % (associate[0], str(associate[1]))

                # return result in json
                elif api_format == "json":
                    associates = OrderedDict()
                    for associate in result["neighbors"]:
                        associates[associate[0]] = associate[1]
                    result = {model: {query: associates}}
                    yield json.dumps(result, ensure_ascii=False)


@wvectors.route(url + "<model>/<word>/api/<api_format>/", methods=["GET"])
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
    if api_format == "csv":
        mime = "text/csv"
    else:
        mime = "application/json"

    cleanword = "".join([char for char in word if char.isalnum()])
    return Response(
        generate(word, model, api_format),
        mimetype=mime,
        headers={
            "Content-Disposition": "attachment;filename=%s.%s"
                                   % (cleanword.encode("utf-8"), api_format.encode("utf-8"))
        },
    )


@wvectors.route(url + "<model>/<wordpair>/api/similarity/", methods=["GET"])
def similarity_api(model, wordpair):
    """
    provides a similarity value for a given word pair
    :param model: a name of a model to be queried
    :param wordpair: a query word pair separated by __ (2 underscores)
    :return: similarity value as a string
    all function arguments are strings
    """
    model = model.strip()
    language = model_props[model]["lang"]
    wordpair = wordpair.split("__")
    if not model.strip() in our_models:
        return "The model " + model.strip() + " is unknown"
    cleanword0 = "".join(
        [
            char
            for char in wordpair[0]
            if char.isalnum() or char == "_" or char == "::" or char == "-"
        ]
    )
    cleanword1 = "".join(
        [
            char
            for char in wordpair[1]
            if char.isalnum() or char == "_" or char == "::" or char == "-"
        ]
    )
    cleanword0 = process_query(cleanword0, language)
    cleanword1 = process_query(cleanword1, language)
    if model_props[model]["tags"] == "False":
        cleanword0 = cleanword0.split("_")[0]
        cleanword1 = cleanword1.split("_")[0]
    message = {"operation": "2", "query": [[cleanword0, cleanword1]], "model": model}
    result = json.loads(serverquery(message).decode("utf-8"))
    if "Unknown to the model" in result:
        return "Unknown"
    sim = result["similarities"][-1][-1]
    return str(sim) + "\t" + cleanword0 + "\t" + cleanword1 + "\t" + model


@wvectors.route(url + "<lang:lang>/models/")
def models_page(lang):
    g.lang = lang
    s = set()
    s.add(lang)
    other_lang = list(set(language_dicts.keys()) - s)[0]  # works only for two languages
    g.strings = language_dicts[lang]
    return render_template(
        "%s/models.html" % lang, other_lang=other_lang, languages=languages, url=url
    )


@wvectors.route(url + "<lang:lang>/about/")
def about_page(lang):
    g.lang = lang
    s = set()
    s.add(lang)
    other_lang = list(set(language_dicts.keys()) - s)[0]  # works only for two languages
    g.strings = language_dicts[lang]

    return render_template(
        "%s/about.html" % lang, other_lang=other_lang, languages=languages, url=url
    )


# redirecting requests with no lang:
@wvectors.route(url + "about/", methods=["GET", "POST"])
@wvectors.route(url + "calculator/", methods=["GET", "POST"])
@wvectors.route(url + "similar/", methods=["GET", "POST"])
@wvectors.route(url + "associates/", methods=["GET", "POST"])
@wvectors.route(url + "contextual/", methods=["GET", "POST"])
@wvectors.route(url + "visual/", methods=["GET", "POST"])
@wvectors.route(url + "models/", methods=["GET", "POST"])
@wvectors.route(url, methods=["GET", "POST"])
def redirect_main():
    req = request.path.split("/")[-2]
    if len(req) == 0:
        req = "/"
    else:
        if req[-1] != "/":
            req += "/"
    return redirect(url + "en" + req)
