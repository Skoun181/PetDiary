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

if __name__=="__main__":
    unittest.main()
