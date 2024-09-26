#########################################################################
# 1. Import modules
#########################################################################
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
from pathlib import Path
from datetime import datetime, timedelta
import macrobond_module as md
import matplotlib.pyplot as plt
from pathlib import Path

import functions_fx_scorecard as fxs # Find this saved in c:/Users/rfield/
import statsmodels.api as sm

geo_uni = ['usd','gbp','eur','jpy','sek','nok','chf','cad','nzd','aud']

#########################################################################
# 3. Import and clean raw data
#########################################################################

# Read in and clean the data
path = "Z:/Global strategy team/GAA frameworks/DM FX and FI/FX/FX_SCORECARD/fx_scorecard_input.xlsx"

dfs_raw =(
      pd.read_excel(path, 'fx'),pd.read_excel(path, 'carry'),
      pd.read_excel(path, 'realised_vol'),
       pd.read_excel(path, 'implied_vol_1m'),
       pd.read_excel(path, 'implied_vol_3m'),
       pd.read_excel(path, 'implied_vol_1y'),
       pd.read_excel(path, 'risk_reversal_25d_1m'),
       pd.read_excel(path, 'risk_reversal_25d_3m'),
      pd.read_excel(path, 'risk_reversal_10d_1m'),
      pd.read_excel(path, 'risk_reversal_10d_3m'),
      pd.read_excel(path, 'forwards_1m'),
      pd.read_excel(path, 'forwards_3m'),
      pd.read_excel(path, 'forward_returns')
      )

demi_pairs = dfs_raw[0].columns[1:].str.lower().str.replace(' ', '')

row_indices = (3,3,5,5,5,5,5,5,5,5,5,5,5)
names = ('fx','1y1y_forward','rel_vol','imp_vol_1m','imp_vol_3m','imp_vol_1y','rr_25d_1m','rr_25d_3m','rr_10d_1m','rr_10d_3m','forwards_1m','forwards_3m','forward_returns')

dfs = {}

for i, df in enumerate(dfs_raw):
    clean = fxs.clean_excel(df, row_indices[i], False)
    dfs[names[i]] = clean
    
# Then do some extra cleaning

## clean fx
dfs['fx'].columns = dfs['fx'].columns.str.replace(' ','').str.lower()
## Clean forwards
dfs['1y1y_forward'].columns = ['usd','eur','gbp','cad','chf','sek','nok','aud','nzd','jpy']
# Clean forward returns
dfs['forward_returns'].columns = dfs['forward_returns'].columns.str.replace('TL Curncy','').str.lower()


rr_geo = ['gbpusd','eurgbp','gbpjpy','eursek','usdsek','eurnok','usdnok','eurusd','usdjpy','usdcad','nzdusd','audusd','audnzd','audjpy','usdchf','eurchf']
v_geo = ['gbpusd','eurgbp','gbpjpy','eursek','usdsek','eurnok','usdnok','eurusd','usdjpy','usdcad','nzdusd','audusd','audnzd','audjpy','usdchf','eurchf']

keys = [label for label in names if label not in ['fx','1y1y_forward','forward_returns']]

[dfs[key].set_axis(rr_geo, axis=1, inplace=True) for key in keys]

# Some JPY pairs have been rescaled by bloomberg, so we need to fix this
scaled_pairs = ['jpynok','jpysek','jpychf','jpygbp','sekchf','nokchf','jpyeur']

dfs['fx'][scaled_pairs] = dfs['fx'][scaled_pairs] / 100


# Create the reverse pairs for each dataframe 

for df in names:
    if df == '1y1y_forward' or df == 'imp_vol_1m' or df == 'imp_vol_3m' or df == 'imp_vol_1y' or df == 'rel_vol' or df =='forward_returns':
        continue
    elif df == 'fx':
        dfs[df] = fxs.reverse_pair(dfs[df], sign = False)
    else:
        dfs[df] = fxs.reverse_pair(dfs[df], sign = True)


#########################################################################
# 4. Generate FX returns
#########################################################################
# Calculate returns
returns = dfs['forward_returns'].resample('M').last().pct_change().dropna()

returns_daily = dfs['forward_returns'].pct_change().dropna()

returns = fxs.reverse_pair(returns, sign = True)
returns_daily = fxs.reverse_pair(returns_daily, sign = True)

#########################################################################
# 5. Factor 1: Rate expectations
# Trade on differentials in the third component differential
#########################################################################

# Import all yields for all countries and tenors

yields = fxs.clean_excel(pd.read_excel('Z:/Global strategy team/GAA frameworks/DM FX and FI/FX/FX_SCORECARD/yields.xlsx'), 4, True)
geo = ['us','gb','de','jp','se','no','ch','ca','nz','au']

# Now run a 2 year rolling sample

dates = pd.to_datetime(yields.index)


master_component_1 = []
master_component_2 = []
master_component_3 = []


component_1 = pd.DataFrame(index = dates, columns = geo)
component_2 = pd.DataFrame(index = dates, columns = geo)
component_3 = pd.DataFrame(index = dates, columns = geo)

i=3
for date in dates:
    for country in geo:
        if date > dates[-1] + pd.DateOffset(years=-i) + pd.DateOffset(days=-3):
            break
        
        
        sample_dates = pd.date_range(date, date + pd.DateOffset(years=i))
        common_indices = sample_dates.intersection(dates)
        columns = [col for col in yields.columns if country in col]
        sample = yields.loc[common_indices, columns]
        sample = sample.apply(pd.to_numeric, errors='coerce')
        
        
        pca = fxs.PCA(sample,3)
        component_1.loc[date + pd.DateOffset(years=i), country] = pca[-1][0]
        component_2.loc[date + pd.DateOffset(years=i), country] = pca[-1][1]
        component_3.loc[date + pd.DateOffset(years=i), country] = pca[-1][2]
    
master_component_1.append(component_1)
master_component_2.append(component_2)
master_component_3.append(component_3)




# Now actually try and trade on this


_1_monthly = component_1.loc[dates].dropna().resample('M').last()
_1_monthly.columns = geo_uni

_2_monthly = component_2.loc[dates].dropna().resample('M').last()
_2_monthly.columns = geo_uni

_3_monthly = component_3.loc[dates].dropna().resample('M').last()
_3_monthly.columns = geo_uni

_1_daily = component_1.loc[dates].dropna()
_1_daily.columns = geo_uni

_2_daily = component_2.loc[dates].dropna()
_2_daily.columns = geo_uni

_3_daily = component_3.loc[dates].dropna()
_3_daily.columns = geo_uni

l = _1_daily
s = _2_daily
c = _3_daily

for j in range(1,6):
    plt.plot(fxs.portfolio(fxs.mapping(_3_daily.astype(float)), -1, returns_daily, j, False)['cum_return'], label = f'Component 3 {j} pairs')
    plt.legend()
    plt.title(f'{i} year sample')
plt.show()


for j in range(1,6):
    plt.plot(fxs.portfolio(fxs.mapping(_2_monthly.astype(float)).loc['2023-12-01':], -1, returns, j, False)['cum_return'], label = f'Component 3 {j} pairs')
    plt.legend()
    plt.title(f'{i} year sample')
plt.show()




returns.loc['2004-09-30':'2005-01-31'][['usdgbp','usdeur','usdsek','usdnok','usdchf','usdjpy','usdcad','usdaud','usdnzd']].mean(axis=1)


plt.plot(fxs.portfolio(fxs.mapping(_2_monthly), 1, returns, 1, False)['cum_return'])



test = _3_monthly


_3_monthly = master_component_3[2].loc[dates].dropna()
_3_monthly.columns = geo_uni




# Only trade if curvature differential is above a certain number
threshold = -0.55

threshold_strategy = fxs.mapping(_3_monthly)
threshold_strategy[threshold_strategy > threshold] = 0
    
for i in range(1,6):
    plt.plot(fxs.portfolio(threshold_strategy, -1, returns, 1, False)['cum_return'], label = f'{i} Pairs')
    plt.legend()
    

fxs.portfolio(threshold_strategy, -1, returns, 1, False)
    
# Best performance comes from 1 pair and component 3 (curvature)        
fxs.portfolio(fxs.mapping(_3_monthly), -1, returns, 1, False)
        








test = fxs.portfolio(fxs.mapping(_3_monthly), -1, returns, 1, False)
test2 = pd.DataFrame(index=test.index)
test2['position'] = None
for date in test.index:
    value = test.loc[date,0][0]
    test2.loc[date,'position'] = value
    
test2 ['binary'] = 1
choices = test2.groupby('position').sum('binary')
test2





# If curvature looks good, why not just trade on a 2s10s30s butterfly?
# Does the trade still look good trading a butterfly?
butterfly = pd.DataFrame(index = yields.index, columns = geo)
slope = pd.DataFrame(index = yields.index, columns = geo)

for country in geo:
    df = yields[[col for col in yields.columns if ('2y' in col or '5y' in col or '10y' in col) and country in col]]
    wing1 = yields[country + '2y']
    wing2 = yields[country + '10y']
    body = yields[country + '5y']
    curvature = 2 * body - wing1 - wing2
    slope_ = wing2 - wing1
    butterfly[country] = curvature
    slope[country] = slope_

butterfly.columns = geo_uni
butterfly = butterfly.astype(float)
butterfly = butterfly.apply(lambda x: pd.to_numeric(x))
butterfly = fxs.mapping(butterfly)

for i in range(1,6):
    plt.plot(fxs.portfolio(fxs.mapping(butterfly.resample('M').last().dropna()), 1, returns, i, False)['cum_return'])
plt.show()


threshold = 0.3

threshold_strategy_butterfly = fxs.mapping(butterfly.dropna())
threshold_strategy_butterfly[threshold_strategy_butterfly < threshold] = 0

for i in range(1,6):
    plt.plot(fxs.portfolio(threshold_strategy_butterfly.resample('M').last().dropna(), 1, returns, i, False)['cum_return'])
plt.show()





# 15 - 20 obs differences look the best

yields = md.macrobond_daily(['us2ygov','gb2ygov','de2ygov','jp2ygov','se2ygov','no2ygov','ch2ygov','ca2ygov','nz2ygov','au2ygov'])
yields.columns = geo_uni
yields = fxs.mapping(yields)

for j in range(1,6):
    plt.plot(fxs.portfolio(yields.resample('M').last().dropna(),1,returns,j,False)['cum_return'], label = f'{j}')
    plt.legend()
    plt.title(f'{i} day change')
plt.show()

for j in range(1,6):
    plt.plot(fxs.portfolio(fxs.mapping(dfs['1y1y_forward'].resample('M').last().dropna()),1,returns,j,False)['cum_return'], label = f'{j}')
    plt.legend()
plt.show()


for j in [5,10,15,20,25,30]:

    fwd_swp = fxs.mapping(dfs['1y1y_forward'].dropna()).diff(j).dropna().resample('M').last()
    
    
    for i in range(1,6):
        plt.plot(fxs.portfolio(fwd_swp.diff(j).dropna(),-1,returns,i,False)['cum_return'], label = f'{i}')
    
    plt.legend()
    plt.show()








common_indicates = fxs.mapping(dfs['1y1y_forward'].dropna())['gbpusd'].index.intersection(dfs['forwards_1m']['gbpusd'].index)
common_indicates = common_indicates[-100:]

plt.subplots(figsize=(12, 6))
plt.plot(fxs.mapping(dfs['1y1y_forward'].dropna())['gbpusd'].loc[common_indicates], label = 'rate_diff')
plt.twinx()
plt.plot(dfs['forwards_1m']['gbpusd'].loc[common_indicates], label = 'fwd_diff1', color='red')
plt.legend()
plt.show()


plt.plot(fxs.portfolio(-dfs['forwards_1m'].dropna(),1,returns,1,False)['cum_return'])


# Let's try the forward rate premium puzzle
fwd_m = dfs['forwards_1m'].resample('M').last()
plt.plot(fxs.portfolio(fwd_m.dropna(),1,returns,3,False)['cum_return'])

plt.plot(dfs['forwards_3m']['gbpusd'].dropna())




###################################################################################################################################
## Let's try Macrosynergy UIP/carry strategy
##################################################################################################################################


df = pd.DataFrame()

for file in ['Z:/Global strategy team/GAA frameworks/DM FX and FI/Fixed Income/FI Scorecard/Final Scorecard/daily_automated/oe_forecasts_fair_value.xlsx','Z:/Global strategy team/GAA frameworks/DM FX and FI/Fixed Income/FI Scorecard/Final Scorecard/daily_automated/oe_forecasts_2020_onwards.xlsx']:
    data = pd.read_excel(file)
    data.index = data.iloc[:,0]
    data = data[[country + '_cpi' for country in geo]]
    df = df.append(data)
    
df = df[:163].append(df[209:])
df.index = pd.to_datetime(df.index)
df = df.resample('M').last()
df.columns = ['usd','gbp','eur','jpy','sek','nok','chf','cad','nzd','aud']
df = df 

cpi_diff = fxs.mapping(df)
forward3m = dfs['forwards_3m'].dropna()



cpi_diff = cpi_diff[forward3m.columns]

indices = forward3m.index.intersection(cpi_diff.index)
cpi_diff = cpi_diff.loc[indices]
forward3m = forward3m.loc[indices]

# Non jpy * 1000
exjpy_cols = [col for col in real_carry.columns if 'jpy' not in col]
real_carry = forward3m - cpi_diff * 1000

jpy_cols = [col for col in real_carry.columns if 'jpy' in col]
real_carry[jpy_cols] = forward3m[jpy_cols] - cpi_diff[jpy_cols] * 1000

real_carry = real_carry[[col for col in real_carry.columns if 'nzd' not in col]]


for i in range(1,6):
    plt.plot(fxs.portfolio(real_carry, 1, returns, i, False)['cum_return'], label =f'{i} pairs')
    plt.legend()

plt.show()

# Valuation adjustment

indices = fv_dev.index.intersection(real_carry.index)
fv_dev_strat = fv_dev.loc[indices,real_carry.columns] / 0.05 + 1

real_carry = real_carry * fv_dev_strat

for i in range(1,6):
    plt.plot(fxs.portfolio(real_carry, 1, returns, i, False)['cum_return'], label =f'{i}')
    plt.legend()
    
plt.show()


# Try with bonds
cpi_diff = fxs.mapping(df) * 100
cpi_diff = cpi_diff[[col for col in cpi_diff.columns if 'nzd' not in col]]
cpi_diff = cpi_diff.resample('D').ffill()

yields = md.macrobond_daily(['us1ygov','gb1ygov','de1ygov','jp1ygov','se1ygov','no2ygov','ch1ygov','ca1ygov','au1ygov']).dropna()
yields.columns = ['usd','gbp','eur','jpy','sek','nok','chf','cad','aud']

yields = fxs.mapping(yields)

common_indices_carry = yields.index.intersection(cpi_diff.index)

yields = yields.loc[common_indices_carry] - cpi_diff.loc[common_indices_carry]



for i in range(1,6):
    plt.plot(fxs.portfolio(yields.resample('M').last(), -1, returns, i, False)['cum_return'], label =f'{i}')
    plt.legend()
    
plt.show()

# Now try add the valuation factor
indices = fv_dev.index.intersection(yields.index)
fv_dev = fv_dev.loc[indices]
yields = yields.loc[indices]

for z in [0.15,0.3,0.45,0.6,0.75,0.9,1]:
    
    for i in range(1,6):
        plt.plot(fxs.portfolio(yields * (z*fv_dev+1), -1, returns, i, False)['cum_return'], label =f'{i}')
        plt.legend()
        plt.title(f'Valuation Factor {z} apply to real carry differntial')
        
    plt.show()

carry_real = yields * (0.45*fv_dev.resample('D').ffill().loc[common_indices_carry]+1)




for i in range(1,6):
    plt.plot(fxs.portfolio(yields  * (0.45*fv_dev+1), -1, returns, i, False)['cum_return'], label =f'{i}')
    plt.legend()











#########################################################################
# 5. Factor 2: BEER-implied fair value
# REBUILD DvA's model
#########################################################################
path = 'Z:/Global strategy team/GAA frameworks/DM FX and FI/FX/FX_SCORECARD/BEERsG10_quarterly.xlsx'


beers_pairs = ('AUDUSD','NZDUSD','GBPUSD','USDCAD','USDJPY','USDCHF','USDNOK','EURUSD','USDSEK')

beers_input = pd.DataFrame()
for pair in beers_pairs:
    clean = fxs.clean_excel(pd.read_excel(path, pair), 3, True)
    clean = clean.loc['1993-03-31':]
    dates = clean.index

    clean.columns = ["GDP","REALFX","dfpricelevel","ToT","Spot"]
    date_sequence = range(1, len(clean)+1)
    clean[['Time', 'Cross']] = [date_sequence,pair]
    clean = sm.add_constant(clean)
    
    clean['log_GDP'] = np.log(pd.to_numeric(clean['GDP']))
    clean['log_ToT'] = np.log(pd.to_numeric(clean['ToT']))
    clean['log_REALFX'] = np.log(pd.to_numeric(clean['REALFX']))
    clean = clean.join(pd.get_dummies(clean['Cross']))
    clean = clean.drop('Cross', axis =1 ).astype(float).join(clean['Cross'])
    clean['date'] = dates


    

    beers_input = pd.concat([beers_input,clean], ignore_index=True)
    
beers_input[[i for i in beers_pairs]] = beers_input[[i for i in beers_pairs]].applymap(lambda x: 1 if x == 1 else 0)

beers_input['prediction'] = np.nan

# Expanding window

params = pd.DataFrame(index = clean.index, columns = ['log_GDP','log_ToT'])
params_rolling = pd.DataFrame(index = clean.index, columns = ['log_GDP','log_ToT'])

for numeric in date_sequence:
    if numeric < 21: # 3 year rolling window?
        continue
    
    dates_subset = dates[:numeric] # expanding window
    df = beers_input[beers_input['date'].isin(dates_subset)]

    model = sm.OLS(df['log_REALFX'], df[['log_GDP','log_ToT','AUDUSD','NZDUSD','GBPUSD','USDCAD','USDJPY','USDCHF','USDNOK','EURUSD','USDSEK']])
    results = model.fit(cov_type='HC3')
    pred = results.predict()
    indexers = df[df['date'] == dates[numeric-1]].index
    pred = (np.exp(pred) * df['dfpricelevel']).loc[indexers]
    
    for i in range(0,len(beers_pairs)):
        beers_input.loc[indexers[i],'prediction'] = pred.loc[indexers[i]]



beers_input['residual'] = beers_input['Spot'] - beers_input['prediction'] # Positive residual means pair is undervalued

beers_input = beers_input.dropna()


# Now backtest the strategy
dates = pd.date_range(beers_input['date'].values[0], beers_input['date'].values[len(beers_input[beers_input['Cross'] == 'AUDUSD'])-1])
beers = pd.DataFrame(index = dates, columns = [pair.lower() for pair in beers_pairs])

for pair in beers_pairs:
    df = pd.DataFrame(index = dates)

    df_beers = beers_input[beers_input['Cross'] == pair][['date','prediction']]
    df_beers.index = df_beers['date']
    
    df = df.join(df_beers)
    df['prediction'] = df['prediction'].ffill()
    
    spot = pd.DataFrame(dfs['fx'][pair.lower()])
    
    df = df.join(spot)
    
    beers[pair.lower()] = df['prediction']
    
beers = beers.dropna().resample('M').last()

beers = fxs.reverse_pair(beers, False)

all_pairs = dfs['fx'].columns # all pairs
remaining_pairs = beers.columns.symmetric_difference(all_pairs) # Pairs that we need to calculate

beers_complete = pd.DataFrame(columns = all_pairs)
beers_complete[beers.columns] = beers

for pair in all_pairs:
    left = pair[:3]
    right = pair[3:]
    try:
        beers_complete[pair] = beers[pair]
        beers_complete[pair] = 1 / beers_complete[f'{right}{left}']
    except KeyError:
        try:
            beers_complete[f'{left}{right}'] = beers[f'{left}usd'] * beers[f'usd{right}']
        except KeyError:
            beers_complete[f'{left}{right}'] = beers[f'{left}eur'] * beers[f'eur{right}']
            
            
beers_complete = fxs.reverse_pair(beers_complete, False)
                    
# Now calculate deviations
fv_dev = pd.DataFrame(columns = all_pairs)
fx = dfs['fx'].resample('M').last()
for pair in all_pairs:
    temp = pd.DataFrame(beers_complete[pair])
    temp = temp.join(pd.DataFrame(fx[pair]), lsuffix = '_predict', rsuffix = '_spot')
    
    fv_dev[pair] = (temp[f'{pair}_predict'] / temp[f'{pair}_spot']) -1 # if fair value is above spot, then we think spot will appreciate
    

fv_dev = fv_dev.dropna()

# Test the strategy
plt.plot(fxs.portfolio(fv_dev,1,returns,5,False)['cum_return'])


# Suppose the second derivative must be negative to trade
fv_dev.diff()


# Suppose you only trade if deviation is more than 10%
threshold = 0.2
fv_dev_threshold = fv_dev[fv_dev > threshold]

plt.plot(fxs.portfolio(fv_dev,1,returns,5,False)['cum_return'])

# Suppose you only trade if the second derivative is negative (sell off is slowing)
fv_dev_moment = fv_dev
temp = fv_dev.diff().dropna() # second derivative

for date in fv_dev_moment.index[3:]:
    for pair in fv_dev_moment.columns:

        if temp.loc[date,pair] > 0: # undervaluation increases, trade
            fv_dev_moment.loc[date,pair] = 0
    
    
plt.plot(fxs.portfolio(fv_dev_moment,1,returns,3,False)['cum_return'])






#########################################################################
# 5. Factor 2: BEER-implied fair value
#########################################################################

# Generate factor #2. Value

## If Javier wants a recreation of the original scorecard 

beers_tickers = ['ih:mb:com:dbeeraudusd','ih:mb:com:dbeernzdusd','ih:mb:com:dbeereurusd','ih:mb:com:dbeergbpusd','ih:mb:com:dbeerusdcad',
                 'ih:mb:com:dbeerusdjpy','ih:mb:com:dbeerusdchf','ih:mb:com:dbeerusdnok','ih:mb:com:dbeerusdsek']

pairs_usd = ['audusd','nzdusd','eurusd','gbpusd','usdcad','usdjpy','usdchf','usdnok','usdsek']
pairs_inverse = ['usdaud','usdnzd','usdeur','usdgbp','cadusd','jpyusd','chfusd','nokusd','sekusd']


beers = md.macrobond_daily(beers_tickers)
beers.columns = pairs_usd

for i in range(9):
    beers[pairs_inverse[i]] = 1 / beers[pairs_usd[i]]

### Now import the list of pairs

pairs = pd.DataFrame(pd.read_excel("Z:/Global strategy team/GAA frameworks/DM FX and FI/FX/FX_SCORECARD/fx_pairs.xlsx")).columns.str.replace(' ', '')

### Calculate the beer estiamtes and spots for every possible pair via a dictionary
spot_ex_usd = {}
fx = dfs['fx']
for i in range(1, len(geo_uni)):
    for j in range(1, len(geo_uni)):
        if i == j:
            continue
        try:
            spot_ex_usd[f'{geo_uni[i]}{geo_uni[j]}'] = fx[f'{geo_uni[i]}usd'] * fx[f'usd{geo_uni[j]}']
        except KeyError:
            try:
                spot_ex_usd[f'{geo_uni[i]}{geo_uni[j]}'] = fx[f'usd{geo_uni[i]}'] / fx[f'usd{geo_uni[j]}']
            except KeyError:
                try:
                    spot_ex_usd[f'{geo_uni[i]}{geo_uni[j]}'] = fx[f'{geo_uni[i]}usd'] / fx[f'{geo_uni[j]}usd']
                except KeyError:
                    spot_ex_usd[f'{geo_uni[i]}{geo_uni[j]}'] = fx[f'usd{geo_uni[i]}'] * fx[f'{geo_uni[j]}usd']
                    
                    
for i in range(1,len(geo_uni)):
    spot_ex_usd[f'{geo_uni[i]}usd'] = fx[f'{geo_uni[i]}usd']
    spot_ex_usd[f'usd{geo_uni[i]}'] = 1/spot_ex_usd[f'{geo_uni[i]}usd']

spot = pd.DataFrame(spot_ex_usd)

beers_ex_usd = {}
for i in range(1, len(geo_uni)):
    for j in range(1, len(geo_uni)):
        if i == j:
            continue
        try:
            beers_ex_usd[f'{geo_uni[i]}{geo_uni[j]}'] = beers[f'{geo_uni[i]}usd'] * beers[f'usd{geo_uni[j]}']
        except KeyError:
            try:
                beers_ex_usd[f'{geo_uni[i]}{geo_uni[j]}'] = beers[f'usd{geo_uni[i]}'] / beers[f'usd{geo_uni[j]}']
            except KeyError:
                try:
                    beers_ex_usd[f'{geo_uni[i]}{geo_uni[j]}'] = beers[f'{geo_uni[i]}usd'] / beers[f'{geo_uni[j]}usd']
                except KeyError:
                    beers_ex_usd[f'{geo_uni[i]}{geo_uni[j]}'] = beers[f'usd{geo_uni[i]}'] * beers[f'{geo_uni[j]}usd']



beers = beers.join(pd.DataFrame(beers_ex_usd))

#### Now calculate log percentage deviations from fair value for each pair
##### beers & spot
beers_spot = spot.join(beers, lsuffix='_spot',rsuffix='_estimate').dropna()
pairs = spot.columns
fv_dev = pd.DataFrame(columns = pairs, index = beers_spot.index)


for i in range(len(pairs)):
    fv_dev[pairs[i]] = 0
    for j in range(len(beers_spot)):
        fv_dev[pairs[i]][j] = np.log(beers_spot[pairs[i].lower() + '_spot'][j] / beers_spot[pairs[i].lower() + '_estimate'][j])


#### Assign a value to each pair in each month, 0 -1 or 1 based on the magnitude of the deviation

fv_dev = fv_dev.resample('M').last()
portfolio_fv_dev = fxs.portfolio(fv_dev, -1, returns, 5, False)

fxs.factor_chart(portfolio_fv_dev, 'title', 1)














#########################################################################
# 6. Factor 3: Momentum
#########################################################################
fx = dfs['fx']
for a in [10,20]:
    for b in [1,2,3,4,5]:

        print(a, b)
        import calendar
        from datetime import date
        from dateutil.relativedelta import relativedelta
        
        fx = fx.dropna()
        
        # Get the last day of the current month
        last_day = calendar.monthrange(date.today().year, date.today().month)[1]
        
        # Create a new date object for the last day of the current month
        last_day_date = date(date.today().year, date.today().month, last_day)
        two_years_ago = last_day_date - timedelta(days=365 * 2)
        month_before_last = last_day_date - relativedelta(months=1)
        
        # Start at 650 giving us a starting point with 1.5 years from start of data
        # List of dates to extract
        d = pd.date_range('31/07/2003', last_day_date, freq='M')
        d_prev = pd.date_range('31/07/1999', two_years_ago, freq='M')
        
        # Extract the sample of data
        deposit = []
        date = []
        
        
        
        for i in range(0,len(d)):
            sample_hurst = fx.loc[d_prev[i]:d[i]] # 300 is the trailing training window
            # Calculate the Hurst exponents for the given window of data
            ex = fxs.get_hurst_exponent(sample_hurst, 30*a)
            deposit.append(ex)
        
        deposit = pd.DataFrame(deposit) - 0.5
        deposit.index = d
        deposit.columns = fx.columns
        
        
        
        # Hurst exponent & that month's return imply the sign and therefore the long or short position
        hurst = pd.DataFrame(index=deposit.index, columns= deposit.columns)
        pct_rtn = fx.resample('M').last().pct_change(b).dropna()
        
        for date in deposit.index:
            for country in deposit.columns:
                try:
                    if (pct_rtn.loc[date,country] < 0 and deposit.loc[date,country] < 0):
                        hurst.loc[date,country] = abs(deposit.loc[date,country])
                    elif (pct_rtn.loc[date,country] > 0 and deposit.loc[date,country] > 0):
                        hurst.loc[date,country] = abs(deposit.loc[date,country])
                    elif (pct_rtn.loc[date,country] < 0 and deposit.loc[date,country] > 0):
                        hurst.loc[date,country] = -abs(deposit.loc[date,country])
                    elif (pct_rtn.loc[date,country] > 0 and deposit.loc[date,country] < 0):
                        hurst.loc[date,country] = -abs(deposit.loc[date,country])
                except:
                    continue
        
        hurst = hurst.dropna().astype(float)
        
        plt.plot(fxs.portfolio(hurst,1,returns,5,False)['cum_return'], label = f'{a}{b}')
        plt.legend()

plt.show()
    







fxs.portfolio(hurst,-1,returns,5,False).join(pd.DataFrame(hurst.idxmax(axis=1)), lsuffix='brah',rsuffix='sunbeam')







hurst = hurst.applymap(lambda x: 0 if x < 0 else x)





## Try mean-reversion vs momentum violation of UIP strategy
import macrobond_module as mb
df = mb.macrobond_daily(['gb1mgov','us1mgov'])
df['gbus'] = 10 * (df['us1mgov'] - df['gb1mgov'])
df = dfs['forwards_1m'].join(df)[['gbpusd','gbus']].dropna()
df = df['gbpusd'] - df['gbus']
plt.plot(df)


# Step 1: Calculate monthly deviations from UIP
# ln(s_t+1) - ln(s_t) = ln(F_t) - ln(s_t)

dfs['forwards_1m']['gbpusd']
dfs['fx']['gbpusd']


dates = mb.macrobond_daily(['gb1mgov']).index.intersection(mb.macrobond_daily(['us1mgov']).index).intersection(dfs['forwards_1m'].index)
1m = mb.macrobond_daily(['gb1mgov'])
gb = mb.macrobond_daily(['gb1mgov'])
us = mb.macrobond_daily(['us1mgov']).loc[dates]

df = dfs['fx'].dropna()


# START HERE 


df = pd.DataFrame(columns = ['price'])    
df['price'] = dfs['fx']['gbpusd']








df = dfs['forward_returns'].dropna()
symbols = df.columns

import statsmodels.formula.api as smf


import pandas as pd
import statsmodels.api as sm
import numpy as np

class YourAlgorithm:
    def __init__(self, df):
        self.df = df
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

# Assuming df is your DataFrame containing data on 90 FX pairs
# Assuming df has columns like 'symbol' and 'price'
# Create an instance of YourAlgorithm with your data


df = dfs['forward_returns'].dropna()

uip = pd.DataFrame(index = df[1000:].resample('M').last().index, columns = df.columns)

#returns = dfs['forward_returns'].resample('D').last().pct_change()

for date in df[1000:].resample('M').last().index:
    print(date)
    
    your_algorithm = YourAlgorithm(np.log(df.astype(float)).loc[:date])
    # Retrieve the expected returns for all symbols
    expected_returns = your_algorithm.get_expected_returns()
    uip.loc[date] = expected_returns
    



uip = uip.astype(float)
uip_reverse = fxs.reverse_pair(uip, True)

uip_reverse = uip_reverse[[col for col in uip_reverse.columns if ('chf' not in col) and ('jpy' not in col)]]

for i in range(1,6):
    plt.plot(fxs.portfolio(uip_reverse.resample('M').last(), 1, returns,i, False)['cum_return'], label = f'{i} pairs')
    plt.legend()
plt.show()
    

plt.plot(fxs.portfolio(uip.dropna(axis=1), 1, returns,5, False)['cum_return'])




# Remove yen and chf

uip_exjpy = uip.loc['1990-01-03':]

uip_exjpy = uip

uip_exjpy = uip_exjpy.drop(uip_exjpy.filter(like='jpy',axis=1).columns,axis=1)


    
portfolio_fv_dev = fxs.portfolio(uip_exjpy, 1, returns, 5, False)

fxs.factor_chart(portfolio_fv_dev, 'title', 1)





#########################################################################
# X. Calculate returns using fx basket
#########################################################################


# Build monthly returns
pairwise_returns = spot.resample('M').last().pct_change()

pct_rtn_basket = pd.DataFrame(columns = geo_uni)

for i in range(10):
    pct_rtn_basket[geo_uni[i]] = pairwise_returns.loc[:, pairs.str.startswith(geo_uni[i])].mean(axis=1)



#########################################################################
# 7. Factor 4: 1 month Implied vs Realised Volatility
#########################################################################

#### Missing 7 years of data using bbberg calculated realised vol
#### Can fill this with own calculation
#### Need to also try tenors other than 1 month

# A large volatility risk premium implies that the market is more scared than it should be

common_indices = dfs['imp_vol_1m'].dropna().index.intersection(dfs['rel_vol'].dropna().index)
vrp = pd.DataFrame(index=common_indices, columns=v_geo)

for pair in v_geo:
    vrp[pair] = dfs['imp_vol_1m'].loc[common_indices][pair] - dfs['rel_vol'].loc[common_indices][pair]

vrp_monthly = vrp.resample('M').last()

for pair in ['gbpjpy','audjpy','usdjpy','eurnok','eurgbp']:
    plt.subplots(figsize=(12,4))
    plt.plot(dfs['imp_vol_1m'][pair].loc[common_indices], label = '1m_implied_vol')
    plt.plot(dfs['rel_vol'][pair].loc[common_indices], label = '1m_realised_vol')
    plt.title(f'{pair}')
    plt.legend()
    plt.show()

# STRATEGY1: Long pair with largest increase in monthly vrp
vrp_diff = vrp.diff().dropna()

vrp_diff = vrp_diff.apply(lambda x: pd.to_numeric(x))

vrp_diff = vrp_diff.resample('M').last()

for i in range(1,6):
    plt.plot(fxs.portfolio(vrp_diff, 1, returns, i, False)['cum_return'], label = f'{i} pairs')
    plt.legend()

plt.show()


# STRATEGY2: Go long the highest VRP pair, go long the side with the highest carry



carry = fxs.reverse_pair(fxs.mapping(dfs['1y1y_forward'])[vrp.columns], True)
common_indices = carry.index.intersection(vrp.index)
carry = carry.loc[common_indices].resample('M').last()
vrp2 = vrp.loc[common_indices].resample('M').last()

no_positions = 10

vrp2_portfolio = fxs.portfolio(vrp2, 1, returns, 5, False)


for date in vrp2_portfolio.index:
    for i in range(0,no_positions):
        pair = vrp2_portfolio.loc[date][i]
        positive = carry.loc[date, pair] > 0 # True is positive carry
        if positive == False: # If negative carry differential, invert the pair
            inverted_pair = f'{pair[3:]}{pair[:3]}'
            vrp2_portfolio.loc[date][i] = inverted_pair
            
            
portfolio = pd.DataFrame(vrp2_portfolio)
common_rows = returns.index.intersection(portfolio.index)
pct_rtn = returns.loc[common_rows].shift(-1)
portfolio = portfolio.loc[common_rows]
portfolio['return'] = None
        
for date in portfolio.index:
    positioning = vrp2_portfolio.loc[date]
    portfolio['return'].loc[date] = pct_rtn.loc[date,positioning].mean()
    portfolio['cum_return'] = np.cumprod(1+portfolio['return'])

plt.plot(portfolio['cum_return'], label = i+1)
plt.legend()

for i in range(1,6):
    plt.plot(fxs.portfolio(fxs.reverse_pair(vrp2, False),1,returns,i,False)['cum_return'])


# STRATEGY2.1: Do not trade the pair if the term structure has a negative slope

common_indices = dfs['imp_vol_3m'].index.intersection(dfs['imp_vol_1m'].index)
dfs['imp_vol_1m'] = dfs['imp_vol_1m'].loc[common_indices]
dfs['imp_vol_3m'] = dfs['imp_vol_3m'].loc[common_indices]

slope_1m_3m = (dfs['imp_vol_3m'] - dfs['imp_vol_1m']).resample('M').last().dropna()


for i in range(1,6):
    plt.plot(fxs.portfolio(fxs.reverse_pair(slope_1m_3m, False),1,returns,i,False)['cum_return'])






















vrp_monthly

# STRATEGY2 Go long highest vrp with highest carry

carry = fxs.mapping(dfs['1y1y_forward']).resample('M').last()
pairs = dfs['rel_vol'].columns
dates = dfs['rel_vol'].dropna().resample('M').last().index
vrp2 = pd.DataFrame(index = dates, columns = carry.columns)
for pair in pairs:
    vrp2[pair] = vrp_monthly[pair]

vrp2 = vrp2.apply(lambda x: pd.to_numeric(x))

# Long highest VRP

for i in range(1,6):

    plt.plot(fxs.portfolio(vrp2, 1, returns, i, False)['cum_return'], label = i)
    plt.legend()
plt.show()

vrp2 = vrp2.diff()

for date in dates:
    for pair in pairs:
        positive = carry.loc[date,pair] > 0 # True if rate differential is positive
        if positive == False:
            vrp2.loc[date,f'{pair[3:]}{pair[:3]}'] = vrp2.loc[date,pair]
            vrp2.loc[date,pair] = None
            
# Long highest VRP, the side of the highest carry         
            
for i in range(1,6):

    plt.plot(fxs.portfolio(vrp2, 1, returns, i, False)['cum_return'], label = i)
    plt.legend()
plt.show()


# STRATEGY2.1 do not trade the pair if iv  slope is positive
carry = fxs.mapping(dfs['1y1y_forward']).resample('M').last()
pairs = dfs['rel_vol'].columns
dates = dfs['rel_vol'].dropna().resample('M').last().index
vrp21 = pd.DataFrame(index = dates, columns = carry.columns)
for pair in pairs:
    vrp21[pair] = vrp_monthly[pair]

vrp21 = vrp21.apply(lambda x: pd.to_numeric(x))
vrp21 = vrp21.diff()


slope_1m_3m

for date in dates:
    for pair in pairs:
        negative = slope_1m_3m.loc[date,pair] > 0 # If False do not trade
        positive = carry.loc[date,pair] > 0 # True if rate differential is positive
        if negative == False:
            vrp21.loc[date,pair] = np.nan # If slope is negative then drop the obs
            
        if positive == False:
            vrp21.loc[date,f'{pair[3:]}{pair[:3]}'] = vrp21.loc[date,pair]
            vrp21.loc[date,pair] = np.nan



for i in range(1,6):
    plt.plot(fxs.portfolio(vrp21, 1, returns, i, False)['cum_return'], label = i)
    plt.legend()

plt.plot(fxs.portfolio(vrp21, 1, returns, 2, False)['cum_return'])
plt.legend()
plt.show()

test = fxs.portfolio(vrp21, 1, returns, 1, False)
test['vrp'] = np.nan
for date in test.index:
    if test.loc[date,'return'] == 0:
        continue
    pair = test.loc[date,0][0]
    test.loc[date,'vrp'] = vrp21.loc[date,pair]
    
    
test['group'] = pd.qcut(test.dropna()['vrp'], q=[0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0], labels=False, duplicates='drop')

plt.plot(test.dropna().groupby('group')['return'].mean())
vrp21

fxs.portfolio(vrp21.applymap(lambda x: np.nan if x < 0 else x),1, returns, 1, False)

# STRATEGY2.2 Only trade if VRP increases and realised vol decreases
carry = fxs.mapping(dfs['1y1y_forward']).resample('M').last()
pairs = dfs['rel_vol'].columns
dates = dfs['rel_vol'].dropna().resample('M').last().index
vrp22 = pd.DataFrame(index = dates, columns = carry.columns)
for pair in pairs:
    vrp22[pair] = vrp_monthly[pair]

vrp22 = vrp22.apply(lambda x: pd.to_numeric(x))
vrp22 = vrp22.diff()

test = pd.DataFrame(index = dfs['rel_vol'].resample('M').last().index, columns = dfs['rel_vol'].columns)

for date in dates:
    for pair in pairs:
        condition = vrp22.diff().loc[date,pair] > 0 and dfs['rel_vol'].diff(10).resample('M').last().loc[date,pair] < 0 # don't trade unless vrp is increasing and rel_vol decreasing
        test.loc[date,pair] = condition
        if condition == False:
            vrp22.loc[date,pair] = 0
            
            
        positive = carry.loc[date,pair] > 0 # True if rate differential is positive
        if positive == False:
            vrp22.loc[date,f'{pair[3:]}{pair[:3]}'] = vrp22.loc[date,pair]
            vrp22.loc[date,pair] = np.nan


vrp22 = vrp22.applymap(lambda x: np.nan if x == 0 else x)

for i in range(1,6):
    plt.plot(fxs.portfolio(vrp22, 1, returns, i, False)['cum_return'], label = i)
    plt.legend()
plt.show()

test = test.applymap(lambda x: 1 if x == True else 0)





    

# Try and create some summary table for Javier
for pair in vrp2.columns:
    pd.qcut(vrp2[pair], q=[0, 0.2, 0.4, 0.6, 0.8, 1.0], labels=False, duplicates='drop')


pairs = dfs['rel_vol'].columns
pairs = [f'{pair[:3]}{pair[3:]}' for pair in pairs]
reverse_pairs = [f'{pair[3:]}{pair[:3]}' for pair in pairs]

vrp_monthly_quantiles = pd.DataFrame()
for pair in pairs:
    reverse_pair = f'{pair[3:]}{pair[:3]}'
    pair_vrp = pd.DataFrame(vrp21[pair]).join(pd.DataFrame(vrp21[reverse_pair]), how='inner') # volatility risk premium
    pair_return = pd.DataFrame(returns[pair]).join(pd.DataFrame(returns[reverse_pair]), how='inner')
    pair_return = pair_return.shift(-1) # shifted returns
    


    combined = pd.DataFrame(index = pair_vrp.index)
    combined[[pair,pair + '_return']] = np.NaN
    
    for date in combined.index:
        if pd.isna(pair_vrp.loc[date, pair]): # if second currency has carry advantage
            combined.loc[date,'vrp'] = pair_vrp.loc[date, reverse_pair] 
            combined.loc[date,pair + '_return'] = pair_return.loc[date, reverse_pair]
            
        else: # If first currency has a carry advantage
            combined.loc[date,'vrp'] = pair_vrp.loc[date, pair] 
            combined.loc[date,pair + '_return'] = pair_return.loc[date, pair]
    
    combined = combined[['vrp',pair + '_return']]
    combined['grouped'] = pd.qcut(combined['vrp'], q=[0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0], labels=False, duplicates='drop')
    combined = combined.dropna()
    vrp_monthly_quantiles[pair] = combined.groupby('grouped')[pair + '_return'].mean()
    
    
    
    
    
    
    
    series = pair_vrp.sum(axis=1)
    
    
    vrp_monthly_quantiles[pair] = pd.qcut(combined['vrp'], q=[0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0], labels=False, duplicates='drop')
    


# Now calculate following months returns

q_returns = returns.shift(-1)
q_returns

quantiles = pd.DataFrame(index = [0, 1, 2, 3, 4, 5, 6, 7 ,8, 9])
for pair in pairs:
    temp = pd.DataFrame(vrp_monthly_quantiles[pair]).join(pd.DataFrame(q_returns[pair]), lsuffix='_vrp', rsuffix='_return')
    average = temp.groupby(pair+'_vrp')[pair+'_return'].mean()
    quantiles[pair] = average * 100


























# STRATEGY2: Use calculated realised vols
fx_complete = dfs['fx']

rel_vol = fxs.rel_vol_cal(fx_complete, fx_complete.columns).dropna()
imp_vol = dfs['imp_vol_1y']

common_indices = rel_vol.index.intersection(imp_vol.index)
common_columns = rel_vol.columns.intersection(imp_vol.columns)

rel_vol = rel_vol.loc[common_indices, common_columns]
imp_vol = imp_vol.loc[common_indices, common_columns]


vrp = pd.DataFrame(index=common_indices, columns=common_columns)
for pair in common_columns:
    vrp[pair] = imp_vol[pair] - rel_vol[pair]
    left = pair[:3]
    right = pair[3:]
    vrp[f'{right}{left}'] = - vrp[left+right]
    
    


vrp_diff = vrp.resample('M').last().dropna(axis=1).diff().dropna()

vrp_diff = vrp_diff.apply(lambda x: pd.to_numeric(x))



for i in range(1,6):
    plt.plot(fxs.portfolio(vrp_diff, -1, returns, i, False)['cum_return'], label =f'{i} pairs')
    plt.legend()

plt.show()



# STRATEGY3: Memory effects, VRP increase led by realised vol

# Only trade if there are memory effects
# This means currrent implied vol is high after realised vol has decreased
# I.e the VRP is rising but this increase is led by realised rather than implied
# Hence first derivative of VRP is positive, first derivative of realised vol is negative



# How to check whether it is led by realised vol?
# VRP must be increasing, and at least 50% of that increase 




# I have constructed my own realised volatility which is not great, but let's see if the trading strategies work on it anyway


df_r_comp = dfs['imp_vol_1m'].join(rel_vol, lsuffix = '_imp', rsuffix = '_rel_man')

vrp = pd.DataFrame(index=df_r_comp.index, columns=df_r_comp.columns)






for pair in v_geo:
    vrp[pair] = dfs['imp_vol_1m'].loc[common_indices][pair] - dfs['rel_vol'].loc[common_indices][pair]
    left = pair[:3]
    right = pair[3:]
    vrp[f'{right}{left}'] = - vrp[left+right]





pair = 'gbpusd'
temp = df_r_comp[[f'{pair}_imp', f'{pair}_rel_man', f'{pair}']]





##################################################################################
# 7. contd gets messy, let's try creating some summary statistics to start with, especially looking at individual pairs
##################################################################################




























#########################################################################
# 8. Factor 5: Risk reversal vs interest rate differential
#########################################################################

### Create and combine the datasets

on_tickers = ['us2ygov','gb2ygov','de2ygov','jp2ygov','se2ygov','no2ygov','ch2ygov','ca2ygov','nz2ygov','au2ygov']
yield_2y = md.macrobond_daily(on_tickers)
yield_2y.columns = geo_uni



r_diff = pd.DataFrame(columns = rr_geo)
key = 'rr_25d_1m'
rr = dfs[key].dropna()
rr.index = pd.to_datetime(rr.index)


for pair in rr_geo:
    left = pair[:3]
    right = pair[3:]
    r_diff[pair] = yield_2y[left] - yield_2y[right]
    r_diff[f'{right}{left}'] = - r_diff[left+right]
    rr[f'{right}{left}'] = - rr[left+right]
    
    
    
rr.index = pd.to_datetime(rr.index)

### Plot scatter charts of each pair rate differentials vs risk reversals
# for col in rr.columns:
#     labels = [f'{col}_rr',f'{col}_rdiff']
              
#     df = rr.join(r_diff, lsuffix='_rr', rsuffix='_rdiff')[labels]
#     df = df[abs(df[labels[0]]) < 4]
    
#     fxs.draw_date_coloured_scatterplot(labels, df)


### Crate strategy: trade on risk reversal fair value regressions
d_prev = pd.date_range(start='2006-01-31', end='2021-05-31', freq='M')
d = pd.date_range(start='2009-01-31', end='2024-05-31', freq='M')

rr_residuals = pd.DataFrame(index=d, columns = rr.columns)
rr_pred = pd.DataFrame(index=d, columns = rr.columns)



for date in d:  
    print(date)
    
    rr_temp = rr.loc[(date - pd.DateOffset(years=3)):date]
    
    
    rate_diff = fxs.mapping(yield_2y).loc[(date - pd.DateOffset(years=3)):date].diff().dropna()
    rate_diff = rate_diff.dropna()
    
    combined_rows = rr_temp.index.intersection(rate_diff.index)
    
    rr_temp = rr_temp.loc[combined_rows]
    rate_diff = rate_diff.loc[combined_rows]
    
    for pair in rr_temp.columns:
        X = rate_diff[pair].astype(float)
        X = sm.add_constant(X).astype(float)
        y = rr_temp[pair]
        y = y.astype(float)
        
    
        model = sm.OLS(y, X).fit(cov_type='HC3')
        
        
        
        if model.pvalues.loc[pair] > 0.1:
            rr_residuals.loc[date,pair] = model.resid[-1]
            rr_pred.loc[date,pair] = model.predict()[-1]
        else:
            rr_residuals.loc[date,pair] = 0
            rr_pred.loc[date,pair] = model.predict()[-1]
        

rr_residuals = rr_residuals.astype(float)



for i in range(1,6):
    print(fxs.portfolio(rr_residuals, -1, returns, i, False))
    plt.plot(fxs.portfolio(rr_residuals, -1, returns, i, False)['cum_return'], label =f'{i} pairs')
    plt.legend()
plt.show()











correlation_coeff = pd.DataFrame(index = rr_geo ,columns = ['rr_25d_1m', 'rr_25d_3m', 'rr_10d_1m', 'rr_10d_3m'])
for key in ['rr_25d_1m', 'rr_25d_3m', 'rr_10d_1m', 'rr_10d_3m']:
    rr = dfs[key]
    
    ### Plot scatter
    
    
    rr_rate_diff = rr.join(r_diff, lsuffix = '_rr', rsuffix = '_rdiff').astype(float)
    
    for col in rr_geo:
        x = rr_rate_diff[col + '_rr']
        x = x[abs(x)<4]
        # if x (rr) is greater than absolute 4, drop the observation
        
        y = rr_rate_diff[col +'_rdiff']
        y = y.loc[x.index]
        
        a, b = np.polyfit(x, y, 1)
        
        plt.figure()
        plt.scatter(x, y, label= f'{col} Correlation = {np.round(np.corrcoef(x,y)[0,1], 2)}')
        plt.plot(x, a*x+b, color = 'red')
        plt.title(f' {col.upper()}')
        plt.xlabel('risk reversal')
        plt.ylabel('2 year yield differential')
        plt.legend()
        
        correlation_coeff.loc[col, key] = np.round(np.corrcoef(x,y)[0,1], 2)
        
correlation_coeff.loc['average'] = correlation_coeff.mean(axis=0)
       




### Now  let's test some kind of strategy
### Risk reversal involves buying a call and selling a put, both of which have strikes equidistant from ATM
### If the market is pricing the cross to remain where it is over the maturity of the options, the risk reversal will be 0
### > 0, call > put, market is pricing cross to appreciate. < 0, call < put so market is pricing cross to depreciate
### Over a short horizon like 1 month or 3 month, standard factors like productivity or demographics or trade have practically zero bearing
### Our hypothesis is that over this horizon the primary driver is hot money flows driven by rate differentials
### 


# First make sure variables are integrated of order one
from statsmodels.tsa.stattools import adfuller

rr = dfs['rr_10d_1m']
rr_rate_diff = rr.join(r_diff, lsuffix = '_rr', rsuffix = '_rdiff').astype(float)

for variable in rr_rate_diff.columns:
    if 'diff' in variable:
        print(variable,adfuller(rr_rate_diff[variable].diff().dropna())[1])
    else:
        print(variable,adfuller(rr_rate_diff[variable])[1])

# risk reversals are stationary but rate differentials are non-stationary
# Rolling sample regress risk reversal on rate differential
# Estimate fair value of risk reversal
# Go 




# Why not just try harveting the risk reversal premium by buying the largest risk reversal
for key in ['rr_25d_1m', 'rr_25d_3m', 'rr_10d_1m', 'rr_10d_3m']:
    rr = dfs[key]
    for pair in rr.columns:
        left = pair[:3]
        right = pair[3:]
        rr[f'{right}{left}'] = -rr[pair]
        r_diff[f'{right}{left}'] = -rate_diff[pair]

    for i in range(3,6):
        
        rr = rr.resample('M').last()
        portfolio_naive_rr = portfolio(rr, 1, returns, i, False)
        plt.plot(portfolio_naive_rr['cum_return'], label = f'{i}')
        plt.title(f'Harvest risk reversal premium using {key}')
        plt.legend()
    plt.show()










## We know that rate differentials are non-stationary while risk reversals are stationary. So running a regression to estimate what risk reversals should be
d_prev = pd.date_range(start='2006-01-31', end='2020-08-31', freq='M')
d = pd.date_range(start='2009-01-31', end='2023-08-31', freq='M')
key = 'rr_25d_1m'

rr_residuals = pd.DataFrame(index=d, columns = dfs[key].columns)

import statsmodels.api as sm

for date in d:
    rr = dfs[key]
    rr.index = pd.to_datetime(rr.index)    
    
    rr = rr.loc[(date - pd.DateOffset(years=3)):date]
    
    
    rate_diff = mapping(yield_2y).loc[(date - pd.DateOffset(years=3)):date].diff().dropna()
    
    combined_rows = rr.index.intersection(rate_diff.index)
    
    rr = rr.loc[combined_rows]
    rate_diff = rate_diff.loc[combined_rows]
    
    for pair in rr.columns:
        X = rate_diff[pair].astype(float)
        X = sm.add_constant(X).astype(float)
        y = rr[pair]
        y = y.astype(float)
        
    
        model = sm.OLS(y, X).fit()
        rr_residuals.loc[date,pair] = model.resid.last()[-1]
        
        if date == d[0]:
            print(date, pair, model.resid.resample('M').last()[-1])
            print(X)
            print(y)
        
        
rr_residuals = rr_residuals.astype(float)


for i in range(1,6):
    plt.plot(portfolio(rr_residuals, -1, returns, i, False)['cum_return'], label =f'{i} pairs')
    plt.legend()
    
    
    
    















etfs = ['gbpusd_rr','gbpusd_rdiff']
prices = rr_rate_diff[['gbpusd_rr','gbpusd_rdiff']]
draw_date_coloured_scatterplot(etfs, prices)










#########################################################################
# X. Combine all the factors
#########################################################################


# Overall score
common_indices = rate_expectations.index.intersection(trend.index).intersection(fv.index).intersection(vrp.index)
combined = fv.loc[common_indices] + vrp.loc[common_indices]
combined_monthly = combined.resample('M').last()


md.factor_chart(md.portfolio(combined_monthly.drop(['usd'],axis=1),1,pct_rtn_major), True, 'Performance of combined factors')











#########################################################################
# X. Upload DvA's BEER estimates
#########################################################################

all_crosses = list(beers_input['Cross'].drop_duplicates())

import win32com.client
import datetime
import pandas as pd
 
c = win32com.client.Dispatch("Macrobond.Connection")
d = c.Database
 
from macrobond_api_constants import SeriesFrequency as f
from macrobond_api_constants import SeriesWeekdays as wk

for cross in all_crosses:
 
    m = d.CreateEmptyMetadata()
    df = beers_input[beers_input['Cross'] == cross]
    dates = df['date'].dt.to_pydatetime()
    values = df['prediction'].to_list()
    s = d.CreateSeriesObject(f"ih:mb:com:{cross}", f'{cross}', "us", "FX", f.DAILY, wk.MONDAY_TO_FRIDAY, dates, values, m)
     
    d.UploadOneOrMoreSeries(s)
    
    
    
    
    
    
    
    
    
    
    
    
    
##############################################################################
# FX carry strategy attempts
##############################################################################
df = pd.DataFrame()

for file in ['Z:/Global strategy team/GAA frameworks/DM FX and FI/Fixed Income/FI Scorecard/Final Scorecard/daily_automated/oe_forecasts_fair_value.xlsx','Z:/Global strategy team/GAA frameworks/DM FX and FI/Fixed Income/FI Scorecard/Final Scorecard/daily_automated/oe_forecasts_2020_onwards.xlsx']:
    data = pd.read_excel(file)
    data.index = data.iloc[:,0]
    data = data[[country + '_cpi' for country in geo]]
    df = df.append(data)
    
df = df[:163].append(df[209:])
df.index = pd.to_datetime(df.index)
df = df.resample('M').last()
df.columns = ['usd','gbp','eur','jpy','sek','nok','chf','cad','nzd','aud']
df = df

cpi_diff = fxs.mapping(df)
forward3m = dfs['forwards_3m'].dropna()



cpi_diff = cpi_diff[forward3m.columns]

indices = forward3m.index.intersection(cpi_diff.index)
cpi_diff = cpi_diff.loc[indices]
forward3m = forward3m.loc[indices]

# Non jpy * 1000
real_carry = forward3m - cpi_diff

exjpy_cols = [col for col in real_carry.columns if 'jpy' not in col]
real_carry = forward3m - cpi_diff * 1000

jpy_cols = [col for col in real_carry.columns if 'jpy' in col]
real_carry[jpy_cols] = forward3m[jpy_cols] - cpi_diff[jpy_cols] * 1000

real_carry = real_carry[[col for col in real_carry.columns if 'nzd' not in col]]


for i in range(1,6):
    plt.plot(fxs.portfolio(real_carry.astype(float), 1, returns, i, False)['cum_return'], label =f'{i} pairs')
    plt.legend()

plt.show()

# Valuation adjustment

indices = fv_dev.index.intersection(real_carry.index)
fv_dev_strat = fv_dev.loc[indices,real_carry.columns] / 0.05 + 1

real_carry = real_carry * fv_dev_strat

for i in range(1,6):
    plt.plot(fxs.portfolio(real_carry, 1, returns, i, False)['cum_return'], label =f'{i}')
    plt.legend()
    
plt.show()


# Try with bonds
cpi_diff = fxs.mapping(df) * 100
cpi_diff.loc[:'2017-01-31', [col for col in cpi_diff.columns if 'nzd' in col]] = None

yields = md.macrobond_daily(['us1ygov','gb1ygov','de1ygov','jp1ygov','se1ygov','no2ygov','ch1ygov','ca1ygov','au1ygov','nz1ygov']).dropna()
yields.columns = ['usd','gbp','eur','jpy','sek','nok','chf','cad','aud','nzd']

yields = fxs.mapping(yields)
yields = yields.resample('M').last()

yields = yields - cpi_diff

for i in range(1,6):
    plt.plot(fxs.portfolio(yields.dropna(), 1, returns, i, False)['cum_return'], label =f'{i}')
    plt.legend()
    
plt.show()

# Now try add the valuation factor
indices = fv_dev.index.intersection(yields.index)
fv_dev = fv_dev.loc[indices]
yields = yields.loc[indices]

for z in [0.15,0.3,0.45,0.6,0.75,0.9,1]:
    
    for i in range(1,6):
        plt.plot(fxs.portfolio((yields * (z*fv_dev+1)).loc['2010-01-31':], 1, returns, i, False)['cum_return'], label =f'{i}')
        plt.legend()
        plt.title(f'Valuation Factor {z} apply to real carry differntial')
        
    plt.show()


i=1
plt.plot(fxs.portfolio((yields * (0.3*fv_dev+1)), -1, returns, 1, False)['cum_return'], label =f'{i}')
plt.legend()
plt.title(f'Valuation Factor {z} apply to real carry differntial')

plt.show()


# Instead of OE forecasts try using inflation-linked bond yields
tickers = ['ml_g0qi_ytm','ml_g0li_ytm','ml_g0di_ytm','ml_g0yi_ytm','ml_g0wi_ytm','ml_g0j0_ytm','ml_g0s0_ytm','ml_g0ci_ytm','ml_g0ti_ytm','ml_g0zi_ytm']


real_yields = md.macrobond_daily(tickers) # We only have nominal data for Norway & Switzerland
real_yields.columns = ['usd','gbp','eur','jpy','sek','nok','chf','cad','aud','nzd']

inflation = md.macrobond_monthly(['chcpi','nocpi']).pct_change(12) * 100
inflation = inflation.resample('D').last().ffill()

common_indices = real_yields.index.intersection(inflation.index)

real_yields['chf'] = real_yields.loc[common_indices, 'chf'] - inflation.loc[common_indices,'chcpi']
real_yields['nok'] = real_yields.loc[common_indices, 'nok'] - inflation.loc[common_indices,'nocpi']

real_yields = real_yields.resample('M').last()
real_yields = fxs.mapping(real_yields)

for i in range(1,6):
    plt.plot(fxs.portfolio(real_yields.dropna(), 1, returns, i, False)['cum_return'], label =f'{i}')
    plt.legend()
    
plt.show()


fv_dev
real_yields

# Make valuation adjustment

common_indices = real_yields.index.intersection(fv_dev.index)

fv_dev_1 = fv_dev.resample('D').last().ffill().loc[common_indices].resample('M').last()



for z in [0.45]:
    
    for i in range(1,6):
        plt.plot(fxs.portfolio(real_yields * (z*fv_dev_1+1), 1, returns, i, False)['cum_return'], label =f'{i}')
        plt.legend()
        plt.title(f'Valuation Factor {z} apply to real carry differntial')
        
    plt.show()


    
for i in range(1,6):
    plt.plot(fxs.portfolio((real_yields[:-1] * (1*fv_dev_1+1)), 1, returns_daily, i, False)['cum_return'], label =f'{i}')
    plt.legend()
    plt.title(f'Valuation Factor {z} apply to real carry differntial')
    
plt.show()
     

    
# Let's run some regressions to check for significance of preferred factor
returns
yields
## We need to get returns and yields together into a panel format for regression
yields['date'] = yields.index
pd.melt(yields.reset_index(), id_vars=yields.index, var_name='cross', value_name ='value')



pd.melt(df.reset_index(), id_vars=df.index.name, var_name='Country', value_name='Value')








# Instead of OE forecasts try using inflation-linked bond yields
tickers = ['us2ygov','gb2ygov','de2ygov','jp2ygov','se2ygov','no2ygov','ch2ygov','ca2ygov','au2ygov','nz2ygov']
tickers = [
'ml_g0q0_ytm',
'ml_g0l0_ytm',
'ml_g0d0_ytm',
'ml_g0y0_ytm',
'ml_g0w0_ytm',
'ml_g0j0_ytm',
'ml_g0s0_ytm',
'ml_g0c0_ytm',
'ml_g0z0_ytm',
'ml_gjt0_ytm'
]


real_yields = md.macrobond_daily(tickers) # We only have nominal data for Norway & Switzerland
real_yields.columns = ['usd','gbp','eur','jpy','sek','nok','chf','cad','aud','nzd']


real_yields = real_yields.resample('M').last()
real_yields = fxs.mapping(real_yields)

for i in range(1,6):
    plt.plot(fxs.portfolio(real_yields, 1, returns, i, False)['cum_return'], label =f'{i}')
    plt.legend()
    
plt.show()

# Make valuation adjustment

common_indices = fv_dev.index.intersection(real_yields.index)

fv_dev_1 = fv_dev.resample('D').last().ffill().loc[common_indices].resample('M').last()

real_yields = real_yields.loc[common_indices]



for z in [0.15,0.3,0.45,0.6,0.75,0.9,1]:
    
    for i in range(1,6):
        plt.plot(fxs.portfolio(real_yields * (z*fv_dev_1+1), 1, returns, i, False)['cum_return'], label =f'{i}')
        plt.legend()
        plt.title(f'Valuation Factor {z} apply to real carry differntial')
        
    plt.show()
