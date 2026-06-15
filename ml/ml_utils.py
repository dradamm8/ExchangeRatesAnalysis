import numpy as np 
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit, cross_val_score, GridSearchCV
from sklearn.preprocessing import StandarScaler
from sklearn.metrics import r2_score, root_mean_squared_error
from xgboost import XGBRegressor
import xgboost as xgb
import pickle
import sys
sys.path.append("..")
from database_connection.conn import *
import json
import datetime

# kody walut, które będą analizowane
codes = ['usd', 'eur', 'huf', 'uah', 'jpy', 'czk']


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


def ts_train_test_split(X, y, test_size):

    test_size = int(len(df) * test_size)
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


def train_models(df_dict, best_params_dict, train_existing = False, curr_models_dict = None):

    models_dict = {}
    test_scores_dict = {}
    
    for code in codes:

        curr_df = df_dict[code]
        X = curr_df.iloc[:,1:]
        y = curr_df.iloc[:,[0]]

        X_train, X_test, y_train, y_test = ts_train_test_split(X, y, 0.2)

        model = xgb.XGBRegressor(random_state = 415151, enable_categorical = True, **best_params_dict[code])

        if train_existing:
            curr_model = curr_models_dict[code]
            model.fit(X_train, y_train, xgb_model = curr_model.get_booster())
        else:
            model.fit(X_train, y_train)

        y_pred = model.predict(X_test)
        
        rmse = root_mean_squared_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)

        test_scores_dict[code] = {'rmse' : rmse, 'r2' : r2}

        models_dict[code] = model

    return models_dict, test_scores_dict


def get_ml_models_and_scores(df, curr_models_dict = None):

    # jeśli models_dict jest none, to model jedziemy od 0

    # przygotowanie danych
    df_to_ml = prepare_data(df)

    # słownik przechowujący dane dla różnych walut
    df_dict = make_df_dict(df_to_ml)
    
    # GridSearch - najlepsze parametry
    best_params_dict = grid_search_best_params(df_dict)

    # kroswalidacja z najlepszymi parametrami
    cv_scores = ts_cross_val_score(df_dict, best_params_dict)

    train_existing = True
    if curr_models_dict is None:
        train_existing = False
    
    # trenowanie modeli
    models_dict, test_scores_dict = train_models(df_dict, best_params_dict, train_existing, curr_models_dict)

    return models_dict, best_params_dict, cv_scores, test_scores_dict


