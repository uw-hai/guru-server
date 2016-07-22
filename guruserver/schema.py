import datetime

from .app import db


class Policy(db.Document):
    date_modified = db.DateTimeField(default=datetime.datetime.now)
    config = db.DictField()
    histories = db.ListField()
    policy = db.BinaryField()
    pomdp_policy = db.StringField()
    status = db.StringField()
