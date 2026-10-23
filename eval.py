"""Phase 7: score the system against a hand-labelled golden set. Run after every change.

Targets (the POC is "working" when all are met on the golden set):
  extraction field accuracy >= 0.95   retrieval hit@8 >= 0.90
  coverage recall = 1.0               precedent recall >= 0.95
  draft traceability = 100%
  draft effort within +/-20% of the reference estimate on >= 80% of briefs
  drafts carry their sector's contract terms = 1.0
  SOW review flags the planted gaps and passes the sound clauses >= 0.9
"""
import json
import re
import sys

import search
from assemble import draft_sow
from review import review_sow

TARGETS = {"extraction_accuracy": 0.95, "retrieval_hit_at_8": 0.90, "coverage_recall": 1.0, "precedent_recall": 0.95,
           "draft_traceability": 1.0, "draft_industry_terms": 1.0, "review_accuracy": 0.9, "draft_effort_within_20pct": 0.80}


def run(path="golden.jsonl") -> dict:
    cases = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    scores = {k: [] for k in TARGETS}
    for c in cases:
        if c["type"] == "extraction":
            got = next((s for s in search.contract_details() if s["filename"] == c["filename"]), {})
            for field, want in c["expect"].items():
                scores["extraction_accuracy"].append(str(got.get(field)) == str(want))
        elif c["type"] == "retrieval":
            hits = search.search_text(c["query"], k=8)
            scores["retrieval_hit_at_8"].append(any(
                h["filename"] == c["expect"]["filename"] and h["page_no"] == c["expect"]["page"] for h in hits))
        elif c["type"] == "coverage":
            got = {r["filename"] for r in search.clause_coverage(c["clause_type"])}
            want = set(c["expect_missing"])
            scores["coverage_recall"].append(len(got & want) / len(want) if want else float(not got))
        elif c["type"] == "precedent":
            got = {r["filename"] for r in search.precedents(c["clause_type"], c.get("sector"))}
            want = set(c["expect_files"])
            scores["precedent_recall"].append(len(got & want) / len(want) if want else 1.0)
        elif c["type"] == "review":                 # sample SOWs with planted gaps
            r = review_sow(c["file"], c["sector"], c["product"], c["pricing"])
            flagged = {x["clause_type"] for x in r["rows"] if x["status"] in ("missing", "weak")}
            checks = [ct in flagged for ct in c["expect_flagged"]] + [ct not in flagged for ct in c["expect_ok"]]
            scores["review_accuracy"].append(sum(checks) / len(checks))
        elif c["type"] == "draft":
            d = draft_sow(c["brief"])
            body = d["markdown"].split("## Effort estimate")[0]
            paras = [p for p in body.split("\n\n")[2:] if p.strip() and not p.startswith(("#", ">"))]
            ids, kids = set(d["component_ids"]), set(d.get("clause_ids", []))
            cited = [bool({int(t) for t in re.findall(r"\[C(\d+)\]", p)} & ids
                          or {int(t) for t in re.findall(r"\[K(\d+)\]", p)} & kids) for p in paras]
            scores["draft_traceability"].append(all(cited) if cited else False)
            if c.get("expect_terms") is not None:     # the draft carries its sector's contract terms
                scores["draft_industry_terms"].append(set(c["expect_terms"]) <= set(d.get("industry_terms", [])))
            ref = c.get("reference_hours")
            if ref:
                scores["draft_effort_within_20pct"].append(abs(d["effort"]["total"] - ref) / ref <= 0.20)
    report = {}
    for k, vals in scores.items():
        if vals:
            v = sum(vals) / len(vals)
            report[k] = {"score": round(v, 3), "target": TARGETS[k], "n": len(vals), "pass": v >= TARGETS[k]}
    return report


if __name__ == "__main__":
    import argparse
    from datetime import datetime, timezone

    from config import CHAT_MODEL, EMBED_MODEL, EXTRACT_MODEL

    ap = argparse.ArgumentParser()
    ap.add_argument("golden", nargs="?", default="golden.jsonl")
    ap.add_argument("--out", help="also write the scores to this JSON file")
    args = ap.parse_args()
    r = run(args.golden)
    print(json.dumps(r, indent=2))
    if args.out:
        with open(args.out, "w") as f:
            json.dump({"scores": r, "run_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                       "models": f"{EXTRACT_MODEL} (extraction), {CHAT_MODEL} (drafting), {EMBED_MODEL} (embeddings)"}, f, indent=2)
    sys.exit(0 if all(v["pass"] for v in r.values()) else 1)
