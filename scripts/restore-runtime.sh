#!/usr/bin/env bash
# Install the small runtime part (models, caches, native probes) from this repository
# into ~/AsusNPU, verify hashes and repair the runtime library layout.
# The multi-gigabyte AMD runtime itself is NOT in git; see INSTALL.md.
set -euo pipefail

repo_runtime="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../runtime" && pwd)"
root="${1:-$HOME/AsusNPU}"

echo "source: $repo_runtime"
echo "target: $root"
mkdir -p "$root"

for dir in color-probe hdr-probe framegen-probe; do
  mkdir -p "$root/$dir"
  cp -a "$repo_runtime/$dir/." "$root/$dir/"
  echo "copied $dir"
done

echo
echo "verifying hashes against runtime/MANIFEST.sha256"
cp -a "$repo_runtime/MANIFEST.sha256" "$root/MANIFEST.sha256"
( cd "$root" && sha256sum -c --quiet MANIFEST.sha256 ) && echo "hashes ok"

# runtime.sh puts both $RYZEN_AI_PATH/deployment/lib and .../onnxruntime/lib on LD_LIBRARY_PATH.
# They hold the same libraries; the runtime bundle ships one copy and a symlink.
sdk="$root/runtime-1.9/opt/amd/ryzenai/1.9.0"
if [ -d "$sdk/onnxruntime/lib" ] && [ ! -e "$sdk/deployment/lib" ]; then
  mkdir -p "$sdk/deployment"
  ln -s ../onnxruntime/lib "$sdk/deployment/lib"
  echo "linked deployment/lib -> onnxruntime/lib"
fi

echo
echo "now run: $(dirname -- "${BASH_SOURCE[0]}")/check-runtime.sh $root"
