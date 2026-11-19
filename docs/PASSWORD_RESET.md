# Passwort zurücksetzen – ohne Datenverlust

[Zurück zur README](../README.md)

PetDiary speichert den Passwort-Hash im persistenten SQLite-Datenvolume. Das Löschen des Volumes wäre deshalb der falsche Weg. Ab Version 0.0.1 steht ein lokales interaktives Wiederherstellungswerkzeug bereit.

## Docker Compose

Auf dem Docker-Host im Projektordner ausführen:

```sh
docker compose exec petdiary python /app/reset_password.py
```

Alternativ mit dem Container-Namen:

```sh
docker exec -it petdiary python /app/reset_password.py
```

Gib zweimal das neue Passwort ein (12–256 Zeichen). Die Eingabe bleibt unsichtbar. Das Werkzeug bestätigt den bestehenden Benutzernamen. Anschließend kannst du dich im Browser damit anmelden. Es wird kein neuer Account erzeugt.

## Portainer oder Dockhand

Öffne den laufenden PetDiary-Container und dessen interaktive Konsole (Shell mit TTY). Starte:

```sh
python /app/reset_password.py
```

Wenn das Terminal keine interaktive Passwortabfrage unterstützt, verwende stattdessen den Docker-Host-Befehl oben.

## Was bleibt erhalten?

- Alle Tierprofile, Profilbilder, Akten und Dokumente
- Impfpass, Erinnerungen und Medikamentenpläne einschließlich dokumentierter Gaben
- Der bestehende Benutzername und Home-Assistant-API-Token

Nur Passwort-Hash und Sitzungskennung des bestehenden Administrators werden ersetzt. Alte Browser-Sitzungen verlieren ihre Berechtigung. Das neue Passwort wird weder als Kommandozeilenargument noch als Umgebungsvariable übergeben.

## Wenn etwas schiefgeht

- Meldung über fehlendes Skript: Zuerst auf das Image/den Quellcode 0.0.1 aktualisieren, ohne das Datenvolume zu löschen.
- Meldung über fehlende Datenbank: Prüfe, ob der Container dasselbe persistente Volume unter /data verwendet. Nicht mit einer neuen leeren Datenbank fortfahren.
- Kein Konto vorhanden: Bei einer wirklich neuen Installation normal im Browser einrichten.
- Container gestoppt: Container mit seinem bisherigen Volume starten, dann den Reset ausführen.
- Bei einer Sperre durch falsche Loginversuche nach dem Reset ggf. eine Minute warten.

Vor Wartung ein Backup erstellen. Niemals `docker compose down -v`, Volume-Löschung oder manuelle SQL-Löschbefehle zum Passwort-Reset verwenden. Der Zugriff auf Docker ist privilegiert; gib ihn nur vertrauenswürdigen Administratoren. 
