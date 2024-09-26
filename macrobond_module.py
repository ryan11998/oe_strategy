# A module that improves the accessibility of the macrobond API

# Import modules
import pandas as pd

from macrobond_api_constants import SeriesFrequency as f
from macrobond_api_constants import SeriesToLowerFrequencyMethod as tl
import warnings
warnings.filterwarnings('ignore') # Ignore warning messages


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


macrobond_daily('us2ygov')
