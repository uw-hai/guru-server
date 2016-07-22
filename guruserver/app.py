"""app.py"""
import os
from flask import Flask
from flask_mongoengine import MongoEngine

app = Flask(__name__)
app.config.from_object(os.environ['APP_SETTINGS'])
db = MongoEngine(app)

TMP_DIR = os.environ.get('TMP_DIR', '/tmp/guruserver')

from .api import api


if __name__ == '__main__':
    app.run()
