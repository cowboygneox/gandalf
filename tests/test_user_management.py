import json
import logging
import os

import psycopg2
import tornado.httpclient
import tornado.ioloop
import tornado.log as tornado_logging
import tornado.testing
import tornado.web

from app import GandalfConfiguration
from app.db.postgres_adapter import PostgresAdapter
from run import make_app

tornado_logging.access_log.setLevel(logging.DEBUG)
tornado_logging.app_log.setLevel(logging.DEBUG)
tornado_logging.gen_log.setLevel(logging.DEBUG)


class TestHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("this works")


class UserManagementTest(tornado.testing.AsyncHTTPTestCase):
    def get_app(self):
        conn = psycopg2.connect(host="localhost", user="postgres")
        cursor = conn.cursor()
        cursor.execute("DROP SCHEMA IF EXISTS gandalf CASCADE")
        conn.commit()

        app = make_app(GandalfConfiguration('localhost:8889', PostgresAdapter(), ['localhost']))
        app.listen(8888)
        return app

    def test_create_user(self):
        os.putenv("NEXT_HOST", "http://localhost:8889")
        background_app = tornado.web.Application([
            (r".*", TestHandler),
        ])
        background_app.listen(8889)

        response = self.fetch("/")
        self.assertEqual(response.code, 401)

        response = self.fetch("/auth/users", method="POST", body="username=test&password=test")
        self.assertEqual(response.code, 201)

        response = self.fetch("/auth/login", method="POST", body="username=test&password=test")
        self.assertEqual(response.code, 200)
        self.assertIsNotNone(json.loads(response.body.decode())["access_token"])

    def test_change_user_password(self):
        os.putenv("NEXT_HOST", "http://localhost:8889")
        background_app = tornado.web.Application([
            (r".*", TestHandler),
        ])
        background_app.listen(8889)

        response = self.fetch("/")
        self.assertEqual(response.code, 401)

        response = self.fetch("/auth/users", method="POST", body="username=test&password=test")
        self.assertEqual(response.code, 201)
        user_id = response.headers["USER_ID"]
        self.assertIsNotNone(user_id)

        response = self.fetch("/auth/login", method="POST", body="username=test&password=test")
        self.assertEqual(response.code, 200)
        self.assertIsNotNone(json.loads(response.body.decode())["access_token"])

        response = self.fetch("/auth/users/{}".format(user_id), method="POST", body="password=test2")
        self.assertEqual(response.code, 200)

    def test_deactivate_reactivate_user(self):
        os.putenv("NEXT_HOST", "http://localhost:8889")
        background_app = tornado.web.Application([
            (r".*", TestHandler),
        ])
        background_app.listen(8889)

        response = self.fetch("/")
        self.assertEqual(response.code, 401)

        response = self.fetch("/auth/users", method="POST", body="username=test&password=test")
        self.assertEqual(response.code, 201)
        user_id = response.headers["USER_ID"]
        self.assertIsNotNone(user_id)

        response = self.fetch("/auth/login", method="POST", body="username=test&password=test")
        self.assertEqual(response.code, 200)
        token = json.loads(response.body.decode())["access_token"]
        self.assertIsNotNone(token)

        response = self.fetch("/", headers={"Authorization": "Bearer {}".format(token)})
        self.assertEqual(response.code, 200)

        response = self.fetch("/auth/users/{}/deactivate".format(user_id), method="POST", body="")
        self.assertEqual(response.code, 200)

        response = self.fetch("/", headers={"Authorization": "Bearer {}".format(token)})
        self.assertEqual(response.code, 401)

        response = self.fetch("/auth/login", method="POST", body="username=test&password=test")
        self.assertEqual(response.code, 401)

        response = self.fetch("/auth/users/{}/reactivate".format(user_id), method="POST", body="")
        self.assertEqual(response.code, 200)

        response = self.fetch("/auth/login", method="POST", body="username=test&password=test")
        self.assertEqual(response.code, 200)
        token = json.loads(response.body.decode())["access_token"]
        self.assertIsNotNone(token)

        response = self.fetch("/", headers={"Authorization": "Bearer {}".format(token)})
        self.assertEqual(response.code, 200)