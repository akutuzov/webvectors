#!/usr/bin/python2.7
# -!- coding: utf-8 -!-

import codecs, subprocess

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
        mystem_pos = 'A'
    elif freeling_pos == 'N':
        mystem_pos = 'S'
    elif freeling_pos == 'V':
        mystem_pos = 'V'
    elif freeling_pos == 'Q':
        mystem_pos = 'S'
    elif freeling_pos == 'D':
        mystem_pos = 'ADV'
    elif freeling_pos == 'E':
        mystem_pos = 'SPRO'
    elif freeling_pos == 'P':
        mystem_pos = 'ADVPRO'
    elif freeling_pos == 'Y':
        mystem_pos = 'ANUM'
    elif freeling_pos == 'R':
        mystem_pos = 'APRO'
    elif freeling_pos == 'C':
        mystem_pos = 'CONJ'
    elif freeling_pos == 'J':
        mystem_pos = 'INTJ'
    elif freeling_pos == 'Z':
        mystem_pos = 'NUM'
    elif freeling_pos == 'T':
        mystem_pos = 'PART'
    elif freeling_pos == 'B':
        mystem_pos = 'PR'
    else:
        mystem_pos = 'UNKN'
    return mystem_pos
