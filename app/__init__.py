import json
import os
import uuid

import redis
import tornado.httpclient
import tornado.ioloop
import tornado.web
from passlib.apps import custom_app_context as pwd_context

from app.config import GandalfConfiguration
from app.db.postgres_adapter import PostgresAdapter


def make_app(config: GandalfConfiguration):
    cache = redis.StrictRedis(host=os.getenv("GANDALF_REDIS_HOST", "localhost"), port=6379)

    def user_authenticated(block):
        def wrapper(self):
            authorization = self.request.headers.get_list('Authorization')
            if len(authorization) == 0:
                self.send_error(401)
            else:
                token = authorization[0].replace("Bearer ", "").strip()
                user = cache.get(token)
                if user:
                    block(self, user)
                else:
                    self.send_error(401)

        return wrapper

    class MainHandler(tornado.web.RequestHandler):
        def __init__(self, application, request, **kwargs):
            super().__init__(application, request, **kwargs)

        @user_authenticated
        @tornado.web.asynchronous
        def get(self, user_id):
            def callback(response):
                self.write(response.body)
                self.add_header("USER_ID", user_id)
                self.finish()

            req = tornado.httpclient.HTTPRequest("http://{}/{}".format(config.proxy_host, self.request.uri))
            client = tornado.httpclient.AsyncHTTPClient()
            client.fetch(req, callback, raise_error=False)

    class LoginHandler(tornado.web.RequestHandler):
        def post(self):
            username = self.get_body_argument("username")
            password = self.get_body_argument("password")

            if username and password:
                user = config.db_adapter.get_user(username)
                if pwd_context.verify(password, user.hashed_password):
                    token = str(uuid.uuid1())
                    cache.set(token, user.user_id)
                    self.write(json.dumps({"access_token": token}))
                    self.set_status(200)
                    self.finish()
                else:
                    self.send_error(401)
            else:
                self.send_error(401)

    class UserHandler(tornado.web.RequestHandler):
        def post(self):
            hostname = self.request.host.split(":")[0]
            if not hostname in config.allowed_hosts:
                self.send_error(401)
            else:
                username = self.get_body_argument("username")
                password = self.get_body_argument("password")

                hashed_password = pwd_context.encrypt(password)

                config.db_adapter.create_user(username, hashed_password)

                self.set_status(201)
                self.finish()

    return tornado.web.Application([
        (r"/login", LoginHandler),
        (r"/create", UserHandler),
        (r".*", MainHandler)
    ])
