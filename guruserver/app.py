"""app.py"""
import os
import sys
import logging
from flask import Flask
from flask_mongoengine import MongoEngine

app = Flask(__name__)
app.config.from_object(os.environ['APP_SETTINGS'])
db = MongoEngine(app)

logging.basicConfig(
    stream=app.config['LOGSTREAM'], level=app.config['LOGLEVEL'])

TMP_DIR = os.environ.get('TMP_DIR', os.path.join('/tmp', 'guruserver'))

from .api import api


if __name__ == '__main__':
    app.run()
