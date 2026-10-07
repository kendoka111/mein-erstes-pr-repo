# Verschlankung Energie-System – Plan (Stand 07.10.2026)

Normen: "Wir müssen das Ganze wieder verschlanken und vereinfachen."
Sicherungspunkt vorher: `live_stand_2026-10-07/` (HA-Backup `9c2f0f83`,
Commit `3f0a8e2`).

Dr. Schmidt (07.10.): **FREIGABE MIT AUFLAGEN.** Normen: "Ja", erst
Sicherungspunkt.

## Schritte

| # | Schritt | Status |
|---|---|---|
| 0 | Sicherungspunkt (Backup, Live-Kopie, Commit 3f0a8e2) | erledigt 07.10. |
| 1 | Gielz-Startformel G5 (PV addieren bei "Charging Limit Reached" und Heizung aus, nur `actions[2].choose[0]`) + Bypass-Autolösung v2 (Timeout 15 Min bis "Normal Operation"). Auflage A4: nur einspielen, wenn Merker aus. | offen |
| 2 | Heizung: `input_boolean.balkonheizung_automatik_aktiv` streichen. Überschuss-Automation prüft `input_select.balkonheizung_modus` = "Automatisch"; Trigger `automatik_toggle` ersatzlos weg; Moduswahl schaltet nur noch bei Aus/An; Helfer zuletzt löschen; alle drei Modi testen. Vor dem Beobachtungsfenster von Schritt 1. | offen |
| 3 | Wächter 4 ("Gerät lehnt Befehl ab"): kann nie auslösen (system_log_event wird nicht gefeuert). Empfehlung Dr. Schmidt: löschen und im Audit vermerken. | offen, Normens Entscheidung |
| 4 | Doppelten Sensor `sensor.einspeisung_watt` (= `sensor.netz_einspeisung_watt`) entfernen, nach Prüfung Energie-Dashboard und YAML-Automationen. | offen |
| 5 | HomeWizard-Abruf ("unknown/api/v1/data") dauerhaft abstellen – Normens Wunsch 07.10. | in Klärung |
| 6 | Doku: `SYSTEMSTAND.md` (1–2 Seiten), `gielz_lokale_patches.md` (G1–G5 + Wiedereinspielen + Hash-Prüfung), gepatchtes Gielz-YAML im Repo, YAML-Köpfe kürzen (nicht offensichtliche Regeln bleiben in 1–2 Sätzen), Repo exakt auf Live-Stand. | offen |
| 7 | Bypass-Autolösung + Merker löschen, sobald an **mindestens 5 Tagen** mit "Charging Limit Reached", Bedarf und Heizung aus kein Lösungslauf nötig war und mindestens ein Gielz-Entladestart am SOC-Limit ohne Moduswechsel belegt ist. Beleg über die Historie des Merkers (Tag 7 und 14). Erst deaktivieren, Merker aus und Modus ≠ Quick Discharge prüfen, dann löschen. Verweise in Heizung und Audit anpassen. | offen |

Bewusst **nicht**:
- Wächter zusammenlegen (Dr. Schmidt: Meldungen könnten verloren gehen).
- Ladevorrang und 650/800 in Gielz einbauen.
- Gielz-Patches G1–G3 und die statistics-Helfer zurückbauen.

Ergebnis nach allen Schritten: 10 → 8 eigene Automationen, 3 Helfer weniger.
