# homelab-llm-evals

The eval harness, both suites and every transcript behind the post
*Five models, two eval suites, one homelab: picking my local daily driver*.

It answers one narrow question: which model should run my home agent, on my
hardware, for the jobs I actually give it. It is not a general leaderboard.

## Results

**Round 1: everyday agent jobs** (`evals.yaml`, 7 evals, /68)

| | Qwen 3.8 27B abl | Inkling 2 Mini | Ember (cloud) | DeepSeek V4.1 Flash abl | Inkling 2 Mini abl |
|---|---|---|---|---|---|
| Total | 58 | 60 | 63 | 62 | **65** |

**Round 2: home-network cyber suite** (`cyber-evals.yaml`, 6 cases, /72)

| | Qwen 3.8 27B abl | Inkling 2 Mini | Ember (cloud) | DeepSeek V4.1 Flash abl | Inkling 2 Mini abl |
|---|---|---|---|---|---|
| Total | 48 | 55 | **66** | 57 | 56 |

Per-eval tables: [`results/summary-5way.md`](results/summary-5way.md) and
[`results/summary-cyber-evals.md`](results/summary-cyber-evals.md).

## What's here

| Path | What |
|---|---|
| `run_evals.py` | The harness. Sends each prompt to every contestant, then has a judge model score each rubric line 0–2. Results are cached per eval and model. |
| `evals.yaml` | Round 1: five agentic tasks (coding delegation, CVE triage, email + calendar, travel concierge, doc → action items) plus two Hugging Face hard sets. |
| `cyber-evals.yaml` | Round 2: six cases replayed from real incidents on my home network, each with six checkable rubric lines. |
| `build_hf_evals.py`, `hf_hard_evals.json` | Builds the two hard sets (MMLU-Pro physics/chemistry, IFEval) from the Hugging Face datasets-server API. |
| `bench_tps.py` | Quick decode/prefill speed check. |
| `results/` | Every model's answer (`<eval>.<model>.md`) and the judge's per-line scores and reasoning (`.scores.json`). |
| `results/cyber-uncapped-inkling/` | The first cyber run of both Inklings without a thinking cap, kept as the example of a model spending its whole budget thinking. |
| `serving/` | The llama.cpp flags each local model ran with. |

## Running it

```bash
pip install -r requirements.txt
export ROUTER_URL=http://127.0.0.1:8080/v1/chat/completions   # serves qwen + the judge
export INKLING_URL=... INKLING_ABL_URL=... DEEPSEEK_URL=...    # one llama-server each
export OPENROUTER_API_KEY=...                                  # optional; ember is skipped without it
python3 run_evals.py --models qwen,inkling,inkling_abl,deepseek,ember
python3 run_evals.py --evals cyber-evals.yaml --models qwen,inkling
```

Any OpenAI-compatible endpoint works. Each contestant's URL and model name can be
overridden with `<NAME>_URL` / `<NAME>_MODEL`; see the docstring in `run_evals.py`.
Cached answers in `results/` are reused unless you pass `--force`.

The judge is `gemma-4-12b`. It is a reasoning model, so it gets 2048 output tokens;
at 512 it silently failed long rubric lines.

## Anonymization

The cyber cases and some round-1 prompts came from my real network and life. Before
publishing, every hostname, IP, VLAN ID, SSID, tailnet address, person and company
name was replaced with a consistent fictional one, in the prompts **and** in the
model answers and judge notes, so the transcripts still match the questions. The
4via6 address in the tailnet case was re-derived so it still encodes the (new) IPv4
address.

The models were scored on the original wording. The substitutions are one-for-one
and do not change any fact the rubrics check, but these exact files were not re-run.

## Caveats

- One sample per eval per model.
- A 12B judge. Read the transcripts before trusting a close score; the firewall
  case looked like a judge bug until I read the answers.
- I wrote the rubrics, about my own network. Five of the seven round-1 evals sit
  near the ceiling, so 1–2 point gaps there are noise.
- The Hugging Face hard sets are tiny samples. MMLU-Pro (MIT) and IFEval
  (Apache-2.0) belong to their authors.

## License

MIT for the code and eval files. Model outputs in `results/` are provided as-is for
reference.
