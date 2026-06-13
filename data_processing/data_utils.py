import pandas as pd
from datetime import date, timedelta, datetime
import requests
import json 
from io import StringIO
import time
import sys
sys.path.append("..")
from database_connection.conn import *

print(__name__)

# kody walut, które będą analizowane
codes = ['usd', 'eur', 'huf', 'jpy', 'uah', 'czk']


def make_date_chunks(start_date: date, end_date: date):
    """
    podział zakresu dat na okresy maksymalnie 90-dniowe (związane z limitami pobierania danych z API)
    """
    date_format = "%Y-%m-%d"
    
    dt = timedelta(days = 89)
    no_of_days = (end_date - start_date).days

    # ilość okresów o największej długości
    no_of_max_chunks = no_of_days // 90

    # ilość dat w ostatnim okresie
    last_chunk_size = no_of_days % 90

    # wynikiem będzie lista krotek z datą pierwszą i ostatnią danego okresu
    period_list = []

    # tworzenie zakresów
    curr_date = start_date
    for n in range(no_of_max_chunks):
        
        curr_date_str = curr_date.strftime(date_format)
        next_date_str = (curr_date + dt).strftime(date_format)
        period_tuple = (curr_date_str, next_date_str)
        
        period_list.append(period_tuple)
        curr_date = curr_date + timedelta(days = 90)

    # stworzenie ostatniego zakresu (o długości < od maksymalnej długości)
    if last_chunk_size:
        curr_date_str = curr_date.strftime(date_format)
        next_date_str = (curr_date + timedelta(days = last_chunk_size)).strftime(date_format)
        period_tuple = (curr_date_str, next_date_str)
        period_list.append(period_tuple)

    return period_list



def filter_rates(data, codes = codes):
    """
    Wyciąga z pliku json wyłącznie potrzebne informacje (data i kursy wybranyc walut)
    """
    filtered = []
    for row in data:
        
        row_dict = {}
        row_dict['date'] = row['effectiveDate']
        rates = row['rates']
        filtered_rates = [*filter(lambda x: x['code'].lower() in codes, rates)]
    
        for rate in filtered_rates:
            row_dict[f"{rate['code'].lower()}"] = rate['mid']
        
        filtered.append(row_dict)

    return filtered


def download_data(start_date_str, end_date_str):

    """
    Funkcja do pobierania danych - zwraca dataframe
    """
    
    
    date_format = "%Y-%m-%d"

    start_date = datetime.strptime(start_date_str, date_format)
    end_date = datetime.strptime(end_date_str, date_format)

    periods = make_date_chunks(start_date, end_date)

    dates = pd.date_range(start_date, end_date)

    df = pd.DataFrame(columns = codes, index = dates)
    
    for period in periods:
        
        d1, d2 = period
        
        url = r"https://api.nbp.pl/api/exchangerates/tables/A/{}/{}".format(d1, d2)
        
        resp = requests.get(url, headers = {'Accept': 'application/json'})
        try:
            assert resp.status_code == 200
        except:
            print("Błąd pobierania!")
            print(resp.status_code)
            return

        data = resp.json()

        data = filter_rates(data)

        data_str = json.dumps(data)
        buff = StringIO(data_str)

        temp = pd.read_json(buff, orient = "records")
        temp.set_index("date", inplace = True)
        
        ix = temp.index.strftime(date_format)
        
        try:
            df.loc[ix] = temp.values
        except:
            pass
            
        #print("poszło!")
        time.sleep(3)
    
    
    return df.astype("float")


def clean_data(data):

    """
    Uzupełnianie braków danych - interpolacja (oraz uzupełnienie wartością następną dla braków na samym początku)
    """

    return data.interpolate().bfill()


def get_data(start_date_str, end_date_str):

    df_raw = download_data(start_date_str, end_date_str)

    df = clean_data(df_raw)
    
    return df

def get_data_from_db():
    
    """
    Funkcja do pobrania tabeli danych z bazy
    """

    conn = make_psycopg_connection()
    if not conn:
        print("Nie udalo sie polaczyc!")
        sys.exit(2)
    
    print("Polaczono!")

    cur = conn.cursor()

    cur.execute("SELECT * FROM rates.rates")

    columns = [desc[0] for desc in cur.description]

    data = cur.fetchall()

    cur.close()
    conn.close()

    df = pd.DataFrame(data, columns = columns)
    df.set_index("date", inplace = True)

    df.index = pd.to_datetime(df.index)
    
    return df.astype("float")    


if __name__ == '__main__':

    df = get_data_from_db()
    
    print(df.head())
    print(df.info())