import math
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm
from scipy.stats import mvn
from scipy.optimize import optimize, brute
from scipy.misc import derivative as prime
from scipy.integrate import quad
import pandas as pd
from datetime import datetime as dt
import statsmodels.api as sm
from sklearn import linear_model

mpc = pd.DataFrame({'Date': ['03/23/2023', '05/11/2023', '06/22/2023', '08/03/2023', '09/21/2023', '11/02/2023', '12/14/2023']})
mpc = pd.to_datetime(mpc['Date'])

def _gbs(option_type, fs, x, t, r, b, v):

    t__sqrt = math.sqrt(t)
    d1 = (math.log(fs / x) + (b + (v * v) / 2) * t) / (v * t__sqrt)
    d2 = d1 - v * t__sqrt

    if option_type == "c":
        value = fs * math.exp((b - r) * t) * norm.cdf(d1) - x * math.exp(-r * t) * norm.cdf(d2)
        delta = math.exp((b - r) * t) * norm.cdf(d1)
        gamma = norm.pdf(d1) / (fs * v * t__sqrt)
        theta = -(fs * v * math.exp((b - r) * t) * norm.pdf(d1)) / (2 * t__sqrt) - (b - r) * fs * math.exp((b - r) * t) * norm.cdf(d1) - r * x * math.exp(-r * t) * norm.cdf(d2)
        vega = math.exp((b - r) * t) * fs * t__sqrt * norm.pdf(d1)
        rho = x * t * math.exp(-r * t) * norm.cdf(d2)

    else:
        value = x * math.exp(-r * t) * norm.cdf(-d2) - (fs * math.exp((b - r) * t) * norm.cdf(-d1))
        delta = math.exp((b - r) * t) * norm.cdf(-d1)
        gamma = math.exp((b - r) * t) * norm.pdf(d1) / (fs * v * t__sqrt)
        theta = (fs * v * math.exp((b - r) * t) * norm.pdf(d1)) / (2 * t__sqrt) + (b - r) * fs * math.exp((b - r) * t) * norm.cdf(-d1) + r * x * math.exp(-r * t) * norm.cdf(-d2)
        vega = math.exp((b - r) * t) * fs * t__sqrt * norm.pdf(d1)
        rho = -x * t * math.exp(-r * t) * norm.cdf(-d2)

    return value, delta, gamma, theta, vega, rho


def black_76(option_type, fs, x, t, r, v):
    b = 0
    return _gbs(option_type, fs, x, t, r, b, v)


def _gbs_O(option_type, fs, x, t, r, b, v):

    t__sqrt = math.sqrt(t)
    d1 = (math.log(fs / x) + (b + (v * v) / 2) * t) / (v * t__sqrt)
    d2 = d1 - v * t__sqrt

    if option_type == "c":
        value = fs * math.exp((b - r) * t) * norm.cdf(d1) - x * math.exp(-r * t) * norm.cdf(d2)

    else:
        value = x * math.exp(-r * t) * norm.cdf(-d2) - (fs * math.exp((b - r) * t) * norm.cdf(-d1))
        

    return value


def black_76_O(v,obs_price,option_type, fs, x, t, r):
    b = 0
    return _gbs_O(option_type, fs, x, t, r, b, v) - obs_price


def _gbs_BL(x, fs, t, r, b, v):
    t__sqrt = math.sqrt(t)
    d1 = (math.log(fs / x) + (b + (v * v) / 2) * t) / (v * t__sqrt)
    d2 = d1 - v * t__sqrt
    value = fs * math.exp((b - r) * t) * norm.cdf(d1) - x * math.exp(-r * t) * norm.cdf(d2)
    return value

def black_76_BL(x, fs, t, r, v):
    b = 0
    return _gbs_BL(x, fs, t, r, 0, v)


def bisection_search(obs_price,option_type, fs, x, t, r):
    upper = 1
    lower = 0
    tol = 1e-3
    error = 1
    prev_error = None
    counter = 0
    while error > tol:
        counter +=1
        i = (upper + lower) / 2
        error = black_76_O(i,obs_price,option_type, fs, x, t, r)
        if error > 0:
            upper = i
        else:
            lower = i
        
        prev_error = error 
        error = abs(error)
    return i
    

def IV(alpha, delta):
    a = np.array(alpha)
    d = np.array([delta] * 5 + [abs(0.5 - delta)]) ** np.array([0,1,2,3,4,4])
    return np.sum(a*d)

def implied_strike(delta,fs,t,r,v):
    var = v * v * t
    a = math.sqrt(var)
    b = var/2
    d = norm.ppf(math.exp(r * t) * delta)
    return fs * math.exp(b - (a*d))

def breeden_litzenberger(x, fs, t, r, v):
    return math.exp(r*t)*prime(black_76_BL,dx = 0.001,x0 = x,n=2,args=(fs,t,r,v))



def produce_IV_estimates(chain, asof, r, penalty, return_what='estimates' ):
    path = f'C:/Users/rfield/Desktop/option_implied_distributions/{chain.lower()}_{asof}.xlsx'
    des  = pd.read_excel(path).values[1,0]
    calls = pd.DataFrame(pd.read_excel(path).values[2:,1:6], columns = ['X','B','O','c','iv']).drop(columns = ['B','O']).astype(float)
    puts = pd.DataFrame(pd.read_excel(path).values[2:,8:13], columns = ['X','B','O','p','iv']).drop(columns = ['B','O']).astype(float)
    calls_o = calls[calls['c']>0].index
    puts_o = puts[puts['p']>0].index
    m,d,y = int(des.split('/')[0][-1]), int(des.split('/')[1]),2000 + int(des.split('/')[2][:2]) 
    o = dt(int(asof[:4]),int(asof[4:6]),int(asof[6:]))
    days = (dt(y,m,d) - dt(o.year,o.month,o.day)).days 
    F = float(des.split()[-1])
    t = days / 365
    r /=100
    for i in calls_o:
        try:
            vol = bisection_search(calls.c[i],'c',F,calls.X[i],t,r)
        except ZeroDivisionError:
            vol =0
        calls.iv[i] = vol

    for i in puts_o:
            try:
                vol = bisection_search(puts.p[i],'p',F,puts.X[i],t,r)
            except ZeroDivisionError:
                vol = puts.iv[i-1]
            puts.iv[i] = vol

    for i in calls.index:
        if calls.iv[i] == 0:
            calls.iv[i] = puts.iv[i]

    calls['delta'] = [black_76('c',F,calls.X[i],t,r,calls.iv[i])[1] for i in calls.index]
    puts['delta'] = [black_76('p',F,puts.X[i],t,r,puts.iv[i])[1] for i in puts.index]
    calls = calls[(calls['delta']<0.85)&(calls['delta']>0.15)].copy(deep = True).reset_index(drop = True) 
    puts =  puts[(puts['delta']<0.85)&(puts['delta']>0.15)].copy(deep = True).reset_index(drop = True)
    puts['delta'] = 1 - puts.delta

    data = pd.concat((puts[['iv','delta']],calls[['iv','delta']]),ignore_index=True)
    data['delta_2'] = [i**2 for i in data.delta]
    data['delta_3'] =[i**3 for i in data.delta]
    data['delta_4'] =[i**4 for i in data.delta]
    data['delta_abs'] = [abs(0.5 -i)**4 for i in data.delta]
    
    X = data[['delta','delta_2','delta_3','delta_4','delta_abs']]
    y = data['iv']
    model_2 = linear_model.Ridge(alpha = penalty)
    model_2.fit(X,y)
    fitted_alpha_ridge = [model_2.intercept_] + [i for i in model_2.coef_]
    data['check_r'] = [IV(fitted_alpha_ridge,i) for i in data.delta]
    
    plt.scatter(x = data.delta,y = data.iv,color = 'b')
    plt.scatter(x = data.delta,y = data.check_r,color = 'r')
    
    
    if return_what =='estimates':
        return fitted_alpha_ridge
    else:
        plt.scatter(x = data.delta,y = data.iv,color = 'b')
        plt.scatter(x = data.delta,y = data.check_r,color = 'r')

    
def generate_dist(chain, asof, r ,vol_param):
    path = f'C:/Users/rfield/Desktop/option_implied_distributions/{chain.lower()}_{asof}.xlsx'
    des  = pd.read_excel(path).values[1,0]
    m,d,y = int(des.split('/')[0][-1]), int(des.split('/')[1]),2000 + int(des.split('/')[2][:2]) 
    o = dt(int(asof[:4]),int(asof[4:6]),int(asof[6:]))
    days = (dt(y,m,d) - dt(o.year,o.month,o.day)).days 
    F = float(des.split()[-1])
    t = days / 365
    r /=100
    dist_df = pd.DataFrame({})
    dist_df['delta'] = np.linspace(0.001,0.999,num = 100000)
    dist_df['iv'] = [IV(vol_param,i) for i in dist_df.delta]
    dist_df['x'] = [implied_strike(delta=i,fs=F,t=t,r=r,v=j) for i,j in zip(dist_df.delta,dist_df.iv)]
    dist_df['r'] = [100 - i for i in dist_df.x]
    dist_df['bl'] = [breeden_litzenberger(x=i,fs=F,t=t,r=r,v=j) for i,j in zip(dist_df.x,dist_df.iv)]
    dist_df['dr'] = dist_df['r'].diff()
    dist_df.dropna(inplace = True)
    dist_df.reset_index(inplace = True)
    dist_df_p = np.sum(dist_df.bl.values*dist_df.dr.values)
    dist_df['bl'] = dist_df['bl']/dist_df_p
    dist_df['cum_bl'] = dist_df.bl.values*dist_df.dr.values
    dist_df['cum_bl'] = dist_df['cum_bl'].cumsum()
    
    moments = pd.DataFrame({}, columns = ['AVG','STD','MEDIAN', 'MODE','SKEW','KURTOSIS','NP SKEW'])
    
    moments.loc[0,'AVG'] = np.sum(dist_df.bl.values*dist_df.dr.values*dist_df.r.values)
    moments.loc[0,'STD'] = np.sqrt(np.sum( dist_df.bl.values*dist_df.dr.values*((dist_df.r.values - moments.AVG[0])**2))) 
    moments.loc[0,'SKEW'] = np.sum(dist_df.bl.values*dist_df.dr.values*((dist_df.r.values - moments.AVG[0])**3)) /( moments.STD[0] **3)
    moments.loc[0,'KURTOSIS'] = np.sum( dist_df.bl.values*dist_df.dr.values*((dist_df.r.values - moments.AVG[0])**4)) / (moments.STD[0] ** 4)
    moments.loc[0,'MEDIAN']  = dist_df['r'][dist_df['cum_bl']> 0.5].values[0]
    moments.loc[0,'MODE'] = dist_df[dist_df['bl'] == dist_df['bl'].max()]['r'].values[0]
    return dist_df , moments * 100
    
def plot_dist(df,asof,chain ,color = 'blue'):
    o = dt(int(asof[:4]),int(asof[4:6]),int(asof[6:]))
    fig, ax =  plt.subplots(figsize = (15,6))
    ax.plot(df.r.values,df.bl.values, color = color)
    ax.set_xlabel('RATE')
    ax.set_ylim(ymin=0)
    x = ax.lines[0].get_xydata()[:,0]
    y = ax.lines[0].get_xydata()[:,1]
    ax.fill_between(x, y, color=color, alpha=0.1)
    ax.set_title(f'OPTION IMPLIED DISTRIBUTION ON {chain} AS OF {o.strftime("%B")} {o.strftime("%d")}'.upper())
    plt.show()


def plot_dist_comp(df,df_old,asof,asof_old,chain ,color = 'blue'):
    o = dt(int(asof[:4]),int(asof[4:6]),int(asof[6:]))
    q = dt(int(asof_old[:4]),int(asof_old[4:6]),int(asof_old[6:]))
    fig, ax =  plt.subplots(figsize = (15,6))
    ax.plot(df.r.values,df.bl.values, color = color,label = o.strftime('%b %d'))
    ax.plot(df_old.r.values,df_old.bl.values, color = f'dark{color}', linestyle = '--',label = q.strftime('%b %d'))
    ax.set_xlabel('RATE')
    ax.set_ylim(ymin=0)
    x = ax.lines[0].get_xydata()[:,0]
    y = ax.lines[0].get_xydata()[:,1]
    ax.legend()
    ax.fill_between(x, y, color=color, alpha=0.1)
    ax.set_title(f'OPTION IMPLIED DISTRIBUTION ON {chain} AS OF {o.strftime("%B")} {o.strftime("%d")}'.upper())
    plt.savefig(f'C:/Users/rfield/Desktop/option_implied_distributions/{chain}_{asof}_RND.png', bbox_inches='tight')
    
    plt.show()    
    
chain = 'erm5'
asof_1 = '20240926'
asof = '20240823'
r_1 = 3.39
r = 3.39 + 0.25
penalty = 0.5
x = produce_IV_estimates(chain,asof_1,r_1,penalty)
y = produce_IV_estimates(chain,asof,r,penalty)

df, mom = generate_dist(chain, asof,r,y)
df_1, mom_1 = generate_dist(chain, asof_1,r_1,x)
df.to_excel(f'C:/Users/rfield/Desktop/option_implied_distributions/{chain}_{asof}_mom10.xlsx')
df_1.to_excel(f'C:/Users/rfield/Desktop/option_implied_distributions/{chain}_{asof_1}_mom10.xlsx')

plot_dist_comp(df,df_1,asof,asof_1,chain,color = 'blue')
