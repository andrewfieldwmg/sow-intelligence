"""Phase 3: clause-aware chunks for open questions. Chunks never cross a page, so citations hold."""
import re

from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import CHUNK_OVERLAP, CHUNK_TOKENS, connect

# Split at numbered clauses first, then headings, then paragraphs. Lookaheads keep the number
# with its clause. is_separator_regex=True is required or these are matched as literal strings.
SEPARATORS = [r"\n\n(?=\d+\.\d+\s)", r"\n(?=\d+\.\d+\s)", r"\n\n(?=\d+\.\s)",
              r"\n\n(?=(?:Section|SECTION|Article|ARTICLE)\b)", r"\n\n", r"\n", r" "]

splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
    encoding_name="cl100k_base", chunk_size=CHUNK_TOKENS, chunk_overlap=CHUNK_OVERLAP,
    separators=SEPARATORS, is_separator_regex=True, keep_separator=True)

KEYWORDS = {
    "termination": ["terminate", "termination", "notice period"],
    "payment": ["invoice", "payment terms", "payable", "net 30", "net 60"],
    "liability": ["liability", "indemnif", "consequential", "cap on"],
    "ip": ["intellectual property", "ownership of deliverables", "licence", "license"],
    "sla": ["service level", "sla", "response time", "uptime"],
    "data_protection": ["personal data", "gdpr", "data protection", "processor"],
    "audit": ["audit", "inspection", "records"],
    "change_control": ["change request", "change control", "change order"],
}
PATTERNS = {k: re.compile(r"\b(?:" + "|".join(re.escape(w) for w in ws) + r")", re.I)
            for k, ws in KEYWORDS.items()}


def classify(text: str) -> str | None:
    """Best-effort label used only as a search filter. The clause register is the source of truth."""
    scores = {k: len(p.findall(text)) for k, p in PATTERNS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] else None


def main():
    conn = connect("writer")
    with conn, conn.cursor() as cur:
        # Each chunk carries which deal and section it came from, so "Client A deliverables" can find a
        # page that never names Client A. Context is searched and embedded but never quoted.
        cur.execute("""SELECT p.sow_id, p.page_no, p.text,
                              concat_ws(' | ', s.client_alias, array_to_string(s.products, ', '), s.sector)
                       FROM page p JOIN sow s ON s.id = p.sow_id
                       WHERE NOT EXISTS (SELECT 1 FROM chunk c WHERE c.sow_id = p.sow_id)
                       ORDER BY p.sow_id, p.page_no""")
        rows, n = cur.fetchall(), 0
        idx = {}
        for sow_id, page_no, text, deal in rows:
            first = text.strip().split("\n")[0]
            heading = first if len(first) <= 60 and not re.match(r"\d+\.\d+\s", first) else ""   # a title, not a clause
            for piece in splitter.split_text(text):
                i = idx.get(sow_id, 0)
                cur.execute("""INSERT INTO chunk (sow_id, page_no, chunk_index, clause_type, context, text)
                               VALUES (%s,%s,%s,%s,%s,%s)""",
                            (sow_id, page_no, i, classify(piece), " | ".join(x for x in (deal, heading) if x), piece.strip()))
                idx[sow_id] = i + 1
                n += 1
    print(f"Created {n} chunks")


if __name__ == "__main__":
    main()
