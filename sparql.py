#!/usr/bin/python2
# coding: utf-8

from SPARQLWrapper import SPARQLWrapper, JSON
import codecs

root = '/home/sites/ling.go.mail.ru/quazy-synonyms/'

def getdbpediaimage(query):
    query = query.decode('utf-8')
    query = query.capitalize()
    
    cache = {}
    data = codecs.open(root+'images_cache.csv','r','utf-8')
    for line in data:
	res = line.strip().split('\t')
	(word,image) = res
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
    results = sparql.query().convert()
    if len(results["results"]["bindings"]) > 0:
	image = results["results"]["bindings"][0]["pic"]["value"]
	image = image.split('?')[0]
	data = codecs.open(root+'images_cache.csv','a','utf-8')
	data.write(query+'\t'+image+'\n')
	data.close()
	return image
    else:
	return None
