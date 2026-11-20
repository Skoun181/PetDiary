"""Portable, credential-free PetDiary backups and atomic data restores.

The downloadable SQLite snapshot intentionally omits admin_account and app_settings.
An internal pre-import snapshot is retained under /data with strict permissions,
because it is the emergency rollback copy and contains the destination's credentials.
"""
import hashlib
import json
import logging
import os
import re
import shutil
import sqlite3
import stat
import tempfile
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

LOG = logging.getLogger(__name__)
BACKUP_FORMAT = "petdiary-portable"
FORMAT_VERSION = 1
SCHEMA_VERSION = 1
MAX_ARCHIVE_BYTES = 256 * 1024 * 1024
MAX_DATABASE_BYTES = 1024 * 1024 * 1024
MAX_MANIFEST_BYTES = 32768
BACKUP_TABLES = ("pets", "records", "pet_photos", "attachments", "products", "dose_checks")
DELETE_ORDER = ("dose_checks", "attachments", "pet_photos", "records", "pets", "products")
BACKUP_MEMBERS = {"manifest.json", "petdiary.sqlite3"}
SAFETY_FOLDER = ".petdiary-safety-backups"
CHUNK = 1024 * 1024


class BackupError(ValueError):
    """Expected validation error safe to show to a signed-in user."""


def _connect(database, readonly=False):
    if readonly:
        con = sqlite3.connect(database.resolve().as_uri() + "?mode=ro&immutable=1", uri=True, timeout=30)
        con.execute("PRAGMA trusted_schema=OFF")
    else:
        con = sqlite3.connect(database, timeout=30)
        con.execute("PRAGMA foreign_keys=ON")
        con.execute("PRAGMA busy_timeout=30000")
    return con


def _snapshot(source_path, destination_path):
    """SQLite online-backup API includes committed WAL content without blocking readers."""
    source = sqlite3.connect(source_path, timeout=30)
    target = sqlite3.connect(destination_path)
    try:
        source.backup(target, pages=256, sleep=0.02)
    finally:
        target.close()
        source.close()
    destination_path.chmod(0o600)


def _digest(path):
    result = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(CHUNK), b""):
            result.update(chunk)
    return result.hexdigest()


def _counts(con):
    return {table: con.execute("SELECT count(*) FROM " + table).fetchone()[0] for table in BACKUP_TABLES}


def _check_db(con):
    result = con.execute("PRAGMA integrity_check").fetchone()
    if not result or result[0] != "ok":
        raise BackupError("Die Sicherung enthält eine beschädigte SQLite-Datenbank.")
    if con.execute("PRAGMA foreign_key_check").fetchone():
        raise BackupError("Die Sicherung enthält ungültige Datensatz-Verknüpfungen.")


def _verify_tables(source, destination):
    # Accept only a normal SQLite database without executable schema objects.
    entries = source.execute("SELECT type,name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'").fetchall()
    accepted = set(BACKUP_TABLES) | {"admin_account", "app_settings", "records_pet_day", "records_due",
              "attachments_record", "records_parent"}
    if any(kind not in ("table", "index") or name not in accepted for kind, name in entries):
        raise BackupError("Die Sicherung enthält unerwartete Datenbankobjekte.")
    for table in BACKUP_TABLES:
        incoming = {row[1] for row in source.execute("PRAGMA table_info(" + table + ")")}
        installed = {row[1] for row in destination.execute("PRAGMA table_info(" + table + ")")}
        if not incoming or incoming != installed:
            raise BackupError("Die Datenbankstruktur ist nicht kompatibel (Tabelle " + table + ").")
    for table in ("app_settings", "admin_account"):
        if source.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]:
            raise BackupError("Die Sicherung enthält Zugangsdaten und kann nicht importiert werden.")


def _safe_manifest(manifest):
    if not isinstance(manifest, dict) or manifest.get("format") != BACKUP_FORMAT:
        raise BackupError("Das ist keine gültige PetDiary-Sicherungsdatei.")
    if type(manifest.get("format_version")) is not int or manifest["format_version"] != FORMAT_VERSION:
        raise BackupError("Die Sicherungsversion wird nicht unterstützt.")
    if type(manifest.get("schema_version")) is not int or manifest["schema_version"] != SCHEMA_VERSION:
        raise BackupError("Die Datenbank-Schema-Version ist nicht kompatibel.")
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:[-.][A-Za-z0-9.]+)?", str(manifest.get("app_version", ""))):
        raise BackupError("Die App-Versionsangabe ist ungültig.")
    if not re.fullmatch("[a-f0-9]{64}", str(manifest.get("database_sha256", ""))):
        raise BackupError("Die Sicherungs-Prüfsumme ist ungültig.")
    try:
        datetime.fromisoformat(manifest["created_at"])
    except (KeyError, ValueError, TypeError):
        raise BackupError("Das Exportdatum ist ungültig.")
    if not isinstance(manifest.get("counts"), dict):
        raise BackupError("Die Datensatz-Metadaten fehlen.")
    if set(manifest["counts"]) != set(BACKUP_TABLES) or any(type(x) is not int or x < 0 for x in manifest["counts"].values()):
        raise BackupError("Ungültige Datensatz-Metadaten.")


def create_portable_backup(database, data_dir, app_version):
    """Return (temporary directory, archive path, counts); caller must cleanup."""
    temporary = tempfile.TemporaryDirectory(prefix=".petdiary-export-", dir=data_dir)
    try:
        folder = Path(temporary.name)
        snapshot = folder / "petdiary.sqlite3"
        _snapshot(database, snapshot)
        sanitizing = _connect(snapshot)
        try:
            with sanitizing:
                _check_db(sanitizing)
                sanitizing.execute("PRAGMA secure_delete=ON")
                sanitizing.execute("DELETE FROM admin_account")
                sanitizing.execute("DELETE FROM app_settings")
                sanitizing.execute("PRAGMA user_version=" + str(SCHEMA_VERSION))
                counts = _counts(sanitizing)
        finally:
            sanitizing.close()
        # A copy of a WAL-mode database must not depend on an external -wal file.
        with sqlite3.connect(snapshot) as con:
            con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            con.execute("PRAGMA journal_mode=DELETE")
            # Purge freed pages containing historic credential hashes/keys from the snapshot.
            con.execute("VACUUM")
            _check_db(con)
        if snapshot.stat().st_size > MAX_DATABASE_BYTES:
            raise BackupError("Die Datenbank überschreitet das maximale Exportvolumen (1 GiB).")
        created = datetime.now(timezone.utc)
        meta = {
            "format": BACKUP_FORMAT,
            "format_version": FORMAT_VERSION,
            "schema_version": SCHEMA_VERSION,
            "created_at": created.isoformat(timespec="seconds"),
            "app_version": app_version,
            "database_sha256": _digest(snapshot),
            "counts": counts,
            "credentials": "excluded",
            "note": "Tier- und Gesundheitsdaten können vertraulich sein. Sicher aufbewahren.",
        }
        filename = "petdiary-backup-" + created.strftime("%Y-%m-%d-%H%M%S") + ".zip"
        archive = folder / filename
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as output:
            output.writestr("manifest.json", json.dumps(meta, indent=2, ensure_ascii=False))
            output.write(snapshot, "petdiary.sqlite3")
        if archive.stat().st_size > MAX_ARCHIVE_BYTES:
            raise BackupError("Das ZIP überschreitet die maximale Exportgröße (256 MiB).")
        LOG.info("Portable backup created: pets=%d records=%d attachments=%d",
                 counts["pets"], counts["records"], counts["attachments"])
        return temporary, archive, counts
    except Exception:
        temporary.cleanup()
        LOG.exception("Portable backup generation failed")
        raise


def _save_upload(file, target):
    uploaded = 0
    with target.open("xb") as output:
        target.chmod(0o600)
        while True:
            block = file.stream.read(CHUNK)
            if not block:
                break
            uploaded += len(block)
            if uploaded > MAX_ARCHIVE_BYTES:
                raise BackupError("Die ZIP-Datei ist zu groß (maximal 256 MiB).")
            output.write(block)
    if uploaded < 22:
        raise BackupError("Die Datei ist zu klein oder kein ZIP-Archiv.")


def _inspect_archive(archive, dest):
    try:
        with zipfile.ZipFile(archive, "r", allowZip64=True) as zipped:
            entries = zipped.infolist()
            if len(entries) != 2 or {item.filename for item in entries} != BACKUP_MEMBERS:
                raise BackupError("Das ZIP enthält unerwartete Dateien.")
            for info in entries:
                # Exact-member allowlist forbids paths, traversal and duplicate entries.
                if info.is_dir() or info.flag_bits & 1 or stat.S_ISLNK(info.external_attr >> 16):
                    raise BackupError("Verschlüsselte ZIPs, Links und Verzeichnisse sind nicht erlaubt.")
                maximum = MAX_MANIFEST_BYTES if info.filename == "manifest.json" else MAX_DATABASE_BYTES
                if info.file_size > maximum:
                    raise BackupError("Die entpackten Dateien überschreiten die Größenbegrenzung.")
            raw = zipped.read("manifest.json")
            if len(raw) > MAX_MANIFEST_BYTES:
                raise BackupError("Die ZIP-Metadaten sind zu groß.")
            try:
                manifest = json.loads(raw.decode("utf-8"))
            except (UnicodeError, json.JSONDecodeError):
                raise BackupError("Die ZIP-Metadaten sind ungültig.")
            _safe_manifest(manifest)
            total = 0
            digest = hashlib.sha256()
            with zipped.open("petdiary.sqlite3") as source, dest.open("xb") as destination:
                dest.chmod(0o600)
                for block in iter(lambda: source.read(CHUNK), b""):
                    total += len(block)
                    if total > MAX_DATABASE_BYTES:
                        raise BackupError("Die entpackte Datenbank ist zu groß.")
                    destination.write(block)
                    digest.update(block)
            if digest.hexdigest() != manifest["database_sha256"]:
                raise BackupError("Die ZIP-Prüfsumme stimmt nicht überein.")
            with dest.open("rb") as db_file:
                is_sqlite = db_file.read(16) == b"SQLite format 3\x00"
            if total < 100 or not is_sqlite:
                raise BackupError("Die Sicherung enthält keine gültige SQLite-Datei.")
            return manifest
    except (OSError, zipfile.BadZipFile, zipfile.LargeZipFile, RuntimeError) as error:
        LOG.warning("Invalid uploaded backup: %s", type(error).__name__)
        raise BackupError("Das ZIP-Archiv ist defekt oder kann nicht gelesen werden.") from error


def _safety_backup(database, data_dir):
    directory = Path(data_dir) / SAFETY_FOLDER
    if directory.is_symlink():
        raise BackupError("Unsicheres Sicherungsverzeichnis.")
    directory.mkdir(mode=0o700, exist_ok=True)
    if directory.is_symlink():
        raise BackupError("Unsicheres Sicherungsverzeichnis.")
    directory.chmod(0o700)
    filename = "pre-import-" + datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S") + "-" + uuid.uuid4().hex[:10] + ".sqlite3"
    target = directory / filename
    try:
        _snapshot(database, target)
        with sqlite3.connect(target) as connection:
            _check_db(connection)
        LOG.info("Internal pre-import safety backup created")
        return target
    except Exception:
        target.unlink(missing_ok=True)
        LOG.exception("Pre-import safety backup failed")
        raise


def _replace_data(source, database, default_products):
    destination = _connect(database)
    try:
        with destination:
            destination.execute("BEGIN IMMEDIATE")
            destination.execute("PRAGMA defer_foreign_keys=ON")
            for table in DELETE_ORDER:
                destination.execute("DELETE FROM " + table)
            # Keep IDs and relationships for linked records, photos, attachments and doses.
            for table in BACKUP_TABLES:
                columns = [row[1] for row in source.execute("PRAGMA table_info(" + table + ")")]
                names = ",".join('"' + c + '"' for c in columns)
                marks = ",".join("?" for _ in columns)
                cursor = source.execute("SELECT " + names + " FROM " + table)
                while True:
                    rows = cursor.fetchmany(128)
                    if not rows:
                        break
                    destination.executemany("INSERT INTO " + table + " (" + names + ") VALUES (" + marks + ")", rows)
            destination.executemany("INSERT OR IGNORE INTO products(name) VALUES (?)", ((p,) for p in default_products))
            if destination.execute("PRAGMA foreign_key_check").fetchone():
                raise BackupError("Der Import hat ungültige Referenzen. Die Änderungen wurden zurückgerollt.")
            if destination.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise BackupError("Die Datenbankprüfung schlug fehl. Die Änderungen wurden zurückgerollt.")
            return _counts(destination)
    finally:
        destination.close()


def restore_portable_backup(file, database, data_dir, default_products):
    """Validate first, take a safety backup, then replace only application tables.

    Auth, API tokens and session secret of the destination are never overwritten.
    SQLite transaction keeps the previous state intact if any insertion fails.
    """
    if not file or not file.filename or not file.filename.lower().endswith(".zip"):
        raise BackupError("Bitte eine von PetDiary exportierte ZIP-Datei auswählen.")
    temporary = tempfile.TemporaryDirectory(prefix=".petdiary-import-", dir=data_dir)
    try:
        folder = Path(temporary.name)
        archive = folder / "incoming.zip"
        _save_upload(file, archive)
        incoming = folder / "petdiary.sqlite3"
        manifest = _inspect_archive(archive, incoming)
        source = _connect(incoming, readonly=True)
        try:
            current = _connect(database)
            try:
                _verify_tables(source, current)
            finally:
                current.close()
            _check_db(source)
            actual = _counts(source)
            if actual != manifest["counts"]:
                raise BackupError("Die Anzahl der Datensätze stimmt nicht mit den Backup-Metadaten überein.")
            # Only after full validation: back up the original, including its credentials.
            safety = _safety_backup(database, data_dir)
            try:
                counts = _replace_data(source, database, default_products)
            except Exception:
                LOG.exception("Data import rolled back; internal safety backup retained")
                raise
        finally:
            source.close()
        LOG.info("Portable restore complete: pets=%d records=%d attachments=%d",
                 counts["pets"], counts["records"], counts["attachments"])
        return counts, safety.name
    except BackupError:
        LOG.warning("Portable import rejected by validation")
        raise
    except (sqlite3.Error, OSError, ValueError) as error:
        LOG.exception("Portable data import failed")
        raise BackupError("Der Import ist fehlgeschlagen. Die bestehenden Daten wurden nicht geändert; bitte die Serverlogs prüfen.") from error
    finally:
        temporary.cleanup()

if __name__ == "__main__":
    # Offline converter for installations older than the browser export feature.
    # No Flask, live credentials or Docker Hub access required.
    import argparse
    parser=argparse.ArgumentParser(description="Create a credential-free PetDiary ZIP from an existing SQLite snapshot.")
    parser.add_argument("export", choices=["export"])
    parser.add_argument("--database", required=True, type=Path, help="Existing SQLite database or offline snapshot")
    parser.add_argument("--output-dir", required=True, type=Path, help="Directory for the ZIP file")
    parser.add_argument("--app-version", default="0.0.4", help="Version of the source application")
    arguments=parser.parse_args()
    if not arguments.database.is_file():
        parser.error("The input database does not exist.")
    arguments.output_dir.mkdir(parents=True, exist_ok=True)
    temporary, archive, counts=create_portable_backup(arguments.database, arguments.output_dir, arguments.app_version)
    try:
        final=arguments.output_dir / archive.name
        shutil.copy2(archive, final)
        final.chmod(0o600)
        print("Exported "+str(final)+" (pets="+str(counts["pets"])+", records="+str(counts["records"])+")")
    finally:
        temporary.cleanup()
