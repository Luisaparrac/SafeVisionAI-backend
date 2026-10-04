"""Sends a test event to the backend, as the IoT module will do.

Usage:
  python scripts/simulate_event.py                      # local, random type
  python scripts/simulate_event.py --url https://YOUR-BACKEND.onrender.com --key YOUR_KEY --tipo "Caída"
Only uses the standard library.
"""
import argparse
import json
import random
import urllib.request

TYPES = ["Caída", "Colapso", "Inmovilidad prolongada", "Movimiento anormal",
         "Permanencia en zona restringida", "Cambio repentino de postura"]

parser = argparse.ArgumentParser()
parser.add_argument("--url", default="http://localhost:8000")
parser.add_argument("--key", default="cambia-esta-clave")
parser.add_argument("--tipo", default=None)
parser.add_argument("--camara", type=int, default=1)
parser.add_argument("--sujeto", type=int, default=1)
args = parser.parse_args()

body = {
    "id_camara": args.camara,
    "id_sujeto": args.sujeto,
    "tipo_evento": args.tipo or random.choice(TYPES),
    "descripcion": "Evento simulado desde scripts/simulate_event.py",
}
request = urllib.request.Request(
    args.url.rstrip("/") + "/api/eventos",
    data=json.dumps(body).encode(),
    headers={"Content-Type": "application/json", "X-API-Key": args.key},
    method="POST",
)
with urllib.request.urlopen(request, timeout=90) as response:
    print(response.status, json.loads(response.read()))
