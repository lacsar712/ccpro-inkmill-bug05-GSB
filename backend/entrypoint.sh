#!/bin/sh
set -e

PORT="${PORT:-9200}"

echo "Waiting for MySQL..."
python - <<'PY'
import os, time
from sqlalchemy import create_engine, text
from app.config import settings

url = settings.database_url
for i in range(60):
    try:
        engine = create_engine(url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("Database is ready.")
        break
    except Exception as e:
        print(f"DB not ready ({i+1}/60): {e}")
        time.sleep(2)
else:
    raise SystemExit("Database not ready after retries")
PY

echo "Creating tables..."
python -c "from app.database import Base, engine; from app import models; Base.metadata.create_all(bind=engine)"

echo "Ensuring grind_passes unique constraint..."
python - <<'PY'
# create_all 不会给已存在的表补约束，这里幂等补上
# uq_grind_pass_mill_pass_no (mill_id, pass_no)。存在历史重复数据时只告警、
# 不静默删数据，应用层校验仍会阻止新的冲突写入。
from sqlalchemy import text
from app.database import engine

with engine.begin() as conn:
    idx = conn.execute(text(
        "SELECT COUNT(*) FROM information_schema.statistics "
        "WHERE table_schema = DATABASE() AND table_name = 'grind_passes' "
        "AND index_name = 'uq_grind_pass_mill_pass_no'"
    )).scalar()
    if idx:
        print("Unique constraint already present.")
    else:
        dups = conn.execute(text(
            "SELECT mill_id, pass_no, COUNT(*) c FROM grind_passes "
            "GROUP BY mill_id, pass_no HAVING c > 1"
        )).fetchall()
        if dups:
            print(f"WARNING: {len(dups)} duplicate (mill_id, pass_no) group(s) found; "
                  "skipping unique constraint. Clean them up manually.")
        else:
            conn.execute(text(
                "ALTER TABLE grind_passes "
                "ADD CONSTRAINT uq_grind_pass_mill_pass_no UNIQUE (mill_id, pass_no)"
            ))
            print("Unique constraint uq_grind_pass_mill_pass_no added.")
PY

if [ "${SEED_ON_START}" = "true" ] || [ "${SEED_ON_START}" = "1" ]; then
  echo "Seeding data..."
  python -c "from app.seed import seed; seed()"
fi

echo "Starting gunicorn on :${PORT}..."
exec gunicorn wsgi:app --bind "0.0.0.0:${PORT}" --workers 2 --threads 4 --timeout 120
