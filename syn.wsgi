import sys

root = 'YOUR ROOT DIRECTORY HERE' # Directory where WebVectores resides

sys.path.insert(0,root)
from run_syn import app_syn as application
application.debug = True