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
        cursor.execute("CREATE SCHEMA IF NOT EXISTS gandalf")
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS gandalf.users ("
            "  user_id TEXT PRIMARY KEY,"
            "  username TEXT UNIQUE,"
            "  password TEXT"
            ")"
        )
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS gandalf.deactivated_users ("
            "  user_id TEXT PRIMARY KEY,"
            "  username TEXT UNIQUE,"
            "  password TEXT"
            ")"
        )
        conn.commit()

    def get_user(self, username) -> User:
        conn = self._new_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, username, password FROM gandalf.users WHERE username = lower(%s)", [username])
        return self._user_row_mapper(cursor.fetchone())

    def create_user(self, user_id, username, password):
        conn = self._new_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO gandalf.users (user_id, username, password) VALUES (%s, lower(%s), %s)",
                       [user_id, username, password])
        conn.commit()

    def update_user_password(self, user_id, password):
        conn = self._new_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE gandalf.users SET password = %s WHERE user_id = %s", [password, user_id]),
        conn.commit()

    def search_for_users_by_id(self, user_ids):
        conn = self._new_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, username, password FROM gandalf.users WHERE user_id = ANY(%s)", [user_ids]),
        return [self._user_row_mapper(row) for row in cursor]

    def search_for_users_by_username(self, usernames):
        conn = self._new_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, username, password FROM gandalf.users WHERE username = ANY(lower(%s::text)::text[])", [usernames]),
        return [self._user_row_mapper(row) for row in cursor]

    def deactivate_user(self, user_id):
        conn = self._new_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO gandalf.deactivated_users (user_id, username, password)"
                       "SELECT user_id, username, password FROM gandalf.users WHERE user_id = %s", [user_id])
        cursor.execute("DELETE FROM gandalf.users WHERE user_id = %s", [user_id]),
        conn.commit()

    def reactivate_user(self, user_id):
        conn = self._new_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO gandalf.users (user_id, username, password)"
                       "SELECT user_id, username, password FROM gandalf.deactivated_users WHERE user_id = %s", [user_id])
        cursor.execute("DELETE FROM gandalf.deactivated_users WHERE user_id = %s", [user_id]),
        conn.commit()
