#!/usr/bin/python
# coding: utf-8
import subprocess


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
