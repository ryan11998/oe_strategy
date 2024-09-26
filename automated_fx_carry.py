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
import statsmodels.formula.api as smf
import datetime
from linearmodels.panel import PanelOLS
import statsmodels.api as sm
#################################################################################
# Initialise values
#################################################################################
countries = ['us','gb','jp','de','se','no','ca','au','nz','ch']
currencies = ['usd','gbp','jpy','eur','sek','nok','cad','aud','nzd','chf']
tenors = '1m', '3m', '6m', '1y', '2y', '3y', '4y', '5y', '6y', '7y', '8y', '9y', '10y', '15y', '20y', '30y'
tickers = [country + tenor + 'gov' for tenor in tenors for country in countries]
tickers
paths = [
    # Firstly the raw data
    'Z:/Global strategy team/GAA frameworks/DM FX and FI/FX/FX_SCORECARD/Strategy Deposit/data/fwd_returns.xlsx',
    'Z:/Global strategy team/GAA frameworks/DM FX and FI/FX/FX_SCORECARD/Strategy Deposit/data/rr_25d_1m.xlsx',
    'Z:/Global strategy team/GAA frameworks/DM FX and FI/FX/FX_SCORECARD/Strategy Deposit/Final panel/panel_df.xlsx',
    #'Z:/Global strategy team/GAA frameworks/DM FX and FI/FX/FX_SCORECARD/Strategy Deposit/Final panel/expected_returns.xlsx'
]

#################################################################################
## This class is to import and clean the data (Eventually import via api)
#################################################################################
class import_data:
    def __init__(self):
        self.paths = paths
        
    def clean_excel(self):
        clean_dfs = []
        for path in paths:
            df = pd.read_excel(path)
            df.index = df.iloc[:,0]
            df = df.iloc[1:,1:]
            df.index = pd.to_datetime(df.index)
            # df.columns = [pair[:6].lower() for pair in df.columns]
            clean_dfs.append(df)
            
        return clean_dfs
    
    # Return the tickers that actually contain data in macrobond
    def return_only_valid(self, series_list):
        valid_list = []
        ## Macrobond api setup
        # Import all macrobond series required
        for series in series_list:
            try:
                self.macrobond_daily([series])
                valid_list.append(series)
            except:
                continue
                
        return valid_list
    
    # Request macrobond data
    
    def macrobond_daily(self, series_list):
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
        return(frames)
    
#################################################################################    
## This class is to import all the yields data and build the principal components
#################################################################################

class yield_curve:
    def __init__(self):
        i = import_data()
        last_date = pd.to_datetime(i.clean_excel()[2].index[-1])
        self.yields = i.macrobond_daily(i.return_only_valid(tickers))
        self.dates = pd.date_range(last_date, datetime.date.today())
                
        

    def PCA(self, X, num_components):
        #Step-1
        X_meaned = X - np.mean(X , axis = 0)
         
        #Step-2
        cov_mat = np.cov(X_meaned , rowvar = False)
         
        #Step-3
        eigen_values , eigen_vectors = np.linalg.eigh(cov_mat)
         
        #Step-4
        sorted_index = np.argsort(eigen_values)[::-1]
        sorted_eigenvalue = eigen_values[sorted_index]
        sorted_eigenvectors = eigen_vectors[:,sorted_index]
         
        #Step-5
        eigenvector_subset = sorted_eigenvectors[:,0:num_components]
         
        #Step-6
        X_reduced = np.dot(eigenvector_subset.transpose() , X_meaned.transpose() ).transpose()
         
        return X_reduced
    
    
    ## Extract PCA components for each country in a rolling 3 year window
        
    def calculate_components(self): # insert entire dataframe of yields
        l,s,c = pd.DataFrame(),pd.DataFrame(),pd.DataFrame()
        
        for date in self.dates:
            for country in countries:
                temp = self.yields.loc[date+pd.DateOffset(years=-3):date,self.yields.columns.str.contains(country)].dropna() #  3 year rolling sample
                l.loc[date,country] = self.PCA(temp,3)[-1][0]
                s.loc[date,country] = self.PCA(temp,3)[-1][1]
                c.loc[date,country] = self.PCA(temp,3)[-1][2]
                
        [l.columns, s.columns, c.columns] = [currencies] * 3
        
        l = self.mapping(l)
        s = self.mapping(s)
        c = self.mapping(c)
        
        # merge calculations that have already been done
        return l,s,c
    
    # calculate relative components
    
    def mapping(self, df):
        df_mapped = pd.DataFrame(index=df.index)
        for currency1 in df.columns:
            for currency2 in df.columns:
                if currency1 == currency2:
                    continue
                else:
                    df_mapped[f'{currency1}{currency2}'] = df[f'{currency1}'] - df[f'{currency2}']
        
        return df_mapped

## Then this class will import all the fx prices and build the momentum/mean-reversion strategy

class uip:
    def __init__(self, df):
        self.df = np.log(df.dropna().astype(float))
        self.quoted = df.columns.tolist()  # Initialize with column names as symbols
        self.formula = None  # Add a property to store the OLS regression results
        self.Initialize()  # Initialize the OLS model immediately upon object creation

    def calculate_return(self, df):
        mean = np.mean(df.price)
        sd = np.std(df.price)
        df = df.resample('BM').last()
        df['log_return'] = df.price - df.price.shift(1)
        df['reversal'] = (df.price.shift(1) - mean) / sd
        df['mom'] = df.price.shift(1) - df.price.shift(4)
        df = df.dropna()
        return df, mean, sd

    def concat(self):
        df_list = []
        for symbol in self.quoted:
            fx_data = self.df[symbol].dropna().to_frame(name='price')
            his = self.calculate_return(fx_data)
            df_list.append(his[0])

        df = pd.concat(df_list)
        df = df.sort_index()
        df = df[df.apply(lambda x: np.abs(x - x.mean()) / x.std() < 3).all(axis=1)]
        return df

    def OLS(self, df):
        res = smf.ols(formula='log_return ~ reversal + mom', data=df).fit()

        return res

    def predict(self, symbol):
        res = self.df[symbol].dropna().to_frame(name='price')
        res = res.resample('BM').last()
        res = res.iloc[:-1]
        res = self.calculate_input(res, res['price'].mean(), res['price'].std())
        res = res.iloc[0]
        params = self.formula.params[1:]
        re = sum([a * b for a, b in zip(res[1:], params)]) + self.formula.params[0]
        return re

    def calculate_input(self, df, mean, sd):
        df['reversal'] = (df.price - mean) / sd
        df['mom'] = df.price - df.price.shift(3)
        df = df.dropna()
        return df

    def Initialize(self):
        # This method initializes the OLS model upon object creation
        df = self.concat()
        self.formula = self.OLS(df)

    def get_expected_returns(self):
        expected_returns = {}
        for symbol in self.quoted:
            expected_returns[symbol] = self.predict(symbol)
        return expected_returns



# Now combine the strategies into a panel dataframe

class strategy:
    def __init__(self):
        self.data = import_data().clean_excel()
        # import forward returns
        self.data[0].columns = [pair[:6].lower() for pair in self.data[0].columns] # forward returns
        self.df = self.data[0].dropna()
        self.df.columns = [pair[:6].lower() for pair in self.df.columns]
        # import panel dataset
        self.panel = pd.read_excel("Z:\Global strategy team\GAA frameworks\DM FX and FI\FX\FX_SCORECARD\Strategy Deposit\Final panel\panel_df.xlsx")
        self.last_date = self.panel['date'].max()
        # import expected returns
        #self.returns = pd.read_excel("Z:\Global strategy team\GAA frameworks\DM FX and FI\FX\FX_SCORECARD\Strategy Deposit\Final panel\expected_returns.xlsx")
        
    def uip(self):
        r = pd.DataFrame(columns = self.df.columns) # calculate ytd uip figures
        new_dates = pd.date_range(self.last_date, datetime.date.today())
        for date in new_dates:
            print(date)
            temp = self.df.loc[:date]
            ex = uip(temp).get_expected_returns()
            r.loc[date] = ex
        return r

    def components(self):
        [l_new,s_new,c_new] = yield_curve().calculate_components()
        
        return l_new,s_new,c_new
        
    def melt(self):
        new_dates = pd.date_range(self.last_date, datetime.date.today())
        uip = pd.melt(self.uip(),var_name= 'Cross', value_name ='uip', ignore_index= False)
        uip['date'] = uip.index
        
        l,s,c = self.components()
        
        fwd = self.reverse_pair(self.data[0].pct_change(21).dropna(), sign=True)
        d_add = new_dates.intersection(fwd.index)
        fwd = fwd.loc[d_add]
        
        fwd = pd.melt(fwd,var_name= 'Cross', value_name ='rt', ignore_index= False)
        fwd['date'] = fwd.index
        
        lvl = pd.melt(l,var_name= 'Cross', value_name ='l', ignore_index= False)
        lvl['date'] = lvl.index
        slp = pd.melt(s,var_name= 'Cross', value_name ='s', ignore_index= False)
        slp['date'] = slp.index
        cur = pd.melt(c,var_name= 'Cross', value_name ='c', ignore_index= False)
        cur['date'] = cur.index
        
        merged_df = pd.merge(fwd, uip, on=['Cross', 'date'], how='inner') \
                      .merge(cur, on=['Cross', 'date'], how='inner') \
                          .merge(slp, on=['Cross','date'], how='inner') \
                              .merge(lvl, on=['Cross','date'], how='inner')

        merged_df['rr_uip_curvature'] = merged_df['uip'] * merged_df['c']
        
        return merged_df
    
    def join(self):
        df = self.panel[self.panel['date'] != self.last_date].append(self.melt()) # already calculated inputs
                
        df['rt_ahead'] = df.groupby('Cross')['rt'].shift(-21) # Predicting next month's returns
                
        return df
    
    
    def reverse_pair(self, df, sign):
        for pair in df.columns:
            left = pair[:3]
            right = pair[3:]
            if sign == True:
                df[f'{right}{left}'] = - df[left+right]
            else:
                df[f'{right}{left}'] = 1 / df[left+right]
                
        df = df.apply(lambda x: pd.to_numeric(x))
                
        return(df)

    def expected_returns(self):
        dates = pd.date_range('2020-01-01', datetime.date.today())
        df = self.join()
        print(df)
        pairs = df['Cross'].unique()
        expected_returns = pd.DataFrame(columns = pairs)
        # expected_returns_insig = pd.DataFrame(index=self.dates, columns = self.pairs)
        
        for date in dates:
            print(date)
            fit_date = date + pd.DateOffset(months=-1)
            variables = ['l','s','c']
            temp = df[df['date'] <= fit_date]
            # Run the model
            temp.set_index(['Cross','date'],inplace=True)
            m = PanelOLS(dependent=temp['rt_ahead'],
                          exog=sm.add_constant(temp[variables]),
                          entity_effects=False,
                          time_effects=False)
            f = m.fit(cov_type='clustered', cluster_entity=True)
                        
            # last_date = pd.to_datetime(df.groupby('Cross')['date'][-1])
            
            last_date = pd.to_datetime(df[df['date']<=date]['date'].iloc[-1])
            
            last_data = df[df['date']==last_date]
            # last_data = df[df['date'] > fit_date]
            
            last_data.set_index(['Cross','date'],inplace=True)
            last_data = last_data[variables]
            
            
            pred = f.predict(sm.add_constant(last_data)).reset_index()
            pred.index=pred['Cross']
            expected_returns.loc[date,pairs]=pred.loc[pairs,'predictions']
            
            
            
            # results = f.groupby('Cross').last()
            # expected_returns.loc[date,pairs] = results['fitted_values']

            
            # pvalues = m.fit(cov_type='clustered', cluster_entity=True).pvalues
            # variables = pvalues[pvalues < 0.05].index[1:].tolist()
            
            # m = PanelOLS(dependent=temp['rt_ahead'],
            #               exog=sm.add_constant(temp[variables]),
            #               entity_effects=False,
            #               time_effects=False)
            # f = m.fit(cov_type='clustered', cluster_entity=True).predict()
            # results = f.groupby('Cross').last()
            # expected_returns_insig.loc[date,self.pairs] = results['fitted_values']
            
        #r_old = pd.read_excel("Z:\Global strategy team\GAA frameworks\DM FX and FI\FX\FX_SCORECARD\Strategy Deposit\Final panel\expected_returns.xlsx", index_col=0)
        #r_old = r_old[r_old.index != self.last_date]
        #expected_returns = r_old.append(expected_returns)
        
        #expected_returns = yield_curve().mapping(expected_returns)

            
        return expected_returns
    

# Now let's run the actual strategy


class backtest:
    def __init__(self, x, no_positions):
        #panel = strategy().melt()
        # self.df = strategy().melt()
        # self.pairs = self.df['Cross'].unique()
        self.dates = pd.date_range('1999-12-31',datetime.date.today(), freq='M')
        self.returns = import_data().clean_excel()[0].resample('M').last().pct_change().dropna()
        self.returns.columns = [pair[:6].lower() for pair in self.returns.columns]
        self.returns = self.reverse_pair(self.returns)
        self.x = x
        self.no = no_positions
        
    def portfolio(self):
        df = strategy().expected_returns() * self.x # expected returns
        df = self.reverse_pair(df)
        df = df.resample('M').last()
        
        trades = pd.DataFrame(df.apply(lambda x: x.nlargest(self.no).index.tolist(), axis=1)) # The model's trade suggestions
        
        pct_rtn = self.returns.shift(-1).dropna() # 1 month ahead returns
        
        common_rows = pct_rtn.index.intersection(trades.index)
        
        pct_rtn, trades = [df.loc[common_rows] for df in [pct_rtn, trades]]
        
        for i in range(1,6):
            trades[f'return {i}'] = 0
            for date in common_rows:
                positioning = trades.loc[date,0]
                
                trades.loc[date,f'return {i}'] = pct_rtn.loc[date, positioning][:i].mean()
            
            trades[f'cum_return {i}'] = np.cumprod(1 + trades[f'return {i}'])
                
        return trades
        
    def factor_chart(self):
        df = self.portfolio()
        
        for i in range(1, 6):
            plt.plot(df[f'cum_return {i}'], label=str(i))
        
        plt.legend()
        plt.show()
        
        return df
    
    def reverse_pair(self, df):
        for pair in df.columns:
            left = pair[:3]
            right = pair[3:]
            df[f'{right}{left}'] = - df[left+right]
                
        df = df.apply(lambda x: pd.to_numeric(x))
                
        return df
    


chart = backtest(1, 5).factor_chart()

test = strategy().expected_returns()

for i in range(1,6):
    plt.plot(fxs.portfolio(fxs.reverse_pair(test,True).astype(float).loc['2023-12-31':], 1, returns_daily, 1, False)['cum_return'], label=i)

plt.legend()
plt.show()    




fxs.reverse_pair(test,True).rolling(window=5).mean().dropna().idxmax(axis=1)[-50:]





picks = pd.DataFrame(index = test.resample('M').last().index, columns = geo_uni)
returns_uni = pd.DataFrame(index = test.resample('M').last().index, columns = geo_uni)
next_return = returns.shift(-1).dropna()

for pair in geo_uni:
    r = test.resample('M').last()[[col for col in test.columns if pair in col[:3]]].mean(axis=1)
    picks[pair] = r
    returns_uni[pair] = next_return.resample('M').last()[[col for col in test.columns if pair in col[:3]]].mean(axis=1)
        

h = pd.DataFrame(picks.idxmax(axis=1))
h['return'] = 0

for date in h.index:
    h.loc[date,'return'] = returns_uni.loc[date,h.loc[date,0]]
    
        

h['cum_return'] = np.cumprod(1+h['return'])





m = pd.DataFrame(picks.idxmin(axis=1))
m['return'] = 0

for date in h.index:
    m.loc[date,'return'] = returns_uni.loc[date,m.loc[date,0]]
    
        

m['cum_return'] = np.cumprod(1+m['return'])


plt.plot(h['cum_return'], label = 'ow')
plt.plot(m['cum_return'], label='uw')
plt.legend()
plt.show()
