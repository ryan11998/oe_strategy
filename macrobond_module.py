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
    
