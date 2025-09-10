import os, time, json, requests
from flask import Flask, request, jsonify
import psycopg2
import psycopg2.extras
from datetime import datetime, timezone

app = Flask(__name__)

PG_HOST = os.environ.get("POSTGRES_HOST", "postgres")
PG_PORT = int(os.environ.get("POSTGRES_PORT", "5432"))
PG_DB = os.environ.get("POSTGRES_DB", "logsdb")
PG_USER = os.environ.get("POSTGRES_USER", "logs_user")
PG_PASS = os.environ.get("POSTGRES_PASSWORD", "logs_pass")

PERSISTORS = {
    "auth": os.environ.get("PERSISTOR_AUTH", "persistor-auth"),
    "payment": os.environ.get("PERSISTOR_PAYMENT", "persistor-payment"),
    "system": os.environ.get("PERSISTOR_SYSTEM", "persistor-system"),
    "application": os.environ.get("PERSISTOR_APPLICATION", "persistor-application"),
}
PERSISTOR_PORT = int(os.environ.get("PERSISTOR_PORT", "6000"))

def get_conn():
    return psycopg2.connect(host=PG_HOST, port=PG_PORT, dbname=PG_DB, user=PG_USER, password=PG_PASS)

def wait_for_postgres(retries=15, sleep_sec=2):
    for i in range(retries):
        try:
            conn = get_conn()
            conn.close()
            return True
        except Exception as e:
            print("Waiting for Postgres...", e)
            time.sleep(sleep_sec)
    raise Exception("Postgres not available")

def init_db():
    wait_for_postgres()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
      CREATE TABLE IF NOT EXISTS logs (
        id SERIAL PRIMARY KEY,
        event_id INTEGER,
        type TEXT,
        level TEXT,
        message TEXT,
        timestamp TIMESTAMPTZ,
        meta JSONB
      );
    """)
    conn.commit()
    cur.close()
    conn.close()

def insert_log(event):
    conn = get_conn()
    cur = conn.cursor()
    ts = None
    try:
        ts = datetime.fromisoformat(event.get("timestamp").replace("Z","+00:00"))
    except Exception:
        ts = datetime.now(timezone.utc)
    cur.execute(
        "INSERT INTO logs (event_id, type, level, message, timestamp, meta) VALUES (%s,%s,%s,%s,%s,%s)",
        (event.get("id"), event.get("type"), event.get("level"),
         event.get("message"), ts, json.dumps(event.get("meta") or {}))
    )
    conn.commit()
    cur.close()
    conn.close()

def route_to_persistor(event):
    p = PERSISTORS.get(event.get("type"))
    if not p:
        return False, "unknown type"
    url = f"http://{p}:{PERSISTOR_PORT}/persist"
    try:
        r = requests.post(url, json=event, timeout=3)
        return (r.status_code == 200), r.text
    except Exception as e:
        return False, str(e)

@app.route("/health")
def health():
    return {"status": "ok"}, 200

@app.route("/collect", methods=["POST"])
def collect():
    event = request.get_json()
    if not event:
        return {"error":"invalid"}, 400
    insert_log(event)
    ok, info = route_to_persistor(event)
    return {"stored": True, "routed": ok, "info": info}, 200

@app.route("/analyze", methods=["GET"])
def analyze():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT type, COUNT(*) FROM logs GROUP BY type")
    rows = cur.fetchall()
    counts = {r[0]: r[1] for r in rows}
    cur.close(); conn.close()
    return jsonify({"counts": counts})

@app.route("/logs", methods=["GET"])
def logs():
    limit = int(request.args.get("limit", "50"))
    since = request.args.get("since")
    sql = "SELECT event_id, type, level, message, timestamp, meta FROM logs"
    params = []
    if since:
        sql += " WHERE timestamp >= %s"
        params.append(since)
    sql += " ORDER BY timestamp DESC LIMIT %s"
    params.append(limit)
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute(sql, params)
    rows = cur.fetchall()
    result = []
    for r in rows:
        result.append({
            "id": r["event_id"],
            "type": r["type"],
            "level": r["level"],
            "message": r["message"],
            "timestamp": r["timestamp"].isoformat() if r["timestamp"] else None,
            "meta": r["meta"]
        })
    cur.close(); conn.close()
    return jsonify({"logs": result})

if __name__ == "__main__":
    print("Starting collector, waiting for Postgres...")
    init_db()
    app.run(host="0.0.0.0", port=5002)
