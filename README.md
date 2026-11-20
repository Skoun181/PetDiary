# 🐾 PetDiary 0.0.4

**Self-hosted · Docker · SQLite · Home Assistant**


Private, ressourcenschonende Tiergesundheitsakte für den eigenen Docker-Server. Keine Cloud, kein JavaScript-Framework, keine zusätzliche Datenbank. Deutschsprachige Weboberfläche in Mintgrün und Petrol, inspiriert von modernen Tiergesundheits-Apps.

**Status:** Version 0.0.4 – Erinnerungsübersicht für 365 Tage. Aktuelle Veröffentlichungen unter [Releases](https://github.com/Skoun181/PetDiary/releases). Ein lokales Administratorkonto pro Installation; keine Mehrbenutzerverwaltung.

[📖 Bebilderte Bedienungsanleitung](docs/USER_GUIDE.md) · [🔑 Passwort zurücksetzen](docs/PASSWORD_RESET.md) · [Änderungen](CHANGELOG.md)

![Gesundheitsakte – schematische Illustration](docs/images/tierakte.svg)

Die Illustrationen zeigen fiktive Beispieldaten, keine live aufgenommenen Screenshots.

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
- Kategorie Medikament: bereits verabreichte Einzelgabe ohne Pflicht-Uhrzeit oder Kurdauer, optional mit Menge und Einheit. Bei Termin, Untersuchung oder Medikamenteneintrag können bis zu zwölf weitere Präparate mit individuellen Daten und Plänen hinzugefügt werden. Ein Medikamentenplan benötigt Präparat, Menge, Einheit, Startdatum und 1–3660 Tage; bis zu zwölf Uhrzeiten pro Tag sind optional. Ohne Uhrzeit wird eine tägliche Gabe ohne feste Uhrzeit erzeugt. Alle Tage und Uhrzeiten wiederholen sich gleich; unterschiedliche Mengen als getrennte Pläne dokumentieren. Keine automatisch vorgeschlagene Dosierung.
- Wochenkalender im Dashboard, nach Tier filterbar, einzelne Gaben als gegeben markieren bzw. wieder öffnen. Änderungen des Plans setzen dessen bisherige Häkchen zurück.
- Bestehende Datenbanken werden beim Start um die neuen Felder und Tabellen ergänzt. Vor Update Backup erstellen.

Bei Impfungen bedeutet Gültig bis das dokumentierte Ende des Impfschutzes bzw. der Nachweisgültigkeit, Erinnern am dagegen den gewünschten Erinnerungstag. Bei Medikamenten wird eine separate Erinnerung (z. B. Nachkontrolle) nur optional angezeigt; tägliche Gaben stammen aus dem Medikamentenplan. Bereits gespeicherte Zusatzfelder bleiben sichtbar und erhalten.

### Home Assistant – Medikamentenplan

GET /api/v1/medications?days=7 liefert geplante Gaben ab dem heutigen Tag (optional start=YYYY-MM-DD; days 1–31). Nutzt denselben Bearer-Token wie die Erinnerungs-API. Antwortfelder: count (offene Gaben im Fenster), due_count (bereits fällige offene Gaben im Fenster), next (nächste offene zukünftige Gabe oder null), medications (Liste mit stabiler id, record_id, pet_id, pet, title, product, dose, unit, day, time, scheduled_at mit Zeitzonenoffset (null ohne feste Uhrzeit), entry_id (zugehöriger Akteneintrag), done), timezone. Zeitumstellung: Uhrzeiten werden als lokale Kalenderzeit gespeichert, bei mehrdeutigen Zeiten gilt die erste Stunde; Sonderfälle bitte manuell prüfen. Eine Beispiel-REST-Konfiguration liegt unter examples/home-assistant-medications.yaml. Push-Automationen sind noch nicht Bestandteil der Anwendung.

### Präparatekatalog A–Z (0.0.3)

Der Katalog enthält 607 unterschiedliche Bezeichnungen (einschließlich vorhandener Präparatevarianten). Die bereitgestellten A–Z-Listen umfassen 343 Katzen- und 468 Hundeeinträge, zusammen 540 unterschiedliche Namen. 458 davon wurden neu ergänzt. Gemeinsame Handels- und Wirkstoffnamen werden nur einmal gespeichert. Die Vorschläge der Tierart erscheinen zuerst; Hinweise zeigen die Herkunftsliste und bewahren die Quellmarkierungen für Ergänzungs-/Pflegeprodukte, Humanarzneimittel bzw. mögliche Umwidmung und zu prüfende Varianten. Alle Einträge, auch unmarkierte, sind ungeprüft. Die Listen dienen ausschließlich der nachträglichen Dokumentation, nicht der Therapieauswahl. Freitext und bereits gespeicherte Namen sowie Pläne bleiben erhalten. Keine Dosierungen oder Indikationen aus den Listen übernommen. Permethrinhaltige Hundepräparate können für Katzen lebensgefährlich sein.

## Installation

Voraussetzungen: Docker Engine, Docker Compose v2 bei Compose-Installationen, freier Port 8080. Kein externer Datenbankdienst und keine Pflicht-.env. Die Erstkonfiguration erfolgt im Browser. Der Quellcode ist öffentlich.

### A. Aus dem Git-Repository installieren (sofort verfügbar)

Mit GitHub CLI, auch bei Anmeldung über Google:

```sh
gh auth login
gh repo clone Skoun181/PetDiary -- --branch stable
cd PetDiary
docker compose up -d --build
```

Alternativ mit eingerichtetem Git-Zugriff:

```sh
git clone --branch stable https://github.com/Skoun181/PetDiary.git
cd PetDiary
docker compose up -d --build
```

Die mitgelieferte [compose.yaml](compose.yaml) baut das Image lokal. Sie verwendet einen benannten Docker-Datenträger unter /data. Für bestehende Entwicklungsinstallationen den bisherigen Projektordner und das bisherige Volume beibehalten; siehe Updates unten.

### B. Nur Docker Compose YAML (Docker Hub)

**Docker Hub:** Das Image wird automatisch gebaut. Aktuelle Tags: [Docker Hub](https://hub.docker.com/r/skoun181/petdiary/tags). Bei einem privaten Paket benötigst du einen Docker-Hub-Token mit Leserechten.

Erstelle eine Datei `docker-compose.yaml` mit dem Inhalt der [Stack-Vorlage](deploy/compose.yaml):

```yaml
services:
  petdiary:
    image: skoun181/petdiary:latest
    container_name: petdiary
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - petdiary-data:/data
    read_only: true
    tmpfs:
      - /tmp:size=64m,mode=1777
    cap_drop:
      - ALL
    security_opt:
      - no-new-privileges:true
    init: true
volumes:
  petdiary-data:
```

```sh
docker compose up -d
```

### C. Docker Pull / Docker Run (Docker Hub)

```sh
docker pull skoun181/petdiary:latest
docker run -d --name petdiary --restart unless-stopped \
  -p 8080:8080 -v petdiary-data:/data \
  --read-only --tmpfs /tmp:size=64m,mode=1777 \
  --cap-drop ALL --security-opt no-new-privileges:true --init \
  skoun181/petdiary:latest
```

Das Pull-Kommando lädt nur das Image, startet aber keinen Container. Verwende die Run-Anweisung für den Start. Nicht parallel zur Compose-Installation ausführen; Containername und Port würden kollidieren.

### D. Portainer (Docker Standalone)

**Jetzt verfügbar – Image lokal bauen:**

1. Auf dem Ziel-Docker-Host das Repository wie in A klonen. Im Projektordner `docker compose build` (noch nicht up) ausführen. Dadurch entsteht `petdiary:local`.
2. In Portainer den entsprechenden Docker-Standalone-Endpunkt wählen, **Stacks → Add stack → Web editor**.
3. Stackname `petdiary` eingeben. Inhalt der [Stack-Vorlage](deploy/compose.yaml) einfügen und die Image-Zeile auf `image: petdiary:local` ändern. Kein erzwungenes erneutes Pull aktivieren.
4. **Deploy the stack**. Im Browser Port 8080 aufrufen.

**Docker-Hub-Installation:** Schritte 2–4 mit unveränderter Stack-Vorlage; vorher ggf. die private Docker-Hub-Registry in Portainer konfigurieren.

Optional kann ein Git-Stack mit der Repository-URL, Referenz `refs/heads/stable`, privaten Git-Zugangsdaten und Compose-Pfad `compose.yaml` eingerichtet werden, sofern die jeweilige Portainer-Installation Builds aus Git-Kontext unterstützt. Der lokal gebaute Image-Stack ist die Alternative.

Offizielle Anleitung: [Portainer – Add a new stack](https://docs.portainer.io/user/docker/stacks/add).

### E. Dockhand

**Jetzt verfügbar – Git-Stack:**

1. In Dockhand unter **Settings → Git** bei einem privaten Fork die Git-Zugangsdaten hinterlegen.
2. Unter **Stacks** einen Git-Stack mit der URL `https://github.com/Skoun181/PetDiary.git` erstellen.
3. Branch `stable`, Compose-Datei `compose.yaml`, Kontextverzeichnis Repository-Wurzel einstellen.
4. **Build images on deploy** aktivieren (notwendig für build: .) und deployen. Beim Einsatz eines Remote-Agenten Build-Unterstützung prüfen.

Alternativ Methode A nur bis zum lokalen Build ausführen und einen manuellen Stack mit der Stack-Vorlage und `image: petdiary:local` anlegen.

**Docker-Hub-Installation:** Unter Stacks **Create stack**, Name `petdiary`, unveränderte Stack-YAML einfügen, ggf. Registry-Zugang konfigurieren und deployen. Keine ENV-Zugangsdaten für PetDiary erforderlich.

Offizielle Anleitung: [Dockhand – Compose stacks](https://dockhand.pro/manual/).

### F. Erststart für alle Installationsmethoden

Öffne `http://SERVER-IP:8080` (bei einem Reverse Proxy entsprechend die HTTPS-Adresse). Lege das lokale Administratorkonto an; Passwort mindestens 12 Zeichen. Anschließend ist die Ersteinrichtung gesperrt und es erscheint die reguläre Login-Seite. Unter Einstellungen verwaltest du dein Konto und den HA-API-Token.

![Dashboard – schematische Illustration](docs/images/dashboard.svg)

**Sicherheit:** Die Beispielkonfiguration veröffentlicht Port 8080 auf allen Interfaces. Der erste Besucher kann das noch nicht eingerichtete Konto beanspruchen. Initial nur in einem vertrauenswürdigen Netz starten oder auf `127.0.0.1:8080:8080` beschränken und über einen SSH-Tunnel einrichten. Danach HTTPS-Reverse-Proxy verwenden, optional `COOKIE_SECURE=1` unter environment setzen, Netzwerkzugriff einschränken. Keine ungeschützte Internetfreigabe. Die Reverse-Proxy-Weiterleitung muss den HTTP-Port 8080 erreichen.

### Bestehende Installation aus der alten ENV-Version

Vor dem Upgrade ein Backup anlegen. Wenn bereits Tierdaten vorhanden sind, aber noch kein lokales Administratorkonto existiert, die alten ADMIN_USER, ADMIN_PASSWORD und API_TOKEN einmalig als Umgebungsvariablen über ein temporäres Compose-Override explizit bereitstellen. Die frühere .env allein wird nicht in den Container übernommen. Danach das Override und die Zugangsdaten entfernen. Bei vorhandenen Tierdaten ohne Admin-Konto und ohne alte Zugangsdaten verweigert PetDiary den Start, um eine Übernahme zu verhindern.

## Passwort vergessen?

```sh
docker exec -it petdiary python /app/reset_password.py
```

Das neue Passwort zweimal verdeckt eingeben. Alle Daten und der API-Token bleiben erhalten; alte Sitzungen werden ungültig. [Ausführliche Wiederherstellungsanleitung](docs/PASSWORD_RESET.md).

## Home Assistant

API: GET /api/v1/reminders?days=365. Bearer-Token unter Einstellungen erzeugen; er wird nur direkt nach der Erstellung angezeigt. Ein neuer Token widerruft den alten. Standard ohne days: 365 Tage; days ist weiterhin frei wählbar von 0 bis 3650. Bestehende Home-Assistant-Installationen mit days=30 müssen petdiary_url in secrets.yaml auf days=365 umstellen und Home Assistant neu starten. Überfällige nicht erledigte Einträge sind immer im Ergebnis enthalten. next ist die früheste offene Erinnerung unabhängig vom Fenster. dates sind ISO-8601; days_left ist negativ bei Überfälligkeit.

```sh
curl -H "Authorization: Bearer DEIN_API_TOKEN" \
  "http://127.0.0.1:8080/api/v1/reminders?days=365"
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

Updates: Erst Backup anlegen und Volume beibehalten. Im bisherigen Projektordner einer Entwicklungsinstallation `git fetch origin && git switch stable` (wenn der Branch noch nicht lokal existiert, `git switch --track origin/stable`), dann `docker compose up -d --build`. Bei einer bestehenden Installation auf dem Release-Branch `git pull && docker compose up -d --build`. Bei einem veröffentlichten Image Versions-Tag bewusst aktualisieren, `docker compose pull && docker compose up -d`. Der Compose-Projektname bestimmt den Volume-Namen; nicht versehentlich einen zweiten Stack mit leerem Volume anlegen. Ressourcenverbrauch live mit `docker stats petdiary` messen. Keine validierten RAM-, Durchsatz- oder Stabilitätsbenchmarks vorhanden.

### Fehlersuche

```sh
docker compose ps
docker compose logs --tail=100 petdiary
curl -fsS http://127.0.0.1:8080/healthz
```

Bei Portkonflikten nur die linke Portnummer in der YAML ändern. Bei fehlenden Daten das tatsächlich gemountete Volume prüfen und kein neues Profil anlegen, bis die korrekte Datenbank wieder eingebunden ist. Bei leerer Oberfläche Browser-Cache aktualisieren. Der Healthcheck überprüft Erreichbarkeit und Datenbankzugriff, nicht sämtliche Anwendungsfunktionen.

## Entwicklung

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m unittest discover -s tests -v
```

Die Tests nutzen eine temporäre Datenbank. Sie decken Grundfunktionen ab, ersetzen keine Lasttests, visuelle Browser-Tests oder Sicherheitsprüfung.

## Veröffentlichung (Maintainer)

Dauerhafte Branches: `stable` für die veröffentlichte Version, `develop` für Entwicklung. Neue Versionen erhalten einen Git-Tag `vX.Y.Z`, ein GitHub Release und passende Docker-Hub-Tags. Siehe [Release-Anleitung](docs/RELEASE.md).

## Referenzen

- [Home Assistant RESTful Sensor](https://www.home-assistant.io/integrations/sensor.rest/)
- [EU-Heimtierausweis / Reisen mit Haustieren](https://europa.eu/youreurope/citizens/travel/carry/pets-and-other-animals/index_de.htm)
