import os, sqlite3, threading
from datetime import datetime, timezone
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

DB = os.environ.get("DB_PATH", "forestwatch.db")
OFFLINE_AFTER = 300  # seconds without heartbeat/alert -> node offline

app = Flask(__name__, static_folder="static")
CORS(app)
lock = threading.Lock()
alerts = []      # newest first
heartbeats = {}  # node -> {time, battery, rssi, lat, lng}

def now(): return datetime.now(timezone.utc)
def iso(dt): return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
def parse(s): return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)

def db():
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row; return c

def init():
    with db() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS alerts(
            id INTEGER PRIMARY KEY AUTOINCREMENT, node TEXT, threat TEXT,
            lat REAL, lng REAL, time TEXT, ack INTEGER DEFAULT 0,
            image_url TEXT, label TEXT)""")
        rows = c.execute("SELECT * FROM alerts ORDER BY id DESC").fetchall()
    alerts.extend({**dict(r), "ack": bool(r["ack"])} for r in rows)

@app.post("/alert")
def add_alert():
    d = request.get_json(silent=True) or {}
    try:
        node, threat = str(d["node"]), str(d["threat"]).upper()
        lat, lng = float(d["lat"]), float(d["lng"])
    except (KeyError, TypeError, ValueError):
        return jsonify(error="need node, threat, lat, lng"), 400
    t = iso(now())
    with lock, db() as c:
        cur = c.execute("INSERT INTO alerts(node,threat,lat,lng,time,image_url,label) VALUES(?,?,?,?,?,?,?)",
                        (node, threat, lat, lng, t, d.get("image_url"), d.get("label")))
        a = dict(id=cur.lastrowid, node=node, threat=threat, lat=lat, lng=lng, time=t,
                 ack=False, image_url=d.get("image_url"), label=d.get("label"))
        alerts.insert(0, a)
    return jsonify(a), 201

@app.get("/alerts")
def get_alerts():
    with lock: return jsonify(alerts)

@app.post("/alerts/<int:aid>/ack")
def ack(aid):
    with lock, db() as c:
        for a in alerts:
            if a["id"] == aid:
                a["ack"] = True
                c.execute("UPDATE alerts SET ack=1 WHERE id=?", (aid,))
                return jsonify(a)
    return jsonify(error="not found"), 404

@app.post("/heartbeat")
def heartbeat():
    d = request.get_json(silent=True) or {}
    if "node" not in d: return jsonify(error="need node"), 400
    with lock:
        heartbeats[str(d["node"])] = dict(time=iso(now()), battery=d.get("battery"),
                                          rssi=d.get("rssi"), lat=d.get("lat"), lng=d.get("lng"))
    return jsonify(ok=True)

@app.get("/nodes")
def nodes():
    out, t = {}, now()
    with lock:
        for a in reversed(alerts):  # oldest -> newest, so last write wins
            n = out.setdefault(a["node"], {})
            n.update(node=a["node"], lat=a["lat"], lng=a["lng"],
                     last_threat=a["threat"], last_alert=a["time"], last_seen=a["time"])
        for name, h in heartbeats.items():
            n = out.setdefault(name, {"node": name, "last_threat": None, "last_alert": None})
            if h["lat"] is not None and "lat" not in n: n.update(lat=h["lat"], lng=h["lng"])
            n.update(battery=h["battery"], rssi=h["rssi"], last_heartbeat=h["time"])
            if h["time"] > n.get("last_seen", ""): n["last_seen"] = h["time"]
    for n in out.values():
        n["online"] = (t - parse(n["last_seen"])).total_seconds() < OFFLINE_AFTER
    return jsonify(list(out.values()))

@app.get("/")
def index(): return send_from_directory("static", "index.html")

init()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
