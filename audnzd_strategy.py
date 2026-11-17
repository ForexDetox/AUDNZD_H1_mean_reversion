import os,sys,json,hashlib,time
from pathlib import Path
os.environ['OPENBLAS_NUM_THREADS']='1'

import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parent
O=ROOT/'results';O.mkdir(exist_ok=True)
full=pd.read_csv(ROOT/'data/AUDNZD_H1.csv',index_col='time',parse_dates=True)
full.index=pd.to_datetime(full.index,utc=True).as_unit('ns')
FILTERS=pd.read_csv(ROOT/'data/saved_filters_window8.csv',index_col='time',parse_dates=True)
FILTERS.index=pd.to_datetime(FILTERS.index,utc=True).as_unit('ns')
tr=pd.concat([full.high-full.low,(full.high-full.close.shift()).abs(),(full.low-full.close.shift()).abs()],axis=1).max(axis=1)
atr=tr.rolling(20,min_periods=20).mean()
p=full.loc['2020-04-01':'2026-11-01'];idx=p.index;ns=idx.asi8;op,hi,lo,cl=[p[c].to_numpy() for c in ['open','high','low','close']];at=atr.reindex(idx).to_numpy();N=len(p);hour=3600*10**9
eligible=(idx.dayofweek>=1)&(idx.dayofweek<=3)&(idx.hour>=17)&(idx.hour<=21)
months=pd.date_range('2021-04-01','2026-11-01',freq='MS',tz='UTC')
month_windows=[(idx.searchsorted(m-pd.DateOffset(years=1)),idx.searchsorted(m),idx.searchsorted(m+pd.DateOffset(months=1))) for m in months]
H=[1,2,4,12,0]
def get_ma(method,length=8):
 if length!=8:raise ValueError('This portable package includes the latest 8-bar study only.')
 return FILTERS[method].reindex(idx).to_numpy()

def signals(ma):
 dev=cl-ma;s=np.zeros(N,dtype=np.int8)
 for a,b,c in month_windows:
  train=dev[a:b];train=train[np.isfinite(train)]
  if len(train)<3000:continue
  low,high=np.quantile(train,[.1,.9]);v=dev[b:c];s[b:c]=np.where((v<low)&(v<0),1,np.where((v>high)&(v>0),-1,0))
 s[~eligible]=0;s[:-1][np.diff(ns)!=hour]=0;s[-1]=0
 return s
def simulate(ma,s,h,details=False):
 candidates=np.flatnonzero(s);busy=-1;equity=10000.;peak=equity;dd=0;rows=[]
 for signal in candidates:
  entry=signal+1
  if entry<busy:continue
  side=int(s[signal]);distance=2*at[signal]
  if not np.isfinite(distance) or distance<=0:continue
  start=op[entry];stop=start-side*distance;due=ns[entry]+h*hour if h else np.iinfo(np.int64).max
  j=entry;reason='sample_end';price=cl[-1];exit_ns=ns[-1]+hour;ambiguous=0
  while j<N:
   # Stop orders already in force take priority at a gap; entries occur at this open.
   if side*(op[j]-stop)<=0:price=op[j];reason='gap_stop';exit_ns=ns[j];break
   if ns[j]>=due:price=op[j];reason='time';exit_ns=ns[j];break
   target=ma[j-1] if j>0 else np.nan
   if h==0 and np.isfinite(target) and side*(op[j]-target)>=0:price=op[j];reason='ma_open';exit_ns=ns[j];break
   hitstop=lo[j]<=stop if side==1 else hi[j]>=stop
   hittarget=h==0 and np.isfinite(target) and (hi[j]>=target if side==1 else lo[j]<=target)
   if hitstop:price=stop;reason='stop';ambiguous=int(hittarget);exit_ns=ns[j]+hour;break
   if hittarget:price=target;reason='ma_touch';exit_ns=ns[j]+hour;break
   j+=1
  if j==N:j=N-1
  r=side*(price-start)/distance;ret=.02*r;before=equity;equity*=max(0,1+ret);peak=max(peak,equity);dd=min(dd,equity/peak-1)
  busy=j if exit_ns==ns[j] else j+1
  rows.append((signal,entry,j,side,start,price,distance,r,side*(price-start)*10000,before,equity,exit_ns,reason,ambiguous,.02*start/distance))
  if equity<=0:break
 a=np.array([v[7] for v in rows]);pips=np.array([v[8] for v in rows]);years=(pd.Timestamp('2026-11-02',tz='UTC')-months[0]).total_seconds()/(365.25*86400)
 gain=a[a>0].sum();loss=-a[a<0].sum()
 result=dict(exit_rule=f'{h}h' if h else 'MA',trades=len(rows),total_return_pct=(equity/10000-1)*100,cagr_pct=((equity/10000)**(1/years)-1)*100,closed_trade_max_dd_pct=-dd*100,win_rate_pct=(a>0).mean()*100 if len(a) else 0,mean_R=a.mean() if len(a) else 0,mean_pips=pips.mean() if len(a) else 0,profit_factor_R=gain/loss if loss else np.nan,final_equity_NZD=equity,stop_count=sum(v[12] in ['stop','gap_stop'] for v in rows),ambiguous_stop_target=sum(v[13] for v in rows),max_entry_leverage=max([v[14] for v in rows],default=0),median_hold_hours=np.median([(v[11]-ns[v[1]])/hour for v in rows]) if rows else 0)
 result['trade_fingerprint']=hashlib.sha256(np.array([(r[0],r[2],r[3],round(r[7],10)) for r in rows],dtype=np.float64).tobytes()).hexdigest()
 return result,rows

def main():
 import argparse
 parser=argparse.ArgumentParser(description='AUDNZD H1: saved 8-bar filters, rolling decile signals and fixed ATR stops')
 parser.add_argument('--filter',default='all',help='Filter name, or all for the saved revised top ten')
 parser.add_argument('--exit',choices=['MA','1','2','4','12'],default='MA')
 parser.add_argument('--cost-bps',type=float,default=2.,help='Round-trip cost in basis points of entry notional')
 args=parser.parse_args()
 if args.cost_bps<0:parser.error('Cost must be nonnegative')
 selected=pd.read_csv(ROOT/'reference_results/same_top10_fixed_order.csv')['filter'].tolist() if args.filter=='all' else [args.filter]
 summaries=[];ledger=[]
 for method in selected:
  ma=get_ma(method);stats,trades=simulate(ma,signals(ma),0 if args.exit=='MA' else int(args.exit))
  equity=10000.;peak=equity;mdd=0.
  for t in trades:
   signal,entry,j,side,start,price,distance,R,pips,before,after,exit_ns,reason,ambiguous,leverage=t
   units=.02*equity/distance;cost=args.cost_bps/10000*start*units;pnl=side*(price-start)*units-cost;prior=equity;equity=max(0.,equity+pnl);peak=max(peak,equity);mdd=max(mdd,1-equity/peak)
   ledger.append(dict(filter=method,signal_time=idx[signal],entry_time=idx[entry],exit_time=pd.Timestamp(exit_ns,tz='UTC'),side=side,entry_price=start,exit_price=price,stop=start-side*distance,units_AUD=units,cost_NZD=cost,pnl_NZD=pnl,equity_before_NZD=prior,equity_after_NZD=equity,reason=reason,ambiguous_stop_target=ambiguous))
  stats.update(filter=method,length=8,cost_bps=args.cost_bps,net_final_equity_NZD=equity,net_return_pct=(equity/10000-1)*100,net_closed_trade_MDD_pct=mdd*100)
  summaries.append(stats)
 pd.DataFrame(summaries).to_csv(O/'summary.csv',index=False);pd.DataFrame(ledger).to_csv(O/'trades.csv',index=False)
 print(pd.DataFrame(summaries)[['filter','trades','cost_bps','net_final_equity_NZD','net_return_pct']].to_string(index=False))
 print('Results:',O)
if __name__=='__main__':main()
