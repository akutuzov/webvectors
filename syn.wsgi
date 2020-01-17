import sys

import configparser
config = configparser.RawConfigParser()
config.read('webvectors.cfg')
root = config.get('Files and directories', 'root')

sys.path.insert(0, root)
from run_syn import app_syn as application
application.debug = True
