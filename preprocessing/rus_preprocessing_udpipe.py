#!/usr/bin/env python
# coding: utf-8

from __future__ import print_function
from __future__ import division
from future import standard_library
import sys
import os
import wget
from ufal.udpipe import Model, Pipeline

'''
Этот скрипт принимает на вход необработанный русский текст (одно предложение на строку или один абзац на строку).
Он токенизируется, лемматизируется и размечается по частям речи с использованием UDPipe.
На выход подаётся последовательность разделенных пробелами лемм с частями речи ("зеленый_NOUN трамвай_NOUN").
Их можно непосредственно использовать в моделях с RusVectōrēs (http://rusvectores.org).

Примеры запуска:
echo 'Мама мыла раму.' | python3 rus_preprocessing_udpipe.py
zcat large_corpus.txt.gz | python3 rus_preprocessing_udpipe.py | gzip > processed_corpus.txt.gz
'''


def tag_ud(pipeline, text='Текст нужно передать функции в виде строки!', pos=True):
    # если частеречные тэги не нужны (например, их нет в модели), выставьте pos=False
    # в этом случае на выход будут поданы только леммы

    # обрабатываем текст, получаем результат в формате conllu:
    processed = pipeline.process(text)

    # пропускаем строки со служебной информацией:
    content = [l for l in processed.split('\n') if not l.startswith('#')]

    # извлекаем из обработанного текста лемму и тэг
    tagged = [w.split('\t')[2].lower() + '_' + w.split('\t')[3] for w in content if w]

    tagged_propn = []
    propn = []
    for t in tagged:
        if t.endswith('PROPN'):
            if propn:
                propn.append(t)
            else:
                propn = [t]
        elif t.endswith('PUNCT'):
            propn = []
            continue  # я здесь пропускаю знаки препинания, но вы можете поступить по-другому
        else:
            if len(propn) > 1:
                name = '::'.join([x.split('_')[0] for x in propn]) + '_PROPN'
                tagged_propn.append(name)
            elif len(propn) == 1:
                tagged_propn.append(propn[0])
            tagged_propn.append(t)
            propn = []
    if not pos:
        tagged_propn = [t.split('_')[0] for t in tagged_propn]
    return tagged_propn


standard_library.install_aliases()

udpipe_model_url = 'http://rusvectores.org/static/models/udpipe_syntagrus.model'  # URL of the UDPipe model
udpipe_filename = udpipe_model_url.split('/')[-1]

if not os.path.isfile(udpipe_filename):
    print('UDPipe model not found. Downloading...', file=sys.stderr)
    wget.download(udpipe_model_url)

print('Loading the model...', file=sys.stderr)
model = Model.load(udpipe_filename)
process_pipeline = Pipeline(model, 'tokenize', Pipeline.DEFAULT, Pipeline.DEFAULT, 'conllu')

print('Processing input...', file=sys.stderr)
for line in sys.stdin:
    res = line.strip()
    output = tag_ud(process_pipeline, text=res)
    print(' '.join(output))
