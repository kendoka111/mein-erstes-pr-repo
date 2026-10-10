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

**Bestätigter Workaround (06.09., 17:09 Uhr):** Normen hat
`input_select.zendure_operation_mode` manuell auf "Manual" und direkt
zurück auf "Smart Matching" gestellt — nicht einfach nochmal denselben
Wert gesetzt, sondern über einen anderen Modus dazwischen. Ergebnis
sofort danach live geprüft: `charging_mode` sprang auf "Discharging",
`zendure_power` auf -402 W, `home_energy_meter_power` auf -3 W (praktisch
volle Autarkie). Das ist damit die erste Massnahme, die den Bypass
zuverlaessig durchbrochen hat - anders als Stromlos-Neustart des Hubs,
HA-Core-Neustart, REST-Reload und ein korrekter manueller
`rest_command.zendure_x_discharge`-Aufruf, die alle nichts bewirkt haben.
Vermutlich erzwingt der echte Moduswechsel (nicht das erneute Setzen
desselben Werts) eine harte Neubewertung im Geraet selbst. Praktischer
Vorteil: aus der Ferne durchführbar, kein physischer Zugriff nötig. Bis
Zendure den zugrundeliegenden Fehler behebt (siehe unten, GitHub-Issue
Zendure/Zendure-HA #1505), ist das der schnellste bekannte Weg, den Akku
wieder herauszuholen.

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


**Erneuter Bypass-Hänger 04.10.2026 (ca. 14:28–15:18 Uhr):**

Ablauf:
- 11:36 Uhr: Akku voll (SOC 95 %, „Charging Limit Reached“),
  `max_discharge_power` korrekt auf 800 W.
- Bis ca. 13:28 Uhr entlud das Gerät bei Lastspitzen noch normal, mit bis
  zu −800 W.
- Ab ca. 14:28 Uhr schickte Gielz durchgehend Entladebefehle
  (`set_discharge_power` 80–160 W, zwischendurch 334 W). Das Gerät
  ignorierte alle: `zendure_power` blieb bei 0,0 W, `charging_mode` auf
  „Standby“, das Gerät war in RAM.
- Netzbezug ca. 50 min lang 100–190 W.
- Im HA-Log keine `rest_command`-Fehler: Die Befehle wurden angenommen,
  aber nicht umgesetzt.
- SOC 94 %, also bereits 1 % unter dem Ladelimit, Status weiterhin
  „Charging Limit Reached“. Das passt zur Zendure-Aussage (DC-Abschaltung
  am SOC-Limit) und zeigt: 1 % unter dem Limit reicht **nicht**, damit DC
  wieder einschaltet.
- Wächter „Akku entlädt nicht trotz Bedarf“ meldete korrekt um 15:04 und
  15:16 Uhr. Er meldet aber nur und greift nicht ein.

Gelöst durch Normen von Hand, mit dem bekannten Workaround vom 06.09.
(Moduswechsel über einen anderen Modus):
- 15:17:43 Smart Discharge Only
- 15:17:59 Quick Discharge (sendet `outputLimit` 800)
- 15:18:11 Smart Discharge Only
- 15:18:18 Smart Matching
- Ergebnis: 15:18:28 „Discharging“ mit −238 W, danach −330 W. Netz wieder
  ausgeregelt.

Folgerung: Der Workaround ist jetzt zweimal belegt (06.09. und 04.10.). Ein
automatischer Eingriff des Wächters („Fix 2“, bisher zurückgestellt) wäre
der nächste Schritt; Entscheidung Normen und Prüfung durch Dr. Schmidt
stehen aus.

**Nachtrag 05.10.2026: Mechanismus gefunden, automatische Lösung live.**

Mechanismus (Dr.-Schmidt-Auswertung 04.10., rund zehn Ereignisse am
26.09. und 04.10.):
- Bei „Charging Limit Reached“ läuft die PV im Bypass direkt ins Haus.
  Der Akku springt nur an, wenn das gesendete `outputLimit` **größer als
  die PV-Leistung** ist. Beispiele: 04.10. 12:34 Uhr 800 W bei PV 782 W →
  Entladung; 13:27 Uhr 501–584 W bei PV 605–743 W → keine; ab 13:28 Uhr
  614→714 W bei PV 542→405 W → Entladung.
- Der Gielz-Startzweig sendet 0,75 × (Bezug + 5 W). Am 04.10. waren das
  14:28–15:17 Uhr 79–175 W bei PV 170–330 W, also durchgehend darunter.
  Deshalb kein Anlauf, ohne REST-Fehler.
- `soc_limit_status` wechselt erst bei SOC 93 % (Maximum 95 %) auf
  „Normal Operation“ (26.09. 14:42:51, 04.10. 15:20:16). Ab dann regelt
  das Gerät normal.
- `charging_mode` stand am 04.10. schon ab 12:56:13 auf Standby (Ausnahme
  13:28:33–13:29:19). Bedarf über der Schwelle gab es erst ab ca. 14:29.
- **Korrektur zur Aussage vom 26.09.** (Fehlerklasse 5 und
  `zendure_ausgangsleistung_dynamisch.yaml`: „Quick Discharge
  wirkungslos“): Das stimmt nur für 11:20 Uhr, als die PV am 650-W-Deckel
  stand. Um 13:51:54 Uhr hat Quick Discharge gewirkt (Discharging
  13:52:08). Der sofortige Rückwechsel sendete `outputLimit` 0 und
  beendete die Entladung wieder (Standby 13:52:13).
- Folgerung: Quick Discharge (`{"acMode":2,"outputLimit":800}`, wird in
  diesem Modus gehalten) ist der einzige wirksame Zwischenmodus, solange
  die PV unter 800 W liegt. Zurück auf Smart Matching erst bei „Normal
  Operation“, spätestens 90 s nach Entladebeginn.

Umsetzung (Normen hat zugestimmt, auch Auflage A5; Dr.-Schmidt-Fassung
unverändert übernommen, Datei `zendure_bypass_autoloesung.yaml`):
- Helfer `input_boolean.zendure_bypass_autoloesung_laeuft` ohne `initial`
  (A1).
- `automation.zendure_bypass_hanger_automatisch_losen`, id
  `zendure_bypass_haenger_autoloesung`, Hash `992d2a48da5dc8d6`, live seit
  05.10. ca. 13:41 Uhr, entity_id geprüft (A3).
- Auslöser: `netzbezug_min_40s` über der Entlade-Startschwelle, alle 5 Min
  ein Takt, HA-Start.
- Bedingung (Hänger-Signatur): Smart Matching seit 10 Min, „Charging Limit
  Reached“ seit 10 Min, `charging_mode` Standby seit 2 Min,
  `zendure_power` > −20 W, `min_40s` > Startschwelle, PV <
  `max_discharge_power`, keine Kalibrierung.
- Ablauf: Push, Merker an, Quick Discharge, warten auf Discharging (max.
  90 s), dann auf „Normal Operation“ (max. 90 s), zurück auf Smart
  Matching (nur wenn noch Quick Discharge steht), Merker aus. Nach 2 Min
  Ergebnis-Push. Danach 1 h Sperre.
- Absicherung: Beim HA-Start oder wenn der Merker noch an ist, wird ein
  stehengebliebenes Quick Discharge auf Smart Matching zurückgesetzt (A5).
- Simulation 24.09.–04.10. (5-min-Statistik): keine Fehlauslösung, nur die
  echten Episoden 26.09. nachmittags und 04.10.
- Grenzen: pro Versuch höchstens ca. 15 Wh Einspeisung. Bei PV ≥ 800 W
  greift die Lösung nicht; dann meldet weiter nur der Wächter.
- Der Wächter bleibt unverändert als reiner Melder.
- Offen (A4): Abnahme am ersten vollen Akku-Tag mit Hänger. Im Trace muss
  Quick Discharge höchstens 90 s nach Entladebeginn enden,
  `home_energy_meter_power` darf nicht 2 Min am Stück unter −300 W liegen
  und die Balkonheizung darf nicht durch den Versuch einschalten.
- Nicht umgesetzt (Normens Entscheidung): Patch der Gielz-Startformel,
  sodass sie bei „Charging Limit Reached“ die Bypass-PV einrechnet. Das
  wäre die eigentliche Ursache, ginge aber beim nächsten Gielz-Update
  verloren.

Wann Gielz überhaupt entlädt (nachgelesen 05.10., Hash `89023c6c06b06183`):
- **Entladestart** (Smart Matching Control, alle 5 s): Momentanwert
  `home_energy_meter_power` > 100 W, SOC über Geräte-Minimum (18 %),
  `zendure_power` zwischen −30 und +30 W, Modus Smart Matching,
  `soc_limit_status` „Normal Operation“ oder „Charging Limit Reached“.
  Gesendet werden 0,75 × (Bezug + 5 W). Der Zweig prüft den
  Speichermodus nicht, startet also auch aus Flash.
- **Wecken** (Flash → RAM) ist davon getrennt und folgt meist danach,
  über `zendure_power` < 0 oder `min_40s` > 100 W.
- **Schlafen** (RAM → Flash): 15 Min Standby, keine Kalibrierung und in
  den letzten 5 Min kein Bezugswert über 100 W.
- Beleg 05.10.: Bezug lag 09:20–09:27 Uhr bei ~66 W (unter 100 W, keine
  Entladung). 09:27:45 Uhr Sprung auf 154 W, 09:27:50 Uhr gibt das Gerät
  118 W ins Haus ab (5 s), 09:27:57 Uhr RAM. (Korrigiert am 05.10.
  ca. 14:30 Uhr: Zuerst stand hier „Akku −118 W“, siehe nächster Absatz.)
- Gesperrt ist die Entladung bei SOC ≤ 18 % und im Ladevorrang („Smart
  Charge Only“ ab 18 % bis 40 %; 04.10. 20:31 bis 05.10. 09:20 Uhr).

**Richtigstellung 05.10. (ca. 14:30 Uhr): `sensor.zendure_power` ist nicht die
Akkuleistung** (Dr.-Schmidt-Befund bei der Prüfung der Heizung 260/50):
- Der Sensor zeigt die Ausgangsleistung des Geräts ins Haus, aus PV
  und/oder Akku. Negativ heißt: das Gerät gibt ab.
- Beleg: Am 05.10. von 09:27:50 bis 11:02:41 stand `charging_mode` auf
  „Discharging“ bei −69 bis −200 W. Gleichzeitig stieg der SOC von 43 auf
  95 %, der Akku wurde also geladen. Auch die Gielz-Formel rechnet
  `p1 − zendure_power` als Hausbedarf.
- Im Bypass am SOC-Limit steht der Wert auf 0 W, auch wenn PV ins Haus
  läuft.
- Betroffen sind nur Texte: die Push-Meldungen der Bypass-Autolösung
  („Akkuleistung“, „Akku entlädt (… W)“) und Formulierungen im Kernbefund
  vom 04.10. An der Funktion ändert sich nichts.

**Nachtrag 05.10. (ca. 14:30 Uhr): Heizung ab 260 W, Bypass-Autolösung nur bei
Heizung aus.**
- Die Balkonheizung schaltet jetzt bei mehr als 260 W Einspeisung ein
  (5 Min.) und erst bei mehr als 50 W Netzbezug aus (2 Min.). Neu ist ein
  zweiter Ausschaltgrund: das Gerät gibt mehr als 50 W ins Haus ab
  (1 Min.). Details und Simulation in `balkon_heizung_ueberschuss.yaml`.
  Hash 7d6da0c851ac9711 → 6ad90a6d8d78dd02.
- Weil das Panel jetzt bis zu ~35 W Netzbezug verursacht, hätte die
  Hänger-Signatur der Autolösung den Panelstrom als Bedarf gewertet
  (3 Fehlauslösungen in den Daten, Dr. Schmidt). Deshalb greift sie nur
  noch bei `switch.mystrom_device` = off. Hash 992d2a48da5dc8d6 →
  082760c360e5734b, nach Korrektur der Zeitangabe in der description
  5dedbacfb67d635f.

**Abnahme A4 Bypass-Autolösung (Abend-Check 05.10., 19:30 Uhr): bestanden.**
Erster echter Lauf am selben Nachmittag:
- 16:23:42 Auslöser `min_40s` 102,4 W, SOC 94 %, „Charging Limit
  Reached“ seit 11:02, Standby seit 11:02, PV 204 W, Heizung aus. Push
  „Lösungsversuch“, Merker an, Quick Discharge.
- 16:23:59 „Discharging“ (17 s nach dem Umschalten), Geräteabgabe 800 W.
- 16:25:29 zurück auf Smart Matching nach der 90-s-Obergrenze, Merker aus.
  „Normal Operation“ kam erst 16:26:05 (SOC 93 %). Die Entladung lief
  trotzdem weiter, Gielz regelte das Netz danach auf etwa −5 W.
- 16:27:29 Push „Bypass-Hänger gelöst“ (SOC 93 %, Geräteabgabe −397 W).
- Einspeisespitze 16:24:16–16:25:49 mit −396 bis −479 W, also 94 s am
  Stück unter −300 W. Das liegt unter den 2 Minuten, ab denen die
  Balkonheizung einschalten könnte. Rund 11 Wh eingespeist.
- Balkonheizung blieb aus, Modus danach Smart Matching, Merker aus.
  Danach bis 19:30 Uhr nur noch abgewiesene Läufe (Bedingungen nicht
  erfüllt, Akku nicht mehr am Limit).
- Ohne Autolösung hätte der Hänger wie am 04.10. bis zum Eingriff von Hand
  gedauert.

Abnahme Heizung 260/50 noch offen: Nach dem Einspielen (14:29 Uhr) lag
die Einspeisung nie über etwa 190 W, es gab also keinen Schaltfall.
Nächster Check am nächsten Sonnentag.

**Abnahme Heizung 260/50 (Check 06.10., 18:30 Uhr): bestanden.**
- 10:59:01 eingeschaltet über `soc_wechsel` („Charging Limit Reached“
  seit 10:57, Netz −572 W, Geräteabgabe 0 W). 13:28:10 ausgeschaltet über
  `netzbezug_aus` (Bezug 13:26:10–13:28:10 über +50 W, Wolke).
- Laufzeit 2,48 h am Stück, ein automatischer Zyklus, kein Kurzzyklus.
  Netzbezug während des Laufs zusammen 5 Wh; über +50 W nur die 2
  Ausschalt-Minuten am Ende (1,6 % der Zeit). Es wurden trotzdem noch
  519 Wh eingespeist, der Überschuss war größer als das Panel.
- `zendure_speist` hat während des Laufs nicht ausgelöst (Geräteabgabe
  durchgehend 0 W). Die Bypass-Autolösung lief nicht, solange das Panel an
  war.
- Nebenbefund: 08:31:23 wurde das Panel von Hand eingeschaltet (kein Trace
  der Automatik, Akku noch nicht voll). Die Automatik schaltete es 08:35:00
  beim Resync wieder aus. Das ist das vorgesehene Verhalten bei
  Automatik = an.

**Zweiter Lauf der Bypass-Autolösung 06.10., 16:13 Uhr: NICHT gelöst.**
- 16:13:49 Auslöser `min_40s` 139 W, SOC 94 %, PV 295 W, Panel aus.
  Quick Discharge, 16:14:05 „Discharging“ mit 800 W Geräteabgabe.
- 16:15:35 zurück auf Smart Matching nach der 90-s-Obergrenze. Der SOC
  stand noch bei 94 %, also weiter „Charging Limit Reached“. 16:15:37 wieder
  Standby: Der Rückwechsel hat die Entladung beendet, genau der
  Mechanismus vom 26.09. Push „NICHT gelöst“.
- 16:24:48 lief die Entladung von selbst wieder an (Gielz-Start über der
  PV), 16:25:52 SOC 93 %, 16:25:58 „Normal Operation“. Der Hänger dauerte
  damit etwa 11 Minuten statt bis zum Eingriff von Hand.
- Ursache: 1 % SOC sind etwa 24 Wh. Bei 800 W Geräteabgabe und rund
  290 W PV liefert der Akku nur etwa 510 W, braucht also knapp 3 Minuten
  für 1 %. Am 05.10. reichte es nur, weil die Entladung nach dem Rückwechsel
  weiterlief.
- Die 90-s-Grenze stammt aus der Zeit, als die Heizung schon nach 2 Minuten
  Einspeisung über 300 W einschaltete. Seit 05.10. braucht sie 5 Minuten über
  260 W. Vorschlag (noch nicht umgesetzt, Normen und Dr. Schmidt
  entscheiden): Obergrenze auf etwa 4 Minuten anheben.

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

Ergänzung dazu (06.09., nach dem bestätigten Workaround oben): Der
tatsächlich wirksame Schritt war kein "Aufheben der Einspeisesperre",
sondern ein echter Moduswechsel (Manual -> Smart Matching). Die
Einspeisesperre und der Bypass-Hänger waren zwei unabhängige Probleme,
die zufällig am selben Nachmittag zusammenfielen.

---

## Fehlerklasse 5 — Henne-Ei-Deadlock zwischen Standby-Timeout und RAM-Weckbedingung (26.09.2026)

**Nachgewiesen, live diagnostiziert (Dr.-Schmidt-Prüfung, Agent a96b2be7):**
`automation.zendure_zensdk_gielz_global` schickt das Gerät nach
`input_number.zendure_setting_standby_delay` (15 Min) ununterbrochenem
`charging_mode` = "Standby" in `sensor.zendure_storage_mode` = "Flash
Memory" (Branch "Put on standby after xx minutes of inactivity"). Im
Flash-Modus werden Steuerbefehle dauerhaft ins Flash geschrieben; der
verschleißarme Modus für häufige Befehle ist "RAM Memory", in dem die
5-Sekunden-Befehle nur flüchtig im RAM landen (siehe Community-Doku zu
anderen Zendure-HA-Projekten, arselzer/solarflow-homeassistant: im
Flash-Modus ~17.000 Schreibvorgänge/Tag im 5-Sekunden-Takt). Korrektur
28.09.: Die frühere Fassung dieses Absatzes nannte fälschlich Flash den
verschleißschonenden Modus (von Dr. Schmidt bei der Abnahme der
Entprellung beanstandet). Der einzige Rückweg (Branch "When storage mode is
set to Flash set it to RAM") verlangte bislang `sensor.zendure_power` >
100 oder < 0 — Werte, die im schlafenden Zustand mit `zendure_power` = 0
nie eintreten können. Ein Henne-Ei-Deadlock: das Gerät entlädt nicht, weil
es schläft, und wacht laut Automatisierung nur auf, wenn es bereits (nicht
nullwertige) Leistung liefert.

Zweimal am selben Tag beobachtet: 10:35–11:37 Uhr (47+ Minuten,
Netzbezug bis 1829 W bei 95–100 % SOC) und erneut ab 13:52 Uhr. Ein
direkter, per Hand ausgelöster "Quick Discharge"-Befehl mit vollem
Leistungswert blieb während des Hängers wirkungslos (Akku weiter 0 W;
Korrektur 05.10.: gilt nur für 11:20 Uhr, siehe Fehlerklasse 1) —
das schließt aus, dass eine zu niedrige `max_discharge_power`-Einstellung
die Ursache war (separat mit Live-Gegenprobe belegt: PV und Akku liefen
am 26.09. 10:30–10:35 Uhr bereits gleichzeitig mit zusammen >1150 W bei
identischem Setting).

**Fix (26.09., in `automation.zendure_zensdk_gielz_global` direkt
gepatcht, config_hash vor Patch `60bfc4a914099725`):** Der
Rückweg-Branch bekommt eine dritte Wach-Bedingung, die unabhängig vom
aktuellen Leistungsfluss greift, sobald tatsächlich Entladebedarf
besteht:
```yaml
condition: numeric_state
entity_id: sensor.home_energy_meter_power
above: input_number.zendure_setting_start_discharging_at
```
Das durchbricht den Deadlock, sobald das Haus mehr zieht als die
Entlade-Startschwelle, unabhängig davon ob `zendure_power` schon einen
Wert ungleich 0 zeigt. Direktes Editieren eines Drittanbieter-Pakets ist
mit Bedacht zu behandeln: ein künftiges Gielz-Update könnte diesen
Branch überschreiben — bei Paket-Updates gegenprüfen, ob der Patch noch
vorhanden ist.

**Bekannte Restlücke (Vormittag):** Auch mit `storage_mode` = "RAM Memory"
hat die Entladung nach dem manuellen `rest_command.zendure_save_in_ram`-
Aufruf am 26.09. nicht sofort eingesetzt (charging_mode blieb einige
Minuten auf "Standby", bevor sich die Lage durch sinkenden Hausbedarf von
selbst entspannte) — ob der neue Wach-Pfad das zuverlässig behebt oder ob
es eine zusätzliche geräteseitige Verzögerung beim tatsächlichen
Relais-Schalten gibt, war nach dem ersten Patch noch nicht abschließend
verifiziert.

**Nachtrag 26.09., 14:29–14:40 Uhr — zweiter, tieferliegender Fund und
finale Behebung:** Am Nachmittag trat der Hänger erneut auf (`charging_mode`
"Standby" seit 14:13, `home_energy_meter_power` 250–330 W Netzbezug,
`zendure_power` 0 W), diesmal kurz nachdem Normen das Firmware-Update auf
SolarFlow 2400 Pro V2.0.4 durchgeführt hatte (vorher V2.0.2) — zeitliche
Überschneidung, siehe Einordnung unten. Live-Trace-Analyse eines
Automatisierungslaufs um 14:30:10 Uhr deckte einen zweiten, bis dahin
unentdeckten Fehler auf: **derselbe 5-Sekunden-Zyklus feuerte gleichzeitig
den Wach-Branch (heute Vormittag gefixt) UND den "Put on standby after xx
minutes of inactivity"-Branch**, weil Letzterer nur auf
`storage_mode`/`charging_mode`/`calibrating` prüfte, aber nicht darauf, ob
gerade akuter Entladebedarf besteht. Ergebnis: `rest_command.zendure_full_standby`
und `rest_command.zendure_x_discharge` gingen im Abstand von ~40
Millisekunden an dasselbe Gerät raus — ein Wettlauf zweier
gegensätzlicher Befehle, den das Gerät mit Verharren im Bypass "gewann".

**Zweiter Fix (14:33 Uhr, config_hash vor Patch `bab48c9832900f26`, danach
`a5a45183210c83ec`):** Spiegelbildliche Sperre im Standby-Branch ergänzt —
er darf nicht mehr auslösen, solange Entladebedarf besteht:
```yaml
condition: not
conditions:
  - condition: numeric_state
    entity_id: sensor.home_energy_meter_power
    above: input_number.zendure_setting_start_discharging_at
```
Trace-Bestätigung direkt danach (14:34:10 Uhr): Standby-Branch korrekt
`false` trotz erfüllter Grundbedingungen, weil die neue Sperre griff — kein
erneuter Rückfall nach Flash Memory mehr. Die Automatisierung schickte in
der Folge weiter zuverlässig `x_discharge`-Befehle raus; das Gerät selbst
brauchte bis 14:40:04 Uhr, um darauf mit "Discharging" zu reagieren
(bestätigt sowohl in HA: `zendure_power` -727 W, als auch in der
Zendure-App: 432 W Entladevorgang, 800 W Hausausgang, Netzbezug von 330 W
auf 125 W gefallen). Die rund 6-minütige Verzögerung zwischen Fix und
sichtbarer Entladung bleibt als offene Frage stehen (siehe unten).

**Einordnung Firmware-Update (V2.0.2 → V2.0.4):** Das Update wurde von
Normen etwa zeitgleich mit dem zweiten Auftreten des Hängers eingespielt,
bevor der zweite Fix identifiziert war. Der offizielle Changelog nennt nur
"Bekannte Probleme behoben" ohne Details. Da der Hänger auch nach
abgeschlossenem Update fortbestand und sich erst durch den zweiten
Automatisierungs-Patch auflöste, ist die naheliegendste Lesart, dass das
Update das Symptom nicht behoben hat — die Koinzidenz lässt sich aber mit
den vorliegenden Daten nicht vollständig ausschließen, da beide Eingriffe
(Update und zweiter Patch) in einem Fenster von rund 10 Minuten
zusammenfielen. Für das offene Zendure-Ticket ist das dennoch verwertbar:
Bypass-Hänger nachweislich auch auf V2.0.4 reproduziert, mit Beleg
(Zeitstempel, REST-Payloads), dass valide Entlade-Befehle beim Gerät
ankamen, ohne dass es sofort reagierte.

**Bekannte Restlücke (nach beiden Fixes):** Die ~6 Minuten zwischen dem
zweiten Patch (14:33) und dem tatsächlichen Wechsel zu "Discharging"
(14:40) sind nicht erklärt — möglich sind eine geräteseitige
Nachwirkung des Firmware-Updates, ein noch unbekannter dritter
Automatisierungs-Effekt, oder eine normale Reaktionsträgheit des Geräts
nach längerem Bypass. Weitere Beobachtung nötig, ob diese Verzögerung bei
künftigen Vorfällen wiederkehrt oder eine Einmaligkeit war.

**Abend-Check 26.09., 19:31 Uhr (geplant, Ergebnis):** Alle vier
Prüfpunkte bestanden. `storage_mode` blieb von 14:33 Uhr bis zum
Check-Zeitpunkt durchgehend "RAM Memory" — kein einziger Rückfall nach
Flash Memory, der Deadlock-Fix hält über den ganzen Nachmittag/Abend.
`charging_mode` ist zuverlässig auf "Discharging" gewechselt und blieb ab
16:43:48 Uhr durchgehend stabil dort (kein Hängen im Standby mehr).
`home_energy_meter_power` lag beim Check bei -1,1 W (Akku deckt
Hausbedarf fast exakt). Die neue Automatisierung
`zendure_ausgangsleistung_bei_vollem_akku` zeigte genau einen sauberen
Wechsel 800→650 W (14:44:51 Uhr, als `soc_limit_status` nach Entladestart
auf "Normal Operation" fiel) und danach kein Flattern.

**Neue Beobachtung (nicht Fehlerklasse 5, vermutlich unkritisch):**
Zwischen 15:53 und 16:44 Uhr wechselte `charging_mode` rund 130 Mal
zwischen "Standby" und "Discharging" (Median-Abstand im Sekunden- bis
niedrigen Minutenbereich). Deckt sich zeitlich exakt mit
`home_energy_meter_power`, der in genau diesem Fenster zwischen -137,8 W
und +121,7 W pendelte — knapp um die Entlade-Startschwelle (100 W)
herum. `storage_mode` blieb dabei durchgehend "RAM Memory", also kein
Zusammenhang mit Fehlerklasse 5. Liest sich als normale Reaktion der
Automatisierung auf einen zu diesem Zeitpunkt tatsächlich unruhigen
Hausverbrauch (vermutlich ein an-/abschaltendes Gerät), nicht als
Automatisierungsfehler. Potenziell relevant für Relais-Verschleiß, falls
sich dieses Muster künftig regelmäßig wiederholt — dann wäre eine
Entprellung (z. B. kurze `for:`-Verzögerung vor dem Umschalten) zu
erwägen. Für heute keine Aktion nötig.

**Nachtrag 28.09. — Kurzzeit-Flattern trotz beider Patches, dritter Fix
(Entprellung):** Am 28.09. zog das Haus bei vollem Akku (SOC 94–95 %,
"Charging Limit Reached") wiederholt 100–200 W aus dem Netz. Dr.-Schmidt-
Cross-Check (13:25–13:50 Uhr) belegte: Beide Patches vom 26.09. waren
noch aktiv (Hash `a5a45183210c83ec`), prüften aber den Hausverbrauch als
unentprellten Momentanwert im 5-Sekunden-Takt. Ein einziger Takt über
100 W weckte das Gerät (Storage→RAM, `x_discharge`), der nächste Takt
darunter schickte es per Standby-Branch zurück nach Flash, bevor der
Entlade-Befehl wirken konnte (13:29:52 RAM für 5 s, 13:33:48 für 3 s,
14:10:07 für 10 s; am 27.09. 14:14–15:05 rund 25 Wechsel). Der Akku hat
von 11:08 bis 13:45 Uhr praktisch nicht entladen. Ein Mitsteuern durch
Zendure-HEMS wurde dabei geprüft und nicht gefunden: keine weitere
Zendure-Integration in HA, geräteseitige Einstellungen änderten sich in
vier Tagen nur auf HA-Befehl; die morgendlichen 1200-W-Ladestöße
(26.–28.09., 06:00–06:30) sind der SOC-Schutz der Gielz-Automatisierung
bei SOC 17 % < Minimum 18 %.

Fix (28.09., nach Dr.-Schmidt-Abnahme mit Auflagen, Hash vorher
`a5a45183210c83ec`, nachher `24cba37c9f8593ab`): zwei statistics-Helfer
auf `sensor.home_energy_meter_power`, beide mit `keep_last_sample: true`:
- `sensor.zendure_netzbezug_min_40s` (`value_min`, `max_age` 40 s,
  `sampling_size` 100) ersetzt den Momentanwert in der Weck-Bedingung
  (`actions[1].choose[0].conditions[2].conditions[2]`). Geweckt wird nur,
  wenn der Bezug im ganzen Fenster über der Schwelle lag. 40 s statt 20 s,
  weil der Zähler stoßweise meldet (Lücken bis 16 s); 40 s garantieren
  mindestens ~24 s tatsächlich beobachteten Bezug.
- `sensor.zendure_netzbezug_max_5min` (`value_max`, `max_age` 300 s,
  `sampling_size` 500) ersetzt den Momentanwert in der Schlaf-Sperre
  (`actions[1].choose[1].conditions[4].conditions[0]`). Schlafen gelegt
  wird nur, wenn 5 Minuten lang kein Wert über der Schwelle lag — das
  Gerät bleibt nach jedem Bedarf mindestens 5 Min wach (RAM). 500 statt
  100 Samples, weil bei Lastwechseln bis ~225 Werte in 5 Min anfallen und
  der Puffer sonst still auf ~2 Min schrumpft.
- Ein erster Entwurf mit 20-s-Fenstern für beide wurde von Dr. Schmidt
  nicht freigegeben und wieder entfernt.

Verhalten bei Sensorausfall: Wird die Quelle `unavailable`, werden auch
die Helfer `unavailable`; die Bedingungen ergeben false (kein Wecken,
Schlafen erlaubt) — unkritisch, Smart Matching ist dann ohnehin gesperrt
und Emergency Shutdown greift. Meldet die Quelle `unknown`, halten die
Helfer wegen `keep_last_sample` den letzten gültigen Wert; lag der über
100 W, bleibt das Gerät bis zur Rückkehr der Quelle wach (harmlos).

Was dieser Fix nicht behebt: die geräteseitige Trägheit (13:36:40–13:38:22
Uhr 102 s durchgehender Bedarf ohne Anlauf trotz RAM; 26.09. ~6 Min) —
offen im Zendure-Ticket. Ebenfalls vorgemerkt, nicht neu: der Weck-Branch
prüft den SOC nicht. Die Wächter-Erweiterung auf dieses Flatter-Muster
("Fix 2") ist auf Normens Wunsch zurückgestellt.

Abnahmekriterium (offen, im Abend-Check 28.09. zu prüfen): In der
`storage_mode`-Historie kein Wechsel RAM→Flash mehr früher als 5 Min
nach dem letzten Bezugswert über 100 W; mindestens ein Trace, in dem die
Schlaf-Sperre greift.

**Ergebnis Abend-Check 28.09. (20:00 Uhr) — Abnahme bestanden.**

- Einziger Wechsel RAM→Flash am Nachmittag: 14:30:07 Uhr, 5 Min 4,6 s
  nach dem letzten Bezugswert über 100 W (14:25:03 Uhr). Früher schlief das
  Gerät nicht ein. Genau so soll die Schlaf-Sperre `max_5min` wirken:
  Das Einschlafen passt auf die Sekunde zu ihrem Ablauf.
  Ein Trace, in dem die Sperre greift, lässt sich im Nachhinein nicht mehr
  zeigen: Die Gielz-Automatisierung läuft alle 5 s, ihre gespeicherten
  Traces sind nach wenigen Sekunden überschrieben. Dieser Teil des
  Kriteriums ist daher nur indirekt belegt, über den zeitlichen Ablauf.
- Wecken: 42 s nach Beginn eines anhaltenden Bedarfs. Kurze Spitzen von
  4 s und 6 s wecken das Gerät nicht mehr. Ab 14:53:33 Uhr blieb es den
  ganzen Abend in RAM. Das Flattern vom Vormittag ist weg.
- Entladung lief ohne Unterbrechung von 15:56 bis 19:29 Uhr, bis zum
  Discharge Limit.
- Nicht behoben (war auch nicht Ziel): Das Gerät reagiert weiter träge.
  Um 14:53:33 Uhr war es wach, entladen hat es erst ab 15:00:00 Uhr. Das
  bleibt im Zendure-Ticket.
- Der Netzbezug von ~150 W zwischen 14:20:59 und 14:25:03 Uhr war kein
  Zendure-Fehler: Die Balkonheizung (~300 W) wurde von Hand eingeschaltet.
  Der Zähler sprang um +298 W, das Schalt-Ereignis steht ohne
  HA-Kontext im Logbuch (siehe unten).
- Bypass-Wächter: Heute nur `failed_conditions`, kein Hänger erkannt.
- Verbindungsabbrüche von 192.168.178.101 (25.–28.09., jeweils 1–8 s)
  fallen zeitlich mit keinem der Fehlerbilder zusammen. Das
  Systemprotokoll zeigt seit dem HA-Neustart um 15:31 Uhr keine
  Einträge zu dieser IP.

Am Rande (betrifft nicht Zendure): Die Balkonheizung wurde heute um
14:21, 14:52, 18:57 und 19:47 Uhr ohne HA-Kontext eingeschaltet. Ohne
Kontext heißt: kein Befehl über HA, sondern am Gerät selbst oder über die
myStrom-App. Zwischen 12:13 und 13:22 Uhr hat die Automatik 13 Mal
eingeschaltet und 14 Mal ausgeschaltet. (Eine frühere Fassung dieses
Absatzes nannte „16 Mal“, gezählt aus den Logbuch-Meldungen. Die
erscheinen aber auch, wenn die Heizung schon an war. Korrigiert nach dem
Schaltverlauf, Dr.-Schmidt-Fund.) Grund ist eine Rückkopplung: Die
Heizung zieht ~295 W, die Hysterese betrug aber nur 100 W (an unter
−300 W, aus über −200 W). Schaltet die Heizung ein, sinkt die
Einspeisung unter 200 W, die Heizung geht aus, die Einspeisung steigt
wieder über 300 W, und das Spiel beginnt von vorn.
Behoben am selben Abend nach Normens Vorgabe: Die Aus-Schwelle liegt
jetzt bei −50 W, die Ein-Schwelle bleibt bei −300 W. Details und
Restfall stehen in `balkon_heizung_ueberschuss.yaml`, Nachtrag 28.09.
abends.

**Tages-Check 29.09. (Stand 20:30 Uhr)**

- **Balkonheizung, erster Tag mit 300/50:** genau ein Zyklus.
  - An um 12:05:40 durch die Automatik (soc_wechsel, 2 Min. nach
    „Charging Limit Reached“), aus um 13:15:00 durch den Resync-Tick.
    Laufzeit 69 Min.
  - Kein Flattern, keine Schaltung ohne HA-Kontext, Modus den ganzen
    Tag „Automatisch“.
  - Das Aus um 13:15 kam über den Momentanwert am Resync-Tick. Im
    5-Min.-Fenster davor lag die Einspeisung bei laufendem Panel im
    Mittel bei 67 W, die Spitzen reichten bis +42 W Bezug. Der
    Überschuss ging also gerade zu Ende.
  - Danach lag der Überschuss bis Status-Ende (14:25) nie 2 Min. über
    300 W. Wiedereinschalten war also korrekt nicht vorgesehen.
- **650/800:**
  - 800 W um 12:05:39, zwei Minuten nach „Charging Limit Reached“
    (12:03:39). Das Gerät hat um 12:05:42 übernommen.
  - 650 W um 14:27:31, zwei Minuten nach „Normal Operation“ (14:25:31).
    Das Gerät hat um 14:27:33 übernommen.
  - Das 800-W-Limit wurde bei Lastspitzen tatsächlich ausgeschöpft.
- **Netzbezug:** Alle 5-Min.-Fenster mit Bezug lassen sich einer
  Designregel zuordnen, ein Hänger war nicht dabei:
  - Akku leer (18 %) bis 08:08 Uhr.
  - Ladevorrang bis 40 %: erreicht 09:07:07, Entladung ab 09:07:15.
  - Grundlast unter der 100-W-Startschwelle: 10:10–10:30 Uhr ~73 W,
    13:50–14:00 Uhr ~46–86 W.
  - Lastspitzen über dem 650/800-W-Limit: Koch- und Wasserkocher-Lasten
    bis 2,4 kW.
  - Ab 14:30 Uhr regelt der Akku das Netz im Mittel auf −2 bis −6 W.
    Das passt zu discharge_buffer = 5 W.
- **Wächter:** „Akku entlädt nicht trotz Bedarf“ hat heute nie
  ausgelöst, jeder Lauf endete mit `failed_conditions`.
  `sensor.zendure_error` meldete durchgehend „No Notifications“.
- **Verbindung:** Ein gemeinsamer Aussetzer von Zendure (1 s) und myStrom
  (20 s) um 00:46 Uhr, vermutlich WLAN oder Router. Weitere
  myStrom-Aussetzer um 12:00 und 18:50 Uhr (je 20 s). Folgen hatte
  keiner davon.
- **Log:** Alle 3 Min. „http://unknown/api/v1/data“. Das ist der
  bekannte HomeWizard-P1-Eintrag aus dem Gielz-Paket (siehe
  `gielz-upstream-issues.md`, Issue 1) und harmlos.
- **Neu aufgefallen: nächtliches Weck-/Schlaf-Pendeln.**
  - Zwischen 00:06 und 09:05 Uhr wechselte `storage_mode` 18 Mal von
    Flash auf RAM und nach Standby-Ablauf zurück.
  - Der Modus stand die ganze Zeit auf „Smart Charge Only“ (Ladevorrang
    seit 28.09., 19:29:34 bis 29.09., 09:07:07).
  - Der SOC lag bei 18 % (17 % nur 49 s um 03:45), ab 08:08 stieg er.
    Die letzten drei Weckvorgänge lagen bei 20, 29 und 39 %.
  - Ursache ist jedes Mal die dritte Weckbedingung aus dem Patch vom
    26.09. (`netzbezug_min_40s` > 100 W). Sie griff 3–5 s nach dem
    Überschreiten der 100 W, während `zendure_power` bei −0,0 W lag
    (Dr.-Schmidt-Auswertung). Die nächtliche Grundlast pendelt um
    66–200 W, und die Bedingung prüfte weder SOC noch Modus.
  - Folgen für den Betrieb hatte es keine, weil die Entladung gesperrt
    war. Es waren aber unnötige Befehle ans Gerät.

**Fix 29.09. abends (von Normen freigegeben, Dr.-Schmidt-Abnahme mit
Auflagen):**
- In `automation.zendure_zensdk_gielz_global` wurde nur
  `actions[1].choose[0].conditions[2].conditions[2]` geändert. Diese
  Weckbedingung weckt jetzt nur noch, wenn zusätzlich zwei Dinge
  gelten:
  - `sensor.zendure_total_state_of_charge` liegt über
    `sensor.zendure_minimum_state_of_charge`. Das ist bewusst die
    Geräte-Entity, nicht der `input_number` (Auflage 1), weil die
    Gielz-Entladesperre und der SOC-Schutz genau gegen diese Entity
    vergleichen.
  - Der Modus ist nicht „Smart Charge Only“. Diese Bedingung allein
    hätte alle 18 Weckvorgänge verhindert. Die SOC-Bedingung allein
    hätte 3 davon durchgelassen (20, 29 und 39 %).
- Hash vorher `24cba37c9f8593ab`, nachher `6a78d0e34d691367`. Per Diff
  bestätigt, dass sich sonst nichts geändert hat.
- **SOC-Schutz unberührt:** choose[2] prüft den `storage_mode` nicht.
  Am 26.09. lud er belegt aus dem Flash-Modus heraus mit 1200 W (06:00).
  Er greift jetzt sogar direkter, weil choose[0] bei SOC ≤ min den
  5-s-Takt nicht mehr belegt.
- **Kein Rückfall in den Henne-Ei-Deadlock:** Bei Smart Matching und
  SOC über min ist die Bedingung logisch identisch mit vorher.
- **Abnahmekriterium für die Nacht 29./30.09.:**
  - Im Modus „Smart Charge Only“ kein Wechsel Flash→RAM, außer wenige
    Sekunden nach einer Schutzladung (`set_charge_power` = 1200).
    Erwartet: höchstens 1 statt 18 Wechsel.
  - Nach der Ladevorrang-Freigabe auf „Smart Matching“ wird geweckt,
    sobald `min_40s` über 100 W liegt, spätestens nach 10 s.

**Abnahme Nacht 29./30.09. (Check 30.09., 12:00 Uhr): bestanden.**
- **Nachtruhe:**
  - Das Gerät schlief um 23:02:12 ein. Bis dahin war es seit dem Abend in
    RAM, weil die Abendlast über 100 W die Schlaf-Sperre `max_5min` hielt.
  - Im Modus „Smart Charge Only“ gab es danach genau **einen** Wechsel
    Flash→RAM, um 05:30:52 (statt 18 in der Vornacht). Er kam direkt nach
    der Schutzladung: SOC 17 % um 05:30:37, `set_charge_power` 1200 W um
    05:30:42, `charging_mode` „Charging“ um 05:30:48, noch im
    Flash-Modus.
  - Um 05:56:42 wieder Flash. Damit ist erneut belegt, dass der SOC-Schutz
    ohne Wecken aus Flash heraus lädt.
- **Freigabe nach dem Ladevorrang:**
  - SOC 40 % und Wechsel auf „Smart Matching“ um 10:58:09. Der Netzbezug
    lag danach nur bei ~65 W, also unter der 100-W-Schwelle. `min_40s` kam
    deshalb nie über 100 W, und die neue Weckbedingung war in diesem Fall
    gar nicht gefragt.
  - Um 11:00:03 sprang der Bezug auf 188 W. Um 11:00:10 lief die
    Entladung (−144 W, sofort danach −200 W), und das noch im
    Flash-Modus: Der Gielz-Startzweig von Smart Matching prüft den
    `storage_mode` nicht.
  - Um 11:00:16 folgte RAM über OR[1] (`zendure_power` < 0). Ab 11:00:21
    regelte das Netz auf −5 bis +1 W.
  - Reaktionszeit Bedarf→Entladung: **7 s**. Am 28.09. waren es noch 42 s
    und mehr.
- **Balkonheizung und 650/800:** Nicht angesprochen. Der Akku war bis
  12:00 nicht voll (SOC 60 %), die Heizung blieb aus, `max_discharge_power`
  stand durchgehend auf 650 W. Nichts zu beanstanden.
- **Verbindung:** Die Zendure-Sensoren waren 5-mal für je 1 s nicht
  verfügbar (05:13, 06:59, 07:29, 08:28, 08:52). Das ist öfter als an den
  Vortagen, blieb aber ohne Folgen. Beim myStrom gab es 3 Aussetzer von je
  20 s (21:10, 05:44, 06:22). Weiter beobachten.


---

## SOC-Schutzladung nur noch 11–15 Uhr (02.10.2026)

Normens Wunsch: Der Gielz-SOC-Schutz (`actions[1].choose[2]` „Charging to
minimum SOC (protection)“) soll nachts nicht mehr mit 1200 W aus dem Netz
nachladen, sondern erst mittags. Bisher lag jede Unterschreitung unter
18 % nachts oder früh morgens (07:16, 06:00, 06:23, 06:27, 03:45, 05:30
und 03:46 Uhr). Jede löste ca. 50 s Netzladung mit 1200 W aus, also
15–30 Wh.

**Dr.-Schmidt-Prüfung 01.10.: ZURÜCK für die naive Variante.** Die
vorhandene, deaktivierte Bedingung (sun: sunrise +2 h bis sunset −2 h ODER
`home_energy_meter_power < start_charging_at`) einfach zu aktivieren,
hätte auch den Stopp-Befehl (0 W) zeitgegatet. In „Smart Charge Only“ und
„Smart Matching“ stoppt der Gielz-Balancing-Zweig trotzdem. In „Standby“
und „Smart Discharge Only“ stoppt aber niemand. Eine angefangene
Schutzladung liefe dort bis `socSet` 95 %, also rund 1,8 kWh.

**Umsetzung 02.10. (Dr.-Schmidt-Freigabe mit Auflagen, Variante B):**
- `conditions[2]` ist jetzt ein OR aus zwei Teilen:
  - **Start:** SOC < Geräte-Minimum UND `condition: time` 11:00–15:00.
  - **Stopp:** SOC == Minimum UND `set_charge_power` == 1200. Bewusst
    **nicht** zeitgegatet, damit eine laufende Ladung in allen sieben
    Modi des Zweigs bei 18 % endet.
- Die deaktivierte Bedingung `conditions[4]` wurde ersatzlos gelöscht.
- Die Einspeise-Hälfte (> 300 W Einspeisung startet die Ladung) ist auf
  Normens Wunsch weggefallen. Laut Dr. Schmidt war sie praktisch toter
  Code und hätte, wenn sie doch einmal gegriffen hätte, Netzstrom trotz
  Überschuss gezogen.
- Hash vorher `6a78d0e34d691367`, nachher `89023c6c06b06183`. Per Diff
  bestätigt: Außer diesen zwei Stellen ist nichts verändert.
- **Erwartung:**
  - Nachts sinkt der SOC auf ca. 17 %, im Winter nach einem Ladeende
    kurz vor 15 Uhr schlimmstenfalls auf ca. 15 %. Die Entladung bleibt
    durch das Geräte-Minimum 18 % gesperrt.
  - An PV-Tagen hebt die Sonne den SOC vor 11 Uhr ohne Netzladung über
    18 %. An dunklen Tagen startet der Schutz um 11 Uhr.
- **Abnahmekriterium für die nächsten Nächte:** Außerhalb 11–15 Uhr kein
  `set_charge_power` 1200, außer einem Stopp-Befehl mit 0 W.
- **Achtung:** Ein Gielz-Update überschreibt diesen Patch, genau wie die
  Patches vom 26., 28. und 29.09.

**Abnahme 03.10. (Check 15:30 Uhr): bestanden.**
- Im ganzen Zeitraum 02.10. 21:00 bis 03.10. 15:30 wurde kein
  `set_charge_power` 1200 gesetzt, auch keine Schutzladung außerhalb des
  Fensters.
- Der SOC fiel um 04:18 auf 17 %. Um 09:10 hob ihn die PV ohne
  Ladebefehl wieder auf 18 %, also vor dem Fenster und ohne Netzladung.
  Genau so war es gewünscht.
- Nachtruhe: Das Gerät schlief um 22:38 ein, danach gab es bis zur
  Ladevorrang-Freigabe (12:35:21, SOC 40 %) keinen Wechsel Flash→RAM.
  RAM folgte 5 s nach der Freigabe.
- Die Ladebefehle 194 W und 191 W um 13:21 und 13:23 kamen aus dem
  normalen Smart-Matching-Ladezweig, nicht vom Schutz.
- Nebenbefund: Die Zendure-Sensoren waren mehrfach kurz `unavailable`,
  zwischen 13:27 und 13:38 allein 5-mal für je ca. 1 s. Folgen hatte das
  keine, weiter beobachten.

## Energie-Dashboard: Einspeisung um Faktor ~2,5 zu hoch (02.10.2026)

Am 02.10. zeigte das Dashboard 4,52 kWh Einspeisung (tatsächlich ca.
0,12–0,23 kWh), Autarkie 0 % und Eigenverbrauchsquote 5,8 %.

**Ursache:** Die Integrations-Helfer `sensor.einspeisung_kwh` (Wh) und
`sensor.netz_bezug_kwh` (kWh) rechneten mit der Methode **trapezoidal**.
Ihre Quellen sind Templates, die bei unverändertem Wert keinen Zustand
schreiben. Trapez interpoliert deshalb jede Nullphase linear bis zum
ersten Wert ungleich 0. Am 02.10.: Die Einspeisung stand 18,165 h auf 0
(01.10. 15:51 bis 02.10. 10:01), dann 467,9 W. Das ergibt
(0 + 467,9)/2 × 18,165 h = **+4249,67 Wh** auf einen Schlag.

Das Problem ist systematisch, kein Einzelfall (Dr.-Schmidt-Auswertung):
- Seit 28.08. weist die Statistik 25,45 kWh Einspeisung aus, real waren
  es ca. 10,25 kWh (+148 %).
- Beim Bezug sind es +8,0 kWh (+3,9 %) seit 25.08.

**Behebung 02.10. ca. 20:50 Uhr:**
1. Beide Helfer per Options-Flow auf Methode **left** umgestellt.
   Entity, Statistik-ID, Einheit und Zählerstand blieben erhalten; es gab
   keinen Sprung (Einspeisung blieb bei 26214,597 Wh).
2. Statistik-Korrektur `recorder/adjust_sum_statistics` für
   `sensor.einspeisung_kwh`, Stunde 2026-10-02T08:00Z: **−4289,84 Wh**.
   Tageswert 02.10. danach 0,234 kWh statt 4,52 kWh.

3. Vortage korrigiert (02.10. abends, von Normen freigegeben): die
   übrigen 13 Stunden der Dr.-Schmidt-Liste „Stufe A“, zusammen
   −6942,05 Wh. Darunter 19.09. 09 Uhr (−2914,52), 29.08. 07 Uhr
   (−1400,22) und 25.09. 10 Uhr (−893,28). Jede Stunde zeigt danach
   genau den nach links-Riemann erwarteten Wert, z. B. 25.09. 10 Uhr
   432,16 Wh und 19.09. 09 Uhr 9,94 Wh. Insgesamt sind damit
   −11.231,9 Wh aus `sensor.einspeisung_kwh` entfernt.

**Bewusst nicht korrigiert:**
- Ca. +3,97 kWh systematischer Trapez-Überschuss, verteilt auf viele
  kleine Stunden (je < 100 Wh).
- Beim Bezug ca. +8,0 kWh seit 25.08., ohne Einzelspitze.
- Der Zeitraum 26.08. 15 Uhr bis 28.08. 09 Uhr (damals andere Quelle,
  nicht prüfbar).

Eine stundenweise Vollkorrektur wäre möglich (CSV im Scratchpad), auf
Wunsch.

**Folgewirkungen:**
- `sensor.stromzahler_bezug_1_8_0` liest den Zustand von `netz_bezug_kwh`
  und liegt seit der Basis vom 29.09. um ca. +0,27 kWh zu hoch. Das wird
  bei der nächsten Ablesung neu kalibriert, nicht nachträglich verbogen.
- „Einspeisung heute“ (Utility Meter) wurde bewusst **nicht** kalibriert,
  weil eine Absenkung als Reset gewertet würde. Der Wert ist bis
  Mitternacht falsch und korrigiert sich dann selbst.
- `sensor.zendure_eigenverbrauchsquote`: Die vergangenen Tageswerte
  bleiben verfälscht.

**Abnahme 03.10. (Methode „left“): bestanden.** Die Statistik-Stundenwerte
entsprechen jetzt dem Leistungsmittel × 1 h:
- Einspeisung 12–13 Uhr: 9,53 Wh bei einem Mittel von 9,57 W.
- Einspeisung 13–14 Uhr: 33,26 Wh bei einem Mittel von 33,22 W.
- Bezug 11–12 Uhr: 2,4226 kWh bei einem Mittel von 2423,3 W.
- Die erste Einspeisung des Tages kam um 12 Uhr nach rund 16 h auf 0 W
  und erzeugte keinen Sprung mehr.

**Energiebilanz 02.10. (korrigiert, Dr. Schmidt):**
- Bilanz: PV 4,80 + Bezug 4,25 + Akku raus 1,80 − Akku rein 2,16 −
  Einspeisung 0,12 = **Home ca. 8,6 kWh**, plausibel.
- Darin enthalten sind Waschmaschine 0,70 kWh, Trockner 0,76 kWh und
  18–20 Uhr allein 2,9 kWh.
- Die Zendure-Zähler stimmen mit den Leistungsmitteln überein: PV =
  DC-Eingang, `energy_import` = Akku-Ladung, `energy_export` = AC aus dem
  Akku. Es wird nichts doppelt gezählt.

---

## Gielz nach Core-Update 2026.10.0 deaktiviert, Patch G6 (10.10.2026)

**Was passiert ist:** Home Assistant Core wurde am 10.10. gegen 13:12 Uhr
von 2026.9 auf 2026.10.0 aktualisiert. Beim Neustart (13:13:38) lehnte HA
`automation.zendure_zensdk_gielz_global` ab und deaktivierte sie
(Zustand `unavailable`, Reparaturmeldung auf Normens Handy):
„Cannot use 'for' with a list of states at
'actions[1].choose[13].conditions[1]'“. Gielz steuerte damit von 13:11 bis
16:18 Uhr nichts (letzter Lauf 13:11:05). Schaden gering: Wetter schlecht,
Akku leer („Discharge Limit Reached“), Modus Smart Charge Only.

**Ursache:** HA 2026.10 verbietet in einer state-Bedingung `for` zusammen
mit einer Zustandsliste aus mehreren Einträgen. Betroffen ist nur der
Gielz-Upstream-Zweig „Emergency Shutdown“ (Zähler 1 Minute
`unavailable`/`unknown` → `rest_command.zendure_stop_with_everything`),
kein lokaler Patch. Ein-Element-Listen mit `for` (choose[1], [8]–[11])
akzeptiert HA weiterhin. Alle anderen Automationen luden fehlerfrei.

**Patch G6** (Dr. Schmidt: FREIGABE MIT AUFLAGEN): nur
`actions[1].choose[13].conditions[1]` ersetzt durch ein `or` aus zwei
state-Bedingungen (`unavailable` bzw. `unknown`, je `for` 1 Minute).
Gleiche Wirkung wie vorher, da `last_changed` für beide gemeinsam gilt.
Hash `dab194b233397e2c` → `67885ea906ee1618`, live 16:18:19 Uhr.

**Abnahme:** Automation „on“; Heartbeat 16:19:00 aktualisiert; erster Lauf 16:18:20 läuft fehlerfrei durch
actions[0] bis [4]; der Notaus-Zweig prüft beide Teilbedingungen
(Zähler 600 W → false); keine neue Validierungsmeldung im system_log,
keine offene Reparaturmeldung zu Gielz.

**Wichtig für später:**
- G6 muss bei jedem bewussten Neueinspielen von Gielz erneut gesetzt
  werden, solange Gielz das upstream nicht selbst korrigiert.
- Der alte Stand `dab194b233397e2c` ist **kein** Rückweg mehr: Er lädt
  unter 2026.10 nicht. Rückweg wäre nur ein Core-Downgrade.
- Vor Core-Updates künftig die Breaking Changes gegen Gielz prüfen; ein
  deaktiviertes Gielz meldet keiner der Wächter (Wächter 1 braucht Gielz-
  Zustände, Freshness-Wächter prüft nur die Zendure-Sensoren). Offener
  Punkt: Wächter für `automation.zendure_zensdk_gielz_global` ≠ „on“.

---

## Externe Bestätigung — bekannter Zendure-Fehler (nicht Gielz-Paket, nicht HA)

Websuche vom 06.09. ergab ein passendes, öffentliches GitHub-Issue im
offiziellen Zendure/Zendure-HA-Repository:
[Issue #1505](https://github.com/Zendure/Zendure-HA/issues/1505) —
"SF2400 Pro stops discharging after reaching 100% SoC — output stays at
0 W despite valid output limit". Exakt unser Symptom, betrifft explizit
den SolarFlow 2400 Pro nach Erreichen der SoC-Obergrenze. Dort
dokumentiert: 46 verworfene Entlade-Befehle in 45 Minuten, Ursache im
dortigen Fall ein sporadisch vom Gerät gemeldetes niedrigeres
`inverseMaxPower`-Limit, das die (andere) offizielle Integration
stillschweigend verworfen statt gekappt hat. Fix dafür
([PR #1506](https://github.com/Zendure/Zendure-HA/pull/1506)) am
18.07.2026 gemerged — betrifft aber die Zendure/Zendure-HA-Codebasis,
nicht das hier verwendete Gielz-zenSDK-Paket. Das zugrunde liegende
Geräteverhalten (Bypass-Lock nach SoC-Obergrenze) ist damit als
firmwareseitiger Zendure-Fehler extern bestätigt, unabhängig von unserer
HA-Konfiguration. Ein Support-Fall bei Zendure wurde entsprechend
vorbereitet.

**Offizielle Antwort des Zendure-Supports (29.09.2026).** Das Verhalten
gehört laut dem zuständigen Team zur normalen Betriebslogik:
- Erreicht der Akku den eingestellten SOC-Grenzwert, schaltet das
  System per ARM-Befehl die DC-Seite ab, um den Ladezustand zu halten.
- Erst wenn der SOC unter den Grenzwert fällt, wird DC wieder
  eingeschaltet. Bis dahin läuft nur der Bypass. Der Akku kann dann
  nicht entladen, unabhängig davon, was HA befiehlt.
- Ein Defekt liegt laut Zendure nicht vor.
- Die Entwicklung will prüfen, wie sich die Zeit zum Verlassen des
  Bypass verkürzen lässt. Einen Termin nennt Zendure nicht.

Damit ist die Ursache von Fehlerklasse 1 (Bypass-Hänger) vom Hersteller
bestätigt, und zwar als Firmware-Logik, nicht als Fehler in HA oder im
Gielz-Paket. Offen und beim Support nachgefragt:
1. Wie weit muss der SOC unter den Grenzwert fallen, bis DC wieder
   einschaltet?
2. Lässt sich die DC-Abschaltung deaktivieren?
3. Ist serverseitig noch eine HEMS-Zuordnung oder der alte 144-W-Zeitplan
   aktiv?

Folge für unsere Automatisierungen: Die 650→800-W-Anhebung bei
„Charging Limit Reached“ wirkt nur, solange DC eingeschaltet ist. Dass
das auch in dieser Phase vorkommt, zeigt der 29.09.:
- Zwischen 12:03 und 14:25 Uhr (Status „Charging Limit Reached“, SOC 95 %)
  hat das Gerät bei Lastspitzen mehrfach mit bis zu 800 W entladen: um
  12:25, 13:45 und 14:00–14:05 Uhr.
- Nach der Spitze um 13:45 fiel der SOC um 13:47 von 95 auf 94 %.

Die Anhebung ist also nicht wirkungslos. Die DC-Abschaltung laut Zendure
greift offenbar nicht die ganze Zeit.

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
- **Fassung 3 (26.09.2026):** Fehlerklasse 5 neu ergänzt — Henne-Ei-
  Deadlock zwischen Standby-Timeout und RAM-Weckbedingung, live per
  Dr.-Schmidt-Prüfung diagnostiziert und noch am selben Tag direkt in
  `automation.zendure_zensdk_gielz_global` gepatcht (dritte Wach-Bedingung
  auf Basis von `home_energy_meter_power`). Zusätzlich neue,
  eigenständige Automatisierung `zendure_ausgangsleistung_bei_vollem_akku`
  (hebt `max_discharge_power` bei vollem Akku von 650 auf 800 W an) in
  `zendure_ausgangsleistung_dynamisch.yaml` dokumentiert — ausdrücklich
  kein Fix für Fehlerklasse 5, per Live-Gegenprobe davon abgegrenzt.
- **Fassung 4 (26.09.2026, Nachmittag):** Fehlerklasse 5 um einen zweiten,
  tieferliegenden Fund ergänzt — Wettlauf zwischen dem (vormittags
  gefixten) Wach-Branch und dem Standby-Timeout-Branch im selben
  5-Sekunden-Zyklus, der gegensätzliche Befehle ans Gerät schickte. Zweiter
  Patch in `automation.zendure_zensdk_gielz_global` (Sperre im
  Standby-Branch bei akutem Entladebedarf) live bestätigt: Netzbezug fiel
  von 330 W auf 125 W, Akku ging auf "Discharging" (-727 W bzw. 432 W laut
  App). Einordnung des zeitgleich eingespielten Firmware-Updates (V2.0.2 →
  V2.0.4) ergänzt; unerklärte ~6-Minuten-Verzögerung zwischen Patch und
  sichtbarer Entladung als offene Restfrage vermerkt.
- **Fassung 5 (28.09.2026):** Fehlerklasse 5 um einen dritten Fix ergänzt —
  Entprellung der Weck- und Schlaf-Bedingung über zwei statistics-Helfer
  (`min_40s` zum Wecken, `max_5min` als Schlaf-Sperre), nach
  Dr.-Schmidt-Abnahme mit Auflagen; Hash der Gielz-Automatisierung jetzt
  `24cba37c9f8593ab`. HEMS-Mitsteuerung geprüft und nicht nachgewiesen.
  Falsche Aussage zum verschleißarmen Speichermodus (Flash statt RAM)
  berichtigt.
- **Fassung 6 (28.09.2026, Abend):** Ergebnis des Abend-Checks
  nachgetragen: Abnahme der Entprellung bestanden. Die Trägheit des Geräts
  bleibt offen (Zendure-Ticket). Das Flattern der Balkonheizung ist als
  Rückkopplung eingeordnet und behoben: Aus-Schwelle von −200 auf −50 W
  gesenkt, Zählung auf 13/14 korrigiert.
- **Fassung 7 (29.09.2026):** Offizielle Zendure-Antwort zur
  DC-Abschaltung am SOC-Grenzwert nachgetragen, dazu der Tages-Check
  29.09. (Heizung: 1 Zyklus, 650/800 sauber, kein Hänger). Neu belegt ist
  das nächtliche Weck-/Schlaf-Pendeln. Noch am selben Abend behoben:
  Die Weckbedingung ist an SOC > Geräte-Min-SOC und an einen Modus
  ungleich „Smart Charge Only“ gebunden, Hash jetzt `6a78d0e34d691367`.
- **Fassung 8 (02.10.2026):** SOC-Schutzladung startet nur noch 11–15 Uhr,
  der Stopp ist ungegatet (Hash jetzt `89023c6c06b06183`). Trapez-Fehler
  in den Netz-Energiezählern gefunden, beide Helfer auf „left“ umgestellt,
  der Tagesfehler 02.10. aus der Statistik entfernt.
- **Fassung 9 (05.10.2026):** Bypass-Hänger-Mechanismus nachgetragen
  (outputLimit muss über der PV liegen). Automatische Lösung über Quick
  Discharge live (`zendure_bypass_autoloesung.yaml`, Hash
  `992d2a48da5dc8d6`). Aussage „Quick Discharge wirkungslos“ vom 26.09.
  korrigiert. Gielz-Entladestart, Wecken und Schlafen beschrieben.
- **Fassung 10 (05.10.2026, ca. 14:30 Uhr):** Richtigstellung: `zendure_power`
  ist die Geräteabgabe ins Haus, nicht die Akkuleistung. Heizung auf
  260/50 mit Geräteabgabe-Schutz, Bypass-Autolösung nur bei Heizung aus
  (Hashes 6ad90a6d8d78dd02 und 5dedbacfb67d635f). Abnahme A4 der
  Bypass-Autolösung am selben Tag bestanden (Lauf 16:23 Uhr).
- **Fassung 11 (10.10.2026):** Core-Update 2026.10.0 deaktivierte Gielz
  („for“ mit Zustandsliste im Notaus-Zweig). Patch G6 eingespielt (Hash
  `67885ea906ee1618`), Gielz läuft wieder ab 16:18 Uhr.
