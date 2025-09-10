import time, random, os, requests
from datetime import datetime

LISTENER_HOST = os.environ.get("LISTENER_HOST", "log-listener")
LISTENER_PORT = os.environ.get("LISTENER_PORT", "5001")
LISTENER_URL = f"http://{LISTENER_HOST}:{LISTENER_PORT}/logs"

TYPES = ["auth","payment","system","application"]
LEVELS = ["INFO","DEBUG","WARN","ERROR"]

def make_log():
    return {
        "id": random.randint(100000,999999),
        "type": random.choice(TYPES),
        "level": random.choice(LEVELS),
        "message": f"Auto-generated event {random.randint(1,9999)}",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "meta": {"host": "local-generator", "pid": random.randint(1000,9999)}
    }

if __name__ == "__main__":
    print("Log generator started — sending to", LISTENER_URL)
    interval = float(os.environ.get("INTERVAL", "1.5"))
    while True:
        payload = make_log()
        try:
            r = requests.post(LISTENER_URL, json=payload, timeout=5)
            print("sent", payload["id"], payload["type"], "->", r.status_code)
        except Exception as e:
            print("send error:", e)
        time.sleep(interval)
