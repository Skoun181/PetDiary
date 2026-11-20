# PetDiary – Entwicklung und Releases

## Branches
- stable: produktiver Quellcode, nur geprüfte Releases. Standardbranch.
- develop: laufende Entwicklung. Pushes führen Tests aus, veröffentlichen aber keine Docker-Images.

Temporäre Arbeitsbranches dürfen nach dem Merge gelöscht werden. Versionshistorie über unveränderliche Git-Tags und GitHub Releases, keine dauerhaften Release-Branches.

## Neue Version
1. Änderungen auf develop durchführen und testen. VERSION erhöhen (z. B. 0.0.2 → 0.0.3); für neue Features gegebenenfalls Minor/Major erhöhen. Die Versionsangabe im Dockerfile und die Dokumentation anpassen, CHANGELOG.md ergänzen.
2. Einen Pull Request von develop nach stable öffnen. Tests unter Checks abwarten und Änderungen prüfen.
3. Merge durchführen (Merge Commit empfohlen, damit beide dauerhaften Branches eine gemeinsame Historie behalten).
4. Die GitHub Action testet stable, baut linux/amd64 und linux/arm64 und veröffentlicht das Image auf Docker Hub unter dem Versions-Tag (z. B. 0.0.3) sowie latest und stable. Erst nach erfolgreichem Push legt sie das GitHub Release und den Git-Tag v0.0.3 an.
5. Unter Actions, Releases und Docker Hub Tags den Erfolg kontrollieren; danach Dockhand/Portainer aktualisieren. Vorher das bestehende Datenvolume sichern.

VERSION muss für jede neue veröffentlichte Code-Version erhöht werden. Wenn ein Release bereits existiert, überspringt die Pipeline das Veröffentlichen. Reine Dokumentationsänderungen ohne Versionswechsel sind möglich. Keine bestehenden Versions-Tags verschieben oder erneut veröffentlichen. Nicht mehrere Versionsmerges gleichzeitig durchführen.

## Einmalige Konfiguration
In GitHub Settings → Secrets and variables → Actions müssen die Repository Secrets DOCKERHUB_USERNAME und DOCKERHUB_TOKEN (Docker Hub Read & Write) vorhanden sein. Die Pipeline verwendet den integrierten GITHUB_TOKEN mit contents: write nur im Release-Job. Keine Geheimnisse im Repository speichern.

Standardbranch auf stable setzen. Branch-Regeln für stable: Pull Requests voraussetzen, Force Push und Löschen blockieren, Test-Job als Pflichtcheck erst nach einem erfolgreichen Durchlauf konfigurieren; bei Einzelentwicklung 0 erforderliche Freigaben. Keine Regel darf die automatische Erstellung neuer Versions-Tags durch den Workflow verhindern.

## Fehlerbehebung
Unter [Actions](https://github.com/Skoun181/PetDiary/actions) den fehlgeschlagenen Schritt öffnen. Bei einem Fehler vor dem GitHub Release kann der fehlgeschlagene Job nach Behebung erneut ausgeführt werden. Wenn ein Docker-Versionstag bereits veröffentlicht wurde, aber das GitHub Release fehlt, zuerst prüfen, ob Image, Commit und VERSION zusammengehören; dann fehlendes Release für genau diesen Commit nachtragen. Nicht blind bestehende Tags überschreiben. Manuell gestartete Workflows veröffentlichen ausschließlich vom Branch stable.

[Releases](https://github.com/Skoun181/PetDiary/releases) · [Docker Hub](https://hub.docker.com/r/skoun181/petdiary/tags)

## Aktueller Entwicklungsstand

Die Funktionen für portable ZIP-Backups und den Import sind für die geplante Version 0.0.5 auf `develop` implementiert. Vor einem Merge nach `stable` Integrations- und Sicherheitschecks sowie einen Live-Umzug mit Testdaten im separaten `petdiary-develop-data`-Volume verifizieren. `latest` und `stable` auf Docker Hub bleiben unberührt, bis ein Release ausdrücklich freigegeben und gemergt wird. Bei Veröffentlichung muss `VERSION` strikt höher als `0.0.4` sein.
