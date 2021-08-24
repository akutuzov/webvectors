# webvectors
_Webvectors_ is a toolkit to serve vector semantic models (particularly, prediction-based word embeddings, as in _word2vec_ or _ELMo_) over the web, making it easy to demonstrate their abilities to general public. 
It requires Python >= 3.6, and uses _Flask_, _Gensim_ and _simple_elmo_ under the hood.

Working demos:
<ul>
<li>https://rusvectores.org (for Russian)</li>
<li>http://vectors.nlpl.eu/explore/embeddings/ (for English and Norwegian)</li>
</ul>

The service can be either integrated into _Apache_ web server as a WSGI application or run as a standalone server using _Gunicorn_ (we recommend the latter option).

![Logo](https://rusvectores.org/data/images/associates_rus.png/)

## Brief installation instructions

0. Clone WebVectors git repository (_git clone https://github.com/akutuzov/webvectors.git_) into a directory acessible by your web server.
1. Install _Apache_ for Apache integration or _Gunicorn_ for standalone server.
2. Install all the Python requirements (_pip3 install -r requirements.txt_)
3. If you want to use PoS tagging for user queries, install [UDPipe](https://ufal.mff.cuni.cz/udpipe), [Stanford CoreNLP](https://stanfordnlp.github.io/CoreNLP/), [Freeling](http://nlp.lsi.upc.edu/freeling/) or other PoS-tagger of your choice.
4. Configure the files:

### For Apache installation variant

Add the following line to Apache configuration file:

`WSGIScriptAlias /WEBNAME "PATH/syn.wsgi"`,
where **WEBNAME** is the alias for your service relative to the server root (webvectors for `http://example.com/webvectors`), and **PATH** is your filesystem path to the _WebVectors_ directory.

### For all installation variants

In all `*.wsgi` and `*.py` files in your _WebVectors_ directory, replace `webvectors.cfg` in the string
`config.read('webvectors.cfg')`
with the absolute path to the `webvectors.cfg` file.

Set up your service using the configuration file `webvectors.cfg`.
Most important settings are:
<ul>
<li> `root` - absolute path to your _WebVectors_ directory (**NB: end it with a slash!**)</li>
<li> `temp` - absolute path to your temporary files directory </li>
<li> `font` - absolute path to a TTF font you want to use for plots (otherwise, the default system font will be used) </li>
<li> `detect_tag` - whether to use automatic PoS tagging </li>
<li> `default_search` - URL of search engine to use on individual word pages (for example, https://duckduckgo.com/?q=) </li></ul>

**Tags**

Models can use arbitrary tags assigned to words (for example, part-of-speech tags, as in _boot_NOUN_). If your models are trained on words with tags, you should switch this on in `webvectors.cfg` (`use_tags` variable).
Then, _WebVectors_ will allow users to filter their queries by tags. You also should specify the list of allowed tags (`tags_list` variable in `webvectors.cfg`) and the list of tags which will be shown to the user (`tags.tsv` file).

**Models daemon**

_WebVectors_ uses a daemon, which runs in the background and actually processes all embedding-related tasks. It can also run on a different machine, if you want. Thus, in `webvectors.cfg` you should specify `host` and `port` that this daemon will listen at.
After that, start the actual daemon script `word2vec_server.py`. It will load the models and open a listening socket. This daemon must be active permanently, so you may want to launch it using _screen_ or something like this.

**Models**

The list of models you want to use is defined in the file `models.tsv`. It consists of tab-separated fields:
<ul>
<li> model identifier </li>
<li> model description </li>
<li> path to model </li>
<li> identifier of localized model name </li>
<li> is the model default or not </li>
<li> does the model contain PoS tags</li>
<li> training algorithm of the model (word2vec/fastText/etc)</li>
<li> size of the training corpus in words</li>
<li> language of the model </li>
</ul>

Model identifier will be used as the name for checkboxes in the web pages, and it is also important that in the `strings.csv` file the same identifier is used when denoting model names. Language of the model is used as an argument passed to the lemmatizer function, it is a simple string with the name of the language (e.g. "english", "russian", "french").

Models can currently be in 4 formats:
<ul>
<li> plain text _word2vec_ models (ends with `.vec`); </li>
<li> binary _word2vec_ models (ends with `.bin`); </li>
<li> Gensim format _word2vec_ models (ends with `.model`); </li>
<li> Gensim format _fastText_ models (ends with `.model`).</li>
</ul>

_WebVectors_ will automatically detect models format and load all of them into memory. The users will be able to choose among loaded models.

**Localization**

_WebVectors_ uses the `strings.csv` file as the source of localized strings. It is a comma-separated file with 3 fields:
<ul><li> identifier </li>
<li> string in language 1 </li>
<li> string in language 2 </li></ul>

By default, language 1 is English and language 2 is Russian. This can be changed in `webvectors.cfg`.

**Templates**

Actual web pages shown to user are defined in the files `templates/*.html`.
Tune them as you wish. The main menu is defined at `base.html`.

**Statis files**

If your application does not find the static files (bootstrap and js scripts), edit the variable `static_url_path` in `run_syn.py`. You should put there the absolute path to the `data` folder.

**Query hints**

If you want query hints to work, do not forget to compile your own list of hints (JSON format). Example of such a list is given in `data/example_vocab.json`.
Real URL of this list should be stated in `data/hint.js`.

**Running WebVectors**

Once you have modified all the settings according to your workflow, made sure the templates are OK for you, and launched the models daemon, you are ready to actually start the service.
If you use _Apache_ integration, simply restart/reload _Apache_.
If you prefer the standalone option, execute the following command in the root directory of the project:

`gunicorn run_syn:app_syn -b address:port`

where _address_ is the address on which the service should be active (can be localhost), and _port_ is, well, port to listen (for example, 9999).

**Support for contextualized embeddings**
You can turn on support for contextualized embedding models (currently [ELMo](https://allennlp.org/elmo) is supported). In order to do that:
1. Install [simple_elmo](https://pypi.org/project/simple-elmo/) package

2. Download an ELMo model of your choice (for example, [here](http://vectors.nlpl.eu/repository/)).

3. Create a type-based projection in the `word2vec` format for a limited set of words (for example 10 000), given the ELMo model and a reference corpus. For this, use the [`extract_elmo.py`](https://github.com/akutuzov/webvectors/blob/master/elmo/extract_elmo.py) script we provide:

`python3 extract_elmo.py --input CORPUS --elmo PATH_TO_ELMO --outfile TYPE_EMBEDDING_FILE --vocab WORD_SET_FILE`

It will run the ELMo model over the provided corpus and generate static averaged type embeddings for each word in the word set. They will be used as lexical substitutes.

4. Prepare a frequency dictionary to use with the contextualized visualizations, as a plain-text tab-separated file, where the first column contains words and the second column contains their frequencies in the reference dictionary of your choice. The first line of this file should contain one integer matching the size of the corpus in word tokens.

5. In the `[Token]` section of the `webvectors.cfg` configuration file, switch `use_contextualized` to True and state the paths to your `token_model` (pre-trained ELMo), `type_model` (the type-based projection you created with our script) and `freq_file` which is your frequency dictionary.

6. In the `ref_static_model` field, specify any of your static word embedding models (just its name), which you want to use as the target of hyperlinks from words in the contextualized visualization pages.

7. The page with ELMo lexical substitutes will be available at http://YOUR_ROOT_URL/contextual/


## Contacts

In case of any problems, please feel free to contact us:
<ul><li> andreku@ifi.uio.no (Andrey Kutuzov) </li>
<li> lizaku77@gmail.com (Elizaveta Kuzmenko) </li></ul>

## References
1. http://www.aclweb.org/anthology/E17-3025

2. http://papers.nips.cc/paper/5021-distributed-representations-of-words-and-phrases-and-their-compositionality.pdf

3. http://flask.pocoo.org/

4. http://radimrehurek.com/gensim/

5. http://gunicorn.org/


