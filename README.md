---
title: SOW Contract Intelligence
emoji: 📄
colorFrom: blue
colorTo: gray
sdk: docker
app_port: 7860
startup_duration_timeout: 1h
pinned: false
---

# SOW Contract Intelligence (v2)

Search, check and draft Statements of Work from past contracts. A proof of concept rebuilt in
October 2026 from the original POC (which ran on OpenAI): Claude for extraction, drafting and Q&A,
local bge-small embeddings, PostgreSQL with pgvector, and an MCP server for Claude Desktop or Cursor.

The demo runs on 48 fictional SOWs for invented clients: 38 Adobe implementations and 10 Applied AI engagements run by forward deployed engineers, across financial services, retail, hospitality and other sectors, with full contract boilerplate and 11 supplier-funded pilots whose conversion is recorded in the register (`demo/build_corpus.py`). No real customer data.

Drafts are industry-aware: same-industry precedents come first, and each draft carries its sector's
contract terms (regulatory, audit and exit for financial services, subcontracting for hospitality, AI
governance and enablement exit for Applied AI) copied verbatim from the strongest proven deal.

**Review a SOW** (`review.py`) scores an uploaded SOW against those canonical clauses: missing and weak
clauses, the top fixes before signing, and redlines built only from cited precedents. Uploads are
sanitised and held in memory; they never enter the library.

**Two retrieval paths.** `search.py` is hand-written hybrid search (pgvector plus Postgres full text, fused
with reciprocal rank fusion in SQL). `llamaindex_search.py` answers the same calls with LlamaIndex: chunks
as TextNodes with deal metadata in a PGVectorStore, a vector and a full-text retriever fused by
QueryFusionRetriever. Both use the same embeddings and are scored on the same eval cases, with latency.
The Ask tab can switch between them.

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
