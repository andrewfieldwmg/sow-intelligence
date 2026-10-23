"""Builds the fictional demo corpus: 18 SOWs (Word and PDF) for invented clients, plus the alias
map, the delivery register and a golden eval set whose answers are known by construction.
Every company, person and number here is made up."""
import csv
import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path

from docx import Document
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "demo")
rng = random.Random(42)

CLIENTS = [  # invented names, each mapped to an alias
    ("Halden Retail Group plc", "retail", "enterprise"), ("Brackwater Building Society", "financial services", "enterprise"),
    ("Corrin Motors Ltd", "automotive", "enterprise"), ("Felsham Pharma AG", "pharma", "enterprise"),
    ("Marlowe Leisure Parks", "travel and leisure", "mid-market"), ("Ostrava Components plc", "industrial", "enterprise"),
    ("Pellow Home Stores", "retail", "mid-market"), ("Quillon Insurance plc", "financial services", "enterprise"),
    ("Ravensby Telecom", "telecoms", "enterprise"), ("Stirlow Foods Ltd", "consumer goods", "mid-market"),
    ("Tamsin Optics GmbH", "healthcare", "mid-market"), ("Ulverton Energy plc", "energy", "enterprise"),
    ("Vexley Fashion Ltd", "retail", "mid-market"), ("Wendover Rail", "transport", "enterprise"),
    ("Yardley Learning Trust", "education", "smb"), ("Zennor Hotels Ltd", "travel and leisure", "mid-market"),
    ("Ashcombe Distribution", "logistics", "mid-market"), ("Belmont Mutual", "financial services", "enterprise"),
]
CONTACTS = ["Priya Natarajan", "Tom Ellery", "Sian Morgan", "Lukas Brandt", "Ana Ferreira", "Dev Malhotra"]

PRODUCTS = {
    "AEM Sites": {
        "deliverables": [
            ("component library of {n} reusable AEM Sites components built to the agreed design system", {"architect": 60, "developer": 420, "qa": 80}),
            ("migration of {n} pages from the legacy CMS to AEM Sites as a Cloud Service, including redirects", {"developer": 260, "qa": 60}),
            ("headless delivery of content to the existing React front end using AEM content fragments and GraphQL", {"architect": 40, "developer": 220}),
            ("multi-site manager set-up for {n} markets with language copies and a translation workflow", {"architect": 30, "developer": 160, "qa": 40}),
        ],
        "assumptions": ["The Client supplies final designs in Figma before the build sprint for each template starts.",
                        "Content owners in each market are available to sign off migrated pages within five working days.",
                        "The Client's existing CDN and DNS changes are made by the Client's infrastructure team."],
        "out_of_scope": ["Changes to the React front end beyond consuming the agreed GraphQL endpoints.",
                         "Translation of content, which the Client's agency provides."],
    },
    "AEM Assets": {
        "deliverables": [
            ("metadata schema and folder taxonomy for {n} asset types, agreed with brand and legal", {"architect": 30, "consultant": 60}),
            ("automated asset ingestion and approval workflow from the creative agency into AEM Assets", {"architect": 20, "developer": 140, "qa": 30}),
            ("Brand Portal set-up so that {n} partner agencies can download approved assets", {"developer": 60, "consultant": 20}),
        ],
        "assumptions": ["The Client migrates historic assets using its own team; the Supplier provides the migration scripts.",
                        "Rights and expiry data exists for every asset to be migrated."],
        "out_of_scope": ["Migration of video assets over 2GB.", "Integration with third-party digital asset managers."],
    },
    "Target": {
        "deliverables": [
            ("{n} personalisation activities in Adobe Target, from hypothesis to live test and readout", {"consultant": 120, "developer": 80}),
            ("audience strategy linking Target to the Client's customer data platform for real-time segments", {"architect": 40, "consultant": 60}),
            ("testing playbook and prioritisation framework handed over to the Client's optimisation team", {"consultant": 40}),
        ],
        "assumptions": ["The Client's data layer is already implemented on all in-scope pages.",
                        "Traffic volumes support statistically valid tests within four weeks per activity."],
        "out_of_scope": ["Building or changing the customer data platform.", "Creative production for test variants."],
    },
    "Analytics": {
        "deliverables": [
            ("solution design reference and data layer specification for {n} key journeys", {"architect": 50, "consultant": 70}),
            ("Adobe Analytics implementation through Adobe Launch tags, with QA across all in-scope journeys", {"developer": 160, "qa": 60}),
            ("{n} Analysis Workspace dashboards for marketing, ecommerce and leadership", {"consultant": 90}),
        ],
        "assumptions": ["The Client's developers implement the data layer to the specification.",
                        "One reporting suite per market is sufficient."],
        "out_of_scope": ["Historic data migration from the previous analytics tool."],
    },
    "Journey Optimizer": {
        "deliverables": [
            ("{n} lifecycle journeys in Adobe Journey Optimizer, including welcome, browse abandonment and renewal", {"architect": 40, "developer": 200, "consultant": 60}),
            ("email and push templates built to the brand guidelines, with dynamic content blocks", {"developer": 120, "qa": 40}),
            ("consent and frequency rules aligned with the Client's preference centre", {"architect": 20, "consultant": 30}),
        ],
        "assumptions": ["Customer profile and event data is available in Adobe Experience Platform before journey build starts.",
                        "The Client's ESP domains are warmed before go-live."],
        "out_of_scope": ["SMS channel set-up.", "Decommissioning of the previous email platform."],
    },
}
STAFFING = "The Supplier will provide a delivery team of an engagement manager, a solution architect and {dev} developers, with QA support as needed."
GOVERNANCE = "Weekly status meetings review progress, RAID and budget, and a monthly steering committee with the Client sponsor approves changes to priorities."
ACCEPTANCE = "Each deliverable is accepted when the Client confirms in writing that it meets the acceptance criteria, or ten working days after delivery if no defects are raised."
CHANGE = "Any change to scope, timeline or fees is handled through a written change request, assessed by the Supplier within five working days and approved by both parties before work starts."
LEGAL = {
    "termination": ["Either party may terminate this SOW for convenience on {d} days' written notice; fees for work performed up to the termination date remain payable.",
                    "Either party may terminate this SOW immediately by written notice if the other commits a material breach that is not remedied within {d} days."],
    "liability": ["Each party's total liability under this SOW is limited to the fees paid or payable in the twelve months before the claim.",
                  "The Supplier's total liability under this SOW is capped at {m} times the total fees, excluding liability for death, personal injury or fraud."],
    "ip": ["The Client owns all deliverables created specifically for it under this SOW on payment of the relevant fees; the Supplier retains its pre-existing tools and know-how."],
    "data_protection": ["Where the Supplier processes personal data on the Client's behalf it acts as processor under the data processing agreement in the master services agreement, and complies with UK GDPR."],
    "sla": ["During hypercare the Supplier responds to priority one incidents within four hours and priority two incidents within one working day."],
    "audit": ["The Client may audit the Supplier's time records for this SOW once per year on thirty days' notice."],
}


def build():
    (OUT / "sows").mkdir(parents=True, exist_ok=True)
    aliases, register, golden = [], [], []
    letters = "ABCDEFGHIJKLMNOPQR"
    for i, (name, sector, size) in enumerate(CLIENTS):
        alias = f"Client {letters[i]}"
        aliases.append((name, alias))
        short = name.split()[0]
        if short not in ("Belmont",):
            aliases.append((short, alias))
        product = list(PRODUCTS)[i % len(PRODUCTS)]
        p = PRODUCTS[product]
        year = 2022 + i % 4
        start = date(year, 1 + (i * 5) % 12, 1)
        end = start + timedelta(days=rng.choice([120, 180, 240, 300]))
        pricing = rng.choice(["fixed_price", "fixed_price", "t_and_m"])
        dels = rng.sample(p["deliverables"], k=min(len(p["deliverables"]), rng.choice([2, 3])))
        effort_total, del_lines = {}, []
        for text, eff in dels:
            n = rng.choice([4, 6, 8, 12, 20, 40])
            scale = rng.choice([0.8, 1.0, 1.25])
            hrs = {r: round(h * scale) for r, h in eff.items()}
            for r, h in hrs.items():
                effort_total[r] = effort_total.get(r, 0) + h
            role_txt = ", ".join(f"{r.upper() if len(r) <= 2 else r.title()} {h}h" for r, h in hrs.items())
            del_lines.append(f"The Supplier will deliver a {text.format(n=n)} (estimated effort: {role_txt}).")
        pm = round(sum(effort_total.values()) * rng.choice([0.10, 0.12, 0.15]))
        effort_total["pm"] = pm
        rate = rng.choice([1050, 1150, 1250])
        value = round(sum(effort_total.values()) / 8 * rate, -3)
        currency = "GBP" if i % 5 else "EUR"
        clauses = ["termination", "ip"] + [c for c in ("liability", "data_protection", "sla", "audit") if rng.random() < 0.7]
        if i in (3, 10):
            clauses = [c for c in clauses if c != "liability"]   # guarantee some gaps
        contact = CONTACTS[i % len(CONTACTS)]
        pages = [
            ("1. Overview", [
                f"1.1 This Statement of Work describes the {product} services the Supplier will provide to {name} (the Client).",
                f"1.2 The engagement starts on {start.isoformat()} and ends on {end.isoformat()}.",
                f"1.3 The Client's project sponsor is {contact} ({contact.split()[0].lower()}@{short.lower()}.example, +44 20 7946 {1000 + i:04d}).",
                (f"1.4 Total fixed price: {currency} {value:,.0f}, invoiced against milestones." if pricing == "fixed_price"
                 else f"1.4 Services are charged on a time and materials basis at a blended day rate of {currency} {rate:,}, with an estimated total of {currency} {value:,.0f}."),
            ]),
            ("2. Deliverables", [f"2.{k + 1} {d}" for k, d in enumerate(del_lines)]),
            ("3. Assumptions and exclusions",
             [f"3.{k + 1} Assumption: {a}" for k, a in enumerate(rng.sample(p["assumptions"], k=min(2, len(p["assumptions"]))))]
             + [f"3.{k + 3} Out of scope: {o}" for k, o in enumerate(p["out_of_scope"][:1])]),
            ("4. Staffing and governance", [
                f"4.1 Staffing: {STAFFING.format(dev=rng.choice([2, 3, 4]))} Engagement management is estimated at PM {pm}h.",
                f"4.2 Governance: {GOVERNANCE}"]),
            ("5. Commercial terms", [
                f"5.1 Payment: invoices are payable within {rng.choice([30, 45, 60])} days of receipt.",
                f"5.2 Acceptance: {ACCEPTANCE}",
                f"5.3 Change control: {CHANGE}"]),
            ("6. Legal terms", [
                f"6.{k + 1} {rng.choice(LEGAL[c]).format(d=rng.choice([30, 60, 90]), m=rng.choice([1, 1.5, 2]))}"
                for k, c in enumerate(clauses)]),
        ]
        stem = f"{alias.lower().replace(' ', '_')}_{product.lower().replace(' ', '_')}_{year}"   # files are named by alias
        fname = stem + (".pdf" if i % 3 == 2 else ".docx")
        if fname.endswith(".docx"):
            doc = Document()
            for head, lines in pages:
                doc.add_heading(head, level=1)
                for l in lines:
                    doc.add_paragraph(l)
            doc.save(OUT / "sows" / fname)
        else:
            styles = getSampleStyleSheet()
            story = []
            for head, lines in pages:
                story.append(Paragraph(head, styles["Heading1"]))
                story += [Paragraph(l, styles["Normal"]) for l in lines]
                story.append(PageBreak())
            SimpleDocTemplate(str(OUT / "sows" / fname), pagesize=A4).build(story[:-1])
        health = "red" if i in (4, 11, 15) else rng.choice(["green", "green", "amber"])
        register.append({"filename": fname, "proven": str(health != "red").lower(), "delivery_health": health,
                         "margin_band": {"green": "on", "amber": rng.choice(["on", "below"]), "red": "below"}[health],
                         "csat": {"green": rng.choice([9, 10]), "amber": rng.choice([7, 8]), "red": 6}[health]})
        golden.append({"type": "extraction", "filename": fname,
                       "expect": {"pricing_model": pricing, "currency": currency,
                                  "start_date": start.isoformat(), "end_date": end.isoformat()}})
        golden.append({"type": "retrieval", "query": f"{alias} {product} " + " ".join(dels[0][0].format(n="").split()[:6]),
                       "expect": {"filename": fname, "page": 2}})
        if i % 3 == 0:
            golden.append({"type": "draft", "brief": {"client_alias": "Client Z", "objective": dels[0][0].format(n=10),
                           "products": [product], "size_band": size, "pricing_model": pricing,
                           "exclude_filenames": [fname]},   # hold out the source deal so it can't be copied
                           "reference_hours": sum(effort_total.values())})
        register[-1]["_clauses"] = clauses
    for ct in LEGAL:
        golden.append({"type": "coverage", "clause_type": ct,
                       "expect_missing": [r["filename"] for r in register if ct not in r["_clauses"]]})
    for r in register:
        del r["_clauses"]
    with open(OUT / "alias_map.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["real", "alias"]); w.writerows(aliases)
        w.writerows([(c, "[person]") for c in CONTACTS])
    with open(OUT / "register.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(register[0])); w.writeheader(); w.writerows(register)
    (OUT / "golden.jsonl").write_text("\n".join(json.dumps(g) for g in golden) + "\n")
    print(f"{len(CLIENTS)} SOWs, {len(golden)} golden cases -> {OUT}")


if __name__ == "__main__":
    build()
