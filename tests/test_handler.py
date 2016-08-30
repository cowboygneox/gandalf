import json
import logging
import os

import psycopg2
import tornado.httpclient
import tornado.ioloop
import tornado.log as tornado_logging
import tornado.testing
import tornado.web

from app.db.postgres_adapter import PostgresAdapter
from run import make_app

tornado_logging.access_log.setLevel(logging.DEBUG)
tornado_logging.app_log.setLevel(logging.DEBUG)
tornado_logging.gen_log.setLevel(logging.DEBUG)


class TestHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("this works")


class HandlerTest(tornado.testing.AsyncHTTPTestCase):
    def get_app(self):
        conn = psycopg2.connect(host="localhost", user="postgres")
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS users")
        conn.commit()

        app = make_app('localhost:8889', PostgresAdapter())
        app.listen(8888)
        return app

    def test_get_200(self):
        os.putenv("NEXT_HOST", "http://localhost:8889")
        background_app = tornado.web.Application([
            (r".*", TestHandler),
        ])
        background_app.listen(8889)

        response = self.fetch("/")
        self.assertEqual(response.code, 401)

        response = self.fetch("/create", method="POST", body="username=test&password=test")
        self.assertEqual(response.code, 201)

        response = self.fetch("/login", method="POST", body="username=test&password=test")
        self.assertEqual(response.code, 200)
        token = json.loads(response.body.decode())["token"]

        response = self.fetch("/", headers={"Authorization": "Bearer {}".format(token)})
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body.decode(), "this works")
        self.assertIsNotNone(response.headers['USER_ID'])
