# On-device runtime files (what the plugin reads outside its own folder)

`main.py` does not keep its analysis machinery inside the Decky plugin directory. It launches

```
bash -c 'source ~/AsusNPU/framegen-probe/runtime.sh; exec ~/AsusNPU/sesr-env/bin/python bin/analyzer.py ~/AsusNPU <workdir> <model> <engine>'
```

so everything the models need lives in `~/AsusNPU` on the device. This folder is the small part of
that tree — models, compiled VitisAI caches, native probe binaries and their sources, 7 MB. The
multi-gigabyte AMD runtime is not here; see `INSTALL.md`.

Copy the contents of this folder into `~/AsusNPU/` on the device, preserving the layout:

```
~/AsusNPU/
  framegen-probe/runtime.sh            sets RYZEN_AI_*, XILINX_XRT, PYTHONHOME, LD_LIBRARY_PATH
  framegen-probe/bf16-config.json      VAIML partition config (non-tiled HDR path)
  color-probe/color-probe              native probe: runs lut-classifier.onnx on VitisAI or CPU
  color-probe/lut-classifier.onnx      Image-Adaptive-3DLUT classifier, exported
  color-probe/cache/                   compiled VitisAI cache for the classifier
  color-probe/input.bin                fixed 256x256x3 input used by the probe
  hdr-probe/hdr-probe                  native probe, full 33^3 lattice (CPU and NPU)
  hdr-probe/hdr-probe-tiled            native probe, pointwise tile path (the NPU variant in use)
  hdr-probe/hdr-lattice.onnx           HDRTVNet++ AGCM global stage, 33^3 lattice output
  hdr-probe/hdr-pointwise.onnx         the same stage as a pointwise network, for tiling
  hdr-probe/hdr-condition.onnx         condition branch
  hdr-probe/cache/ cache-tiled/ ...    compiled VitisAI caches per variant
  hdr-probe/npu-tested.json            "NPU verified on this machine" flag + measured numbers
```

`bin/analyzer.py` picks `hdr-probe-tiled` + `cache-tiled` + `hdr-pointwise.onnx` when the tiled
binary exists, otherwise `hdr-probe` + `cache` + `hdr-lattice.onnx`. `npu-tested.json` only advertises
the NPU path; delete it and HDR falls back to the CPU engine.

## Provenance and licences

| Model | Origin | Licence |
| --- | --- | --- |
| `lut-classifier.onnx` | Image-Adaptive-3DLUT classifier weights, rewritten with explicit instance-norm, exported by `color-probe/export.py` (source commit in `color-probe/preparation.json`) | Apache-2.0, `color-probe/LICENSE.upstream` |
| `hdr-lattice.onnx`, `hdr-pointwise.onnx`, `hdr-lattice-dynamic.onnx`, `hdr-condition.onnx` | HDRTVNet++ AGCM global stage only, exported by `hdr-probe/export*.py`; PQ BT.2020 output, fixed 256x256 condition | MIT, `hdr-probe/LICENSE.upstream` (Hoven Li, 2023) |

No custom training was done: the weights are the published pretrained ones, re-exported for
onnxruntime so they can run on the XDNA2 NPU. The 33^3 LUT approximates the pointwise network
between grid points; measured errors are in `hdr-probe/hdr-model-audit.json` and
`color-probe/README.md`.

## Verification

```
cd ~/AsusNPU && sha256sum -c MANIFEST.sha256
```

The manifest lists every file in this folder. Native binaries are x86-64 Linux; rebuild them on the
device with the `build.sh` scripts if they ever stop matching the installed runtime.
