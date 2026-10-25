#!/usr/bin/env bash
# Container entrypoint: local Postgres + pgvector, load the demo data, start the web app.
set -euo pipefail
export PGDATA="$HOME/pgdata" PGHOST=/tmp PGPORT=5432   # the base image sets PGDATA to a root-owned path
if [ ! -s "$PGDATA/PG_VERSION" ]; then
  initdb -U owner --auth=trust -D "$PGDATA" >/dev/null
fi
pg_ctl -D "$PGDATA" -o "-k /tmp -c listen_addresses=''" -l "$HOME/pg.log" -w start
createdb -U owner sow 2>/dev/null || true
psql -U owner -d sow -q -f schema.sql
export DATABASE_URL_WRITER="postgresql://owner@/sow?host=/tmp"
export DATABASE_URL_READER="postgresql://sow_reader:change-me@/sow?host=/tmp"
if [ "$(psql -U owner -d sow -tAc 'select count(*) from sow')" = "0" ]; then
  if [ -s demo/seed.sql ]; then
    # Extraction was run once with Claude and saved, so start-up makes no model calls.
    psql -U owner -d sow -q -f demo/seed.sql >/dev/null
  else
    python demo/build_corpus.py demo
    SOW_DOCUMENTS_PATH=demo/sows ALIAS_MAP_PATH=demo/alias_map.csv REGISTER_PATH=demo/register.csv \
      sh -c 'python ingest.py && python extract.py && python chunk.py'
  fi
  python embed.py
  python llamaindex_search.py build      # second retrieval path, scored against the first in the evals
  psql -U owner -d sow -q -c "GRANT SELECT ON ALL TABLES IN SCHEMA public TO sow_reader"
fi
# Score the live system in the background; the Eval scores tab shows the result when it finishes.
if [ "${RUN_EVALS:-1}" = "1" ] && [ ! -s demo/eval_results.json ]; then
  (python eval.py demo/golden.jsonl --out demo/eval_results.json > "$HOME/eval.log" 2>&1 &)
fi
exec python app.py
