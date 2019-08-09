import sqlite3


class Database:

    def __init__(self, sqlite_database_path):
        self.sqlite_database_path = sqlite_database_path

    def connect(self):
        return sqlite3.connect(self.sqlite_database_path)
