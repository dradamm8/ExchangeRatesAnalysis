import psycopg
from dotenv import load_dotenv
import os
from sqlalchemy import create_engine
import json
import sys
sys.path.append("..")
from ml.ml_utils import *


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
        return
    else:
        print("Polaczono!")

    df.to_sql("helper", conn, schema = "rates", if_exists = "append", index_label = "date")

    conn.close()

    conn = make_psycopg_connection()
    conn.autocommit = True

    cur = conn.cursor()

    cur.execute("""
                MERGE INTO rates.rates r
                USING rates.helper h
                ON r.date = h.date
                WHEN MATCHED THEN DO NOTHING
                WHEN NOT MATCHED THEN INSERT VALUES 
                    (h.date, h.usd, h.eur, h.huf, h.uah, h.jpy, h.czk);
                """)

    cur.execute("""
                DELETE FROM rates.helper;
                """)

    cur.close()
    conn.close()


    

def check_date_range_in_db():
    conn = make_psycopg_connection()
    if not conn:
        print("Nie udalo sie polaczyc!")
        return
    else:
        print("Polaczono!")

    cur = conn.cursor()
    cur.execute("""
                SELECT date FROM rates.rates
                ORDER BY date ASC
                LIMIT 1;
                """)

    first_date = cur.fetchone()[0]

    cur.execute("""
                SELECT date FROM rates.rates
                ORDER BY date DESC
                LIMIT 1;
                """)

    last_date = cur.fetchone()[0]

    cur.close()
    conn.close()

    first_date = first_date.strftime("%Y-%m-%d")
    last_date = last_date.strftime("%Y-%m-%d")
    return first_date, last_date


def save_models_data_to_db(best_params_dict, cv_scores_dict, test_scores_dict, model_type):

    ts = datetime.datetime.now()

    conn = make_psycopg_connection()
    if not conn:
        print("Nie udalo sie polaczyc!")
        return
    else:
        print("Polaczono!")

    conn.autocommit = True

    cur = conn.cursor()
    
    for code in codes:
        params_str = json.dumps(best_params_dict[code])
        cv_str = json.dumps(cv_scores_dict[code])
        test_scores_str = json.dumps(test_scores_dict[code])
        cur.execute("""
                        INSERT INTO model.models
                        VALUES (%s, %s, %s, %s, %s, %s);
                        """, (ts, code, params_str, cv_str, test_scores_str, model_type))

    conn.close()