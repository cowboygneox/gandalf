import json
import logging

import psycopg2
import tornado.log as tornado_logging
import tornado.testing
import tornado.web
import tornado.ioloop
import tornado.websocket
from tornado.httpclient import HTTPRequest

from app import GandalfConfiguration
from app import PostgresAdapter
from app import WEBSOCKET
from app import make_app

tornado_logging.access_log.setLevel(logging.DEBUG)
tornado_logging.app_log.setLevel(logging.DEBUG)
tornado_logging.gen_log.setLevel(logging.DEBUG)


class WebsocketTest(tornado.testing.AsyncHTTPTestCase):
    def get_app(self):
        conn = psycopg2.connect(host="localhost", user="postgres")
        cursor = conn.cursor()
        cursor.execute("DROP SCHEMA IF EXISTS gandalf CASCADE")
        conn.commit()

        app = make_app(GandalfConfiguration('localhost:8889', PostgresAdapter(), 'localhost', mode=WEBSOCKET))
        app.listen(8888)
        return app

    @tornado.testing.gen_test
    async def test_websockets_times_out_without_auth(self):
        testself = self
        user_id = None

        class EchoWebSocket(tornado.websocket.WebSocketHandler):
            def on_message(self, message):
                testself.assertEqual(message, 'USER_ID: %s' % user_id)
                self.write_message("Boom")

        background_app = tornado.web.Application([
            (r".*", EchoWebSocket),
        ])
        background_app.listen(8889)

        response = await self.http_client.fetch("http://localhost:8888/auth/users", method="POST",
                                                body="username=test&password=test")
        self.assertEqual(response.code, 201)
        user_id = response.headers['USER_ID']

        response = await self.http_client.fetch("http://localhost:8888/auth/login", method="POST",
                                                body="username=test&password=test")
        self.assertEqual(response.code, 200)
        token = json.loads(response.body.decode())["access_token"]

        request = HTTPRequest(url="ws://localhost:8888/")

        conn = await tornado.websocket.websocket_connect(request)
        self.assertEqual(await conn.read_message(), None)
        self.assertEqual(conn.close_code, 401)

        request = HTTPRequest(url="ws://localhost:8888/")

        conn = await tornado.websocket.websocket_connect(request)
        conn.write_message("Authorization: Bearer {}".format(token))
        self.assertEqual(await conn.read_message(), 'Boom')

        conn.close()
        self.assertIsNone(await conn.read_message())

    @tornado.testing.gen_test
    async def test_websockets_requires_auth(self):
        testself = self
        user_id = None

        class EchoWebSocket(tornado.websocket.WebSocketHandler):
            def on_message(self, message):
                testself.assertEqual(message, 'USER_ID: %s' % user_id)
                self.write_message("Boom")

        background_app = tornado.web.Application([
            (r".*", EchoWebSocket),
        ])
        background_app.listen(8889)

        response = await self.http_client.fetch("http://localhost:8888/auth/users", method="POST",
                                                body="username=test&password=test")
        self.assertEqual(response.code, 201)
        user_id = response.headers['USER_ID']

        response = await self.http_client.fetch("http://localhost:8888/auth/login", method="POST",
                                                body="username=test&password=test")
        self.assertEqual(response.code, 200)
        token = json.loads(response.body.decode())["access_token"]

        request = HTTPRequest(url="ws://localhost:8888/")

        conn = await tornado.websocket.websocket_connect(request)
        conn.write_message("Authorization: Bearer {}".format(token))
        self.assertEqual(await conn.read_message(), 'Boom')

        conn.close()
        self.assertIsNone(await conn.read_message())

    @tornado.testing.gen_test
    async def test_websockets_closes_on_bogus_auth(self):
        testself = self
        user_id = None

        class EchoWebSocket(tornado.websocket.WebSocketHandler):
            def on_message(self, message):
                testself.assertEqual(message, 'USER_ID: %s' % user_id)
                self.write_message("Boom")

        background_app = tornado.web.Application([
            (r".*", EchoWebSocket),
        ])
        background_app.listen(8889)

        request = HTTPRequest(url="ws://localhost:8888/")

        conn = await tornado.websocket.websocket_connect(request)
        conn.write_message("Authorization: Bearer {}".format("bogus token"))
        self.assertEqual(await conn.read_message(), None)
        self.assertEqual(conn.close_code, 401)

    @tornado.testing.gen_test
    async def test_websockets_closes_when_message_sent_before_auth(self):
        testself = self
        user_id = None

        class EchoWebSocket(tornado.websocket.WebSocketHandler):
            def on_message(self, message):
                testself.assertEqual(message, 'USER_ID: %s' % user_id)
                self.write_message("Boom")

        background_app = tornado.web.Application([
            (r".*", EchoWebSocket),
        ])
        background_app.listen(8889)

        request = HTTPRequest(url="ws://localhost:8888/")

        conn = await tornado.websocket.websocket_connect(request)
        conn.write_message("Sup?")
        self.assertEqual(await conn.read_message(), None)
        self.assertEqual(conn.close_code, 401)

    @tornado.testing.gen_test
    async def test_websockets_allow_two_direct_traffic(self):
        testself = self
        user_id = None

        class EchoWebSocket(tornado.websocket.WebSocketHandler):
            def __init__(self, application, request, **kwargs):
                super().__init__(application, request, **kwargs)
                self.user_id = None

            def on_message(self, message):
                if self.user_id is None:
                    testself.assertEqual(message, 'USER_ID: %s' % user_id)
                    self.user_id = user_id
                elif message == "What does an explosion say?":
                    self.write_message("Boom")
                else:
                    self.write_message("Moo")

        background_app = tornado.web.Application([
            (r".*", EchoWebSocket),
        ])
        background_app.listen(8889)

        response = await self.http_client.fetch("http://localhost:8888/auth/users", method="POST",
                                                body="username=test&password=test")
        self.assertEqual(response.code, 201)
        user_id = response.headers['USER_ID']

        response = await self.http_client.fetch("http://localhost:8888/auth/login", method="POST",
                                                body="username=test&password=test")
        self.assertEqual(response.code, 200)
        token = json.loads(response.body.decode())["access_token"]

        request = HTTPRequest(url="ws://localhost:8888/")

        conn = await tornado.websocket.websocket_connect(request)
        conn.write_message("Authorization: Bearer {}".format(token))

        conn.write_message("What does an explosion say?")
        self.assertEqual(await conn.read_message(), 'Boom')

        conn.write_message("What does a cow say?")
        self.assertEqual(await conn.read_message(), 'Moo')

        conn.close()
        self.assertIsNone(await conn.read_message())

    @tornado.testing.gen_test
    async def test_websockets_block_outgoing_when_deactivated(self):
        class EchoWebSocket(tornado.websocket.WebSocketHandler):
            def on_message(self, message):
                self.write_message("Boom")

        background_app = tornado.web.Application([
            (r".*", EchoWebSocket),
        ])
        background_app.listen(8889)

        response = await self.http_client.fetch("http://localhost:8888/auth/users", method="POST",
                                                body="username=test&password=test")
        self.assertEqual(response.code, 201)
        user_id = response.headers['USER_ID']

        response = await self.http_client.fetch("http://localhost:8888/auth/login", method="POST",
                                                body="username=test&password=test")
        self.assertEqual(response.code, 200)
        token = json.loads(response.body.decode())["access_token"]

        request = HTTPRequest(url="ws://localhost:8888/")

        conn = await tornado.websocket.websocket_connect(request)
        conn.write_message("Authorization: Bearer {}".format(token))
        self.assertEqual(await conn.read_message(), 'Boom')

        response = await self.http_client.fetch("http://localhost:8888/auth/users/%s/deactivate" % user_id, method="POST",
                                                body="")
        self.assertEqual(response.code, 200)

        conn.write_message("What does an explosion say?")
        self.assertEqual(await conn.read_message(), None)
        self.assertEqual(conn.close_code, 401)

    @tornado.testing.gen_test
    async def test_websockets_block_incoming_when_deactivated(self):
        class EchoWebSocket(tornado.websocket.WebSocketHandler):
            def on_message(self, message):
                self.write_message("Boom")

                def delayed_message():
                    self.write_message("Boom2")

                tornado.ioloop.IOLoop.current().call_later(1, delayed_message)

        background_app = tornado.web.Application([
            (r".*", EchoWebSocket),
        ])
        background_app.listen(8889)

        response = await self.http_client.fetch("http://localhost:8888/auth/users", method="POST",
                                                body="username=test&password=test")
        self.assertEqual(response.code, 201)
        user_id = response.headers['USER_ID']

        response = await self.http_client.fetch("http://localhost:8888/auth/login", method="POST",
                                                body="username=test&password=test")
        self.assertEqual(response.code, 200)
        token = json.loads(response.body.decode())["access_token"]

        request = HTTPRequest(url="ws://localhost:8888/")

        conn = await tornado.websocket.websocket_connect(request)
        conn.write_message("Authorization: Bearer {}".format(token))
        self.assertEqual(await conn.read_message(), 'Boom')

        response = await self.http_client.fetch("http://localhost:8888/auth/users/%s/deactivate" % user_id, method="POST",
                                                body="")
        self.assertEqual(response.code, 200)

        self.assertEqual(await conn.read_message(), None)
        self.assertEqual(conn.close_code, 401)
