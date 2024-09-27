# Import modules
import pandas as pd
import win32com.client
from macrobond_api_constants import SeriesFrequency as f
from macrobond_api_constants import SeriesToLowerFrequencyMethod as tl
import warnings
warnings.filterwarnings('ignore') # Ignore warning messages
import os
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import macrobond_data_api as mda
from pathlib import Path


def macrobond_daily(series_list):
    
    ## Macrobond api setup
    def toPandasSeries(series):
        pdates = pd.to_datetime([d.strftime('%Y-%m-%d') for d in series.DatesAtEndOfPeriod])
        return pd.Series(series.values, index=pdates)
    
    def getDataframe(db, unifiedSeriesRequest):
        series = db.FetchSeries(unifiedSeriesRequest)
        return pd.DataFrame({s.Name: toPandasSeries(s) for s in series})
    
    c = win32com.client.Dispatch("Macrobond.Connection")
    d = c.Database
    r = d.CreateUnifiedSeriesRequest()
    
    # Import all macrobond series required
    for i in range(len(series_list)):
        r.AddSeries(series_list[i]).ToLowerFrequencyMethod = tl.LAST
        r.Frequency = f.DAILY
    
    frames = getDataframe(d, r)
    frames = pd.DataFrame(frames.dropna()) ## Downloaded G10 government bond yields with a monthly frequency
    return(frames)


def macrobond_monthly(series_list):
    
    ## Macrobond api setup
    def toPandasSeries(series):
        pdates = pd.to_datetime([d.strftime('%Y-%m-%d') for d in series.DatesAtEndOfPeriod])
        return pd.Series(series.values, index=pdates)
    
    def getDataframe(db, unifiedSeriesRequest):
        series = db.FetchSeries(unifiedSeriesRequest)
        return pd.DataFrame({s.Name: toPandasSeries(s) for s in series})
    
    c = win32com.client.Dispatch("Macrobond.Connection")
    d = c.Database
    r = d.CreateUnifiedSeriesRequest()
    
    # Import all macrobond series required
    for i in range(len(series_list)):
        r.AddSeries(series_list[i]).ToLowerFrequencyMethod = tl.LAST
        r.Frequency = f.MONTHLY
    
    frames = getDataframe(d, r)
    frames = pd.DataFrame(frames.dropna()) ## Downloaded G10 government bond yields with a monthly frequency
    return(frames)

def macrobond_quarterly(series_list):
    
    ## Macrobond api setup
    def toPandasSeries(series):
        pdates = pd.to_datetime([d.strftime('%Y-%m-%d') for d in series.DatesAtEndOfPeriod])
        return pd.Series(series.values, index=pdates)
    
    def getDataframe(db, unifiedSeriesRequest):
        series = db.FetchSeries(unifiedSeriesRequest)
        return pd.DataFrame({s.Name: toPandasSeries(s) for s in series})
    
    c = win32com.client.Dispatch("Macrobond.Connection")
    d = c.Database
    r = d.CreateUnifiedSeriesRequest()
    
    # Import all macrobond series required
    for i in range(len(series_list)):
        r.AddSeries(series_list[i]).ToLowerFrequencyMethod = tl.LAST
        r.Frequency = f.QUARTERLY
    
    frames = getDataframe(d, r)
    return(frames)

def macrobond_excel(path, column_labels):
    df = pd.read_excel(path)
    df.index = df.iloc[:,0]
    df = df.iloc[3:,1:]
    df.columns = column_labels
    return(df)
    

def portfolio(df, x, pct_rtn): # df is the factor
    # rank the countries for each given time period
    percentiles = df.rank(axis=1) 
    
    percentiles = percentiles * x
    
    portfolio = pd.DataFrame(columns = ['long1', 'long2', 'short1', 'short2'])  # Define the portfolio dataframe
    
    # List the top and bottom two countries in the long and short columns respectively
    ## Extract the two highest ranking countries
    portfolio[['long1', 'long2']] = percentiles.apply(
        lambda x: x.nlargest(2).index.tolist(), axis=1).apply(pd.Series) 
    ## Extract the two lowest ranking countries for each date
    portfolio[['short1', 'short2']] = percentiles.apply(
        lambda x: x.nsmallest(2).index.tolist(), axis=1).apply(pd.Series)
    
    portfolio[['long1', 'long2', 'short1', 'short2']] = portfolio[[
        'long1', 'long2', 'short1', 'short2']].apply(lambda x: x.str[:2].str.lower() + x.str[2:], axis=1)
              
    portfolio['return'],portfolio['return_overweight'],portfolio['return_underweight'],portfolio['return_long_only'] = [0,0,0,0]
    
    ## We need to match up return row indices and df row indices such that we are pulling the correct returns
    pct_rtn_temp = pct_rtn
    common_indices = portfolio.index.intersection(pct_rtn_temp.index)
    pct_rtn_temp = pct_rtn_temp.loc[common_indices]
    portfolio = portfolio.loc[common_indices]
    
    ## Extract monthly returns for each position
    ## Calculate cumulative returns for long-short portfolio and long-long portfolio
    portfolio_ll = portfolio # long only portfolio
 
    for i in range(len(portfolio)-1):
        portfolio['return'][i+1] = 0.5 * (pct_rtn_temp[portfolio['long1'][i]][i+1] +pct_rtn_temp[portfolio['long2'][i]][i+1] -pct_rtn_temp[portfolio['short1'][i]][i+1] -pct_rtn_temp[portfolio['short2'][i]][i+1])
        portfolio['return_long_only'][i+1] = 0.75*(0.5*pct_rtn_temp[portfolio['long1'][i]][i+1] +0.5*pct_rtn_temp[portfolio['long2'][i]][i+1]) +0.25*(0.5*pct_rtn_temp[portfolio['short1'][i]][i+1] +0.5*pct_rtn_temp[portfolio['short2'][i]][i+1])

        portfolio['cum_return'] = np.cumprod(1+portfolio['return'])
        portfolio['cum_return_long_only'] = np.cumprod(1+portfolio['return_long_only'])
            
    for i in range(len(portfolio_ll)-1):
            portfolio_ll['return_overweight'][i+1] = 0.5 * (pct_rtn_temp[portfolio_ll['long1'][i]][i+1] +pct_rtn_temp[portfolio_ll['long2'][i]][i+1])
            portfolio_ll['return_underweight'][i+1] = 0.5 * (pct_rtn_temp[portfolio_ll['short1'][i]][i+1] +pct_rtn_temp[portfolio_ll['short2'][i]][i+1])
            
            portfolio_ll['cum_return_overweight'] = np.cumprod(1+portfolio_ll['return_overweight'])
            portfolio_ll['cum_return_underweight'] = np.cumprod(1+portfolio_ll['return_underweight'])

    return(portfolio)

# Define a function that outputs the return chart

def factor_chart(df, chart = False, title = 'factor'): 
    
    fig,(ax1,ax2) = plt.subplots(nrows=1,ncols=2)

    plt.subplots_adjust(left=0, right=1.5)
    plt.subplots_adjust(bottom=0, top=0.75)

    ax1.plot(df['cum_return'])
    ax1.set_title('Cumulative return of long-short portfolio')
    
    
    ax2.plot(df['cum_return_overweight'], label='Overweight')
    ax2.plot(df['cum_return_underweight'], label='Underweight')
    ax2.set_title('Cumulative return of long-long portfolio')
    ax2.legend()

    if chart:
        plt.savefig(f'{title.capitalize()}.png',bbox_inches ='tight')
        
    fig.suptitle(title, fontsize=16)

    plt.show()

