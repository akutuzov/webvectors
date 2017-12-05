import sys

import ConfigParser
config = ConfigParser.RawConfigParser()
config.read('/home/lizaku/PycharmProjects/webvectors/webvectors.cfg')
root = config.get('Files and directories', 'root')

sys.path.insert(0,root)
from run_syn import app_syn as application
application.debug = True
