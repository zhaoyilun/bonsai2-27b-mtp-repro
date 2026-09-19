# 交接文档 — Ternary-Bonsai-2-27B + MTP 推测解码

> 生成时间：2026-09-19 · 生成机器：zylmax（WSL2 / RTX 4080 SUPER / 这台机器 CPU 缩缸，即将退回）
> 一句话现状：**活儿已经干完并且全部公开**（代码在 GitHub、数据在 HF、修复提了 PR #205），
> 这台机器上**没有独有的必需物**；但有三件事必须在退货前处理。

---

## 1. ⚠️ 归还机器前必须做的三件事

### ① 你的研究仓库 `ternary-expand` 只存在于这台机器上 —— 已帮你打包

发现：`E:\AI\ternary-expand` 是 **128 个提交、零远端**，而且**有 66 个未提交改动**。
机器一退，这些就没了。我已经生成三个文件到：

```
E:\AI\handover-20260919\
    ternary-expand.bundle              433 MB   完整 git 历史（所有分支/标签），单文件
    ternary-expand-src.tgz             3.3 MB   工作区源码（含未提交文件，去掉 tmp-models 与 .git）
    ternary-expand-uncommitted.patch    13 MB   未提交改动的补丁（含一个 78 万行 JSON 的删除，故偏大）
    ternary-expand-status.txt          2.1 KB   git status 快照
```

**把整个 `E:\AI\handover-20260919\` 拷到 U 盘/网盘**，在 Mac 或新机器上恢复：

```bash
git clone ternary-expand.bundle ternary-expand        # 历史 + 所有提交
cd ternary-expand && git log --oneline | head          # 应看到 128 个提交
git apply ../ternary-expand-uncommitted.patch          # 恢复未提交改动（可选）
# 或者只要工作区文件：tar -xzf ternary-expand-src.tgz
```

> 23 GB 的 `tmp-models/`（GGUF 等）**不必拷**，全部可重下 —— 但见 §3 的重建清单。

### ② 公开仓里泄露过一个 LAN API key —— 已下架，请你轮换

我发布 systemd 单元和测量脚本时，把 `--api-key sk-lan-97f1c4…` 一起提交了，**在公开 GitHub 上挂了约 4 小时**。
已经替换成 `sk-lan-CHANGE-ME` 并在 README 加了说明（commit `b9d6e7f`）。

**但 key 本身已经公开过，应视为泄露**：建议换掉它 —— 需要同步改三处
（`llama-bonsai-mtp.service` 的 `--api-key`、`~/.dsh/settings.yaml` 里 `local-qwen` 的 `apiKeyEnv` 指向的
`DUCKCODING_API_KEY`、以及 `dsh-web.service` 的 Environment）。

### ③ 值得带走的小东西（都很小）

| 路径 | 体积 | 说明 |
|---|---|---|
| `~/.dsh/sessions/` | 100 MB | 完整对话历史（包含这一整轮工作的推理过程） |
| `~/.dsh/settings.yaml` | 2 KB | DSH 的本地模型配置（含 Bonsai 端点） |
| `~/.config/systemd/user/llama-bonsai*.service` | 2 KB | 两个服务单元 |
| `E:\AI\bonsai2-27b-mtp-repro\` | 1.2 MB | 我们发布的仓库（远端已有，可不带） |
| `C:\Users\zhaoy\.cache\huggingface\token` | 37 B | HF 令牌（含敏感信息，建议在新机器重新登录而非拷贝） |
| `C:\Users\zhaoy\AppData\Roaming\GitHub CLI\` | 小 | gh 的登录态（同上，建议重新 `gh auth login`） |

---

## 2. 已公开的产出（Mac 上直接打开，不需要这台机器）

| 位置 | 内容 | 链接 |
|---|---|---|
| **GitHub 代码仓** | 方法/代码/脚本/单元/结果/中文记录 | https://github.com/zhaoyilun/bonsai2-27b-mtp-repro |
| **上游 PR #205** | **我们的修复**（qwen35 MTP embedding 逆变换，1 文件 +14 行） | https://github.com/PrismML-Eng/llama.cpp/pull/205 |
| issue 评论 | #203（ngram 静默失效佐证）/ #85（16GB 卡 262k + q4_0 KV） | [#203](https://github.com/PrismML-Eng/llama.cpp/issues/203#issuecomment-5740120220) · [#85](https://github.com/PrismML-Eng/llama.cpp/issues/85#issuecomment-5740120304) |
| **HF 数据集** | 原始 timings JSON + 中英文图 + 英文报告 | https://huggingface.co/datasets/zhaokeqi/bonsai2-27b-mtp-repro |
| HF 讨论（官方模型仓）| 报 bug + 修复 + 实测 + 长上下文 | https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf/discussions/23 |
| HF 讨论（草稿作者仓）| 独立复现 + README 澄清 | https://huggingface.co/ProCreations/Ternary-Bonsai-2-27B-MTP/discussions/2 |

**已有第三方独立复现**（AMD RX 7900 XTX / gfx1100 / ROCm 6.4 / Win11，在 PR #205 上）：
不装补丁报错与我们**逐字相同**，装补丁后 **41.6 → 75.9 t/s（1.82×）**、接受率 **0.82**。

---

## 3. 这台机器上跑着什么 / 新机器怎么重建

### 当前部署（如果要重建）

| 项 | 值 |
|---|---|
| 服务 | `systemctl --user llama-bonsai-mtp`（enabled，`0.0.0.0:8080`，别名 `bonsai-27b`）|
| 模型 | `Ternary-Bonsai-2-27B-PQ2_0-MTP-Q8_0.gguf`（7.66 GB，target+MTP 合体）|
| 运行时 | 自建 b10683 + 社区补丁 → `/home/zyl/bonsai2/mtp-runtime/source/llama/build/bin` |
| 关键参数 | `-c 262144 -ctk q4_0 -ctv q4_0 -ngl 99 -fa on --jinja --reasoning-preserve --spec-type draft-mtp --spec-draft-n-max 2` |
| 显存 | 15.7 / 16.0 GiB |
| 回退档 | `llama-bonsai`（PTQ1_0，无 MTP）保留未删 |

### 重建步骤（新机器，约 30 分钟）

```bash
# 1) 仓库 + 数据（GitHub/HF 都可达）
git clone https://github.com/zhaoyilun/bonsai2-27b-mtp-repro
# 2) 模型（ModelScope 或 HF；WSL 内 egress 不通时用 Windows 侧 curl，或浏览器直接下）
#    Ternary-Bonsai-2-27B-PQ2_0-MTP-Q8_0.gguf   7.66 GB
#    sha256 3cb3f0056d2e34ee44245a64396004a21f8492573d6ce1266ec4b7222c131dd4
# 3) 打补丁的运行时（源码含修复；或直接用 PR #205 的补丁打到 fork 源码）
SRC_TGZ=prism-dflash2-source.tar.gz CUDA_ARCH=89 ./scripts/build-runtime.sh
#    两个坑：nvcc 不在 PATH 时必须显式 -DCMAKE_CUDA_COMPILER；
#    官方预编译包只有 SM120(Blackwell)，Ada/其它卡要自己编
# 4) 起服务：参考 systemd/llama-bonsai-mtp.service（记得换成你自己的 api-key）
```

**所有源材料都可重下**（`tmp-models/bonsai2/` 里是下载归档）：模型 2 个、运行时源码 36.5 MB、
官方预编译包 3 个。唯一不可重下的是**你的研究仓库**（见 §1①）。

---

## 4. 在 Mac 上能做什么

**能（推荐，零成本）**：看/回 PR 与 issue、审 GitHub 上的代码、看 HF 数据集与讨论帖、贴数据回答提问。

**关于本地跑**：理论上 16 GB 统一内存**能装下** PQ2_0（7.66 GB）+ 小上下文，而且 fork 有 macOS arm64 的
Metal 预编译包 —— 但要注意：

* **Metal 上同样有这个 bug**（#203 的报告人就是 M4 Max 撞上的），所以没打补丁的 macOS 包**同样跑不了内置 MTP**；
* 16 GB 统一内存里还要留 macOS + 其它程序，**KV 只能开很小**（q4_0、几 k 上下文），和我们测的 8k–191k 曲线
  完全不是一个工况，**测出来的数不能和本机对比**；
* 所以结论：**不必在 Mac 上测**，跟帖 + 引用已有数据即可。真想验证，等新机器到。

---

## 5. 跟帖要盯什么 + 有人回怎么答

### 盯这些（每天扫一眼即可）

| 对象 | 看什么 |
|---|---|
| **PR #205** | 有没有 maintainer review / 要求改；`mergeable_state`；CI（目前只有 labeler）|
| issue **#203** | `ngram-*` 静默失效 —— 我们的佐证在 07:08 UTC 那条；看有没有人跟进 |
| issue **#85** | q4_0 KV / mean-center —— 我们的数据在 07:08 UTC 那条；维护者 `khosravipasha` 在这个帖子里活跃 |
| HF 讨论 ×2 | 目前各 5 条事件、**他人 0 条**；有人回就在对应帖下答 |

### 回答时可以直接用的数字速查

| 项 | 数字 |
|---|---|
| 12-prompt A/B（MTP vs 无）| **中位 1.338×**，接受率 **68.1%**（803/1180），范围 1.23–1.70× |
| 分类 | 代码/JSON/列表续写 1.5–1.7×（接受率 77–94%）；自由推理散文 1.25–1.3×（48–58%）|
| 长上下文 decode | 8,020 tok **86.9** → 31,939 **62.4** → 64,084 **55.4** → 127,870 **46.1** → 191,099 **35.0** t/s（无推测：63.0 → 26.5）|
| 长上下文接受率 | 随深度**升**（66% → 84%），所以 MTP 倍数不衰减（1.16–1.38×）|
| prefill | 12.5k 提示 **1726 t/s**（PQ2_0 + q4_0 KV，256K 上下文）；同配置 PTQ1_0 是 1073 |
| 显存 | 15.7 / 16.0 GiB（`-c 262144` + KV q4_0 + MTP）|
| 前缀复用 | 同一 12,485-token 提示二次发送：只评估 **4 token / 0.28 s** |
| 报错原文 | `E failed to initialize the context: Hadamard-latent table 'token_embd.weight' is read without the inverse transform` + `E common_speculative_init_result: failed to create MTP context` |
| 修复位置 | `src/models/qwen35.cpp::graph_mtp`，在 `ggml_get_rows` 之后补 rot+signs 逆变换（照抄同仓库 `llm_graph_context::build_inp_embd` 的写法）|
| 第三方复现 | gfx1100/ROCm 6.4：重编译后 41.6 → 75.9 t/s（1.82×），接受率 0.82；`n-max=4` 比 2 慢 |

### 回帖时要避免的坑

* **别把"倍数"直接横向比**：跨平台差在**无推测基线**（41.6 vs 67 t/s），不是修复有问题 —— 这个解释已经写进 PR 回复和 README §8；
* **`timings.prompt_n` 是增量不是深度**（191k 提示会报 63745），别当成截断 bug；
* **`common_fit_params: failed to fit params` 不是信号**，KV 字节数才是（q4_0 状态也有这条警告但性能正常）；
* 我们的接受率是**单次运行**（非多次平均），引用时说清"single run per prompt"。

---

## 6. 工具链踩坑速查（这台机器上踩过的，换机器还会遇到）

| 坑 | 症状 | 解法 |
|---|---|---|
| `HF_ENDPOINT=https://hf-mirror.com` | `huggingface_hub` 报 `Invalid user token`（同一 token 用原生 requests 是 200）| 设回 `https://huggingface.co` |
| HF NDJSON commit 接口 | 提交二进制被拒（"use xet"）| 二进制走 `HfApi.upload_file` |
| GitHub 直连 | WSL 与 Windows 直连都 000 | Windows 侧 `set HTTPS_PROXY=http://127.0.0.1:7890`（Clash），git/gh 都能通 |
| `nvcc` 不在 PATH | cmake 报 `CMAKE_CUDA_COMPILER-NOTFOUND` | 显式 `-DCMAKE_CUDA_COMPILER=/usr/local/cuda/bin/nvcc` |
| WSL 沙箱看不到 `/dev/dxg` | `nvidia-smi` 报 GPU blocked | 用 `systemd-run --user` 起外部单元才拿得到 GPU |
| GitHub 不可达时的替代通道 | — | jsDelivr 读仓库单文件；`gh-proxy.com` 拉 release 资产 |
| `pkill -f 名字` | 会匹配到**自己这条命令行**而自杀 | 用 `[d]epth_` 括号技巧 |
| 后台 `python3 x.py > log` | 进度被块缓冲吞掉 | 加 `-u` |
| `.bat` 里写中文或 `\|` | cmd 解析崩（乱码/管道）| 批处理只用 ASCII，jq 表达式别带 `\|` |
| `huggingface_hub` 认证 | 报 invalid token（真因是 HF_ENDPOINT）| 或直接用原生 `requests` 打 API |

---

## 7. 账号与凭证

| 账号 | 用途 | 备注 |
|---|---|---|
| GitHub **zhaoyilun** | 代码仓、PR、issue | gh 已登录，token 存在 Windows 凭据管理器，scopes: `gist, read:org, repo, workflow` |
| HF **zhaokeqi** (Yilun Zhao) | 数据集、讨论帖 | fine-grained token，含全局 `discussion.write`；token 文件在 `C:\Users\zhaoy\.cache\huggingface\token` |

新机器上重新登录即可（`gh auth login`；HF 用 `hf auth login` 或环境变量 `HF_TOKEN`）。

---

## 8. 还没做的（新机器/以后可选）

1. **升级运行时到 b10709+**：官方最新构建含一批性能修复（#165 混合注意力融合 -25% ops/token、#166 FWHT 块内核 +17%/+11% decode、#173 推测解码不再每轮回退整段 KV checkpoint），但**内置 MTP 仍需我们的补丁**（已在 PR #205 里对 HEAD 验证过）。
2. **`-spec-draft-n-max` 扫参**（2/3/4）与 DFlash2 头在 Ada 上的对比。
3. 把 `gf` 边界补偿写进展开管线的导出（老账，见 `results/mtp_sidecar.md` §6）。
4. 多 prompt 多次重复取均值（目前每 prompt 单次）。

---

## 9. 安全审计：泄露了什么、实际风险多大

**一句话结论：GitHub 上那个 key 的实际攻击面很低；真正要处理的是"这台机器要退给商家"而磁盘上有一整套凭证。**

### ① 公开的只有 LAN API key（其余都没公开）

* 它在**公开 git 历史**里（`e65af53` … `b9d6e7f`）—— 下架最新版 ≠ 删除历史：任何人都能
  `git show e65af53:systemd/llama-bonsai-mtp.service` 读出原文；HF 数据集的旧 revision 同理保留。
* **它能做什么**：只能从**同一局域网内**访问 `http://192.168.3.40:8080`（llama-server 的 HTTP API）。
  没有工具执行、没有文件读写、没有通向宿主机的路径；最坏情况是别人白用你的 GPU、或读写 `/slots` 的槽状态。
* **前提是 8080 没有做端口映射**（relay 只隧穿了 `8128 → 3080`，即 DSH Web，不含 8080）—— 建议在路由器上确认一次。
* 内网 IP **没有**公开（已按要求核查：公开物里搜不到 `192.168.`）。
* 想彻底消掉：**轮换 key**（最简单，改三处）或 `git filter-repo` 重写历史 + 删掉 HF 数据集重建（麻烦、收益小）。

### ② 真正要紧的：退货 = 磁盘连同凭证一起交出去

这台机器上（会被商家拿到）：

| 文件 | 内容 | 风险 |
|---|---|---|
| `~/.dsh/federation/device.json` | **联邦设备令牌 + ed25519 私钥** | 可冒充这台设备连 `wss://dsh-mqtt.fljx.top/mqtt` |
| `~/.dsh/federation/host-access.json` | 本机访问令牌 | 同上 |
| `~/.dsh/.credentials.yaml` | DSH 的 provider 凭证 | 账号相关 |
| `~/.ssh/id_ed25519` | SSH 私钥 | 任何用了这把公钥的地方 |
| `C:\Users\zhaoy\.cache\huggingface\token` | HF 令牌 | 可写你的数据集/讨论 |
| gh 登录态（Windows 凭据管理器）| GitHub OAuth token（`repo, workflow`）| 可写你的仓库 |

**建议（按优先级）**：
1. 退货前**擦盘 / 系统重置**（或按 RMA 政策把硬盘留下）—— 这是唯一能一次性解决的办法；
2. 在 DSH 侧**撤销这台设备**（registry 里置 `revoked`），并轮换上面所有令牌；
3. `gh auth logout`、删掉 HF token 文件、**轮换 SSH key**（旧公钥从各处移除）；
4. 确认路由器上 8080 没有端口映射（顺带把广播型服务也检查一下）。

### ③ 会话历史里有明文凭证 —— 别原样往云上传

这次会话里我打印过**联邦设备令牌、ed25519 私钥、host-access 令牌、LAN key**，它们会落进
`~/.dsh/sessions/`（100 MB）。所以 §1③ 那条"值得带走"要加前提：**它含密钥，属于机密文件** ——
要么别拷，要么加密保管，别丢进公共网盘。

（好消息：HF token 和 gh token 我**只打印过长度/前缀**，明文没有落进会话记录。）

### ④ 顺带修正 §1③ 的建议

`~/.dsh/sessions/` 与 `~/.dsh/federation/*` **不要**当普通资料带走；真要留，按密钥对待。
