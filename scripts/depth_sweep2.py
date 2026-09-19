#!/usr/bin/env python3
"""长上下文扫描 v3：走 chat 路径（与 agent 用法一致），逐深度测 prefill/decode/接受率。"""
import json, sys, time, urllib.request
TAG = sys.argv[1]; NP = int(sys.argv[2]) if len(sys.argv) > 2 else 256
URL = "http://127.0.0.1:8080/v1/chat/completions"
H = {"Content-Type": "application/json", "Authorization": "Bearer sk-lan-CHANGE-ME"}
TEXT = open("/mnt/e/AI/ternary-expand/tmp-models/longtext.txt", encoding="utf-8").read()
Q = "\n\nQuestion: in one sentence, what is the single most important idea in the text above?"
POINTS = [("~0.2k", 800), ("~8k", 33000), ("~32k", 132000), ("~64k", 265000), ("~128k", 530000), ("~192k", 795000)]

print(f"[{TAG}] max_tokens={NP}", flush=True)
res = []
for label, chars in POINTS:
    body = json.dumps({"model": "bonsai-27b", "messages": [{"role": "user", "content": TEXT[:chars] + Q}],
                       "max_tokens": NP, "temperature": 0.0}).encode()
    t0 = time.time()
    try:
        r = json.load(urllib.request.urlopen(urllib.request.Request(URL, data=body, headers=H), timeout=3600))
    except Exception as e:
        print(f"  {label:6} 失败: {type(e).__name__} {str(e)[:60]}", flush=True); continue
    t = r.get("timings", {}); wall = time.time() - t0
    dn, da = t.get("draft_n") or 0, t.get("draft_n_accepted") or 0
    acc = (da / dn * 100) if dn else None
    print(f"  {label:6} prompt {t.get('prompt_n'):>7} tok | prefill {t.get('prompt_per_second',0):7.1f} t/s "
          f"({t.get('prompt_ms',0)/1000:6.1f}s) | decode {t.get('predicted_per_second',0):5.1f} t/s "
          f"| gen {t.get('predicted_n')}" + (f" | acc {acc:5.1f}%" if acc is not None else " | no draft")
          + f" | wall {wall:6.1f}s", flush=True)
    res.append({"label": label, "prompt_n": t.get("prompt_n"), "prefill_tps": t.get("prompt_per_second"),
                "prefill_s": t.get("prompt_ms", 0)/1000, "decode_tps": t.get("predicted_per_second"),
                "gen": t.get("predicted_n"), "draft_n": dn, "draft_acc": da, "acc": acc, "wall": wall})
json.dump({"tag": TAG, "results": res}, open(f"/home/zyl/bonsai2/depth2_{TAG}.json", "w"), indent=1)
print(f"[{TAG}] 完成 {len(res)}/{len(POINTS)}", flush=True)
