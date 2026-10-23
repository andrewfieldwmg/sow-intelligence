---
title: SOW Contract Intelligence
emoji: 📄
colorFrom: blue
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
---

# SOW Contract Intelligence (v2)

Search, check and draft Statements of Work from past contracts. A proof of concept rebuilt in
October 2026 from the original POC (which ran on OpenAI): Claude for extraction, drafting and Q&A,
local bge-small embeddings, PostgreSQL with pgvector, and an MCP server for Claude Desktop or Cursor.

The demo runs on 18 fictional SOWs for invented clients (`demo/build_corpus.py`). No real customer data.

## Run it

```bash
pip install -r requirements.txt
cp .env.example .env                 # ANTHROPIC_API_KEY and database URLs
psql -d sow_intelligence -f schema.sql
python demo/build_corpus.py demo
SOW_DOCUMENTS_PATH=demo/sows ALIAS_MAP_PATH=demo/alias_map.csv REGISTER_PATH=demo/register.csv \
  sh -c 'python ingest.py && python extract.py && python chunk.py && python embed.py'
python eval.py demo/golden.jsonl
python answer.py "Which SOWs have no liability cap?"
```

MCP (Claude Desktop): add a server with command `python` and args `["/path/to/server.py"]`; keys stay in `.env`.

Offline tests: `cd tests && python smoke_test.py` (needs Postgres with pgvector; the model is stubbed).

## Space secrets

`ANTHROPIC_API_KEY` (required) and `DEMO_PASSWORD` (recommended: the page asks for user `demo` and this password, so
strangers can't spend your API credits).
