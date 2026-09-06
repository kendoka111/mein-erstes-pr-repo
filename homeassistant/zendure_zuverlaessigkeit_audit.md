# Zendure-Zuverlässigkeit: Fehlerklassen vom 06.09.2026 und Erkennungsplan

Anlass: Am 06.09. stand der Akku ab ca. 13:17 Uhr durchgehend im Bypass/Standby,
obwohl er bei 95 % SOC lag und das Haus zeitweise 150–280 W aus dem Netz zog.
Zusätzlich lief die PV-Erzeugung mindestens seit Beginn der Aufzeichnung
(sicher nachweisbar für den 06.09., Startzeitpunkt davor unbekannt) auf eine
stille 153-W-Grenze gedeckelt ("Netzeinspeisung verboten" in der Zendure-App).
Beides wurde nicht von Home Assistant gemeldet, sondern zufällig beim Blick
aufs Handy entdeckt. Verlorene Autarkie an diesem einen Nachmittag: die
Differenz zwischen dem, was PV bei offener Grenze lieferte (300–430 W,
belegt ab 15:57 Uhr), und den gedeckelten ~150 W, während gleichzeitig ein
voller Akku nicht aushalf.

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
start_discharging_at-Schwelle` UND das gleichzeitig für mehr als 10 Minuten
zusammenhängend — dann Meldung "Akku entlädt nicht, obwohl er sollte".
Das erkennt den Bypass-Hänger unabhängig davon, ob die Ursache ein
`client_error`, das Flash/RAM-Problem oder etwas drittes ist.

---

## Fehlerklasse 2 — Stille PV-Export-Deckelung ("Netzeinspeisung verboten")

**Nachgewiesen:** `sensor.zendure_power_pv_total` lag über Stunden stabil
bei 130–155 W (auffällig konstant für echte Sonneneinstrahlung). Um
15:57:02–15:57:04 Uhr, exakt beim Umschalten in der App, sprang der Wert
auf 346 W, kurz danach auf 420+ W und schwankte seither natürlich
zwischen ~100–430 W.

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

## Was in diesem Dokument bewusst NICHT steht

Keine YAML, keine fertige Automation, keine Schwellenwerte, die schon
scharf geschaltet sind. Das ist Aufgabe des nächsten Schritts, nachdem
Dr. Schmidt diese Fehlerklassen und die vorgeschlagenen Erkennungslogiken
gegengeprüft hat — insbesondere ob die drei Wächter (Bypass-Hänger,
PV-Deckelung, Sensor-Freshness) die Fälle von heute wirklich abgedeckt
hätten und ob es Fehlalarm-Risiken gibt, die vor dem Scharfschalten
kalibriert werden müssen.
