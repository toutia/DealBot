#!/usr/bin/env bash
set -e



# --- Choose model directory ---
MODEL_DIR=~/models/gpt-oss-20b
mkdir -p "$MODEL_DIR"
cd "$MODEL_DIR"

echo "=== Downloading GPT-OSS 20B base weights ==="
huggingface-cli download openai/gpt-oss-20b \
  --include "original/*" \
  --local-dir "$MODEL_DIR" \
  --resume-download

echo "=== Cloning llama.cpp for conversion ==="
cd ~
if [ ! -d llama.cpp ]; then
  git clone https://github.com/ggerganov/llama.cpp.git
fi
cd llama.cpp

echo "=== Building llama.cpp with CUDA for Orin ==="
cmake -B build -DGGML_CUDA=1
cmake --build build --config Release -j$(nproc)

echo "=== Converting to GGUF format ==="
python3 convert-hf-to-gguf.py "$MODEL_DIR" --outfile ~/models/gpt-oss-20b-fp16.gguf

echo "=== Quantizing to 4-bit (Q4_K_M) ==="
./build/bin/llama-quantize ~/models/gpt-oss-20b-fp16.gguf \
    ~/models/gpt-oss-20b-q4.gguf q4_K_M

echo "=== Verifying model ==="
./build/bin/llama-cli \
  -m ~/models/gpt-oss-20b-q4.gguf \
  -p "Bonjour, que peux-tu faire ?" \
  --n-predict 40
