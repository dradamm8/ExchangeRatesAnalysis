from database_connection.conn import *
from data_processing.data_utils import *
from ml.ml_utils import *
import sys
import warnings
warnings.simplefilter(action='ignore')
from dashboards.dashboards import *

# mam już wszystko jeśli chodzi o pobieranie i zapisywanie danych i modeli
# teraz - dashboardy

def main():
    
    load_dotenv()
    
    date_today = date.today()
    date_str = date_today.strftime("%Y-%m-%d")

    prev = date(2023, 5, 3).strftime("%Y-%m-%d")

    new_data = get_data(prev, date_str)

    df_to_db(new_data)

    

    

if __name__ == "__main__":
    main()