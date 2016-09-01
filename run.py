import tornado.ioloop

from app import GandalfConfiguration
from app import PostgresAdapter
import os
from app import make_app

if __name__ == "__main__":
    host = os.getenv("GANDALF_PROXIED_HOST")
    secret = os.getenv("GANDALF_SIGNING_SECRET", "")
    if len(secret) == 0:
        print("GANDALF_SIGNING_SECRET is not set. *DO NOT RUN THIS IN PRODUCTION!!!*")
    app = make_app(GandalfConfiguration(host, PostgresAdapter(), [host], signing_secret=secret))
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()
