#!/usr/bin/env python
# coding: utf-8

import subprocess
import requests
import json


def tag_ud(port, text='Do not forget to pass some text as a string!'):
    # UDPipe tagging for any language you have a model for.
    # Demands UDPipe REST server (https://ufal.mff.cuni.cz/udpipe/users-manual#udpipe_server)
    # running on a port defined in webvectors.cfg
    # Start the server with something like:
    # udpipe_server --daemon 66666 MyModel MyModel /opt/my.model UD

    # Sending user query to the server:
    ud_reply = requests.post('http://localhost:%s/process' % port,
                             data={'tokenizer': '', 'tagger': '', 'data': text}).content

    # Getting the result in the CONLLU format:
    processed = json.loads(ud_reply.decode('utf-8'))['result']

    # Skipping technical lines:
    content = [l for l in processed.split('\n') if not l.startswith('#')]

    # Extracting lemmas and tags from the processed queries:
    tagged = [w.split('\t')[2].lower() + '_' + w.split('\t')[3] for w in content if w]
    poses = [t.split('_')[1] for t in tagged]
    return poses


def tagword(word):
    # Stanford CoreNLP tagging for English (and other languages)
    # Demands Stanford Core NLP server running on a defined port
    # Start server with something like:
    # java -mx4g -cp "*" edu.stanford.nlp.pipeline.StanfordCoreNLPServer --port 9999
    port = 9999

    corenlp = requests.post(
        'http://localhost:%s/?properties='
        '{"annotators": "tokenize, pos, lemma", "outputFormat": "json"}' % port,
        data=word.encode('utf-8')).content
    tagged = json.loads(corenlp.decode('utf-8'), strict=False)
    if len(tagged["sentences"]) < 1:
        return 'Error!'
    poses = []
    for el in tagged["sentences"][0]["tokens"]:
        pos = el["pos"]
        poses.append(ptb2upos[pos])
    return poses


def freeling_lemmatizer(word):
    # Freeling tagging for Russian
    # Queries Freeling service at localhost port 50006

    freeling = subprocess.Popen([u'/usr/local/bin/analyzer_client', u'50006'],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    tagged = freeling.communicate(word.encode('utf-8').strip())
    tagged = tagged[0].decode('utf-8').split('\n')
    tagged = [l for l in tagged if len(l) > 0]
    if len(tagged) < 1:
        return 'Error!'
    poses = []
    for line in tagged:
        tag = line.split()[2]
        freeling_pos = tag[0]
        if freeling_pos in freeling2upos:
            universal_pos = freeling2upos[freeling_pos]
            if universal_pos == 'NOUN':
                noun_type = tag[1]
                if noun_type == 'P':
                    universal_pos = 'PROPN'
                if len(tag) > 5:
                    freeling_info = tag[6]
                    if freeling_info == 'G' or freeling_info == 'N' or freeling_info == 'S' \
                            or freeling_info == 'F':
                        universal_pos = 'PROPN'
        else:
            universal_pos = 'X'
        poses.append(universal_pos)
    return poses


# Mappings from Freeling tags to Universal tags.

freeling2upos = {"A": "ADJ",
                 "N": "NOUN",
                 "V": "VERB",
                 "Q": "NOUN",
                 "D": "ADV",
                 "E": "PRON",
                 "P": "ADV",
                 "Y": "ADJ",
                 "R": "DET",
                 "C": "CCONJ",
                 "J": "INTJ",
                 "Z": "NUM",
                 "T": "PART",
                 "B": "ADP"}

# Mappings from Penn Treebank tagset to Universal PoS tags
ptb2upos = {"!": "PUNCT",
            "#": "PUNCT",
            "$": "PUNCT",
            "''": "PUNCT",
            "(": "PUNCT",
            ")": "PUNCT",
            ",": "PUNCT",
            "-LRB-": "PUNCT",
            "-RRB-": "PUNCT",
            ".": "PUNCT",
            ":": "PUNCT",
            "?": "PUNCT",
            "CC": "CCONJ",
            "CD": "NUM",
            "CD|RB": "X",
            "DT": "DET",
            "DT.": "DET",
            "EX": "DET",
            "FW": "X",
            "IN": "ADP",
            "IN|RP": "ADP",
            "JJ": "ADJ",
            "JJR": "ADJ",
            "JJRJR": "ADJ",
            "JJS": "ADJ",
            "JJ|RB": "ADJ",
            "JJ|VBG": "ADJ",
            "LS": "X",
            "MD": "AUX",
            "NN": "NOUN",
            "NNP": "PROPN",
            "NNPS": "PROPN",
            "NNS": "NOUN",
            "NN|NNS": "NOUN",
            "NN|SYM": "NOUN",
            "NN|VBG": "NOUN",
            "NP": "NOUN",
            "PDT": "DET",
            "POS": "PART",
            "PRP": "PRON",
            "PRP$": "PRON",
            "PRP|VBP": "PRON",
            "PRT": "PART",
            "RB": "ADV",
            "RBR": "ADV",
            "RBS": "ADV",
            "RB|RP": "ADV",
            "RB|VBG": "ADV",
            "RN": "X",
            "RP": "PART",
            "SYM": "SYM",
            "TO": "PART",
            "UH": "INTJ",
            "VB": "VERB",
            "VBD": "VERB",
            "VBD|VBN": "VERB",
            "VBG": "VERB",
            "VBG|NN": "VERB",
            "VBN": "VERB",
            "VBP": "VERB",
            "VBP|TO": "VERB",
            "VBZ": "VERB",
            "VP": "VERB",
            "V": "VERB",
            "WDT": "DET",
            "WH": "X",
            "WP": "PRON",
            "WP$": "PRON",
            "WRB": "ADV",
            "``": "PUNCT"}
