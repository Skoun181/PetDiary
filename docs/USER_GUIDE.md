# PetDiary 0.0.1 – Bedienungsanleitung

[Zurück zur README](../README.md) · [Passwort zurücksetzen](PASSWORD_RESET.md)

Die Bilder sind schematische Illustrationen auf Basis des Oberflächenaufbaus, keine Screenshots eines laufenden Containers. Namen und Inhalte sind fiktiv.

## 1. Ersteinrichtung und Anmeldung

1. Installiere PetDiary nach der [README](../README.md).
2. Öffne die Adresse deines Docker-Hosts mit Port 8080 im Browser.
3. Erstelle einmalig deinen lokalen Benutzernamen und ein Passwort mit 12–256 Zeichen. Bestätige es.
4. Du wirst auf die Übersicht weitergeleitet. Bei späteren Besuchen meldest du dich über die Login-Seite an.
5. Unter **Einstellungen** kannst du das Konto ändern, dich abmelden und einen API-Token erzeugen.

Keine Standard-Zugangsdaten, keine Pflicht-.env und keine Cloud-Anmeldung. Der erste Besucher kann die Ersteinrichtung beanspruchen. Richte den Dienst deshalb in einem vertrauenswürdigen Netz ein und verwende HTTPS für regulären Netzwerkzugriff.

## 2. Dashboard und Tiere

![Illustration der Übersicht und des Kalenders](images/dashboard.svg)

Das Dashboard zeigt die Tierprofile, den wöchentlichen Medikamentenkalender und offene Fälligkeiten der nächsten 30 Tage einschließlich überfälliger Einträge.

Wähle **+ Tier hinzufügen** und erfasse:

| Feld | Hinweise |
|---|---|
| Name und Tierart | Pflichtfelder; Tierart aus der Liste oder eigene Eingabe |
| Rasse | Vorschläge abhängig von Tierart; eigene Rassen zulässig |
| Geburtsdatum, Geschlecht | Optional; Geschlecht ist frei editierbar |
| Fellfarbe, Merkmale | Suchbare Farbliste; Merkmale separat als Freitext |
| Profilbild | JPEG, PNG oder WebP; maximal 5 MB |
| Mikrochip | Nummer, Kennzeichnungsdatum, Position; eigene Position möglich |
| Tätowierung | Zeichen/Nummer und Position |
| Halter und Heimtierausweis | Halter, Kontakt, Ausweisnummer, ausstellende Praxis und Datum |

Die suchbaren Vorschlagsfelder filtern beim Tippen. Pfeiltaste nach unten öffnet bzw. navigiert die Liste, Enter übernimmt den markierten Vorschlag, Escape schließt sie. Ein frei eingegebener Text bleibt bei editierbaren Feldern zulässig. Kategorien und Kalenderfilter sind feste Auswahllisten.

Speichere das Profil. Über **Profil bearbeiten** kannst du Angaben und Bild später austauschen oder das Bild entfernen. Weitere Tiere werden über die Übersicht hinzugefügt. Ein Tier zu löschen entfernt auch seine Einträge, Anhänge und Medikamentenstatus. Die Namensbestätigung schützt vor versehentlichem Löschen; es gibt keinen Papierkorb.

## 3. Gesundheitsakte

![Illustration der chronologischen Tierakte](images/tierakte.svg)

Öffne ein Tier und wähle **+ Eintrag**. Die Akte ist nach Ereignisdatum absteigend sortiert und nach Kategorien filterbar.

| Kategorie | Typische dokumentierte Angaben |
|---|---|
| Termin | Datum, Praxis, Anlass, Erinnerung |
| Impfung | Impfdatum, Impfstoff, Charge, Tierarzt, Gültigkeit |
| Untersuchung | Datum, Ergebnis, Gewicht, Tierarzt, Befund |
| Labor/Befund | Notizen, Untersuchungsergebnis, Dokument |
| Medikament | Präparat, verordnete Menge und Einnahmeplan |
| Entwurmung / Parasitenbehandlung | Datum, Präparat, Charge und Notizen |
| Gewicht | Gewicht in kg, Datum, Notizen |
| Ernährung | Futter, Beobachtungen, Verträglichkeit als Notiz |
| Notiz / Erinnerung | Titel, Datum, Beschreibung, optionales Erinnerungsdatum |
| Tollwut-Antikörpertest | Dokumentierte Nachweisgültigkeit, Befund |

Kategorie, Titel und Datum sind Pflicht. Die restlichen Angaben sind optional, außer bei einem ausdrücklich angelegten Medikamentenplan. Je nach Kategorie werden passende Zusatzfelder angezeigt. Bereits gespeicherte Zusatzangaben können weiterhin sichtbar sein.

Einträge lassen sich über **Bearbeiten** ändern. Beim Löschen werden die zugehörigen Anhänge und Gabe-Häkchen ebenfalls gelöscht.

### Dokumente und Befunde

Wähle eine oder mehrere Dateien im Akteneintrag aus. Unterstützt: PDF, JPEG, PNG, WebP. Pro Speichervorgang sind fünf Dateien von je maximal 10 MB möglich. Nach dem Speichern erscheint der Dateilink in der Akte. Öffne ihn für die Vorschau; der Download ist optional. PDFs benötigen die PDF-Unterstützung des Browsers. Im Bearbeitungsmodus können einzelne Anhänge gelöscht werden.

## 4. Digitaler Impfpass

![Illustration des privaten digitalen Impfpasses](images/impfpass.svg)

1. Öffne die Tierakte und den Reiter **Digitaler Impfpass**.
2. Ergänze die Stammdaten des Heimtierausweises über **Ausweisdaten bearbeiten**.
3. Lege eine Impfung mit Datum, Präparat, Charge, behandelnder Praxis und dokumentierter Gültigkeit an.
4. Füge bei Bedarf ein Foto oder PDF des Nachweises an.
5. Trage unter **Erinnern am** einen gewünschten Termin ein. Ohne eigenes Datum wird bei Impfungen das Gültigkeitsende übernommen.

Beispiel: Der Nachweis ist bis 15.12.2027 gültig, erinnert werden möchtest du am 01.12.2027. Das sind unterschiedliche Angaben. PetDiary berechnet keine medizinischen Impfintervalle.

Der Bereich umfasst auch Vorsorgeeinträge wie Entwurmungen, Parasitenbehandlungen und Tollwut-Antikörpertests. Er ist eine private Abschrift und kein amtlicher EU-Heimtierausweis, keine tierärztliche Bescheinigung und kein Ersatz für erforderliche Originaldokumente bei Reisen.

## 5. Medikamentenplan und Kalender

![Illustration eines Medikamentenplans](images/medikamentenplan.svg)

1. Lege einen Eintrag mit Kategorie **Medikament** an.
2. Erfasse den Behandlungsbeginn und einen Titel.
3. Suche das konkrete Präparat einschließlich Stärke. Fehlt es, nutze die eigene genaue Präparatbezeichnung. Sie überschreibt die Auswahl und wird künftig vorgeschlagen.
4. Gib die vom Tierarzt verordnete Menge je Gabe, Einheit und Behandlungsdauer in Tagen an.
5. Trage die tatsächlichen Uhrzeiten ein. Über **+ Weitere Uhrzeit** sind bis zu zwölf Zeiten pro Tag möglich.
6. Speichere. Der Wochenkalender erzeugt die Gaben vom ersten Tag bis einschließlich des letzten Behandlungstags.

Ein Plan mit 14 Tagen und zwei eingetragenen Uhrzeiten ergibt 28 Kalendereinträge. Das ist eine reine Planungsrechnung, keine medizinische Empfehlung. Unterschiedliche Mengen, wechselnde Zeiten oder Unterbrechungen als getrennte Pläne abbilden. Derzeit unterstützt ein Plan identische tägliche Zeiten und Mengen für 1–3660 Tage. Für Dauermedikation müssen Pläne bei Bedarf verlängert werden.

Im Dashboard kannst du die Woche wechseln und nach Tier filtern. Markiere jede tatsächliche Gabe als gegeben. Ein Häkchen kann rückgängig gemacht werden. Änderungen am Plan (Präparat, Menge, Start, Dauer oder Uhrzeiten) setzen die bisherigen Häkchen dieses Plans zurück. Ändere abgeschlossene Verläufe daher nur bewusst.

Unter **Separate Erinnerung** kann zusätzlich ein Nachkontrolltermin eingetragen werden. Die täglichen Gaben benötigen kein zusätzliches Erinnerungsdatum.

Der lokale Präparatekatalog ist ein Startkatalog und keine vollständige behördliche Arzneimitteldatenbank. Die Produktstärke ist nicht die verordnete Dosierung. Die Eingabe und Verabreichung von Medikamenten erfolgen nach tierärztlicher Anweisung; PetDiary prüft keine Eignung, Wechselwirkungen oder Dosierungen.

## 6. Erinnerungen

Die Übersicht zeigt offene Fälligkeiten der kommenden 30 Tage und Überfälliges. Unter **Erinnerungen** findest du alle offenen datumsbasierten Fälligkeiten. Markiere eine Erinnerung als erledigt; der Akteneintrag bleibt erhalten. Du kannst sie beim Bearbeiten wieder öffnen. Zukünftige Termine erhalten standardmäßig den Termintag als Fälligkeit.

Medikamentengaben besitzen einen eigenen Status pro Uhrzeit und Datum im Kalender. Sie laufen getrennt von den datumsbasierten Erinnerungen.

## 7. Home Assistant

1. In PetDiary unter **Einstellungen → Home Assistant** das aktuelle Passwort bestätigen und einen API-Token erstellen.
2. Den Token sofort sicher kopieren. Er wird nur bei Erstellung angezeigt. Ein neuer Token widerruft den alten.
3. Die Beispielkonfigurationen [Erinnerungen](../examples/home-assistant.yaml) und [Medikamente](../examples/home-assistant-medications.yaml) unter derselben vorhandenen `rest:`-Liste in Home Assistant zusammenführen (nicht zwei gleichnamige YAML-Schlüssel anlegen).
4. In `secrets.yaml` die tatsächlichen Adressen mit erreichbarer HTTPS- oder LAN-Adresse und den Bearer-Header eintragen:

```yaml
petdiary_url: "https://PETDIARY-HOST/api/v1/reminders?days=30"
petdiary_medication_url: "https://PETDIARY-HOST/api/v1/medications?days=1"
petdiary_authorization: "Bearer DEIN_TOKEN"
```

5. HA-Konfiguration prüfen und neu laden bzw. neu starten. Über **Entwicklerwerkzeuge → Zustände** die tatsächlich erzeugten Entity-IDs überprüfen.
6. Die [Dashboard-Karte](../examples/home-assistant-card.yaml) als manuelle Markdown-Karte hinzufügen und Entity-IDs ggf. ändern.

Die API ist lesend. Datumsfälligkeiten sind in der Zeitzone des Servers, standardmäßig Europe/Berlin; Medikamentenzeiten enthalten einen Offset. Die Medikamenten-API liefert nur das gewählte Zeitfenster. Eine HA-Benachrichtigungsautomation muss separat angelegt werden. PetDiary verschickt keine eigenen Push-Nachrichten. Verlass dich bei medizinisch kritischen Gaben nicht auf eine einzige Polling-Automation.

## 8. Einstellungen und Wartung

Unter Einstellungen änderst du Konto und API-Token. Das Passwort muss 12–256 Zeichen umfassen. Passwortänderungen machen frühere Sitzungen ungültig; der API-Token bleibt unabhängig davon gültig.

Wenn du das Passwort vergessen hast: [Passwort zurücksetzen](PASSWORD_RESET.md).

Zur Datensicherung, Wiederherstellung, Aktualisierung und Fehlersuche siehe [README](../README.md). Der derzeitige Stand ist eine Vorabversion, nicht medizinisch validierte Software. Kein Live-Docker-/Browser-Test oder Performancebenchmark ist dokumentiert.
