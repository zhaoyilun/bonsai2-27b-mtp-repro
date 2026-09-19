#!/usr/bin/env python3
"""A/B 测 MTP 接受率与速度：同一 prompt 集、temp0/topk1/seed7，读 timings 的 draft_n/draft_n_accepted。"""
import json, sys, time, urllib.request

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
TAG  = sys.argv[2] if len(sys.argv) > 2 else "run"
NP   = int(sys.argv[3]) if len(sys.argv) > 3 else 96
URL  = f"http://127.0.0.1:{PORT}/completion"
H    = {"Content-Type": "application/json",
        "Authorization": "Bearer sk-lan-97f1c41bb1642ab23f810c65"}

PROMPTS = {
  "V(reasoning)": ("Quantum computing exploits superposition and entanglement to perform "
                   "computations that are intractable for classical machines. The principal "
                   "obstacle in practice is decoherence, which"),
  "P(repetitive)": "The capital of France is",
  "C(code)": ("def merge_intervals(intervals):\n    \"\"\"Merge overlapping intervals.\"\"\"\n"
              "    if not intervals:\n        return []\n    intervals = sorted(intervals)\n    merged = [intervals[0]]\n    for start, end in intervals[1:]:\n"),
}

def run(name, prompt):
    body = json.dumps({"prompt": prompt, "n_predict": NP, "temperature": 0.0,
                       "top_k": 1, "seed": 7, "cache_prompt": False}).encode()
    t0 = time.time()
    try:
        r = json.load(urllib.request.urlopen(
            urllib.request.Request(URL, data=body, headers=H), timeout=1800))
    except Exception as e:
        print(f"  {name:14} 请求失败: {e}"); return None
    wall = time.time() - t0
    t = r.get("timings", {})
    dn, da = t.get("draft_n"), t.get("draft_n_accepted")
    acc = (da / dn) if (dn and da is not None) else None
    print(f"  {name:14} gen {t.get('predicted_per_second',0):6.1f} t/s | {t.get('predicted_n'):4} tok | "
          f"wall {wall:5.1f}s | draft {dn if dn is not None else '-'}"
          f"{f'/{da}' if da is not None else ''}"
          f"{f' = {acc*100:.1f}%' if acc is not None else ''}")
    return {"name": name, "tps": t.get("predicted_per_second"), "n": t.get("predicted_n"),
            "wall": wall, "draft_n": dn, "draft_accepted": da, "acc": acc,
            "prompt_ms": t.get("prompt_ms"), "timings": t}

print(f"[{TAG}] n_predict={NP}")
res = [x for x in (run(k, v) for k, v in PROMPTS.items()) if x]
json.dump({"tag": TAG, "results": res}, open(f"/home/zyl/bonsai2/mtp_{TAG}.json", "w"), indent=1)
if res:
    tot_n = sum(r["n"] for r in res); tot_w = sum(r["wall"] for r in res)
    dn = sum(r["draft_n"] or 0 for r in res); da = sum(r["draft_accepted"] or 0 for r in res)
    print(f"  合计: {tot_n} tok / {tot_w:.1f}s = {tot_n/tot_w:.1f} t/s | "
          f"draft {dn}→{da}" + (f" ({da/dn*100:.1f}%)" if dn else ""))
