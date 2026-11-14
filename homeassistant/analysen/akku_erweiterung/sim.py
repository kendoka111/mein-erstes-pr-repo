import numpy as np
ETA_INV=0.95; ETA_B=0.95
def simulate(P, L, cap, soc0=None, out_bat=650, out_max=800):
    """Stundenweise Simulation (Wh je Stunde). P = PV-DC-Potenzial, L = Hauslast (AC).
    Nulleinspeise-Regelung: Geraet deckt die Hauslast (aus PV bis 800 W, mit Akku bis 650 W),
    Ueberschuss laedt den Akku; Akku voll -> PV-Durchreichung bis 800 W, Rest Einspeisung bzw. Abregelung."""
    e = cap*0.5 if soc0 is None else soc0
    imp=exp=curt=batt_out=0.0
    for p,l in zip(P,L):
        pv_ac=p*ETA_INV
        # 1) Hauslast aus PV
        to_load=min(l, pv_ac, out_max)
        rest_dc=p - to_load/ETA_INV
        need=l-to_load
        out=to_load
        # 2) Restlast aus Akku (Ausgang gesamt <= out_bat, solange Akku liefert)
        if need>0 and e>0:
            room=max(0.0, out_bat-out)
            d_ac=min(need, room, e*ETA_B*ETA_INV)
            e-=d_ac/(ETA_B*ETA_INV); out+=d_ac; need-=d_ac; batt_out+=d_ac
        imp+=need
        # 3) PV-Ueberschuss in den Akku
        if rest_dc>0:
            ch=min(rest_dc*ETA_B, cap-e)
            e+=ch; rest_dc-=ch/ETA_B
            # 4) Akku voll: Durchreichen bis 800 W, Rest abgeregelt
            if rest_dc>0:
                x=min(rest_dc*ETA_INV, max(0.0,out_max-out))
                exp+=x; curt+=rest_dc*ETA_INV-x
    return dict(imp=imp/1000, exp=exp/1000, curt=curt/1000, batt=batt_out/1000)
