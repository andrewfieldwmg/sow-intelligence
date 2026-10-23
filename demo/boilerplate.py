"""Contract boilerplate for the fictional demo corpus. Illustrative only, not legal advice.

Written to read like English-law professional services paper. Where a clause matters for the demo
questions there is a strong version (clear, objective, enforceable) and a weak version (vague or
one-sided), so the app can compare precedents against delivery outcomes.
"""

SUPPLIER = ("Arkwright Digital Services Limited", "09871234", "4th Floor, 12 Cardinal Place, London EC2A 4BX")
FOOTER = "Illustrative only. Not legal advice. All parties, people and figures are fictional."


def definitions(strong: bool) -> list[str]:
    d = [
        '"Acceptance" means confirmation, given or deemed under clause 7, that a Deliverable meets its Acceptance Criteria, and "Accept" and "Accepted" are construed accordingly.',
        '"Acceptance Criteria" means the objective, measurable criteria for each Deliverable set out in Schedule 3, as updated by agreement in writing.',
        '"Acceptance Tests" means the tests set out in the Acceptance Test Plan, used to establish whether a Deliverable meets its Acceptance Criteria.',
        '"Business Day" means a day other than a Saturday, Sunday or public holiday in England.',
        '"Change Request" means a written request to change the Services, a Deliverable, the timetable or the Charges, made under clause 8.',
        '"Deliverable" means each output of the Services listed in Schedule 1.',
        '"Key Personnel" means the individuals named as such in clause 5.1, or their approved replacements.',
        '"Milestone" means an event or date set out in Schedule 2 to which a payment or a Deliverable is linked.',
        '"Subcontractor" means any third party engaged by the Supplier to perform any part of the Services.',
        '"Regulator" means any body with regulatory or supervisory authority over the Client, including the Financial Conduct Authority and the Prudential Regulation Authority.',
        '"Confidential Information" means all information disclosed by or on behalf of a party that is marked confidential or would reasonably be regarded as confidential.',
    ]
    if strong:
        d += [
            '"Non-Conformity" means a failure of a Deliverable to meet its Acceptance Criteria that can be reproduced by following the steps recorded in a Non-Conformity Notice.',
            '"Severity 1" means a Non-Conformity that stops a critical business process or causes loss or corruption of data, with no workaround.',
            '"Severity 2" means a Non-Conformity that materially degrades a critical business process, where a workaround exists but is not sustainable for more than five Business Days.',
            '"Severity 3" means a Non-Conformity that affects a non-critical function, or a critical function where a reasonable workaround exists.',
            '"Severity 4" means a cosmetic or documentation Non-Conformity that does not affect the operation of the Deliverable.',
        ]
    else:
        d += ['"Defect" means any error or fault in a Deliverable identified by the Client.']
    return d


def acceptance(strong: bool) -> list[str]:
    if strong:
        return [
            "Acceptance Test Plan. The Supplier will deliver a draft Acceptance Test Plan for each Deliverable at least ten Business Days before testing starts. The Client will approve it or give reasoned comments within five Business Days, and approval will not be unreasonably withheld or delayed.",
            "Testing. The Client will run the Acceptance Tests within the test window of ten Business Days after the Supplier notifies it that the Deliverable is ready for testing. The Supplier may attend.",
            "Non-Conformity Notice. If a Deliverable fails an Acceptance Test, the Client will give the Supplier a Non-Conformity Notice within the test window, identifying each Non-Conformity, its proposed severity, and the steps needed to reproduce it.",
            "Remediation. The Supplier will correct each Severity 1 and Severity 2 Non-Conformity and resubmit the Deliverable within five Business Days of the Non-Conformity Notice, or within such longer period as the parties agree, after which the relevant Acceptance Tests are repeated.",
            "Minor Non-Conformities. Severity 3 and Severity 4 Non-Conformities do not prevent Acceptance. They are logged and corrected in the next scheduled release.",
            "Deemed Acceptance. A Deliverable is deemed Accepted on the earliest of: (a) the Client confirming Acceptance in writing; (b) the end of the test window, if no Non-Conformity Notice identifying a Severity 1 or Severity 2 Non-Conformity has been given; or (c) the Client using the Deliverable in live operation for any purpose other than testing.",
            "Repeated failure. If a Deliverable fails the same Acceptance Test for a Severity 1 or Severity 2 reason after two remediation cycles, either party may refer the matter for resolution under clause 12.2, and the Client may, as its sole remedy for that failure, accept the Deliverable subject to a reasonable reduction in the Charges, or reject it and recover the Charges paid for it.",
            "Partial Acceptance. The Client may Accept part of a Deliverable where that part can be used independently, and the Charges for that Milestone will be apportioned accordingly.",
        ]
    return [
        "Acceptance. The Supplier will present each Deliverable to the Client for review. The Client will accept each Deliverable when it is satisfied, acting reasonably, that the Deliverable meets its requirements.",
        "Defects. The Supplier will correct any Defect notified by the Client as soon as reasonably practicable.",
    ]


def liability(strong: bool, cap_multiple: float, currency: str, data_cap: int) -> list[str]:
    out = [
        "Unlimited liability. Nothing in this SOW limits or excludes either party's liability for death or personal injury caused by negligence, fraud or fraudulent misrepresentation, or any other liability that cannot be limited or excluded by law.",
        "Excluded losses. Subject to clause 9.1, neither party is liable for any loss of profits, revenue, business or goodwill, or for any indirect or consequential loss, in each case however arising.",
    ]
    if strong:
        out += [
            f"Liability cap. Subject to clauses 9.1 and 9.2, each party's total aggregate liability arising under or in connection with this SOW is limited to {cap_multiple:g} times the total Charges paid or payable under this SOW.",
            f"Data protection cap. Each party's total liability for breach of clause 10.1 is subject to a separate cap of {currency} {data_cap:,}, which is in addition to the cap in clause 9.3.",
            "Indemnities. The Supplier will indemnify the Client against all losses arising from any claim that the Deliverables infringe the intellectual property rights of a third party, except to the extent the claim arises from materials or instructions provided by the Client. The indemnified party will notify the claim promptly, allow the indemnifying party to conduct it, and give reasonable assistance at the indemnifying party's cost.",
            "Insurance. The Supplier will maintain, with reputable insurers, professional indemnity insurance of at least GBP 5,000,000 per claim, public liability insurance of at least GBP 5,000,000 and cyber insurance of at least GBP 2,000,000, and will provide evidence of cover on request.",
        ]
    else:
        out += ["Liability cap. The Supplier's total liability under this SOW is limited to the Charges paid in the three months before the claim."]
    return out


def compliance(sector_reg: list[str]) -> list[str]:
    out = [
        "Data protection. Where the Supplier processes personal data on the Client's behalf it acts as processor, will process it only on the Client's documented instructions, and will comply with UK GDPR and the data processing agreement in the MSA.",
        "Confidentiality. Each party will keep the other's Confidential Information confidential, use it only to perform or receive the Services, and disclose it only to its personnel, professional advisers and Subcontractors who need to know it and are bound by equivalent obligations. These obligations survive termination for five years.",
        "Anti-bribery and modern slavery. Each party will comply with the Bribery Act 2010 and the Modern Slavery Act 2015, maintain adequate procedures to prevent breaches of them, and notify the other promptly of any breach in connection with this SOW.",
    ]
    return out + sector_reg


def termination_exit(strong: bool, notice_days: int, regulated: bool = False) -> list[str]:
    if strong:
        reg = (["Regulatory direction. The Client may terminate this SOW, in whole or in part, without liability for "
                "wind-down fees, if a Regulator directs or formally requires it to do so."] if regulated else [])
        return [
            f"Termination for convenience. The Client may terminate this SOW for convenience on {notice_days} days' written notice. The Client will pay the Charges for work performed up to the termination date and any committed, non-cancellable costs, and, for fixed price SOWs, a wind-down fee of 5% of the Charges for unstarted Milestones.",
            "Termination for cause. Either party may terminate this SOW with immediate effect by written notice if the other party: (a) commits a material breach that is irremediable or, if remediable, is not remedied within 30 days of a written notice requiring it; (b) commits persistent breaches that together amount to a material breach; (c) suffers an insolvency event; or (d) undergoes a change of control in favour of a competitor of the terminating party.",
            *reg,
            "Effect of termination. On termination the Supplier will stop work, deliver all work in progress and documentation for which the Client has paid, and each party will return or securely destroy the other's Confidential Information. Clauses 9, 10 and 12 and this clause 11 survive termination.",
            "Exit plan. Within 60 days of the start date the Supplier will deliver an exit plan, set out in Schedule 4, covering the handover of the Services, documentation, data and knowledge to the Client or a replacement supplier. The Supplier will review the exit plan annually and on any material change.",
            "Exit assistance. For up to six months after termination or expiry the Supplier will provide the exit assistance in the exit plan, including up to ten days of knowledge transfer at no extra charge and further transitional assistance at the rates in Schedule 2. Within 30 days of the end of exit assistance the Supplier will return or securely delete all Client data and certify that it has done so.",
        ]
    return [
        f"Termination. Either party may terminate this SOW on {notice_days} days' written notice.",
        "Exit. On termination the parties will agree in good faith any handover arrangements needed at the time.",
    ]


def general(strong: bool, law: str, courts: str) -> list[str]:
    out = [
        "Force majeure. Neither party is liable for delay or failure to perform caused by events beyond its reasonable control, provided it notifies the other promptly and uses reasonable endeavours to mitigate the effect. If an event of force majeure continues for more than 60 days, either party may terminate the affected Services on written notice.",
    ]
    if strong:
        out += [
            "Dispute resolution. A dispute is first referred to the project managers, then, if unresolved within ten Business Days, to the steering committee, and then, if unresolved within a further ten Business Days, to the parties' executive sponsors. If the dispute is not resolved within 20 Business Days of referral to the executive sponsors, either party may refer it to mediation under the CEDR Model Mediation Procedure. Nothing in this clause prevents a party seeking urgent injunctive relief.",
            "Key Personnel and non-solicitation. The Supplier will not remove or replace Key Personnel without the Client's prior written consent, except for illness, resignation or termination of employment, and will provide a replacement of equivalent skill within ten Business Days. Neither party will, during the term and for six months after it, solicit for employment any person engaged in the Services by the other, other than through general advertising.",
        ]
    else:
        out += ["Disputes. The parties will try to resolve any dispute amicably."]
    out += [
        f"Governing law and jurisdiction. This SOW and any dispute arising from it are governed by the law of {law}, and the courts of {courts} have exclusive jurisdiction.",
        "Order of precedence. If there is a conflict, the following order of precedence applies: the MSA, then the body of this SOW, then its Schedules, except where this SOW expressly states that a provision overrides the MSA.",
        "Entire agreement. This SOW and the MSA constitute the entire agreement between the parties about their subject matter. Each party acknowledges that it has not relied on any statement not set out in them.",
        "Notices and counterparts. Notices must be in writing and sent to the addresses on the cover page or by email to the named contract managers. This SOW may be signed in counterparts and by electronic signature.",
    ]
    return out


# Supplier-funded engagements: the commercial terms are about proving value and converting.
INVESTMENT_STRONG = [
    "Investment and conversion. No fees are payable for the Services, which the Supplier funds as an investment. The engagement is time-boxed to eight weeks. Success means meeting the success criteria in Schedule 3, which are measured against the baseline agreed at mobilisation: at least one use case in production with live users, a documented reduction in handling time of 20% or more, and sign-off by the executive sponsor. The Client commits a named product owner for two days a week and production access by week two. Within ten Business Days of the final readout, the Client's executive sponsor will decide whether to proceed to the paid phase described in Schedule 2, which is priced at the rates in the MSA.",
    "Investment and conversion. The Supplier funds the Services up to an investment cap of 40 days. Success criteria, owners and the decision date are agreed in a mutual success plan at kick-off, and progress is reviewed fortnightly with the executive sponsor. If the success criteria are met, the Client will sign the follow-on SOW for the production rollout within 30 days of the readout. If the Client does not proceed, the Supplier may publish an anonymised case study with the Client's approval, not to be unreasonably withheld.",
]
INVESTMENT_WEAK = [
    "Investment. No fees are payable. The Supplier will explore AI use cases with the Client's teams and share recommendations at the end of the engagement.",
]


# Applied AI engagements. The strong versions are what a forward deployed team needs to get to
# production and hand over; the weak versions are how pilots stall.
def ai_acceptance(strong: bool) -> list[str]:
    if strong:
        return ["AI acceptance. A Deliverable that includes a model-based component is Accepted against the evaluation "
                "thresholds in Schedule 3, measured on the agreed golden set of at least 200 cases held back from "
                "development: task accuracy of at least 90%, correct escalation to a human on at least 98% of "
                "out-of-policy cases, and no Severity 1 safety failure. Results must be reproducible from the evaluation "
                "harness delivered with the Deliverable, and the Client may re-run it at any time during the test window."]
    return ["AI acceptance. The AI solution will be accepted when the Client is satisfied with the quality of its responses."]


def ai_governance(strong: bool, eu: bool, fsi: bool = False) -> list[str]:
    if not strong:
        return ["AI governance. The Supplier will use reasonable endeavours to ensure the AI solution produces accurate results."]
    out = [
        "AI governance: human oversight. The operating model in Schedule 5 lists the decisions the AI solution may take "
        "without human review. Every other output is reviewed by a trained member of the Client's staff before it "
        "affects a customer, and the Client can switch any automated decision back to human review at any time.",
        "AI governance: model and data. Client Data is not used to train any third-party model. The Supplier will give "
        "the Client at least 30 days' notice of any change to the underlying model version in production and will "
        "re-run the evaluation suite, sharing the results, before the change goes live.",
        "AI governance: outputs. The Supplier warrants that the solution meets the evaluation thresholds in Schedule 3 at "
        "Acceptance. It does not warrant that every individual output will be accurate, and the Client remains "
        "responsible for decisions it makes using the outputs.",
    ]
    if fsi:
        out.append("AI governance: model risk. The Client will treat the solution as a model under its model risk "
                   "management framework, consistent with PRA Supervisory Statement SS1/23. The Supplier will provide "
                   "model documentation, evaluation results and monitoring metrics so the Client can validate the "
                   "solution before go-live and monitor its performance afterwards.")
    if eu:
        out.append("AI governance: EU AI Act. The parties will assess together whether the solution is a high-risk AI "
                   "system under Regulation (EU) 2024/1689. If it is, the Supplier will provide the technical "
                   "documentation and logs the Client needs to meet its obligations as deployer.")
    return out


def knowledge_transfer(strong: bool) -> list[str]:
    if strong:
        return ["Knowledge transfer and exit criteria. The engagement ends when the exit criteria in Schedule 3 are met: "
                "the Client's named engineers have (a) deployed a change to the production solution without Supplier "
                "help, (b) run the evaluation suite and acted on its results, and (c) shipped a second use case from the "
                "starter repository with Supplier review only. Supplier staffing steps down from the full team to one "
                "advisory engineer once criteria (a) and (b) are met."]
    return ["Knowledge transfer. The Supplier will hold handover sessions with the Client's team at the end of the engagement."]
