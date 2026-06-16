import numpy as np 
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit, cross_val_score, GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score, root_mean_squared_error
from xgboost import XGBRegressor
import xgboost as xgb
import pickle
import sys
sys.path.append("..")
from database_connection.conn import *
import json
import datetime
from statsmodels.tsa.seasonal import STL
import os
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.statespace.sarimax import SARIMAX

# kody walut, które będą analizowane
codes = ['usd', 'eur', 'huf', 'uah', 'jpy', 'czk']
codes_upp = ['USD', 'EUR', 'HUF', 'UAH', 'JPY', 'CZK']


def create_directory_for_models(path):
    
    if not os.path.exists(path):
        os.makedirs(path)



def models_to_pickle(models_dict):

    for code, model in models_dict.items():
        filename = f"{os.getenv("MODELS_DIR")}{code}_model.pkl"
        with open(filename, "wb") as f:
            pickle.dump(model, f)


def model_exists():
    return os.path.exists(os.getenv("MODELS_DIR"))


def prepare_data(df):

    # standaryzacja danych
    sc = StandardScaler()
    data_scaled = sc.fit_transform(df)

    df_scaled = pd.DataFrame(data_scaled, index = df.index, columns = df.columns)

    # STL - dekompozycja szeregu czasowego
    for i, code in enumerate(codes_upp):
        ts = df_scaled.iloc[:,i]
        name = df_scaled.columns[i]
        stl_res = STL(ts, period = 24, seasonal = 15).fit()
    
        df_scaled[f"{code.lower()}_trend"] = stl_res.trend
        df_scaled[f"{code.lower()}_seasonal"] = stl_res.seasonal
        df_scaled[f"{code.lower()}_resid"] = stl_res.resid

    # przesunięcia
    for code in codes:
        for lag in [1,5,6,7]:
            df_scaled[f"{code}_lag{lag}"] = df_scaled[code].shift(lag)

    df_scaled = df_scaled.bfill()

    
    # okna czasowe - tygodniowe i miesięczne - średnia, mediana i odch. std rolling window
    for code in codes:

        # rolling window
        rolling_mean_week = df_scaled[code].rolling(7, min_periods = 1, closed = "left").mean().bfill()
        rolling_median_week = df_scaled[code].rolling(7, min_periods = 1, closed = "left").median().bfill()
        rolling_std_week = df_scaled[code].rolling(7, min_periods = 1, closed = "left").std().bfill()
    
        rolling_mean_month = df_scaled[code].rolling(30, min_periods = 1, closed = "left").mean().bfill()
        rolling_median_month = df_scaled[code].rolling(30, min_periods = 1, closed = "left").median().bfill()
        rolling_std_month = df_scaled[code].rolling(30, min_periods = 1, closed = "left").std().bfill()
    
        # expanding window
        expanding_mean = df_scaled[code].expanding().mean()
        expanding_median = df_scaled[code].expanding().median()
        expanding_std = df_scaled[code].expanding().std()
    
        # dodanie do df
        df_scaled[f"{code}_mean_week"] = rolling_mean_week
        df_scaled[f"{code}_median_week"] = rolling_median_week
        df_scaled[f"{code}_std_week"] = rolling_std_week
    
        df_scaled[f"{code}_mean_month"] = rolling_mean_month
        df_scaled[f"{code}_median_month"] = rolling_median_month
        df_scaled[f"{code}_std_month"] = rolling_std_month
    
        df_scaled[f"{code}_exp_mean"] = expanding_mean
        df_scaled[f"{code}_exp_median"] = expanding_median
        df_scaled[f"{code}_exp_std"] = expanding_std

    df_scaled = df_scaled.bfill()

    df_scaled['month'] = df.index.month.astype("category")
    df_scaled['day'] = df.index.day.astype("category")
    df_scaled['quarter'] = df.index.quarter.astype("category")

    return df_scaled

def get_features(df, code):
    
    cols = df.columns.tolist()
    code = code.lower()

    cols = [*filter(lambda x: (code in x) or (x in ['month', 'day', 'quarter']), cols)]

    return df[cols]


def make_df_dict(df_scaled):
    df_dict = {}
    for code in codes:
        temp = get_features(df_scaled, code)
        df_dict[code] = temp

    return df_dict

def ts_train_test_split(X, y, test_size):

    test_size = int(len(X) * test_size)
    X_train = X.iloc[:-test_size]
    X_test = X.iloc[-test_size:]
    y_train = y.iloc[:-test_size]
    y_test = y.iloc[-test_size:]

    return X_train, X_test, y_train, y_test


def grid_search_best_params(df_dict):

    tscv = TimeSeriesSplit(n_splits = 6)
    
    param_grid = {'max_depth' : [6,9,12],
    'n_estimators' : [100, 300, 500],
    'eta' : [0.1, 0.3]}
    
    best_params_dict = {}
    
    for code in codes:
    
        curr_df = df_dict[code]
        X = curr_df.iloc[:,1:]
        y = curr_df.iloc[:,[0]]
    
        X_train, X_test, y_train, y_test = ts_train_test_split(X, y, 0.2)
        
        print(f"Szukanie parametrów dla modelu dla {code.upper()}")
        
        model = XGBRegressor(enable_categorical = True)
    
        gs_cv = GridSearchCV(model, param_grid, cv = tscv)
        gs_cv.fit(X_train, y_train)
        
        best_params_dict[code] = gs_cv.best_params_

    return best_params_dict


def ts_cross_val_score(df_dict, best_params_dict):

    cv_scores = {}

    for code in codes:

        curr_df = df_dict[code]
        X = curr_df.iloc[:,1:]
        y = curr_df.iloc[:,[0]]

        X_train, X_test, y_train, y_test = ts_train_test_split(X, y, 0.2)
        
        model = xgb.XGBRegressor(random_state = 415151, enable_categorical = True, **best_params_dict)
        
        rmse = []
        r2 = []
        
        tscv = TimeSeriesSplit(n_splits = 6)
        for train_ix, test_ix in tscv.split(X_train):
            X_train_cv = X_train.iloc[train_ix]
            y_train_cv = y_train.iloc[train_ix]
            X_test_cv = X_train.iloc[test_ix]
            y_test_cv = y_train.iloc[test_ix]
            model.fit(X_train_cv, y_train_cv)
            y_pred_cv = model.predict(X_test_cv)
            
            rmse.append(root_mean_squared_error(y_test_cv, y_pred_cv))
            r2.append(r2_score(y_test_cv, y_pred_cv))

        cv_scores[code] = {'rmse' : rmse, 'r2' : r2}

    return cv_scores


def train_models(df_dict, best_params_dict, train_existing = True):

    models_dict = {}
    test_scores_dict = {}
    
    for code in codes:

        curr_df = df_dict[code]
        X = curr_df.iloc[:,1:]
        y = curr_df.iloc[:,[0]]

        X_train, X_test, y_train, y_test = ts_train_test_split(X, y, 0.2)

        model = xgb.XGBRegressor(random_state = 415151, enable_categorical = True, **best_params_dict[code])

        if train_existing and model_exists():
            curr_model = pickle.load(f"{os.getenv("MODELS_DIR")}{code}_model.pkl")
            model.fit(X_train, y_train, xgb_model = curr_model.get_booster())
        else:
            model.fit(X_train, y_train)

        y_pred = model.predict(X_test)
        
        rmse = root_mean_squared_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)

        test_scores_dict[code] = {'rmse' : rmse, 'r2' : r2}

        models_dict[code] = model

    if not model_exists():
        create_directory_for_models(os.getenv("MODELS_DIR"))
    models_to_pickle(models_dict)

    return models_dict, test_scores_dict




def get_ml_models_and_scores(df, curr_models_dict = None):

    # jeśli models_dict jest none, to model jedziemy od 0

    # przygotowanie danych
    df_to_ml = prepare_data(df)

    # słownik przechowujący dane dla różnych walut
    df_dict = make_df_dict(df_to_ml)
    
    print(df_dict)

    # GridSearch - najlepsze parametry
    best_params_dict = grid_search_best_params(df_dict)

    # kroswalidacja z najlepszymi parametrami
    cv_scores = ts_cross_val_score(df_dict, best_params_dict)

    train_existing = True
    if curr_models_dict is None:
        train_existing = False
    
    # trenowanie modeli
    models_dict, test_scores_dict = train_models(df_dict, best_params_dict, train_existing)

    return models_dict, best_params_dict, cv_scores, test_scores_dict

def model_dict_from_pickle():

    model_dict = {}

    for code in codes:

        path = os.getenv("MODELS_DIR") + code + "_model.pkl"

        with open(path, "rb") as f:
            model = pickle.load(f)

        model_dict[code] = model

    return model_dict


def make_arima_forecasts(X, extra_dates):
    # arima i sarimax trenowane na 3 miesięcznych danych
    # przewidywania na 2 tygodnie
    
    # arima dla trendu, reszt, okien
    # sarimax dla sezonowosci

    arima_cols = [0, 2, 7, 8, 9, 10, 11, 12, 13, 14, 15]
    sarimax_col = 1

    last_date = X.index[-1]

    X_for_training = X.iloc[-90:, arima_cols + [sarimax_col]]

    X_final = pd.DataFrame(index = extra_dates, columns = X.columns)
    
    for col in X_for_training.columns[:-1]:

        arima_model = ARIMA(X_for_training.loc[:,col], order = (2,2,1), enforce_stationarity = False).fit()
        forecasts = arima_model.get_forecast(steps = 14).predicted_mean

        X_final.loc[extra_dates, col] = forecasts.values


    sarimax_model = SARIMAX(X_for_training.iloc[:,-1], order = (1,1,0), seasonal_order = (0,1,0,30)).fit()
    sarimax_forecasts = sarimax_model.get_forecast(steps = 14).predicted_mean
   
    X_final.iloc[:, sarimax_col] = sarimax_forecasts.values
    
    return pd.concat((X, X_final))


def predict_data(df_dict, models_dict):

    # po jednej wartości - przewidywanie po jednej dacie naraz
    # ta wymodelowana wartość posłuży potem do modelowania kolejnych
    
    predictions_dict = {}
    dt1 = datetime.timedelta(days = 1)
    dt2 = datetime.timedelta(days = 14)
    
    for code in codes:

        curr_df = df_dict[code]
        model = models_dict[code]
        
        last_date = curr_df.index[-1]
        extra_dates = pd.date_range(last_date + dt1, last_date + dt2)

        X = curr_df.iloc[:,1:]
        y = curr_df.iloc[:,[0]]

        y_temp = pd.DataFrame(columns = y.columns, index = extra_dates)
        y_temp = pd.concat((y, y_temp))
        
        # arima i sarimax dla trendu, sezonowości i zmiennych w oknach
        X = make_arima_forecasts(X, extra_dates)

        # wybór zmiennych, gdzie jest shift
        lag_cols = [3,4,5,6]

        # nany na końcu uzupełniamy tymi przesunięciami, a wcześniejsze - tym co było
        for lag_col, lag in zip(lag_cols, [1,5,6,7]):
            colname = X.columns[lag_col]
            X.loc[extra_dates, colname] = y_temp.shift(lag).loc[extra_dates].values
            
        X.iloc[:8] = curr_df.iloc[:8, 1:]
        
        # cechy czasowe
        X['month'] = X.index.month.astype("category")
        X['day'] = X.index.day.astype("category")
        X['quarter'] = X.index.quarter.astype("category")

        for col in X.columns[:-3]:
            X[col] = X[col].astype(float)
        
        
        # teraz przewidywać WIERSZ PO WIERSZU - DATA PO DACIE
        # po tym mogę użyć wartości przewidzianych i uzupełniać kolejne lagi i przewidywać kolejne wartości

        for date in extra_dates:
            
            row = X.loc[[date]]
            
            y_predicted_for_date = model.predict(row)
            y_temp.loc[date] = y_predicted_for_date
            
            if date != extra_dates[-1]:
                for lag_col, lag in zip(lag_cols, [1,5,6,7]):
                    colname = X.columns[lag_col]
                    X.loc[date + dt1, colname] = y_temp.shift(lag).loc[date + dt1].values[0]
                    

        predictions_dict[code] = y_temp.loc[extra_dates]
        
        
    return predictions_dict