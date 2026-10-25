"""A second retrieval path built on LlamaIndex, scored against the hand-written one in search.py.

Same database, same chunks, same embedding model, so the comparison is about the retrieval layer only:
- each chunk becomes a TextNode carrying its deal metadata and the vector embed.py already computed;
- the nodes live in LlamaIndex's PGVectorStore (table data_li_chunks) with its own full-text column;
- a vector retriever and a full-text retriever are fused with reciprocal rank fusion by
  QueryFusionRetriever, the LlamaIndex counterpart of the RRF query in search.search_text.

Build once after embed.py:  python llamaindex_search.py build
"""
import os
import re
import sys
from functools import lru_cache

from llama_index.core import VectorStoreIndex
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.llms import MockLLM
from llama_index.core.retrievers import QueryFusionRetriever
from llama_index.core.schema import TextNode
from llama_index.core.vector_stores import FilterOperator, MetadataFilter, MetadataFilters
from llama_index.core.vector_stores.types import VectorStoreQueryMode
from llama_index.vector_stores.postgres import PGVectorStore

from config import EMBED_DIMS, connect
from llm import embed

TABLE = "li_chunks"                     # PGVectorStore prefixes it: data_li_chunks


class LocalEmbedding(BaseEmbedding):
    """Adapts llm.embed (local bge-small) to LlamaIndex, so both paths use identical vectors."""

    def _get_query_embedding(self, query: str) -> list[float]:
        return list(embed([query], query=True)[0])

    def _get_text_embedding(self, text: str) -> list[float]:
        return list(embed([text])[0])

    def _get_text_embeddings(self, texts: list[str]) -> list[list[float]]:
        return [list(v) for v in embed(texts)]

    async def _aget_query_embedding(self, query: str) -> list[float]:
        return self._get_query_embedding(query)


def _urls(role: str) -> tuple[str, str]:
    """psycopg2-style DATABASE_URL -> SQLAlchemy sync and async URLs (unix-socket host kept as a query arg)."""
    url = os.environ["DATABASE_URL_WRITER" if role == "writer" else "DATABASE_URL_READER"]
    rest = url.split("://", 1)[1]
    return f"postgresql+psycopg2://{rest}", f"postgresql+asyncpg://{rest}"


def _store(role: str) -> PGVectorStore:
    sync_url, async_url = _urls(role)
    return PGVectorStore(connection_string=sync_url, async_connection_string=async_url, table_name=TABLE,
                         embed_dim=EMBED_DIMS, hybrid_search=True, text_search_config="english",
                         perform_setup=(role == "writer"),          # the reader can't create tables
                         hnsw_kwargs={"hnsw_m": 16, "hnsw_ef_construction": 64, "hnsw_ef_search": 100, "hnsw_dist_method": "vector_cosine_ops"})


def build() -> int:
    """Copy every chunk into the LlamaIndex store as a node, reusing its stored embedding."""
    conn = connect("writer")
    with conn, conn.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS data_{TABLE}")           # rebuilds are full and idempotent
        cur.execute("""SELECT c.id, c.sow_id, c.page_no, c.clause_type, c.context, c.text, c.embedding,
                              s.filename, s.client_alias, s.sector, array_to_string(s.products, ', ')
                       FROM chunk c JOIN sow s ON s.id = c.sow_id WHERE c.embedding IS NOT NULL ORDER BY c.id""")
        rows = cur.fetchall()
    nodes = [TextNode(id_=f"chunk-{cid}", text=f"{context}\n{text}" if context else text, embedding=[float(x) for x in vec.to_list()],
                      metadata={"chunk_id": cid, "sow_id": sow_id, "page_no": page_no, "clause_type": ct or "",
                                "filename": fn, "client_alias": alias or "", "sector": sector or "",
                                "products": products or ""},
                      excluded_embed_metadata_keys=["chunk_id", "sow_id", "page_no", "filename"],
                      excluded_llm_metadata_keys=["chunk_id", "sow_id"])
             for cid, sow_id, page_no, ct, context, text, vec, fn, alias, sector, products in rows]
    _store("writer").add(nodes)
    return len(nodes)


@lru_cache(maxsize=1)
def _index() -> VectorStoreIndex:
    return VectorStoreIndex.from_vector_store(_store("reader"), embed_model=LocalEmbedding())


def search_text(query: str, k: int = 8, clause_type: str | None = None, sow_id: int | None = None) -> list[dict]:
    """Same contract as search.search_text, answered by LlamaIndex retrievers fused with RRF."""
    filters = []
    if clause_type:
        filters.append(MetadataFilter(key="clause_type", value=clause_type))
    if sow_id:
        filters.append(MetadataFilter(key="sow_id", value=sow_id))
    named = sorted(set(re.findall(r"\bClient [A-Z]{1,2}\b", query)))
    if named and not sow_id:                              # a question naming a client is about that client
        filters.append(MetadataFilter(key="client_alias", value=named, operator=FilterOperator.IN))
    mf = MetadataFilters(filters=filters) if filters else None
    idx = _index()
    vector = idx.as_retriever(similarity_top_k=50, filters=mf)
    keyword = idx.as_retriever(vector_store_query_mode=VectorStoreQueryMode.TEXT_SEARCH,
                               similarity_top_k=50, filters=mf)
    fused = QueryFusionRetriever([vector, keyword], mode="reciprocal_rerank", similarity_top_k=k,
                                 num_queries=1, use_async=False,     # one query: fusion only, no LLM rewrites,
                                 llm=MockLLM())                      # so no model is ever called here
    hits = fused.retrieve(query)
    if named and not hits:                                # an alias that matches nothing shouldn't blank the answer
        return search_text(re.sub(r"\bClient [A-Z]{1,2}\b", "", query), k, clause_type, sow_id)
    return [{"filename": h.node.metadata["filename"], "client_alias": h.node.metadata["client_alias"],
             "page_no": h.node.metadata["page_no"], "clause_type": h.node.metadata["clause_type"] or None,
             "text": h.node.get_content().split("\n", 1)[-1], "score": round(h.score or 0, 4),
             "retriever": "llamaindex"} for h in hits]


if __name__ == "__main__":
    if sys.argv[1:] == ["build"]:
        print(f"LlamaIndex: indexed {build()} nodes")
    else:
        for h in search_text(" ".join(sys.argv[1:])):
            print(f"{h['filename']} p{h['page_no']} {h['score']}: {h['text'][:100]}")
