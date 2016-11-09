import psycopg2
import tornado.testing

from app import GandalfConfiguration
from app import PostgresAdapter
from app import make_app


class HealthTest(tornado.testing.AsyncHTTPTestCase):
    def get_app(self):
        conn = psycopg2.connect(host="localhost", user="postgres")
        cursor = conn.cursor()
        cursor.execute("DROP SCHEMA IF EXISTS gandalf CASCADE")
        conn.commit()

        app = make_app(GandalfConfiguration('localhost:8889', PostgresAdapter(), 'localhost'))
        app.listen(8888)
        return app

    def test_live(self):
        response = self.fetch("/auth/live", method="GET")
        self.assertEqual(response.body, b'OK')
        self.assertEqual(response.code, 200)

    def test_ready(self):
        response = self.fetch("/auth/ready", method="GET")
        self.assertEqual(response.body, b'OK')
        self.assertEqual(response.code, 200)
