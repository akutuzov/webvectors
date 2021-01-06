#!/usr/bin/env python3
# coding:utf8

"""
this module reads strings.csv, which contains all
the strings, and lets the main app use it
"""

import sys
import csv
from flask import Markup
import configparser

config = configparser.RawConfigParser()
config.read("webvectors.cfg")

root = config.get("Files and directories", "root")
l10nfile = config.get("Files and directories", "l10n")

# open the strings database:
csvfile = open(root + l10nfile, "rU")
acrobat = csv.reader(csvfile, dialect="excel", delimiter=",")

# initialize a dictionary for each language:
language_dicts = {}
langnames = config.get("Languages", "interface_languages").split(",")
header = next(acrobat)
included_columns = []
for langname in langnames:
    language_dicts[langname] = {}
    included_columns.append(header.index(langname))

# read the csvfile, populate language_dicts:
for row in acrobat:
    for i in included_columns:  # range(1, len(row)):
        # Markup() is used to prevent autoescaping in templates
        if sys.version_info[0] < 3:
            language_dicts[header[i]][row[0]] = Markup(row[i])
        else:
            language_dicts[header[i]][row[0]] = Markup(row[i])
