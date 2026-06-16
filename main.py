from database_connection.conn import *
from data_processing.data_utils import *
from ml.ml_utils import *
import sys
import datetime
import warnings
warnings.simplefilter(action='ignore')

# mam pobieranie danych z API, dodawanie ich do bazy i pobieranie z bazy

# przygotować model ML - niech zwraca predykcje na najbliższy tydzień
# co tydzień - dotrenowywanie modelu przy użyciu danych z tygodnia


def main():
    
    load_dotenv()

    df = get_data_from_db()
    
    df_to_ml = prepare_data(df)
    
    df_dict = make_df_dict(df_to_ml)
    
    best_params_dict = grid_search_best_params(df_dict, "arima")
    
    cv_scores_dict = ts_cross_val_score(df_dict, best_params_dict, "arima")
    
    models_dict, test_scores_dict = train_models(df_dict, best_params_dict, train_existing = False, model = "arima")
    
    save_models_data_to_db(best_params_dict, cv_scores_dict, test_scores_dict, "arima")

if __name__ == "__main__":
    main()