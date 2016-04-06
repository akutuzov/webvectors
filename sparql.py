#!/usr/bin/python2
# coding: utf-8

from SPARQLWrapper import SPARQLWrapper, JSON
import codecs

import ConfigParser
config = ConfigParser.RawConfigParser()
config.read('webvectors.cfg')

root = config.get('Files and directories', 'root')
cachefile = config.get('Files and directories', 'image_cache')

def getdbpediaimage(query):
    query = query.decode('utf-8')
    query = query.capitalize()

    cache = {}
    data = codecs.open(root + cachefile, 'r', 'utf-8')
    for line in data:
        res = line.strip().split('\t')
        (word, image) = res
        cache[word.strip()] = image.strip()
    data.close()

    if query in cache:
        return cache[query]
    #else:
    #    return None
    sparql = SPARQLWrapper("http://dbpedia.org/sparql")
    sparql.setQuery("""
	SELECT DISTINCT ?e ?pic
	WHERE {
        ?e rdfs:label "%s"@ru .
        ?e <http://dbpedia.org/ontology/thumbnail> ?pic .
            }
    """ % query)

    sparql.setReturnFormat(JSON)
    try:
        results = sparql.query().convert()
    except:
        return None
    if len(results["results"]["bindings"]) > 0:
        image = results["results"]["bindings"][0]["pic"]["value"]
        data = codecs.open(root + cachefile, 'a', 'utf-8')
        data.write(query + '\t' + image + '\n')
        data.close()
        return image
    else:
        return None
