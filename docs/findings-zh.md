# Bonsai 2 27B 的 MTP 推测解码：1.40× 实测（2026-09-19）

**一句话**：把 MTP 块放进**主文件**、让草稿挂在与目标**共享词表**的上下文上，MTP 从"净亏"变成
**decode 1.30–1.67×（合计 1.40×，接受率 69.9%）**。挡在路上的不是头，是**草稿的成本结构**，
以及官方 fork 里一道 7 行的折叠边界闸门。

## 0. 口径

- 卡：RTX 4080 SUPER 16GB（WSL2，CUDA 13.3，本地编译 SM89）。模型：`Ternary-Bonsai-2-27B-PQ2_0-MTP-Q8_0.gguf`（7.66 GB，sha256 `3cb3f005…1dd4` 与发布方 `SHA256SUMS` 逐位一致）。
- 命令（A/B 只差 `--spec-type`）：`llama-server -m <bundle> -ngl 99 -fa on -c 131072 -ctk q4_0 -ctv q4_0 -np 1 -t 16 --temp 0`，A 臂加 `--spec-type none`，B 臂 `--spec-type draft-mtp --spec-draft-n-max 2`。
- 采样：`/completion`，`temperature=0, top_k=1, seed=7, cache_prompt=false, n_predict=96`；接受率读 timings 的 `draft_n/draft_n_accepted`（`llama-cli` 不打印，必须走服务端）。
- 三个 prompt：V=量子计算推理散文、P="The capital of France is"（重复型）、C=Python 函数续写（代码型）。

## 1. 结果 [实测]

| prompt | 无推测 | **draft-mtp (n-max=2)** | 加速 | 接受率 | draft-mtp (n-max=3) | 接受率 |
|---|---:|---:|---:|---:|---:|---:|
| V 推理散文 | 65.3 t/s | **84.6** | **1.30×** | 54.4% | 88.2 | 47.9% |
| P 重复文本 | 65.2 | **109.0** | **1.67×** | 83.1% | 103.1 | 61.6% |
| C 代码 | 65.8 | **103.2** | **1.57×** | 76.0% | 111.3 | 70.3% |
| **合计** | 58.7 | **82.4** | **1.40×** | **69.9%** | 83.0 | 59.0% |

显存：**12488 MiB / 16376**（PQ2_0 + 131072 q4_0 KV + MTP 块），比 PTQ1_0@256K 的 12692 MiB 还低。
`n-max=2` 与 `3` 总吞吐基本打平：2 在重复文本上更好（接受率高），3 在代码上更好。

### 1b. 正式口径：12 prompt × 5 类 × n=128 [实测]

`--spec-type none` vs `draft-mtp --spec-draft-n-max 2`，其余完全相同（`-c 262144 -ctk/-ctv q4_0`，
temp 0 / top_k 1 / seed 7 / `cache_prompt=false` / n=128）：

| 类别 (n) | 基线 t/s | MTP t/s | 加速 | 接受率 |
|---|---:|---:|---:|---:|
| 推理散文 (3) | 66.4 | 84.9 | 1.25–1.31× | 47.7–57.6% |
| 代码续写 (3) | 67.4 | 101.3 | 1.32–1.70× | 62.5–94.3% |
| 数学分步 (2) | 68.2 | 90.6 | 1.23–1.43× | 54.5–72.1% |
| 格式/重复 (2) | 68.3 | 111.9 | 1.63–1.64× | 90.0–92.1% |
| 中文 (1) | 68.5 | 91.7 | 1.34× | 64.5% |
| **中位** | **67.5** | **90.4** | **1.34×** | **68.1%**（803/1180）|

> 第 12 条（中文 Z2）两臂都在第 1 个 token 命中 eos（`stop_type=eos`、content 空），是**裸 `/completion`
> 未套 chat template** 的 prompt 伪影（两条臂完全一致），已从统计中剔除；**这不是模型缺陷**，
> 走 `/v1/chat/completions`（带模板）时正常。

## 2. 为什么之前是净亏：账在 ρ，不在接受率 [推导]

我们 2026-09-11 的 27B **独立 sidecar** 方案（`results/mtp_sidecar.md`）实测 5.16 t/s vs 无 spec 16.6 t/s。
对照本次结果，根因是 sidecar 的**成本结构**：

| 方案 | 草稿每 token 读 | 目标每 token 读 | ρ（成本比）| α=0.405, k=2 的预期 |
|---|---:|---:|---:|---:|
| 独立 sidecar（5.55 GiB，92% 是两份词表矩阵）| ~5.6 GB | 12.94 GB | **0.43** | **0.84×（净亏，与实测吻合）** |
| 本轮：MTP 块在主文件、词表共享 | ~0.45 GB（只有 MTP 块）| 7.66 GB | **~0.06** | **1.3–1.4×（与实测吻合）** |

公式：`加速 ≈ (1−α^(k+1))/(1−α) ÷ (k·ρ + 1)`。**同样的接受率，ρ 从 0.43 掉到 0.06，结论就从净亏翻成 1.4×。**
所以"MTP 不行"是 sidecar 架构的判断，不是 MTP 的判断。

## 3. 真正的闸门：官方 fork 的折叠边界检查（7 行补丁）

用**官方 `prism-b10683` fork** 直接跑这同一个 bundle（`-m <bundle> --spec-type draft-mtp`，不带 `-md`）会**拒绝启动**：

```
E llama_init_from_model: failed to initialize the context:
    Hadamard-latent table 'token_embd.weight' is read without the inverse transform
E common_speculative_init_result: failed to create MTP context
```

这正是本仓库早就刻画过的那类"折叠边界"问题（`mtp_sidecar.md` §2.4 的 gf 边界同理）：
MTP 图直接 `ggml_get_rows` 读 `token_embd`，而折叠模型里它是**旋转基（Hadamard-latent）表**，
草稿图没有施加逆变换。`libllama.so` 里能 `strings` 到守卫本体 `llama_verify_hadamard_graph` 与两条报错
（`Hadamard-folded weight '%s' is consumed without its activation transform` /
`Hadamard-latent table '%s' is read without the inverse transform`），**没有开关可绕**。

社区（`ProCreations/Ternary-Bonsai-2-27B-MTP`）随包发布了修复与源码：
`runtime/bonsai-mtp-embedding.patch` 就是在 MTP 图里补上逆变换 ——

```cpp
// src/models/qwen35.cpp, graph_mtp 内、ggml_get_rows(tok_embd_w, inp->tokens) 之后
if (hadamard_inverses) {
    const auto it = hadamard_inverses->find(tok_embd_w);
    if (it != hadamard_inverses->end()) {
        tok_embd = llama_mul_mat_hadamard(ctx0, tok_embd, it->second.rot);
        if (it->second.signs) tok_embd = ggml_mul(ctx0, tok_embd, it->second.signs);
    }
}
```

`runtime/manifest.json`：`base = Prism d8f26ee…`（即 b10683）、`source_is_already_patched: true`。
所以**源码包已含修复**，直接编译即可；`build-runtime.sh` 的 `CMAKE_CUDA_ARCHITECTURES` 可覆盖 → 本机用 **89**。
本机编译记录：`cmake -DGGML_CUDA=ON -DCMAKE_CUDA_COMPILER=/usr/local/cuda/bin/nvcc -DCMAKE_CUDA_ARCHITECTURES=89`
（注意 `nvcc` 不在 PATH 时要显式给路径，否则 cmake 报 `CMAKE_CUDA_COMPILER-NOTFOUND`），
484 个目标、32 核约 9 分钟，产物 `build/bin/llama-server`。

## 4. 复现

```bash
# 1) 权重（HF，Windows 侧 curl 可达；WSL 内 egress 不通）
#    Ternary-Bonsai-2-27B-PQ2_0-MTP-Q8_0.gguf  7.66 GB  sha256 3cb3f005…1dd4
# 2) 源码（36.5 MB，sha256 8c0f5896…9d05，已含修复）
#    runtime/prism-dflash2-source.tar.gz
tar -xzf prism-dflash2-source.tar.gz          # → llama/
cmake -S llama -B llama/build -G Ninja -DGGML_CUDA=ON \
      -DCMAKE_CUDA_COMPILER=/usr/local/cuda/bin/nvcc \
      -DCMAKE_CUDA_ARCHITECTURES=89 -DCMAKE_BUILD_TYPE=Release -DLLAMA_CURL=OFF
cmake --build llama/build -j 28 --target llama-server llama-bench
# 3) 起服务（注意：不要传 -md，MTP 块在主文件里）
LD_LIBRARY_PATH=llama/build/bin llama/build/bin/llama-server \
  -m Ternary-Bonsai-2-27B-PQ2_0-MTP-Q8_0.gguf -ngl 99 -fa on \
  -c 131072 -ctk q4_0 -ctv q4_0 -np 1 --spec-type draft-mtp --spec-draft-n-max 2
# 4) 量接受率（llama-cli 不打印）：读服务端 timings 的 draft_n/draft_n_accepted，
#    或日志里的 "slot print_timing: draft acceptance = …"
```

## 5. 与社区/官方数字的关系

- 社区同一份头的自报是 **head-vs-head**：+0.54%（DFlash2）/ +1.26%（MTP），**不是 vs 无草稿**；本次给出的是 vs 无草稿的 **1.40×**。
- 社区把 target 从 PTQ1_0 换成 PQ2_0 后，无推测基线 58.7 t/s 低于我们 PTQ1_0 的 ~76 t/s —— 与官方"PTQ1_0 在 Ada 上 decode 更优"一致；但 PQ2_0 的 prefill 更快，且 MTP 只支持 PQ2_0 这档。
- 我们的独立 sidecar 方案在同一台机上测到 40.5% 接受率（推理散文），本轮共享词表的 MTP 是 **54.4%** —— 说明"草稿与目标共享词表"不只是省钱，**接受率也更高**（草稿的 embedding/head 与目标逐位一致）。

## 6. 生产切换与社区发布（2026-09-19 已完成）

**生产已切**：新增 `systemctl --user llama-bonsai-mtp`（enabled，占 8080），配置 =
本 bundle + 本地自建运行时 + `-c 262144 -ctk/-ctv q4_0` + `--jinja --reasoning-preserve`
+ `--spec-type draft-mtp --spec-draft-n-max 2`。老的 `llama-bonsai`（PTQ1_0 + 256K）**保留未删**，
`systemctl --user enable --now llama-bonsai` 可一键回退（两者互斥，同时只能跑一个）。

256K 下的实测对比（同 KV 类型 q4_0）[实测]：

| 配置 | prefill（12.5k prompt）| decode | 显存 |
|---|---:|---:|---:|
| PTQ1_0 + 256K（旧）| 1073 t/s | ~76 t/s | 12692 MiB |
| **PQ2_0 + MTP + 256K（新）** | **1726 t/s** | **90.4（中位）** | **15727 MiB** |

→ **PQ2_0 的 prefill 比 PTQ1_0 快 1.6×，与官方"PQ2_0 赢 prefill"一致**；代价是显存贴到 15.7/16 GiB
（只剩 ~650 MiB，桌面抢显存时需回退 `-c 131072`）。注意 256K 下仍会出现
`common_fit_params: failed to fit params` 警告，但**实测 prefill 1726 t/s 无异常** ——
当初 prefill 崩到 101 t/s 的元凶是 **q8_0 KV 撑爆显存**，不是 256K 本身，也不是这条警告。

**社区发布**（HF，账号 zhaokeqi）：
- 官方模型仓：[`prism-ml/Ternary-Bonsai-2-27B-gguf` discussions/23](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf/discussions/23)
  —— 报"官方 fork 的 MTP 图拒绝 Hadamard 折叠表"这个 bug + 7 行修复 + 1.34× 实测，建议上游。
- 补丁作者仓：[`ProCreations/Ternary-Bonsai-2-27B-MTP` discussions/2](https://huggingface.co/ProCreations/Ternary-Bonsai-2-27B-MTP/discussions/2)
  —— Ada/SM89 独立复现 + 提醒 README 的 `+1.26%` 是 head-vs-head 而非 vs 无草稿。
- **公开复现包**（dataset 仓，public）：[`zhaokeqi/bonsai2-27b-mtp-repro`](https://huggingface.co/datasets/zhaokeqi/bonsai2-27b-mtp-repro)
  —— 两个讨论帖各追加了一条**原始数据回复**（逐条 prompt 的 base/MTP/加速/接受率、测量协议、
  16GB 卡的 KV 陷阱、未测项），并各追加一条**内嵌 A/B 图**的短回复；bundle 内含两臂**逐条 timings
  原始 JSON**（`ab_base.json` / `ab_mtp.json` / `mtp_n3.json`）、A/B harness（`mtp_ab.py`）、驱动脚本、
  英文报告与图（`chart_en.png` / `chart_zh.png`）。两个帖子均 `status=open`。
- **配图**：本机 matplotlib 出图，英文版进 HF、中文版用于朋友圈；图随 bundle 公开（resolve URL 实测
  `206 image/png`）。图本身读出的规律：**加速跟着接受率走，接受率跟着"文本可预测性"走**
  （Python/列表/JSON 续写 77–94% 接受率、1.5–1.7×；自由推理散文 48–58%、1.25–1.3×）。

> **本机 HF 工具链的两个坑（下次直接用）**
> 1. `huggingface_hub` 报 `Invalid user token` 的**真因是环境变量 `HF_ENDPOINT=https://hf-mirror.com`**
>    —— hf_hub 把 token 发给了镜像，镜像不认。设回 `https://huggingface.co` 后 `whoami()` 立刻通过。
> 2. NDJSON commit 接口（`POST /api/datasets/{repo}/commit/main`）**拒收二进制**（"contains binary files…
>    use xet"），文本文件可用；PNG 这类必须走 `HfApi.upload_file`（Xet/LFS）。

## 7. 下一步（未做）

1. **多 prompt 多次重复**：本轮每 prompt 单次，PR 口径建议重复 2–3 次取均值（当前单次已足够看出量级）。
2. **把 gf 边界补偿写进导出管线**（`mtp_sidecar.md` §6 的老账），并把 `mtp_sidecar.py` 折进新协议。
3. **向上游提 patch**：GitHub 从本机不可达（全域名 000），补丁与复现步骤已随 HF 讨论帖给出。
4. `-spec-draft-n-max` 扫参（2/3/4）与 `--spec-draft-*` 家族（DFlash2 头在 Ada 上的对比）。
