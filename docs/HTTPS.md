# HTTPS mit eigenem Zertifikat (Develop 0.0.7)

PetDiary unterstützt den Upload einer bestehenden PEM-Zertifikatskette plus privatem Schlüssel unter **Einstellungen → HTTPS / TLS-Zertifikat**. **Die Web-App selbst bleibt intern auf HTTP**. Nur der optionale Caddy-Reverse-Proxy übernimmt TLS. Der Upload **allein** schaltet HTTPS nicht ein.

**Falls du bereits Synology Reverse Proxy, Nginx Proxy Manager oder Traefik verwendest:** Hinterlege dein Wildcard-Zertifikat vorzugsweise dort. Dann musst du den privaten Schlüssel nicht zusätzlich bei PetDiary hochladen. Die neue Uploadfunktion ist für den mitgelieferten Caddy-Companion gedacht.

## 1. Voraussetzungen

- Ein öffentlich vertrauenswürdiges Zertifikat für den DNS-Namen der App, z. B. `petdiary.meinedomain.de`. Ein Wildcard `*.meinedomain.de` deckt diesen Host ab, aber nicht `meinedomain.de` oder `a.b.meinedomain.de`.
- `fullchain.pem`: Serverzertifikat **zuerst**, danach Zwischenzertifikate, alles im PEM-Format.
- `privkey.pem`: genau dazugehöriger **unverschlüsselter** privater PEM-Schlüssel. Ein PFX/P12 lässt sich nicht direkt hochladen; es muss vorher an einem geschützten Ort in PEM umgewandelt werden.
- Ein DNS-Eintrag zur richtigen Server-IP, ein freier HTTPS-Port sowie passende Router-/Firewall-Regeln. Standardport 443 ist ideal für spätere Apps; im Beispiel verwenden wir **4443**, da 443 auf NAS-Hosts häufig bereits belegt ist.
- Der Upload prüft Zertifikatsformat, Schlüsselzugehörigkeit, Gültigkeit und DNS-SAN. Er prüft **nicht** die CA-Vertrauenskette oder den DNS-Besitz; das verifiziert der Browser beim Zugriff. Ein selbstsigniertes Zertifikat führt normalerweise zu einer Warnung.

## 2. Develop-Stack in Dockhand für HTTPS vorbereiten

1. Erstelle zunächst ein **externes ZIP-Backup** deiner Tierdaten. Lösche **kein** Volume (also nie `docker compose down -v`).
2. Aktualisiere das GHCR-Image `ghcr.io/skoun181/petdiary:develop` nach erfolgreichem Build.
3. Öffne deinen **vorhandenen** Develop-Stack `petdiary-develop` in Dockhand und ersetze die Compose-Konfiguration durch die komplette Vorlage [compose.develop.https.yaml](../deploy/compose.develop.https.yaml). **Keinen zweiten Stack mit demselben Namen anlegen.**
4. Deployment durchführen. Das bisherige Tierdatenvolume `petdiary-develop-data` bleibt erhalten. Das **zusätzliche** Volume `petdiary-develop-tls` enthält nur Zertifikat und Schlüssel. Der Caddy-Container `petdiary-develop-https` liest ausschließlich dieses Volume im Read-only-Modus und hat keinen Zugriff auf deine SQLite-Datenbank.
5. Die App ist zum Einrichten zunächst weiter unter `http://DEIN-HOST:8081` erreichbar. Der HTTPS-Container wartet auf das erste gültige Zertifikat.

**Achtung bei Synology-Bind-Mounts:** Verwendet dein bisheriger produktiver Stack z. B. `/volume2/docker/petdiary:/data`, dann ändere ihn **nicht** stillschweigend auf ein leeres benanntes Volume. Die hier verlinkte Vorlage ist für deinen **separaten Develop-Stack**. Niemals Stable und Develop gleichzeitig schreibend auf dieselbe SQLite-Datenbank zugreifen lassen.

## 3. Wildcard-Zertifikat hochladen

1. Öffne PetDiary über einen bereits sicheren Proxy oder im **vertrauenswürdigen LAN** über Port 8081 und melde dich an.
2. Gehe auf **Einstellungen → HTTPS / TLS-Zertifikat**.
3. Gib den konkreten Hostnamen `petdiary.meinedomain.de` ein, **ohne** `https://`, Port oder `*`.
4. Lade `fullchain.pem` und `privkey.pem` hoch.
5. Gib dein aktuelles PetDiary-Admin-Passwort ein und klicke **Zertifikat prüfen und sicher speichern**.
6. Die Einstellungen zeigen danach lediglich öffentliche Daten wie Gültigkeitsende, DNS-Namen und SHA-256-Fingerabdruck, **nie** den privaten Schlüssel. Dieser wird nicht in SQLite gespeichert.
7. Der Caddy-Proxy startet nach dem ersten Upload selbständig und erkennt spätere Zertifikatswechsel (Prüfung alle ca. 10 Sekunden). Öffne anschließend `https://petdiary.meinedomain.de:4443`. Vertraue nur der URL, wenn der Browser das Zertifikat als gültig anzeigt.

Wenn 443 auf deinem Host frei ist, kannst du in der Compose-Vorlage die Portzuordnung `"4443:8443"` durch `"443:8443"` ersetzen und danach `https://petdiary.meinedomain.de` ohne Port aufrufen.

## 4. HTTPS nach dem Test absichern

- Beschränke die direkte HTTP-Veröffentlichung `8081:8080` auf `127.0.0.1:8081:8080` oder entferne sie nach erfolgreichem HTTPS-Test. Der Caddy-Proxy erreicht PetDiary intern über das Docker-Netzwerk weiterhin.
- Ergänze **erst dann** beim PetDiary-Service die Umgebungsvariable `COOKIE_SECURE: "1"` und deploye neu. Dadurch wird das Anmeldecookie ausschließlich über HTTPS gesendet; normale HTTP-Logins funktionieren dann nicht mehr.
- Leite öffentliche HTTP-Zugriffe in deinem bestehenden Router/Reverse Proxy auf HTTPS um. Schalte HSTS erst ein, wenn Domain und TLS-Zugriff korrekt funktionieren.
- Das Zertifikat ist ein wichtiges Fundament für eine spätere Smartphone-App, ersetzt aber keine App-Authentifizierung oder spätere mobile Schnittstellen.

## 5. Erneuerung, Fehlersuche und Geheimnisse

Ein **manuell hochgeladenes Wildcard-Zertifikat wird nicht automatisch bei deiner CA erneuert**. Erneuere das Zertifikat rechtzeitig und lade das neue passende Paar im selben Einstellungsbereich hoch; Caddy lädt es automatisch neu. Die Restlaufzeit wird angezeigt.

Zur Diagnose in Dockhand oder auf dem Docker-Host:

~~~bash
docker logs --tail=100 petdiary-develop
docker logs --tail=100 petdiary-develop-https
~~~

Wenn der HTTPS-Container wartet, fehlt der Upload oder das TLS-Volume ist nicht identisch. Bei Browser-Warnungen prüfe Hostname, Zertifizierungskette und CA-Vertrauen. Ist der Port nicht erreichbar, kontrolliere DNS, Port 4443/443, Synology-Hostport und Firewall. Die Datei muss mit UID/GID **10001** lesbar sein.

Der private Schlüssel liegt im dedizierten Docker-Volume `petdiary-develop-tls` mit restriktiven Rechten (0600 für den Schlüssel, 0700 für Verzeichnisse). Neue Schlüsselpaare werden in einem separaten Verzeichnis geschrieben und anschließend **atomar als zusammengehöriges Paar** aktiviert. Ein vorheriger Stand bleibt für die lokale Notfallwiederherstellung erhalten. Der HTTPS-Proxy bindet das Volume nur lesbar ein.

**Weder Zertifikat noch privater Schlüssel befinden sich im portablen ZIP-Datenexport** oder in der internen SQLite-Sicherheitskopie. Für einen Serverumzug Zertifikat, DNS-/Portkonfiguration und Proxy separat und geschützt übertragen bzw. neu ausstellen. Jeder mit administrativem Docker-/Host-Zugriff kann die Schlüsseldateien lesen – Volume, NAS und Host entsprechend absichern.

[Zur README](../README.md) · [HTTPS-Compose für Develop](../deploy/compose.develop.https.yaml)
