#!/bin/sh
set -eu

python - <<'PY'
import os
import time

import psycopg

host = os.environ.get("POSTGRES_HOST", "db")
port = os.environ.get("POSTGRES_PORT", "5432")
dbname = os.environ.get("POSTGRES_DB", "djangopub")
user = os.environ.get("POSTGRES_USER", "djangopub")
password = os.environ.get("POSTGRES_PASSWORD", "djangopub")

for attempt in range(30):
    try:
        with psycopg.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password,
            connect_timeout=3,
        ):
            break
    except Exception:
        time.sleep(1)
else:
    raise SystemExit("database unavailable")
PY

python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py seed_event --if-empty
python manage.py ensure_organizer

exec "$@"
