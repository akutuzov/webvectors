#!/usr/bin/python
# coding: utf-8
import subprocess
import requests
import json

# Stanford CoreNLP tagging for English (and other languages)
# Demands Stanford Core NLP server running on a defined port
# Start server with something like:
# java -mx4g -cp "*" edu.stanford.nlp.pipeline.StanfordCoreNLPServer --port 9000
port = 9999


def tagword(word):
    corenlp = requests.post(
        'http://localhost:%s/?properties={"annotators": "tokenize, pos,lemma", "outputFormat": "json"}' % port,
        data=word.encode('utf-8')).content
    tagged = json.loads(corenlp, strict=False)
    if len(tagged["sentences"]) < 1:
        return 'Error!'
    poses = []
    for el in tagged["sentences"][0]["tokens"]:
        pos = el["pos"]
        poses.append(ptb2upos[pos])
    return poses


# Freeling lemmatization for Russian
# Queries Freeling service at localhost port 50006
# Converts Freeling tags into Mystem ones

def freeling_lemmatizer(word):
    freeling = subprocess.Popen([u'/usr/local/bin/analyzer_client', u'50006'], stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE)
    tagged = freeling.communicate(word.encode('utf-8').strip())
    tagged = tagged[0].split('\n')[0]
    freeling_pos = tagged.split()[2][0]
    if freeling_pos == 'A':
        universal_pos = 'ADJ'
    elif freeling_pos == 'N':
        universal_pos = 'NOUN'
    elif freeling_pos == 'V':
        universal_pos = 'VERB'
    elif freeling_pos == 'Q':
        universal_pos = 'NOUN'
    elif freeling_pos == 'D':
        universal_pos = 'ADV'
    elif freeling_pos == 'E':
        universal_pos = 'PRON'
    elif freeling_pos == 'P':
        universal_pos = 'ADV'
    elif freeling_pos == 'Y':
        universal_pos = 'ADJ'
    elif freeling_pos == 'R':
        universal_pos = 'DET'
    elif freeling_pos == 'C':
        universal_pos = 'CCONJ'
    elif freeling_pos == 'J':
        universal_pos = 'INTJ'
    elif freeling_pos == 'Z':
        universal_pos = 'NUM'
    elif freeling_pos == 'T':
        universal_pos = 'PART'
    elif freeling_pos == 'B':
        universal_pos = 'ADP'
    else:
        universal_pos = 'X'
    return universal_pos


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
