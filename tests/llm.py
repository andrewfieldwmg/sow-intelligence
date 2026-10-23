"""Offline stand-in for llm.py: hashed bag-of-words embeddings and rule-based extraction."""
import hashlib
import json
import re

import numpy as np

SECTION_WORDS = {"deliverable": "will deliver", "assumption": "assum", "out_of_scope": "out of scope",
                 "staffing": "key personnel", "governance": "steering", "acceptance": "accept",
                 "change_control": "change request", "payment": "invoice", "scope": "scope"}
CLAUSE_WORDS = {"exit_management": "exit plan", "termination": "terminat", "subcontracting": "subcontract",
                "regulatory": "regulat", "acceptance": "accept", "indemnity": "indemnif", "insurance": "insurance",
                "liability": "liabilit", "payment": "invoice", "ip": "intellectual property",
                "data_protection": "personal data", "sla": "service level", "audit": "audit",
                "non_solicitation": "solicit", "force_majeure": "force majeure"}


def embed(texts, query=False):
    out = []
    for t in texts:
        v = np.zeros(384)
        for w in re.findall(r"[a-z]{3,}", t.lower()):
            v[int(hashlib.md5(w.encode()).hexdigest(), 16) % 384] += 1
        out.append((v / (np.linalg.norm(v) or 1)).tolist())
    return out


def extract_json(system, user, schema, name):
    if name == "sow_metadata":
        val = re.search(r"Total fixed price: [A-Z]{3} ([\d,]+)", user)
        term = re.search(r"start on (\d{4}-\d{2}-\d{2}) and end on (\d{4}-\d{2}-\d{2})", user)
        dates = list(term.groups()) if term else re.findall(r"\d{4}-\d{2}-\d{2}", user)
        cur = re.search(r"\b(GBP|EUR|USD) [\d,]+", user)
        return {"client_alias": (re.search(r"Client [A-Z]", user) or [None])[0], "sector": "retail",
                "size_band": "enterprise", "products": ["AEM"] if "AEM" in user else ["Target"],
                "pricing_model": "investment" if "Supplier-funded investment" in user else "fixed_price" if val else "t_and_m",
                "contract_value": float(val.group(1).replace(",", "")) if val else None,
                "currency": cur.group(1) if cur else "GBP", "start_date": dates[0] if dates else None,
                "end_date": dates[1] if len(dates) > 1 else None}
    clauses, comps = [], []
    for m in re.finditer(r"(?ms)^\d+\.\d+ (.+?)(?=^\d+\.\d+ |\Z)", user):   # a clause may wrap over lines
        body = " ".join(m.group(1).split())
        heading = body.split(".")[0].lower()             # a clause's own heading decides its type, as a reader would
        for ct, w in sorted(CLAUSE_WORDS.items(), key=lambda kv: kv[1] not in heading):
            if w in body.lower():
                clauses.append({"clause_type": ct, "summary": body[:60], "key_value": None, "quote": body})
                break
        sec = next((s for s, w in SECTION_WORDS.items() if w in body.lower()), None)
        if sec:
            effort = [{"role": r.lower(), "hours": float(h)} for r, h in re.findall(r"([A-Z][A-Za-z]*) (\d+)h", body)]
            comps.append({"section": sec, "title": body[:40], "body": body, "product": next((p for p in ("AEM Sites", "AEM Assets", "Journey Optimizer", "Analytics", "Target")
                                       if p in body), None),
                          "effort": effort})
    if "hallucinate" in user:              # simulate a model inventing text: must be dropped
        comps.append({"section": "scope", "title": "made up", "body": "The supplier will also build a mobile app for free.",
                      "product": None, "effort": []})
    return {"clauses": clauses, "components": comps}


def complete(system, user):
    ids = re.findall(r"\[C(\d+)\]", user)
    if "Section: governance" in user:      # simulate an uncited paragraph: must fall back to verbatim
        return "We will hold weekly meetings."
    return "\n\n".join(f"Adapted text for the brief. [C{i}]" for i in ids)


def tool_loop(system, question, tools, funcs, max_steps=4):
    return str(funcs["clause_coverage"](clause_type="liability"))
