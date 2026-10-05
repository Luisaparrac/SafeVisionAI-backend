"""Sends a test event to the backend, as the IoT module will do.

Usage:
  python scripts/simulate_event.py                                    # local backend
  python scripts/simulate_event.py --url https://YOUR-BACKEND.onrender.com --key YOUR_KEY
  python scripts/simulate_event.py --tipo "Caída" --camara 1 --sujeto 2
Without --camara/--tipo it picks the first camera and a random event type from the API.
Only uses the standard library.
"""
import argparse
import json
import random
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument("--url", default="http://localhost:8000")
parser.add_argument("--key", default="")
parser.add_argument("--tipo", default=None, help="event type name as stored in event_types")
parser.add_argument("--camara", type=int, default=None)
parser.add_argument("--sujeto", type=int, default=None)
args = parser.parse_args()
base = args.url.rstrip("/")


def get(path):
    with urllib.request.urlopen(base + path, timeout=90) as response:
        return json.loads(response.read())


camera_id = args.camara or get("/api/camaras")[0]["camera_id"]
event_type = args.tipo or random.choice(get("/api/tipos-evento"))["name"]

body = {
    "camera_id": camera_id,
    "event_type": event_type,
    "subject_id": args.sujeto,
    "detected_class": "person",
    "confidence": round(random.uniform(0.7, 0.99), 2),
    "description": "Evento simulado desde scripts/simulate_event.py",
}
request = urllib.request.Request(
    base + "/api/eventos",
    data=json.dumps(body).encode(),
    headers={"Content-Type": "application/json", "X-API-Key": args.key},
    method="POST",
)
with urllib.request.urlopen(request, timeout=90) as response:
    print(response.status, json.loads(response.read()))
