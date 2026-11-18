"""Package the plugin as a Decky-installable ZIP and refresh BUILD-MANIFEST.json.

  python3 scripts/package_release.py [--out DIR]

The archive mirrors what Decky Loader expects: a single top-level folder named after
plugin.json's "name", with dist/, main.py, bin/, assets/, defaults/ and — since 0.4.2 —
runtime/ so the panel's install button has the models locally.
"""
import argparse
import datetime
import hashlib
import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INCLUDE = ['LICENSE', 'README.md', 'INSTALL.md', 'main.py', 'package.json', 'package-lock.json',
           'plugin.json', 'dist', 'assets', 'bin', 'backend', 'defaults', 'src', 'runtime']
SKIP_DIRS = {'__pycache__', 'node_modules', '.venv', 'runs', 'npu-run', 'npu-tiled-run',
             'cpu-run', 'npu-dynamic-run', 'npu-vectorized-run', 'npu-aligned-run'}
SKIP_SUFFIX = {'.pyc', '.log'}


def collect(pkg):
    for path in sorted(pkg.rglob('*')):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file() and path.suffix not in SKIP_SUFFIX:
            yield path.relative_to(pkg).as_posix()


def digest(path):
    value = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(8 << 20), b''):
            value.update(block)
    return value.hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', default=str(ROOT.parent))
    args = parser.parse_args(argv)

    plugin_json = json.loads((ROOT / 'plugin.json').read_text())
    version = json.loads((ROOT / 'package.json').read_text())['version']
    name = plugin_json['name']

    with tempfile.TemporaryDirectory() as temp:
        pkg = Path(temp) / name
        pkg.mkdir(parents=True)
        for item in INCLUDE:
            source = ROOT / item
            if not source.exists():
                print(f'skip missing {item}', file=sys.stderr)
                continue
            target = pkg / item
            if source.is_dir():
                shutil.copytree(source, target,
                                ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.log'))
            else:
                shutil.copy2(source, target)

        manifest_path = pkg / 'BUILD-MANIFEST.json'
        manifest = {
            'built_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'version': version,
            'plugin_name': name,
            'sha256': {rel: digest(pkg / rel) for rel in collect(pkg)},
        }
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
        manifest['sha256']['BUILD-MANIFEST.json'] = digest(manifest_path)

        target = Path(args.out).expanduser() / f'Decky-Color-Lab-{version}.zip'
        target.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
            for rel in sorted(collect(pkg)):
                archive.write(pkg / rel, f'{name}/{rel}')

    print(json.dumps({'zip': str(target), 'version': version,
                      'files': len(manifest['sha256']),
                      'bytes': target.stat().st_size,
                      'manifest_sha256': digest(target)}, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
