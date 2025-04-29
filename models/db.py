import sqlite3
from flask import g

class Database:
    def __init__(self, db_name="file.db", check_same_thread=False):
       self.connection = sqlite3.connect(db_name, check_same_thread=check_same_thread)
       self.connection.row_factory = sqlite3.Row
    #    self.cursor = self.connection.cursor()

    def execute(self,query, params=()):
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params)
            self.connection.commit()
            return cursor
        except sqlite3.Error as e:
            self.connection.rollback()
            raise 
    
    def fetch_one(self, query, params):
       cursor = self.connection.cursor()
       cursor.execute(query, params)
       return cursor.fetchone()

    def fetch_all(self, query, params=()):
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

    def close(self):
        self.connection.close()
        
# def get_db():
#      if 'db' not in g:
#         g.db = Database()
#      return g.db

# def close_connection(exception):
#       db = g.pop('db', None)
#       if db is not None:
#         db.close()

    
        
       