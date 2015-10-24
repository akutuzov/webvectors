from flask import Flask,request,url_for
from synonyms_main import *
from lang_converter import LangConverter
from flask import g

app_syn = Flask(__name__)

app_syn.url_map.converters['lang'] = LangConverter
app_syn.register_blueprint(synonyms)

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

