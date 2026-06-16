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
    # df_to_ml = prepare_data(df)
    # df_dict = make_df_dict(df_to_ml)
    # best_params_dict = grid_search_best_params(df_dict)
    # models_dict, test_scores_dict = train_models(df_dict, best_params_dict)

    model_dict = model_dict_from_pickle()

    
    df_to_ml = prepare_data(df)

    df_dict = make_df_dict(df_to_ml)

    print(predict_data(df_dict, model_dict))

if __name__ == "__main__":
    main()