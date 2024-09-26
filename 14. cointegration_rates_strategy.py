import pandas as pd
import matplotlib.pyplot as plt
import win32com.client
import numpy as np
import macrobond_data_api as mda
from macrobond_api_constants import SeriesFrequency as f
from macrobond_api_constants import SeriesToLowerFrequencyMethod as tl
import warnings
warnings.filterwarnings('ignore') # Ignore warning messages
import math as math
import os
from datetime import datetime, timedelta
import macrobond_module as md
import matplotlib.pyplot as plt
from pathlib import Path
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.vector_ar.vecm import coint_johansen
from statsmodels.tsa.stattools import coint

base = md.macrobond_daily(['usrate0190','gbrate0001','eurate0003'])
base.columns = ['fed','boe','ecb']
base['boe'] = base['boe']-0.15
base['ecb'] = base['ecb']-0.1
base = base.ffill()
base.loc['2024-09-03','ecb'] = 3.65
base.loc['2024-09-03','fed'] = 5.33

def import_clean_df():
    df = pd.read_excel('Z:/Global strategy team/Personal/Ryan/Publications/ecb cuts more than fed/meeting_day_swaps.xlsx', index_col=0)
    df = df.iloc[3:, :]
    df.columns = [f'boe{i}' for i in range(1,11)] + [f'fed{i}' for i in range(1,11)] + [f'ecb{i}' for i in range(1,11)]
    df = df.dropna().astype(float)
    df = df.drop(['boe1','fed1','ecb1','fed10','fed9','ecb10','ecb9','boe10','boe9'], axis=1)
    return df
    
def rate_trajectory(): # Calculate market pricing of rate change
    df = import_clean_df()
    # df = md.macrobond_daily(return_only_valid(mb))
    # df.columns = lab
    # df = 100-df
    for cb in ['fed','boe','ecb']:
        df[df.columns[df.columns.str.contains(cb)]] = subtract(df[df.columns[df.columns.str.contains(cb)]], base, cb)
    return df
    
# def spread(): # calculate spread of pricing trajectory between cbs/tenors
#     df = rate_trajectory()
#     df_mapped = pd.DataFrame(index=df.index)
#     for cb1 in df.columns:
#         for cb2 in df.columns:
#             if cb1 == cb2:
#                 continue
#             else:
#                 df_mapped[f'{cb1}{cb2}'] = df[f'{cb1}'] - df[f'{cb2}']
    
#     return df_mapped

def spread():  # Calculate spread of pricing trajectory between cbs/tenors
    df = rate_trajectory()
    col_pairs = [(cb1, cb2) for i, cb1 in enumerate(df.columns) for cb2 in df.columns[i+1:]]

    df_mapped = pd.DataFrame(index=df.index)

    for cb1, cb2 in col_pairs:
        if cb1[:3] == cb2[:3]:
            continue
        
        # if cb1 == cb2:
        #     continue
        
        df_mapped[f'{cb1}{cb2}'] = df[cb1] - df[cb2]
        df_mapped[f'{cb2}{cb1}'] = df[cb2] - df[cb1]

    return df_mapped

def zscore(df):
    mean = df.mean()
    std = df.std()
    z = (df-mean) / std
    return z

def generate_signals(): # if zscore <2 / >2 then spread should tighten/widen
    df = spread()
    
    df_lead = df.diff(1).shift(-1)
    dates = pd.to_datetime(df.loc['2024-05-01':].index)
    strategy = pd.DataFrame(index=dates, columns=['pair','long_change', 'score'])
    z = pd.DataFrame(index=dates, columns = df.columns)
    
    # before = pd.to_datetime(df.loc[:'2023-06-01'].index)
    # after = pd.to_datetime(df.loc['2023-06-01':].index)

    for date in dates:
        print(date)
        date_prev = date - pd.DateOffset(months=12)
        temp = df.loc[date_prev:date].dropna(axis=1)
        
        # Check stationarity and filter columns
        # stationary_cols = [pair for pair in temp.columns 
        #                    if adfuller(temp[pair].dropna(), autolag='AIC')[1] < 0.1]
        
        # temp = temp[stationary_cols]
        
        # if temp.empty:
        #     continue
        
        
        # # only trade if the spread is stationary and there is at least one trade to choose from
        # stationary = pd.DataFrame(columns = temp.columns)
        # stationary.loc[date] = 0
        
        # for pair in temp.columns:
        #     if adfuller(temp[pair].dropna(), autolag='AIC')[1] < 0.1:
        #         stationary[pair] = True
        #     else:
        #         stationary[pair] = False
                
                
            
        # temp = temp.loc[:, stationary.loc[date].astype(bool)]
        
        s = zscore(temp).loc[date]
        
        # if date in before:
        #     long = s.idxmax()
        # if date in after:
        #     long = s.idxmin()
        # else:
        #     print('else')
        
        long = s.idxmin()
        strategy.loc[date, ['pair','score']] = long, s.min()
        # if abs(s.min()) < 2:
        #     strategy.loc[date,'long_change'] = 0
        #     continue
        
        long_change=df_lead.loc[date, long]
        
        z.loc[date]=s
        
        if date in dates[:-1]:
            strategy.loc[date,['long_change']] = long_change
            
    return strategy
    
    # return z, df_lead
        
def return_only_valid(series_list):
    valid_list = []
    ## Macrobond api setup
    # Import all macrobond series required
    for series in series_list:
        try:
            md.macrobond_daily([series])
            valid_list.append(series)
        except:
            continue
            
    return valid_list

def subtract(left, right, col):
    left = left.join(right[col])
    left = left.subtract(right[col],axis=0)
    left = left.drop(col, axis=1)
    
    return left
    
ry5 = generate_signals()
