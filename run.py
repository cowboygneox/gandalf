import tornado.ioloop

from app import PostgresAdapter
import os
from app import make_app

if __name__ == "__main__":
    host = os.getenv("GANDALF_PROXIED_HOST")
    app = make_app(host, PostgresAdapter(), [host])
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()
