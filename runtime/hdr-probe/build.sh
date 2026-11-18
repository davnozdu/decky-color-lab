#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
source ../framegen-probe/runtime.sh
g++ -std=c++17 -O2 probe.cpp -I"$RYZEN_AI_PATH/onnxruntime/include/onnxruntime" \
 -L"$RYZEN_AI_PATH/onnxruntime/lib" -lonnxruntime -o hdr-probe
