import os
import unittest
import redis
import json

from ..app import app
from ..app import db
from ..schema import Policy as PolicyDB

redis_connection = redis.StrictRedis.from_url(os.environ['REDIS_URL'])

quiz = {'name': 'ask', 'quiz_val': 0}
work = {'name': 'ask', 'quiz_val': None}
exp = {'name': 'exp', 'quiz_val': None}
boot = {'name': 'boot', 'quiz_val': None}

# Two finished workers, one unfinished.
history = [
    [{'action': quiz, 'observation': 'r'},
     {'action': exp, 'observation': 'null'},
     {'action': work, 'observation': 'null'},
     {'action': boot, 'observation': 'term'}],
    [{'action': quiz, 'observation': 'r'},
     {'action': quiz, 'observation': 'w'},
     {'action': work, 'observation': 'null'},
     {'action': work, 'observation': 'term'}],
    [{'action': quiz, 'observation': 'r'}],
]


class TestCase(unittest.TestCase):

    def setUp(self):
        PolicyDB.drop_collection()
        redis_connection.flushall()
        self.app = app.test_client()

    def test_api(self):
        with open(os.path.join(os.path.dirname(__file__), 'data', 'config1.json'), 'r') as f:
            data = json.load(f)
            data['histories'] = history[:2]
            rv = self.app.post(
                '/policies', content_type='application/json', data=json.dumps(data))
        self.assertEqual(200, rv.status_code)
        data = json.loads(rv.data)
        self.assertIn('id', data)
        policy_id = data['id']

        rv = self.app.get('/policies/{}'.format(policy_id))
        self.assertEqual(200, rv.status_code)
        data = json.loads(rv.data)
        self.assertIn('policy', data)
        self.assertLess(0, len(data['policy']))

        # Check explores for first worker and assigns work action (base
        # policy).
        query = {'mode': 'rl',
                 'budget_spent': 0,
                 'budget_explore': 100,
                 'history': history[2]}
        rv = self.app.post('/policies/{}'.format(policy_id),
                           content_type='application/json', data=json.dumps(query))
        self.assertEqual(200, rv.status_code)
        data = json.loads(rv.data)
        self.assertIn('action', data)
        self.assertIn('explore', data)
        self.assertDictEqual({'name': 'ask', 'quiz_val': None}, data['action'])
        self.assertTrue(data['explore'])

        # Check is not exploring.
        query = {'mode': 'exploit',
                 'history': history[2]}
        rv = self.app.post('/policies/{}'.format(policy_id),
                           content_type='application/json', data=json.dumps(query))
        self.assertEqual(200, rv.status_code)
        data = json.loads(rv.data)
        self.assertIn('action', data)
        self.assertIn('explore', data)
        self.assertFalse(data['explore'])
