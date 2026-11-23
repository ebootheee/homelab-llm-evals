# Eval summary: QWEN vs INKLING vs EMBER vs DEEPSEEK vs INKLING_ABL

- Generated: 2026-11-22 19:24:55
- **qwen**: `qwen3.8-27b-abliterated-gpu1` @ http://100.101.1.10:8080/v1/chat/completions
- **inkling**: `inkling-2-mini` @ http://127.0.0.1:5810/v1/chat/completions
- **ember**: `meta/muse-ember` @ https://openrouter.ai/api/v1/chat/completions
- **deepseek**: `deepseek-v4.1-flash-abliterated` @ http://127.0.0.1:5830/v1/chat/completions
- **inkling_abl**: `inkling-2-mini-abliterated` @ http://127.0.0.1:5812/v1/chat/completions
- Judge: `gemma-4-12b` (0-2 per criterion)

| Eval | qwen | inkling | ember | deepseek | inkling_abl | Winner |
|---|---|---|---|---|---|---|
| cyber-exposure-map | 10/12 | 11/12 | 12/12 | 12/12 | 10/12 | tie (ember, deepseek) |
| cyber-firewall-isolation | 5/12 | 6/12 | 9/12 | 5/12 | 7/12 | ember |
| cyber-vlan-incident | 7/12 | 6/12 | 11/12 | 7/12 | 6/12 | ember |
| cyber-tailnet-policy | 7/12 | 10/12 | 11/12 | 11/12 | 10/12 | tie (ember, deepseek) |
| cyber-advisory-triage | 11/12 | 12/12 | 12/12 | 12/12 | 12/12 | tie (inkling, ember, deepseek, inkling_abl) |
| cyber-scope-restraint | 8/12 | 10/12 | 11/12 | 10/12 | 11/12 | tie (ember, inkling_abl) |
| **TOTAL** | **48/72** | **55/72** | **66/72** | **57/72** | **56/72** | **ember** |

Wins: qwen 0, inkling 0, ember 2, deepseek 0, inkling_abl 0, tie 4

⚠ = model or judge error; see the matching .scores.json.
