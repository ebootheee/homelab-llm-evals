# Eval summary: QWEN vs INKLING vs EMBER vs DEEPSEEK vs INKLING_ABL

- Generated: 2026-11-22 14:44:14
- **qwen**: `qwen3.8-27b-abliterated-gpu1` @ http://100.101.1.10:8080/v1/chat/completions
- **inkling**: `inkling-2-mini` @ http://127.0.0.1:5810/v1/chat/completions
- **ember**: `meta/muse-ember` @ https://openrouter.ai/api/v1/chat/completions
- **deepseek**: `deepseek-v4.1-flash-abliterated` @ http://127.0.0.1:5830/v1/chat/completions
- **inkling_abl**: `inkling-2-mini-abliterated` @ http://127.0.0.1:5812/v1/chat/completions
- Judge: `gemma-4-12b` (0-2 per criterion)

| Eval | qwen | inkling | ember | deepseek | inkling_abl | Winner |
|---|---|---|---|---|---|---|
| hermes-coding-delegation | 11/12 | 12/12 | 12/12 | 12/12 | 12/12 | tie (inkling, ember, deepseek, inkling_abl) |
| homelab-cve-triage | 10/12 | 12/12 | 12/12 | 12/12 | 12/12 | tie (inkling, ember, deepseek, inkling_abl) |
| email-calendar-synthesis | 11/12 | 11/12 | 11/12 | 12/12 | 12/12 | tie (deepseek, inkling_abl) |
| travel-concierge-sydney | 11/12 | 10/12 | 11/12 | 12/12 | 12/12 | tie (deepseek, inkling_abl) |
| doc-to-action-items | 10/12 | 10/12 | 11/12 | 11/12 | 12/12 | inkling_abl |
| hard-reasoning-gpqa | 3/4 | 3/4 | 4/4 | 1/4 | 3/4 | ember |
| instruction-following-ifeval | 2/4 | 2/4 | 2/4 | 2/4 | 2/4 | tie (qwen, inkling, ember, deepseek, inkling_abl) |
| **TOTAL** | **58/68** | **60/68** | **63/68** | **62/68** | **65/68** | **inkling_abl** |

Wins: qwen 0, inkling 0, ember 1, deepseek 0, inkling_abl 1, tie 5

⚠ = model or judge error; see the matching .scores.json.
