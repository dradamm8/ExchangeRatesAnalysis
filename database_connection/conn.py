import psycopg
from dotenv import load_dotenv
import os
from sqlalchemy import create_engine

load_dotenv()

def make_psycopg_connection():
    user = os.getenv("DBUSER")
    passwd = os.getenv("DBPASSWORD")
    host = os.getenv("DBHOST")
    dbname = os.getenv("DBNAME")

    try:
        return psycopg.connect(f"dbname={dbname} user={user} host={host} password={passwd}")
    except:
        return False

def make_sqlalchemy_connection():

    
    user = os.getenv("DBUSER")
    passwd = os.getenv("DBPASSWORD")
    host = os.getenv("DBHOST")
    dbname = os.getenv("DBNAME")
    dbport = os.getenv("DBPORT")

    conn_string = f"postgresql+psycopg://{user}:{passwd}@{host}:{dbport}/{dbname}"

    db = create_engine(conn_string)
    conn = db.connect()
    return conn
    try:
        conn = db.connect()
        return conn
    except:
        return False

    
def df_to_db(df):

    conn = make_sqlalchemy_connection()
    if not conn:
        print("Nie udalo sie polaczyc!")
        sys.exit(1)
    else:
        print("Polaczono!")

    df.to_sql("rates", conn, "rates", "append", index_label = "date")

    conn.close()