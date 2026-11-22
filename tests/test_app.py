import base64
import io
import tempfile
import unittest
from datetime import date, timedelta
from app import create_app

class PetDiaryTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.app=create_app(dict(TESTING=True,DATA_DIR=self.tmp.name))
        self.client=self.app.test_client()
        self.password="test-password-123"
        self.auth={}
        self.refresh_csrf(self.client,"/setup")
        r=self.post("/setup",username="admin",password=self.password,confirm_password=self.password)
        self.assertEqual(r.status_code,303)
        self.refresh_csrf(self.client,"/")
        r=self.post("/settings",action="generate",current_password=self.password)
        import re
        token=re.search(rb'Neuer API-Token<input readonly value="([^"]+)"',r.data).group(1).decode()
        self.api={"Authorization":"Bearer "+token}

    def refresh_csrf(self,client,url):
        client.get(url)
        with client.session_transaction() as sess:
            self.csrf=sess["csrf"]

    def post(self,url,**data):
        return self.client.post(url,data={"csrf":self.csrf,**data})

    def pet(self,name="Milo"):
        r=self.post("/pets/new",name=name,species="Katze")
        self.assertEqual(r.status_code,303)
        return r.location

    def test_auth_and_csrf(self):
        self.assertEqual(self.app.test_client().get("/").location,"/login")
        self.assertEqual(self.client.get("/setup").location,"/")
        self.assertEqual(self.client.get("/healthz").status_code,200)
        self.assertEqual(self.client.get("/api/v1/reminders",headers=self.auth).status_code,401)
        self.assertEqual(self.client.post("/pets/new",data={"name":"X","species":"Katze"},headers=self.auth).status_code,403)

    def test_multi_pet_passport_and_reminders(self):
        a=self.pet("Milo")
        b=self.pet("Luna")
        due=(date.today()+timedelta(days=7)).isoformat()
        result=self.post(a+"/records/new",kind="vaccine",title="Tollwut",day=date.today().isoformat(),
                         vet="Dr. Test",batch="ABC123",valid_until=due)
        self.assertEqual(result.status_code,303)
        self.assertIn(b"ABC123",self.client.get(a+"?tab=passport",headers=self.auth).data)
        self.assertNotIn(b"ABC123",self.client.get(b,headers=self.auth).data)
        data=self.client.get("/api/v1/reminders",headers=self.api).get_json()
        self.assertEqual(data["count"],1)
        self.assertEqual(data["reminders"][0]["pet"],"Milo")
        rid=data["reminders"][0]["id"]
        self.assertEqual(self.post("/records/"+str(rid)+"/toggle").status_code,303)
        self.assertEqual(self.client.get("/api/v1/reminders",headers=self.api).get_json()["count"],0)
        self.assertEqual(self.post("/records/"+str(rid)+"/toggle").status_code,303)
        self.assertEqual(self.post(a+"/delete",confirm="Milo").status_code,303)
        self.assertEqual(self.client.get("/api/v1/reminders",headers=self.api).get_json()["count"],0)

    def test_inline_attachment_and_invalid_upload(self):
        a=self.pet()
        png=base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jR1sAAAAASUVORK5CYII=")
        payload=dict(kind="exam",title="Befund",day=date.today().isoformat())
        r=self.post(a+"/records/new",**payload,files=(io.BytesIO(png),"Befund.png"))
        self.assertEqual(r.status_code,303)
        self.assertIn(b"Befund.png",self.client.get(a,headers=self.auth).data)
        self.assertEqual(self.client.get("/attachments/1",headers=self.auth).status_code,200)
        response=self.client.get("/attachments/1/content",headers=self.auth)
        self.assertEqual(response.data,png)
        self.assertTrue(response.headers["Content-Disposition"].startswith("inline"))
        self.assertTrue(self.client.get("/attachments/1/content?download=1",headers=self.auth).headers["Content-Disposition"].startswith("attachment"))
        r=self.post(a+"/records/new",kind="exam",title="BadUpload",day=date.today().isoformat(),files=(io.BytesIO(b"<script>bad</script>"),"bad.html"))
        self.assertIn("Nur PDF".encode(),r.data)
        self.assertNotIn(b"BadUpload",self.client.get(a,headers=self.auth).data)

    def test_persistence(self):
        self.pet("Persistenz")
        app2=create_app(dict(TESTING=True,DATA_DIR=self.tmp.name))
        client=app2.test_client()
        self.assertEqual(client.get("/").location,"/login")
        self.refresh_csrf(client,"/login")
        self.assertEqual(client.post("/login",data={"csrf":self.csrf,"username":"admin","password":self.password}).status_code,303)
        self.assertIn(b"Persistenz",client.get("/").data)
        self.assertEqual(client.get("/api/v1/reminders",headers=self.api).status_code,200)

    def test_setup_login_token_rotation_logout(self):
        other=self.app.test_client()
        self.assertEqual(other.get("/setup").location,"/login")
        r=self.post("/settings",action="revoke",current_password=self.password)
        self.assertEqual(r.status_code,200)
        self.assertEqual(self.client.get("/api/v1/reminders",headers=self.api).status_code,401)
        self.assertEqual(self.post("/logout").location,"/login")
        self.assertEqual(self.client.get("/").location,"/login")
        self.refresh_csrf(self.client,"/login")
        self.assertEqual(self.post("/login",username="admin",password="wrong").status_code,401)
        self.assertEqual(self.post("/login",username="admin",password=self.password).location,"/")

    def test_profile_suggestions_and_photo(self):
        png=base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jR1sAAAAASUVORK5CYII=")
        r=self.post("/pets/new",name="Custom",species="Eigene Tierart",breed="Eigene Rasse",color="Eigene Farbe",
                    sex="Eigene Angabe",features="Weißer Fleck",chip_location="Eigene Position",
                    tattoo_location="Eigene Tattoo-Position",photo=(io.BytesIO(png),"photo.png"))
        self.assertEqual(r.status_code,303)
        p=r.location
        self.assertEqual(self.client.get(p+"/photo").data,png)
        self.assertEqual(self.app.test_client().get(p+"/photo").location,"/login")
        self.assertIn("Eigene Rasse".encode(),self.client.get(p+"/edit").data)
        self.assertIn("Weißer Fleck".encode(),self.client.get(p+"/edit").data)
        self.assertEqual(self.post(p+"/edit",name="Custom",species="Eigene Tierart",remove_photo="yes").status_code,303)
        self.assertEqual(self.client.get(p+"/photo").status_code,404)

    def test_medication_schedule_and_checks(self):
        p=self.pet("Milo")
        self.pet("Luna")
        day="2026-12-01"
        r=self.post(p+"/records/new",kind="med",title="Testplan",day=day,product="Eigenes Präparat",
                    dose="0,5",dose_unit="ml",duration="14",dose_clock=["08:00","20:00"])
        self.assertEqual(r.status_code,303)
        url="/api/v1/medications?start="+day+"&days=14"
        result=self.client.get(url,headers=self.api).get_json()
        self.assertEqual(result["count"],28)
        self.assertEqual(result["medications"][0]["pet"],"Milo")
        self.assertEqual(result["medications"][-1]["day"],"2026-12-14")
        rid=result["medications"][0]["record_id"]
        self.assertIn("Eigenes Präparat".encode(),self.client.get(p+"/records/new").data)
        self.assertIn("Eigenes Präparat".encode(),self.client.get("/?week="+day).data)
        self.assertEqual(self.post(f"/medications/{rid}/check",day=day,clock="08:00",action="mark").status_code,303)
        self.assertEqual(self.client.get(url,headers=self.api).get_json()["count"],27)
        self.assertEqual(self.post(f"/medications/{rid}/check",day=day,clock="08:00",action="undo").status_code,303)
        self.assertEqual(self.client.get(url,headers=self.api).get_json()["count"],28)
        self.assertEqual(self.post(f"/medications/{rid}/check",day=day,clock="09:00",action="mark").status_code,400)
        self.assertEqual(self.client.get(url).status_code,401)
        self.assertEqual(self.client.get("/api/v1/medications?days=32",headers=self.api).status_code,400)

    def test_custom_product_overrides_selection(self):
        p=self.pet()
        form=self.client.get(p+"/records/new?kind=med").data
        self.assertIn(b"Milpro 16 mg/40 mg",form)
        self.assertIn(b"product_custom",form)
        r=self.post(p+"/records/new",kind="med",title="Test",day="2026-12-01",product="Milpro",
                    product_custom="Eigene Variante 123",dose="1",dose_unit="Tablette",duration="1",dose_clock="08:00")
        self.assertEqual(r.status_code,303)
        result=self.client.get("/api/v1/medications?start=2026-12-01&days=1",headers=self.api).get_json()
        self.assertEqual(result["medications"][0]["product"],"Eigene Variante 123")
        self.assertIn(b"Eigene Variante 123",self.client.get(p+"/records/new").data)

    def test_password_recovery_preserves_data_and_revokes_sessions(self):
        from pathlib import Path
        from reset_password import reset_password
        a=self.pet("Recovery")
        self.assertEqual(self.post(a+"/records/new",kind="note",title="Behalten",day="2026-12-01").status_code,303)
        path=Path(self.tmp.name)/"petdiary.sqlite3"
        with self.assertRaises(ValueError):
            reset_password(path,"short")
        self.assertEqual(reset_password(path,"new-password-1234"),"admin")
        self.assertEqual(self.client.get("/").location,"/login")
        self.refresh_csrf(self.client,"/login")
        self.assertEqual(self.post("/login",username="admin",password=self.password).status_code,401)
        self.assertEqual(self.post("/login",username="admin",password="new-password-1234").location,"/")
        self.assertIn(b"Recovery",self.client.get("/").data)
        self.assertIn(b"Behalten",self.client.get(a).data)
        self.assertEqual(self.client.get("/api/v1/reminders",headers=self.api).status_code,200)

    def test_given_medication_without_clock_duration(self):
        p=self.pet()
        r=self.post(p+"/records/new",kind="med",title="Praxisgabe",day="2026-12-01",
                    product="Test A",dose="1",dose_unit="ml")
        self.assertEqual(r.status_code,303)
        self.assertIn(b"Verabreicht",self.client.get(p).data)
        self.assertEqual(self.client.get("/api/v1/medications?start=2026-12-01&days=1",headers=self.api).get_json()["count"],0)

    def test_multiple_meds_per_visit_and_edit(self):
        p=self.pet()
        form=dict(kind="visit",title="Tierarztbesuch",day="2026-12-01",vet="Test",
                  extra_present="1",extra_key=["0","1","2"],
                  extra_0_product="Praxis A",extra_0_dose="1",extra_0_dose_unit="ml",extra_0_mode="given",
                  extra_1_product="Plan B",extra_1_day="2026-12-02",extra_1_mode="plan",
                  extra_1_dose="1",extra_1_dose_unit="Tablette",extra_1_duration="2",extra_1_clock=["08:00","20:00"],
                  extra_2_product="Plan C",extra_2_day="2026-12-03",extra_2_mode="plan",
                  extra_2_dose="0,5",extra_2_dose_unit="ml",extra_2_duration="3")
        self.assertEqual(self.post(p+"/records/new",**form).status_code,303)
        url="/api/v1/medications?start=2026-12-01&days=7"
        result=self.client.get(url,headers=self.api).get_json()
        self.assertEqual(result["count"],7)
        self.assertEqual({m["product"] for m in result["medications"]},{"Plan B","Plan C"})
        b=next(m for m in result["medications"] if m["product"]=="Plan B")
        c=next(m for m in result["medications"] if m["product"]=="Plan C")
        self.assertEqual(b["entry_id"],c["entry_id"])
        self.assertNotEqual(b["record_id"],c["record_id"])
        self.assertIsNone(c["scheduled_at"])
        self.assertEqual(c["time"],"")
        self.assertIn(b"Praxis A",self.client.get(p+"?kind=med").data)
        self.assertIn(b"Ohne Uhrzeit",self.client.get("/?week=2026-12-01").data)
        self.assertEqual(self.post(f"/medications/{c['record_id']}/check",day=c["day"],clock="",action="mark").status_code,303)
        self.assertEqual(self.client.get(url,headers=self.api).get_json()["count"],6)
        entry=b["entry_id"]
        edit=p+f"/records/{entry}/edit"
        self.assertEqual(self.client.get(edit).status_code,200)
        import sqlite3
        from pathlib import Path
        with sqlite3.connect(Path(self.tmp.name)/"petdiary.sqlite3") as con:
            a=con.execute("SELECT id FROM records WHERE product='Praxis A'").fetchone()[0]
        form.update(extra_0_id=str(a),extra_1_id=str(b["record_id"]),extra_2_id=str(c["record_id"]),notes="Kontrolle")
        self.assertEqual(self.post(edit,**form).status_code,303)
        self.assertEqual(self.client.get(url,headers=self.api).get_json()["count"],6)
        form["extra_key"]=["0","2"]
        self.assertEqual(self.post(edit,**form).status_code,303)
        self.assertEqual(self.client.get(url,headers=self.api).get_json()["count"],2)
        self.assertEqual(self.post(f"/records/{entry}/delete").status_code,303)
        self.assertEqual(self.client.get(url,headers=self.api).get_json()["count"],0)

    def test_validation_keeps_unsaved_extra_fields(self):
        p=self.pet()
        r=self.post(p+"/records/new",kind="visit",title="",day="2026-12-01",
                    extra_present="1",extra_key="0",extra_0_product="Ungespeicherte Gabe",extra_0_mode="given")
        self.assertEqual(r.status_code,200)
        self.assertIn(b"Ungespeicherte Gabe",r.data)
        self.assertNotIn(b"Ungespeicherte Gabe",self.client.get(p).data)

    def test_expanded_catalog_species_and_persistence(self):
        from catalog import ANIMAL_PRODUCT_LISTS, PRODUCTS, product_suggestions
        self.assertEqual(len(ANIMAL_PRODUCT_LISTS["Katze"]),343)
        self.assertEqual(len(ANIMAL_PRODUCT_LISTS["Hund"]),468)
        self.assertEqual(len(PRODUCTS),607)
        self.assertEqual(len({p.casefold() for p in PRODUCTS}),len(PRODUCTS))
        cats,cat_hints=product_suggestions(PRODUCTS,"Katze")
        dogs,dog_hints=product_suggestions(PRODUCTS,"Hund")
        self.assertLess(cats.index("Bonqat"),cats.index("Advantix"))
        self.assertLess(dogs.index("Advantix"),dogs.index("Bonqat"))
        self.assertIn("Nicht in der Katze-Liste",cat_hints["Advantix"])
        self.assertIn("Humanarzneimittel",cat_hints["Gabapentin"])
        self.assertIn("Ergänzung",dog_hints["Adaptil"])
        self.assertIn("Zulassung prüfen",dog_hints["Acepromazin"])
        self.assertIn("Milpro 16 mg/40 mg – Filmtabletten für Katzen",cats)
        pet=self.pet("Katalog")
        form=self.client.get(pet+"/records/new?kind=med").data
        self.assertIn(b'value="Bonqat"',form)
        self.assertIn(b'value="Advantix" data-hint="Nicht in der Katze-Liste',form)
        self.assertNotIn(b'value="Gabapentin**"',form)
        self.assertEqual(self.post(pet+"/records/new",kind="med",title="Dokumentation",day="2026-12-01",product="Eigene unveraenderte Variante").status_code,303)
        app2=create_app(dict(TESTING=True,DATA_DIR=self.tmp.name))
        client=app2.test_client()
        self.refresh_csrf(client,"/login")
        self.assertEqual(client.post("/login",data={"csrf":self.csrf,"username":"admin","password":self.password}).status_code,303)
        self.assertIn(b"Eigene unveraenderte Variante",client.get(pet+"/records/new?kind=med").data)

    def test_reminder_horizon_365_days(self):
        from datetime import datetime
        from zoneinfo import ZoneInfo
        p=self.pet("Jahresvorschau")
        today=datetime.now(ZoneInfo("Europe/Berlin")).date()
        for offset,title in [(-1,"VergangenTest"),(180,"HalbjahrTest"),(365,"GrenzeTest"),(366,"AusserhalbTest")]:
            due=(today+timedelta(days=offset)).isoformat()
            self.assertEqual(self.post(p+"/records/new",kind="reminder",title=title,
                                       day=today.isoformat(),due=due).status_code,303)
        for suffix in ("", "?days=365"):
            response=self.client.get("/api/v1/reminders"+suffix,headers=self.api)
            self.assertEqual(response.status_code,200)
            result=response.get_json()
            self.assertEqual(result["count"],3)
            self.assertEqual(result["overdue"],1)
            self.assertEqual({r["title"] for r in result["reminders"]},
                             {"VergangenTest","HalbjahrTest","GrenzeTest"})
        short=self.client.get("/api/v1/reminders?days=30",headers=self.api).get_json()
        self.assertEqual(short["count"],1)
        self.assertEqual(short["reminders"][0]["title"],"VergangenTest")
        dashboard=self.client.get("/").data
        self.assertIn("In den nächsten 365 Tagen".encode(),dashboard)
        self.assertIn(b"HalbjahrTest",dashboard)
        self.assertIn(b"GrenzeTest",dashboard)
        self.assertNotIn(b"AusserhalbTest",dashboard)
        self.assertIn(b"AusserhalbTest",self.client.get("/reminders").data)
        self.assertIn(b"?days=365",self.client.get("/settings").data)


    def make_portable_backup(self):
        response=self.client.post("/settings/backups/export",
            data={"csrf":self.csrf,"current_password":self.password},
            headers={"Accept":"application/json"})
        self.assertEqual(response.status_code,200,response.get_data(as_text=True)[:300] if response.status_code!=200 else "")
        self.assertIn("application/zip",response.content_type)
        self.assertIn("petdiary-backup-",response.headers["Content-Disposition"])
        result=response.data
        response.close()
        return result

    def test_portable_backup_roundtrip_and_destination_credentials(self):
        import hashlib
        import json
        import sqlite3
        import zipfile
        from pathlib import Path
        a=self.pet("Kopie")
        png=base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jR1sAAAAASUVORK5CYII=")
        self.assertEqual(self.post(a+"/records/new",kind="exam",title="Bild im Befund",
                                  day="2026-11-20",files=(io.BytesIO(png),"bild.png")).status_code,303)
        self.assertEqual(self.post(a+"/records/new",kind="med",title="Plan",day="2026-11-20",
                                  product="Eigene Tablette",dose="1",dose_unit="Tablette",duration="3",
                                  dose_clock=["08:00","20:00"]).status_code,303)
        med=self.client.get("/api/v1/medications?start=2026-11-20&days=3",headers=self.api).get_json()
        self.assertEqual(med["count"],6)
        rid=med["medications"][0]["record_id"]
        self.assertEqual(self.post(f"/medications/{rid}/check",day="2026-11-20",clock="08:00",action="mark").status_code,303)
        with sqlite3.connect(Path(self.tmp.name)/"petdiary.sqlite3") as con:
            secret=con.execute("SELECT value FROM app_settings WHERE key='session_secret'").fetchone()[0]
            tokenhash=con.execute("SELECT value FROM app_settings WHERE key='api_token_hash'").fetchone()[0]
            pwdhash=con.execute("SELECT password_hash FROM admin_account").fetchone()[0]
        self.assertEqual(self.post("/costs/new",pet_id=a.split("/")[-1],record_id="1",day="2026-11-20",
                                  category="vet",title="Rechnung",amount="125,50",refund="50,25",notes="").status_code,303)
        exported=self.make_portable_backup()
        with zipfile.ZipFile(io.BytesIO(exported)) as archive:
            self.assertEqual(set(archive.namelist()),{"manifest.json","petdiary.sqlite3"})
            meta=json.loads(archive.read("manifest.json"))
            raw=archive.read("petdiary.sqlite3")
            self.assertEqual(meta["schema_version"],3)
            self.assertEqual(meta["app_version"],"0.0.6")
            self.assertEqual(hashlib.sha256(raw).hexdigest(),meta["database_sha256"])
            self.assertEqual(meta["counts"]["attachments"],1)
            self.assertEqual(meta["counts"]["costs"],1)
            self.assertEqual(meta["counts"]["cost_records"],1)
            self.assertNotIn(secret.encode(),raw)
            self.assertNotIn(tokenhash.encode(),raw)
            self.assertNotIn(pwdhash.encode(),raw)
            dbfile=Path(self.tmp.name)/"export-inspect.sqlite3"
            dbfile.write_bytes(raw)
            with sqlite3.connect(dbfile) as con:
                self.assertEqual(con.execute("SELECT count(*) FROM admin_account").fetchone()[0],0)
                self.assertEqual(con.execute("SELECT count(*) FROM app_settings").fetchone()[0],0)
                self.assertEqual(con.execute("SELECT count(*) FROM attachments").fetchone()[0],1)
                self.assertEqual(con.execute("PRAGMA user_version").fetchone()[0],3)
        with tempfile.TemporaryDirectory() as newdir:
            newapp=create_app(dict(TESTING=True,DATA_DIR=newdir))
            other=newapp.test_client()
            other.get("/setup")
            with other.session_transaction() as sess:
                csrftoken=sess["csrf"]
            newpass="different-admin-pass123"
            self.assertEqual(other.post("/setup",data={"csrf":csrftoken,"username":"different",
                "password":newpass,"confirm_password":newpass}).status_code,303)
            # Creating the session rotates the CSRF secret.
            other.get("/settings")
            with other.session_transaction() as sess:
                csrftoken=sess["csrf"]
            response=other.post("/settings",data={"csrf":csrftoken,"action":"generate",
                     "current_password":newpass})
            import re
            other_token=re.search(rb'Neuer API-Token<input readonly value="([^"]+)"',response.data).group(1).decode()
            self.assertEqual(other.post("/pets/new",data={"csrf":csrftoken,"name":"Alter Bestand",
                              "species":"Hund"}).status_code,303)
            imported=other.post("/settings/backups/import",
                 data={"csrf":csrftoken,"current_password":newpass,"confirm_text":"ERSETZEN",
                       "confirm_overwrite":"yes","backup":(io.BytesIO(exported),"petdiary.zip")},
                 headers={"Accept":"application/json"})
            self.assertEqual(imported.status_code,200,imported.get_data(as_text=True))
            data=imported.get_json()
            self.assertTrue(data["ok"])
            self.assertEqual(data["imported"]["pets"],1)
            self.assertEqual(data["imported"]["records"],2)
            self.assertEqual(data["imported"]["attachments"],1)
            self.assertEqual(data["imported"]["costs"],1)
            self.assertIn("75,25 €".encode(),other.get("/costs?year=2026").data)
            self.assertIn(b"Kopie",other.get("/").data)
            self.assertNotIn(b"Alter Bestand",other.get("/").data)
            self.assertEqual(other.get("/attachments/1/content").data,png)
            checks=other.get("/api/v1/medications?start=2026-11-20&days=3",
                  headers={"Authorization":"Bearer "+other_token}).get_json()
            self.assertEqual(checks["count"],5)
            self.assertEqual(other.get("/api/v1/reminders",headers=self.api).status_code,401)
            with sqlite3.connect(Path(newdir)/"petdiary.sqlite3") as con:
                self.assertEqual(con.execute("SELECT username FROM admin_account").fetchone()[0],"different")
            safety=Path(newdir)/".petdiary-safety-backups"/data["safety_backup"]
            self.assertTrue(safety.is_file())
            with sqlite3.connect(safety) as con:
                self.assertEqual(con.execute("SELECT name FROM pets").fetchone()[0],"Alter Bestand")
                self.assertEqual(con.execute("SELECT username FROM admin_account").fetchone()[0],"different")
            self.assertEqual(other.get("/healthz").status_code,200)

    def test_portable_restore_validation_keeps_existing_data(self):
        import hashlib
        import json
        import sqlite3
        import zipfile
        from pathlib import Path
        self.pet("Sicher behalten")
        exported=self.make_portable_backup()
        with zipfile.ZipFile(io.BytesIO(exported)) as source:
            manifest=json.loads(source.read("manifest.json"))
            database=source.read("petdiary.sqlite3")
        def modified_zip(meta, payload=database, badname=None):
            buff=io.BytesIO()
            with zipfile.ZipFile(buff,"w",compression=zipfile.ZIP_DEFLATED) as target:
                target.writestr("manifest.json",json.dumps(meta))
                target.writestr(badname or "petdiary.sqlite3",payload)
            return buff.getvalue()
        cases=[
            ("wrong-hash.zip",modified_zip({**manifest,"database_sha256":"0"*64})),
            ("future-schema.zip",modified_zip({**manifest,"schema_version":99})),
            ("traversal.zip",modified_zip(manifest,badname="../petdiary.sqlite3")),
            ("not-zip.zip",b"invalid zip"),
        ]
        for filename,data in cases:
            response=self.client.post("/settings/backups/import",
                data={"csrf":self.csrf,"current_password":self.password,"confirm_text":"ERSETZEN",
                     "confirm_overwrite":"yes","backup":(io.BytesIO(data),filename)},
                headers={"Accept":"application/json"})
            self.assertEqual(response.status_code,400,(filename,response.get_data(as_text=True)))
            self.assertIn(b"Sicher behalten",self.client.get("/").data)
        safety=Path(self.tmp.name)/".petdiary-safety-backups"
        self.assertFalse(safety.exists())
        wrong=self.client.post("/settings/backups/export",
            data={"csrf":self.csrf,"current_password":"not-right"},
            headers={"Accept":"application/json"})
        self.assertEqual(wrong.status_code,403)
        self.assertEqual(self.client.post("/settings/backups/export",
            data={"current_password":self.password}).status_code,403)

    def test_portable_restore_rolls_back_failed_insert(self):
        import sqlite3
        import backups
        from pathlib import Path
        self.pet("Vorher")
        exported=self.make_portable_backup()
        # Simulate an unexpected failure while replacing rows.
        original=backups._replace_data
        def fail_after_delete(source,database,default_products):
            dest=sqlite3.connect(database)
            try:
                with dest:
                    dest.execute("PRAGMA foreign_keys=ON")
                    dest.execute("DELETE FROM pets")
                    raise sqlite3.IntegrityError("forced failure")
            finally:
                dest.close()
        from unittest.mock import patch
        with patch("backups._replace_data",side_effect=fail_after_delete):
            response=self.client.post("/settings/backups/import",
                data={"csrf":self.csrf,"current_password":self.password,"confirm_text":"ERSETZEN",
                     "confirm_overwrite":"yes","backup":(io.BytesIO(exported),"valid.zip")},
                headers={"Accept":"application/json"})
        self.assertEqual(response.status_code,400,response.get_data(as_text=True))
        self.assertIn(b"Vorher",self.client.get("/").data)
        self.assertEqual(self.client.get("/healthz").status_code,200)


    def test_costs_validation_filters_and_delete(self):
        a=self.pet("Kostenkatze")
        b=self.pet("AnderesTier")
        pid=a.split("/")[-1]
        other=b.split("/")[-1]
        self.assertEqual(self.post(a+"/records/new",kind="visit",title="Rechnung",
                                  day="2026-11-20").status_code,303)
        data=dict(pet_id=pid,record_id="1",day="2026-11-20",category="vet",title="Praxis",
                  amount="125,50",refund="50,25",notes="Beleg")
        self.assertEqual(self.post("/costs/new",**data).status_code,303)
        self.assertEqual(self.post("/costs/new",**{**data,"record_id":"","pet_id":other,
                         "day":"2025-01-01","title":"Futter","category":"food","amount":"10.10","refund":""}).status_code,303)
        for invalid in ({"amount":"-1"},{"amount":"1.001"},{"amount":"NaN"},{"refund":"999"},
                        {"pet_id":other},{"category":"bad"},{"day":"2026-02-30"}):
            self.assertEqual(self.post("/costs/new",**{**data,**invalid}).status_code,200)
        page=self.client.get("/costs?year=2026&pet="+pid)
        self.assertIn("125,50 €".encode(),page.data)
        self.assertIn("75,25 €".encode(),page.data)
        self.assertNotIn(b"Futter</h3>",page.data)
        self.assertIn(b"Praxis",page.data)
        self.assertIn("135,60 €".encode(),self.client.get("/costs?year=all").data)
        self.assertEqual(self.post("/costs/1/edit",**{**data,"refund":"100"}).status_code,303)
        self.assertIn("25,50 €".encode(),self.client.get("/costs?year=2026").data)
        self.assertEqual(self.post("/costs/1/delete",confirm="yes").status_code,303)
        self.assertNotIn(b"Praxis",self.client.get("/costs?year=2026").data)
        self.assertEqual(self.client.get("/costs/1/edit").status_code,404)
        self.assertEqual(self.client.get("/costs?year=invalid").status_code,400)
        self.assertEqual(self.client.post("/costs/new",data=data).status_code,403)

    def test_multiple_cost_links_and_legacy_migration(self):
        import sqlite3
        from pathlib import Path
        from backups import create_portable_backup
        a=self.pet("Mehrfach")
        b=self.pet("Anderes Tier")
        for url,title in ((a,"Impfung A"),(a,"Entwurmung B"),(b,"Fremd C")):
            self.assertEqual(self.post(url+"/records/new",kind="visit",title=title,day="2026-11-20").status_code,303)
        data=dict(pet_id=a.split("/")[-1],record_id=["1","2","2"],day="2026-11-20",
                  category="vet",title="Sammelrechnung",amount="120",refund="20",notes="")
        self.assertEqual(self.post("/costs/new",**data).status_code,303)
        view=self.client.get("/costs?year=all").data
        self.assertIn(b"Impfung A",view)
        self.assertIn(b"Entwurmung B",view)
        self.assertIn("120,00 €".encode(),view)
        self.assertNotIn("240,00 €".encode(),view)
        self.assertEqual(self.post("/costs/1/edit",**{**data,"record_id":["1","3"]}).status_code,200)
        root=Path(self.tmp.name)
        dbpath=root/"petdiary.sqlite3"
        with sqlite3.connect(dbpath) as con:
            self.assertEqual(con.execute("SELECT record_id FROM cost_records ORDER BY record_id").fetchall(),[(1,),(2,)])
        exported=self.make_portable_backup()
        self.assertEqual(self.post("/costs/1/edit",**{**data,"record_id":["2"]}).status_code,303)
        result=self.client.post("/settings/backups/import",data={"csrf":self.csrf,"current_password":self.password,
            "confirm_text":"ERSETZEN","confirm_overwrite":"yes","backup":(io.BytesIO(exported),"multi.zip")},
            headers={"Accept":"application/json"})
        self.assertEqual(result.status_code,200,result.get_data(as_text=True))
        with sqlite3.connect(dbpath) as con:
            self.assertEqual(con.execute("SELECT record_id FROM cost_records ORDER BY record_id").fetchall(),[(1,),(2,)])
        # Simulate an older 0.0.6 single-link backup.
        legacy=root/"legacy2.sqlite3"
        src=sqlite3.connect(dbpath)
        dst=sqlite3.connect(legacy)
        src.backup(dst)
        src.close()
        with dst:
            dst.execute("DROP TABLE cost_records")
            dst.execute("UPDATE costs SET record_id=1")
            dst.execute("PRAGMA user_version=2")
        dst.close()
        temporary,archive,_=create_portable_backup(legacy,root,"0.0.6")
        try:
            payload=archive.read_bytes()
        finally:
            temporary.cleanup()
        result=self.client.post("/settings/backups/import",data={"csrf":self.csrf,"current_password":self.password,
            "confirm_text":"ERSETZEN","confirm_overwrite":"yes","backup":(io.BytesIO(payload),"legacy2.zip")},
            headers={"Accept":"application/json"})
        self.assertEqual(result.status_code,200,result.get_data(as_text=True))
        with sqlite3.connect(dbpath) as con:
            self.assertEqual(con.execute("SELECT record_id FROM cost_records").fetchall(),[(1,)])
            self.assertEqual(con.execute("SELECT cents,record_id FROM costs").fetchone(),(12000,None))
        # Starting an existing single-link database also migrates it once.
        create_app(dict(TESTING=True,DATA_DIR=str(root)))
        with sqlite3.connect(dbpath) as con:
            self.assertEqual(con.execute("SELECT record_id FROM cost_records").fetchall(),[(1,)])
    
    def test_pdf_download_is_private(self):
        a=self.pet("Müller & Katze")
        self.assertEqual(self.post(a+"/records/new",kind="exam",title="Lunge < Befund",
                                  day="2026-11-20",notes="Zeile & Text\n"+"Beschreibung "*1500).status_code,200)
        self.assertEqual(self.post(a+"/records/new",kind="exam",title="Lunge < Befund",
                                  day="2026-11-20",notes="Zeile & Text\n"+"Beschreibung "*650).status_code,303)
        pdf=self.client.get(a+"/health-record.pdf")
        self.assertEqual(pdf.status_code,200)
        self.assertEqual(pdf.mimetype,"application/pdf")
        self.assertTrue(pdf.data.startswith(b"%PDF-"))
        self.assertIn("attachment",pdf.headers["Content-Disposition"])
        self.assertEqual(self.app.test_client().get(a+"/health-record.pdf").status_code,303)
        self.assertEqual(self.client.get("/pets/99999/health-record.pdf").status_code,404)
        self.assertIn(b"theme-choice",self.client.get("/settings").data)

    def test_legacy_schema_one_backup_import(self):
        import sqlite3,json,zipfile
        from pathlib import Path
        from backups import create_portable_backup
        self.pet("Legacy")
        root=Path(self.tmp.name)
        legacy=root/"legacy.sqlite3"
        source=sqlite3.connect(root/"petdiary.sqlite3")
        dest=sqlite3.connect(legacy)
        source.backup(dest)
        source.close()
        with dest:
            dest.execute("DROP TABLE cost_records")
            dest.execute("DROP TABLE costs")
            dest.execute("PRAGMA user_version=1")
        dest.close()
        temporary,archive,counts=create_portable_backup(legacy,root,"0.0.5")
        try:
            data=archive.read_bytes()
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                self.assertEqual(json.loads(z.read("manifest.json"))["schema_version"],1)
        finally:
            temporary.cleanup()
        self.assertEqual(self.post("/costs/new",pet_id="1",record_id="",day="2026-11-20",
                                  category="vet",title="Vor Import",amount="3",refund="",notes="").status_code,303)
        response=self.client.post("/settings/backups/import",
             data={"csrf":self.csrf,"current_password":self.password,"confirm_text":"ERSETZEN",
                   "confirm_overwrite":"yes","backup":(io.BytesIO(data),"legacy.zip")},
             headers={"Accept":"application/json"})
        self.assertEqual(response.status_code,200,response.get_data(as_text=True))
        self.assertEqual(response.get_json()["imported"]["costs"],0)
        self.assertIn(b"Legacy",self.client.get("/").data)
        self.assertNotIn(b"Vor Import",self.client.get("/costs?year=all").data)

if __name__=="__main__":
    unittest.main()
