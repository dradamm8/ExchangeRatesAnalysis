import schedule
import sys
sys.path.append("..")
from data_processing.data_utils import *
from database_connection.conn import *
import datetime
import time

def download_and_insert_to_db():

    date = datetime.today().date()
    date_str = date.strftime("%Y-%m-%d")

    new_data = get_data_for_one_day(date_str)

    df_to_db(new_data)


schedule.every().day.at("13:30").do(download_and_insert_to_db)


while True:
    schedule.run_pending()
    time.sleep(1)




