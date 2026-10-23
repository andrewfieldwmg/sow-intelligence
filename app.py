"""Web demo (Hugging Face Space). Read-only over the demo database; drafting calls Claude."""
import json
import os
from pathlib import Path

import gradio as gr
import pandas as pd

import search
from answer import ask
from assemble import draft_sow
from config import CLAUSE_TYPES

PRODUCTS = ["AEM Sites", "AEM Assets", "Target", "Analytics", "Journey Optimizer"]
INTRO = """# SOW Contract Intelligence (v2 demo)
Search, check and draft Statements of Work from a library of **18 fictional SOWs** for invented clients.
New drafts are assembled only from components of deals the delivery register marks as proven, and every
paragraph cites its source. Nothing here is real customer data."""


def _df(rows, cols):
    return pd.DataFrame([{c: r.get(c) for c in cols} for r in rows], columns=cols)


def do_ask(q):
    return ask(q) if q.strip() else "Type a question."


def do_coverage(clause_type, present):
    rows = search.clause_coverage(clause_type, present=present == "have it")
    return f"**{len(rows)}** SOWs {'have' if present == 'have it' else 'are missing'} a {clause_type.replace('_', ' ')} clause.", \
        _df(rows, ["filename", "client_alias", "start_date", "end_date"])


def do_draft(alias, objective, product, size_band, pricing):
    if not objective.strip():
        return "Describe the objective first.", ""
    d = draft_sow({"client_alias": alias or "New Client", "objective": objective, "products": [product],
                   "size_band": size_band, "pricing_model": pricing})
    notes = (f"Gaps: {', '.join(d['gaps']) or 'none'}. "
             f"Citation problems fixed by falling back to verbatim text: {len(d['citation_issues'])}.")
    return d["markdown"], notes


def library():
    rows = search.contract_details()
    for r in rows:
        r["products"] = ", ".join(r["products"] or [])
        r["clauses"] = ", ".join(sorted({c["clause_type"] for c in r["clauses"]}))
    return _df(rows, ["filename", "client_alias", "sector", "products", "pricing_model", "contract_value",
                      "currency", "start_date", "end_date", "proven", "delivery_health", "clauses"])


def scores():
    p = Path(os.getenv("EVAL_RESULTS", "demo/eval_results.json"))
    if not p.exists():
        return "No eval run recorded yet."
    r = json.loads(p.read_text())
    lines = ["| Measure | Score | Target | Cases | Pass |", "|---|---|---|---|---|"]
    lines += [f"| {k.replace('_', ' ')} | {v['score']:.0%} | {v['target']:.0%} | {v['n']} | {'yes' if v['pass'] else 'no'} |"
              for k, v in r.get("scores", r).items()]
    return "\n".join(lines) + (f"\n\nRun on {r['run_at']} with {r['models']}." if "run_at" in r else "")


with gr.Blocks(title="SOW Contract Intelligence") as demo:
    gr.Markdown(INTRO)
    with gr.Tab("Ask"):
        q = gr.Textbox(label="Question", placeholder="Which SOWs have no liability cap? What's our usual notice period?")
        a = gr.Markdown()
        gr.Button("Ask", variant="primary").click(do_ask, q, a)
        gr.Examples(["Which SOWs are missing a data protection clause?",
                     "What payment terms do we usually agree?",
                     "Which contracts include an audit right, and what notice does it need?"], q)
    with gr.Tab("Clause coverage"):
        with gr.Row():
            ct = gr.Dropdown(CLAUSE_TYPES, value="liability", label="Clause type")
            pr = gr.Radio(["are missing it", "have it"], value="are missing it", label="Show SOWs that")
        summary, table = gr.Markdown(), gr.Dataframe(interactive=False)
        gr.Button("Check", variant="primary").click(do_coverage, [ct, pr], [summary, table])
    with gr.Tab("Draft a SOW"):
        with gr.Row():
            alias = gr.Textbox(label="Client alias", value="Client Z")
            prod = gr.Dropdown(PRODUCTS, value="AEM Sites", label="Product")
            size = gr.Dropdown(["enterprise", "mid-market", "smb"], value="enterprise", label="Size")
            price = gr.Dropdown(["fixed_price", "t_and_m"], value="fixed_price", label="Pricing")
        obj = gr.Textbox(label="Objective", lines=2,
                         placeholder="Migrate 30 market sites to AEM Sites with a shared component library")
        notes, draft = gr.Markdown(), gr.Markdown()
        gr.Button("Draft", variant="primary").click(do_draft, [alias, obj, prod, size, price], [draft, notes])
    with gr.Tab("Library"):
        lib = gr.Dataframe(interactive=False)
        gr.Button("Load").click(library, None, lib)
    with gr.Tab("Eval scores"):
        sc = gr.Markdown()
        gr.Button("Show").click(scores, None, sc)

if __name__ == "__main__":
    pw = os.getenv("DEMO_PASSWORD")       # set as a Space secret so strangers can't spend the API credits
    demo.queue(default_concurrency_limit=2).launch(
        server_name="0.0.0.0", server_port=int(os.getenv("PORT", "7860")),
        auth=("demo", pw) if pw else None)
