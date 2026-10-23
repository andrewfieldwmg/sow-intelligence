"""Shared settings and database connections."""
import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from pgvector.psycopg2 import register_vector

load_dotenv()

SOW_PATH = Path(os.getenv("SOW_DOCUMENTS_PATH", "./sanitised_sows"))
ALIAS_MAP_PATH = Path(os.getenv("ALIAS_MAP_PATH", "./private/alias_map.csv"))
REGISTER_PATH = Path(os.getenv("REGISTER_PATH", "./register.csv"))
EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")   # local; OpenAI build: text-embedding-3-small
EMBED_DIMS = int(os.getenv("EMBED_DIMS", "384"))                    # must match vector(N) in schema.sql
EXTRACT_MODEL = os.getenv("EXTRACT_MODEL", "claude-haiku-5-5")
CHAT_MODEL = os.getenv("CHAT_MODEL", "claude-opus-5-5")
CHUNK_TOKENS = int(os.getenv("CHUNK_TOKENS", "400"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "60"))

SECTIONS = ["scope", "deliverable", "assumption", "out_of_scope", "staffing",
            "governance", "acceptance", "change_control", "payment"]
CLAUSE_TYPES = ["termination", "payment", "liability", "ip", "sla",
                "data_protection", "audit", "change_control"]


def connect(role: str = "writer"):
    """Writer for the build scripts; reader (SELECT only) for the server and CLI."""
    key = "DATABASE_URL_WRITER" if role == "writer" else "DATABASE_URL_READER"
    conn = psycopg2.connect(os.environ[key])
    register_vector(conn)
    return conn
