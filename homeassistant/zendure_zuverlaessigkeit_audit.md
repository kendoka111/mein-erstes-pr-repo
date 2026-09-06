# Zendure-Zuverlässigkeit: Fehlerklassen vom 06.09.2026 und Erkennungsplan

Anlass: Am 06.09. stand der Akku ab ca. 13:17 Uhr durchgehend im Bypass/Standby,
obwohl er bei 95 % SOC lag und das Haus zeitweise 150–280 W aus dem Netz zog.
Zusätzlich lief die PV-Erzeugung mindestens seit Beginn der Aufzeichnung
(sicher nachweisbar für den 06.09., Startzeitpunkt davor unbekannt) auf den
jeweiligen Hausverbrauch gedeckelt (89–158 W je nach Tageszeit,
"Netzeinspeisung verboten" in der Zendure-App) statt frei zu erzeugen.
Beides wurde nicht von Home Assistant gemeldet, sondern zufällig beim Blick
aufs Handy entdeckt. Verlorene Autarkie an diesem einen Nachmittag: die
Differenz zwischen dem, was PV bei offener Grenze lieferte (300–430 W,
belegt ab 15:57 Uhr), und der Deckelung auf den Hausverbrauch davor,
während gleichzeitig ein voller Akku nicht aushalf.

Ziel dieses Dokuments: jede beobachtete Fehlerklasse benennen, die
nachgewiesene Ursache von der bloßen Vermutung trennen, und für jede eine
Erkennung vorschlagen, die uns benachrichtigt, statt dass wir es zufällig
bemerken. Es werden hier noch KEINE Automationen angelegt — das ist die
Grundlage für die Dr.-Schmidt-Prüfung, danach erst Umsetzung.

---

## Fehlerklasse 1 — Akku hängt im Bypass trotz vollem Speicher und Hausbedarf

**Nachgewiesen:** `sensor.zendure_charging_mode` blieb ab 13:17:40 Uhr auf
"Standby"/Bypass, bestätigt auch am Gerät selbst (Zendure-App zeigte
"Bypass"). SOC 94–96 % die ganze Zeit, `home_energy_meter_power` wiederholt
über 150 W Netzbezug. Weder Moduswechsel (input_select), noch REST-Reload,
noch HA-Core-Neustart, noch physischer Stromlos-Neustart des Hubs haben das
behoben — erst der manuelle Eingriff in der App (Aufhebung der
Einspeisesperre) hat die Situation gelöst, wobei unklar ist, ob das direkt
ursächlich war oder zeitgleich mit einer Erholung des Geräts zusammenfiel.

**Ursache, mit Beleg:** REST-`client_error` beim Senden des Entladebefehls,
erstmals 12:05:12 Uhr, danach wiederholt (14:33:18, 15:39:24 Uhr) — jeweils
exakt beim Schritt "Start discharging". Kein SOC-Schwelleneffekt: der Akku
erreichte 95 % bereits am 05.09. um 11:50 Uhr und entlud sich danach
störungsfrei die ganze Nacht. Der Unterschied ist der Kommunikationsfehler
zum Gerät, nicht der Ladestand.

**Offen, nicht belegt:** ob der `client_error` selbst schon Symptom eines
tieferliegenden Problems ist (Zendure zeigte separat `sensor.zendure_storage_mode`
= "Flash Memory" statt "RAM" fest — die paketeigene Rückschaltregel dafür
setzt voraus, dass `zendure_power` über 100 W oder unter 0 W liegt, was bei
eingefrorenen 0 W nie eintreten kann — ein Zirkelschluss im Paket selbst,
den Dr. Schmidt gefunden hat). Nicht geklärt, ob das ein Mitverursacher oder
nur eine Begleiterscheinung ist.

**Vorschlag Erkennung:** Automation, die unabhängig vom Grund feuert:
`SOC(Akku) > minimum_allowed_soc + Puffer` UND `home_energy_meter_power >
start_discharging_at-Schwelle` UND **`charging_mode != 'Discharging'`**
(bzw. `zendure_power` bleibt nahe 0 trotz Bedarf) UND das gleichzeitig für
mehr als 10 Minuten zusammenhängend — dann Meldung "Akku entlädt nicht,
obwohl er sollte". Der Ausschluss über `charging_mode`/`zendure_power` ist
notwendig, nicht optional: `sensor.zendure_inverter_max_discharge_power`
steht auf 650 W, übersteigt der Hausverbrauch das dauerhaft, bleibt auch
bei korrekt aktiver Entladung ein Rest-Netzbezug bestehen — ohne diesen
Ausschluss würde die Automation an jedem Tag mit Verbrauchsspitzen über
650 W einen Fehlalarm auslösen. Mit dem Ausschluss erkennt sie den
Bypass-Hänger unabhängig davon, ob die Ursache ein `client_error`, das
Flash/RAM-Problem oder etwas drittes ist.

**Entscheidung Normen (06.09.):** Der Wächter prüft `operation_mode`
NICHT gesondert und meldet auch dann, wenn der Modus bewusst manuell auf
"Standby"/"Manual" o. ä. steht. Begründung: eine Erinnerung, dass der Akku
gerade nicht automatisch mitläuft, ist erwünscht. Kann bei Bedarf später
geändert werden, ist kein Blocker für den Bau.

---

## Fehlerklasse 2 — Stille PV-Export-Deckelung ("Netzeinspeisung verboten")

**Nachgewiesen:** `sensor.zendure_power_pv_total` war deutlich sichtbar
gedeckelt, allerdings nicht auf einen festen Wert — zwischen ca. 11:00 und
13:00 Uhr stabil bei nur 89–90 W, in den letzten 30–60 Minuten vor der
Behebung dann im Band 148–158 W. Das passt eher zu einer Deckelung auf
den jeweiligen Hausverbrauch (typisch für "Netzeinspeisung verboten") als
zu einer festen Wattgrenze. Um 15:57:02–15:57:04 Uhr, exakt beim
Umschalten in der App, sprang der Wert auf 346 W, kurz danach auf 420+ W
und schwankte seither natürlich zwischen ~100–430 W.

**Kritischer Befund:** `sensor.zendure_pv_export_mode` stand die gesamte
aufgezeichnete Woche (mindestens seit 30.08.) durchgehend auf "Unknown" —
kein einziges Mal ein lesbarer Zustand ("Allow"/"Forbid"), bis er heute um
15:57:02 Uhr zum ersten Mal überhaupt "Allow" zeigte. Das heißt: Diese
Einstellung war für Home Assistant die gesamte Zeit unsichtbar. Seit wann
die Deckelung real aktiv war, lässt sich aus den HA-Daten nicht
rekonstruieren — nur die App hätte das gezeigt.

**Vorschlag Erkennung:** Zwei unabhängige Wächter, weil die Ursache hier
in zwei Teilen liegt:
1. Sensor-Gesundheit: Meldung, wenn `zendure_pv_export_mode` (oder ein
   Ersatz-Sensor mit gleicher Aussage) länger als z. B. 2 Stunden im
   Zustand "Unknown"/"unavailable" verharrt — das allein hätte uns
   monatelang blind gehalten, unabhängig vom Exportstatus selbst.
2. Plausibilitätsprüfung PV: Vergleich `zendure_power_pv_total` gegen die
   Solar-Prognose (`sensor.power_production_now`, bereits vorhanden) —
   wenn die reale Erzeugung über längere Zeit signifikant und stabil unter
   der Prognose bleibt (kein normales Wolkenflackern, sondern eine flache
   Linie), Meldung "PV möglicherweise gedeckelt". Schwelle und
   Zeitfenster müssen noch anhand mehrerer Tage Normal-Daten kalibriert
   werden, sonst zu viele Fehlalarme an bewölkten Tagen.

---

## Fehlerklasse 3 — Sensoren frieren nach Reload/Neustart ein (Unique-ID-Kollision)

**Nachgewiesen:** Nach dem REST-Platform-Reload um 13:26:24 Uhr erschienen
für praktisch alle Zendure-Sensoren Log-Einträge "Platform rest does not
generate unique IDs ... already exists - ignoring". Mehrere Sensoren
(`soc_limit_status`, `calibrating`, `storage_mode`, `error`) blieben danach
über Stunden auf dem letzten Stand vor dem Reload eingefroren, obwohl das
Gerät weiterlief — Home Assistant hat schlicht keine neuen Werte mehr
angenommen.

**Vorschlag Erkennung:** Genereller Freshness-Wächter statt gerätespezifischer
Einzellösung: für eine Liste kritischer Zendure-Sensoren prüfen, ob
`last_reported` länger als z. B. 10 Minuten zurückliegt (bei einem Gerät,
das im Sekundentakt pollt, ist das eindeutig ein Hänger) — Meldung
"Zendure-Sensor X liefert keine frischen Daten mehr". Deckt Klasse 3 UND
wäre in Klasse 1 und 2 ebenfalls ein zusätzliches Frühwarnsignal gewesen.

---

## Fehlerklasse 4 — Befehl kommt mit leeren Werten an, Gerät lehnt mit 400 ab

**Nachgewiesen:** Um 13:58:42 Uhr liegt eine weitere, andersartige
Störung im Log — eine `rest_command`-WARNUNG (kein ERROR) mit HTTP-Status
400 und sichtbar kaputtem Payload:
```
Url: http://192.168.178.101/properties/write. Status code 400.
Payload: {"sn":"", "properties":{"acMode": 2, "outputLimit":  }}
```
Leeres `sn`, leerer `outputLimit`-Wert. Das ist kein Netzwerkfehler wie
bei Klasse 1, sondern ein Befehl, dessen Template zum Sendezeitpunkt leere
Werte gerendert hat — deckt sich mit dem in `gielz-upstream-issues.md`
(Issue 2) bereits dokumentierten Muster fehlender `| float`-Defaults bei
`unavailable`-Quellsensoren. Liegt zeitlich mitten im Bypass-Fenster
(13:17–15:57) und ist damit vermutlich eine Folge, nicht die Erstursache,
aber ein eigenständig zu überwachendes Symptom: Es erzeugt keinen
`client_error` (Klasse 1 würde ihn nur über den Umweg SOC/Netzbezug
fangen, nicht benennen), betrifft nicht `pv_export_mode` (Klasse 2), und
der Sensor bleibt dabei aktuell — der Befehl wird nur abgelehnt, kein
Freshness-Problem (Klasse 3).

**Vorschlag Erkennung:** Log-Wächter speziell auf `rest_command`-Antworten
mit Statuscode 4xx für die Zendure-Write-Ressource
(`http://<zendure-ip>/properties/write`) — Meldung "Zendure lehnt Befehl
ab (4xx), Payload möglicherweise unvollständig". Muss beim Bau explizit
auf Zendure-Entities/-Ressourcen gescoped werden: Das Error-Log enthält im
selben Zeitfenster über 1000 Zeilen eines unabhängigen, bereits bekannten
Problems (HomeWizard-P1-DNS-Fehler, siehe `gielz-upstream-issues.md`,
Issue 1) — ein ungescoptes Log-Grep würde in diesem Rauschen untergehen.

**Zusatzkontext zur offenen Frage in Klasse 1** ("war die Aufhebung der
Einspeisesperre ursächlich für das Ende des Bypass, oder nur zeitgleich
mit einer Geräte-Erholung?"): `input_select.zendure_operation_mode` zeigt
zwischen 13:16:47 und 13:17:22 Uhr eine Kaskade von fünf Moduswechseln,
darunter "Dynamic Smart Matching" und "Smart Discharge Only" — Modi, die
die eigene `zendure_ladevorrang_hysterese`-Automation nachweislich nie
selbst setzt (sie kennt nur Smart Matching/Smart Charge Only). Das
spricht für manuelle Troubleshooting-Versuche in genau diesem Fenster,
klärt die offene Frage aber nicht abschließend.

---

## Was in diesem Dokument bewusst NICHT steht

Keine YAML, keine fertige Automation, keine Schwellenwerte, die schon
scharf geschaltet sind. Das ist Aufgabe des nächsten Schritts, nachdem
Dr. Schmidt diese Fehlerklassen und die vorgeschlagenen Erkennungslogiken
gegengeprüft hat — insbesondere ob die vier Wächter (Bypass-Hänger,
PV-Deckelung, Sensor-Freshness, 4xx-Befehlsablehnung) die Fälle von heute
wirklich abgedeckt hätten und ob es Fehlalarm-Risiken gibt, die vor dem
Scharfschalten kalibriert werden müssen.

---

## Änderungshistorie

- **Fassung 1:** Erstfassung mit drei Fehlerklassen.
- **Fassung 2 (nach Dr.-Schmidt-Prüfung, Runde 1):** Fehlerklasse 1 um den
  `charging_mode`/`zendure_power`-Ausschluss ergänzt (sonst Fehlalarm bei
  Verbrauch über 650 W); Beschreibung der PV-Deckelung in Fehlerklasse 2
  präzisiert (89–90 W bzw. 148–158 W statt pauschal "130–155 W über
  Stunden"); Fehlerklasse 4 (REST-400 mit leerem Payload) neu ergänzt;
  Kontext zur Moduswechsel-Kaskade als Zusatzbeleg zur offenen Frage in
  Fehlerklasse 1 aufgenommen.
