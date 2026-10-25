"""End-to-end offline test: synthetic corpus -> ingest -> extract -> chunk -> embed -> search -> draft -> eval.
Runs against a real Postgres with pgvector; only the model is faked (tests/llm.py shadows ../llm.py)."""
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(1, str(HERE.parent))
work = Path(os.environ["SMOKE_DIR"])
subprocess.run([sys.executable, str(HERE / "make_corpus.py"), str(work / "sows")], check=True)
(work / "alias_map.csv").write_text("real,alias\nExample Retail Group plc,Client A\n")
(work / "register.csv").write_text(
    "filename,proven,delivery_health,margin_band,csat\n"
    "client_a_aem_2024.docx,true,green,on,9\nclient_b_aem_2023.docx,true,amber,above,8\n"
    "client_c_target_2023.pdf,false,red,below,\n")
os.environ.update(SOW_DOCUMENTS_PATH=str(work / "sows"), ALIAS_MAP_PATH=str(work / "alias_map.csv"),
                  REGISTER_PATH=str(work / "register.csv"),
                  MIN_SIMILARITY="0.1")       # hashed test embeddings score lower than real ones

import tiktoken                                            # noqa: E402
class _WordEnc:                                            # this sandbox can't download the BPE file
    def encode(self, text, **_): return text.split()
tiktoken.get_encoding = lambda name: _WordEnc()

import ingest, extract, chunk, embed, search, sanitise   # noqa: E402
from assemble import draft_sow                             # noqa: E402

def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond:
        sys.exit(1)

ingest.main(); ingest.main()                               # second run must skip everything
w = search.conn()
cnt = lambda sql: search._rows(sql)[0]["n"]
check(cnt("SELECT count(*) n FROM sow") == 3, "3 SOWs ingested once (idempotent)")
check(cnt("SELECT count(*) n FROM page WHERE text ILIKE '%Example Retail%'") == 0, "real client name removed")
check(cnt("SELECT count(*) n FROM page WHERE text LIKE '%@example.com%'") == 0, "email scrubbed")
check(cnt("SELECT count(*) n FROM page p JOIN sow s ON s.id=p.sow_id WHERE s.filename LIKE '%.pdf'") == 2, "PDF pages kept")

extract.main()
d = {s["filename"]: s for s in search.contract_details()}
check(str(d["client_a_aem_2024.docx"]["end_date"]) == "2025-03-31", "end date extracted")
check(d["client_a_aem_2024.docx"]["proven"] and not d["client_c_target_2023.pdf"]["proven"], "proven flag from register")
check(cnt("SELECT count(*) n FROM component WHERE body LIKE '%mobile app%'") == 0, "invented component dropped")

chunk.main(); chunk.main()
check(cnt("SELECT count(*) n FROM chunk") == cnt("SELECT count(DISTINCT (sow_id, chunk_index)) n FROM chunk"), "chunks not duplicated")
embed.main()
check(cnt("SELECT count(*) n FROM pg_indexes WHERE indexname LIKE '%vec_idx'") == 2, "HNSW indexes built")

hits = search.search_text("terminate for convenience on written notice", k=3)
check(hits and hits[0]["filename"] == "client_a_aem_2024.docx", f"hybrid search top hit: {hits[0]['filename']} p{hits[0]['page_no']}")
missing = {r["filename"] for r in search.clause_coverage("liability")}
check(missing == {"client_b_aem_2023.docx", "client_c_target_2023.pdf"}, f"coverage complete: {sorted(missing)}")
comps = search.find_components("AEM templates deliverable", section="deliverable")
check(comps and all(c["filename"] != "client_c_target_2023.pdf" for c in comps), "unproven SOW excluded")

dr = draft_sow({"client_alias": "Client X", "objective": "AEM Sites migration with templates and content migration",
                "products": ["AEM"], "size_band": "enterprise", "pricing_model": "fixed_price"})
check("DRAFT" in dr["markdown"] and dr["gaps"], f"draft built, gaps: {dr['gaps']}")
check(any("governance" in i for i in dr["citation_issues"]), "uncited paragraph caught and replaced")
check(dr["effort"]["total"] > 0, f"effort roll-up: {dr['effort']}")
print(dr["markdown"][:1500])

try:
    sanitise.leak_check("Example Retail Group plc", sanitise.load_aliases(), "test")
    check(False, "leak gate")
except sanitise.LeakError:
    check(True, "leak gate blocks unsanitised text")

(work / "golden.jsonl").write_text("\n".join(json.dumps(x) for x in [
    {"type": "extraction", "filename": "client_a_aem_2024.docx", "expect": {"pricing_model": "fixed_price", "currency": "GBP"}},
    {"type": "retrieval", "query": "liability capped fees", "expect": {"filename": "client_a_aem_2024.docx", "page": 3}},
    {"type": "coverage", "clause_type": "liability", "expect_missing": ["client_b_aem_2023.docx", "client_c_target_2023.pdf"]},
    {"type": "draft", "brief": {"client_alias": "Client Y", "objective": "AEM migration", "products": ["AEM"]}, "reference_hours": 1500}]))
import eval as ev                                            # noqa: E402
print(json.dumps(ev.run(str(work / "golden.jsonl")), indent=2))
print("SMOKE TEST PASSED")
