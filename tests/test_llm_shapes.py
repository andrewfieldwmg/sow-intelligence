"""Checks llm.py builds valid SDK requests and parses responses, using a mocked HTTP transport."""
import json
import sys
from pathlib import Path

import anthropic
import httpx2 as httpx

sys.path.insert(0, str(Path(__file__).parent.parent))
import llm                                                      # the real Claude module
from extract import META_SCHEMA

seen = []


def handler(request: httpx.Request):
    body = json.loads(request.content)
    seen.append((dict(request.headers), body))
    if body.get("tools") and not any(m["role"] == "user" and isinstance(m["content"], list) for m in body["messages"]):
        content, stop = [{"type": "tool_use", "id": "tu_1", "name": "clause_coverage", "input": {"clause_type": "liability"}}], "tool_use"
    elif "output_config" in body and "format" in body["output_config"]:
        content, stop = [{"type": "text", "text": json.dumps({k: None for k in META_SCHEMA["properties"]} | {"products": []})}], "end_turn"
    else:
        content, stop = [{"type": "text", "text": "Answer (a.docx, page 1)"}], "end_turn"
    return httpx.Response(200, json={"id": "msg_1", "type": "message", "role": "assistant", "model": body["model"],
                                     "content": content, "stop_reason": stop, "stop_sequence": None,
                                     "usage": {"input_tokens": 1, "output_tokens": 1}})


llm._client = anthropic.Anthropic(api_key="test", http_client=httpx.Client(transport=httpx.MockTransport(handler)))
print(llm.extract_json("sys", "text", META_SCHEMA, "sow_metadata"))
print(llm.complete("sys", "hi"))
print(llm.tool_loop("sys", "which SOWs lack liability caps?",
                    [{"name": "clause_coverage", "description": "d", "parameters": {"type": "object", "properties": {"clause_type": {"type": "string"}}, "required": ["clause_type"]}}],
                    {"clause_coverage": lambda clause_type: [{"filename": "a.docx"}]}))
for h, b in seen:
    print(b["model"], h.get("anthropic-beta"), "fallbacks=" + str(b.get("fallbacks")), "output_config=" + json.dumps(b.get("output_config"))[:80],
          "temperature" in b)
print("SHAPES OK")
