# ForestWatch AI dashboard

## Run locally
    pip install -r requirements.txt
    python app.py          # http://localhost:5000

## Send a test alert
    curl -X POST http://localhost:5000/alert -H "Content-Type: application/json" \
      -d '{"node":"NODE1","threat":"CHAINSAW","lat":12.9716,"lng":77.5946}'

Heartbeat:  curl -X POST http://localhost:5000/heartbeat -H "Content-Type: application/json" -d '{"node":"NODE1","battery":87,"rssi":-90}'
With photo: add "image_url":"https://...","label":"human" to the alert JSON.
Threats: CHAINSAW / GUNSHOT (red), HUMAN (orange), ANIMAL (green).

## Deploy on Render (free)
1. Push this folder to a GitHub repo.
2. Render -> New -> Web Service -> pick the repo. It reads render.yaml
   (build: `pip install -r requirements.txt`, start: `gunicorn app:app --workers 1 --threads 4`).
3. Open the URL Render gives you and use it in the gateway ESP32 code (`/alert`).

Notes: keep `--workers 1` (alerts live in memory). Render's free disk is wiped on
redeploy/restart, so the SQLite history resets. The free tier sleeps when idle:
open the URL a few minutes before your demo.
