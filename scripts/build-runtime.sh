#!/usr/bin/env bash
# Build the PrismML fork runtime (with the MTP embedding inverse-transform fix) for a chosen CUDA arch.
#
# Usage:
#   SRC_TGZ=/path/to/prism-dflash2-source.tar.gz CUDA_ARCH=89 ./build-runtime.sh
#
# The source archive comes from the drafter repo:
#   https://huggingface.co/ProCreations/Ternary-Bonsai-2-27B-MTP/resolve/main/runtime/prism-dflash2-source.tar.gz
#   sha256 8c0f589673b25574f27f013bb3278824384eb35eb984034a2445af3c437b9d05
#   base commit d8f26ee (== prism-b10683-d8f26ee), already patched (see manifest.json: source_is_already_patched)
set -euo pipefail

SRC_TGZ="${SRC_TGZ:?set SRC_TGZ to prism-dflash2-source.tar.gz}"
CUDA_ARCH="${CUDA_ARCH:-89}"          # 89 = Ada (RTX 40xx), 120 = Blackwell, 86 = Ampere consumer, 80 = A100
BUILD_JOBS="${BUILD_JOBS:-$(nproc)}"
NVCC="${NVCC:-/usr/local/cuda/bin/nvcc}"
ROOT="$(cd -- "$(dirname -- "$0")/.." && pwd)"
SRC="$ROOT/runtime-src"

mkdir -p "$SRC"
tar -xzf "$SRC_TGZ" -C "$SRC"

# NOTE: pass -DCMAKE_CUDA_COMPILER explicitly. Without it, CMake fails with
# "CMAKE_CUDA_COMPILER-NOTFOUND" whenever nvcc is not on PATH, which is the
# default in most containers and in WSL.
cmake -S "$SRC/llama" -B "$SRC/llama/build" -G Ninja \
      -DGGML_CUDA=ON \
      -DCMAKE_CUDA_COMPILER="$NVCC" \
      -DCMAKE_CUDA_ARCHITECTURES="$CUDA_ARCH" \
      -DCMAKE_BUILD_TYPE=Release \
      -DLLAMA_CURL=OFF -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF

cmake --build "$SRC/llama/build" -j "$BUILD_JOBS" --target llama-server llama-bench

echo
echo "built: $SRC/llama/build/bin/llama-server"
echo "LD_LIBRARY_PATH=$SRC/llama/build/bin"
