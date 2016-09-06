import os
import uuid

import psycopg2

from app.db import DBAdapter, User


class PostgresAdapter(DBAdapter):
    @staticmethod
    def _new_connection():
        host = os.getenv("GANDALF_POSTGRES_HOST", "localhost")
        port = os.getenv("GANDALF_POSTGRES_PORT", "5432")
        database = os.getenv("GANDALF_POSTGRES_DB", None)
        user = os.getenv("GANDALF_POSTGRES_USER", "postgres")
        password = os.getenv("GANDALF_POSTGRES_PASSWORD", "postgres")
        return psycopg2.connect(host=host, port=port, user=user, password=password, database=database)

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
            "CREATE TABLE IF NOT EXISTS users ("
            "  user_id TEXT PRIMARY KEY,"
            "  username TEXT UNIQUE,"
            "  password TEXT"
            ")"
        )
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS deactivated_users ("
            "  user_id TEXT PRIMARY KEY,"
            "  username TEXT UNIQUE,"
            "  password TEXT"
            ")"
        )
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

    def deactivate_user(self, user_id):
        conn = self._new_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO deactivated_users (user_id, username, password)"
                       "SELECT user_id, username, password FROM users WHERE user_id = %s", [user_id])
        cursor.execute("DELETE FROM users WHERE user_id = %s", [user_id]),
        conn.commit()

    def reactivate_user(self, user_id):
        conn = self._new_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (user_id, username, password)"
                       "SELECT user_id, username, password FROM deactivated_users WHERE user_id = %s", [user_id])
        cursor.execute("DELETE FROM deactivated_users WHERE user_id = %s", [user_id]),
        conn.commit()
