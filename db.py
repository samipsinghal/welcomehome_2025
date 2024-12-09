import pymysql
import os

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")    # adjust if needed
DB_PASS = os.getenv("DB_PASS", "root")    # adjust if needed
DB_NAME = os.getenv("DB_NAME", "welcomehome_db")

def get_db_connection():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        db=DB_NAME,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )

def query_db(query, args=None):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, args)
            return cursor.fetchall()
    finally:
        conn.close()

def execute_db(query, args=None):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, args)
            return cursor.lastrowid
    finally:
        conn.close()

