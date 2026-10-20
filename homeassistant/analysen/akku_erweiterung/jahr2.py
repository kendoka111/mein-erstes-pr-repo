import pandas as pd, numpy as np, jahr, sim
from jahr import T, tdays, CS, CLR, cs_day, CUR, EXT
csd={d.date():cs_day(d.date()) for d in pd.date_range('2026-01-01','2026-12-31',freq='D')}
def build(offset, use_pot, heat):
    P=[];L=[]
    for i,day in enumerate(pd.date_range('2026-01-01','2026-12-31',freq='D')):
        t=tdays[(i+offset)%len(tdays)]
        pot,act,ld,ldn=T[t]; src=pot if use_pot else act
        cst=CS[t]; csm=csd[day.date()]
        f=CLR[day.month]/CLR[t.month]
        rd=src.sum()/max(cst.sum(),1)
        p=np.where(cst>30, src*csm/np.maximum(cst,1), csm*rd*np.where(np.arange(24)>=15,0.5,1.0))*f
        P.extend(p); L.extend(ld if heat else ldn)
    return np.array(P),np.array(L)
res={}
idx=pd.date_range('2026-01-01','2026-12-31 23:00',freq='1h')
for use_pot in (False,True):
  for heat in (True,False):
    out=[]; mon=np.zeros((12,4))
    for off in range(0,len(tdays),3):
        P,L=build(off,use_pot,heat)
        a=sim.simulate(P,L,CUR); b=sim.simulate(P,L,EXT)
        out.append((P.sum()/1000,a['imp'],b['imp'],a['exp'],a['curt'],b['exp'],b['curt']))
        if use_pot and not heat:
            for m in range(1,13):
                s=idx.month==m
                am=sim.simulate(P[s],L[s],CUR,soc0=0); bm=sim.simulate(P[s],L[s],EXT,soc0=0)
                mon[m-1]+=[P[s].sum()/1000, am['exp']+am['curt'], am['curt'], am['imp']-bm['imp']]
    o=np.array(out); sv=(o[:,1]-o[:,2])
    print(f"Drosselung {'raus' if use_pot else 'drin'} | Heizung {'in Last' if heat else 'nicht '} | PV {o[:,0].mean():.0f} | heute Einsp {o[:,3].mean():.0f} Abreg {o[:,4].mean():.0f} | Zusatzakku Einsp {o[:,5].mean():.0f} Abreg {o[:,6].mean():.0f} | Ersparnis {sv.mean():.0f} kWh (Spanne {sv.min():.0f}-{sv.max():.0f}) = {sv.mean()*0.30:.0f} EUR/Jahr")
    if use_pot and not heat:
        n=len(range(0,len(tdays),3)); mon/=n
        print('Monat | PV kWh | Ueberschuss heute | davon abgeregelt | Mehrnutzung Zusatzakku')
        for m in range(12): print(m+1, *[round(x,1) for x in mon[m]])
