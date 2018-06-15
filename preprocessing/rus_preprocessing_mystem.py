#!/usr/bin/env python
# coding: utf-8

from __future__ import print_function
from __future__ import division
from future import standard_library
import sys
import requests
from pymystem3 import Mystem

'''
Этот скрипт принимает на вход необработанный русский текст (одно предложение на строку или один абзац на строку).
Он токенизируется, лемматизируется и размечается по частям речи с использованием Mystem.
На выход подаётся последовательность разделенных пробелами лемм с частями речи ("зеленый_NOUN трамвай_NOUN").
Их можно непосредственно использовать в моделях с RusVectōrēs (http://rusvectores.org).

Примеры запуска:
echo 'Мама мыла раму.' | python3 rus_preprocessing_mystem.py
zcat large_corpus.txt.gz | python3 rus_preprocessing_mystem.py | gzip > processed_corpus.txt.gz
'''


def tag_mystem(text='Текст нужно передать функции в виде строки!', mapping=None, postags=True):
    # если частеречные тэги не нужны (например, их нет в модели), выставьте postags=False
    # в этом случае на выход будут поданы только леммы

    processed = m.analyze(text)
    tagged = []
    for w in processed:
        try:
            lemma = w["analysis"][0]["lex"].lower().strip()
            pos = w["analysis"][0]["gr"].split(',')[0]
            pos = pos.split('=')[0].strip()
            if mapping:
                if pos in mapping:
                    pos = mapping[pos]  # здесь мы конвертируем тэги
                else:
                    pos = 'X'  # на случай, если попадется тэг, которого нет в маппинге
            tagged.append(lemma.lower() + '_' + pos)
        except KeyError:
            continue  # я здесь пропускаю знаки препинания, но вы можете поступить по-другому
    if not postags:
        tagged = [t.split('_')[0] for t in tagged]
    return tagged


standard_library.install_aliases()

# Таблица преобразования частеречных тэгов Mystem в тэги UPoS:
mapping_url = \
    'https://raw.githubusercontent.com/akutuzov/universal-pos-tags/4653e8a9154e93fe2f417c7fdb7a357b7d6ce333/ru-rnc.map'

mystem2upos = {}
r = requests.get(mapping_url, stream=True)
for pair in r.text.split('\n'):
    pair = pair.split()
    if len(pair) > 1:
        mystem2upos[pair[0]] = pair[1]

print('Loading the model...', file=sys.stderr)
m = Mystem()

print('Processing input...', file=sys.stderr)
for line in sys.stdin:
    res = line.strip()
    output = tag_mystem(text=res, mapping=mystem2upos)
    print(' '.join(output))
