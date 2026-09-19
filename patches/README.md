# The MTP embedding boundary fix

## Why it is needed

The PrismML fork folds a blockwise Hadamard rotation into the stored weights and applies the matching
transform to activations at runtime. It verifies this at graph-build time
(`llama_verify_hadamard_graph` in `src/llama-graph.cpp` / `libllama.so`), with two hard errors:

```
Hadamard-folded weight '%s' is consumed without its activation transform;
    this graph's matmul path does not support prism.hadamard folding
Hadamard-latent table '%s' is read without the inverse transform
```

The **MTP graph** in `src/models/qwen35.cpp::graph_mtp` reads the token embedding table directly:

```cpp
ggml_tensor * tok_embd_w = layer.nextn.embed_tokens ? layer.nextn.embed_tokens : model.tok_embd;
tok_embd = ggml_get_rows(ctx0, tok_embd_w, inp->tokens);
```

`tok_embd` is a Hadamard-latent table, so the draft head would consume embeddings in the rotated basis. The
verification therefore aborts context creation:

```
E failed to initialize the context: Hadamard-latent table 'token_embd.weight' is read without the inverse transform
E common_speculative_init_result: failed to create MTP context
```

`prism-b10683-d8f26ee` has **no flag** to bypass this (checked with `strings`; the guard is unconditional).

## The reference fix

Apply the inverse transform — counter-rotation plus the explicit per-weight signs — to the embedding lookup,
so the MTP head sees embeddings in the same primal basis as the trunk. Conceptually, right after the
`ggml_get_rows`:

```cpp
if (hadamard_inverses) {
    const auto it = hadamard_inverses->find(tok_embd_w);
    if (it != hadamard_inverses->end()) {
        tok_embd = llama_mul_mat_hadamard(ctx0, tok_embd, it->second.rot);
        if (it->second.signs) {
            tok_embd = ggml_mul(ctx0, tok_embd, it->second.signs);
        }
    }
}
```

**Upstream source of truth (credit):**
[`ProCreations/Ternary-Bonsai-2-27B-MTP`](https://huggingface.co/ProCreations/Ternary-Bonsai-2-27B-MTP) ships this as
`runtime/bonsai-mtp-embedding.patch`, and the runtime source archive they publish already contains it
(`runtime/manifest.json`: `source_is_already_patched: true`, base `d8f26ee`). The snippet above is quoted here
for documentation only; please take the patch from them, not from this file.

## How it was verified here

* Without the fix (official `prism-b10683-d8f26ee` binary): refuses to start, the two errors above.
* With the fix (runtime built from their source for SM89): `creating MTP draft context against the target model`,
  and the measurements in the top-level `README.md` (median **1.338x** decode, aggregate acceptance **68.1%**).

## Why this matters beyond one user

Because the guard is unconditional, **in-file MTP is unusable on official binaries for any Hadamard-folded
release** (Bonsai 2 and anything built the same way). The workaround today is to run a patched runtime; the
useful upstream change is to apply the inverse transform (and audit any other latent table the draft graph
reads) in the fork itself. This was raised on the official model repo:
<https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf/discussions/23>
