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

if __name__=="__main__":
    unittest.main()
