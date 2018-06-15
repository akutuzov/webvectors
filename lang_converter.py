#!/usr/bin/env python
# coding: utf-8

from werkzeug.routing import BaseConverter, ValidationError
from strings_reader import language_dicts

"""
this module enables delicate control of the URL argument in requests
see this for details:
http://stackoverflow.com/questions/5870188/does-flask-support-regular-expressions-in-its-url-routing
"""


# validate the language in URL & stuff
class LangConverter(BaseConverter):
    def to_python(self, value):
        if value not in language_dicts:
            raise ValidationError()
        return value

    def to_url(self, value):
        return value
