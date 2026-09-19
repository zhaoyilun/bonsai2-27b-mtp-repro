#!/usr/bin/env python3
"""长上下文扫描 v4：/tokenize 精确标定深度 + 每点前缓存打断，保证 prompt_n 就是真实深度。"""
import json, sys, time, urllib.request
TAG = sys.argv[1]; NP = int(sys.argv[2]) if len(sys.argv) > 2 else 256
BASE = "http://127.0.0.1:8080"
H = {"Content-Type": "application/json", "Authorization": "Bearer sk-lan-CHANGE-ME"}
TEXT = open("/mnt/e/AI/ternary-expand/tmp-models/longtext.txt", encoding="utf-8").read()
Q = "\n\nQuestion: in one sentence, what is the single most important idea in the text above?"
TARGETS = [8000, 32000, 64000, 128000, 192000]

def post(path, obj, timeout=3600):
    req = urllib.request.Request(BASE + path, data=json.dumps(obj).encode(), headers=H)
    return json.load(urllib.request.urlopen(req, timeout=timeout))

def tokens(s):
    return len(post("/tokenize", {"content": s}, 300).get("tokens", []))

def calibrate(target):
    """线性调整字符数，使 tokenize 结果贴近 target。"""
    chars = int(target * 4.0)
    for _ in range(5):
        n = tokens(TEXT[:chars] + Q)
        if abs(n - target) <= max(50, target * 0.02):
            return chars, n
        chars = max(1000, int(chars * target / max(1, n)))
    return chars, tokens(TEXT[:chars] + Q)

print(f"[{TAG}] max_tokens={NP} targets={TARGETS}", flush=True)
res = []
for target in TARGETS:
    chars, ntok = calibrate(target)
    post("/v1/chat/completions", {"model": "x", "messages": [{"role": "user", "content": "Reply with the single word: ok"}], "max_tokens": 8, "temperature": 0.0}, 600)  # 缓存打断
    body = {"model": "bonsai-27b", "messages": [{"role": "user", "content": TEXT[:chars] + Q}],
            "max_tokens": NP, "temperature": 0.0}
    t0 = time.time(); r = post("/v1/chat/completions", body); wall = time.time() - t0
    t = r.get("timings", {}); dn, da = t.get("draft_n") or 0, t.get("draft_n_accepted") or 0
    acc = (da / dn * 100) if dn else None
    print(f"  target {target:>7} | chars {chars:>8} | prompt {t.get('prompt_n'):>7} tok | "
          f"prefill {t.get('prompt_per_second',0):7.1f} t/s ({t.get('prompt_ms',0)/1000:6.1f}s) | "
          f"decode {t.get('predicted_per_second',0):5.1f} t/s | gen {t.get('predicted_n')}"
          + (f" | acc {acc:5.1f}%" if acc is not None else " | no draft") + f" | wall {wall:6.1f}s", flush=True)
    res.append({"target": target, "chars": chars, "prompt_n": t.get("prompt_n"),
                "prefill_tps": t.get("prompt_per_second"), "prefill_s": t.get("prompt_ms", 0)/1000,
                "decode_tps": t.get("predicted_per_second"), "gen": t.get("predicted_n"),
                "draft_n": dn, "draft_acc": da, "acc": acc, "wall": wall})
json.dump({"tag": TAG, "results": res}, open(f"/home/zyl/bonsai2/depth3_{TAG}.json", "w"), indent=1)
print(f"[{TAG}] 完成 {len(res)}/{len(TARGETS)}", flush=True)
