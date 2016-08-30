import redis
import tornado.httpclient
import tornado.ioloop
import tornado.web


def make_app(proxy_host):
    def with_authentication(block):
        def wrapper(self):
            authorization = self.request.headers.get_list('Authorization')
            if authorization == []:
                self.send_error(401)
            else:
                block(self)

        return wrapper

    class MainHandler(tornado.web.RequestHandler):
        def __init__(self, application, request, **kwargs):
            super().__init__(application, request, **kwargs)
            self.redis = redis.StrictRedis(host='localhost', port=6379)

        @with_authentication
        @tornado.web.asynchronous
        def get(self):
            def callback(response):
                self.write(response.body)
                self.redis.set(response.body, "cached")
                self.finish()

            req = tornado.httpclient.HTTPRequest("http://{}/{}".format(proxy_host, self.request.uri))
            client = tornado.httpclient.AsyncHTTPClient()
            client.fetch(req, callback, raise_error=False)

    class LoginHandler(tornado.web.RequestHandler):
        def post(self):
            username = self.get_body_argument("username")
            password = self.get_body_argument("password")

            if username and password:
                self.set_status(200)
                self.finish()
            else:
                self.send_error(401)
                self.finish()

    return tornado.web.Application([
        (r"/login", LoginHandler),
        (r".*", MainHandler)
    ])


if __name__ == "__main__":
    app = make_app('localhost')
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()
