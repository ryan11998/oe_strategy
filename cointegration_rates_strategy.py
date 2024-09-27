# Relative value rates strategy based on cointegrated pairs
# Under the conjecture that central bankers are dependent on data that is measured with an error that has increased in recent years
# Hence injecting volatility into the market, an environment in which rv strategies should perform well
# Research note available upon request

import pandas as pd
import macrobond_module as md
from statsmodels.tsa.stattools import adfuller

base = md.macrobond_daily(['usrate0190','gbrate0001','eurate0003'])
base.columns = ['fed','boe','ecb']
base['boe'] = base['boe']-0.15 # sonia trades 15bps ish below base rate
base['ecb'] = base['ecb']-0.1 # estr more like 10bps
base = base.ffill()

def import_clean_df():
    df = pd.read_excel('Z:/Global strategy team/Personal/Ryan/Publications/ecb cuts more than fed/meeting_day_swaps.xlsx', index_col=0) # 1st - 10th OIS meeting day swaps for boe, fed & ecb
    df = df.iloc[3:, :]
    df.columns = [f'boe{i}' for i in range(1,11)] + [f'fed{i}' for i in range(1,11)] + [f'ecb{i}' for i in range(1,11)]
    df = df.dropna().astype(float)
    df = df.drop(['boe1','fed1','ecb1','fed10','fed9','ecb10','ecb9','boe10','boe9'], axis=1) # Issues with data on these contracts
    return df
    
def rate_trajectory(): # Calculate market pricing of rate change
    df = import_clean_df()

    for cb in ['fed','boe','ecb']:
        df[df.columns[df.columns.str.contains(cb)]] = subtract(df[df.columns[df.columns.str.contains(cb)]], base, cb)
    return df
    

def spread():  # Calculate spread of pricing trajectory between cbs/tenors
    df = rate_trajectory()
    col_pairs = [(cb1, cb2) for i, cb1 in enumerate(df.columns) for cb2 in df.columns[i+1:]]

    df_mapped = pd.DataFrame(index=df.index)

    for cb1, cb2 in col_pairs:
        if cb1[:3] == cb2[:3]:
            continue
        
        df_mapped[f'{cb1}{cb2}'] = df[cb1] - df[cb2]
        df_mapped[f'{cb2}{cb1}'] = df[cb2] - df[cb1]

    return df_mapped

def zscore(df):
    mean = df.mean()
    std = df.std()
    z = (df-mean) / std
    return z

def is_stationary(series):
        # Run the ADF test and return whether it's stationary
        return adfuller(series.dropna(), autolag='AIC')[1] < 0.1
    

def generate_signals(from_date): # if zscore <2 / >2 then spread should tighten/widen
    df = spread()
    
    df_lead = df.diff(1).shift(-1)
    dates = pd.to_datetime(df.loc[from_date:].index)
    strategy = pd.DataFrame(index=dates, columns=['pair','long_change', 'score'])
    
    for date in dates:
        print(date)
        date_prev = date - pd.DateOffset(months=12)
        temp = df.loc[date_prev:date].dropna(axis=1)
        
        # Computationally expensive option: Check stationarity and filter columns 
        stationary_cols = [pair for pair in temp.columns if is_stationary(temp[pair])]
        temp = temp[stationary_cols]
        
        if temp.empty:
            continue
        
        
        s = zscore(temp).loc[date]
        
        long = s.idxmin()
        strategy.loc[date, ['pair','score']] = long, s.min()
        
        long_change=df_lead.loc[date, long]
        
        
        if date in dates[:-1]:
            strategy.loc[date,['long_change']] = long_change
                        
    return strategy
        
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
    
ry5 = generate_signals('2024-09-20')
