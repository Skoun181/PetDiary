"""Local administrator recovery. Run inside the PetDiary container."""
import getpass
import os
import secrets
import sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash


def reset_password(db_path, password):
    if not 12 <= len(password) <= 256:
        raise ValueError("Passwort muss 12–256 Zeichen enthalten.")
    path = Path(db_path)
    if not path.is_file():
        raise ValueError("Keine vorhandene PetDiary-Datenbank gefunden.")
    con = sqlite3.connect(path.resolve().as_uri() + "?mode=rw", uri=True, timeout=10)
    try:
        with con:
            con.execute("BEGIN IMMEDIATE")
            account = con.execute("SELECT username FROM admin_account WHERE id=1").fetchone()
            if not account:
                raise ValueError("Kein bestehendes Administratorkonto gefunden. Nutze die Ersteinrichtung.")
            con.execute("UPDATE admin_account SET password_hash=?, session_version=? WHERE id=1",
                        (generate_password_hash(password), secrets.token_hex(16)))
        return account[0]
    finally:
        con.close()


def main():
    path = Path(os.getenv("DATA_DIR", "/data")) / "petdiary.sqlite3"
    try:
        if not path.is_file():
            raise ValueError("Keine vorhandene PetDiary-Datenbank gefunden.")
        if not os.isatty(0):
            raise ValueError("Interaktives Terminal erforderlich (docker exec -it).")
        password = getpass.getpass("Neues Passwort: ")
        if password != getpass.getpass("Neues Passwort wiederholen: "):
            raise ValueError("Passwörter stimmen nicht überein.")
        username = reset_password(path, password)
        print("Passwort für", username, "geändert. Alte Sitzungen sind ungültig.")
        print("Tierakten, Bilder, Anhänge, Medikamentenpläne und API-Token bleiben erhalten.")
        return 0
    except (ValueError, sqlite3.Error, EOFError, KeyboardInterrupt) as exc:
        print("Passwort nicht geändert:", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
