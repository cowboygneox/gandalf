import os

import tornado.httpclient
import tornado.ioloop
import tornado.testing
import tornado.web

from app.run import make_app


class TestHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("this works")


class HandlerTest(tornado.testing.AsyncHTTPTestCase):
    def get_app(self):
        app = make_app('localhost:8889')
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

        response = self.fetch("/login", method="POST", body="username=test&password=test")
        self.assertEqual(response.code, 200)

        response = self.fetch("/", headers={"Authorization": "Bearer 1234"})
        self.assertEqual(response.code, 200)