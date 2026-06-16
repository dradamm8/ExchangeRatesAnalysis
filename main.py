from database_connection.conn import *
from data_processing.data_utils import *
from ml.ml_utils import *
import sys
import datetime
# mam pobieranie danych z API, dodawanie ich do bazy i pobieranie z bazy

# przygotować model ML - niech zwraca predykcje na najbliższy tydzień
# co tydzień - dotrenowywanie modelu przy użyciu danych z tygodnia


def main():
    
    load_dotenv()

    model_dict = model_dict_from_pickle()

    

    print(model_dict)

if __name__ == "__main__":
    main()