"""Security tests for optional certificate upload and isolated TLS storage."""
import io
import json
import os
import stat
import tempfile
import unittest
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from app import create_app
from tls_config import (
    CertificateError, certificate_status, hostname_matches,
    install_certificate, normalize_hostname, validate_certificate
)


def make_cert(dns_name="*.example.de", expired=False):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=60 if expired else 1)
    end = now - timedelta(days=1) if expired else now + timedelta(days=60)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, dns_name)])
    certificate = (
        x509.CertificateBuilder().subject_name(subject).issuer_name(subject)
        .public_key(key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(start).not_valid_after(end)
        .add_extension(x509.SubjectAlternativeName([x509.DNSName(dns_name)]), critical=False)
        .add_extension(x509.BasicConstraints(ca=False,path_length=None),critical=True)
        .sign(key,hashes.SHA256())
    )
    cert_pem = certificate.public_bytes(serialization.Encoding.PEM)
    key_pem = key.private_bytes(
        serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()
    )
    return cert_pem,key_pem


class TestTLSConfiguration(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store=Path(self.tmp.name)/"tls"

    def test_dns_validation_and_reject_bad_pairs(self):
        cert,key=make_cert()
        self.assertEqual(normalize_hostname("PETDIARY.Example.DE."),"petdiary.example.de")
        self.assertTrue(hostname_matches("*.example.de","petdiary.example.de"))
        self.assertFalse(hostname_matches("*.example.de","sub.petdiary.example.de"))
        self.assertFalse(hostname_matches("*.example.de","example.de"))
        self.assertEqual(validate_certificate(cert,key,"petdiary.example.de")["hostname"],"petdiary.example.de")
        for hostname in ("https://petdiary.example.de", "*.example.de", "example.de:443", "sub.petdiary.example.de", "example.de"):
            with self.subTest(hostname=hostname),self.assertRaises(CertificateError):
                validate_certificate(cert,key,hostname)
        second,wrong_key=make_cert()
        with self.assertRaisesRegex(CertificateError,"nicht zusammen"):
            validate_certificate(cert,wrong_key,"petdiary.example.de")
        with self.assertRaisesRegex(CertificateError,"abgelaufen"):
            bad_cert,bad_key=make_cert(expired=True)
            validate_certificate(bad_cert,bad_key,"petdiary.example.de")
        with self.assertRaises(CertificateError):
            validate_certificate(cert,key,b"wrong-host".decode()+"#bad")
        with self.assertRaises(CertificateError):
            validate_certificate(cert+b"garbage",key,"petdiary.example.de")

    def test_atomic_store_and_key_permissions(self):
        cert,key=make_cert()
        self.assertIsNone(certificate_status(self.store))
        metadata=install_certificate(self.store,cert,key,"petdiary.example.de")
        current=self.store/"current"
        self.assertTrue(current.is_symlink())
        self.assertEqual((current/"privkey.pem").read_bytes(),key)
        self.assertEqual(stat.S_IMODE((current/"privkey.pem").stat().st_mode),0o600)
        self.assertEqual(stat.S_IMODE((current/"fullchain.pem").stat().st_mode),0o600)
        self.assertEqual(stat.S_IMODE(current.resolve().stat().st_mode),0o700)
        self.assertEqual(certificate_status(self.store)["hostname"],"petdiary.example.de")
        self.assertNotIn("private_key",json.dumps(metadata))
        before=current.readlink()
        other_cert,other_key=make_cert()
        with self.assertRaises(CertificateError):
            install_certificate(self.store,other_cert,key,"petdiary.example.de")
        self.assertEqual(current.readlink(),before)
        install_certificate(self.store,other_cert,other_key,"petdiary.example.de")
        self.assertNotEqual(current.readlink(),before)
        self.assertEqual((current/"privkey.pem").read_bytes(),other_key)
        self.assertEqual(len(list((self.store/"versions").iterdir())),2)

    def test_admin_upload_route_and_zip_exclusion(self):
        app=create_app({"TESTING":True,"DATA_DIR":self.tmp.name,"TLS_CERT_DIR":str(self.store)})
        client=app.test_client()
        client.get("/setup")
        with client.session_transaction() as sess: csrf=sess["csrf"]
        passwd="example-password-123"
        setup=client.post("/setup",data={"csrf":csrf,"username":"admin","password":passwd,"confirm_password":passwd})
        self.assertEqual(setup.status_code,303)
        client.get("/settings")
        with client.session_transaction() as sess: csrf=sess["csrf"]
        cert,key=make_cert()
        def upload(password, key_bytes=None, token=None):
            return client.post("/settings/https/certificate",
                data={"csrf":csrf if token is None else token,"hostname":"petdiary.example.de",
                    "current_password":password,
                    "fullchain":(io.BytesIO(cert),"fullchain.pem"),
                    "private_key":(io.BytesIO(key if key_bytes is None else key_bytes),"privkey.pem")},
                content_type="multipart/form-data")
        self.assertEqual(upload("incorrect").status_code,303)
        self.assertIsNone(certificate_status(self.store))
        self.assertEqual(upload(passwd,token="bogus").status_code,403)
        self.assertIsNone(certificate_status(self.store))
        self.assertEqual(upload(passwd,b"not a private key").status_code,303)
        self.assertIsNone(certificate_status(self.store))
        self.assertEqual(upload(passwd).status_code,303)
        status=certificate_status(self.store)
        self.assertEqual(status["hostname"],"petdiary.example.de")
        page=client.get("/settings").data
        self.assertIn(b"petdiary.example.de",page)
        self.assertNotIn(key,page)
        self.assertNotIn(cert,page)
        other=app.test_client()
        self.assertEqual(other.post("/settings/https/certificate").status_code,403)
        backup=client.post("/settings/backups/export",data={"csrf":csrf,"current_password":passwd})
        self.assertEqual(backup.status_code,200)
        with zipfile.ZipFile(io.BytesIO(backup.data)) as zipped:
            self.assertEqual(set(zipped.namelist()),{"manifest.json","petdiary.sqlite3"})
            self.assertNotIn(key,zipped.read("petdiary.sqlite3"))
            self.assertNotIn(key,zipped.read("manifest.json"))


if __name__=="__main__":
    unittest.main()
