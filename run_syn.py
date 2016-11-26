from flask import Flask, url_for
from lang_converter import LangConverter
from webvectors import *

app_syn = Flask(__name__)

app_syn.url_map.converters['lang'] = LangConverter
app_syn.register_blueprint(wvectors)


@app_syn.context_processor
def set_globals():
    return dict(lang=g.lang, strings=g.strings, other_lang=g.other_lang, languages=g.languages)


def url_for_other_page(page):
    args = request.view_args.copy()
    args['page'] = page
    return url_for(request.endpoint, **args)


app_syn.jinja_env.globals['url_for_other_page'] = url_for_other_page

if __name__ == '__main__':
    app_syn.run()

