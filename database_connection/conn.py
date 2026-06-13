import psycopg
from dotenv import load_dotenv
import os

load_dotenv()

def make_connection():
    user = os.getenv("DBUSER")
    passwd = os.getenv("DBPASSWORD")
    host = os.getenv("DBHOST")
    dbname = os.getenv("DBNAME")

    try:
        return psycopg.connect(f"dbname={dbname} user={user} host={host} password={passwd}")
    except:
        return False