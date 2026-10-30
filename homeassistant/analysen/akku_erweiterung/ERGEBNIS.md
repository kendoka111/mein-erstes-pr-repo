# Lohnt ein Zusatzakku (AB3000L, 2,88 kWh)? – Rechnung mit Abregelung (12.10.2026)

Anlass: Bei vollem Akku regelt der SolarFlow die Module auf 800 W ab. Diese
Energie taucht in keinem Zähler auf, die erste Rechnung (Okt. 2026) hat sie
nicht berücksichtigt.

## Daten und Annahmen
- Messdaten 27.08.–11.10.2026 (Stundenmittel aus HA): PV, Netz, SOC, Heizung.
- Module: 2 × 520 Wp Südost, 1 × 520 Wp Südwest, steil am Balkongeländer,
  15–20° aus der Senkrechten (Angabe Normen, präzisiert am 30.10.2026).
  Gemessen liefert die Anlage vormittags am meisten, ab 12 Uhr deutlich
  weniger (Nachmittagsschatten oder effektiv mehr Ost). Deshalb keine reine
  Geometrie, sondern die gemessenen Tage als Vorlage.
- Abregelung erkannt an: SOC ≥ 93 % und PV-Spitze ≥ 780 W in der Stunde.
  Mögliche Leistung = bestes ungedrosseltes Stundenmittel derselben Uhrzeit
  ±7 Tage (eher zu hoch geschätzt).
- Hauslast = Netz + Geräteabgabe (aus PV und SOC-Änderung, 1 % = 24 Wh);
  Nachtprüfung gegen `sensor.zendure_power`: 13,3 statt 14,8 kWh (−10 %).
- Jahreshochrechnung: Vorlagetage auf jeden Monat übertragen (Verhältnis
  Klarhimmel-Modell pvlib Ineichen und typische DWD-Monatssummen der
  Globalstrahlung Raum Fulda), 16 Versätze gemittelt.
- Simulation stündlich, Nulleinspeisung, Ausgang 650 W aus Akku / 800 W
  Durchreichung, Wirkungsgrad je Richtung 0,95 × 0,95, nutzbar 18–95 %
  (heute 1,85 kWh, mit Zusatzakku 4,07 kWh). Strompreis 0,30 €/kWh,
  Einspeisung 0 €.
- Gegenprobe Messzeitraum: simulierter Netzbezug 236,9 kWh, gemessen
  241,8 kWh.

## Ergebnis
| Variante | Ersparnis Zusatzakku |
|---|---|
| ohne Abregelung gerechnet | 86–90 kWh/Jahr ≈ 26–27 € |
| mit Abregelung (zurückgewonnen) | 96–100 kWh/Jahr ≈ 29–30 € |

- Abgeregelt werden heute rund 34 kWh im Jahr (vor allem Mai–August, je
  ca. 8 kWh/Monat). Der Zusatzakku würde davon etwa 28 kWh nutzen, das sind
  rund 3 € im Jahr.
- Messzeitraum allein (46 Tage): 3,6–6,9 kWh Ersparnis, 1–2 €.
- Mehrnutzung je Monat (mit Abregelung): Jan 0, Feb 0,5, Mär 7, Apr 13,
  Mai 18, Jun 17, Jul 17, Aug 16, Sep 7, Okt 1, Nov/Dez 0 kWh.
- Amortisation bei 480–600 €: 16–23 Jahre. Das ist länger als die zu
  erwartende Lebensdauer. **Lohnt sich weiterhin nicht.**
- Grund: Der Haushalt braucht rund 8 kWh am Tag, die Anlage ist klein und
  nachmittags verschattet. Der Überschuss über den heutigen Akku hinaus liegt
  auch im Sommer nur bei etwa 1 kWh am Tag.

## Grenzen
Sommer ist hochgerechnet, nicht gemessen; Lastprofil aus dem Herbst.
Stundenwerte glätten Lastspitzen. Prüfung mit echten Sommerdaten: Erinnerung
30.07.2027 (gleiche Skripte, `prep.py` → `jahr2.py`).
