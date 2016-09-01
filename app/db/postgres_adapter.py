import os
import uuid

import psycopg2

from app.db import DBAdapter, User


class PostgresAdapter(DBAdapter):
    @staticmethod
    def _new_connection():
        return psycopg2.connect(host=os.getenv("GANDALF_POSTGRES_HOST", "localhost"), user="postgres")

    @staticmethod
    def _user_row_mapper(row):
        if row:
            return User(row[0], row[1], row[2])
        else:
            return None

    def __init__(self):
        conn = self._new_connection()
        cursor = conn.cursor()
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, username TEXT UNIQUE, password TEXT)")
        conn.commit()

    def get_user(self, username) -> User:
        conn = self._new_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, username, password FROM users WHERE username = %s", [username])
        return self._user_row_mapper(cursor.fetchone())

    def create_user(self, user_id, username, password):
        conn = self._new_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (user_id, username, password) VALUES (%s, %s, %s)",
                       [user_id, username, password])
        conn.commit()

    def update_user_password(self, user_id, password):
        conn = self._new_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET password = %s WHERE user_id = %s", [password, user_id]),
        conn.commit()

    def search_for_users(self, user_ids):
        conn = self._new_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, username, password FROM users WHERE user_id = ANY(%s)", [user_ids]),
        return [self._user_row_mapper(row) for row in cursor]
