"""Web demo (Hugging Face Space). Read-only over the demo database; drafting calls Claude."""
import json
import os
import tempfile
from pathlib import Path

import gradio as gr
import pandas as pd

import search
from answer import ask
from assemble import draft_sow
from config import CLAUSE_TYPES
from review import review_sow

SAMPLES = {"FSI AI pilot (weak)": "demo/review_samples/fsi_ai_pilot_weak.docx",
           "Hospitality AEM (weak subcontracting)": "demo/review_samples/hospitality_aem_weak.docx",
           "Retail Target (strong)": "demo/review_samples/retail_target_strong.docx"}
AUTO = "detect from document"
REVIEW_BANNER = ("**Don't upload confidential client documents.** Uploads are sanitised, sent to the Claude API "
                 "for analysis, held in memory only and discarded after the review. Illustrative, not legal advice.")

SECTORS = ["financial services", "retail", "hospitality", "healthcare", "pharma", "public sector", "education",
           "telecoms", "energy", "utilities", "transport", "logistics", "automotive", "industrial", "consumer goods"]
PRODUCTS = ["Applied AI", "AEM Sites", "AEM Assets", "Target", "Analytics", "Journey Optimizer"]
INTRO = """# SOW Contract Intelligence (v2 demo)
Search, check and draft Statements of Work from a library of **48 fictional SOWs** for invented clients:
38 Adobe implementations and 10 Applied AI engagements run by forward deployed engineers, including
supplier-funded pilots. The delivery register records how each deal went, and whether pilots converted.
New drafts are assembled only from components of deals the delivery register marks as proven, and every
paragraph cites its source. Nothing here is real customer data."""


def _df(rows, cols):
    return pd.DataFrame([{c: r.get(c) for c in cols} for r in rows], columns=cols)


def do_ask(q, backend="Native (pgvector + SQL)"):
    return ask(q, backend="llamaindex" if backend.startswith("LlamaIndex") else "native") if q.strip() else "Type a question."


def do_coverage(clause_type, present):
    rows = search.clause_coverage(clause_type, present=present == "have it")
    return f"**{len(rows)}** SOWs {'have' if present == 'have it' else 'are missing'} a {clause_type.replace('_', ' ')} clause.", \
        _df(rows, ["filename", "client_alias", "start_date", "end_date"])


def do_draft(alias, objective, product, sector, size_band, pricing):
    if not objective.strip():
        return "Describe the objective first.", ""
    d = draft_sow({"client_alias": alias or "New Client", "objective": objective, "products": [product],
                   "sector": sector, "size_band": size_band, "pricing_model": pricing})
    notes = (f"Gaps: {', '.join(d['gaps']) or 'none'}. "
             f"Citation problems fixed by falling back to verbatim text: {len(d['citation_issues'])}.")
    return d["markdown"], notes


def do_review(upload, sample, sector, product, pricing):
    path = upload or SAMPLES.get(sample)
    if not path:
        return "Upload a .docx or .pdf, or pick a sample.", None
    try:
        r = review_sow(path, None if sector == AUTO else sector, None if product == AUTO else product,
                       None if pricing == AUTO else pricing)
    except ValueError as e:
        return str(e), None
    out = Path(tempfile.mkdtemp()) / "sow_review.md"
    out.write_text(r["markdown"])
    return r["markdown"], str(out)


def library():
    rows = search.contract_details()
    for r in rows:
        r["products"] = ", ".join(r["products"] or [])
        r["clauses"] = ", ".join(r["clause_types"])
    return _df(rows, ["filename", "client_alias", "sector", "products", "pricing_model", "contract_value",
                      "currency", "start_date", "end_date", "proven", "delivery_health", "converted",
                      "weeks_to_production", "clauses"])


def scores():
    p = Path(os.getenv("EVAL_RESULTS", "demo/eval_results.json"))
    if not p.exists():
        return "No eval run recorded yet."
    r = json.loads(p.read_text())
    lines = ["| Measure | Score | Target | Cases | Pass |", "|---|---|---|---|---|"]
    lines += [f"| {k.replace('_', ' ')} | {v['score']:.0%} | {v['target']:.0%} | {v['n']} | {'yes' if v['pass'] else 'no'} |"
              for k, v in r.get("scores", r).items()]
    lat = r.get("latency_ms") or {}
    if lat:
        lines.append("\nMedian retrieval latency: " + ", ".join(f"{b} {ms:g} ms" for b, ms in lat.items()) + ".")
    return "\n".join(lines) + (f"\n\nRun on {r['run_at']} with {r['models']}." if "run_at" in r else "")


with gr.Blocks(title="SOW Contract Intelligence") as demo:
    gr.Markdown(INTRO)
    with gr.Tab("Ask"):
        q = gr.Textbox(label="Question", placeholder="Which SOWs have no liability cap? What's our usual notice period?")
        rb = gr.Radio(["Native (pgvector + SQL)", "LlamaIndex (PGVectorStore + fusion)"],
                      value="Native (pgvector + SQL)", label="Retrieval")
        a = gr.Markdown()
        gr.Button("Ask", variant="primary").click(do_ask, [q, rb], a)
        gr.Examples(["How should we define acceptance for an AI agent so it's commercially enforceable?",
                     "What exit criteria hand an AI engagement over to the client's own engineers, and did they work?",
                     "Which supplier-funded pilots converted to paid work, and what did their SOWs have in common?",
                     "Why did some AI engagements take much longer to reach production?",
                     "What are best-practice regulatory assumptions for financial services clients?",
                     "What's the optimum payment schedule for fixed-price retail milestones?",
                     "What subcontracting boilerplate do we use for hospitality clients?"], q)
    with gr.Tab("Clause coverage"):
        with gr.Row():
            ct = gr.Dropdown(CLAUSE_TYPES, value="liability", label="Clause type")
            pr = gr.Radio(["are missing it", "have it"], value="are missing it", label="Show SOWs that")
        summary, table = gr.Markdown(), gr.Dataframe(interactive=False)
        gr.Button("Check", variant="primary").click(do_coverage, [ct, pr], [summary, table])
    with gr.Tab("Draft a SOW"):
        with gr.Row():
            alias = gr.Textbox(label="Client alias", value="Client Z")
            prod = gr.Dropdown(PRODUCTS, value="Applied AI", label="Product")
            sect = gr.Dropdown(SECTORS, value="financial services", label="Industry")
            size = gr.Dropdown(["enterprise", "mid-market", "smb"], value="enterprise", label="Size")
            price = gr.Dropdown(["fixed_price", "t_and_m", "investment"], value="fixed_price", label="Pricing")
        obj = gr.Textbox(label="Objective", lines=2,
                         placeholder="Production AI agent for 12 customer-service intents; evaluation harness and golden set; enablement programme for 4 client engineers")
        notes, draft = gr.Markdown(), gr.Markdown()
        gr.Button("Draft", variant="primary").click(do_draft, [alias, obj, prod, sect, size, price], [draft, notes])
    with gr.Tab("Review a SOW"):
        gr.Markdown(REVIEW_BANNER)
        with gr.Row():
            up = gr.File(label="Upload a SOW (.docx or .pdf, up to 5 MB / 40 pages)", file_types=[".docx", ".pdf"],
                         type="filepath")
            smp = gr.Dropdown(list(SAMPLES), value="FSI AI pilot (weak)", label="...or try a sample")
        with gr.Row():
            rsec = gr.Dropdown([AUTO] + SECTORS, value=AUTO, label="Industry")
            rprod = gr.Dropdown([AUTO] + PRODUCTS, value=AUTO, label="Product")
            rprice = gr.Dropdown([AUTO, "fixed_price", "t_and_m", "investment"], value=AUTO, label="Pricing")
        rmd, rfile = gr.Markdown(), gr.File(label="Download the review")
        gr.Button("Review", variant="primary").click(do_review, [up, smp, rsec, rprod, rprice], [rmd, rfile])
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
