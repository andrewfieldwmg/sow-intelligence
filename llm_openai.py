"""The only module that talks to the model provider. Swap this file to change provider."""
import json
import time

from openai import OpenAI

from config import CHAT_MODEL, EMBED_MODEL, EXTRACT_MODEL

_client = None


def client():
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


def _retry(fn, attempts=5):
    for i in range(attempts):
        try:
            return fn()
        except Exception:                      # rate limits and transient errors
            if i == attempts - 1:
                raise
            time.sleep(2 ** i)


def embed(texts: list[str], query: bool = False) -> list[list[float]]:
    resp = _retry(lambda: client().embeddings.create(model=EMBED_MODEL, input=texts))
    return [d.embedding for d in resp.data]


def extract_json(system: str, user: str, schema: dict, name: str, model=None) -> dict:
    resp = _retry(lambda: client().chat.completions.create(
        model=EXTRACT_MODEL, temperature=0,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        response_format={"type": "json_schema",
                         "json_schema": {"name": name, "strict": True, "schema": schema}},
    ))
    return json.loads(resp.choices[0].message.content)


def complete(system: str, user: str) -> str:
    resp = _retry(lambda: client().chat.completions.create(
        model=CHAT_MODEL, temperature=0,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
    ))
    return resp.choices[0].message.content


def tool_loop(system: str, question: str, tools: list[dict], funcs: dict, max_steps: int = 4) -> str:
    defs = [{"type": "function", "function": t} for t in tools]
    messages = [{"role": "system", "content": system}, {"role": "user", "content": question}]
    for _ in range(max_steps):
        msg = _retry(lambda: client().chat.completions.create(
            model=CHAT_MODEL, temperature=0, messages=messages, tools=defs)).choices[0].message
        if not msg.tool_calls:
            return msg.content
        messages.append(msg)
        for call in msg.tool_calls:
            try:
                out = funcs[call.function.name](**json.loads(call.function.arguments))
            except Exception as e:
                out = {"error": str(e)}
            messages.append({"role": "tool", "tool_call_id": call.id,
                             "content": json.dumps(out, default=str)[:20000]})
    return "Stopped after the step limit without a final answer."
