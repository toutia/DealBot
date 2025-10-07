#!/usr/bin/env bash
set -e

# make sure huggingface cli is instaleld and access token added via huggingface-cli login 
# create a virtual env using reqs_hf and use it 

# --- Choose model directory ---
MODEL_DIR=~/models/gpt-oss-20b
mkdir -p "$MODEL_DIR"
cd "$MODEL_DIR"

if [ ! -f ~/models/gpt-oss-20b/config.json ]; then
  echo "⏬ Downloading model (first run only)..."
  huggingface-cli download openai/gpt-oss-20b \
    --local-dir ~/models/gpt-oss-20b \
    --local-dir-use-symlinks False
else
  echo "✅ Model already present, skipping download."
fi

echo "=== Cloning llama.cpp for conversion ==="
cd ~
if [ ! -d llama.cpp ]; then
  git clone https://github.com/ggerganov/llama.cpp.git
fi
cd llama.cpp

echo "=== Building llama.cpp with CUDA for Orin ==="
cmake -B build -DGGML_CUDA=1
cmake --build build --config Release -j$(nproc)

# llama-cpp-python with cuda support
CMAKE_ARGS="-DLLAMA_CUDA=ON -DGGML_CUDA=ON" FORCE_CMAKE=1 pip install --upgrade --force-reinstall llama-cpp-python


echo "=== Converting to GGUF format ==="
python3 convert_hf_to_gguf.py ~/models/gpt-oss-20b \
  --outfile ~/models/gpt-oss-20b-fp16.gguf \
  --outtype f16


echo "=== Verifying model ==="


~/llama.cpp/build/bin/llama-cli \
  -m ~/models/gpt-oss-20b-fp16.gguf \
  -ngl 999 \
   -p "Bonjour, que peux-tu faire ?"\
  --n-predict 1000 \
  --temp 0.8 \
  --top-p 0.95 \
  --repeat-last-n 64 \
  --repeat-penalty 1.1 \
  --threads 12 \
  -sys "Bonjour qu'est ce que tu peux faire"



