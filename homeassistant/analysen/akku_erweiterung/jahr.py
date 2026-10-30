import pandas as pd, numpy as np, pvlib, warnings, sim, model
warnings.filterwarnings('ignore')
df=pd.read_pickle('../ausbau/prepared.pkl')
loc=model.loc
# Typische Monatssummen Globalstrahlung Raum Fulda, kWh/m2 (DWD-Mittel, gerundet)
GHI={1:21,2:37,3:76,4:119,5:148,6:154,7:156,8:133,9:93,10:55,11:25,12:16}
def cs_ghi_month(m, year=2026):
    idx=pd.date_range(f'{year}-{m:02d}-01',periods=pd.Period(f'{year}-{m:02d}').days_in_month*24,freq='1h',tz='Europe/Berlin')+pd.Timedelta('30min')
    return loc.get_clearsky(idx,model='ineichen')['ghi'].sum()/1000
CLR={m:GHI[m]/cs_ghi_month(m) for m in range(1,13)}
def cs_day(date):
    idx=pd.date_range(pd.Timestamp(date,tz='Europe/Berlin'),periods=24,freq='1h')+pd.Timedelta('30min')
    return model.clearsky_pv(idx).values
tdays=sorted({d for d in df.index.date})
T={d:(df.loc[str(d)].pv_pot.values, df.loc[str(d)].pv_mean.values, df.loc[str(d)].load.values, (df.loc[str(d)].load-df.loc[str(d)].heat).clip(lower=30).values) for d in tdays}
T={d:v for d,v in T.items() if len(v[0])==24}
tdays=sorted(T)
CS={d:cs_day(d) for d in tdays}
def build_year(year=2026, use_pot=True, heat=True):
    P=[];L=[]
    for i,day in enumerate(pd.date_range(f'{year}-01-01',f'{year}-12-31',freq='D')):
        t=tdays[i%len(tdays)]
        pot,act,ld,ldn=T[t]; src=pot if use_pot else act
        cst=CS[t]; csm=cs_day(day.date())
        f=CLR[day.month]/CLR[t.month]
        ratio_day=src.sum()/max(cst.sum(),1)
        p=np.where(cst>30, src*np.divide(csm,np.maximum(cst,1)), csm*ratio_day*np.where(np.arange(24)>=15,0.5,1.0))*f
        P.extend(p); L.extend(ld if heat else ldn)
    return np.array(P),np.array(L)
CUR=2400*0.77; EXT=(2400+2880)*0.77
if __name__=='__main__':
    print('Klarheitsfaktor je Monat', {m:round(v,2) for m,v in CLR.items()})
    for use_pot in (False,True):
        for heat in (True,False):
            P,L=build_year(use_pot=use_pot,heat=heat)
            a=sim.simulate(P,L,CUR); b=sim.simulate(P,L,EXT)
            mon=pd.date_range('2026-01-01',periods=len(P),freq='1h').month
            print(f"Drosselung {'raus' if use_pot else 'drin'} | Heizung {'in Last' if heat else 'nicht'} | PV {P.sum()/1000:.0f} kWh/Jahr | jetzt: Bezug {a['imp']:.0f} Einsp {a['exp']:.0f} Abreg {a['curt']:.0f} | +2,88: Bezug {b['imp']:.0f} Einsp {b['exp']:.0f} Abreg {b['curt']:.0f} | Ersparnis {a['imp']-b['imp']:.0f} kWh = {(a['imp']-b['imp'])*0.30:.0f} EUR/Jahr")
    P,L=build_year(use_pot=True,heat=False)
    idx=pd.date_range('2026-01-01',periods=len(P),freq='1h')
    rows=[]
    for m in range(1,13):
        sel=idx.month==m
        a=sim.simulate(P[sel],L[sel],CUR,soc0=0); b=sim.simulate(P[sel],L[sel],EXT,soc0=0)
        rows.append((m,round(P[sel].sum()/1000),round(a['exp']+a['curt'],1),round(a['curt'],1),round(a['imp']-b['imp'],1)))
    print('Monat, PV kWh, Ueberschuss heute (Einsp+Abreg), davon Abreg, Mehrnutzung mit Zusatzakku kWh'); [print(r) for r in rows]
