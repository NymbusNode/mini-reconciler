# Mini Post‑Trade Reconciler

An example project that simulates basic post‑trade workflows via gRPC:

* **Trade ingestion** into PostgreSQL
* **Real‑time position & break detection**
* **gRPC ReconcileService** with streaming ingest
* **Rich CLI** front‑end

## Quick start (local)

```bash
git clone https://github.com/NymbusNode/mini-reconciler.git
cd mini-reconciler
python -m venv .recon_venv && source .recon_venv/bin/activate
pip install -r requirements.txt
createdb reconciler_db  # or use docker‑compose
psql -d reconciler_db -f schema.sql
python seed.py          # load sample data
python app/service/server.py &
python app/cli.py positions
```

## With Docker Compose

```bash
docker compose up -d   # Postgres + app container
```

Then in another shell:

```bash
python seed.py
python app/cli.py positions
```

---

