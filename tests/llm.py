"""Offline stand-in for llm.py: hashed bag-of-words embeddings and rule-based extraction."""
import hashlib
import json
import re

import numpy as np

SECTION_WORDS = {"deliverable": "deliver", "assumption": "assum", "out_of_scope": "out of scope",
                 "staffing": "staff", "governance": "steering", "acceptance": "accept",
                 "change_control": "change request", "payment": "invoice", "scope": "scope"}
CLAUSE_WORDS = {"termination": "terminat", "liability": "liabilit", "payment": "invoice",
                "ip": "intellectual property", "data_protection": "personal data", "sla": "service level"}


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
        val = re.search(r"Total fixed price: GBP ([\d,]+)", user)
        dates = re.findall(r"\d{4}-\d{2}-\d{2}", user)
        return {"client_alias": (re.search(r"Client [A-Z]", user) or [None])[0], "sector": "retail",
                "size_band": "enterprise", "products": ["AEM"] if "AEM" in user else ["Target"],
                "pricing_model": "fixed_price" if val else "t_and_m",
                "contract_value": float(val.group(1).replace(",", "")) if val else None,
                "currency": "GBP", "start_date": dates[0] if dates else None,
                "end_date": dates[1] if len(dates) > 1 else None}
    clauses, comps = [], []
    for line in user.split("\n"):
        m = re.match(r"\d+\.\d+ (.+)", line)
        if not m:
            continue
        body = m.group(1)
        for ct, w in CLAUSE_WORDS.items():
            if w in body.lower():
                clauses.append({"clause_type": ct, "summary": body[:60], "key_value": None, "quote": body})
                break
        sec = next((s for s, w in SECTION_WORDS.items() if w in body.lower()), None)
        if sec:
            effort = [{"role": r.lower(), "hours": float(h)} for r, h in re.findall(r"(Architect|Developer|PM) (\d+)h", body)]
            comps.append({"section": sec, "title": body[:40], "body": body, "product": "AEM" if "AEM" in body else None,
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
