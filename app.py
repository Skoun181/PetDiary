import os
import hmac
import secrets
import hashlib
import time
import threading
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from contextlib import contextmanager
from pathlib import Path
from flask import Flask, abort, request, render_template, redirect, url_for, jsonify, flash, session
from io import BytesIO
from flask import send_file

CATEGORIES = {"visit":"Termin", "vaccine":"Impfung", "exam":"Untersuchung", "lab":"Labor/Befund", "med":"Medikament", "worm":"Entwurmung", "weight":"Gewicht", "food":"Ernährung", "note":"Notiz", "reminder":"Erinnerung", "titer":"Tollwut-Antikörpertest", "parasite":"Parasitenbehandlung"}
PET_FIELDS = ["name","species","breed","birth","sex","color","chip","chip_date","chip_location","tattoo","owner","owner_contact","passport","issuer","issued"]
RECORD_FIELDS = ["kind","title","day","vet","notes","product","batch","valid_from","valid_until","due","weight"]
MAX_FILE = 10 * 1024 * 1024
SCHEMA = """
CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS admin_account (id INTEGER PRIMARY KEY CHECK(id=1), username TEXT NOT NULL, password_hash TEXT NOT NULL, session_version TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS pets (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL, species TEXT NOT NULL, breed TEXT, birth TEXT, sex TEXT, color TEXT,
 chip TEXT, chip_date TEXT, chip_location TEXT, tattoo TEXT, owner TEXT, owner_contact TEXT, passport TEXT, issuer TEXT, issued TEXT
);
CREATE TABLE IF NOT EXISTS records (
 id INTEGER PRIMARY KEY, pet_id INTEGER NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
 kind TEXT NOT NULL, title TEXT NOT NULL, day TEXT NOT NULL, vet TEXT, notes TEXT, product TEXT, batch TEXT,
 valid_from TEXT, valid_until TEXT, due TEXT, weight TEXT, done INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS records_pet_day ON records(pet_id, day DESC, id DESC);
CREATE INDEX IF NOT EXISTS records_due ON records(done, due);
CREATE TABLE IF NOT EXISTS attachments (
 id INTEGER PRIMARY KEY, record_id INTEGER NOT NULL REFERENCES records(id) ON DELETE CASCADE,
 name TEXT NOT NULL, mime TEXT NOT NULL, data BLOB NOT NULL
);
CREATE INDEX IF NOT EXISTS attachments_record ON attachments(record_id);
"""

def create_app(config=None):
    app = Flask(__name__)
    app.config.update(DATA_DIR=os.getenv("DATA_DIR", "/data"),
        TZ=os.getenv("TZ","Europe/Berlin"), MAX_CONTENT_LENGTH=55*1024*1024,
        SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Strict",
        SESSION_COOKIE_SECURE=os.getenv("COOKIE_SECURE","0")=="1",
        PERMANENT_SESSION_LIFETIME=timedelta(days=7))
    if config:
        app.config.update(config)
    tz = ZoneInfo(app.config["TZ"])
    folder = Path(app.config["DATA_DIR"])
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "petdiary.sqlite3"

    @contextmanager
    def db():
        con = sqlite3.connect(path, timeout=10)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        con.execute("PRAGMA busy_timeout=10000")
        try:
            with con:
                yield con
        finally:
            con.close()

    with db() as con:
        con.execute("PRAGMA journal_mode=WAL")
        con.executescript(SCHEMA)
        con.execute("INSERT OR IGNORE INTO app_settings VALUES ('session_secret',?)",(secrets.token_hex(32),))
        app.secret_key=con.execute("SELECT value FROM app_settings WHERE key='session_secret'").fetchone()[0]
        # Import old credentials once, when upgrading from the initial ENV version.
        old_password=os.getenv("ADMIN_PASSWORD","")
        if old_password and not con.execute("SELECT 1 FROM admin_account").fetchone():
            con.execute("INSERT OR IGNORE INTO admin_account VALUES (1,?,?,?)",
                        (os.getenv("ADMIN_USER","admin"),generate_password_hash(old_password),secrets.token_hex(16)))
            old_token=os.getenv("API_TOKEN","")
            if old_token:
                con.execute("INSERT OR IGNORE INTO app_settings VALUES ('api_token_hash',?)",
                            (hashlib.sha256(old_token.encode()).hexdigest(),))
        existing=con.execute("SELECT 1 FROM pets LIMIT 1").fetchone()
        if existing and not con.execute("SELECT 1 FROM admin_account").fetchone():
            raise RuntimeError("Bestehende Tierdaten ohne Admin-Konto. Beim ersten Upgrade alte ADMIN_USER/ADMIN_PASSWORD einmalig bereitstellen.")
    login_lock=threading.Lock()
    failures=[]

    def today():
        return datetime.now(tz).date()

    def equal(a,b):
        return hmac.compare_digest(str(a).encode(),str(b).encode())

    def csrf():
        if "csrf" not in session:
            session["csrf"] = os.urandom(32).hex()
        return session["csrf"]

    def account():
        with db() as con:
            return con.execute("SELECT * FROM admin_account WHERE id=1").fetchone()

    def signed_in(a):
        return a is not None and equal(session.get("version",""),a["session_version"])

    def start_session(a):
        session.clear()
        session["version"]=a["session_version"]
        session.permanent=True

    def new_credentials():
        username=request.form.get("username","").strip()
        password=request.form.get("password","")
        if not 1<=len(username)<=80 or not 12<=len(password)<=256:
            raise ValueError("Benutzername (1–80 Zeichen) und Passwort (12–256 Zeichen) angeben.")
        if password!=request.form.get("confirm_password",""):
            raise ValueError("Die Passwörter stimmen nicht überein.")
        return username,password

    @app.before_request
    def auth():
        if request.endpoint in ("health","static"):
            return
        if request.path.startswith("/api/"):
            with db() as con:
                token=con.execute("SELECT value FROM app_settings WHERE key='api_token_hash'").fetchone()
            supplied=request.headers.get("Authorization","")
            if not token or not supplied.startswith("Bearer ") or not equal(hashlib.sha256(supplied[7:].encode()).hexdigest(),token[0]):
                return jsonify(error="Unauthorized"),401
            return
        a=account()
        if request.method=="POST" and (not session.get("csrf") or not equal(request.form.get("csrf",""),session["csrf"])):
            abort(403)
        if a is None:
            if request.endpoint!="setup":
                return redirect(url_for("setup"),303)
        elif request.endpoint=="setup":
            return redirect(url_for("home" if signed_in(a) else "login"),303)
        elif request.endpoint!="login" and not signed_in(a):
            return redirect(url_for("login"),303)

    @app.route("/setup",methods=["GET","POST"])
    def setup():
        if request.method=="POST":
            try:
                username,password=new_credentials()
                with db() as con:
                    result=con.execute("INSERT OR IGNORE INTO admin_account VALUES (1,?,?,?)",
                        (username,generate_password_hash(password),secrets.token_hex(16)))
                    created=result.rowcount==1
                if not created:
                    return redirect(url_for("login"),303)
                start_session(account())
                return redirect(url_for("home"),303)
            except ValueError as e:
                flash(str(e))
        return page("setup")

    @app.route("/login",methods=["GET","POST"])
    def login():
        a=account()
        if signed_in(a):
            return redirect(url_for("home"),303)
        if request.method=="POST":
            with login_lock:
                now=time.monotonic()
                failures[:]=[t for t in failures if now-t<60]
                if len(failures)>=5:
                    return page("login",login_error="Zu viele Anmeldeversuche. Bitte in einer Minute erneut versuchen."),429
                password=request.form.get("password","")
                username=request.form.get("username","").strip()
                valid=bool(a and len(password)<=256 and check_password_hash(a["password_hash"],password) and equal(username,a["username"]))
                if not valid:
                    failures.append(now)
                    return page("login",login_error="Benutzername oder Passwort ist falsch."),401
                failures.clear()
            start_session(a)
            return redirect(url_for("home"),303)
        return page("login")

    @app.post("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"),303)

    @app.route("/settings",methods=["GET","POST"])
    def settings():
        a=account()
        new_token=None
        if request.method=="POST":
            action=request.form.get("action")
            if action in ("generate","revoke","password"):
                password=request.form.get("current_password","")
                if len(password)>256 or not check_password_hash(a["password_hash"],password):
                    flash("Aktuelles Passwort ist falsch.")
                elif action=="password":
                    try:
                        username,password=new_credentials()
                        with db() as con:
                            con.execute("UPDATE admin_account SET username=?,password_hash=?,session_version=? WHERE id=1",
                                        (username,generate_password_hash(password),secrets.token_hex(16)))
                        start_session(account())
                        flash("Kontodaten aktualisiert. Andere Sitzungen wurden abgemeldet.")
                    except ValueError as e:
                        flash(str(e))
                else:
                    with db() as con:
                        if action=="generate":
                            new_token=secrets.token_urlsafe(32)
                            con.execute("INSERT OR REPLACE INTO app_settings VALUES ('api_token_hash',?)",
                                        (hashlib.sha256(new_token.encode()).hexdigest(),))
                        else:
                            con.execute("DELETE FROM app_settings WHERE key='api_token_hash'")
                            flash("API-Token widerrufen.")
            else:
                abort(400)
        with db() as con:
            token_active=con.execute("SELECT 1 FROM app_settings WHERE key='api_token_hash'").fetchone() is not None
        return page("settings",username=account()["username"],token_active=token_active,new_token=new_token)

    @app.after_request
    def headers(r):
        r.headers["X-Content-Type-Options"]="nosniff"
        r.headers["Referrer-Policy"]="no-referrer"
        r.headers["X-Frame-Options"]="SAMEORIGIN"
        r.headers.setdefault("Content-Security-Policy","default-src 'self'; style-src 'self'; img-src 'self'; frame-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'self'")
        if request.endpoint != "static":
            r.headers["Cache-Control"]="no-store"
        return r

    def page(screen, **kwargs):
        return render_template("index.html",screen=screen,categories=CATEGORIES,csrf=csrf(),today=today().isoformat(),**kwargs)

    def item(con,table,pk):
        # table is chosen solely by server code
        row = con.execute("SELECT * FROM "+table+" WHERE id=?",(pk,)).fetchone()
        if row is None: abort(404)
        return dict(row)

    def values(fields, dates=()):
        result = {}
        for field in fields:
            v = request.form.get(field,"").strip()
            if len(v) > (10000 if field=="notes" else 300):
                raise ValueError("Eingabe zu lang: "+field)
            if field in dates and v:
                v = date.fromisoformat(v).isoformat()
            result[field] = v
        return result

    def reminder_rows(con, days=None):
        sql = """SELECT r.id,r.pet_id,p.name AS pet,r.kind,r.title,r.due
                 FROM records r JOIN pets p ON p.id=r.pet_id
                 WHERE r.done=0 AND r.due!='' """
        args = ()
        if days is not None:
            sql += "AND r.due<=? "
            args = ((today()+timedelta(days=days)).isoformat(),)
        rows = [dict(r) for r in con.execute(sql+"ORDER BY r.due,r.id",args)]
        for r in rows:
            r["days_left"]=(date.fromisoformat(r["due"])-today()).days
        return rows

    @app.get("/healthz")
    def health():
        with db() as con:
            con.execute("SELECT 1 FROM pets LIMIT 1").fetchone()
        return {"status":"ok"}

    @app.get("/")
    def home():
        with db() as con:
            pets = [dict(r) for r in con.execute("SELECT * FROM pets ORDER BY name,id")]
            reminders = reminder_rows(con,30)
        return page("home",pets=pets,reminders=reminders)

    @app.get("/reminders")
    def reminders():
        with db() as con:
            return page("reminders",reminders=reminder_rows(con))

    @app.route("/pets/new",methods=["GET","POST"])
    @app.route("/pets/<int:pid>/edit",methods=["GET","POST"])
    def pet_edit(pid=None):
        with db() as con:
            pet=item(con,"pets",pid) if pid is not None else {}
            if request.method=="POST":
                try:
                    d=values(PET_FIELDS,("birth","chip_date","issued"))
                    if not d["name"] or not d["species"]: raise ValueError("Name und Tierart sind Pflicht.")
                    if pid is None:
                        pid=con.execute("INSERT INTO pets ("+",".join(PET_FIELDS)+") VALUES ("+",".join("?" for _ in PET_FIELDS)+")",list(d.values())).lastrowid
                    else:
                        con.execute("UPDATE pets SET "+",".join(k+"=?" for k in PET_FIELDS)+" WHERE id=?",[*d.values(),pid])
                    return redirect(url_for("pet_detail",pid=pid),303)
                except ValueError as e:
                    flash(str(e),"error")
                    pet={**pet,**request.form.to_dict()}
            return page("pet_edit",pet=pet,pid=pid)

    @app.post("/pets/<int:pid>/delete")
    def pet_delete(pid):
        with db() as con:
            p=item(con,"pets",pid)
            if request.form.get("confirm")!=p["name"]: abort(400)
            con.execute("DELETE FROM pets WHERE id=?",(pid,))
        return redirect(url_for("home"),303)

    @app.get("/pets/<int:pid>")
    def pet_detail(pid):
        tab=request.args.get("tab","timeline")
        category=request.args.get("kind","")
        with db() as con:
            pet=item(con,"pets",pid)
            rows=con.execute("SELECT * FROM records WHERE pet_id=? ORDER BY day DESC,id DESC",(pid,))
            records=[dict(r) for r in rows]
            files=con.execute("SELECT a.id,a.record_id,a.name,a.mime FROM attachments a JOIN records r ON r.id=a.record_id WHERE r.pet_id=? ORDER BY a.id",(pid,))
            groups={}
            for f in files: groups.setdefault(f["record_id"],[]).append(dict(f))
            for r in records: r["files"]=groups.get(r["id"],[])
        if tab=="passport":
            records=[r for r in records if r["kind"] in ("vaccine","titer","parasite","worm")]
        elif category in CATEGORIES:
            records=[r for r in records if r["kind"]==category]
        return page("pet",pet=pet,records=records,tab=tab,category=category)

    def read_files():
        uploads=[]
        incoming=[f for f in request.files.getlist("files") if f.filename]
        if len(incoming)>5: raise ValueError("Maximal fünf Dateien je Speichervorgang.")
        for f in incoming:
            b=f.stream.read(MAX_FILE+1)
            if len(b)>MAX_FILE: raise ValueError("Maximal 10 MB je Datei.")
            if b.startswith(b"%PDF-"): mime="application/pdf"
            elif b.startswith(bytes.fromhex("ffd8ff")): mime="image/jpeg"
            elif b.startswith(bytes.fromhex("89504e470d0a1a0a")): mime="image/png"
            elif b[:4]==b"RIFF" and b[8:12]==b"WEBP": mime="image/webp"
            else: raise ValueError("Nur PDF, JPEG, PNG und WebP erlaubt.")
            name=f.filename.replace(chr(92),"/").split("/")[-1][:180]
            name="".join(c for c in name if ord(c)>=32 and ord(c)!=127) or "Datei"
            uploads.append((name,mime,b))
        return uploads

    @app.route("/pets/<int:pid>/records/new",methods=["GET","POST"])
    @app.route("/pets/<int:pid>/records/<int:rid>/edit",methods=["GET","POST"])
    def record_edit(pid,rid=None):
        with db() as con:
            pet=item(con,"pets",pid)
            record=item(con,"records",rid) if rid is not None else {"day":today().isoformat(),"kind":request.args.get("kind","visit")}
            if rid is not None and record["pet_id"]!=pid: abort(404)
            files=[dict(f) for f in con.execute("SELECT id,name,mime FROM attachments WHERE record_id=?",(rid,))]
            if request.method=="POST":
                try:
                    d=values(RECORD_FIELDS,("day","valid_from","valid_until","due"))
                    if d["kind"] not in CATEGORIES or not d["title"] or not d["day"]: raise ValueError("Kategorie, Titel und Datum sind Pflicht.")
                    if d["valid_from"] and d["valid_until"] and d["valid_from"]>d["valid_until"]: raise ValueError("Gültigkeitszeitraum prüfen.")
                    if d["weight"]:
                        w=float(d["weight"].replace(",","."))
                        if not 0<w<10000: raise ValueError("Ungültiges Gewicht.")
                        d["weight"]=str(w)
                    if d["kind"]=="vaccine" and not d["due"]:
                        d["due"]=d["valid_until"]
                    if d["kind"]=="visit" and not d["due"] and d["day"]>=today().isoformat():
                        d["due"]=d["day"]
                    uploads=read_files()
                    if rid is None:
                        rid=con.execute("INSERT INTO records (pet_id,"+",".join(RECORD_FIELDS)+") VALUES ("+",".join("?" for _ in range(len(RECORD_FIELDS)+1))+")",[pid,*d.values()]).lastrowid
                    else:
                        done=record["done"] if record["due"]==d["due"] else 0
                        con.execute("UPDATE records SET "+",".join(k+"=?" for k in RECORD_FIELDS)+",done=? WHERE id=?",[*d.values(),done,rid])
                    con.executemany("INSERT INTO attachments(record_id,name,mime,data) VALUES (?,?,?,?)",[(rid,*f) for f in uploads])
                    return redirect(url_for("pet_detail",pid=pid),303)
                except ValueError as e:
                    flash(str(e),"error")
                    record={**record,**request.form.to_dict()}
            return page("record_edit",pet=pet,record=record,rid=rid,files=files)

    @app.post("/records/<int:rid>/delete")
    def record_delete(rid):
        with db() as con:
            r=item(con,"records",rid)
            con.execute("DELETE FROM records WHERE id=?",(rid,))
        return redirect(url_for("pet_detail",pid=r["pet_id"]),303)

    @app.post("/records/<int:rid>/toggle")
    def toggle(rid):
        with db() as con:
            r=item(con,"records",rid)
            con.execute("UPDATE records SET done=1-done WHERE id=?",(rid,))
        return redirect(url_for("reminders"),303)

    @app.get("/attachments/<int:aid>")
    def attachment(aid):
        with db() as con:
            f=con.execute("SELECT id,name,mime FROM attachments WHERE id=?",(aid,)).fetchone()
            if f is None: abort(404)
        return page("preview",file=dict(f))

    @app.get("/attachments/<int:aid>/content")
    def attachment_content(aid):
        with db() as con:
            f=item(con,"attachments",aid)
        response=send_file(BytesIO(f["data"]), mimetype=f["mime"],
                           as_attachment=request.args.get("download")=="1",
                           download_name=f["name"], conditional=True)
        response.headers["Content-Security-Policy"]="default-src 'none'; frame-ancestors 'self'"
        return response

    @app.post("/attachments/<int:aid>/delete")
    def attachment_delete(aid):
        with db() as con:
            f=con.execute("SELECT a.record_id,r.pet_id FROM attachments a JOIN records r ON r.id=a.record_id WHERE a.id=?",(aid,)).fetchone()
            if f is None: abort(404)
            con.execute("DELETE FROM attachments WHERE id=?",(aid,))
        return redirect(url_for("record_edit",pid=f["pet_id"],rid=f["record_id"]),303)

    @app.get("/api/v1/reminders")
    def api_reminders():
        try:
            days=int(request.args.get("days","30"))
            if not 0<=days<=3650: raise ValueError()
        except ValueError:
            return jsonify(error="days must be 0..3650"),400
        with db() as con:
            rows=reminder_rows(con,days)
            all_rows=reminder_rows(con)
        return jsonify(count=len(rows),overdue=sum(r["days_left"]<0 for r in rows),
                       due_today=sum(r["days_left"]==0 for r in rows),
                       next=all_rows[0] if all_rows else None,reminders=rows,as_of=today().isoformat())

    @app.errorhandler(413)
    def too_large(e):
        return "Upload zu groß (max. 55 MB pro Anfrage).",413

    return app

if __name__ == "__main__":
    create_app().run(host="127.0.0.1",port=8080)
