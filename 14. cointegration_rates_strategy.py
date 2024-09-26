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


df = pd.read_excel('Z:/Global strategy team/Personal/Ryan/Publications/ecb cuts more than fed/meeting_day_swaps.xlsx', index_col=0)
df = df.iloc[3:, :]
df.columns = [f'boe{i}' for i in range(1,11)] + [f'fed{i}' for i in range(1,11)] + [f'ecb{i}' for i in range(1,11)]
df = df.astype(float)
# df = df[['boe10','fed10']].resample('M').last().dropna()

plt.plot(df.join(base)[['ecb9','ecb','ecb4']].dropna().loc['2023-01-01':], label=['9th meeting','base','4th meeting'])
plt.title('ecb base rate vs market pricing')
plt.legend()

for cb in ['fed','boe','ecb']:
    df[df.columns[df.columns.str.contains(cb)]] = subtract(df[df.columns[df.columns.str.contains(cb)]], base, cb)






# Check for unit roots (ADF test) in each time series
def adf_test(series, name=None):
    result = adfuller(series, autolag='AIC')
    print(f'ADF Test Results for {name}')
    print('Test Statistic:', result[0])
    print('p-value:', result[1])

for country_dependent in ['fed','boe','ecb']:
    for country_independent in ['fed','boe','ecb']:
        if country_dependent == country_independent:
            continue
        else:
            temp = df[[country_dependent, country_independent]].dropna()
            adf_test(temp[country_independent], name=f'{country_independent}')
            adf_test(temp[country_dependent], name=f'{country_dependent}')
            # Estimate the cointegrating relationship using Engle-Granger
            X = sm.add_constant(temp[country_independent])
            model = sm.OLS(temp[country_dependent], X)
            results = model.fit()
            print(results.summary())
            
            # Check for cointegration
            if results.pvalues[1] < 0.05:
                print('Engle-Granger Test: The two series are cointegrated.')
                print('Cointegration Relationship Coefficient:', results.params[country_independent])
            else:
                print('Engle-Granger Test: The two series are not cointegrated.')
                print('Cointegration Relationship Coefficient:', results.params[country_independent])
                
plt.plot(df['us'], label='us')
plt.plot(df['jp'], label='jp')
plt.legend()
plt.show()



plt.plot(temp['ecb7'], label='ecb 6th')
plt.plot(temp['fed7'], label='fed 6th')
plt.legend()
plt.show()

(temp['fed7'] - temp['ecb7']).mean()


plt.plot(temp, label=temp.columns)
plt.legend()




temp = df[['fed7','ecb7']].diff(22).dropna().loc['2022-01-01':]
adf_test(temp['fed7'])
adf_test(temp['ecb7'])
# Estimate the cointegrating relationship using Engle-Granger
X = sm.add_constant(temp['fed7'])
model = sm.OLS(temp['ecb7'], X)
results = model.fit()
print(results.summary())







temp = df[['fed6','boe6']].resample('W').last().dropna().loc['2016-01-01':]

coint(temp['fed6'],temp['boe6'],trend='ct',autolag='bic')

plt.plot((temp['fed8']-temp['boe8']))

(temp['fed8']-temp['boe8']).mean()








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


jt.coint_johansen(df[['boe7','boe4','boe6','ecb2','ecb7','ecb4','ecb6','fed2','fed7','fed4','fed6']].dropna(),0,1)



jt.coint_johansen(df[df.columns[:20]].dropna(),0,1)


z_long = ry4[0].iloc[:, :int(len(ry4[0].columns))].reset_index().melt(id_vars='index', var_name='pair', value_name='zscore').dropna()

spd_nxt = ry4[1].iloc[:,:int(len(ry4[0].columns))].reset_index().melt(id_vars='index',var_name='pair',value_name='spd_next').dropna()

test = pd.merge(spd_nxt, z_long, on=['index', 'pair'], how='inner').dropna()

# Perform linear regression
X = test['zscore'].astype(float)
y = test['spd_next'].astype(float)

# Add a constant to the model (intercept)
X = sm.add_constant(X)

# Fit the regression model
model = sm.OLS(y, X).fit()

# Print the regression results
print(model.summary())







X = test[test['pair']=='boejun23ecbapr23']['zscore'].astype(float)
y = test[test['pair']=='boejun23ecbapr23']['spd_next'].astype(float)

# Add a constant to the model (intercept)
X = sm.add_constant(X)

# Fit the regression model
model = sm.OLS(y, X).fit()

# Print the regression results
print(model.summary())



# ry3.to_excel("C:/Users/rfield/Downloads/rates_coint.xlsx")


# Trading strategy
# Step one, calculate spreads between

pair_mapping = {
    'boefed': 'gbpusd',
    'fedboe': 'usdgbp',
    'boeecb': 'gbpeur',
    'ecbboe': 'eurgbp',
    'ecbfed': 'eurusd',
    'fedecb': 'usdeur'
}

fx = md.macrobond_daily(['gbp','eur','gbpeur'])
fx.columns = ['usdgbp','usdeur','eurgbp']
fx = fx.pct_change(5).shift(-5).dropna()
fx[['gbpusd','eurusd','gbpeur']] = -fx[['usdgbp','usdeur','eurgbp']]


def remove_numbers(input_string):
    return ''.join([char for char in input_string if not char.isdigit()])


test['pair_short'] = [pair_mapping[remove_numbers(test['pair'][i])] for i in range(len(test))]

test['return'] = np.nan


# for i in range(len(test)):
#     date = test['index'][i]
#     if date == test['index'][633]:
#         continue
#     pair = test['pair_short'][i]
#     r = fx.loc[date,pair]
#     test.loc[(test['index'] ==date) & (test['pair_short']==pair),'return'] = r
    
    
    
    
skip_date = test['index'][633]

# Apply the mapping function
test['return'] = test.apply(
    lambda row: fx.at[row['index'], row['pair_short']] if row['index'] < pd.to_datetime('2024-05-24') else row['return'], 
    axis=1
)


test = test.dropna()




test2 = test[(test['pair']=='boe1fed1')|(test['pair']=='boe1ecb1')|(test['pair']=='boe2fed2')|(test['pair']=='boe2ecb2')|(test['pair']=='boe4ecb4')|
             (test['pair']=='boe4fed4')|(test['pair']=='boe6fed6')|(test['pair']=='boe6ecb6')|(test['pair']=='boe8fed8')]



test2 = test[(test['pair']=='fed1ecb1')|(test['pair']=='fed1boe1')|
             
             
             
             (test['pair']=='fed2ecb2')|(test['pair']=='fed2boe2')|(test['pair']=='fed4boe4')|
             (test['pair']=='fed4ecb4')|(test['pair']=='fed6ecb6')|(test['pair']=='fed6boe6')|(test['pair']=='fed8ecb8')]


test2 = test[(test['pair']=='fed1ecb1')|(test['pair']=='fed1boe1')|(test['pair']=='fed2ecb2')|
             (test['pair']=='fed2boe2')|(test['pair']=='fed3ecb3')|(test['pair']=='fed3boe3')|
             (test['pair']=='fed4ecb4')|(test['pair']=='fed4boe4')|(test['pair']=='fed5ecb5')|
             (test['pair']=='fed5boe5')|(test['pair']=='fed6ecb6')|(test['pair']=='fed6boe6')|
             (test['pair']=='fed7ecb7')|(test['pair']=='fed7boe7')|(test['pair']=='fed8ecb8')|(test['pair']=='fed8boe8')]



test2 = test[(test['pair']=='boe1ecb1')|(test['pair']=='boe1fed1')|(test['pair']=='boe2ecb2')|
             (test['pair']=='boe2fed2')|(test['pair']=='boe3ecb3')|(test['pair']=='boe3fed3')|
             (test['pair']=='boe4ecb4')|(test['pair']=='boe4fed4')|(test['pair']=='boe5ecb5')|
             (test['pair']=='boe5fed5')|(test['pair']=='boe6ecb6')|(test['pair']=='boe6fed6')|
             (test['pair']=='boe7ecb7')|(test['pair']=='boe7fed7')|(test['pair']=='boe8ecb8')|(test['pair']=='boe8fed8')]

test2 = test[(test['pair']=='ecb3boe3')]

test.index = test['index']
test2 = test.groupby('pair').resample('W').last()


test3 = test2[test2['index'] > '2023-06-01']

test2 = test2[test2['pair_short'] == 'gbpeur']

test['zscore'] = test.groupby('pair')['zscore'].diff()

test3['zscore_l']= test3.groupby('pair')['zscore'].shift(5)
test3['zscore_ll']= test3.groupby('pair')['zscore'].shift(2)
test3['zscore_lll']= test3.groupby('pair')['zscore'].shift(3)
test3['zscore_llll']= test3.groupby('pair')['zscore'].shift(4)


test3.set_index(['pair','index'],inplace=True)
test3 = test3.dropna()

import pandas as pd
from linearmodels.panel import PanelOLS

dependent_var = 'return'
independent_vars = ['zscore']

# Prepare the model
model = PanelOLS(test3[dependent_var], test3[independent_vars], entity_effects=False)

# Fit the model
results = model.fit(cov_type='robust')

# Print the results
print(results.summary)


# Perform linear regression
test3.index = test3['index']
test3 = test3.groupby('pair').resample('W').last()

test3 = test3.reset_index()

test3 = test3.drop(['zscore_l','zscore_ll','zscore_lll','zscore_llll'],axis=1)
test3 = test3.drop(['pair_short','spd_next'],axis=1)

test4 = test.pivot(index='index', columns='pair', values='zscore')
test4['return'] = test[test['pair']=='boe2ecb2']['return']


X = test3[['zscore','zscore_l','zscore_ll']].astype(float)



adfuller(X, autolag='AIC')

X = test4[['boe7ecb7']].loc['2023-06-01':].astype(float)
y = test4['return'].loc['2023-06-01':].astype(float)

# Add a constant to the model (intercept)
X = sm.add_constant(X)

# Fit the regression model
model = sm.OLS(y, X).fit()

# Print the regression results
print(model.summary())


plt.plot(model.predict())

# def contains_fed_twice(cell):
#     return cell.lower().count('fed') >= 2

# def contains_ecb_twice(cell):
#     return cell.lower().count('ecb') >= 2

# def contains_boe_twice(cell):
#     return cell.lower().count('boe') >= 2

# for date in ry4.dropna().index:
#     if contains_fed_twice(ry4.loc[date,'pair']) | contains_ecb_twice(ry4.loc[date,'pair']) | contains_boe_twice(ry4.loc[date,'pair']):
#         ry4.loc[date,'long_change'] = np.nan
#         ry4.loc[date,'pair'] = np.nan




# If lies one day +- meeting date, do not trade
meeting_dates = md.macrobond_daily(['usrate2056','gbrate0236','eurate0021','sofr','sonia','estr']).dropna().astype(float)
meeting_dates[['sofr','sonia','estr']] = meeting_dates[['sofr','sonia','estr']].diff()
meeting_dates[abs(meeting_dates) > 0.20] = 1

for date in meeting_dates.index:
    date_prev = date + pd.DateOffset(days=-1)
    if meeting_dates.loc[date,'sofr'] == 1:
        meeting_dates.loc[date_prev,'usrate2056'] = 1
    if meeting_dates.loc[date,'estr'] == 1:
        meeting_dates.loc[date_prev,'eurate0021'] = 1
    if meeting_dates.loc[date,'sonia'] == 1:
        meeting_dates.loc[date_prev,'gbrate0236'] = 1


meeting_dates['sum'] = meeting_dates.sum(axis=1)
ry4['omit'] = 0
ry4['z'] = 0


for i in range(len(ry4)-3):
    date = ry4.index[i]
    print(date)
    date_last = ry4.index[i-1]
    date_last_last = ry4.index[i-2]
    date_last_last_last = ry4.index[i-3]
    date_next = ry4.index[i+1]
    date_next_next = ry4.index[i+2]
    date_next_next_next = ry4.index[i+3]
    if (meeting_dates.loc[date,'sum'] > 0):
        print(date,True)
        ry4.loc[date,'omit'] = np.nan
        print(ry4.loc[date,'omit'])
    
    # if ry4.loc[date,'score'] > -2:
    #     ry4.loc[date,'z'] = np.nan
    







# import re

# ry4
# r = md.macrobond_daily(['ml_g1o2_truh','ml_g1l0_truh','ml_g1d0_truh']).pct_change().shift(-1).dropna()
# r.columns = ['fed','boe','ecb']
# bruh = ry4.join(r)
# bruh['return'] = 0 
# for date in bruh.index:
#     short = re.sub(r'\d+', '', bruh.loc[date,'pair'])[:3]
#     long = re.sub(r'\d+', '', bruh.loc[date,'pair'])[3:]
#     bruh.loc[date,'return'] = bruh.loc[date,long] - bruh.loc[date,short]
    












# Do exactly the same with futures
codes  = ['f','g','h','j','k','m','n','q','u','v','x','z']
years = ['2023','2024','2025']
tickers = ['sr1','eon','soa']
mb = []
lab = []

tick_map = {
    "f": "jan",
    "g": "feb",
    "h": "mar",
    "j": "apr",
    "k": "may",
    "m": "jun",
    "n": "jul",
    "q": "aug",
    "u": "sep",
    "v": "oct",
    "x": "nov",
    "z": "dec",
    "sr1":"fed",
    "eon":"ecb",
    "soa":"boe",
    "2020":"20",
    "2021":"21",
    "2022":"22",
    "2023":"23",
    "2024":"24",
    "2025":"25"
}

for code in codes:
    for year in years:
        for tick in tickers:
            try:
                md.macrobond_daily([tick + year + code + '_cl'])
                mb = mb + [tick + year + code + '_cl']
                lab = lab + [tick_map[tick]+tick_map[code]+tick_map[year]]
            except Exception as e:
                print([tick_map[tick]+tick_map[code]+tick_map[year]], "this ticker does not exist")
            
            
            
        
df = md.macrobond_daily(return_only_valid(mb))
df.columns = lab
df = 100-df


def adf_test(series, name=None):
    result = adfuller(series, autolag='AIC')
    return result[1]

    
    
    

adf_test(nnn['feddec24boejun25'].dropna().resample('W').last()[-40:])


stat = pd.DataFrame(columns=['pvalue'])

for col in nnn.columns:
    try:
        stat.loc[col,'pvalue'] = adf_test(nnn[col].dropna().resample('W').last()[-40:])
    except Exception as e:
        continue



plt.plot(nnn['ecbdec24boedec24'].dropna())




for col in nnn.columns:
    adf_test()









import requests
from bs4 import BeautifulSoup

# Define the URL
urls_ecb = {




    https://www.ecb.europa.eu/press/press_conference/monetary-policy-statement/2014/html/is141204.en.html
    https://www.ecb.europa.eu/press/press_conference/monetary-policy-statement/2018/html/ecb.is180726.en.html
    https://www.ecb.europa.eu/press/press_conference/monetary-policy-statement/2019/html/ecb.is191024~78a5550bc1.en.html
    https://www.ecb.europa.eu/press/press_conference/monetary-policy-statement/2020/html/ecb.is200430~ab3058e07f.en.html
    "https://www.ecb.europa.eu/press/press_conference/monetary-policy-statement/2020/html/ecb.is200604~b479b8cfff.en.html":"0620",
        "https://www.ecb.europa.eu/press/press_conference/monetary-policy-statement/2020/html/ecb.is200716~3865f74bf8.en.html":"0720",
        "https://www.ecb.europa.eu/press/press_conference/monetary-policy-statement/2020/html/ecb.is200910~5c43e3a591.en.html":"0920",
        "https://www.ecb.europa.eu/press/press_conference/monetary-policy-statement/2020/html/ecb.is201029~80b00b5789.en.html":"1020",
        "https://www.ecb.europa.eu/press/press_conference/monetary-policy-statement/2020/html/ecb.is201210~9b8e5f3cdd.en.html":"1220",
        "https://www.ecb.europa.eu/press/press_conference/monetary-policy-statement/2021/html/ecb.is210121~e601112a72.en.html":"0121",
        "https://www.ecb.europa.eu/press/press_conference/monetary-policy-statement/2021/html/ecb.is210311~d368d7151a.en.html":"0321",
        "https://www.ecb.europa.eu/press/press_conference/monetary-policy-statement/2021/html/ecb.is210422~b0ad2d3414.en.html":"0421",
        "https://www.ecb.europa.eu/press/press_conference/monetary-policy-statement/2021/html/ecb.is210610~115f4c0246.en.html":"0621",
        "https://www.ecb.europa.eu/press/press_conference/monetary-policy-statement/2021/html/ecb.is210722~13e7f5e795.en.html":"0721",
        "https://www.ecb.europa.eu/press/press_conference/monetary-policy-statement/2021/html/ecb.is210909~b2d882f724.en.html":"0921",
        "https://www.ecb.europa.eu/press/press_conference/monetary-policy-statement/2021/html/ecb.is211028~939f22970b.en.html":"1021",
        "https://www.ecb.europa.eu/press/press_conference/monetary-policy-statement/2021/html/ecb.is211216~9abaace28e.en.html":"1221",
        "https://www.ecb.europa.eu/press/press_conference/monetary-policy-statement/2022/html/ecb.is220203~ca7001dec0.en.html":"0222",
        "https://www.ecb.europa.eu/press/press_conference/monetary-policy-statement/2022/html/ecb.is220310~1bc8c1b1ca.en.html":"0322",
        "https://www.ecb.europa.eu/press/press_conference/monetary-policy-statement/2022/html/ecb.is220414~fa5c8fe142.en.html":"0422",
        "https://www.ecb.europa.eu/press/press_conference/monetary-policy-statement/2022/html/ecb.is220609~abe7c95b19.en.html":"0622",
        "https://www.ecb.europa.eu/press/press_conference/monetary-policy-statement/2022/html/ecb.is220721~51ef267c68.en.html":"0722",
        "https://www.ecb.europa.eu/press/press_conference/monetary-policy-statement/2022/html/ecb.is220908~cd8363c58e.en.html":"0922",
        "https://www.ecb.europa.eu/press/press_conference/monetary-policy-statement/2022/html/ecb.is221027~358a06a35f.en.html":"1022",
        "https://www.ecb.europa.eu/press/press_conference/monetary-policy-statement/2022/html/ecb.is221215~197ac630ae.en.html":"1222",
        "https://www.ecb.europa.eu/press/press_conference/monetary-policy-statement/2023/html/ecb.is230202~4313651089.en.html":"0223",
        "https://www.ecb.europa.eu/press/press_conference/monetary-policy-statement/2023/html/ecb.is230316~6c10b087b5.en.html":"0323",
        "https://www.ecb.europa.eu/press/press_conference/monetary-policy-statement/2023/html/ecb.is230504~f242392c72.en.html":"0523",
        "https://www.ecb.europa.eu/press/press_conference/monetary-policy-statement/2023/html/ecb.is230615~3de9d68335.en.html":"0623",
        "https://www.ecb.europa.eu/press/press_conference/monetary-policy-statement/2023/html/ecb.is230727~e0a11feb2e.en.html":"0723",
        "https://www.ecb.europa.eu/press/press_conference/monetary-policy-statement/2023/html/ecb.is230914~686786984a.en.html":"0923",
        "https://www.ecb.europa.eu/press/press_conference/monetary-policy-statement/2023/html/ecb.is231026~c23b4eb5f0.en.html":"1023",
        "https://www.ecb.europa.eu/press/press_conference/monetary-policy-statement/2023/html/ecb.is231214~df8627de60.en.html":"1223",
        "https://www.ecb.europa.eu/press/press_conference/monetary-policy-statement/2024/html/ecb.is240125~db0f145c32.en.html":"0124",
        "https://www.ecb.europa.eu/press/press_conference/monetary-policy-statement/2024/html/ecb.is240307~314650bd5c.en.html":"0324",
        "https://www.ecb.europa.eu/press/press_conference/monetary-policy-statement/2024/html/ecb.is240411~9974984b58.en.html":"0424",
        "https://www.ecb.europa.eu/press/press_conference/monetary-policy-statement/2024/html/ecb.is240606~d32cd6cc8a.en.html":"0624"
        }
        



urls_fed = {
    "https://www.federalreserve.gov/mediacenter/files/FOMCpresconf20200303.pdf": "0320",
    "https://www.federalreserve.gov/mediacenter/files/FOMCpresconf20200610.pdf": "0620",
    "https://www.federalreserve.gov/mediacenter/files/FOMCpresconf20200729.pdf": "0720",
    "https://www.federalreserve.gov/mediacenter/files/FOMCpresconf20200916.pdf": "0920",
    "https://www.federalreserve.gov/mediacenter/files/FOMCpresconf20201216.pdf": "1220",
    "https://www.federalreserve.gov/mediacenter/files/FOMCpresconf20210127.pdf": "0121",
    "https://www.federalreserve.gov/mediacenter/files/FOMCpresconf20210428.pdf": "0421",
    "https://www.federalreserve.gov/mediacenter/files/FOMCpresconf20210616.pdf": "0621",
    "https://www.federalreserve.gov/mediacenter/files/FOMCpresconf20210728.pdf": "0721",
    "https://www.federalreserve.gov/mediacenter/files/FOMCpresconf20210922.pdf": "0921",
    "https://www.federalreserve.gov/mediacenter/files/FOMCpresconf20211215.pdf": "1221",
    "https://www.federalreserve.gov/mediacenter/files/FOMCpresconf20220126.pdf": "0122",
    "https://www.federalreserve.gov/mediacenter/files/FOMCpresconf20220316.pdf": "0322",
    "https://www.federalreserve.gov/mediacenter/files/FOMCpresconf20220504.pdf": "0522",
    "https://www.federalreserve.gov/mediacenter/files/FOMCpresconf20220615.pdf": "0622",
    "https://www.federalreserve.gov/mediacenter/files/FOMCpresconf20220727.pdf": "0722",
    "https://www.federalreserve.gov/mediacenter/files/FOMCpresconf20220921.pdf": "0922",
    "https://www.federalreserve.gov/mediacenter/files/FOMCpresconf20221102.pdf": "1122",
    "https://www.federalreserve.gov/mediacenter/files/FOMCpresconf20221214.pdf": "1222",
    "https://www.federalreserve.gov/mediacenter/files/FOMCpresconf20230201.pdf": "0223",
    "https://www.federalreserve.gov/mediacenter/files/FOMCpresconf20230322.pdf": "0323",
    "https://www.federalreserve.gov/mediacenter/files/FOMCpresconf20230503.pdf": "0523",
    "https://www.federalreserve.gov/mediacenter/files/FOMCpresconf20230614.pdf": "0623",
    "https://www.federalreserve.gov/mediacenter/files/FOMCpresconf20230726.pdf": "0723",
    "https://www.federalreserve.gov/mediacenter/files/FOMCpresconf20230920.pdf": "0923",
    "https://www.federalreserve.gov/mediacenter/files/FOMCpresconf20231101.pdf": "1123",
    "https://www.federalreserve.gov/mediacenter/files/FOMCpresconf20231213.pdf": "1223",
    "https://www.federalreserve.gov/mediacenter/files/FOMCpresconf20240131.pdf": "0124",
    "https://www.federalreserve.gov/mediacenter/files/FOMCpresconf20240320.pdf": "0324",
    "https://www.federalreserve.gov/mediacenter/files/FOMCpresconf20240501.pdf": "0524"
}


import requests
from bs4 import BeautifulSoup
import PyPDF2
import pandas as pd
from io import BytesIO

# Define the phrases to count
phrases = ["data-dependent", "data",'forecast']

# Create an empty DataFrame to store the counts
mentions = pd.DataFrame(columns=phrases)

for url, date in urls_fed.items():
    print(url)
    
    # Fetch the content from the URL
    response = requests.get(url)
    content = response.content
    
    # Parse the PDF content using PyPDF2
    pdf_file = BytesIO(content)
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    
    text = ""
    for page_num in range(len(pdf_reader.pages)):
        page = pdf_reader.pages[page_num]
        text += page.extract_text()
    
    text = text.lower()
    
    # Count the occurrences of each phrase
    counts = {phrase: text.count(phrase) for phrase in phrases}
    
    # Print the results and update the DataFrame
    for phrase, count in counts.items():
        print(f"The phrase '{phrase}' appears {count} times in the document.")
        mentions.loc[date, phrase] = count





boe_transcripts_dict = {
    "https://www.bankofengland.co.uk/-/media/boe/files/monetary-policy-summary-and-minutes/2024/monetary-policy-summary-and-minutes-february-2024.html": "0224",
    "https://www.bankofengland.co.uk/-/media/boe/files/monetary-policy-summary-and-minutes/2023/monetary-policy-summary-and-minutes-september-2023.html": "0923",
    "https://www.bankofengland.co.uk/-/media/boe/files/monetary-policy-summary-and-minutes/2023/monetary-policy-summary-and-minutes-november-2023.html": "1123",
    "https://www.bankofengland.co.uk/-/media/boe/files/monetary-policy-summary-and-minutes/2023/monetary-policy-summary-and-minutes-august-2023.html": "0823",
    "https://www.bankofengland.co.uk/-/media/boe/files/monetary-policy-summary-and-minutes/2022/monetary-policy-summary-and-minutes-december-2022.html": "1222",
    "https://www.bankofengland.co.uk/-/media/boe/files/monetary-policy-summary-and-minutes/2021/monetary-policy-summary-and-minutes-november-2021.html": "1121",
    "https://www.bankofengland.co.uk/-/media/boe/files/monetary-policy-summary-and-minutes/2020/monetary-policy-summary-and-minutes-may-2020.html": "0520",
    "https://www.bankofengland.co.uk/-/media/boe/files/monetary-policy-summary-and-minutes/2020/monetary-policy-summary-and-minutes-november-2020.html": "1120",
    "https://www.bankofengland.co.uk/-/media/boe/files/monetary-policy-summary-and-minutes/2021/monetary-policy-summary-and-minutes-may-2021.html": "0521",
    "https://www.bankofengland.co.uk/-/media/boe/files/monetary-policy-summary-and-minutes/2022/monetary-policy-summary-and-minutes-february-2022.html": "0222",
    "https://www.bankofengland.co.uk/-/media/boe/files/monetary-policy-summary-and-minutes/2023/monetary-policy-summary-and-minutes-may-2023.html": "0523",
    "https://www.bankofengland.co.uk/-/media/boe/files/monetary-policy-summary-and-minutes/2021/monetary-policy-summary-and-minutes-august-2021.html": "0821"
}





import requests
from bs4 import BeautifulSoup
import PyPDF2
import pandas as pd
from io import BytesIO

# Define the phrases to count
phrases = ["data-dependent", "data"]

# Create an empty DataFrame to store the counts
mentions = pd.DataFrame(columns=phrases)

for url, date in boe_transcripts_dict.items():
    print(url)
    
    # Fetch the content from the URL
    response = requests.get(url)
    content = response.content
    
    # Parse the PDF content using PyPDF2
    pdf_file = BytesIO(content)
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    
    text = ""
    for page_num in range(len(pdf_reader.pages)):
        page = pdf_reader.pages[page_num]
        text += page.extract_text()
    
    text = text.lower()
    
    # Count the occurrences of each phrase
    counts = {phrase: text.count(phrase) for phrase in phrases}
    
    # Print the results and update the DataFrame
    for phrase, count in counts.items():
        print(f"The phrase '{phrase}' appears {count} times in the document.")
        mentions.loc[date, phrase] = count








import requests
from bs4 import BeautifulSoup



mentions_ecb = pd.DataFrame(columns = phrases)

for url in urls_ecb:
    print(url)


    # Fetch the content from the URL
    response = requests.get(url)
    content = response.content
    
    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(content, 'html.parser')
    text = soup.get_text().lower()
    
    # Define the phrases to count
    phrases = ["data-dependent", "data",'forecast']
    
    # Count the occurrences of each phrase
    counts = {phrase: text.count(phrase) for phrase in phrases}
    
    
    # Print the results
    for phrase, count in counts.items():
        print(f"The phrase '{phrase}' appears {count} times in the document.")
        mentions_ecb.loc[urls[url],f'{phrase}'] = count 
    









# Have revisions been larger than average in the last couple years?


site = "https://www.federalreserve.gov/newsevents/speech/2023-speeches.htm'
https://www.federalreserve.gov/newsevents/speech/2023-speeches/newsevents/speech/bowman20230807a.htm

import requests

from bs4 import BeautifulSoup

def extract_all_links(site):
    
    html = requests.get(site).text
    
    soup = BeautifulSoup(html, 'html.parser').find_all('a')
    
    links = [link.get('href') for link in soup]
    
    return links

site_link = input('Enter URL of the site : ')

all_links = extract_all_links(site_link)

print(all_links)


'newsevents/speech' in all_links




import requests
from bs4 import BeautifulSoup
 
 
url = 'https://www.ecb.europa.eu/press/press_conference/monetary-policy-statement/html/index.en.html'
reqs = requests.get(url)
soup = BeautifulSoup(reqs.text, 'html.parser')
 
urls = []
for link in soup.find_all('a'):
    if '0606' in link.get('href'):
        print(link.get('href'))
    # print(link.get('href'))
    
    
    






df_ecb = pd.read_csv("C:/Users/rfield/Downloads/all_ECB_speeches.csv", index_col=0)
counts_ecb = df_ecb.apply(lambda row: row.astype(str).str.lower().str.count('data').sum(), axis=1)

counts_ecb.index = pd.to_datetime(counts_ecb.index)

plt.plot((counts_ecb.groupby(pd.Grouper(freq='M')).sum() / counts_ecb.groupby(pd.Grouper(freq='M')).count()).dropna().rolling(12).mean())




df.apply(lambda row: row.astype(str).str.lower().str.count('data').sum(), axis=1)
counts_fed = df.apply(lambda row: row.astype(str).str.lower().str.count('data').sum(), axis=1)
counts_fed.index = pd.to_datetime(df['date'])


plt.plot((counts_ecb.groupby(pd.Grouper(freq='M')).sum() / counts_ecb.groupby(pd.Grouper(freq='M')).count()).dropna().rolling(12).mean(), label ='ecb')
plt.plot((counts_fed.groupby(pd.Grouper(freq='M')).sum() / counts_fed.groupby(pd.Grouper(freq='M')).count()).dropna().rolling(12).mean(), label='fed')
plt.legend()




counts_ecb
counts_fed
ecb_monthly = (counts_ecb.groupby(pd.Grouper(freq='M')).sum() / counts_ecb.groupby(pd.Grouper(freq='M')).count()).dropna()
fed_monthly = (counts_fed.groupby(pd.Grouper(freq='M')).sum() / counts_fed.groupby(pd.Grouper(freq='M')).count()).dropna()



# Define your Excel writer
writer = pd.ExcelWriter('output.xlsx', engine='xlsxwriter')

# Write each DataFrame to a separate worksheet
counts_ecb.to_excel(writer, sheet_name='ecb', index=True)
counts_fed.to_excel(writer, sheet_name='fed', index=True)
ecb_monthly.to_excel(writer, sheet_name='ecb_monthly', index=True)
fed_monthly.to_excel(writer, sheet_name='fed_monthly', index=True)

# Save the Excel file
writer.save()





def count_word_in_file(file_path, word):
    try:
        # Open the file with the correct encoding
        with open(file_path, 'r', encoding='utf-8') as file:
            # Read the entire file content
            content = file.read()
            
            # Count occurrences of the word
            count = content.count(word)
            
            return count
    except FileNotFoundError:
        print(f"File '{file_path}' not found.")
        return 0  # Return 0 if file is not found
    except UnicodeDecodeError:
        print(f"Error decoding file '{file_path}'. Try using a different encoding.")
        return -1  # Return -1 or handle the error as appropriate

# Example usage:
file_path = 'C:/Users/rfield/Downloads/t.txt'  # Replace with your file path
word_to_count = 'data'

# Count occurrences of 'data' in the file
result = count_word_in_file(file_path, word_to_count)
if result >= 0:
    print(f"The word '{word_to_count}' appears {result} times in the file.")
