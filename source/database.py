import os
import mysql.connector
import sqlite3
try:
        conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="rootme",
        database="Voidlocker"
        )

        print("Connected to MySQL!")

except Exception as e:
        print("Error:", e)


cursor = conn.cursor()
actions = {
        'select':'select * from table where'
}

def db_execute(action,value):

        cursor.execute("SHOW TABLES")

        for table in cursor:
                print(table)



BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "..", "db", "store.db")
DB_PATH = os.path.abspath(DB_PATH)
cx = sqlite3.connect(DB_PATH, check_same_thread=False)
sqlite = cx.cursor()

def local_db_execute(action,value):
        sqlite.execute()
        cx.commit()