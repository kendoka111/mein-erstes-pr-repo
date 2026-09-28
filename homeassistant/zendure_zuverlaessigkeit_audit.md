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
Leistungswert blieb während des Hängers wirkungslos (Akku weiter 0 W) —
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
