import macrobond_module as md
import oe_scenarios_functions as OE
import datetime as dt
import pandas as pd
import matplotlib.pyplot as plt
# rebuild the macro signal

# Calculate macro forecast

def o_fcst():
    df = pd.read_excel("C:/Users/rfield/us_gem/us_gem_old.xlsx", index_col=0).transpose().iloc[10:212,:] # even columns are cpi and odd columns are gdp
    df.index = [convert_datetime(date, False) for date in df.index]
    df.columns = [str(extract_digits(element)) for element in df.columns]
    df = var_split(df)
    return df

def n_fcst():
    df = pd.read_excel("C:/Users/rfield/us_gem/us_gem.xlsx", index_col=0)
    df.index = [convert_datetime(date, False) for date in df.index]
    df.columns = [str(date_convert(element)) for element in df.columns]
    df = var_split(df)
    return df

def h_data():
    df = md.macrobond_quarterly(['usgdp','uscpi','nberq'])
    df.columns = ['gdp','cpi','recession']
    df.loc['2020-09-30':,'recession'] = 0
    for variable in ['gdp','cpi']:
        df[f'current {variable}'] = ((df[variable].pct_change()))*4
        df[f'trend {variable}'] = ((((df[variable].shift(1).pct_change(5*4))+1)**(1/5))-1)
        df[f'signal {variable}'] = df.apply(lambda row: f'high {variable}' if row[f'current {variable}'] > row[f'trend {variable}'] else f'low {variable}', axis=1)
    
    for date in df.index:
        if df.loc[date,'recession'] == 1:
            df.loc[date, 'signal gdp'] = 'recession'
            
    df['signal'] = df['signal gdp'] + " " + df['signal cpi']
    return df['signal']

def concatenate():
    df = {}
    for var in ['gdp', 'cpi']:
        temp = pd.merge(o_fcst()[var], n_fcst()[var], left_index=True, right_index=True, how='left',suffixes=('', '_dup'))        
        temp = temp.loc[:, ~temp.columns.str.endswith('_dup')]
        df[var] = temp
        
    return df
    
def extract_digits(s):
    return int(''.join([char for char in s if char.isdigit()]))
    
def date_convert(element): # Function to extract database date from column
    try:
        return dt.datetime.strptime(element.split('@')[1][:6].replace('_',''), '%b%y').strftime('%Y%m')
    except ValueError:
        return element.split('@')[1][:6].replace('_','')

def var_split(df):
    df = {'cpi':df.iloc[:,range(0,len(df.columns),2)],
          'gdp':df.iloc[:,range(1,len(df.columns),2)]
          }
    return df
    
def convert_datetime(date, month):
    if month == False:
        year = str(date)[:4]
        quarter = str(date)[4:]
        return pd.to_datetime(year) + pd.offsets.QuarterBegin(int(quarter)) - pd.DateOffset(months=2)
    else:
        date = pd.to_datetime(date, format='%Y%m')
        return date.to_period('Q').start_time.strftime('%Y-%m-%d')
    
def high_low_pred(df,quarter,last_quarter,trend_quarter, variable, base):
    current = 2*((df.loc[quarter,base] / df.loc[last_quarter,base])-1) # This quarter growth annualised
    trend = ((df.loc[last_quarter,base] / df.loc[trend_quarter,base])**(1/5))-1 # This quarter growth
    if current < 0 and variable == 'gdp':
        return 'recession'
    else:
        signal = current - trend > 0
        return f'high {variable}' if signal else f'low {variable}'
    
# def high_low_actual(df,quarter,last_quarter,trend_quarter,variable):
#     current = df.diff()
#     trend = 
            
def pred_signal():
    df = concatenate()
    bases = df['gdp'].columns
    signal = pd.DataFrame(index=bases)
    for base in bases:
        quarter = pd.to_datetime(convert_datetime(base, True)) + pd.DateOffset(months=3)
        last_quarter = pd.to_datetime(convert_datetime(base, True)) - pd.DateOffset(months=3)
        trend_quarter = pd.to_datetime(convert_datetime(base, True)) - pd.DateOffset(years=5)
        for variable in ['gdp','cpi']:
            signal.loc[base,variable] = high_low_pred(df[variable], quarter, last_quarter, trend_quarter, variable, base)
            
        signal['joint'] = signal['gdp'] + " " + signal['cpi']
        
    signal = signal.sort_index()
    signal.index = pd.to_datetime(signal.index, format='%Y%m') + pd.offsets.MonthEnd(0)
            
    return signal

quarterly_returns = pd.read_excel('Z:/Global strategy team/GAA frameworks/Macro signal/ryan_new_signal/returns.xlsx', sheet_name='shiller_q', index_col=0)
# quarterly_returns = quarterly_returns.iloc[:,:8]
quarterly_returns = quarterly_returns[['spx','bond','corp','cash']]
# quarterly_returns= quarterly_returns.loc['2000-01-01':]
        
def choices(last, current):
    df = quarterly_returns.loc[last:current]
    # df.columns = df.iloc[0,:]
    df = df.join(h_data()).dropna()
    state_dictionary = dict(df.groupby('signal').mean().idxmax(axis=1))
    
    return state_dictionary
    
def strategy():
    df = pred_signal().shift(1).dropna()
    df = df.resample('M').last().ffill()
    df = df.join(pd.read_excel('Z:/Global strategy team/GAA frameworks/Macro signal/ryan_new_signal/returns.xlsx', sheet_name='shiller_m', index_col=0))
    

    for date in df.index:
        last_date = date - pd.DateOffset(years=15)
        selection = choices(last_date,date)
        state = df.loc[date,'joint']
        print(date,selection[state])
        df.loc[date,'return'] = df.loc[date,selection[state]]

    return df


df = strategy()

plt.plot(df[['spx','return']].cumprod(),label=['spx','strategy'])
plt.legend()

# Alternatives

    

    
current = pd.to_datetime('2024-07-31')
last = current -pd.DateOffset(years=10)
    
choices(last,current)





df = pd.read_excel("Z:/Global strategy team/GAA frameworks/Macro signal/ryan_new_signal/returns.xlsx", sheet_name='innes_alternatives_q', index_col=0)
df.columns = df.iloc[0,:]
df=df.iloc[1:,:8]
df.join





# dispersion/average returns in publically listed private equity companies
def returns():
    df = pd.read_excel("Z:\Global strategy team\Personal\Hubert/Sheets/LPX50.xlsx", sheet_name='df', index_col = 0).pct_change()
    df = df.join(md.macrobond_daily(['sp500_500tr']).pct_change())
    df[df.columns[0]] = df['sp500_500tr']
    df = df.drop(['sp500_500tr'],axis=1)
    return df
    
def fx_dictionary():
    df = pd.read_excel("Z:\Global strategy team\Personal\Hubert/Sheets/LPX50.xlsx", sheet_name='mapping', index_col = 0)
    df = df['Currency']
    return dict(df), df.unique()[1:]


# def sector_dictionary():
#     df = pd.read_excel("Z:\Global strategy team\Personal\Hubert/Sheets/LPX50.xlsx", sheet_name='mapping', index_col = 0)
#     df = df['Sector']
#     return dict(df), df.unique()[1:]

def returns_usd():
    fx = md.macrobond_daily(fx_dictionary()[1]).pct_change()
    fx['usd'] = 0
    dictionary = fx_dictionary()
    r = returns()
    concat = r.join(fx)
    for company in r.columns[1:]:
        pair = dictionary[0][company]
        concat[company] = concat[company] - concat[pair]
        
    concat = concat.drop(['jpy','cad','usd','eur','chf','gbp'],axis=1)

    
    concat['average return'] = concat.mean(axis=1)
    concat['std'] = concat.std(axis=1)
    
    for company in r.columns[1:]:
        concat[company] = abs(concat[company] - concat[r.columns[0]])
        
    concat['dispersion'] = concat[r.columns[1:]].sum(axis=1) / concat[r.columns[1:]].count(axis=1)
    
    
    # concat = concat.drop(r.columns, axis=1)
    
    return concat
        

df = returns_usd()

df_ = pd.DataFrame(h_data()).join(df.resample('Q').last())
df_ = df_[['signal','average return']].dropna().loc['2000-01-01':].groupby('signal').mean()

df_.std()

df.resample('Q').last()

plt.plot(df['dispersion'])
    
    
h_data()




list_fx = currencies['Currency'].unique()[1:]
fx = md.macrobond_daily(list_fx)



currencies = df.iloc[0,:]





import statsmodels.api as sm

# df = returns_usd()
df = pd.read_excel("Z:\Global strategy team\Personal\Hubert/Sheets/LPX50.xlsx", sheet_name='df', index_col = 0)
df = df[df.columns[0]]
df = pd.DataFrame(df).join(pd.read_excel('Z:/Global strategy team/Personal/Hubert/Sheets/MOVE.xlsx',index_col=0))
df = df.join(md.macrobond_daily(['vix']))
df.columns = ['pe','3m','6m','1m','vix']
df= df[['pe','6m','vix']].dropna()
df = df.resample('W').last()
df['pe'] = df['pe'].pct_change()


df[['6m','vix']] = df[['6m','vix']].diff()
df = df.dropna()
df = sm.add_constant(df)

model = sm.OLS(df['pe'], df[['const','6m','vix']]).fit(cov_type='HC3')
model.summary()
