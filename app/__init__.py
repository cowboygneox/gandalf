import base64
import json
import os
import uuid

import jwt
import redis
import tornado.httpclient
import tornado.ioloop
import tornado.web
import tornado.websocket
from passlib.apps import custom_app_context as pwd_context

from app.config import GandalfConfiguration, WEBSOCKET
from app.db import User
from app.db.postgres_adapter import PostgresAdapter


def make_app(config: GandalfConfiguration):
    cache = redis.StrictRedis(host=os.getenv("GANDALF_REDIS_HOST", "localhost"), port=6379)

    def generate_token(user):
        token_payload = {
            "userId": user.user_id,
            "username": user.username
        }

        return base64.b64encode(jwt.encode(
            token_payload,
            config.signing_secret,
            algorithm='HS256'
        )).decode()

    def decode_token(token):
        return jwt.decode(base64.b64decode(token), key=config.signing_secret)

    def base_authenticated(block, failure_block):
        def wrapper(self):
            authorization = self.request.headers.get_list('Authorization')
            if len(authorization) == 0:
                failure_block(self)
            else:
                try:
                    token = authorization[0].replace("Bearer ", "").strip()
                    cached_user = json.loads(cache.get(token).decode())
                    decoded_user = decode_token(token)
                except Exception as e:
                    failure_block(self)
                    return

                if decoded_user == cached_user:
                    block(self, cached_user)
                else:
                    failure_block(self)

        return wrapper

    def user_authenticated(block):
        def failure(self):
            self.send_error(401)

        return base_authenticated(block, failure)

    def ws_user_authenticated(block):
        def failure(self):
            self.close(code=401)

        return base_authenticated(block, failure)

    def passthru_headers():
        return {
            'Content-Type',
            'Location'
        }

    class RestHandler(tornado.web.RequestHandler):
        def compute_etag(self):
            return None

        def passthru(self, user):
            def callback(response):
                if response.body:
                    self.write(response.body)
                self.set_status(response.code)
                for header_name in filter(lambda header_name: header_name in passthru_headers(), response.headers):
                    self.set_header(header_name, response.headers[header_name])
                self.finish()

            url = "http://{}{}".format(config.proxy_host, self.request.uri)
            method = self.request.method

            if method == "GET" or method == "DELETE":
                body = None
            else:
                body = self.request.body

            headers = {header_name: self.request.headers[header_name] for header_name in self.request.headers}

            headers['USER_ID'] = user['userId']
            headers['USERNAME'] = user['username']

            req = tornado.httpclient.HTTPRequest(url, method=method, body=body, headers=headers)
            client = tornado.httpclient.AsyncHTTPClient()
            client.fetch(req, callback, raise_error=False)

        @user_authenticated
        @tornado.web.asynchronous
        def get(self, user):
            self.passthru(user)

        @user_authenticated
        @tornado.web.asynchronous
        def post(self, user):
            self.passthru(user)

        @user_authenticated
        @tornado.web.asynchronous
        def put(self, user):
            self.passthru(user)

        @user_authenticated
        @tornado.web.asynchronous
        def delete(self, user):
            self.passthru(user)

        @user_authenticated
        @tornado.web.asynchronous
        def patch(self, user):
            self.passthru(user)

    class WebsocketHandler(tornado.websocket.WebSocketHandler):
        def __init__(self, application, request, **kwargs):
            super().__init__(application, request, **kwargs)
            self.active = False
            self.proxy = None

        @ws_user_authenticated
        def open(self, *args, **kwargs):
            url = "ws://{}/{}".format(config.proxy_host, self.request.uri)
            tornado.websocket.websocket_connect(url, callback=self.on_proxy_connected, on_message_callback=self.on_message)

        def on_proxy_connected(self, future):
            self.proxy = future.result()
            self.active = True

        def on_message(self, message):
            if self.active:
                self.write_message(message)

        def on_close(self):
            self.active = False
            if self.proxy:
                self.proxy.close()

    class LoginHandler(tornado.web.RequestHandler):
        def post(self):
            try:
                username = self.get_body_argument("username")
                password = self.get_body_argument("password")

                user = config.db_adapter.get_user(username)

                if pwd_context.verify(password, user.hashed_password):
                    cached_token = cache.get(user.user_id)
                    if cached_token:
                        token = cached_token.decode()
                    else:
                        token = generate_token(user)
                        cache.set(token, json.dumps({"userId": user.user_id, "username": user.username}))
                        cache.set(user.user_id, token)
                    self.write(json.dumps({"access_token": token}))
                    self.set_status(200)
                    self.finish()
                else:
                    self.send_error(401)
            except Exception:
                self.send_error(401)

    def internal_only(block):
        def wrapper(self, *args, **kwargs):
            hostname = self.request.host.split(":")[0]
            if not hostname in config.allowed_hosts:
                self.send_error(404)
            else:
                block(self, *args, **kwargs)

        return wrapper

    class CreateUserHandler(tornado.web.RequestHandler):
        @internal_only
        def post(self):
            username = self.get_body_argument("username")
            password = self.get_body_argument("password")
            user_id = str(uuid.uuid1())

            hashed_password = pwd_context.encrypt(password)

            config.db_adapter.create_user(user_id, username, hashed_password)

            self.set_status(201)
            self.add_header("USER_ID", user_id)
            self.finish()

    class UserGetHandler(tornado.web.RequestHandler):
        def get_user(self, user_id):
            def payload(user):
                return {
                    "username": user.username,
                    "userId": user.user_id
                }

            users = config.db_adapter.search_for_users_by_id([user_id])

            if len(users) > 0:
                user = users[0]
                self.finish(payload(user))
            else:
                self.send_error(404)

    class MeUserHandler(UserGetHandler):
        @user_authenticated
        def get(self, user):
            self.get_user(user['userId'])

    class UpdateUserHandler(UserGetHandler):
        @internal_only
        def get(self, user_id):
            self.get_user(user_id)

        @internal_only
        def post(self, user_id):
            password = self.get_body_argument("password")

            hashed_password = pwd_context.encrypt(password)

            config.db_adapter.update_user_password(user_id, hashed_password)

            self.set_status(200)
            self.finish()

    class DeactivateUserHandler(tornado.web.RequestHandler):
        @internal_only
        def post(self, user_id):
            token = cache.get(user_id)
            cache.delete(user_id)
            cache.delete(token)

            config.db_adapter.deactivate_user(user_id)

            self.set_status(200)
            self.finish()

    class ReactivateUserHandler(tornado.web.RequestHandler):
        @internal_only
        def post(self, user_id):
            config.db_adapter.reactivate_user(user_id)

            self.set_status(200)
            self.finish()

    class SearchUserHandler(tornado.web.RequestHandler):
        def search_with_user_ids(self, user_ids):
            users = config.db_adapter.search_for_users_by_id(user_ids)

            found_user_ids = [user.user_id for user in users]
            missing_user_ids = list(filter(lambda user_id: user_id not in found_user_ids, user_ids))

            response_payload = {}

            if len(users) > 0:
                def message(user):
                    return {
                        "username": user.username,
                        "userId": user.user_id
                    }

                response_payload['results'] = [message(user) for user in users]

            if len(missing_user_ids) > 0:
                def message(user_id):
                    return {
                        "message": "Unable to find user_id",
                        "key": "user_id",
                        "value": user_id
                    }

                response_payload['errors'] = [message(user_id) for user_id in missing_user_ids]

            self.write(response_payload)
            self.set_status(200)
            self.finish()

        def search_with_usernames(self, usernames):
            users = config.db_adapter.search_for_users_by_username(usernames)

            found_usernames = [user.username for user in users]
            missing_usernames = list(filter(lambda username: username not in found_usernames, usernames))

            response_payload = {}

            if len(users) > 0:
                def message(user):
                    return {
                        "username": user.username,
                        "userId": user.user_id
                    }

                response_payload['results'] = [message(user) for user in users]

            if len(missing_usernames) > 0:
                def message(username):
                    return {
                        "message": "Unable to find username",
                        "key": "username",
                        "value": username
                    }

                response_payload['errors'] = [message(username) for username in missing_usernames]

            self.write(response_payload)
            self.set_status(200)
            self.finish()

        @internal_only
        def post(self):
            user_ids = self.get_body_arguments("user_id")
            usernames = self.get_body_arguments("username")

            if len(user_ids) > 0 and len(usernames) > 0:
                self.set_status(400)
                self.write("Cannot search with both 'user_id' and 'username'. Please choose one.")
                self.finish()
            elif len(user_ids) > 0:
                self.search_with_user_ids(user_ids)
            elif len(usernames) > 0:
                self.search_with_usernames(usernames)
            else:
                self.write({'results': []})
                self.set_status(200)
                self.finish()

    if config.mode == WEBSOCKET:
        handler = WebsocketHandler
    else:
        handler = RestHandler

    return tornado.web.Application([
        (r"/auth/login", LoginHandler),
        (r"/auth/users/search", SearchUserHandler),
        (r"/auth/users/(.*)/deactivate", DeactivateUserHandler),
        (r"/auth/users/(.*)/reactivate", ReactivateUserHandler),
        (r"/auth/users/me", MeUserHandler),
        (r"/auth/users/(.*)", UpdateUserHandler),
        (r"/auth/users", CreateUserHandler),
        (r".*", handler)
    ])
