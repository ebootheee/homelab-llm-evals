# How each model was served

Hardware: 2x RTX 5090 (32 GB each), 121 GB RAM, llama.cpp `llama-server`.
Every local model ran on one GPU at a time. The flags below are the ones from the
round-2 (cyber) run scripts.

## Qwen 3.8 27B abliterated (IQ4_XS, MTP draft head)

```bash
llama-server -m Huihui-Qwen3.8-27B-abliterated-UD-IQ4_XS.gguf \
  --jinja -ngl 999 --parallel 1 --flash-attn on \
  --cache-type-k q8_0 --cache-type-v q8_0 \
  --temp 0.6 --repeat-penalty 1.05 --repeat-last-n 64 \
  --spec-type draft-mtp --spec-draft-n-max 2 \
  --spec-draft-type-k q8_0 --spec-draft-type-v q8_0 \
  -c 131072
```

The harness sends `chat_template_kwargs: {enable_thinking: false}` to Qwen.

## Inkling 2 Mini, stock (Q4_K_M) and abliterated (AD-Q4_K)

```bash
llama-server -m <inkling gguf> \
  --jinja -ngl 999 --parallel 1 --flash-attn on \
  --cache-type-k q8_0 --cache-type-v q8_0 \
  --temp 0.6 --repeat-penalty 1.05 --repeat-last-n 64 -c 65536 \
  --reasoning-budget 8000 \
  --reasoning-budget-message "Thinking budget reached. Now write the final answer."
```

Without `--reasoning-budget`, both Inklings spent their whole 16k output budget
thinking on two cyber cases and the judge ended up scoring raw reasoning (see
`results/cyber-uncapped-inkling/`). Inkling ignores `enable_thinking: false`.

Context note: Inkling repeats a block of layers three times, so its KV cache is much
larger than the layer count suggests. 131k context needs about 31 GB with q8_0 KV;
98k needs about 27 GB.

## DeepSeek V4.1 Flash abliterated (Mix-128G GGUF, ~225 GB)

The model is bigger than system RAM. llama.cpp memory-maps the file, so with
`--n-cpu-moe` the expert weights stay file-backed pages the kernel can drop and
re-read from NVMe. Attention and shared layers sit on one GPU.

```bash
llama-server -m DeepSeek-V4.1-Flash-1017-abliterated-Mix-128G.gguf \
  --jinja -ngl 999 --n-cpu-moe 35 -c 32768 --parallel 1 --flash-attn on \
  -t 16 --no-warmup -ub 2048 \
  --reasoning-budget 8000 \
  --reasoning-budget-message "Thinking budget reached. Now write the final answer."
```

Run it in a memory-capped unit (for example `systemd-run --user -p MemoryMax=90G
-p MemorySwapMax=0 ...`) so page cache pressure can't take the desktop down.
Decode was about 20 tok/s; prompt processing only 22–35 tok/s on a PCIe Gen4 x4 slot.

## Muse Ember (cloud)

Via OpenRouter, with `reasoning: {max_tokens: 4000}`.
