#!/usr/bin/env python3
"""Run an eval suite against several OpenAI-compatible endpoints and judge with an LLM.

Usage: python3 run_evals.py [--evals cyber-evals.yaml] [--force] [--only EVAL_ID ...]
                            [--models qwen,inkling,inkling_abl,deepseek,ember]
       Cached results in results/ are reused unless --force. ember is skipped if
       OPENROUTER_API_KEY is unset.
Env:  ROUTER_URL (default http://127.0.0.1:8080/v1/chat/completions; serves qwen + judge),
      HUB_INFERENCE_KEY (optional bearer for the router),
      <NAME>_URL / <NAME>_MODEL per contestant (QWEN, INKLING, INKLING_ABL, DEEPSEEK, EMBER),
      INKLING_KEY, JUDGE_URL, OPENROUTER_API_KEY, DEEPSEEK_TIMEOUT.
See serving/README.md for the llama.cpp flags each model ran with.
"""
import argparse, json, os, re, sys, time, urllib.error, urllib.request
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
SUMMARY = RESULTS / "summary.md"



ROUTER_URL = os.environ.get("ROUTER_URL", "http://127.0.0.1:8080/v1/chat/completions")
HUB_KEY = os.environ.get("HUB_INFERENCE_KEY", "")

MODELS = {
    "qwen": {
        "url": os.environ.get("QWEN_URL", ROUTER_URL),
        "model": os.environ.get("QWEN_MODEL", "qwen3.8-27b-abliterated-gpu1"),
        "key": HUB_KEY,
        # Reasoning model: without this, llama-server spends the whole budget on
        # reasoning_content and returns empty content (finish_reason=length).
        "extra_body": {"chat_template_kwargs": {"enable_thinking": False}},
    },
    "inkling": {
        "url": os.environ.get("INKLING_URL", "http://127.0.0.1:5810/v1/chat/completions"),
        "model": os.environ.get("INKLING_MODEL", "inkling-2-mini"),
        "key": os.environ.get("INKLING_KEY", ""),
    },
    # Frontier cloud reasoning model via OpenRouter. Reasoning is capped: uncapped,
    # its thinking eats the whole budget (finish_reason=length, empty content).
    # extract_text still falls back to the `reasoning` field if content is empty.
    "ember": {
        "url": os.environ.get("EMBER_URL", "https://openrouter.ai/api/v1/chat/completions"),
        "model": os.environ.get("EMBER_MODEL", "meta/muse-ember"),
        "key": os.environ.get("OPENROUTER_API_KEY", ""),
        "extra_body": {"reasoning": {"max_tokens": 4000}},
    },
    # Abliterated Inkling 2 Mini (AtomicChat AD-Q4_K, refusal direction baked in).
    "inkling_abl": {
        "url": os.environ.get("INKLING_ABL_URL", "http://127.0.0.1:5812/v1/chat/completions"),
        "model": os.environ.get("INKLING_ABL_MODEL", "inkling-2-mini-abliterated"),
        "key": "",
    },
    # DeepSeek-V4.1-Flash-1017 abliterated (Mix-128G GGUF) on llama.cpp with
    # --n-cpu-moe: experts are mmap'd from host RAM / NVMe, so it is slow. Long timeout.
    "deepseek": {
        "url": os.environ.get("DEEPSEEK_URL", "http://127.0.0.1:5830/v1/chat/completions"),
        "model": os.environ.get("DEEPSEEK_MODEL", "deepseek-v4.1-flash-abliterated"),
        "key": "",
        "timeout": int(os.environ.get("DEEPSEEK_TIMEOUT", "5400")),
    },
}
# Contestants that cannot run without a key (skipped by default when it is missing).
REQUIRES_KEY = {"ember": "OPENROUTER_API_KEY"}
JUDGE = {"url": os.environ.get("JUDGE_URL", ROUTER_URL), "model": "gemma-4-12b", "key": HUB_KEY}

MAX_TOKENS, TEMPERATURE, TIMEOUT, RETRIES = 2048, 0.6, 300, 1
# Per-candidate budgets; judge keeps its own. inkling and ember leave thinking on
# and can burn ~8k tokens reasoning before answering, so they get more headroom.
CANDIDATE_MAX_TOKENS = {"qwen": 8192, "inkling": 16384, "ember": 12000,
                        "inkling_abl": 16384, "deepseek": 12000}
# gemma-4-12b is a reasoning model: a small budget is consumed entirely by
# reasoning_content (empty content, finish_reason=length). Long rubric criteria
# starve it at 512; leave room for reasoning plus the final digit.
JUDGE_MAX_TOKENS = 2048
ERROR_MARKER = "<!-- EVAL_ERROR -->"
THINK_RE = re.compile(r"<think>.*?</think>", re.S)
THINK_TAG_RE = re.compile(r"</?think>")


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def strip_think(text):
    """Drop complete <think>...</think> blocks, then any stray/unclosed think tags."""
    return THINK_TAG_RE.sub("", THINK_RE.sub("", text or "")).strip()


def extract_text(msg):
    """Reply text from a chat message: content first, any reasoning field as fallback.

    Reasoning fields: `reasoning_content` (llama-server) and `reasoning` (OpenRouter).
    Returns (text, source) where source is "content", the reasoning field name, or None.
    """
    content = msg.get("content") or ""
    if not isinstance(content, str):  # some APIs return a list of content parts
        content = "".join(p.get("text") or "" for p in content if isinstance(p, dict))
    text = strip_think(content)
    if text:
        return text, "content"
    # Fallback: reasoning text. Keep what is inside think blocks, just drop the tags.
    for field, raw in (("reasoning_content", msg.get("reasoning_content")),
                       ("reasoning", msg.get("reasoning")),
                       ("reasoning_content", content)):
        if not isinstance(raw, str):
            continue
        text = THINK_TAG_RE.sub("", raw).strip()
        if text:
            return text, field
    return "", None


def chat(endpoint, messages, max_tokens=MAX_TOKENS, temperature=TEMPERATURE):
    """POST a chat completion; retry once on any failure (incl. empty reply).

    Returns (text, meta). text is extracted via extract_text and never empty.
    """
    payload = {
        "model": endpoint["model"], "messages": messages,
        "max_tokens": max_tokens, "temperature": temperature,
    }
    payload.update(endpoint.get("extra_body") or {})
    body = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"}
    if endpoint["key"]:
        headers["Authorization"] = f"Bearer {endpoint['key']}"
    last_err = None
    for attempt in range(1 + RETRIES):
        t0 = time.time()
        try:
            req = urllib.request.Request(endpoint["url"], data=body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=endpoint.get("timeout", TIMEOUT)) as resp:
                data = json.loads(resp.read().decode())
            choice = data["choices"][0]
            msg = choice.get("message") or {}
            text, source = extract_text(msg)
            if not text:
                raise ValueError(f"empty reply (finish_reason={choice.get('finish_reason')})")
            meta = {
                "latency_s": round(time.time() - t0, 1),
                "finish_reason": choice.get("finish_reason"),
                "usage": data.get("usage"),
                "attempt": attempt + 1,
                "source": source,
            }
            if source != "content":
                meta["note"] = f"empty content; fell back to {source}"
            return text, meta
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:500]
            last_err = f"HTTP {e.code}: {detail}"
        except Exception as e:  # timeouts, connection errors, bad JSON
            last_err = f"{type(e).__name__}: {e}"
        log(f"    attempt {attempt + 1} failed: {last_err}")
        if attempt < RETRIES:
            time.sleep(3)
    raise RuntimeError(last_err)


def is_valid_response(text):
    """A cached .md is usable only if non-empty after think-stripping and not an error marker."""
    return bool(text) and ERROR_MARKER not in text and bool(strip_think(text))


def get_response(ev, name, force):
    path = RESULTS / f"{ev['id']}.{name}.md"
    if path.exists() and not force:
        text = path.read_text()
        if is_valid_response(text):
            log(f"  {name}: reusing {path.name}")
            return text, {"cached": True}
        log(f"  {name}: cached {path.name} is empty/errored; regenerating")
    log(f"  {name}: querying {MODELS[name]['model']} ...")
    try:
        content, meta = chat(MODELS[name], [{"role": "user", "content": ev["prompt"]}],
                             max_tokens=CANDIDATE_MAX_TOKENS[name])
        path.write_text(content)
        log(f"  {name}: {len(content)} chars from {meta['source']} in {meta['latency_s']}s "
            f"(finish={meta['finish_reason']}) -> {path.name}")
        return content, meta
    except RuntimeError as e:
        path.write_text(f"{ERROR_MARKER}\nERROR: {e}\n")
        log(f"  {name}: FAILED ({e})")
        return None, {"error": str(e)}


JUDGE_ONE_PROMPT = """You are an evaluation judge.

Criterion: {criterion}

Scoring: 0 = missing or wrong, 1 = partially met, 2 = fully met.
Judge only what RESPONSE actually says.

RESPONSE:
<<<
{response}
>>>

Reply with ONLY one character: 0, 1, or 2. No other text."""

SCORE_DIGIT_RE = re.compile(r"[0-2]")


def judge_one(criterion, response):
    """Score a single criterion. Returns (score or None, raw reply). Asks at most twice.

    chat() returns text via extract_text(): message content if non-empty after
    think-stripping, otherwise reasoning_content. The score is the FIRST 0-2
    digit found anywhere in that text.
    """
    prompt = JUDGE_ONE_PROMPT.format(criterion=criterion, response=response)
    raw = ""
    for _ in range(2):  # retry once on chat failure or no digit in reply
        try:
            raw, _meta = chat(JUDGE, [{"role": "user", "content": prompt}],
                              max_tokens=JUDGE_MAX_TOKENS, temperature=0.0)
        except RuntimeError as e:
            raw = f"ERROR: {e}"
            continue
        m = SCORE_DIGIT_RE.search(raw)
        if m:
            return int(m.group()), raw
    return None, raw


def judge(ev, name, response, force):
    path = RESULTS / f"{ev['id']}.{name}.scores.json"
    rubric = ev["rubric"]
    if path.exists() and not force:
        cached = json.loads(path.read_text())
        if not cached.get("error"):
            log(f"  judge {name}: reusing {path.name} (total {cached['total']})")
            return cached
    result = {"eval_id": ev["id"], "model": MODELS[name]["model"], "judge": JUDGE["model"],
              "max_total": 2 * len(rubric)}
    if response is None or not strip_think(response):
        result.update(error="no response to judge", total=0,
                      criteria=[{"criterion": c, "score": 0, "reason": "no response"} for c in rubric])
    else:
        body = strip_think(response)
        log(f"  judge {name}: scoring {len(rubric)} criteria with {JUDGE['model']} ...")
        criteria, failed = [], 0
        for i, c in enumerate(rubric, 1):
            score, raw = judge_one(c, body)
            if score is None:
                failed += 1
                log(f"  judge {name}: criterion {i} unscored (raw: {raw[:80]!r})")
                criteria.append({"criterion": c, "score": None, "reason": "unscored",
                                 "judge_raw": raw[:500]})
            else:
                criteria.append({"criterion": c, "score": score, "reason": ""})
        result["criteria"] = criteria
        result["total"] = sum(x["score"] for x in criteria if x["score"] is not None)
        if failed:
            result["error"] = f"judge failed on {failed}/{len(rubric)} criteria"
    path.write_text(json.dumps(result, indent=2))
    log(f"  judge {name}: total {result['total']}/{result['max_total']}"
        + (f" [ERROR: {result['error']}]" if result.get("error") else ""))
    return result


def pick_winner(totals):
    """Winner name from {name: total}; ties are reported as 'tie (a, b)'."""
    best = max(totals.values())
    top = [n for n, t in totals.items() if t == best]
    return top[0] if len(top) == 1 else f"tie ({', '.join(top)})"


def write_summary(rows, names):
    lines = [
        "# Eval summary: " + " vs ".join(n.upper() for n in names), "",
        f"- Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        *[f"- **{n}**: `{MODELS[n]['model']}` @ {MODELS[n]['url']}" for n in names],
        f"- Judge: `{JUDGE['model']}` (0-2 per criterion)", "",
        "| Eval | " + " | ".join(names) + " | Winner |",
        "|---|" + "---|" * len(names) + "---|",
    ]
    grand = {n: 0 for n in names}
    wins = {n: 0 for n in names + ["tie"]}
    grand_max = 0
    for ev_id, scores in rows:
        mx = next(iter(scores.values()))["max_total"]
        grand_max += mx
        cells = []
        for n in names:
            s = scores[n]
            grand[n] += s["total"]
            cells.append(f"{s['total']}/{mx}" + (" ⚠" if s.get("error") else ""))
        winner = pick_winner({n: scores[n]["total"] for n in names})
        wins["tie" if winner.startswith("tie") else winner] += 1
        lines.append(f"| {ev_id} | " + " | ".join(cells) + f" | {winner} |")
    overall = pick_winner(grand)
    lines.append("| **TOTAL** | " + " | ".join(f"**{grand[n]}/{grand_max}**" for n in names)
                 + f" | **{overall}** |")
    lines += ["", "Wins: " + ", ".join(f"{k} {v}" for k, v in wins.items()),
              "", "⚠ = model or judge error; see the matching .scores.json.", ""]
    SUMMARY.write_text("\n".join(lines))
    return overall, grand, grand_max


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--force", action="store_true", help="re-run models and judge")
    ap.add_argument("--only", nargs="*", help="eval ids to run")
    ap.add_argument("--evals", default="evals.yaml",
                    help="eval file (default evals.yaml); others write results/summary-<stem>.md")
    ap.add_argument("--models", default=None,
                    help=f"comma-separated contestants from {','.join(MODELS)} "
                         "(default: all; ember skipped if OPENROUTER_API_KEY is unset)")
    args = ap.parse_args()

    if args.models:
        names = [n.strip() for n in args.models.split(",") if n.strip()]
        unknown = [n for n in names if n not in MODELS]
        if unknown or not names:
            ap.error(f"--models: unknown {unknown}; choose from {','.join(MODELS)}")
        names = list(dict.fromkeys(names))  # dedupe, keep order
        missing = [n for n in names if n in REQUIRES_KEY and not MODELS[n]["key"]]
        if missing:
            ap.error(", ".join(f"{n} needs {REQUIRES_KEY[n]}" for n in missing))
    else:
        names = []
        for n in MODELS:
            if n in REQUIRES_KEY and not MODELS[n]["key"]:
                log(f"WARNING: {REQUIRES_KEY[n]} not set; skipping {n}")
            else:
                names.append(n)

    global SUMMARY
    evals_path = Path(args.evals) if Path(args.evals).is_absolute() else HERE / args.evals
    if evals_path.name != "evals.yaml":
        SUMMARY = RESULTS / f"summary-{evals_path.stem}.md"
    evals = yaml.safe_load(evals_path.read_text())["evals"]
    if args.only:
        evals = [e for e in evals if e["id"] in args.only]
    if not HUB_KEY:
        log("WARNING: HUB_INFERENCE_KEY not set; router calls will likely fail")
    RESULTS.mkdir(exist_ok=True)
    log(f"Running {len(evals)} evals x {len(names)} models ({', '.join(names)}); "
        f"results -> {RESULTS}")

    rows = []
    for i, ev in enumerate(evals, 1):
        log(f"[{i}/{len(evals)}] {ev['id']} ({len(ev['rubric'])} criteria)")
        scores = {}
        for name in names:
            response, meta = get_response(ev, name, args.force)
            # A freshly generated response always gets re-judged.
            scores[name] = judge(ev, name, response, args.force or not meta.get("cached"))
        rows.append((ev["id"], scores))

    if not rows:
        log("No evals matched; summary not written.")
        return 1
    overall, grand, grand_max = write_summary(rows, names)
    log("Done. " + ", ".join(f"{n} {grand[n]}/{grand_max}" for n in grand)
        + f" -> winner: {overall}. See {SUMMARY}")


if __name__ == "__main__":
    sys.exit(main())
