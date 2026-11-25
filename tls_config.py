"""Secure, optional TLS certificate storage for the PetDiary Caddy companion.

TLS terminates at Caddy. Never write private keys to SQLite, logs, HTTP responses,
or portable ZIP backups. The store is a dedicated Docker volume when configured.
"""
import json
import os
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, ed448, rsa
from cryptography.x509.oid import ExtendedKeyUsageOID

MAX_PEM_BYTES = 128 * 1024
MAX_KEY_BYTES = 64 * 1024
MAX_CHAIN_CERTIFICATES = 10
CERT_BLOCK = re.compile(rb"-----BEGIN CERTIFICATE-----\r?\n[A-Za-z0-9+/=\r\n]+-----END CERTIFICATE-----")
HOST_PATTERN = re.compile(r"(?=.{4,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")


class CertificateError(ValueError):
    """Validation failure safe to display to a signed-in administrator."""


def normalize_hostname(value):
    name = value.strip().rstrip(".").lower()
    if not name or any(c in name for c in "/:@*\\?#"):
        raise CertificateError("Bitte nur einen DNS-Hostnamen angeben, z. B. petdiary.example.de (ohne https:// und Port).")
    try:
        name = name.encode("idna").decode("ascii")
    except UnicodeError as error:
        raise CertificateError("Der DNS-Hostname ist ungültig.") from error
    if not HOST_PATTERN.fullmatch(name):
        raise CertificateError("Der DNS-Hostname ist ungültig.")
    return name


def hostname_matches(pattern, hostname):
    pattern = pattern.lower().rstrip(".")
    if pattern == hostname:
        return True
    if pattern.startswith("*.") and pattern.count("*") == 1:
        suffix = pattern[2:]
        return hostname.endswith("." + suffix) and hostname.count(".") == suffix.count(".") + 1
    return False


def validate_certificate(fullchain, private_key, hostname):
    """Validate PEM structure, unencrypted key, identity, period and DNS SAN.

    Does not replace browser trust-chain verification or DNS configuration.
    """
    hostname = normalize_hostname(hostname)
    if not fullchain or len(fullchain) > MAX_PEM_BYTES or not private_key or len(private_key) > MAX_KEY_BYTES:
        raise CertificateError("Zertifikatskette oder privater Schlüssel fehlt bzw. überschreitet das Größenlimit.")
    matches = list(CERT_BLOCK.finditer(fullchain))
    if not matches or len(matches) > MAX_CHAIN_CERTIFICATES or CERT_BLOCK.sub(b"", fullchain).strip():
        raise CertificateError("Die Zertifikatsdatei muss ausschließlich PEM-Zertifikate enthalten (fullchain.pem).")
    try:
        chain = [x509.load_pem_x509_certificate(m.group(0)) for m in matches]
    except ValueError as error:
        raise CertificateError("Die PEM-Zertifikatskette ist ungültig.") from error
    if b"-----BEGIN CERTIFICATE-----" in private_key or b"-----BEGIN " not in private_key:
        raise CertificateError("Bitte einen separaten unverschlüsselten PEM-Privatschlüssel hochladen.")
    try:
        key = serialization.load_pem_private_key(private_key, password=None)
    except (ValueError, TypeError) as error:
        raise CertificateError("Der private PEM-Schlüssel ist ungültig oder passwortverschlüsselt. Bitte eine unverschlüsselte Schlüsseldatei verwenden.") from error
    if isinstance(key, rsa.RSAPrivateKey):
        if key.key_size < 2048:
            raise CertificateError("RSA-Schlüssel müssen mindestens 2048 Bit besitzen.")
    elif isinstance(key, ec.EllipticCurvePrivateKey):
        if key.key_size < 256:
            raise CertificateError("Der EC-Schlüssel ist zu schwach.")
    elif not isinstance(key, (ed25519.Ed25519PrivateKey, ed448.Ed448PrivateKey)):
        raise CertificateError("Nur RSA-, EC- oder EdDSA-Schlüssel werden unterstützt.")
    leaf = chain[0]
    encoding = serialization.Encoding.DER
    public_format = serialization.PublicFormat.SubjectPublicKeyInfo
    if leaf.public_key().public_bytes(encoding, public_format) != key.public_key().public_bytes(encoding, public_format):
        raise CertificateError("Zertifikat und privater Schlüssel passen nicht zusammen.")
    now = datetime.now(timezone.utc)
    if now < leaf.not_valid_before_utc or now >= leaf.not_valid_after_utc:
        raise CertificateError("Das Zertifikat ist noch nicht gültig oder bereits abgelaufen.")
    try:
        names = leaf.extensions.get_extension_for_class(x509.SubjectAlternativeName).value.get_values_for_type(x509.DNSName)
    except x509.ExtensionNotFound as error:
        raise CertificateError("Dem Zertifikat fehlt der DNS-SubjectAlternativeName (SAN).") from error
    if not any(hostname_matches(name, hostname) for name in names):
        raise CertificateError("Das Zertifikat gilt nicht für den angegebenen Hostnamen.")
    try:
        if leaf.extensions.get_extension_for_class(x509.BasicConstraints).value.ca:
            raise CertificateError("Bitte das Serverzertifikat als erstes Zertifikat hochladen, kein CA-Zertifikat.")
    except x509.ExtensionNotFound:
        pass
    try:
        eku = leaf.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value
        if ExtendedKeyUsageOID.SERVER_AUTH not in eku:
            raise CertificateError("Das Zertifikat ist nicht für TLS-Serverauthentifizierung freigegeben.")
    except x509.ExtensionNotFound:
        pass
    return {
        "hostname": hostname,
        "dns_names": names[:30],
        "not_before": leaf.not_valid_before_utc.isoformat(),
        "not_after": leaf.not_valid_after_utc.isoformat(),
        "fingerprint_sha256": leaf.fingerprint(hashes.SHA256()).hex(),
        "chain_certificates": len(chain),
        "updated_at": now.isoformat(),
    }


def install_certificate(store_path, fullchain, private_key, hostname):
    """Install a matched pair atomically via an immutable version and symlink swap."""
    metadata = validate_certificate(fullchain, private_key, hostname)
    store = Path(store_path)
    store.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(store, 0o700)
    versions = store / "versions"
    versions.mkdir(exist_ok=True, mode=0o700)
    os.chmod(versions, 0o700)
    version = uuid.uuid4().hex
    destination = versions / version
    destination.mkdir(mode=0o700)
    temp_link = store / (".current-" + version)
    try:
        for name, contents in (("fullchain.pem", fullchain), ("privkey.pem", private_key)):
            target = destination / name
            with target.open("xb") as stream:
                stream.write(contents)
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(target, 0o600)
        target = destination / "metadata.json"
        target.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        os.chmod(target, 0o600)
        temp_link.symlink_to("versions/" + version, target_is_directory=True)
        os.replace(temp_link, store / "current")
        # Keep one previous version for operator rollback; remove older secret keys.
        old = sorted((p for p in versions.iterdir() if p.is_dir()), key=lambda p: p.stat().st_mtime, reverse=True)
        for directory in old[2:]:
            if directory.name != version:
                shutil.rmtree(directory)
        return metadata
    except Exception:
        temp_link.unlink(missing_ok=True)
        if (store / "current").is_symlink() and (store / "current").readlink().name == version:
            # A complete, committed version must not be removed.
            raise
        shutil.rmtree(destination, ignore_errors=True)
        raise


def certificate_status(store_path):
    """Public certificate metadata only. Never return certificate/key PEM content."""
    try:
        store = Path(store_path)
        current = store / "current"
        if not current.is_symlink():
            return None
        info = json.loads((current / "metadata.json").read_text(encoding="utf-8"))
        expiry = datetime.fromisoformat(info["not_after"])
        info["days_remaining"] = max(0, (expiry - datetime.now(timezone.utc)).days)
        info["expired"] = expiry <= datetime.now(timezone.utc)
        return info
    except (OSError, ValueError, KeyError, TypeError):
        return None
