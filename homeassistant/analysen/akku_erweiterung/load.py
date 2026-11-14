import json, pandas as pd, numpy as np
D='/tmp/claude-0/-home-user-mein-erstes-pr-repo/54a3f62b-d1d7-5f2b-8d56-4bc899caced4/scratchpad/ausbau/hourly.json'
def frame():
    H=json.load(open(D))
    cols={}
    for eid,short in [('sensor.zendure_power_pv_total','pv'),('sensor.home_energy_meter_power','grid'),('sensor.zendure_total_state_of_charge','soc'),('sensor.mystrom_device_leistung','heat'),('sensor.zendure_power','zp'),('sensor.zendure_power_to_home','toh')]:
        for st in ('mean','min','max'):
            s={pd.Timestamp(r['start'],unit='ms',tz='UTC').tz_convert('Europe/Berlin'):r.get(st) for r in H[eid]}
            cols[f'{short}_{st}']=pd.Series(s)
    df=pd.DataFrame(cols).sort_index()
    df=df.asfreq('1h')
    return df
