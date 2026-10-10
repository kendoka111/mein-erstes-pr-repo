# Sicherungspunkt 07.10.2026 (vor der Verschlankung)

Hierher kommen wir zurück, falls die Verschlankung etwas verschlechtert.

- **HA-Vollbackup:** "Sicherungspunkt vor Verschlankung 2026-10-07",
  Backup-ID `9c2f0f83`, 07.10.2026 19:24 Uhr, ca. 77 MB (ohne Datenbank).
  Wiederherstellen startet HA neu und setzt **alles** seit dem Zeitpunkt
  zurück. Nur als letzter Ausweg und nur nach Rückfrage.
- **Git-Stand:** Commit `3f0a8e2` auf Branch claude/ha-battery-charge-strategy-c4ybdd
- **Live-Konfiguration:** Die 11 YAML-Dateien in diesem Ordner sind exakte
  Kopien der Live-Automationen. Jede ergibt den angegebenen `config_hash`
  (sha256 über das sortierte, kompakte JSON, erste 16 Zeichen).
  Eine einzelne Automation lässt sich damit gezielt zurücksetzen, ohne das
  ganze Backup einzuspielen.

| Datei | config_hash |
|---|---|
| zendure_zensdk_gielz_global.yaml (Gielz mit Patches G1–G4) | 89023c6c06b06183 |
| zendure_ladevorrang_hysterese_40_18.yaml | de58a573927a3f65 |
| zendure_ausgangsleistung_bei_vollem_akku_anheben.yaml | d0e36f1e21834513 |
| zendure_bypass_hanger_automatisch_losen.yaml | 5dedbacfb67d635f |
| zendure_wachter_akku_entladt_nicht_trotz_bedarf.yaml | bba7d0f4a36d191e |
| zendure_wachter_pv_export_status_nicht_lesbar.yaml | 8ea5c5f265753c5f |
| zendure_wachter_sensoren_liefern_keine_frischen_werte_mehr.yaml | 97f4bb24f4f01830 |
| zendure_wachter_gerat_lehnt_befehl_ab_4xx.yaml | ac4fdb46c9bce62c |
| balkonheizung_pv_uberschuss.yaml | 6ad90a6d8d78dd02 |
| balkonheizung_moduswahl_aus_an_automatisch.yaml | 101834b6f2b95701 |
| stromzahler_ablesung_ubernehmen.yaml | 52a010850768dd6b |

Der Verschlankungsplan steht in `../VERSCHLANKUNG_PLAN.md`.
