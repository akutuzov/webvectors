# webvectors
_Webvectors_ is a toolkit to serve distributional semantic models (particularly, continuous word embeddings, as in _word2vec_) over the web, making it easy to demonstrate models to general public. It uses _Flask_ and _Gensim_ under the hood.

Working demos:
<ul>
<li>http://rusvectores.org (for Russian)</li>
<li>http://ltr.uio.no/semvec (for English and Norwegian)</li>
</ul>

The service can be either integrated into Apache web server as a WSGI application or run as a standalone server using Gunicorn.

## Funny picture
![alt-text](https://github.com/akutuzov/webvectors/blob/master/word2vec.jpg "future with word2vec")
<img src="https://github.com/akutuzov/webvectors/blob/master/word2vec.jpg" alt="future with word2vec" style="width: 100px;"/>

## Brief installation instructions

1. Install _Apache_ for Apache integration or _Gunicorn_ for standalone server.
2. Install _Flask_ and _Gensim_.
3. If you want to use lemmatization, install [Stanford CoreNLP](https://stanfordnlp.github.io/CoreNLP/), [Freeling](http://nlp.lsi.upc.edu/freeling/) or other PoS-tagger of your choice.
4. Clone [WebVectors code](https://github.com/akutuzov/webvectors) into a directory accessible by your web server.
5. Configure the files:

### For Apache installation variant

Add the following line to Apache configuration file:

`WSGIScriptAlias /WEBNAME "PATH/syn.wsgi"`,
where **WEBNAME** is the alias for your service relative to the server root (webvectors for `http://example.com/webvectors`), and **PATH** is your filesystem path to the _WebVectors_ directory.

### For all installation variants

In all `*.wsgi` and `*.py` files in your _WebVectors_ directory, replace `webvectors.cfg` in the string
`config.read('webvectors.cfg')`
with the absolute path to the `webvectors.cfg` file

Set up your service using the configuration file `webvectors.cfg`.
Most important settings are:
<ul>
<li> `root` - absolute path to your _WebVectors_ directory (**NB: end it with a slash!**)</li>
<li> `temp` - absolute path to your temporary files directory </li>
<li> `font` - absolute path to a TTF font you want to use for plots (otherwise default system font will be used) </li>
<li> `lemmatize` - whether to use automatic PoS-tagging and lemmatization </li>
<li> `default_search` - URL of search engine to use on individual word pages (for example, http://go.mail.ru/search?q=) </li></ul>

**Tags**

Models can use arbitrary tags assigned to words (for example, part-of-speech tags, as in _boot_N_). If your models are trained on words with tags, you should switch this on in `webvectors.cfg` (`use_tags` variable).
Then, _WebVectors_ will allow users to limit their queries by tags. You also should specify the list of allowed tags (`tags_list` variable in `webvectors.cfg`) and the default tag (`default_tag`).

**Models daemon**

_WebVectors_ uses a daemon, which runs in the background and actually processes all vector tasks. It can also run on a different machine.
Thus, in `webvectors.cfg` you should specify host and port that this daemon will listen at.
After that, start `word2vec_server.py`. It will load the models and open a listening socket. This script must run permanently, so you may want to launch it using _screen_ or something like this.

**Models**

The list of models you want to use is defined in the file `models.csv`. It consists of tab-separated fields:
<ul>
<li> model identifier </li>
<li> model description </li>
<li> path to model </li>
<li> identifier of localized model name </li>
<li> is the model default or not </li></ul>
Model identifier will be used as the name for checkboxes, and it is also important that in `strings.csv` the same identifier is used when denoting model names.

Models can be of two formats:
<ul><li> binary _word2vec_ models compressed with gzip (ends with `.bin.gz`) </li>
<li> _Gensim_ format models (ends with `.model`) </li></ul>

_Webvectors_ will automatically detect models format and load all of them into memory. The users will be able to choose among loaded models.

**Localization**

_WebVectors_ uses `strings.csv` file as the source of localized strings. It is a comma-separated file with 3 fields:
<ul><li> identifier </li>
<li> string in language 1 </li>
<li> string in language 2 </li></ul>

By default, language 1 is Russian and language 2 is English. This can be changed is `webvectors.cfg`.

**Templates**

Actual web pages shown to user are defined in the files `templates/*.html`.
Tune them as you wish. The main menu is defined at `base.html`.

**Query hints**
If you want query hints to work, do not forget to compile your own list of hints (JSON format). Example of such a list is given in data/example_vocab.json.
Real URL of this list should be stated in data/hint.js.

**Running WebVectors**

Once you have modified all the settings according to your workflow, made sure the templates are OK for you and launched the models daemon, you are ready to actually start the service.
If you use _Apache_ integration, simply restart/reload _Apache_.
If you prefer the standalone option, execute the following command in the root directory of the project:

`gunicorn run_syn:app_syn -b address:port`

where _address_ is the address on which the service should be active (can be localhost), and _port_ is, well, port to listen (for example, 9999).


## Contacts

In case of any problems, please feel free to contact us:
<ul><li> andreku@ifi.uio.no (Andrey Kutuzov) </li>
<li> lizaku77@gmail.com (Elizaveta Kuzmenko) </li></ul>

## References
1. https://www.academia.edu/24306935/WebVectors_a_Toolkit_for_Building_Web_Interfaces_for_Vector_Semantic_Models

2. http://papers.nips.cc/paper/5021-distributed-representations-of-words-and-phrases-and-their-compositionality.pdf

3. http://flask.pocoo.org/

4. http://radimrehurek.com/gensim/

5. http://gunicorn.org/


