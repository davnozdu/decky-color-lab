# Installing Decky Color Lab, and restoring it after a reinstall

Two layers are involved, and only the first one comes from this repository.

1. **The plugin** — `main.py`, `dist/`, `bin/`, `assets/`, `defaults/`. Install the release ZIP
   through Decky Loader. This layer is complete in git.
2. **The analysis runtime** — the ONNX models, native probes, compiled VitisAI caches in `runtime/`
   (7 MB, in git) plus AMD Ryzen AI 1.9.0, XRT and a Python environment in `~/AsusNPU`
   (≈2.7 GB, not in git — see below).

Without layer 2 the plugin installs, the panel opens, presets and the LUT writer work, but
**analysis does not run at all** — not on NPU and not on CPU. Nothing is downloaded automatically;
there is no network code in the plugin. Missing pieces show up as `last_error` in the panel.

## 1. Plugin

```
Decky Loader → Developer mode → Install Plugin from ZIP → Decky-Color-Lab-<version>.zip
```

or from git:

```
git clone https://github.com/davnozdu/decky-color-lab.git "/home/$USER/homebrew/plugins/Decky Color Lab"
```

Restart the plugin afterwards (`main.py` stays in memory until the plugin is restarted).

## 2. System layer

Needed once per install of the OS:

```
sudo pacman -S linux-firmware-amd xrt xrt-plugin-amdxdna
```

* NPU firmware: `/usr/lib/firmware/amdnpu/{1502_00,17f0_10,17f0_11}` (package `linux-firmware-amd`)
* NPU kernel driver `amdxdna` — built into `linux-cachyos-deckify` 7.3.4 and later
* `xrt`, `xrt-plugin-amdxdna` — system XRT

Checks: `lsmod | grep amdxdna`, `ls /dev/accel/`.

## 3. User runtime in ~/AsusNPU

### 3a. Models, caches, native probes (from git)

```
scripts/restore-runtime.sh                      # copies runtime/* into ~/AsusNPU, verifies hashes
```

This is enough to make the CPU engine and the LUT path whole for the model side. It restores:

```
~/AsusNPU/color-probe/   color-probe, lut-classifier.onnx, cache/, input.bin
~/AsusNPU/hdr-probe/     hdr-probe, hdr-probe-tiled, hdr-*.onnx, cache*/, input.bin, npu-tested.json
~/AsusNPU/framegen-probe/ runtime.sh, bf16-config.json
```

### 3b. AMD runtime (not in git, ≈2.7 GB)

`~/AsusNPU/framegen-probe/runtime.sh` expects these paths:

```
~/AsusNPU/runtime-1.9/opt/amd/ryzenai/1.9.0/{onnxruntime/lib,deployment/lib}   Ryzen AI 1.9.0 SDK
~/AsusNPU/xrt-1.9/opt/xilinx/xrt/lib                                           XRT 1.9
~/AsusNPU/sesr-env/bin/python                                                 Python 3.12 venv (numpy)
~/AsusNPU/ubuntu-compat/usr/lib/x86_64-linux-gnu                              Ubuntu libs the SDK links against
```

`deployment/lib` and `onnxruntime/lib` hold the same libraries on a working install — `deployment/lib`
can be a symlink to `../onnxruntime/lib`, which `scripts/restore-runtime.sh` creates.

Two ways to get them:

* **From the release bundle** (fastest, byte-identical to a machine where NPU is proven) — asset of
  [`runtime-v1`](https://github.com/davnozdu/decky-color-lab/releases/tag/runtime-v1):
  `colorlab-runtime.tar.zst`, 1 545 322 018 bytes, 2 988 769 280 bytes unpacked,
  sha256 `9abb29d3da5dec247187cd9cef3295c148ca51a4a5c2967a6fa5f74e093490ed`.

  ```
  gh release download runtime-v1 -R davnozdu/decky-color-lab -p 'colorlab-runtime*' -D /tmp
  cd /tmp && sha256sum -c colorlab-runtime.tar.zst.sha256
  tar --zstd -xf colorlab-runtime.tar.zst -C ~/AsusNPU
  ln -s ../onnxruntime/lib ~/AsusNPU/runtime-1.9/opt/amd/ryzenai/1.9.0/deployment/lib
  ```

* **From AMD**: install Ryzen AI 1.9.0 (needs an AMD account), then rebuild the XRT/venv layout to
  match the paths above. Version drift matters — the VitisAI compiled caches in `runtime/` are
  built for 1.9.0 and will be recompiled (slowly) by other versions.

### 3c. NPU flag

`~/AsusNPU/hdr-probe/npu-tested.json` is committed as measured on an Ally where the NPU path works:
HDR defaults to the NPU engine and the NPU switch is offered. Delete it and HDR falls back to CPU
with the switch refused («NPU-вариант ещё не проверен»).

Re-measure on a new machine rather than trusting a copied flag:

```
source ~/AsusNPU/framegen-probe/runtime.sh
~/AsusNPU/hdr-probe/hdr-probe-tiled ~/AsusNPU/hdr-probe/hdr-pointwise.onnx \
  ~/AsusNPU/hdr-probe/input.bin /tmp/hdr-out.bin ~/AsusNPU/hdr-probe/cache-tiled \
  ~/AsusNPU/hdr-probe/bf16-vectorized.json 0
```

Numbers from the reference machine (tiled variant): CPU inference 17.7 ms, NPU inference 31.7 ms,
NPU process CPU time 5.9 ms vs 17.3 ms on CPU — the NPU wins on CPU load, not on latency.

## 4. Verify

```
scripts/check-runtime.sh          # every path the plugin needs, with ok/MISS per item
```

Then open the panel, press analyse, and confirm the plugin log has no traceback. A wrong engine
choice surfaces as `last_error` in the panel; the analysis log is at `~/AsusNPU/<work>/native-analysis.log`.
