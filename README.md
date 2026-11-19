# 🐾 PetDiary

Private, ressourcenschonende Tiergesundheitsakte für den eigenen Docker-Server. Keine Cloud, kein JavaScript-Framework, keine zusätzliche Datenbank. Deutschsprachige Weboberfläche in Mintgrün und Petrol, inspiriert von modernen Tiergesundheits-Apps.

**Status:** erste Entwicklungsfassung 0.1; vor produktiver Nutzung testen. Ein lokales Administratorkonto pro Installation; keine Mehrbenutzerverwaltung.

## Funktionen

- Mehrere Tiere mit eigenen Profilen und getrennten Akten
- Chronologischer Verlauf mit Kategorien für Termine, Impfungen, Untersuchungen, Befunde, Medikamente, Entwurmung, Gewicht, Ernährung, Notizen und Erinnerungen
- Einträge erstellen, bearbeiten und löschen; Tierarzt, Datum, Notizen, Präparat, Charge und Gültigkeit
- PDF- und Bildanhänge (JPEG, PNG, WebP), Inline-Vorschauseite mit optionalem Download; maximal 10 MB je Datei und fünf je Speichervorgang
- Digitaler privater Impfpass, orientiert am EU-Heimtierausweis: Halter, Tierdaten, Kennzeichnung, Ausweisnummer, ausstellende Praxis sowie Impf- und Vorsorgehistorie
- Erinnerungen für Termine und Impfungen, als erledigt markieren und wieder öffnen; Gültigkeitsende bei Impfungen als Standardfälligkeit
- Lesende REST-API für Home Assistant, Beispielkonfiguration und Dashboard-Karte
- Browser-Ersteinrichtung, lokale Anmeldung, eigener API-Token, CSRF-Schutz, persistent gespeicherte SQLite-Daten, Non-Root-Container, Healthcheck

Der digitale Impfpass ist eine private Abschrift, keine amtliche Ausstellung und kein Ersatz für den Original-Heimtierausweis. Es werden keine medizinischen Impfintervalle berechnet und keine tierärztlichen Signaturen erzeugt. Weitere amtliche Sonderabschnitte sind noch nicht vollständig abgebildet. Es gibt noch keine Tierarztterminbuchung, Push-Nachrichten, einzelne Benutzerkonten.

## Tierprofile und Medikamentenkalender

- Eigene gestaltete, suchbare Vorschlagslisten mit Freitext: Tierart, passende Rassen, Geschlecht, Fellfarbe, Chip- und Tätowierungsposition; eigenes Merkmale-Feld.
- Eigene Profilbilder (JPEG, PNG oder WebP, maximal 5 MB), lokal in SQLite gespeichert.
- Lokaler Präparate-Startkatalog (keine vollständige oder amtlich abgeglichene Arzneimitteldatenbank). Eigene Präparate werden bei gespeichertem Eintrag zur Vorschlagsliste hinzugefügt. Geprüfte Varianten unter anderem für Milpro, Milbemax, Apoquel und Metacam ergänzen den Startkatalog. Die genaue eigene Präparatbezeichnung kann separat eingegeben werden; sie ersetzt beim Speichern die Auswahl. Name allein sagt nichts über Zulassung, Eignung oder Dosierung aus. Offizielle Recherche: [EU-Produktdatenbank](https://medicines.health.europa.eu/veterinary/de).
- Kategorie Medikament: Präparat, Menge je Gabe, Einheit, Startdatum, Anzahl Tage (1–3660), bis zu zwölf Uhrzeiten pro Tag. Alle Tage und Uhrzeiten wiederholen sich gleich; unterschiedliche Mengen als getrennte Pläne dokumentieren. Keine automatisch vorgeschlagene Dosierung.
- Wochenkalender im Dashboard, nach Tier filterbar, einzelne Gaben als gegeben markieren bzw. wieder öffnen. Änderungen des Plans setzen dessen bisherige Häkchen zurück.
- Bestehende Datenbanken werden beim Start um die neuen Felder und Tabellen ergänzt. Vor Update Backup erstellen.

Bei Impfungen bedeutet Gültig bis das dokumentierte Ende des Impfschutzes bzw. der Nachweisgültigkeit, Erinnern am dagegen den gewünschten Erinnerungstag. Bei Medikamenten wird eine separate Erinnerung (z. B. Nachkontrolle) nur optional angezeigt; tägliche Gaben stammen aus dem Medikamentenplan. Bereits gespeicherte Zusatzfelder bleiben sichtbar und erhalten.

### Home Assistant – Medikamentenplan

GET /api/v1/medications?days=7 liefert geplante Gaben ab dem heutigen Tag (optional start=YYYY-MM-DD; days 1–31). Nutzt denselben Bearer-Token wie die Erinnerungs-API. Antwortfelder: count (offene Gaben im Fenster), due_count (bereits fällige offene Gaben im Fenster), next (nächste offene zukünftige Gabe oder null), medications (Liste mit stabiler id, record_id, pet_id, pet, title, product, dose, unit, day, time, scheduled_at mit Zeitzonenoffset, done), timezone. Zeitumstellung: Uhrzeiten werden als lokale Kalenderzeit gespeichert, bei mehrdeutigen Zeiten gilt die erste Stunde; Sonderfälle bitte manuell prüfen. Eine Beispiel-REST-Konfiguration liegt unter examples/home-assistant-medications.yaml. Push-Automationen sind noch nicht Bestandteil der Anwendung.

## Installation

Voraussetzung: Docker und Docker Compose v2. Das Repository ist privat; zum Klonen ist GitHub-Zugriff erforderlich.

```sh
git clone -b petdiary-v0.1 https://github.com/Skoun181/PetDiary.git
cd PetDiary
docker compose up -d --build
```

Öffne http://SERVER-IP:8080 im Browser. Beim ersten Aufruf legst du ein lokales Administratorkonto an (Passwort mindestens 12 Zeichen). Es gibt keine Standard-Zugangsdaten und keine benötigte .env. Das Session-Geheimnis wird automatisch erzeugt und zusammen mit dem Passwort-Hash im persistenten Datenvolume gespeichert. Danach ist die Ersteinrichtung gesperrt und du meldest dich über die normale Login-Seite an. Unter Einstellungen kannst du Kontodaten ändern, dich abmelden und einen Home-Assistant-API-Token erzeugen oder widerrufen.

**Sicherheit:** Der Compose-Port ist standardmäßig im Netzwerk erreichbar. Der erste Besucher kann das noch nicht eingerichtete Konto beanspruchen. Führe die Ersteinrichtung in einem vertrauenswürdigen Netzwerk durch; bei Bedarf Port zunächst auf 127.0.0.1:8080:8080 beschränken und per SSH-Tunnel einrichten. Für dauerhaften Netzwerkzugriff HTTPS-Reverse-Proxy verwenden und optional COOKIE_SECURE=1 als Compose-Umgebungsvariable setzen; keine ungeschützte Internetfreigabe.

### Bereits vorhandene Installation der ENV-Version

Vor dem Upgrade ein Backup anlegen. Wenn bereits Tierdaten vorhanden sind, müssen beim ersten Start der neuen Version die bisherigen ADMIN_USER, ADMIN_PASSWORD und API_TOKEN einmalig als Umgebungsvariablen über ein temporäres Compose-Override explizit bereitgestellt werden. Die alte .env allein wird nicht automatisch an den Container übergeben. Die Zugangsdaten werden beim ersten Start als Hashes übernommen und bestehende Sitzungen verworfen; danach das Override und die ENV-Zugangsdaten entfernen. Ohne Admin-Konto und mit bestehenden Tierdaten verweigert die Anwendung den Start, damit niemand die bestehende Akte per Ersteinrichtung übernehmen kann.

### Geplante Installation per fertigem Image

Sobald ein Docker-Image in einer Registry veröffentlicht ist, entfällt auch das Klonen und Bauen. Die Compose-Datei benötigt dann nur Image, Port, persistentes Volume und Restart-Policy. Ein öffentlich zugängliches Registry-Image wurde noch nicht veröffentlicht.

## Home Assistant

API: GET /api/v1/reminders?days=30. Bearer-Token unter Einstellungen erzeugen; er wird nur direkt nach der Erstellung angezeigt. Ein neuer Token widerruft den alten. days ist 0 bis 3650. Überfällige nicht erledigte Einträge sind immer im Ergebnis enthalten. next ist die früheste offene Erinnerung unabhängig vom Fenster. dates sind ISO-8601; days_left ist negativ bei Überfälligkeit.

```sh
curl -H "Authorization: Bearer DEIN_API_TOKEN" \
  "http://127.0.0.1:8080/api/v1/reminders?days=30"
```

Antwort (Beispieldaten):

```json
{"count":1,"overdue":0,"due_today":0,"as_of":"2026-11-19","next":{"id":1,"pet_id":1,"pet":"Milo","kind":"vaccine","title":"Tollwut","due":"2026-11-26","days_left":7},"reminders":[{"id":1,"pet_id":1,"pet":"Milo","kind":"vaccine","title":"Tollwut","due":"2026-11-26","days_left":7}]}
```

1. `examples/home-assistant.yaml` in die HA-Konfiguration übernehmen.
2. In HA secrets.yaml die erreichbare URL und den vollständigen Bearer-Header eintragen. HTTPS-URL oder bewusst freigegebenen LAN-Endpunkt verwenden.
3. Konfiguration prüfen und HA neu laden bzw. neu starten.
4. `examples/home-assistant-card.yaml` als manuelle Karte hinzufügen. Entity-ID gegebenenfalls anpassen.

Home Assistant kann die Sensoren für eigene Automationen nutzen. PetDiary selbst verschickt keine Nachrichten. Fälligkeiten sind Kalendertage in TZ, standardmäßig Europe/Berlin.

## Architektur, Backup, Betrieb

Ein Gunicorn-Worker mit zwei Threads, Flask, serverseitigem HTML und CSS, SQLite (WAL und Fremdschlüssel). Alle Daten inklusive Anhänge befinden sich in `/data/petdiary.sqlite3` im benannten Docker-Volume. Kein externer Datenbank- oder Cache-Dienst. Attachments werden als BLOB gespeichert, damit Datenbank-Backups konsistent bleiben; große Uploads erzeugen kurzfristig zusätzlichen RAM-Bedarf.

Konsistentes Online-Backup mittels SQLite Backup-API (nicht die laufende DB-Datei einfach kopieren):

```sh
docker compose exec -T petdiary python -c 'import sqlite3; s=sqlite3.connect("/data/petdiary.sqlite3"); d=sqlite3.connect("/data/backup.sqlite3"); s.backup(d); d.close(); s.close()'
docker compose cp petdiary:/data/backup.sqlite3 ./petdiary-backup.sqlite3
docker compose exec -T petdiary rm /data/backup.sqlite3
```

Backup geschützt aufbewahren: Es enthält auch die Anmelde-Hashes und das Session-Geheimnis. Für Restore Container stoppen, Datenbank in einem separaten Test-Volume wiederherstellen, Rechte UID/GID 10001 sicherstellen und erst nach Prüfung das Produktiv-Volume ersetzen. Nie `docker compose down -v` verwenden, wenn die Daten erhalten bleiben sollen.

Updates (nach Backup): `git pull && docker compose up -d --build`. Ressourcenverbrauch live mit `docker stats petdiary` messen. Keine validierten RAM-, Durchsatz- oder Stabilitätsbenchmarks vorhanden.

## Entwicklung

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m unittest discover -s tests -v
```

Die Tests nutzen eine temporäre Datenbank. Sie decken Grundfunktionen ab, ersetzen keine Lasttests, visuelle Browser-Tests oder Sicherheitsprüfung.

## Referenzen

- [Home Assistant RESTful Sensor](https://www.home-assistant.io/integrations/sensor.rest/)
- [EU-Heimtierausweis / Reisen mit Haustieren](https://europa.eu/youreurope/citizens/travel/carry/pets-and-other-animals/index_de.htm)
