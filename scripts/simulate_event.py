"""Sends a test event to the backend, as the IoT module does.

The backend URL and the IoT key have no default values: pass them as arguments
or as the environment variables BACKEND_URL and IOT_API_KEY.

Usage:
  python scripts/simulate_event.py --url http://localhost:8000 --key YOUR_KEY
  BACKEND_URL=https://BACKEND-HOST IOT_API_KEY=YOUR_KEY python scripts/simulate_event.py
  python scripts/simulate_event.py --url ... --key ... --tipo "Caída" --camara 1 --sujeto 2

Without --camara/--tipo it picks the first camera and a random event type from the API.
Only uses the standard library.
"""

import argparse
import json
import os
import random
import sys
import urllib.request
from collections.abc import Mapping, Sequence


def parse_args(argv: Sequence[str], environ: Mapping[str, str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Envía un evento de prueba al backend.")
    parser.add_argument("--url", default=environ.get("BACKEND_URL"), help="o BACKEND_URL")
    parser.add_argument("--key", default=environ.get("IOT_API_KEY"), help="o IOT_API_KEY")
    parser.add_argument("--tipo", help="nombre del tipo de evento, como en event_types")
    parser.add_argument("--camara", type=int)
    parser.add_argument("--sujeto", type=int)
    args = parser.parse_args(argv)
    if not args.url:
        parser.error("falta la URL del backend: usa --url o BACKEND_URL")
    if not args.key:
        parser.error("falta la clave del módulo IoT: usa --key o IOT_API_KEY")
    args.url = args.url.rstrip("/")
    return args


def build_event(camera_id: int, event_type: str, subject_id: int | None) -> dict:
    return {
        "camera_id": camera_id,
        "event_type": event_type,
        "subject_id": subject_id,
        "detected_class": "person",
        "confidence": round(random.uniform(0.7, 0.99), 2),
        "description": "Evento simulado desde scripts/simulate_event.py",
    }


def main(argv: Sequence[str], environ: Mapping[str, str]) -> None:
    args = parse_args(argv, environ)

    def get(path: str):
        # The catalogs require a panel session or the IoT key.
        request = urllib.request.Request(args.url + path, headers={"X-API-Key": args.key})
        with urllib.request.urlopen(request, timeout=90) as response:
            return json.loads(response.read())

    camera_id = args.camara or get("/api/camaras")[0]["camera_id"]
    event_type = args.tipo or random.choice(get("/api/tipos-evento"))["name"]
    request = urllib.request.Request(
        args.url + "/api/eventos",
        data=json.dumps(build_event(camera_id, event_type, args.sujeto)).encode(),
        headers={"Content-Type": "application/json", "X-API-Key": args.key},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        print(response.status, json.loads(response.read()))


if __name__ == "__main__":
    main(sys.argv[1:], os.environ)
