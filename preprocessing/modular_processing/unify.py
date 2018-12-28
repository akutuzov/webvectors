#!/usr/bin/python
# coding: utf-8

# Produced from https://github.com/TatianaShavrina/taiga/blob/master/tagging_pipeline/unify.py

# Данный файл содержит в себе правила унификации символов юникода
# для сокращения рабочего числа букв в дальнейшей обработке текста
# Данный модуль является обязательным в общей цепочке обработки, и сейчас заточен под русский язык.
# Чтобы адаптировать его для других языков, достаточно адаптировать список alphabet
# под стандартную клавиатуру на этом языке,
# а также проверить, что спецсимволы с точками не входят в состав алфавита этого языка

import sys
import re


# функция использует дефолтную библиотеку
def list_replace(search, replacement, text):
    search = [el for el in search if el in text]
    for c in search:
        text = text.replace(c, replacement)
    return text


def unify_sym(text):  # принимает строку в юникоде
    # сейчас эти правила ориентированы на списки для символов юникода
    # для облегчения понимания используются помимо названий коды 16-ричного юникода
    # предлагается все свести к следующим унифицированным вариантам:
    # для кавычек - "
    # для скобок - () [] {} <> оставляем как есть
    # для дефиса и тире - (минус) предлагаю не различать дефис и тире, как знаки препинания,
    # кроме случаев, где дефис разделяет части слова.
    # для пробела - неразрывный заменяется на обычный,
    # несколько пробелов подряд заменяется на 1,l то же самое для табуляций
    # кавычки 00AB/00BB/2039/203A/201E/201A/201C/201F/2018/201B/201D/2019 --> 0022
    text = list_replace('\u00AB\u00BB\u2039\u203A\u201E\u201A\u201C\u201F\u2018\u201B\u201D\u2019', '\u0022', text)

    # тире заменяется на два дефиса, в окружении пробелов по бокам. 2012/2013/2014/2015/203E/0305/00AF -->  002D
    # короткое тире, среднее тире, длинное тире, цифровое тире, неразрывный дефис, дефис-минус, дефис,
    # макроны и так далее
    text = list_replace('\u2012\u2013\u2014\u2015\u203E\u0305\u00AF', '\u2003\u002D\u002D\u2003', text)

    # дефис 2010/2011--> 002D
    text = list_replace('\u2010\u2011', '\u002D', text)

    # пробел
    # 2000/2001/2002/2004/2005/2006/2007/2008/2009/200A/200B/202F/205F/2060/3000 --> 2003
    text = list_replace('\u2000\u2001\u2002\u2004\u2005\u2006\u2007\u2008\u2009\u200A\u200B\u202F\u205F\u2060\u3000', '\u2002', text)

    # 2 пробела в один и две табуляции в 1
    # здесь оставлены регулярки, т.к. здесь нужно заменять последовательность из 2 символов
    text = re.sub('\u2003\u2003', '\u2003', text)
    text = re.sub('\t\t', '\t', text)

    # остальное - десятичный разделитель, булит, диакритические точки, интерпункт
    # 02CC/0307/0323/2022/2023/2043/204C/204D/2219/25E6/00B7/00D7/22C5/2219/2062  -- > точка
    text = list_replace('\u02CC\u0307\u0323\u2022\u2023\u2043\u204C\u204D\u2219\u25E6\u00B7\u00D7\u22C5\u2219\u2062', '.', text)

    # астериск --> звездочка на 8
    # 2217--> 002A
    text = list_replace('\u2217', '\u002A', text)

    # многоточие --> три точки
    text = list_replace('…', '...', text)

    # тильда к одному виду 2241/224B/2E2F/0483/--> 223D
    text = list_replace('\u2241\u224B\u2E2F\u0483', '\u223D', text)

    # гласные с надстрочными символами, умляуты, диерезис, эсцет
    # сами по себе умляуты, акуты, грависы мы игнорируем, оставляем только буквы с точками
    # - и их переводим в обычные латинские
    # для работы с малыми языками России, такими как удмурсткий, хантыйский, саамский и пр.
    # следует добавить к этому списку расширенную кириллицу
    text = list_replace('\u00C4', 'A', text)  # латинская
    text = list_replace('\u00E4', 'a', text)
    text = list_replace('\u00CB', 'E', text)
    text = list_replace('\u00EB', 'e', text)
    text = list_replace('\u1E26', 'H', text)
    text = list_replace('\u1E27', 'h', text)
    text = list_replace('\u00CF', 'I', text)
    text = list_replace('\u00EF', 'i', text)
    text = list_replace('\u00D6', 'O', text)
    text = list_replace('\u00F6', 'o', text)
    text = list_replace('\u00DC', 'U', text)
    text = list_replace('\u00FC', 'u', text)
    text = list_replace('\u0178', 'Y', text)
    text = list_replace('\u00FF', 'y', text)
    text = list_replace('\u00DF', 's', text)
    text = list_replace('\u1E9E', 'S', text)

    # все валюты
    currencies = list('\u20BD\u0024\u00A3\u20A4\u20AC\u20AA\u2133\u20BE\u00A2\u058F\u0BF9\u20BC\u20A1\u20A0\u20B4\u20A7\u20B0\u20BF\u20A3\u060B\u0E3F\u20A9\u20B4\u20B2\u0192\u20AB\u00A5\u20AD\u20A1\u20BA\u20A6\u20B1\uFDFC\u17DB\u20B9\u20A8\u20B5\u09F3\u20B8\u20AE\u0192'
    )
    # все символы на стандартной клавиатуре:
    alphabet = list('\t\n\r абвгдеёзжийклмнопрстуфхцчшщьыъэюяАБВГДЕЁЗЖИЙКЛМНОПРСТУФХЦЧШЩЬЫЪЭЮЯ,.[]{}()=+-−*&^%$#@!~;:0123456789§/\|"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ ')

    alphabet.append("'")

    allowed = set(currencies + alphabet)

    # по результатам сравнения полученного с алфавитом все остальное выкинуть
    cleaned_text = [sym for sym in text if sym in allowed]
    cleaned_text = ''.join(cleaned_text)

    return cleaned_text


for line in sys.stdin:
    res = line.strip()
    if len(res) > 1 and len(res.split()) > 1:
        print(unify_sym(res))
