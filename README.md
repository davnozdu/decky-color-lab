# Decky Color Lab 0.4 — Ally experimental build

0.4: movie/video players (VLC, mpv, Kodi, Jellyfin, Plex, Stremio, streaming apps; browsers only for non-Steam shortcuts) get, on first focus, the Cinema preset with automatic analysis every 2 s and the HDRTVNet++ pseudo-HDR model. Existing manual profiles are untouched. Letterbox/pillarbox bars are cropped from the analysis thumbnail (reported as `letterbox` fraction) so black bars do not bias the look. HDR defaults to the NPU executor when ~/AsusNPU/hdr-probe/npu-tested.json exists. Any running app can be set manually to «Игра» or «Фильмы и видео» in the panel (stored in its profile). Scene tracking (video default): a capture+histogram probe ~2×/s on CPU, the network runs immediately on a scene cut and otherwise at the chosen interval. `gamescopectl screenshot` captures before the look is applied, so screenshots cannot verify a look; 0.4.1: interval «Авто» (default for Cinema/Games) picks 10 s / 2 s / 1 s from the smoothed picture drift measured by the probes; verification is visual (diagnostic LUT) or offline LUT application.

Two choices: Image-Adaptive-3DLUT adaptive SDR color and HDRTVNet++ AGCM SDR-to-HDR global mapping followed by a custom SDR preview tone map. AGCM is only the global stage, not the full three-stage HDRTVNet++ pipeline. No true HDR output is enabled. The original Pseudo-HDR preset is a separate tone curve.

Native PipeWire capture obtains Gamescope BGRx buffers directly. It requests a 256×144 buffer and produces a 256×256 RGB thumbnail. No screenshot command, PNG encoding or screenshot notification is used. The persistent consumer pauses between requests and can reuse its last frame while a scene is static. Corrupted buffers during renegotiation are discarded.

CNN input is fixed at 256×256; this is experimental preprocessing for HDRTVNet++. A 33³ color lattice approximates its pointwise mapping. PQ/BT.2020 output is decoded to linear light, converted to BT.709, and filmic tone mapped to SDR Gamma22. LUT interpolation has measurable approximation error; quality is subjective and not guaranteed to improve all content.

Adaptive 3DLUT uses CPU normalization and NPU convolutions. HDRTVNet++ offers CPU reference and experimental CPU+NPU executors. The scene classifier runs on CPU; nine 64×64 color-lattice tiles use NPU convolution plus CPU feature/affine setup. CPU reference remains default for HDR. Availability is recorded in ~/AsusNPU/hdr-probe/npu-tested.json. Warm benchmark: CPU 17.7 ms wall / 17.3 ms process CPU; hybrid 31.7 ms wall / 5.9 ms process CPU. BF16 can differ substantially for extreme saturated RGB grid points; one RDR2 frame had MAE 0.00353, p99 0.01738, max 0.04297 at full effect, before strength blending. This is not a general quality guarantee. NPU use alone does not prove lower energy consumption. No FPS or battery improvement is established.

Profiles are stored by Gamescope base AppID and display EDID. Steam overlays do not change the base app identity. Each profile stores model, preset, strength, black adjustment, enabled/auto state and interval. Steam shell processing defaults off. External display switching and movie applications have not been physically tested. Apps and movies must run inside this Gamescope session; arbitrary desktop players are not filtered.

Runtime color LUTs, captured data and worker logs live in /run/user/1000/decky-color-lab (RAM). User settings persist in ~/homebrew/data/Decky Color Lab/settings.json. The look is global to the current Gamescope output, without independent simultaneous processing for multiple displays. NPU runtimes, environments and model files remain device-specific under ~/AsusNPU.

Native dependencies: Wayland (legacy helper), PipeWire and X11. Build frontend with npm run build. The systemd override /etc/systemd/system/plugin_loader.service.d/20-npu-memory.conf raises LimitMEMLOCK to 512M for NPU buffers; it is a ceiling, not a reservation. Plugin stays unprivileged. Helpers run at nice 10. Disable clears only the Gamma22 look. The CLI accepts one value argument: gamescopectl set_look PATH. Do not add a separate g22 argument. Visible output was verified by a user-observed green diagnostic. Old static LUT performance comparisons were invalid and must be repeated. Manual reset within Gamescope: gamescopectl set_look /dev/null.

Code/template BSD-3-Clause (LICENSE); adaptive LUT weights Apache-2.0 (assets/LICENSE-Image-Adaptive-3DLUT); HDRTVNet++ AGCM weights MIT (assets/LICENSE-HDRTVNet-plus). Source: HuiZeng/Image-Adaptive-3DLUT and xiaom233/HDRTVNet-plus. This is a device-specific development package, not a general standalone installer.

## Install and restore

0.4.2 ships the models inside the ZIP and adds a button: the panel section «Рантайм анализа» shows
whether analysis can run and, if not, installs everything with one press — it copies the bundled
models into `~/AsusNPU` and downloads the AMD Ryzen AI runtime bundle (1.5 GB, release `runtime-v1`,
verified against its sha256) and unpacks it. Only the system packages
(`linux-firmware-amd xrt xrt-plugin-amdxdna`) still need root.

Without the button the same thing is doable by hand; full procedure, including a from-scratch
restore after reinstalling the OS: [INSTALL.md](INSTALL.md). Check a machine with
`scripts/check-runtime.sh`.
