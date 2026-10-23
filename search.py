"""Read-only query functions shared by the MCP server, the CLI and the evals.

Coverage and listing questions go to SQL over the clause register, so the answer is complete.
Only open "what does the text say" questions go to retrieval.
"""
import numpy as np

from config import CLAUSE_TYPES, connect
from llm import embed

_conn = None


def conn():
    global _conn
    if _conn is None or _conn.closed:
        _conn = connect("reader")
        _conn.rollback()                         # register_vector opened a transaction
        _conn.set_session(readonly=True, autocommit=True)
    return _conn


def _rows(sql, params=()):
    with conn().cursor() as cur:
        cur.execute(sql, params or None)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def search_text(query: str, k: int = 8, clause_type: str | None = None,
                sow_id: int | None = None) -> list[dict]:
    """Hybrid search: vector and keyword rankings fused with reciprocal rank fusion (RRF)."""
    qv = np.array(embed([query], query=True)[0])
    filt, params = "", []
    if clause_type:
        filt += " AND c.clause_type = %s"
        params.append(clause_type)
    if sow_id:
        filt += " AND c.sow_id = %s"
        params.append(sow_id)
    sql = f"""
    WITH vec AS (
        SELECT c.id, row_number() OVER (ORDER BY c.embedding <=> %s) AS r
        FROM chunk c WHERE c.embedding IS NOT NULL {filt}
        ORDER BY c.embedding <=> %s LIMIT 50),
    kw AS (
        SELECT c.id, row_number() OVER (ORDER BY ts_rank(c.tsv, q) DESC) AS r
        FROM chunk c, websearch_to_tsquery('english', %s) q
        WHERE c.tsv @@ q {filt} LIMIT 50),
    fused AS (
        SELECT id, sum(1.0 / (60 + r)) AS score
        FROM (SELECT * FROM vec UNION ALL SELECT * FROM kw) u GROUP BY id)
    SELECT c.id AS chunk_id, s.id AS sow_id, s.filename, s.client_alias, c.page_no,
           c.clause_type, c.text, round(f.score::numeric, 4) AS score
    FROM fused f JOIN chunk c ON c.id = f.id JOIN sow s ON s.id = c.sow_id
    ORDER BY f.score DESC LIMIT %s"""
    return _rows(sql, [qv, *params, qv, query, *params, k])


def clause_coverage(clause_type: str, present: bool = False) -> list[dict]:
    """Every SOW missing (or having) a clause type. Complete by construction: no top-k cut-off."""
    if clause_type not in CLAUSE_TYPES:
        raise ValueError(f"clause_type must be one of {CLAUSE_TYPES}")
    op = "EXISTS" if present else "NOT EXISTS"
    return _rows(f"""
        SELECT s.id AS sow_id, s.filename, s.client_alias, s.start_date, s.end_date
        FROM sow s
        WHERE {op} (SELECT 1 FROM clause c WHERE c.sow_id = s.id AND c.clause_type = %s)
        ORDER BY s.filename""", (clause_type,))


def contract_details(sow_id: int | None = None, expiring_within_days: int | None = None,
                     product: str | None = None) -> list[dict]:
    where, params = ["TRUE"], []
    if sow_id:
        where.append("s.id = %s"); params.append(sow_id)
    if expiring_within_days is not None:
        where.append("s.end_date BETWEEN current_date AND current_date + %s"); params.append(expiring_within_days)
    if product:
        where.append("%s ILIKE ANY (s.products)"); params.append(product)
    sows = _rows(f"""SELECT s.id AS sow_id, s.filename, s.client_alias, s.sector, s.size_band,
                            s.products, s.pricing_model, s.contract_value, s.currency,
                            s.start_date, s.end_date, s.proven, s.delivery_health, s.margin_band
                     FROM sow s WHERE {' AND '.join(where)} ORDER BY s.end_date NULLS LAST""", params)
    for s in sows:
        s["clauses"] = _rows("""SELECT clause_type, key_value, summary, quote, page_no
                                FROM clause WHERE sow_id = %s ORDER BY clause_type""", (s["sow_id"],))
    return sows


def find_components(query: str, section: str | None = None, product: str | None = None,
                    size_band: str | None = None, pricing_model: str | None = None,
                    proven_only: bool = True, k: int = 5,
                    exclude_filenames: list[str] | None = None) -> list[dict]:
    """Reusable blocks from past SOWs, nearest first. By default only SOWs the register marks proven."""
    qv = np.array(embed([query], query=True)[0])
    where, params = ["c.embedding IS NOT NULL"], []
    if proven_only:
        where.append("s.proven")
    if exclude_filenames:                                 # used by the evals to hold out a deal
        where.append("NOT (s.filename = ANY(%s))"); params.append(list(exclude_filenames))
    if product:                                           # generic components (no product) still qualify
        where.append("(c.product = %s OR c.product IS NULL)"); params.append(product)
    for col, val in (("c.section", section), ("s.size_band", size_band), ("s.pricing_model", pricing_model)):
        if val:
            where.append(f"{col} = %s"); params.append(val)
    return _rows(f"""
        SELECT c.id AS component_id, c.section, c.title, c.body, c.product, c.effort, c.page_no,
               s.id AS sow_id, s.filename, s.client_alias, s.delivery_health, s.margin_band,
               round((1 - (c.embedding <=> %s))::numeric, 3) AS similarity
        FROM component c JOIN sow s ON s.id = c.sow_id
        WHERE {' AND '.join(where)}
        ORDER BY c.embedding <=> %s LIMIT %s""", [qv, *params, qv, k])
