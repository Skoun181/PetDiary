# Changelog

## 0.0.4 – Jahresvorschau für Erinnerungen

- Dashboard zeigt offene Erinnerungen der nächsten 365 Tage inklusive überfälliger Einträge.
- Erinnerungs-API nutzt 365 Tage als Standard; individuelle days-Parameter (0–3650) bleiben möglich.
- Home-Assistant-Beispiele, API-Einstellungen und Anleitung aktualisiert. Bestehende HA-URLs mit days=30 müssen auf days=365 angepasst werden.
- Medikamenten-API und bestehende Daten unverändert.

## 0.0.3 – Präparatekatalog für Katzen und Hunde

- 343 Katzen- und 468 Hundeeinträge aus den bereitgestellten A–Z-Listen übernommen (540 unterschiedliche Namen, davon 458 neu).
- Insgesamt 607 unterschiedliche Grundkatalog-Bezeichnungen inklusive früherer detaillierter Präparatevarianten.
- Tierart-bezogene Priorisierung und Quellenhinweise in Haupt- und Zusatzmedikamenten; Quellmarkierungen bleiben erhalten, ohne sie in gespeicherte Produktnamen zu übernehmen.
- Keine automatische Therapieempfehlung oder Zulassungsprüfung. Freitext und bereits gespeicherte Daten bleiben unverändert.
- Regressionstests für Import, Suchreihenfolge, Markierungen, Varianten und eigene Präparate.

## 0.0.2 – Medikamentengaben

- Veröffentlichungen über dauerhafte Branches stable und develop mit automatisierten GitHub Releases und Docker Hub Tags.

- Bereits verabreichte Medikamente ohne Uhrzeit oder Kurdauer dokumentieren.
- Mehrere Medikamente pro Termin, Untersuchung oder Medikamenteneintrag; jeder zusätzliche Block hat eigene Angaben und optionalen Plan.
- Zeitlose Pläne erzeugen eine Gabe pro Tag ohne feste Uhrzeit; API liefert scheduled_at: null und time: leer.
- Bestehende Pläne und Häkchen bleiben bei technischen Migrationen erhalten. Geänderte oder gelöschte Pläne betreffen nur deren Häkchen.

## 0.0.1 – erste Vorabversion

- Lokale Browser-Ersteinrichtung, Anmeldung, Kontoeinstellungen und API-Token-Verwaltung ohne Pflicht-.env.
- Mehrere Haustiere, Profilbilder, durchsuchbare Tierarten/Rassen/Farben/Kennzeichnungsfelder mit Freitext.
- Chronologische Akten, Kategorien, digitaler privater Impfpass, PDF- und Bildvorschau.
- Lokaler Präparate-Startkatalog mit Varianten und eigenen Einträgen.
- Medikamentenpläne, tägliche Gaben, Wochenkalender, Erledigt-Status.
- Lesende Home-Assistant-API für Fälligkeiten und Medikamentengaben.
- Persistentes SQLite-Volume, Docker Compose, Backup- und Passwort-Recovery-Dokumentation.
- Illustrationen und Projekt-Handbuch.

Status: Quellcode-Vorabversion; Docker-Build, Integrationstests und Release-/Registry-Veröffentlichung noch zu verifizieren.
