import os, time, sqlite3, datetime as dt
from contextlib import closing
from flask import Flask, render_template, request, redirect, url_for, session, g
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from dotenv import load_dotenv
import stripe
from puzzles import generate_puzzle_seeded

load_dotenv()
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY","change-me")
app.config["APP_NAME"]   = os.getenv("APP_NAME","Mini Word Finder")
app.config["LOGO_URL"]   = os.getenv("LOGO_URL","https://via.placeholder.com/160x42?text=Logo")
app.config["ADSENSE_CLIENT"] = os.getenv("ADSENSE_CLIENT","")
app.config["ADSENSE_SLOT"]   = os.getenv("ADSENSE_SLOT","")
stripe.api_key = os.getenv("STRIPE_SECRET_KEY","")
PRICE_ID = os.getenv("STRIPE_PRICE_ID","")
DB_PATH="app.db"

# ---------- DB ----------
def get_db():
    if "db" not in g:
        g.db=sqlite3.connect(DB_PATH,detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory=sqlite3.Row
    return g.db
@app.teardown_appcontext
def close_db(_=None): db=g.pop("db",None); db and db.close()
def init_db():
    with closing(get_db()) as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          email TEXT UNIQUE NOT NULL,
          pw_hash TEXT NOT NULL,
          credits INTEGER DEFAULT 0,
          ad_free_until INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS scores(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL,
          mode TEXT NOT NULL,
          score INTEGER NOT NULL,
          elapsed INTEGER,
          note TEXT,
          seed INTEGER,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY(user_id) REFERENCES users(id)
        );
        """); db.commit()

with app.app_context():
    init_db()

# ---------- helpers ----------
ts=URLSafeTimedSerializer(app.config["SECRET_KEY"])
def parse_reset_token(token,max_age=3600):
    try: return ts.loads(token,max_age=max_age).get("email")
    except (BadSignature,SignatureExpired): return None
def login_required(view):
    def wrapper(*a,**kw): 
        if "uid" not in session: return redirect(url_for("login"))
        return view(*a,**kw)
    wrapper.__name__=view.__name__; return wrapper
def current_user():
    if "uid" not in session: return None
    return get_db().execute("SELECT * FROM users WHERE id=?",(session["uid"],)).fetchone()
def ad_free_context(u):
    now=int(time.time())
    return u["ad_free_until"]>now, dt.datetime.fromtimestamp(u["ad_free_until"]).strftime("%Y-%m-%d %H:%M")

# ---------- MODES ----------
MODES={"easy":{"size":10,"k":5,"seconds":0},"medium":{"size":12,"k":7,"seconds":120},"hard":{"size":14,"k":10,"seconds":180}}

# ---------- AUTH (register/login/logout/reset) ----------
@app.route("/register",methods=["GET","POST"])
def register():
    if request.method=="POST":
        email=request.form["email"].lower(); pw=request.form["password"]
        try: get_db().execute("INSERT INTO users(email,pw_hash) VALUES (?,?)",(email,generate_password_hash(pw))); get_db().commit(); return redirect(url_for("login"))
        except: return render_template("register.html",flash_msg=("err","Email exists"))
    return render_template("register.html")
@app.route("/login",methods=["GET","POST"])
def login():
    if request.method=="POST":
        email=request.form["email"].lower(); pw=request.form["password"]
        u=get_db().execute("SELECT * FROM users WHERE email=?",(email,)).fetchone()
        if u and check_password_hash(u["pw_hash"],pw): session["uid"]=u["id"]; return redirect(url_for("home"))
        return render_template("login.html",flash_msg=("err","Invalid credentials"))
    return render_template("login.html")
@app.route("/logout"); def logout(): session.clear(); return redirect(url_for("login"))
@app.route("/reset/<token>",methods=["GET","POST"])
def reset_token(token):
    email=parse_reset_token(token)
    if not email: return redirect(url_for("login"))
    if request.method=="POST": pw=request.form["password"]; get_db().execute("UPDATE users SET pw_hash=? WHERE email=?",(generate_password_hash(pw),email)); get_db().commit(); return redirect(url_for("login"))
    return render_template("reset_token.html")

# ---------- GAME ----------
@app.route("/"); def root(): return redirect(url_for("home") if "uid" in session else url_for("login"))
@app.route("/home"); @login_required
def home(): return render_template("home.html")
@app.route("/play/<mode>"); @login_required
def play(mode):
    cfg=MODES[mode]; seed=int(time.time()*1000)%2147483647
    grid,words,_=generate_puzzle_seeded(seed,cfg["size"],cfg["k"])
    u=current_user(); adf,until=ad_free_context(u)
    return render_template("game.html",grid=grid,words=words,mode=mode,seconds=cfg["seconds"],seed=seed,ad_free=adf,ad_free_until_human=until,credits=u["credits"])
@app.route("/daily/<mode>"); @login_required
def daily(mode):
    cfg=MODES[mode]; day=dt.datetime.utcnow().strftime("%Y%m%d"); seed=int(f"{day}{list(MODES).index(mode)}")
    grid,words,_=generate_puzzle_seeded(seed,cfg["size"],cfg["k"])
    u=current_user(); adf,until=ad_free_context(u)
    return render_template("game.html",grid=grid,words=words,mode=mode,seconds=cfg["seconds"],seed=seed,ad_free=adf,ad_free_until_human=until,credits=u["credits"])
@app.route("/seed/<mode>/<int:seed>"); @login_required
def seed_play(mode,seed):
    cfg=MODES[mode]; grid,words,_=generate_puzzle_seeded(seed,cfg["size"],cfg["k"])
    u=current_user(); adf,until=ad_free_context(u)
    return render_template("game.html",grid=grid,words=words,mode=mode,seconds=cfg["seconds"],seed=seed,ad_free=adf,ad_free_until_human=until,credits=u["credits"])

# ---------- SCORES ----------
@app.route("/submit-score",methods=["POST"]); @login_required
def submit_score():
    u=current_user(); mode=request.form["mode"]; score=int(request.form["score"]); elapsed=int(request.form["elapsed"]); seed=int(request.form["seed"])
    get_db().execute("INSERT INTO scores(user_id,mode,score,elapsed,seed) VALUES (?,?,?,?,?)",(u["id"],mode,score,elapsed,seed)); get_db().commit()
    return redirect(url_for("leaderboard"))
@app.route("/leaderboard"); @login_required
def leaderboard():
    leaders={m:get_db().execute("SELECT s.score,s.elapsed,u.email FROM scores s JOIN users u ON u.id=s.user_id WHERE s.mode=? ORDER BY s.score DESC LIMIT 10",(m,)).fetchall() for m in MODES}
    return render_template("leaderboard.html",leaders=leaders)
@app.route("/daily-leaderboard"); @login_required
def daily_leaderboard():
    day=request.args.get("day") or dt.datetime.utcnow().strftime("%Y%m%d")
    leaders={m:get_db().execute("SELECT s.score,s.elapsed,u.email FROM scores s JOIN users u ON u.id=s.user_id WHERE s.mode=? AND s.seed=? ORDER BY s.score DESC LIMIT 10",(m,int(f"{day}{list(MODES).index(m)}"))).fetchall() for m in MODES}
    dates=[(dt.datetime.utcnow()-dt.timedelta(days=i)).strftime("%Y%m%d") for i in range(7)]
    return render_template("daily_leaderboard.html",leaders=leaders,day=day,dates=dates)

# ---------- CREDITS / STRIPE ----------
@app.route("/spend-credit",methods=["POST"]); @login_required
def spend_credit():
    u=current_user()
    if u["credits"]>0: until=max(u["ad_free_until"],int(time.time()))+86400; get_db().execute("UPDATE users SET credits=credits-1,ad_free_until=? WHERE id=?",(until,u["id"])); get_db().commit()
    return redirect(url_for("home"))
@app.route("/buy-credits",methods=["POST"]); @login_required
def buy_credits():
    session_stripe=stripe.checkout.Session.create(payment_method_types=["card"],line_items=[{"price":PRICE_ID,"quantity":1}],mode="payment",success_url=url_for("buy_success",_external=True),cancel_url=url_for("home",_external=True))
    return redirect(session_stripe.url,303)
@app.route("/buy-success"); @login_required
def buy_success():
    get_db().execute("UPDATE users SET credits=credits+10 WHERE id=?",(session["uid"],)); get_db().commit(); return redirect(url_for("home"))

if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT",8080)))