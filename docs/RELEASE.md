# Maintainer: PetDiary 0.0.1 veröffentlichen

Die Quellcode-Version liegt im Branch `release/0.0.1`. GitHub-Release, Tag und Container-Registry-Paket sind getrennte Dinge. Dieses Dokument beschreibt die manuellen Schritte; es gibt noch keinen verifizierten Release-Workflow.

## 1. Quellcode und Tests

```sh
git fetch origin
git switch release/0.0.1
git pull --ff-only
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m unittest discover -s tests -v
docker compose build
```

Docker anschließend in einer separaten Testinstallation mit eigenem Volume und freiem Port prüfen. Anmeldung, Tierprofile, PDF/Bilder, Impfpass, Kalender, Dropdowns auf Desktop/Mobilgerät, API und Passwort-Recovery testen. Bestehende Produktivdaten nie als Testdaten benutzen. Tests/Build müssen vor Registry-Freigabe erfolgreich sein.

## 2. GitHub-Release und Tag

Mit autorisierter GitHub CLI (`gh auth login`) und Schreibrechten:

```sh
gh release create v0.0.1 --repo Skoun181/PetDiary \
  --target release/0.0.1 --title "PetDiary 0.0.1" \
  --notes-file CHANGELOG.md --prerelease
```

Der Befehl erzeugt den Tag, falls er noch nicht existiert, sowie ein GitHub-Prerelease. Alternativ in GitHub unter Releases → Draft a new release einen neuen Tag `v0.0.1` mit Zielbranch release/0.0.1 wählen, Titel und Changelog übernehmen, als Prerelease markieren und veröffentlichen. Das Repository bleibt privat, sofern der Eigentümer die Sichtbarkeit nicht ändert.

## 3. Container-Image in GHCR veröffentlichen

Benötigt einen Personal Access Token (classic) mit passenden Paket-Schreibrechten (write:packages) und ggf. Organisationsfreigabe; niemals Token in die Repository-Dateien schreiben. In Bash:

```sh
read -rsp "GHCR-Token: " GHCR_TOKEN; echo
printf '%s' "$GHCR_TOKEN" | docker login ghcr.io -u Skoun181 --password-stdin
unset GHCR_TOKEN
```

Docker Buildx und Multiarch-Unterstützung vorausgesetzt. Falls der Builder keine ARM64-Ausführung unterstützt, einen geeigneten ARM64-Builder oder eingerichtete Emulation verwenden. Aus dem geprüften Release-Quellcode:

```sh
docker buildx build --platform linux/amd64,linux/arm64 \
  -t ghcr.io/skoun181/petdiary:0.0.1 --push .
docker buildx imagetools inspect ghcr.io/skoun181/petdiary:0.0.1
```

Beide Architekturen erst nach erfolgreichem Pull und Laufzeittest als unterstützt kennzeichnen. Falls zunächst nur der native Build möglich ist, stattdessen `docker build -t ghcr.io/skoun181/petdiary:0.0.1 .` und `docker push ghcr.io/skoun181/petdiary:0.0.1` auf der jeweiligen Architektur ausführen; das ist noch kein Multiarch-Image.

## 4. Sichtbarkeit

GHCR-Pakete sind nicht automatisch öffentlich. Für private Nutzung Paket privat lassen und auf jedem Zielhost mit einem berechtigten read:packages-Token anmelden. Nur wenn ausdrücklich eine öffentliche Verteilung gewünscht ist, die Paket-Sichtbarkeit in den GitHub-Package-Einstellungen auf Public setzen; das kann öffentlich zugänglichen Anwendungscode bedeuten. Das Recht zur Veröffentlichung und ggf. eine Softwarelizenz vorher klären.

Danach die README und Stack-Vorlage auf den verifizierten Registry-Status aktualisieren, die Versionsnummer nicht stillschweigend für neuen Code wiederverwenden und ein Update mit der dokumentierten Backup-Strategie testen.

Referenzen: [GitHub CLI release create](https://cli.github.com/manual/gh_release_create), [GitHub Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry), [Docker Multi-platform builds](https://docs.docker.com/build/building/multi-platform/).
