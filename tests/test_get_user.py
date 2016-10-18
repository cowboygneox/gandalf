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


class GetUserTest(tornado.testing.AsyncHTTPTestCase):
    def get_app(self):
        conn = psycopg2.connect(host="localhost", user="postgres")
        cursor = conn.cursor()
        cursor.execute("DROP SCHEMA IF EXISTS gandalf CASCADE")
        conn.commit()

        app = make_app(GandalfConfiguration('localhost:8889', PostgresAdapter(), 'localhost'))
        app.listen(8888)
        return app

    def test_get_me(self):
        response = self.fetch("/auth/users", method="POST", body="username=test&password=test")
        self.assertEqual(response.code, 201)
        user_id = response.headers['USER_ID']

        response = self.fetch("/auth/login", method="POST", body="username=test&password=test")
        self.assertEqual(response.code, 200)
        token = json.loads(response.body.decode())["access_token"]

        response = self.fetch("/auth/users/me".format(user_id), method="GET", headers={"Authorization": "Bearer {}".format(token)})
        self.assertEqual(response.code, 200)
        json_payload = {
            "username": "test",
            "userId": user_id
        }
        self.assertEqual(json.loads(response.body.decode()), json_payload)

    def test_get_user(self):
        response = self.fetch("/auth/users", method="POST", body="username=test&password=test")
        self.assertEqual(response.code, 201)
        user_id = response.headers['USER_ID']

        response = self.fetch("/auth/users/{}".format(user_id), method="GET")
        self.assertEqual(response.code, 200)
        json_payload = {
            "username": "test",
            "userId": user_id
        }
        self.assertEqual(json.loads(response.body.decode()), json_payload)

    def test_case_insensitive_get(self):
        # Create McTest
        response = self.fetch("/auth/users", method="POST", body="username=McTest&password=test")
        self.assertEqual(response.code, 201)
        user_id = response.headers['USER_ID']

        # Make sure McTest = mctest
        response = self.fetch("/auth/users/{}".format(user_id), method="GET")
        self.assertEqual(response.code, 200)
        json_payload = {
            "username": "mctest",
            "userId": user_id
        }
        self.assertEqual(json.loads(response.body.decode()), json_payload)

        # Make sure create mcTest already exists
        response = self.fetch("/auth/users", method="POST", body="username=mcTest&password=test")
        self.assertEqual(response.code, 409)