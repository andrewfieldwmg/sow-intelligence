-- schema.sql: run once as the database owner
-- vector(384) matches the local bge-small embeddings; use vector(1536) with text-embedding-3-small.
CREATE EXTENSION IF NOT EXISTS vector;

-- One row per sanitised SOW. "proven" comes from the delivery register, not the model.
CREATE TABLE IF NOT EXISTS sow (
    id              SERIAL PRIMARY KEY,
    filename        TEXT NOT NULL,
    file_sha256     TEXT NOT NULL UNIQUE,          -- makes ingestion idempotent
    client_alias    TEXT,                          -- pseudonym only, never the real name
    sector          TEXT,
    size_band       TEXT,                          -- e.g. 'enterprise', 'mid-market'
    products        TEXT[] DEFAULT '{}',
    pricing_model   TEXT,                          -- 'fixed_price' | 't_and_m' | 'mixed'
    contract_value  NUMERIC,
    currency        TEXT,
    start_date      DATE,
    end_date        DATE,
    proven          BOOLEAN NOT NULL DEFAULT FALSE,
    delivery_health TEXT,                          -- from register.csv: green / amber / red
    margin_band     TEXT,                          -- from register.csv: above / on / below target
    csat            NUMERIC,
    extracted_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- Page text (PDF page, or Word Heading-1 section) so every citation can point somewhere.
CREATE TABLE IF NOT EXISTS page (
    sow_id  INT REFERENCES sow(id) ON DELETE CASCADE,
    page_no INT NOT NULL,
    text    TEXT NOT NULL,
    PRIMARY KEY (sow_id, page_no)
);

-- Clause register: one row per clause, so coverage questions are answered with SQL, not top-k.
CREATE TABLE IF NOT EXISTS clause (
    id          SERIAL PRIMARY KEY,
    sow_id      INT REFERENCES sow(id) ON DELETE CASCADE,
    clause_type TEXT NOT NULL,                     -- termination, payment, liability, ip, sla, data_protection, audit, change_control
    summary     TEXT,
    key_value   TEXT,                              -- e.g. '30 days', '1x annual fees'
    quote       TEXT NOT NULL,                     -- verbatim text, checked against the source
    page_no     INT
);

-- Component library: verbatim, reusable building blocks for new SOWs.
CREATE TABLE IF NOT EXISTS component (
    id        SERIAL PRIMARY KEY,
    sow_id    INT REFERENCES sow(id) ON DELETE CASCADE,
    section   TEXT NOT NULL,                       -- see SECTIONS in config.py
    title     TEXT,
    body      TEXT NOT NULL,                       -- verbatim text, checked against the source
    product   TEXT,
    effort    JSONB DEFAULT '{}',                  -- hours by role, e.g. {"architect": 40, "pm": 12}
    page_no   INT,
    embedding vector(384)
);

-- Retrieval chunks for open questions about contract text.
CREATE TABLE IF NOT EXISTS chunk (
    id          SERIAL PRIMARY KEY,
    sow_id      INT REFERENCES sow(id) ON DELETE CASCADE,
    page_no     INT,
    chunk_index INT NOT NULL,
    clause_type TEXT,
    text        TEXT NOT NULL,
    tsv         tsvector GENERATED ALWAYS AS (to_tsvector('english', text)) STORED,
    embedding   vector(384)
);
CREATE INDEX IF NOT EXISTS chunk_tsv_idx ON chunk USING gin (tsv);
CREATE INDEX IF NOT EXISTS clause_type_idx ON clause (clause_type);
CREATE INDEX IF NOT EXISTS component_section_idx ON component (section);
-- Vector (HNSW) indexes are created by embed.py after data is loaded.

-- Read-only role for the MCP server and the query CLI.
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'sow_reader') THEN
        CREATE ROLE sow_reader LOGIN PASSWORD 'change-me';
    END IF;
END $$;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO sow_reader;
