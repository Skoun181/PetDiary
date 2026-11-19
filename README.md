# 🐾 PetDiary

Private, ressourcenschonende Tiergesundheitsakte für den eigenen Docker-Server. Keine Cloud, kein JavaScript-Framework, keine zusätzliche Datenbank. Deutschsprachige Weboberfläche in Mintgrün und Petrol, inspiriert von modernen Tiergesundheits-Apps.

**Status:** erste Entwicklungsfassung 0.1; vor produktiver Nutzung testen.

## Funktionen

- Mehrere Tiere mit eigenen Profilen und getrennten Akten
- Chronologischer Verlauf mit Kategorien für Termine, Impfungen, Untersuchungen, Befunde, Medikamente, Entwurmung, Gewicht, Ernährung, Notizen und Erinnerungen
- Einträge erstellen, bearbeiten und löschen; Tierarzt, Datum, Notizen, Präparat, Charge und Gültigkeit
- PDF- und Bildanhänge (JPEG, PNG, WebP), Inline-Vorschauseite mit optionalem Download; maximal 10 MB je Datei und fünf je Speichervorgang
- Digitaler privater Impfpass, orientiert am EU-Heimtierausweis: Halter, Tierdaten, Kennzeichnung, Ausweisnummer, ausstellende Praxis sowie Impf- und Vorsorgehistorie
- Erinnerungen für Termine und Impfungen, als erledigt markieren und wieder öffnen; Gültigkeitsende bei Impfungen als Standardfälligkeit
- Lesende REST-API für Home Assistant, Beispielkonfiguration und Dashboard-Karte
- Basic-Auth für die Oberfläche, eigener API-Token, CSRF-Schutz, persistent gespeicherte SQLite-Daten, Non-Root-Container, Healthcheck

Der digitale Impfpass ist eine private Abschrift, keine amtliche Ausstellung und kein Ersatz für den Original-Heimtierausweis. Es werden keine medizinischen Impfintervalle berechnet und keine tierärztlichen Signaturen erzeugt. Weitere amtliche Sonderabschnitte sind noch nicht vollständig abgebildet. Es gibt noch keine Tierarztterminbuchung, Push-Nachrichten, Foto-Profilbilder oder einzelne Benutzerkonten.

## Installation

Voraussetzung: Docker und Docker Compose v2. Das Repository ist privat; zum Klonen ist GitHub-Zugriff erforderlich.

```sh
git clone -b petdiary-v0.1 https://github.com/Skoun181/PetDiary.git
cd PetDiary
cp .env.example .env
chmod 600 .env
openssl rand -hex 24
openssl rand -hex 32
openssl rand -hex 32
```

Die drei Ausgaben getrennt in `.env` als ADMIN_PASSWORD, API_TOKEN und SECRET_KEY eintragen. Keine Geheimnisse committen. Das Admin-Passwort braucht mindestens 12 Zeichen, die anderen beiden mindestens 32 Zeichen.

```sh
docker compose up -d --build
docker compose ps
```

Standardmäßig ist PetDiary unter http://127.0.0.1:8080 erreichbar. Benutzername: admin (oder ADMIN_USER). Für andere Geräte bevorzugt per HTTPS-Reverse-Proxy bereitstellen und COOKIE_SECURE=1 einstellen. BIND_ADDRESS nur bei bewusstem Netzwerkzugriff ändern (z. B. LAN-IP); Firewall entsprechend setzen. Basic Auth / API-Token sind ohne TLS im Netzwerk nicht verschlüsselt. Nicht ungeschützt im Internet freigeben. Läuft der Proxy ebenfalls in Docker, kann er über ein gemeinsames Netzwerk direkt auf Port 8080 zugreifen; dazu die Compose-Konfiguration anpassen.

## Home Assistant

API: GET /api/v1/reminders?days=30. Bearer-Token aus API_TOKEN. days ist 0 bis 3650. Überfällige nicht erledigte Einträge sind immer im Ergebnis enthalten. next ist die früheste offene Erinnerung unabhängig vom Fenster. dates sind ISO-8601; days_left ist negativ bei Überfälligkeit.

```sh
curl -H "Authorization: Bearer DEIN_API_TOKEN" \
  "http://127.0.0.1:8080/api/v1/reminders?days=30"
```

Antwort (Beispieldaten):

```json
{"count":1,"overdue":0,"due_today":0,"as_of":"2026-11-19","next":{"id":1,"pet_id":1,"pet":"Milo","kind":"vaccine","title":"Tollwut","due":"2026-11-26","days_left":7},"reminders":[{"id":1,"pet_id":1,"pet":"Milo","kind":"vaccine","title":"Tollwut","due":"2026-11-26","days_left":7}]}
```

1. `examples/home-assistant.yaml` in die HA-Konfiguration übernehmen.
2. In HA secrets.yaml die erreichbare URL und den vollständigen Bearer-Header eintragen. Der Standard-Loopback-Port ist von einem anderen Host nicht erreichbar; HTTPS-URL oder bewusst freigegebenen LAN-Endpunkt verwenden.
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

Backup geschützt aufbewahren, auch .env separat sicher sichern. Für Restore Container stoppen, Datenbank in einem separaten Test-Volume wiederherstellen, Rechte UID/GID 10001 sicherstellen und erst nach Prüfung das Produktiv-Volume ersetzen. Nie `docker compose down -v` verwenden, wenn die Daten erhalten bleiben sollen.

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
