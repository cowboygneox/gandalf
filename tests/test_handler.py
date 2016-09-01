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


def login(block):
    def wrapper(self):
        response = self.fetch("/")
        self.assertEqual(response.code, 401)

        response = self.fetch("/users", method="POST", body="username=test&password=test")
        self.assertEqual(response.code, 201)

        response = self.fetch("/login", method="POST", body="username=test&password=test")
        self.assertEqual(response.code, 200)
        token = json.loads(response.body.decode())["access_token"]

        block(self, token)

    return wrapper


class HandlerTest(tornado.testing.AsyncHTTPTestCase):
    def get_app(self):
        conn = psycopg2.connect(host="localhost", user="postgres")
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS users")
        cursor.execute("DROP TABLE IF EXISTS deactivated_users")
        conn.commit()

        app = make_app(GandalfConfiguration('localhost:8889', PostgresAdapter(), ['localhost']))
        app.listen(8888)
        return app

    def wire_app(self, app):
        background_app = tornado.web.Application([
            (r".*", app),
        ])
        background_app.listen(8889)

    @login
    def test_get_200(self, token):
        test_self = self

        class TestHandler(tornado.web.RequestHandler):
            def get(self):
                test_self.assertIsNotNone(self.request.headers['USER_ID'])
                self.write("this works")

        self.wire_app(TestHandler)

        response = self.fetch("/", headers={"Authorization": "Bearer {}".format(token)})
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body.decode(), "this works")

    @login
    def test_get_400(self, token):
        test_self = self

        class TestHandler(tornado.web.RequestHandler):
            def get(self):
                test_self.assertIsNotNone(self.request.headers['USER_ID'])
                self.set_status(400)
                self.write("the request was missing some parameter")

        self.wire_app(TestHandler)

        response = self.fetch("/", headers={"Authorization": "Bearer {}".format(token)})
        self.assertEqual(response.code, 400)
        self.assertEqual(response.body.decode(), "the request was missing some parameter")

    @login
    def test_get_404(self, token):
        test_self = self

        class TestHandler(tornado.web.RequestHandler):
            def get(self):
                test_self.assertIsNotNone(self.request.headers['USER_ID'])
                self.set_status(404)

        self.wire_app(TestHandler)

        response = self.fetch("/", headers={"Authorization": "Bearer {}".format(token)})
        self.assertEqual(response.code, 404)

    @login
    def test_get_500(self, token):
        test_self = self

        class TestHandler(tornado.web.RequestHandler):
            def get(self):
                test_self.assertIsNotNone(self.request.headers['USER_ID'])
                self.set_status(500)

        self.wire_app(TestHandler)

        response = self.fetch("/", headers={"Authorization": "Bearer {}".format(token)})
        self.assertEqual(response.code, 500)

    @login
    def test_post_200(self, token):
        test_self = self

        class TestHandler(tornado.web.RequestHandler):
            def post(self):
                test_self.assertIsNotNone(self.request.headers['USER_ID'])
                self.write("this works")

        self.wire_app(TestHandler)

        response = self.fetch("/", method="POST", headers={"Authorization": "Bearer {}".format(token)}, body="")
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body.decode(), "this works")

    @login
    def test_post_400(self, token):
        test_self = self

        class TestHandler(tornado.web.RequestHandler):
            def post(self):
                test_self.assertIsNotNone(self.request.headers['USER_ID'])
                self.set_status(400)
                self.write("the request was missing some parameter")

        self.wire_app(TestHandler)

        response = self.fetch("/", method="POST", headers={"Authorization": "Bearer {}".format(token)}, body="")
        self.assertEqual(response.code, 400)
        self.assertEqual(response.body.decode(), "the request was missing some parameter")


    @login
    def test_post_404(self, token):
        test_self = self

        class TestHandler(tornado.web.RequestHandler):
            def post(self):
                test_self.assertIsNotNone(self.request.headers['USER_ID'])
                self.set_status(404)

        self.wire_app(TestHandler)

        response = self.fetch("/", method="POST", headers={"Authorization": "Bearer {}".format(token)}, body="")
        self.assertEqual(response.code, 404)

    @login
    def test_post_500(self, token):
        test_self = self

        class TestHandler(tornado.web.RequestHandler):
            def post(self):
                test_self.assertIsNotNone(self.request.headers['USER_ID'])
                self.set_status(500)

        self.wire_app(TestHandler)

        response = self.fetch("/", method="POST", headers={"Authorization": "Bearer {}".format(token)}, body="")
        self.assertEqual(response.code, 500)

    @login
    def test_get_propagates_headers(self, token):
        test_self = self

        class TestHandler(tornado.web.RequestHandler):
            def post(self):
                test_self.assertIsNotNone(self.request.headers['USER_ID'])
                test_self.assertEqual(self.request.headers['A_HEADER'], "a_value")
                self.add_header("SOME_HEADER", "some_value")
                self.set_status(200)

        self.wire_app(TestHandler)

        response = self.fetch("/", method="POST", headers={"Authorization": "Bearer {}".format(token), "A_HEADER": "a_value"}, body="")
        self.assertEqual(response.code, 200)
        self.assertEqual(response.headers['SOME_HEADER'], "some_value")
