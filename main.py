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

    df = get_data_from_db()

    models_dict, best_params_dict, cv_scores, test_scores_dict = get_ml_models_and_scores(df)

    print(best_params_dict)

    save_models_data_to_db(best_params_dict, cv_scores)

if __name__ == "__main__":
    main()