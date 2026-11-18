#!/usr/bin/env bash
# Check whether this machine can run the plugin's analysis path, and report what is missing.
# Read-only: prints a table, changes nothing.
set -u
ROOT="${1:-$HOME/AsusNPU}"
ok=0; bad=0
have() { if [ -e "$1" ]; then printf '  ok   %s\n' "$2"; ok=$((ok+1)); else printf '  MISS %s\n' "$2"; bad=$((bad+1)); fi }

echo "runtime root: $ROOT"
echo
echo "system"
have /usr/lib/firmware/amdnpu "NPU firmware (/usr/lib/firmware/amdnpu, package linux-firmware-amd)"
if lsmod | grep -q '^amdxdna'; then
  printf '  ok   amdxdna kernel module loaded\n'; ok=$((ok+1))
else
  printf '  MISS amdxdna kernel module not loaded (kernel with CONFIG_DRM_ACCEL / amdxdna)\n'; bad=$((bad+1))
fi
if [ -e /dev/accel/accel0 ]; then
  printf '  ok   /dev/accel/accel0 present\n'; ok=$((ok+1))
else
  printf '  MISS /dev/accel/accel0 (NPU device node)\n'; bad=$((bad+1))
fi

echo
echo "AMD runtime and python"
have "$ROOT/framegen-probe/runtime.sh" "framegen-probe/runtime.sh"
have "$ROOT/framegen-probe/bf16-config.json" "framegen-probe/bf16-config.json"
have "$ROOT/sesr-env/bin/python" "sesr-env/bin/python (Python 3.12 venv with numpy)"
have "$ROOT/runtime-1.9/opt/amd/ryzenai/1.9.0/onnxruntime/lib/libonnxruntime.so.1" "Ryzen AI 1.9.0 onnxruntime libs"
have "$ROOT/runtime-1.9/opt/amd/ryzenai/1.9.0/deployment/lib/libonnxruntime_vitisai_ep.so" "VitisAI execution provider"
have "$ROOT/xrt-1.9/opt/xilinx/xrt/lib" "XRT 1.9 libs"
have "$ROOT/ubuntu-compat/usr/lib/x86_64-linux-gnu" "ubuntu-compat libraries"

echo
echo "models and native probes"
have "$ROOT/color-probe/color-probe" "color-probe (adaptive, native)"
have "$ROOT/color-probe/lut-classifier.onnx" "lut-classifier.onnx"
have "$ROOT/color-probe/input.bin" "color-probe/input.bin"
have "$ROOT/hdr-probe/hdr-probe" "hdr-probe (lattice, native)"
have "$ROOT/hdr-probe/hdr-lattice.onnx" "hdr-lattice.onnx"
have "$ROOT/hdr-probe/hdr-probe-tiled" "hdr-probe-tiled (NPU tile path)"
have "$ROOT/hdr-probe/hdr-pointwise.onnx" "hdr-pointwise.onnx"
have "$ROOT/hdr-probe/input.bin" "hdr-probe/input.bin"
have "$ROOT/hdr-probe/npu-tested.json" "npu-tested.json (NPU advertised for HDR)"

echo
echo "summary: $ok present, $bad missing"
[ "$bad" -eq 0 ] && echo "analysis path looks complete" || echo "plugin will install and open, but analysis needs the missing pieces above"
exit 0
