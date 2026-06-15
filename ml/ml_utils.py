import numpy as np 
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit, cross_val_score, GridSearchCV
from sklearn.preprocessing import StandarScaler
from xgboost import XGBRegressor

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