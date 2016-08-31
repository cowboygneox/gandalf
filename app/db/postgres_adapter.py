import os
import uuid

import psycopg2

from app.db import DBAdapter, User


class PostgresAdapter(DBAdapter):
    def _new_connection(self):
        return psycopg2.connect(host=os.getenv("GANDALF_POSTGRES_HOST", "localhost"), user="postgres")

    def __init__(self):
        conn = self._new_connection()
        cursor = conn.cursor()
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS users (user_id UUID PRIMARY KEY, username TEXT UNIQUE, password TEXT)")
        conn.commit()

    def get_user(self, username) -> User:
        conn = self._new_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, username, password FROM users WHERE username = %s", [username])
        first = cursor.fetchone()
        if first:
            return User(first[0], first[1], first[2])
        else:
            return None

    def create_user(self, username, password):
        conn = self._new_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (user_id, username, password) VALUES (%s, %s, %s)",
                       [str(uuid.uuid1()), username, password])
        conn.commit()
