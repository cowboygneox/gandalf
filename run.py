import logging
import os

import tornado.ioloop
import tornado.log as tornado_logging

from app import GandalfConfiguration
from app import PostgresAdapter
from app import WEBSOCKET
from app import make_app
from app.config import HTTP

tornado_logging.access_log.setLevel(logging.DEBUG)
tornado_logging.app_log.setLevel(logging.DEBUG)
tornado_logging.gen_log.setLevel(logging.DEBUG)

if __name__ == "__main__":
    host = os.getenv("GANDALF_PROXIED_HOST")
    secret = os.getenv("GANDALF_SIGNING_SECRET", "")

    if os.getenv("GANDALF_WEBSOCKET_MODE", "False").lower() == "true":
        mode = WEBSOCKET
        print("Running in WEBSOCKET mode.")
    else:
        mode = HTTP
        print("Running in HTTP mode.")

    internal_hosts = os.getenv("GANDALF_ALLOWED_HOSTS", "").strip()
    if len(secret) == 0:
        print("GANDALF_SIGNING_SECRET is not set. *DO NOT RUN THIS IN PRODUCTION!!!*")
    app = make_app(GandalfConfiguration(host, PostgresAdapter(), internal_hosts, signing_secret=secret, mode=mode))
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()
