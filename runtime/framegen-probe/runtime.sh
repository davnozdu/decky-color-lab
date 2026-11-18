#!/usr/bin/env bash
# Source from any directory; uses only the user-local AMD runtime.
PROBE_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
export RYZEN_AI_INSTALLATION_PATH="$PROBE_ROOT/runtime-1.9/opt/amd/ryzenai/1.9.0"
export RYZEN_AI_PATH="$RYZEN_AI_INSTALLATION_PATH"
export XILINX_XRT="$PROBE_ROOT/xrt-1.9/opt/xilinx/xrt"
PYTHON_ROOT=$("$PROBE_ROOT/sesr-env/bin/python" -c 'import sys; print(sys.base_prefix)')
export PYTHONHOME="$PYTHON_ROOT"
export PYTHONPATH="$PROBE_ROOT/sesr-env/lib/python3.12/site-packages"
export LD_LIBRARY_PATH="$XILINX_XRT/lib:$PYTHON_ROOT/lib:$PROBE_ROOT/ubuntu-compat/usr/lib/x86_64-linux-gnu:/usr/lib:$RYZEN_AI_PATH/deployment/lib:$RYZEN_AI_PATH/onnxruntime/lib"
