#!/usr/bin/python2
# coding: utf-8

from SPARQLWrapper import SPARQLWrapper, JSON
import codecs

import ConfigParser

config = ConfigParser.RawConfigParser()
config.read('webvectors.cfg')

root = config.get('Files and directories', 'root')
cachefile = config.get('Files and directories', 'image_cache')


def getdbpediaimage(query, cache):
    query = query.decode('utf-8')
    query = query.capitalize()

    if query in cache:
        return cache[query]
    else:
        sparql = SPARQLWrapper("http://dbpedia.org/sparql")
        sparql.setQuery("""
        SELECT DISTINCT ?e ?pic
        WHERE {
            ?e rdfs:label "%s"@en .
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
            image = image.replace('http://', 'https://')
            data = codecs.open(root + cachefile, 'a', 'utf-8')
            data.write(query + '\t' + image + '\n')
            data.close()
            return image
        else:
            data = codecs.open(root + cachefile, 'a', 'utf-8')
            data.write(query + '\tNone\n')
            data.close()
            return None
