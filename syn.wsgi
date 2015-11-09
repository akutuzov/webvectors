import sys

root = '/home/sites/ling.go.mail.ru/quazy-synonyms'

sys.path.insert(0,root)
from run_syn import app_syn as application
application.debug = True