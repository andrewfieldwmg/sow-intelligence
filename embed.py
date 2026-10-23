"""Phase 4: embed chunks and components, then build vector indexes on the loaded data."""
import numpy as np

from config import connect
from llm import embed

BATCH = 100


def fill(cur, table: str, text_col: str) -> int:
    cur.execute(f"SELECT id, {text_col} FROM {table} WHERE embedding IS NULL ORDER BY id")
    rows, done = cur.fetchall(), 0
    for i in range(0, len(rows), BATCH):
        batch = rows[i:i + BATCH]
        vectors = embed([t for _, t in batch])
        cur.executemany(f"UPDATE {table} SET embedding = %s WHERE id = %s",
                        [(np.array(v), rid) for (rid, _), v in zip(batch, vectors)])
        done += len(batch)
    return done


def main():
    conn = connect("writer")
    with conn, conn.cursor() as cur:
        n_chunks = fill(cur, "chunk", "context || ' ' || text")
        n_comps = fill(cur, "component", "coalesce(title, '') || E'\\n' || body")
        # HNSW works on any amount of data and needs no training, unlike IVFFlat on an empty table.
        cur.execute("CREATE INDEX IF NOT EXISTS chunk_vec_idx ON chunk USING hnsw (embedding vector_cosine_ops)")
        cur.execute("CREATE INDEX IF NOT EXISTS component_vec_idx ON component USING hnsw (embedding vector_cosine_ops)")
    print(f"Embedded {n_chunks} chunks and {n_comps} components")


if __name__ == "__main__":
    main()
