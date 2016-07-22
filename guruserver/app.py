"""app.py"""
import os
from flask import Flask
from flask_mongoengine import MongoEngine
from guru.research_utils.util import ensure_dir

app = Flask(__name__)
app.config.from_object(os.environ['APP_SETTINGS'])
db = MongoEngine(app)

MODELS_DIR = os.path.join(os.path.dirname(__file__), 'models')
POLICIES_DIR = os.path.join(os.path.dirname(__file__), 'policies')


@app.before_first_request
def create_zmdp_folders():
    ensure_dir(MODELS_DIR)
    ensure_dir(POLICIES_DIR)

from .api import api


if __name__ == '__main__':
    app.run()
