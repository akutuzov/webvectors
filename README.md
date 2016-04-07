# webvectors
Toolkit to serve distributional semantic models (particularly, distributed word embeddings, as in word2vec) over the web.

It uses Flask and Gensim under the hood.

Brief installation instructions

1. Install Apache web server.
2. Install Flask and Gensim.
3. If you want to use lemmatization, install Freeling (http://nlp.lsi.upc.edu/freeling/) or other PoS-tagger of your choice.
4. Clone WebVectors code (https://github.com/akutuzov/webvectors) into a directory accessible by your web server
5. Add the following line to Apache configuration file:
WSGIScriptAlias /WEBNAME "PATH/syn.wsgi"
where WEBNAME is the alias for your service relative to the server root (webvectors for http://example.com/webvectors), and PATH is your filesystem path to the WebVectors directory.

In all *.wsgi and *.py files in your WebVectors directory, replace 'webvectors.cfg'in the string
config.read('webvectors.cfg')
with the absolute path to webvectors.cfg file

6. Set up your service using the configuration file webvectors.cfg
Most important settings are:
root - absolute path to your WebVectors directory
temp - absolute path to your temporary files directory
font - absolute path to a TTF font you want to use for plots (otherwise default system font will be used)
lemmatize - whether to use automatic PoS-tagging and lemmatization
default_search - URL of search engine to use on individual word pages (for example, http://go.mail.ru/search?q=%D1%8E%D1%82%D0%B5%D1%80%D0%BD%D1%8B%D0%B9)

7. Tags
Models can use arbitrary tags assigned to words (for example, part-of-speech tags, as in "boot_N"). If your models are trained on words with tags, you should switch this on in webvectors.cfg ("use_tags" variable).
Then, WebVectors will allow users to limit their queries by tags. You also should specify the list of allowed tags ("tags_list" variable in webvectors.cfg) and the default tag ("default_tag").

8. Model daemon
WebVectors uses a daemon, which runs in the background and actually processes all vector tasks. It can also run on a different machine.
Thus, in webvectors.cfg you should specify host and port that this daemon will listen at.
After that, start word2vec_server.py. It will load the models and open a listening socket. This script must run permanently, so you may want to run in using screen, or something like this.

9. Models
The list of models you want to use is defined in the file models.csv. It consists of tab-separated fields:
- model identifier
- model description
- path to model
- identifier of localized model name
- is the model default or not

Models can be of two formats:
- binary word2vec models compressed with gzip (ends with ".bin.gz")
- Gensim format models (ends with ".model")

Webvectors will automatically detect models format and load all of them into memory. The users will be able to choose among loaded models.

10. Localization
WebVectors uses strings.csv file as the source of localized strings. It is a comma-separated file with 3 fields:
- identifier
- string in language 1
- string in language 2

By default, language 1 is Russian and language 2 is English. This can be changed is webvectors.cfg.

11. Templates
Actual web pages shown to user are defined in the files templates/*.html.
Tune them as you want. Main menu is defined at base.html.


References

1. http://papers.nips.cc/paper/5021-distributed-representations-of-words-and-phrases-and-their-compositionality.pdf

2. http://flask.pocoo.org/

3. http://radimrehurek.com/gensim/


