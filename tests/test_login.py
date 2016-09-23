import json
import logging

import psycopg2
import tornado.log as tornado_logging
import tornado.testing

from app import GandalfConfiguration
from app.db.postgres_adapter import PostgresAdapter
from run import make_app

tornado_logging.access_log.setLevel(logging.DEBUG)
tornado_logging.app_log.setLevel(logging.DEBUG)
tornado_logging.gen_log.setLevel(logging.DEBUG)


class LoginTest(tornado.testing.AsyncHTTPTestCase):
    def get_app(self):
        conn = psycopg2.connect(host="localhost", user="postgres")
        cursor = conn.cursor()
        cursor.execute("DROP SCHEMA IF EXISTS gandalf CASCADE")
        conn.commit()

        app = make_app(GandalfConfiguration('localhost:8889', PostgresAdapter(), 'localhost'))
        app.listen(8888)
        return app

    def test_logout(self):
        response = self.fetch("/auth/users", method="POST", body="username=test&password=test")
        self.assertEqual(response.code, 201)

        response = self.fetch("/auth/login", method="POST", body="username=test&password=test")
        self.assertEqual(response.code, 200)

        access_token = json.loads(response.body.decode())['access_token']

        response = self.fetch("/auth/users/me", method="GET", headers={"Authorization": "Bearer {}".format(access_token)})
        self.assertEqual(response.code, 200)

        response = self.fetch("/auth/logout", method="POST", headers={"Authorization": "Bearer {}".format(access_token)}, body="")
        self.assertEqual(response.code, 200)

        response = self.fetch("/auth/users/me", method="GET", headers={"Authorization": "Bearer {}".format(access_token)})
        self.assertEqual(response.code, 401)

    def test_break_login(self):
        response = self.fetch("/auth/users", method="POST", body="username=test&password=test")
        self.assertEqual(response.code, 201)

        def should_fail_login(body):
            self.assertEqual(self.fetch("/auth/login", method="POST", body=body).code, 401)

        def should_succeed_login(body):
            self.assertEqual(self.fetch("/auth/login", method="POST", body=body).code, 200)

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

    def test_multiple_logins_return_same_token(self):
        response = self.fetch("/auth/users", method="POST", body="username=test&password=test")
        self.assertEqual(response.code, 201)

        response = self.fetch("/auth/login", method="POST", body="username=test&password=test")
        token1 = json.loads(response.body.decode())['access_token']

        response = self.fetch("/auth/login", method="POST", body="username=test&password=test")
        token2 = json.loads(response.body.decode())['access_token']

        self.assertEqual(token1, token2)

    def test_bearer_token_is_case_insensitive(self):
        response = self.fetch("/auth/users", method="POST", body="username=test&password=test")
        self.assertEqual(response.code, 201)

        response = self.fetch("/auth/login", method="POST", body="username=test&password=test")
        self.assertEqual(response.code, 200)
        access_token = json.loads(response.body.decode())['access_token']

        def authorization_should_succeed(authorization_value):
            response = self.fetch("/auth/users/me", method="GET", headers={"Authorization": authorization_value})
            self.assertEqual(response.code, 200)

        def authorization_should_fail(authorization_value):
            response = self.fetch("/auth/users/me", method="GET", headers={"Authorization": authorization_value})
            self.assertEqual(response.code, 401)

        authorization_should_succeed("Bearer {}".format(access_token))
        authorization_should_succeed("bearer {}".format(access_token))
        authorization_should_succeed("BEARER {}".format(access_token))
        authorization_should_succeed("bEaReR {}".format(access_token))
        authorization_should_succeed("bEaReR       {}".format(access_token))
        authorization_should_succeed("     bEaReR       {}".format(access_token))
        authorization_should_succeed("bEaReR {}    ".format(access_token))
        authorization_should_succeed("      bEaReR {}    ".format(access_token))
        authorization_should_succeed("      bEaReR        {}    ".format(access_token))

        authorization_should_fail("Bear {}".format(access_token))
        authorization_should_fail("Bear er {}".format(access_token))
        authorization_should_fail("Bearer{}".format(access_token))
        authorization_should_fail("b e a r e r {}".format(access_token))