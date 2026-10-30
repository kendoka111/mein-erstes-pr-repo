import pandas as pd, numpy as np, pvlib
LAT,LON,ALT=50.53,9.73,300
loc=pvlib.location.Location(LAT,LON,'Europe/Berlin',ALT)
ARRAYS=[(135,1040),(225,520)]   # Azimut (Grad, Nord=0), Wp
TILT=17
def clearsky_pv(index_center):
    """Modell-DC-Leistung (W) bei klarem Himmel ohne Verluste, fuer Zeitpunkte index_center (tz-aware)."""
    cs=loc.get_clearsky(index_center, model='ineichen')
    sp=loc.get_solarposition(index_center)
    tot=np.zeros(len(index_center))
    for az,wp in ARRAYS:
        poa=pvlib.irradiance.get_total_irradiance(TILT,az,sp['apparent_zenith'],sp['azimuth'],cs['dni'],cs['ghi'],cs['dhi'],albedo=0.2)
        tot+= poa['poa_global'].fillna(0).values*wp/1000
    return pd.Series(tot,index=index_center)
