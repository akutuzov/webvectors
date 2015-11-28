#!/usr/bin/python2.7
# -!- coding: utf-8 -!-

import codecs, subprocess


def freeling_lemmatizer(word):
    freeling = subprocess.Popen([u'/usr/local/bin/analyzer_client', u'50005'], stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE)
    tagged = freeling.communicate(word.encode('utf-8').strip())
    tagged = tagged[0].split('\n')[0]
    # print tagged
    freeling_pos = tagged.split()[2][0]
    #print freeling_pos
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
        mystem_pos = 'S-PRO'
    elif freeling_pos == 'P':
        mystem_pos = 'ADV-PRO'
    elif freeling_pos == 'Y':
        mystem_pos = 'A-NUM'
    elif freeling_pos == 'R':
        mystem_pos = 'A-PRO'
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