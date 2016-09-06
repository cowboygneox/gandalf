import json
import logging

import psycopg2
import tornado.log as tornado_logging
import tornado.testing
import tornado.web
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
        cursor.execute("DROP TABLE IF EXISTS gandalf.users")
        cursor.execute("DROP TABLE IF EXISTS gandalf.deactivated_users")
        conn.commit()

        app = make_app(GandalfConfiguration('localhost:8889', PostgresAdapter(), ['localhost'], mode=WEBSOCKET))
        app.listen(8888)
        return app

    @tornado.testing.gen_test
    async def test_websockets_require_authentication(self):
        class EchoWebSocket(tornado.websocket.WebSocketHandler):
            def open(self):
                self.write_message("Boom")

        background_app = tornado.web.Application([
            (r".*", EchoWebSocket),
        ])
        background_app.listen(8889)

        response = await self.http_client.fetch("http://localhost:8888/users", method="POST", body="username=test&password=test")
        self.assertEqual(response.code, 201)

        response = await self.http_client.fetch("http://localhost:8888/login", method="POST", body="username=test&password=test")
        self.assertEqual(response.code, 200)
        token = json.loads(response.body.decode())["access_token"]

        request = HTTPRequest(url="ws://localhost:8888/")

        conn = await tornado.websocket.websocket_connect(request)
        self.assertEqual(await conn.read_message(), None)
        self.assertEqual(conn.close_code, 401)

        request = HTTPRequest(url="ws://localhost:8888/", headers={"Authorization": "Bearer {}".format(token)})

        conn = await tornado.websocket.websocket_connect(request)
        self.assertEqual(await conn.read_message(), 'Boom')

        conn.close()
        self.assertIsNone(await conn.read_message())

