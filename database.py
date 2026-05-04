import sqlite3
import json
import os

DB_PATH = os.environ.get("DB_PATH", "bot.db")


class Database:
    def __init__(self):
        self.path = DB_PATH

    def init(self):
        with sqlite3.connect(self.path) as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    joined_at TEXT DEFAULT (datetime('now')),
                    prefs TEXT DEFAULT '{}'
                )
            """)
            con.commit()

    def add_user(self, user_id: int):
        with sqlite3.connect(self.path) as con:
            con.execute(
                "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
                (user_id,)
            )
            con.commit()

    def get_prefs(self, user_id: int) -> dict:
        self.add_user(user_id)
        with sqlite3.connect(self.path) as con:
            row = con.execute(
                "SELECT prefs FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()
        if row:
            try:
                return json.loads(row[0])
            except Exception:
                return {}
        return {}

    def set_pref(self, user_id: int, key: str, value):
        prefs = self.get_prefs(user_id)
        prefs[key] = value
        with sqlite3.connect(self.path) as con:
            con.execute(
                "UPDATE users SET prefs = ? WHERE user_id = ?",
                (json.dumps(prefs), user_id)
            )
            con.commit()

    def get_subscribed_users(self) -> list:
        with sqlite3.connect(self.path) as con:
            rows = con.execute("SELECT user_id, prefs FROM users").fetchall()
        result = []
        for user_id, prefs_str in rows:
            try:
                prefs = json.loads(prefs_str)
            except Exception:
                prefs = {}
            if prefs.get("notify", True):
                result.append(user_id)
        return result
