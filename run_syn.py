#!/usr/bin/env python
# coding: utf-8

from flask import Flask, url_for, send_from_directory
from lang_converter import LangConverter
from webvectors import *
import configparser

config = configparser.RawConfigParser()
config.read('webvectors.cfg')
url = config.get('Other', 'url')

app_syn = Flask(__name__, static_url_path='/data/')


@app_syn.route(url + 'data/<path:query>')
def send_js(query):
    return send_from_directory('data/', query)


app_syn.url_map.converters['lang'] = LangConverter
app_syn.register_blueprint(wvectors)


@app_syn.context_processor
def set_globals():
    return dict(lang=g.lang, strings=g.strings)


def url_for_other_page(page):
    args = request.view_args.copy()
    args['page'] = page
    return url_for(request.endpoint, **args)


app_syn.jinja_env.globals['url_for_other_page'] = url_for_other_page

if __name__ == '__main__':
    app_syn.run()
