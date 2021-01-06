#!/usr/bin/env python3
# coding: utf-8

from SPARQLWrapper import SPARQLWrapper, JSON, SPARQLExceptions
import configparser

config = configparser.RawConfigParser()
config.read("webvectors.cfg")

root = config.get("Files and directories", "root")
cachefile = config.get("Files and directories", "image_cache")


def getdbpediaimage(query, cache):
    query = query
    if "::" in query:
        query = " ".join([w.capitalize() for w in query.split("::")])
    else:
        query = query.capitalize()

    if query in cache:
        return cache[query]
    else:
        # return None
        sparql = SPARQLWrapper("http://dbpedia.org/sparql")
        sparql.setQuery(
            """
        SELECT DISTINCT ?e ?pic
        WHERE {
            ?e rdfs:label "%s"@en .
            ?e <http://dbpedia.org/ontology/thumbnail> ?pic .
                }
        """
            % query
        )
        sparql.setReturnFormat(JSON)
        try:
            results = sparql.query().convert()
        except SPARQLExceptions.QueryBadFormed:
            return None
        if len(results["results"]["bindings"]) > 0:
            image = results["results"]["bindings"][0]["pic"]["value"]
            image = image.replace("http://", "https://")
            data = open(root + cachefile, "a")
            data.write(query + "\t" + image + "\n")
            data.close()
            return image
        else:
            data = open(root + cachefile, "a")
            data.write(query + "\tNone\n")
            data.close()
            return None
