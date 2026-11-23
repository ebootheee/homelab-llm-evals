"""Quick decode/prefill speed check against llama-server endpoints (reads the server's timings)."""
import json, os, sys, urllib.request

PROMPT = ("Write a 300-word technical overview of Mixture-of-Experts routing, "
          "covering top-k gating, load balancing loss, and expert parallelism.")

TARGETS = [
    ("qwen-gpu1", "qwen3.8-27b-abliterated-gpu1",
     os.environ.get("ROUTER_URL", "http://127.0.0.1:8080/v1/chat/completions"), True),
    ("inkling-mini", "inkling-2-mini",
     "http://127.0.0.1:5811/v1/chat/completions", False),
]

for name, model, url, auth in TARGETS:
    body = {"model": model,
            "messages": [{"role": "user", "content": PROMPT}],
            "max_tokens": 2500, "temperature": 0.6,
            "chat_template_kwargs": {"enable_thinking": False}}
    headers = {"Content-Type": "application/json"}
    if auth:
        headers["Authorization"] = "Bearer " + os.environ.get("HUB_INFERENCE_KEY", "")
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers)
    d = json.load(urllib.request.urlopen(req, timeout=300))
    m = d["choices"][0]["message"]
    t = d.get("timings", {})
    print(f"{name}: finish={d['choices'][0]['finish_reason']} "
          f"content={len(m.get('content') or '')}ch "
          f"reasoning={len(m.get('reasoning_content') or '')}ch")
    print(f"  prompt_t/s={t.get('prompt_per_second')} "
          f"gen_t/s={t.get('predicted_per_second')} n={t.get('predicted_n')}")
