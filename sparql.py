#!/usr/bin/python2
# coding: utf-8

# Module to download images for words from DBPedia.

from SPARQLWrapper import SPARQLWrapper, JSON
import codecs

root = 'YOUR ROOT DIRECTORY HERE' # Directory where WebVectores resides

def getdbpediaimage(query):
    query = query.decode('utf-8')
    query = query.capitalize()

    cache = {}
    data = codecs.open(root + 'images_cache.csv', 'r', 'utf-8')
    for line in data:
        res = line.strip().split('\t')
        (word, image) = res
        cache[word.strip()] = image.strip()
    data.close()

    if query in cache:
        return cache[query]
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
        image = image.split('?')[0]
        data = codecs.open(root + 'images_cache.csv', 'a', 'utf-8')
        data.write(query + '\t' + image + '\n')
        data.close()
        return image
    else:
        return None
