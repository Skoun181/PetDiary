# 📦 PetDiary: Datenexport, Import und Serverumzug

**Status:** Ab PetDiary **0.0.5** sind ZIP-Export und -Import im offiziellen Docker-Hub-Image (`skoun181/petdiary:0.0.5` bzw. `stable`) enthalten. Ältere Installationen auf **0.0.4** haben keinen Exportknopf und benötigen den einmaligen Umweg in Abschnitt 6. Der Branch `develop` kann weiterhin separat in einem Testcontainer ausgeführt werden.

## 1. Was wird gesichert?

Die portable Datei `petdiary-backup-YYYY-MM-DD-HHMMSS.zip` enthält:

- Alle Tiere und Profilangaben (inkl. eigener Freitextfelder).
- Alle Akteneinträge, Impf- und Arzttermine, Medikamente, Einnahmepläne und Erledigt-Häkchen.
- Profilfotos sowie hochgeladene Bilder und PDF-Anhänge. Diese liegen bereits als BLOBs in SQLite; es gibt aktuell kein weiteres Upload-Verzeichnis.
- Eigene Präparate und den lokal gespeicherten Katalog.
- Ab 0.0.6: Kosteneinträge, Erstattungen und zugehörige Aktenverknüpfungen. Browserlokale Designwahl und generierte Gesundheitsakten-PDFs werden nicht gespeichert/exportiert.
- Eine `manifest.json` mit Erstellungsdatum in UTC, App-Version, Schema-Version (1 bei 0.0.5, 2 beim ersten 0.0.6-Stand, 3 mit Mehrfachverknüpfungen), Tabellen-Zählwerten und SHA-256-Prüfsumme.
- Eine mit der SQLite-Online-Backup-API erstellte konsistente Datenbankkopie.

**Nicht enthalten:** Administratorkonto, Benutzername, Passwort-Hash, API-Token/-Hash, Sitzungsschlüssel oder andere `app_settings`. Vor dem Verpacken werden diese Daten aus der kopierten SQLite-Datei entfernt; anschließend wird die Kopie per `VACUUM` bereinigt. Die eigentliche Instanz bleibt unberührt. Ein Export enthält trotzdem personenbezogene Angaben, Tier-/Halterdaten und vertrauliche Behandlungsdokumentation: Datei sicher aufbewahren.

**Beim Import** bleiben das bestehende Administratorkonto und der API-Token **der Zielinstanz** erhalten. Beim Wechsel auf einen neuen Server zunächst in der neuen Instanz ein eigenes Admin-Konto anlegen, dann die ZIP-Datei importieren. Danach den Home-Assistant-Endpunkt gegebenenfalls an die neue Server-IP anpassen; der Quell-Token wird nicht übertragen.

## 2. Export direkt im Browser (ab 0.0.5)

1. In PetDiary einloggen und **Einstellungen → Daten sichern und umziehen** öffnen.
2. Unter **Daten exportieren** das aktuelle Passwort eingeben.
3. **ZIP-Backup herunterladen** auswählen. Während des Downloads erscheint ein Ladezustand, anschließend eine Rückmeldung.
4. ZIP auf einem geschützten externen Datenträger sichern. Nicht in öffentlichen Git-Repositories oder ungeschützten Clouds ablegen.
5. Falls Dockhand beim Herunterladen ein Archiv mit der Endung `.zip.tar` erzeugt, **nur die äußere TAR-Hülle entpacken**. Die innere ZIP-Datei unverändert importieren.

Die ZIP-Datei muss nicht manuell entpackt werden. Große Installationen brauchen genügend freien Platz auf dem gemounteten `/data`-Volume, da während des Exports eine temporäre Datenbankkopie entsteht. Maximal 256 MiB ZIP und 1 GiB entpackte SQLite-Datenbank.

## 3. Import im Browser

1. Die neue Instanz starten, im Browser **ein lokales Admin-Konto erstellen** und einloggen. Das Passwort dieses Kontos gilt nach dem Import weiterhin.
2. **Einstellungen → Daten sichern und umziehen → Backup importieren** öffnen.
3. Die zuvor exportierte ZIP wählen, Ziel-Adminpasswort eingeben, `ERSETZEN` eintippen und die Warnung bestätigen.
4. **Backup importieren und Daten ersetzen** wählen. PetDiary prüft Archivstruktur, Größenlimits, Prüfsumme, SQLite-Integrität, erlaubte Tabellen, Verknüpfungen und Schema-Version **vor** dem Import.
5. Unmittelbar vor der Datenübernahme erstellt PetDiary intern ein vollständiges Sicherheitsbackup unter `/data/.petdiary-safety-backups/pre-import-....sqlite3`. **Achtung:** Diese lokale Notfallkopie enthält das alte Ziel-Administratorkonto und dessen Token-Hash. Der Ordner wird mit eingeschränkten Dateirechten angelegt; das gesamte Volume muss geschützt bleiben.
6. Der Import ersetzt Tier- und Gesundheitsdaten in einer einzigen SQLite-Transaktion. Bei Fehlern werden die Änderungen zurückgerollt; es gibt keinen halb importierten Zustand. Die Ziel-Zugangsdaten bleiben erhalten.
7. Die Erfolgsmeldung enthält die Zahl der Tiere, Akteneinträge, Fotos und Anhänge sowie den Namen der Sicherheitskopie. Im Anschluss Startseite, Tierprofile, Impfpass, Bilder, Medikamentenkalender und API prüfen. Kein Neustart nötig.

**Wichtig:** Der Import ersetzt die vorhandenen **Anwendungsdaten der Zielinstanz**, nicht nur fehlende Datensätze. Vor dem Überschreiben wichtige Ziel-Daten selbst exportieren. Der normale Import akzeptiert ausschließlich das von PetDiary erzeugte portable ZIP-Format, **keine** Roh-SQLite-Datei und **keine** mit `docker export` erstellte Containerdatei.

## 4. Unterschied: Image, Stack und Daten

| Bestandteil | Speicherort | Umzug |
| --- | --- | --- |
| Anwendungscode | GitHub (`stable`, `develop`) | Git-Klon/Checkout oder Git-Stack |
| Docker-Image | Docker Hub `skoun181/petdiary:stable` bzw. lokaler Build aus `develop` | Neu herunterladen bzw. bauen |
| Konfiguration | Compose-Datei, Port-/Proxy-/Firewall-Regeln, ggf. Umgebungsvariablen | Separat übernehmen und anpassen |
| Persistente Tierdaten | Benanntes Docker-Volume, im Container `/data/petdiary.sqlite3` | Browser-ZIP exportieren/importieren |
| Zugangsdaten und API-Token | Zielinstanz in SQLite (nicht im portablen Export) | Auf neuer Instanz neu anlegen/konfigurieren |

`docker export` und ein Image-Pull enthalten **keine** Daten aus Docker-Volumes. `docker compose down -v` oder `docker volume rm` können deine Tierakte endgültig löschen – nicht verwenden.

## 5. Optional: develop parallel zu stable testen

**Die Export-/Importfunktion ist jetzt ab 0.0.5 als Docker-Hub-Release verfügbar.** Dieser Abschnitt zeigt eine zusätzliche, vollständig isolierte `develop`-Testinstanz für zukünftige Änderungen. Die `develop`-Builds werden weiterhin nicht automatisch auf Docker Hub veröffentlicht.

**In Dockhand (Git-Stack):**

1. Den bestehenden PetDiary-Stable-Stack mit `skoun181/petdiary:stable` unverändert weiterlaufen lassen (Hostport 8080 und altes Volume).
2. In Dockhand einen **neuen Git-Stack** anlegen, z. B. `petdiary-develop`.
3. Git-Repository: `https://github.com/Skoun181/PetDiary.git`, Branch **`develop`**, Compose-Datei **`compose.develop.yaml`** aus der Repository-Wurzel. Den Build aus Git/Dockerfile beim Deploy aktivieren.
4. Deployen. Die Entwicklungsinstanz bekommt den Container `petdiary-develop`, Hostport **8081** und das ausdrücklich getrennte Volume `petdiary-develop-data`.
5. `http://DEIN-SERVER:8081` öffnen, dort ein eigenes Admin-Konto einrichten. Es ist zunächst **eine leere Testinstanz**.
6. Eine portable Sicherung über die Exportfunktion von Stable (ab 0.0.5) importieren; bei alten 0.0.4-Installationen Abschnitt 6 befolgen. Änderungen in der Testinstanz verändern **nicht** die alten Daten.
7. Export und Rückimport sowie Fotos, Anhänge, Termine und Medikamente prüfen. Die Originalinstanz auf Port 8080 läuft unverändert weiter.

Alternativ über eine Docker-Konsole auf einem Testhost:

```sh
git clone --branch develop https://github.com/Skoun181/PetDiary.git
cd PetDiary
docker compose -f compose.develop.yaml up -d --build
```

Für eine weitere Testinstanz die festen Namen und den Hostport jeweils anpassen, sonst entstehen Konflikte.

## 6. Einmaliger Export aus einer alten 0.0.4-Installation

Version 0.0.4 bietet noch keinen Downloadknopf. Um die Daten in die neue, isolierte Testinstanz zu übernehmen, kannst du zuerst ein **konsistentes SQLite-Backup** aus dem laufenden Container erzeugen und anschließend mit dem neuen, rein Python-basierten Werkzeug in eine portable, von Zugangsdaten bereinigte ZIP-Datei umwandeln.

Befehle auf einem Rechner mit Docker-Zugriff auf den alten Host (z. B. per Docker CLI/SSH):

```sh
# 1. Online-Snapshot der alten SQLite-Datenbank im bestehenden Volume:
docker exec petdiary python -c 'import sqlite3; s=sqlite3.connect("/data/petdiary.sqlite3"); d=sqlite3.connect("/data/migration-source.sqlite3"); s.backup(d); d.close(); s.close()'

# 2. Snapshot herunterladen (enthält NOCH Passwort-/Token-Hashes!):
docker cp petdiary:/data/migration-source.sqlite3 ./migration-source.sqlite3

# 3. Das neue Portable-Backup-Skript aus develop beziehen:
curl -fsSL https://raw.githubusercontent.com/Skoun181/PetDiary/develop/backups.py -o backups.py

# 4. Ein ZIP ohne Admin-Konto, Schlüssel und API-Token erzeugen:
python3 backups.py export --database ./migration-source.sqlite3 --output-dir . --app-version 0.0.4

# 5. Temporären Snapshot im Container entfernen:
docker exec petdiary rm /data/migration-source.sqlite3
```

Das Skript benötigt nur Python 3 und dessen Standardbibliothek. Jetzt liegt eine `petdiary-backup-....zip` bereit, die du über **`http://DEIN-SERVER:8081 → Einstellungen → Daten sichern und umziehen`** importieren kannst.

**Sicherheits-Hinweis:** Die zwischenzeitlich gespeicherte Rohdatei `migration-source.sqlite3` enthält ursprüngliche Anmeldedaten, Session-Secret und Token-Hashes. Schütze sie besonders gut und entferne sie nach erfolgreichem ZIP-Export aus dem unverschlüsselten Arbeitsverzeichnis. Auf SSDs ist Dateilöschen nicht zwangsläufig ein sicheres Überschreiben.

Falls nur die Dockhand-Weboberfläche verfügbar ist und du keinen Docker-Host-Zugriff hast, nutze die Dockhand-Container-Konsole zum Erstellen des Snapshots; für dessen Übertragung auf deinen Rechner kann zusätzlich ein Dateimanager oder Docker-Zugriff notwendig sein. **Nicht** ersatzweise denselben laufenden SQLite-Datenträger in zwei PetDiary-Containern gleichzeitig beschreibbar einhängen.

## 7. Auf einen neuen Server / Rechner umziehen

1. Quellinstallation sichern – bei 0.0.4 über Abschnitt 6, ab 0.0.5 direkt über **Daten exportieren**.
2. ZIP auf den neuen Rechner übertragen (z. B. USB oder sichere Dateiübertragung).
3. Docker Engine/Compose installieren oder in Dockhand einen neuen PetDiary-Stack mit dem veröffentlichten Image **`skoun181/petdiary:0.0.5`** anlegen. Nur für experimentelle Entwicklung `develop` und `compose.develop.yaml` bauen.
4. **Neues leeres Volume** unter `/data` anlegen, Container starten, Browser-Ersteinrichtung mit neuen Zugangsdaten durchführen.
5. ZIP über das neue Browserformular importieren, anschließend alle Daten und Dateien prüfen.
6. Portfreigabe/Reverse Proxy und Home-Assistant-REST-URL bei Bedarf auf die neue IP/Port ändern. Einen neuen API-Token nur erzeugen, wenn noch keiner in der Zielinstanz existiert.
7. Alte Installation erst nach erfolgreicher Prüfung außer Betrieb nehmen; das alte Volume und externe Backups zunächst behalten.

### Docker Compose für einen optionalen separaten Entwicklungscontainer

[compose.develop.yaml](../compose.develop.yaml) verwendet `build: .`, Hostport 8081 und `petdiary-develop-data:/data`. Der `stable`-Stack auf Hostport 8080 bleibt unberührt. Wenn du eine produktive Installation später auf develop umstellen willst, **niemals unbemerkt auf ein neues leeres Volume wechseln**.

### Fortgeschritten: Develop mit dem bisherigen Volume statt isolierter Testkopie

Nur mit zusätzlichem **externen Backup** der Originaldaten. Zuerst `stable` stoppen (Volume **nicht** löschen), den tatsächlichen Namen des bisherigen Volumes aus **Dockhand → Container → Mounts** oder über den Befehl ermitteln:

```sh
docker inspect petdiary --format '{{range .Mounts}}{{if eq .Destination "/data"}}{{.Name}}{{end}}{{end}}'
```

In einer Git-basierten `develop`-Compose-Datei das alte Volume dann ausdrücklich als **external** einbinden, z. B.:

```yaml
name: petdiary-develop-live
services:
  petdiary:
    build: .
    image: petdiary:develop-local
    container_name: petdiary-develop
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - existing-petdiary-data:/data
    read_only: true
    tmpfs:
      - /tmp:size=64m,mode=1777
    cap_drop: [ALL]
    security_opt: [no-new-privileges:true]
    init: true
volumes:
  existing-petdiary-data:
    external: true
    name: TATSÄCHLICHER_EXISTIERENDER_VOLUME_NAME
```

**Den Platzhalter vor dem Deploy ersetzen.** Stelle sicher, dass nicht gleichzeitig die alte Instanz mit Schreibzugriff auf diesem Volume läuft und Port 8080 nicht doppelt belegt ist. Der neue Code verwendet das bisherige Volume direkt – du solltest damit nicht experimentieren, wenn du nur die neuen Funktionen testen möchtest. Der sichere Weg ist ein zweiter Container mit getrennter Datenkopie.

## 8. Interne Sicherheitskopie nach einem Import wiederherstellen (Notfall)

Die vor jedem Import automatisch angelegte `/data/.petdiary-safety-backups/pre-import-....sqlite3` ist **keine portable ZIP-Datei**, sondern eine vollständige Momentaufnahme der **Zielinstanz inklusive deren Zugangsdaten**.

Für eine manuelle Wiederherstellung muss der betreffende PetDiary-Container gestoppt sein. Beispiel für das isolierte Entwicklungsvolume (DATEINAME ersetzen), nur wenn du bewusst vollständig auf den Zustand vor dem Import zurückgehen willst:

```sh
docker stop petdiary-develop
docker run --rm --user 10001:10001 -v petdiary-develop-data:/data python:3.12-slim \
  python -c 'import sqlite3; s=sqlite3.connect("/data/.petdiary-safety-backups/DATEINAME.sqlite3"); d=sqlite3.connect("/data/petdiary.sqlite3"); s.backup(d); d.close(); s.close()'
docker start petdiary-develop
```

Danach `/healthz`, Anmeldung und alle Tierakten prüfen. PetDiary bewahrt automatisch maximal fünf solcher internen Sicherheitskopien auf. Sie enthalten sensible Daten; nach erfolgreich geprüftem Import und zusätzlicher externer Sicherung können nicht mehr benötigte Kopien manuell gelöscht werden.

## 9. Technische Grenzen und Sicherheit

- ZIP: maximal 256 MiB komprimiert, SQLite maximal 1 GiB entpackt; Dateinamen sind auf die zwei erwarteten Archivmitglieder beschränkt, ZIP-Symlinks, außergewöhnlich starke Komprimierung und verschlüsselte Einträge werden abgewiesen.
- Serverseitige Validierung: Schema-Version 1, 2 bzw. 3, App-Version-Metadaten, SHA-256, CRC beim Lesen, SQLite-`integrity_check`, Fremdschlüssel und Tabellenstruktur. Freitextinhalte werden beim Import nicht als SQL ausgeführt.
- Die Datenübernahme verwendet eine SQLite-Transaktion. Wenn sie fehlschlägt, bleibt die bisherige Akte erhalten.
- Export und Import verlangen eine gültige Sitzung, CSRF-Schutz und erneute Eingabe des Adminpassworts. Import zusätzlich eine ausdrückliche Ersetzungsbestätigung.
- Metadaten und Fehler werden ohne Passwörter, Tokens oder Datei-Inhalte geloggt; detaillierte Serverfehler erscheinen nur in den Logs.
- Alle persistenten Daten einschließlich Uploads liegen in `/data/petdiary.sqlite3`. Das normale Compose bindet ein benanntes Volume ein. Der Container selbst ist austauschbar.
- **Kein Merge nach `stable`**, solange dieser Entwicklungsstand nicht vollständig getestet und freigegeben wurde.


## Kompatibilität ab 0.0.6

Schema-1-ZIPs aus Version 0.0.5 lassen sich weiterhin importieren. Weil sie keine Kosteneinträge enthalten, wird die Kostenliste beim Ersetzen der Anwendungsdaten geleert. Schema-2-ZIPs enthalten Kosten und Einzelverknüpfungen; sie werden in Schema 3 migriert. Schema-3-ZIPs sichern alle Mehrfachverknüpfungen und sind nicht für ältere Versionen geeignet. Vor einem Zurückwechseln auf einen älteren Softwarestand ein separates Datenvolume verwenden.
