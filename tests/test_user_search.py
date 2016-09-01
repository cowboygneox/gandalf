import logging

import psycopg2
import tornado.log as tornado_logging
import tornado.testing
import json
import uuid

from app import GandalfConfiguration
from app.db.postgres_adapter import PostgresAdapter
from run import make_app

tornado_logging.access_log.setLevel(logging.DEBUG)
tornado_logging.app_log.setLevel(logging.DEBUG)
tornado_logging.gen_log.setLevel(logging.DEBUG)


class UserSearchTest(tornado.testing.AsyncHTTPTestCase):
    def get_app(self):
        conn = psycopg2.connect(host="localhost", user="postgres")
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS users")
        conn.commit()

        app = make_app(GandalfConfiguration('localhost:8889', PostgresAdapter(), ['localhost']))
        app.listen(8888)
        return app

    def test_search_for_single_user_id(self):
        response = self.fetch("/users/search", method="POST", body="user_id=asdf")
        self.assertEqual(response.code, 200)
        json_payload = {
            "errors": [{
                "message": "Unable to find user_id",
                "key": "user_id",
                "value": "asdf"
            }]
        }
        self.assertEqual(json.loads(response.body.decode()), json_payload)

        response = self.fetch("/users", method="POST", body="username=test&password=test")
        self.assertEqual(response.code, 201)
        user_id = response.headers['USER_ID']

        response = self.fetch("/users/search", method="POST", body="user_id={}".format(user_id))
        self.assertEqual(response.code, 200)
        json_payload = {
            "results": [{
                "username": "test",
                "user_id": user_id
            }]
        }
        self.assertEqual(json.loads(response.body.decode()), json_payload)

    def test_search_for_many_user_ids(self):
        user_id1 = str(uuid.uuid1())
        user_id2 = str(uuid.uuid1())
        user_id3 = str(uuid.uuid1())

        response = self.fetch("/users/search", method="POST",
                              body="user_id={}&user_id={}&user_id={}".format(user_id1, user_id2, user_id3))
        self.assertEqual(response.code, 200)
        json_payload = {
            "errors": [{
                "message": "Unable to find user_id",
                "key": "user_id",
                "value": user_id1
            }, {
                "message": "Unable to find user_id",
                "key": "user_id",
                "value": user_id2
            }, {
                "message": "Unable to find user_id",
                "key": "user_id",
                "value": user_id3
            }]
        }
        self.assertEqual(json.loads(response.body.decode()), json_payload)

        response = self.fetch("/users", method="POST", body="username=test&password=test")
        self.assertEqual(response.code, 201)
        user_id1 = response.headers['USER_ID']

        response = self.fetch("/users/search", method="POST",
                              body="user_id={}&user_id={}&user_id={}".format(user_id1, user_id2, user_id3))
        self.assertEqual(response.code, 200)
        json_payload = {
            "results": [{
                "username": "test",
                "user_id": user_id1
            }],
            "errors": [{
                "message": "Unable to find user_id",
                "key": "user_id",
                "value": user_id2
            }, {
                "message": "Unable to find user_id",
                "key": "user_id",
                "value": user_id3
            }]
        }
        self.assertEqual(json.loads(response.body.decode()), json_payload)

        response = self.fetch("/users", method="POST", body="username=test2&password=test2")
        self.assertEqual(response.code, 201)
        user_id2 = response.headers['USER_ID']

        response = self.fetch("/users/search", method="POST",
                              body="user_id={}&user_id={}&user_id={}".format(user_id1, user_id2, user_id3))
        self.assertEqual(response.code, 200)
        json_payload = {
            "results": [{
                "username": "test",
                "user_id": user_id1
            }, {
                "username": "test2",
                "user_id": user_id2
            }],
            "errors": [{
                "message": "Unable to find user_id",
                "key": "user_id",
                "value": user_id3
            }]
        }
        self.assertEqual(json.loads(response.body.decode()), json_payload)

        response = self.fetch("/users", method="POST", body="username=test3&password=test3")
        self.assertEqual(response.code, 201)
        user_id3 = response.headers['USER_ID']

        response = self.fetch("/users/search", method="POST",
                              body="user_id={}&user_id={}&user_id={}".format(user_id1, user_id2, user_id3))
        self.assertEqual(response.code, 200)
        json_payload = {
            "results": [{
                "username": "test",
                "user_id": user_id1
            }, {
                "username": "test2",
                "user_id": user_id2
            }, {
                "username": "test3",
                "user_id": user_id3
            }]
        }
        self.assertEqual(json.loads(response.body.decode()), json_payload)
