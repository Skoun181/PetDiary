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
        self.app=create_app(dict(TESTING=True,DATA_DIR=self.tmp.name,ADMIN_PASSWORD="test-password-123",API_TOKEN="a"*32,SECRET_KEY="b"*32))
        self.client=self.app.test_client()
        self.auth={"Authorization":"Basic "+base64.b64encode(b"admin:test-password-123").decode()}
        self.api={"Authorization":"Bearer "+"a"*32}
        self.client.get("/",headers=self.auth)
        with self.client.session_transaction() as s:
            self.csrf=s["csrf"]

    def post(self,url,**data):
        return self.client.post(url,data={"csrf":self.csrf,**data},headers=self.auth)

    def pet(self,name="Milo"):
        r=self.post("/pets/new",name=name,species="Katze")
        self.assertEqual(r.status_code,303)
        return r.location

    def test_auth_and_csrf(self):
        self.assertEqual(self.client.get("/").status_code,401)
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
        app2=create_app(dict(TESTING=True,DATA_DIR=self.tmp.name,ADMIN_PASSWORD="test-password-123",API_TOKEN="a"*32,SECRET_KEY="b"*32))
        self.assertIn(b"Persistenz",app2.test_client().get("/",headers=self.auth).data)

if __name__=="__main__":
    unittest.main()
