import load, pandas as pd, numpy as np, warnings
warnings.filterwarnings('ignore')
def prepared():
    df=load.frame()
    df=df[df.index>=pd.Timestamp('2026-08-27',tz='Europe/Berlin')]   # erste volle Tage
    df=df[df.index< pd.Timestamp('2026-10-12',tz='Europe/Berlin')]   # nur volle Tage
    df['heat']=df.heat_mean.fillna(0)
    df['clipped']=(df.soc_max>=93)&(df.pv_max>=780)
    # Akku-Energieaenderung (DC, Wh) aus SOC-Mittelwerten, 1 % = 24 Wh
    s=df.soc_mean.interpolate()
    dsoc=(s.shift(-1)-s.shift(1))/2
    eb=(dsoc*24).fillna(0)
    P=df.pv_mean.fillna(0)
    ac=np.where(eb>=0, np.maximum(0,P-eb/0.95)*0.95, 0.95*(P+(-eb)*0.95))
    df['ac_out']=ac
    df['load']=(df.grid_mean+df.ac_out).clip(lower=30)
    # Huellkurve: bestes ungedrosseltes Stundenmittel derselben Uhrzeit, +-7 Tage
    df['h']=df.index.hour
    env=[]
    for t,row in df.iterrows():
        w=df[(abs((df.index-t).total_seconds())<=7*86400)&(df.h==row.h)&(~df.clipped)]
        env.append(w.pv_mean.max() if len(w) else row.pv_mean)
    df['env']=env
    df['pv_pot']=np.where(df.clipped, np.maximum(df.pv_mean, df.env), df.pv_mean)
    return df
if __name__=='__main__':
    df=prepared()
    df.to_pickle('../ausbau/prepared.pkl')
    night=df[(df.pv_mean<1)&(df.zp_mean<-20)]
    print('Validierung Nacht: AC-Schaetzung vs zendure_power', round(night.ac_out.sum()/1000,2), round(-night.zp_mean.sum()/1000,2), 'kWh in', len(night),'h')
    days=(df.index[-1]-df.index[0]).total_seconds()/86400
    print(f'Tage {days:.1f}; PV gemessen {df.pv_mean.sum()/1000:.1f} kWh; Haus {df.load.sum()/1000:.1f} kWh (davon Heizung {df.heat.sum()/1000:.1f}); Netz netto+ {df.grid_mean.clip(lower=0).sum()/1000:.1f} / netto- {-df.grid_mean.clip(upper=0).sum()/1000:.1f} kWh')
    c=df[df.clipped]
    print(f'gedrosselte Stunden {len(c)}; abgeregelt (Huellkurve) {(c.pv_pot-c.pv_mean).sum()/1000:.2f} kWh')
    print(c[['pv_mean','pv_max','env','pv_pot','soc_max']].round(0).to_string())
