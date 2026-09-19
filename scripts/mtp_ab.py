#!/usr/bin/env python3
"""多 prompt A/B：12 条 × 5 类，temp0/topk1/seed7/n=128，读 timings 的 draft 计数。"""
import json, sys, time, urllib.request, statistics

PORT = int(sys.argv[1]); TAG = sys.argv[2]; NP = int(sys.argv[3]) if len(sys.argv) > 3 else 128
URL = f"http://127.0.0.1:{PORT}/completion"
H = {"Content-Type":"application/json","Authorization":"Bearer sk-lan-97f1c41bb1642ab23f810c65"}

P = {
 "R1 reasoning": "Quantum computing exploits superposition and entanglement to perform computations that are intractable for classical machines. The principal obstacle in practice is decoherence, which",
 "R2 reasoning": "The reason ternary weights appeal to hardware designers is not only the storage density. A ternary multiply accumulator can be implemented as",
 "R3 reasoning": "When a large language model is quantized below two bits per weight, the failure mode that appears first is usually not factual recall but rather",
 "C1 code":      "def merge_intervals(intervals):\n    \"\"\"Merge overlapping intervals.\"\"\"\n    if not intervals:\n        return []\n    intervals = sorted(intervals)\n    merged = [intervals[0]]\n    for start, end in intervals[1:]:\n",
 "C2 code":      "class RingBuffer:\n    def __init__(self, capacity):\n        self.capacity = capacity\n        self.buf = [None] * capacity\n        self.head = 0\n        self.size = 0\n\n    def push(self, item):\n",
 "C3 code":      "async def fetch_all(session, urls, concurrency=8):\n    sem = asyncio.Semaphore(concurrency)\n    async def one(u):\n        async with sem:\n            async with session.get(u) as r:\n",
 "M1 math":      "A train leaves at 09:15 and travels 240 km at an average speed of 96 km/h. It then waits 20 minutes and returns at 80 km/h. Step by step, the arrival time back is",
 "M2 math":      "We flip a fair coin until we see two heads in a row. Let E be the expected number of flips. Setting up the recursion gives",
 "F1 format":    "Output the JSON object for a user record with fields name, age, city, tags (array), then output it again, then again, then again:",
 "F2 format":    "Item 1: alpha\nItem 2: beta\nItem 3: gamma\nItem 4: delta\nItem 5:",
 "Z1 chinese":   "把下面这段技术说明改写成更通俗的中文，保持信息不丢：折叠旋转基把正交变换折进权重，运行时只需对激活做一次同构变换即可。改写结果：",
 "Z2 chinese":   "请用中文解释为什么三值权重（-1、0、+1）在存储上比 int4 更省，并给一个具体数字例子。回答：",
}

def run(name, prompt):
    body = json.dumps({"prompt": prompt, "n_predict": NP, "temperature": 0.0,
                       "top_k": 1, "seed": 7, "cache_prompt": False}).encode()
    t0 = time.time()
    try:
        r = json.load(urllib.request.urlopen(urllib.request.Request(URL, data=body, headers=H), timeout=1800))
    except Exception as e:
        print(f"  {name:14} 失败: {e}"); return None
    wall = time.time() - t0; t = r.get("timings", {})
    dn, da = t.get("draft_n") or 0, t.get("draft_n_accepted") or 0
    tps = t.get("predicted_per_second", 0.0)
    print(f"  {name:14} {tps:6.1f} t/s | {t.get('predicted_n'):4} tok | {wall:5.1f}s wall | "
          f"acc {da/dn*100:5.1f}% ({da}/{dn})" if dn else f"  {name:14} {tps:6.1f} t/s | {t.get('predicted_n'):4} tok | no draft")
    return {"name": name, "tps": tps, "n": t.get("predicted_n"), "wall": wall, "dn": dn, "da": da}

print(f"[{TAG}] n_predict={NP} prompts={len(P)}")
res = [x for x in (run(k, v) for k, v in P.items()) if x]
tps = [r["tps"] for r in res]
tot_n = sum(r["n"] for r in res); tot_w = sum(r["wall"] for r in res)
dn = sum(r["dn"] for r in res); da = sum(r["da"] for r in res)
print(f"  ---- {TAG}: 均值 {statistics.mean(tps):.1f} t/s | 中位 {statistics.median(tps):.1f} | "
      f"端到端 {tot_n/tot_w:.1f} t/s | 接受率 {da/dn*100:.1f}% ({da}/{dn})" if dn else
      f"  ---- {TAG}: 均值 {statistics.mean(tps):.1f} t/s | 中位 {statistics.median(tps):.1f} | 端到端 {tot_n/tot_w:.1f} t/s")
json.dump({"tag": TAG, "results": res}, open(f"/home/zyl/bonsai2/ab_{TAG}.json","w"), indent=1)
