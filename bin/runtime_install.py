"""Fetch and unpack the AMD NPU runtime the plugin needs in ~/AsusNPU.

Runs as the plugin's user, so every extracted file ends up owned by that user.
Prints one JSON object per line on stdout so the panel can show progress:

  {"stage":"status", ...}            what is present / missing
  {"stage":"download","done":N,"total":M}
  {"stage":"extract"}
  {"stage":"link"}
  {"stage":"done","root":"..."}
  {"error":"..."}

CLI: python3 bin/runtime_install.py status|install [--root DIR]
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

RELEASE = 'https://github.com/davnozdu/decky-color-lab/releases/download/runtime-v1/colorlab-runtime.tar.zst'
ASSET = 'colorlab-runtime.tar.zst'
SHA256 = '9abb29d3da5dec247187cd9cef3295c148ca51a4a5c2967a6fa5f74e093490ed'
SIZE = 1545322018
UNPACKED = 2988769280
USER_AGENT = 'decky-color-lab/0.4.2 (+https://github.com/davnozdu/decky-color-lab)'
CHUNK = 1 << 20


def sdk_paths(root):
    sdk = root / 'runtime-1.9/opt/amd/ryzenai/1.9.0'
    return {
        'runtime-1.9': sdk / 'onnxruntime/lib/libonnxruntime.so.1',
        'VitisAI EP': sdk / 'deployment/lib/libonnxruntime_vitisai_ep.so',
        'xrt-1.9': root / 'xrt-1.9/opt/xilinx/xrt/lib',
        'sesr-env': root / 'sesr-env/bin/python',
        'ubuntu-compat': root / 'ubuntu-compat/usr/lib/x86_64-linux-gnu',
    }


def model_paths(root):
    return {
        'color-probe': root / 'color-probe/color-probe',
        'lut-classifier.onnx': root / 'color-probe/lut-classifier.onnx',
        'hdr-probe-tiled': root / 'hdr-probe/hdr-probe-tiled',
        'hdr-lattice.onnx': root / 'hdr-probe/hdr-lattice.onnx',
        'hdr-pointwise.onnx': root / 'hdr-probe/hdr-pointwise.onnx',
        'runtime.sh': root / 'framegen-probe/runtime.sh',
    }


def system_paths():
    return {
        'прошивка NPU (linux-firmware-amd)': Path('/usr/lib/firmware/amdnpu'),
        'модуль amdxdna': Path('/dev/accel/accel0'),
    }


def missing(root):
    """Split what the plugin needs into system packages, runtime bundle and repository models."""
    return {
        'system': [name for name, path in system_paths().items() if not path.exists()],
        'runtime': [name for name, path in sdk_paths(root).items() if not (path.exists() or path.is_symlink())],
        'models': [name for name, path in model_paths(root).items() if not path.exists()],
    }


def emit(obj):
    print(json.dumps(obj), flush=True)


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(8 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def free_bytes(path):
    usage = shutil.disk_usage(path)
    return usage.free


def download(target, progress=True):
    """Resume-aware download; returns when the file is complete and its sha256 matches."""
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_suffix(target.suffix + '.part')
    have = part.stat().st_size if part.exists() else 0
    if have > SIZE:
        part.unlink()
        have = 0
    request = urllib.request.Request(RELEASE, headers={'User-Agent': USER_AGENT})
    if have:
        request.add_header('Range', f'bytes={have}-')
    try:
        response = urllib.request.urlopen(request, timeout=60)
    except Exception as error:
        if have:
            part.unlink()
            return download(target, progress)
        raise RuntimeError(f'Не удалось скачать рантайм: {error}') from error
    if have and response.status != 206:
        # server ignored the Range header: start over
        response.close()
        part.unlink(missing_ok=True)
        return download(target, progress)
    done = have
    if progress:
        emit({'stage': 'download', 'done': done, 'total': SIZE})
    with open(part, 'ab' if have else 'wb') as handle:
        while True:
            block = response.read(CHUNK)
            if not block:
                break
            handle.write(block)
            done += len(block)
            if progress and done % (16 << 20) < CHUNK:
                emit({'stage': 'download', 'done': min(done, SIZE), 'total': SIZE})
    if progress:
        emit({'stage': 'download', 'done': done, 'total': SIZE})
    if done != SIZE:
        raise RuntimeError(f'Размер не совпал: {done} вместо {SIZE}')
    checksum = sha256_of(part)
    if checksum != SHA256:
        part.unlink()
        raise RuntimeError(f'Контрольная сумма не совпала: {checksum[:16]}…')
    part.replace(target)
    return target


def extract(archive, root):
    root.mkdir(parents=True, exist_ok=True)
    if shutil.which('tar') and subprocess.run(['tar', '--zstd', '-tf', str(archive)],
                                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
        command = ['tar', '--zstd', '-xf', str(archive), '-C', str(root)]
    elif shutil.which('zstd'):
        command = ['sh', '-c', f'zstd -dc "$1" | tar -xf - -C "$2"', 'unpack', str(archive), str(root)]
    else:
        raise RuntimeError('Нет ни tar с поддержкой zstd, ни zstd')
    result = subprocess.run(command, capture_output=True)
    if result.returncode:
        raise RuntimeError('Распаковка не удалась: ' + result.stderr.decode(errors='replace')[-200:])


def link(root):
    sdk = root / 'runtime-1.9/opt/amd/ryzenai/1.9.0'
    deployment = sdk / 'deployment/lib'
    if deployment.is_symlink() or deployment.exists():
        return
    deployment.parent.mkdir(parents=True, exist_ok=True)
    os.symlink('../onnxruntime/lib', deployment)


def install_models(source, root):
    """Copy the models/probes shipped inside the plugin package into the runtime root."""
    if source is None or not source.is_dir():
        return
    for name in ('color-probe', 'hdr-probe', 'framegen-probe'):
        if (source / name).is_dir():
            shutil.copytree(source / name, root / name, dirs_exist_ok=True, copy_function=shutil.copy2)
    manifest = source / 'MANIFEST.sha256'
    if manifest.exists():
        shutil.copy2(manifest, root / 'MANIFEST.sha256')
        result = subprocess.run(['sha256sum', '-c', '--quiet', 'MANIFEST.sha256'],
                                cwd=root, capture_output=True)
        if result.returncode:
            raise RuntimeError('Модели не совпали с MANIFEST: ' +
                               result.stdout.decode(errors='replace')[-200:])


def install(root, keep_archive=False, models_from=None):
    state = missing(root)
    if not state['runtime'] and not state['models']:
        emit({'stage': 'done', 'root': str(root), 'note': 'уже установлено'})
        return
    if state['models']:
        emit({'stage': 'models'})
        install_models(models_from, root)
        state = missing(root)
    if state['system']:
        emit({'stage': 'system', 'missing': state['system']})
    need = 0 if not state['runtime'] else SIZE + UNPACKED
    if need and free_bytes(root if root.exists() else root.parent) < need + (2 << 30):
        raise RuntimeError('Недостаточно места: нужно около 5 ГБ свободно')
    if state['runtime']:
        archive = root / ASSET
        if not (archive.exists() and sha256_of(archive) == SHA256):
            download(archive)
        emit({'stage': 'extract'})
        extract(archive, root)
        link(root)
        emit({'stage': 'link'})
        if not keep_archive:
            archive.unlink(missing_ok=True)
    emit({'stage': 'done', 'root': str(root), 'missing': missing(root)})


def main(argv):
    command = argv[1] if len(argv) > 1 else 'status'
    root = Path.home() / 'AsusNPU'
    if '--root' in argv:
        root = Path(argv[argv.index('--root') + 1]).expanduser()
    models_from = None
    if '--models-from' in argv:
        models_from = Path(argv[argv.index('--models-from') + 1]).expanduser()
    try:
        if command == 'status':
            emit({'stage': 'status', 'root': str(root), 'missing': missing(root)})
        elif command == 'install':
            install(root, keep_archive='--keep-archive' in argv, models_from=models_from)
        elif command == 'verify':
            emit({'stage': 'status', 'root': str(root), 'missing': missing(root)})
        else:
            emit({'error': f'Неизвестная команда: {command}'})
            return 2
    except Exception as error:  # noqa: BLE001 - report everything to the panel
        emit({'error': str(error)[:300]})
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
