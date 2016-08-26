"""app.py"""
import os
import sys
import logging
from celery import Celery
from flask import Flask
from flask_mongoengine import MongoEngine

def make_celery(app):
    celery = Celery(app.import_name, backend=app.config['CELERY_BACKEND'],
                    broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)
    TaskBase = celery.Task
    class ContextTask(TaskBase):
        abstract = True
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)
    celery.Task = ContextTask
    return celery

app = Flask(__name__)
app.config.from_object(os.environ['APP_SETTINGS'])
db = MongoEngine(app)
celery = make_celery(app)


logging.basicConfig(
    stream=app.config['LOGSTREAM'], level=app.config['LOGLEVEL'])

TMP_DIR = os.environ.get('TMP_DIR', os.path.join('/tmp', 'guruserver'))

from .api import api


if __name__ == '__main__':
    app.run()
