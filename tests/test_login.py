import logging

import psycopg2
import tornado.log as tornado_logging
import tornado.web

from app import GandalfConfiguration
from app.db.postgres_adapter import PostgresAdapter
from run import make_app

tornado_logging.access_log.setLevel(logging.DEBUG)
tornado_logging.app_log.setLevel(logging.DEBUG)
tornado_logging.gen_log.setLevel(logging.DEBUG)


class HandlerTest(tornado.testing.AsyncHTTPTestCase):
    def get_app(self):
        conn = psycopg2.connect(host="localhost", user="postgres")
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS users")
        conn.commit()

        app = make_app(GandalfConfiguration('localhost:8889', PostgresAdapter(), ['localhost']))
        app.listen(8888)
        return app

    def test_break_login(self):
        response = self.fetch("/create", method="POST", body="username=test&password=test")
        self.assertEqual(response.code, 201)

        def should_fail_login(body):
            self.assertEqual(self.fetch("/login", method="POST", body=body).code, 401)

        def should_succeed_login(body):
            self.assertEqual(self.fetch("/login", method="POST", body=body).code, 200)

        should_fail_login("")
        should_fail_login("username=")
        should_fail_login("password=")
        should_fail_login("username=test")
        should_fail_login("password=test")
        should_fail_login("username=&password=")
        should_fail_login("username=test&password=")
        should_fail_login("username=&password=test")
        should_fail_login("username=test2&password=test")
        should_fail_login("username=test&password=test2")

        should_succeed_login("username=test&password=test")
