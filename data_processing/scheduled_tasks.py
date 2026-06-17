import schedule
import sys
sys.path.append("..")
from data_processing.data_utils import *
from database_connection.conn import *
import datetime
import time

# regularne pobieranie danych z API
def download_and_insert_to_db():

    date_today = datetime.date.today()
    date_str = date_today.strftime("%Y-%m-%d")

    
    new_data = get_data(start_date_str, date_str)

    df_to_db(new_data)

# wg strony NBP dane są udostępniane między 11.45 a 12.15 - dodany jest jeszcze dodatkowy bufor czasowy do 13.30
schedule.every().day.at("13:30").do(download_and_insert_to_db)


# trenowanie modeli
def model_training():

    load_dotenv()

    df = get_data_from_db()

    # xgboost
    models_dict, best_params_dict, cv_scores, test_scores_dict = get_ml_models_and_scores(df, 
        curr_models_dict = None, model_type = "xgboost")

    save_models_data_to_db(best_params_dict, cv_scores_dict, test_scores_dict, "xgboost")

    # arima
    models_dict, best_params_dict, cv_scores, test_scores_dict = get_ml_models_and_scores(df, 
    curr_models_dict = None, model_type = "arima")

    save_models_data_to_db(best_params_dict, cv_scores_dict, test_scores_dict, "arima")


# trenowanie co 2 tygodnie
schedule.every(2).weeks.do(model_training)





while True:
    schedule.run_pending()
    time.sleep(1)




