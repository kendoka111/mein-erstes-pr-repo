# PV-Vorhersage (Forecast.Solar): Fläche aus Messdaten (30.10.2026)

## Änderung
- Integration Forecast.Solar, Entry `01M0YVTQG558NV2RT97HMHM2AK`,
  Plane-Subentry `01M0YVTQG64HAMVK5159Y8JJG9`.
- Vorher: 25° Neigung / 180° (Süd) / 1500 W.
- Neu: 75° Neigung / 115° (Ost-Südost) / 1560 W.
- Dämpfung morgens/abends bleibt 0, kein API-Key (Free-Tier, eine Fläche,
  stündlicher Abruf).
- Rückweg: Subentry wieder auf 25 / 180 / 1500 setzen. Kein Neustart nötig.
- Prüfung danach: Entry geladen, Titel "75° / 115° / 1560W",
  `sensor.power_highest_peak_time_today` von 14:00 auf 10:00 UTC gewandert.
- Freigabe Dr. Schmidt (Schritte Reconfigure und Prüfung).

## Warum diese Werte
- Laut Normen: 2 × 520 Wp Südost, 1 × 520 Wp Südwest, "Neigung ca. 15–20°".
- Gemessen (`sensor.zendure_power_pv_total`, Stundenmittel) liefert die
  Anlage morgens weit mehr, als flache Module bei Oktobersonne schaffen
  (12.10. 08–09 UTC: 1011 W bei ~21° Sonnenhöhe). Das passt nur zu steilen,
  nach Ost-Südost zeigenden Modulen. Vermutlich ist "15–20°" von der
  Senkrechten gemessen (Balkongeländer). Offen, ob das stimmt.
- Vergleich mit pvlib-Clear-Sky-Modell (Ineichen, PR 0,85), klare Tage 12.,
  19., 20. und 29.10., 06–15 UTC, abgeregelte Stunden ausgeschlossen
  (Nachrechnung Dr. Schmidt, 27 Stunden):

  | Fläche | RMSE | Summe Modell:Messung |
  |---|---|---|
  | 25/180/1500 (alt) | 333 W | – |
  | 17/165/1560 (erster Vorschlag) | ~280 W* | ~1,08* |
  | 75/115/1560 (neu) | 115 W | 0,93 |
  | 70/115/1560 | 117 W | 0,94 |
  | 80/105/1560 | 128 W | 0,83 |

  \* mit abgeregelten Stunden gerechnet.
- Die Fläche ist eine effektive Ersatzfläche für die Vorhersage, nicht die
  echte Geometrie. Zwei echte Flächen (Südost + Südwest) gingen nur mit
  kostenpflichtigem Forecast.Solar-Zugang.

## Abregelung ist kein Schatten
- An allen vier klaren Tagen war der Akku mittags voll und die PV wurde
  abgeregelt (PV-Maximum genau 801 W, SOC ≥ 95 %): 12.10. um 10–11 UTC,
  19.10. 09–13 UTC, 20.10. 09–12 UTC, 29.10. um 10 UTC.
- Ein Teil des Mittagseinbruchs ist also Abregelung. Echter
  Nachmittagsschatten ist nur belegt, wo der SOC fällt und die PV trotzdem
  niedrig bleibt (12.10. ab 12 UTC, 29.10. ab 11 UTC).
- Die Vorhersage soll das Potenzial der Module abbilden, nicht die
  abgeregelte Ist-Leistung.

## Nachjustieren (Option C, ab ca. 13.11.2026)
- Vorhersage und Messung stundenweise vergleichen.
- Stunden mit SOC ≥ 95 % oder PV-Maximum ≈ 800 W ausschließen, sonst wird die
  Dämpfung auf Abregelung statt auf Schatten kalibriert.
- Erst dann über `damping_evening` entscheiden. Die genaue Dämpfungsformel
  von Forecast.Solar ist nicht geprüft (Doku aus der Sitzung nicht
  erreichbar), deshalb vorerst 0.

## Vorbehalte
- Nur aus Oktoberdaten bestimmt (Sonnenhöhe ≤ ~30°). Für hohe Sommersonne
  und das Südwest-Modul am Nachmittag nicht geprüft. Im Frühjahr/Sommer
  erneut prüfen.
- `sensor.power_production_now` (state_class measurement) zeigt in der
  Langzeitstatistik ab 30.10.2026 ~13:41 einen gewollten Niveausprung.
  Die Energie-Sensoren der Vorhersage haben keine state_class, dort gibt es
  keinen Statistikbruch.
- Wetterfehler der Vorhersage (z. B. Nebel 30.10. früh, real >900 W ab
  9:30) lassen sich mit der Fläche nicht beheben.
- Die Vorhersage wird nur angezeigt (Dashboards, Energie-Dashboard). Keine
  Automation nutzt sie.
