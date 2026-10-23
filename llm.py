"""The only module that talks to a model provider. Swap this file to change provider.

v2 live build: Claude for extraction, drafting and Q&A; embeddings run locally (fastembed,
bge-small, 384 dimensions), so contract text goes to one provider only.
llm_openai.py is the original OpenAI version with the same interface.
"""
import json

import anthropic

from config import CHAT_MODEL, EMBED_MODEL, EXTRACT_MODEL

_client = None
_embedder = None
# Policy declines on the main model are re-run server-side on a suitable fallback model.
FALLBACK = {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}


class ModelRefusal(Exception):
    pass


def client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(max_retries=5)   # SDK retries 429s, 5xx and connection errors
    return _client


def _text(resp) -> str:
    if resp.stop_reason == "refusal":
        raise ModelRefusal(str(resp.stop_details))
    return "".join(b.text for b in resp.content if b.type == "text")


def embed(texts: list[str], query: bool = False) -> list[list[float]]:
    global _embedder
    if _embedder is None:
        from fastembed import TextEmbedding
        _embedder = TextEmbedding(EMBED_MODEL)
    vecs = _embedder.query_embed(texts) if query else _embedder.embed(texts)
    return [v.tolist() for v in vecs]


def extract_json(system: str, user: str, schema: dict, name: str, model: str | None = None) -> dict:
    resp = client().messages.create(
        model=model or EXTRACT_MODEL, max_tokens=16000, system=system,
        messages=[{"role": "user", "content": user}],
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": schema}},
    )
    return json.loads(_text(resp))


def complete(system: str, user: str) -> str:
    resp = client().beta.messages.create(
        model=CHAT_MODEL, max_tokens=16000, system=system,
        messages=[{"role": "user", "content": user}],
        output_config={"effort": "medium"}, **FALLBACK,
    )
    return _text(resp)


def tool_loop(system: str, question: str, tools: list[dict], funcs: dict, max_steps: int = 4) -> str:
    """tools: [{"name", "description", "parameters"}] in a provider-neutral shape."""
    defs = [{"name": t["name"], "description": t["description"], "input_schema": t["parameters"]}
            for t in tools]
    messages = [{"role": "user", "content": question}]
    for _ in range(max_steps):
        resp = client().beta.messages.create(
            model=CHAT_MODEL, max_tokens=16000, system=system, tools=defs,
            messages=messages, output_config={"effort": "medium"}, **FALLBACK)
        if resp.stop_reason == "refusal":
            raise ModelRefusal(str(resp.stop_details))
        if resp.stop_reason != "tool_use":
            return _text(resp)
        messages.append({"role": "assistant", "content": resp.content})
        results = []
        for block in resp.content:
            if block.type != "tool_use":
                continue
            try:
                out, err = funcs[block.name](**block.input), False
            except Exception as e:                       # bad arguments go back to the model
                out, err = {"error": str(e)}, True
            results.append({"type": "tool_result", "tool_use_id": block.id, "is_error": err,
                            "content": json.dumps(out, default=str)[:20000]})
        messages.append({"role": "user", "content": results})   # all results in one message
    return "Stopped after the step limit without a final answer."
