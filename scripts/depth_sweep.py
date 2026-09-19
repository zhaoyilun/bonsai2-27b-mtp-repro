#!/usr/bin/env python3
"""长上下文深度扫描 v2：纯自然续写，结尾触发 EOS 时按偏移重试，直到真的生成。"""
import json, sys, time, urllib.request

TAG = sys.argv[1]; NP = int(sys.argv[2]) if len(sys.argv) > 2 else 64
URL = "http://127.0.0.1:8080/completion"
H = {"Content-Type": "application/json", "Authorization": "Bearer sk-lan-CHANGE-ME"}
TEXT = open("/mnt/e/AI/ternary-expand/tmp-models/longtext.txt", encoding="utf-8").read()
POINTS = [("0.2k", 800), ("8k", 32000), ("32k", 128000), ("64k", 256000), ("128k", 512000), ("192k", 780000)]

def once(prompt):
    b = json.dumps({"prompt": prompt, "n_predict": NP, "temperature": 0.0, "top_k": 1,
                    "seed": 7, "cache_prompt": False}).encode()
    t0 = time.time()
    r = json.load(urllib.request.urlopen(urllib.request.Request(URL, data=b, headers=H), timeout=3600))
    return r, time.time() - t0

def run(label, chars):
    for shift in (0, 1500, 3000, 4500, 6000):
        lo = 200000 + shift if chars == 800 else shift   # 短点用别处文本
        prompt = TEXT[lo:lo + chars]
        if not prompt: continue
        try:
            r, wall = once(prompt)
        except Exception as e:
            print(f"  {label:6} 请求失败: {str(e)[:60]}"); return None
        t = r.get("timings", {})
        if (r.get("tokens_predicted") or 0) > 8:
            dn, da = t.get("draft_n") or 0, t.get("draft_n_accepted") or 0
            acc = (da / dn * 100) if dn else None
            print(f"  {label:6} prompt {t.get('prompt_n'):>7} tok | prefill {t.get('prompt_per_second',0):7.1f} t/s "
                  f"({t.get('prompt_ms',0)/1000:6.1f}s) | decode {t.get('predicted_per_second',0):5.1f} t/s"
                  + (f" | acc {acc:5.1f}%" if acc is not None else " | no draft")
                  + f" | gen {r.get('tokens_predicted')} tok | wall {wall:6.1f}s | shift {shift}")
            return {"label": label, "prompt_n": t.get("prompt_n"), "prefill_tps": t.get("prompt_per_second"),
                    "prefill_s": t.get("prompt_ms", 0)/1000, "decode_tps": t.get("predicted_per_second"),
                    "gen": r.get("tokens_predicted"), "draft_n": dn, "draft_acc": da, "acc": acc,
                    "wall": wall, "shift": shift}
    print(f"  {label:6} 5 个偏移都触发 EOS"); return None

print(f"[{TAG}] n_predict={NP}")
res = [x for x in (run(l, c) for l, c in POINTS) if x]
json.dump({"tag": TAG, "results": res}, open(f"/home/zyl/bonsai2/depth_{TAG}.json", "w"), indent=1)
print(f"[{TAG}] 完成 {len(res)}/{len(POINTS)}")
