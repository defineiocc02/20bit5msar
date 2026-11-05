#!/usr/bin/env python3
"""Guarded file-level installer/rollback for the SAR20 RA OU release.

Deterministic, stdlib-only. Never touches MATLAB. Every step is SHA-256 gated;
backups are written to a NEW external directory, read back and re-hashed before
any production byte is written.

Subcommands:
  verify   --root --baseline --manifest
  backup   --root --baseline --out
  install  --root --manifest --release --out
  rollback --root --baseline --out

Path conventions: project-relative POSIX paths ('current/src/...').
"""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

SCOPE_DIRS = ('current', 'config', 'state')
SCOPE_ROOT_FILES = ('SAR20.m',)


def sha_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def obj_files(root, parts):
    rows = []
    for part in parts:
        tree = Path(root) / part
        if not tree.is_dir():
            raise SystemExit('missing directory: %s' % tree)
        for dirpath, dirnames, filenames in os.walk(tree):
            dirnames.sort()
            for name in sorted(filenames):
                p = Path(dirpath) / name
                rel = p.relative_to(root).as_posix()
                if p.is_symlink() or not p.is_file():
                    raise SystemExit('refusing non-regular file: %s' % p)
                rows.append({'path': rel, 'sha256': sha_file(p)})
    for name in SCOPE_ROOT_FILES:
        p = Path(root) / name
        if p.is_file():
            if p.is_symlink():
                raise SystemExit('refusing symlink: %s' % p)
            rows.append({'path': name, 'sha256': sha_file(p)})
    return sorted(rows, key=lambda r: r['path'])


def require(cond, message):
    if not cond:
        raise SystemExit('FAILED: ' + message)


def check_baseline(root, baseline, manifest):
    rows = obj_files(root, SCOPE_DIRS)
    by_path = {r['path']: r['sha256'] for r in rows}
    for row in baseline['files']:
        require(row['path'] in by_path, 'baseline file missing: %s' % row['path'])
        require(by_path[row['path']] == row['sha256'], 'baseline file changed: %s' % row['path'])
    require(sha_file(Path(root) / 'current' / 'models' / 'SarAdc.slx') == manifest['baseline_model_sha256'],
            'main model differs from frozen baseline')
    require(sha_file(Path(root) / 'state' / 'applied_config.json') == manifest['baseline_state_sha256'],
            'applied state differs from frozen baseline')
    for row in manifest['files']:
        if row['operation'] == 'replace':
            target = Path(root) / row['path']
            require(target.is_file(), 'replace target missing: %s' % row['path'])
            require(sha_file(target) == row['baseline_sha256'],
                    'replace target differs from manifest baseline: %s' % row['path'])
        elif row['operation'] == 'add':
            require(not os.path.lexists(Path(root) / row['path']),
                    'add target already exists: %s' % row['path'])
        else:
            raise SystemExit('unexpected operation: %s' % row['operation'])
    return {'status': 'baseline_verified', 'files': len(rows), 'model_sha256': manifest['baseline_model_sha256'],
            'state_sha256': manifest['baseline_state_sha256']}


def cmd_verify(args):
    baseline = load_json(args.baseline)
    manifest = load_json(args.manifest)
    print(json.dumps(check_baseline(args.root, baseline, manifest), ensure_ascii=False, indent=2))


def cmd_backup(args):
    root = Path(args.root)
    out = Path(args.out)
    require(not out.exists(), 'backup destination must be new: %s' % out)
    baseline = load_json(args.baseline)
    manifest = load_json(args.manifest)
    before = check_baseline(root, baseline, manifest)
    out.mkdir(parents=True)
    rows = obj_files(root, SCOPE_DIRS)
    for row in rows:
        src = root / row['path']
        dst = out / 'files' / row['path']
        dst.parent.mkdir(parents=True, exist_ok=True)
        with open(src, 'rb') as fi, open(dst, 'wb') as fo:
            for block in iter(lambda: fi.read(1 << 20), b''):
                fo.write(block)
    # Empty directories are part of the layout contract.
    empties = []
    for part in SCOPE_DIRS:
        for dirpath, dirnames, filenames in os.walk(root / part):
            if not dirnames and not filenames:
                empties.append(Path(dirpath).relative_to(root).as_posix())
    record = {'schema': 'sar20-ou-backup/v1', 'root': str(root), 'files': rows,
              'empty_dirs': sorted(empties), 'baseline_check': before}
    (out / 'BACKUP.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n',
                                     encoding='utf-8')
    # Read back and re-hash every copied file.
    for row in rows:
        dst = out / 'files' / row['path']
        require(dst.is_file() and sha_file(dst) == row['sha256'],
                'backup readback differs: %s' % row['path'])
    receipt = {'status': 'backup_verified', 'files': len(rows), 'dest': str(out),
               'backup_manifest_sha256': sha_file(out / 'BACKUP.json')}
    (out / 'BACKUP_RECEIPT.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n',
                                             encoding='utf-8')
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


def cmd_install(args):
    root = Path(args.root)
    release = Path(args.release)
    out = Path(args.out)
    manifest = load_json(args.manifest)
    require((out / 'BACKUP.json').is_file(), 'missing verified backup in %s' % out)
    backup = load_json(out / 'BACKUP.json')
    for row in backup['files']:
        p = out / 'files' / row['path']
        require(p.is_file() and sha_file(p) == row['sha256'], 'backup file invalid: %s' % row['path'])
    require(sha_file(out / 'BACKUP.json') == load_json(out / 'BACKUP_RECEIPT.json')['backup_manifest_sha256'],
            'backup manifest hash differs from its receipt')
    # Pre-install identity.
    baseline = load_json(Path(args.baseline)) if args.baseline else None
    if baseline is not None:
        check_baseline(root, baseline, manifest)
    installed = []
    for row in manifest['files']:
        src = release / 'files' / row['path']
        require(src.is_file(), 'release file missing: %s' % row['path'])
        require(sha_file(src) == row['target_sha256'], 'release file differs: %s' % row['path'])
        dst = root / row['path']
        dst.parent.mkdir(parents=True, exist_ok=True)
        tmp = dst.with_name(dst.name + '.sar20tmp')
        with open(src, 'rb') as fi, open(tmp, 'wb') as fo:
            for block in iter(lambda: fi.read(1 << 20), b''):
                fo.write(block)
        os.replace(tmp, dst)
        require(sha_file(dst) == row['target_sha256'], 'installed file differs: %s' % row['path'])
        installed.append(row['path'])
    # Post-install: every manifest entry matches, and untouched baseline files still match.
    replaced = {r['path'] for r in manifest['files']}
    base = load_json(args.baseline) if args.baseline else None
    if base is not None:
        for row in base['files']:
            if row['path'] in replaced:
                continue
            require(sha_file(root / row['path']) == row['sha256'],
                    'untouched baseline file changed: %s' % row['path'])
    for row in manifest['files']:
        require(sha_file(root / row['path']) == row['target_sha256'],
                'post-install hash differs: %s' % row['path'])
    receipt = {'schema': 'sar20-ou-install/v1', 'status': 'installed_pending_matlab_smoke',
               'root': str(root), 'release_manifest_sha256': sha_file(Path(args.manifest)),
               'installed': installed, 'count': len(installed),
               'backup_manifest_sha256': sha_file(out / 'BACKUP.json')}
    (out / 'INSTALL_RECEIPT.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n',
                                              encoding='utf-8')
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


def cmd_rollback(args):
    root = Path(args.root)
    out = Path(args.out)
    baseline = load_json(args.baseline)
    manifest = load_json(args.manifest) if args.manifest else None
    require((out / 'BACKUP.json').is_file(), 'missing backup in %s' % out)
    require(manifest is not None, 'rollback needs --manifest for baseline identity')
    backup = load_json(out / 'BACKUP.json')
    for row in backup['files']:
        p = out / 'files' / row['path']
        require(p.is_file() and sha_file(p) == row['sha256'], 'backup file invalid: %s' % row['path'])
    removed = []
    if manifest is not None:
        for row in manifest['files']:
            if row['operation'] != 'add':
                continue
            target = root / row['path']
            if os.path.lexists(target):
                require(target.is_file() and sha_file(target) == row['target_sha256'],
                        'refusing to delete changed added file: %s' % row['path'])
                target.unlink()
                removed.append(row['path'])
    restored = []
    for row in backup['files']:
        dst = root / row['path']
        dst.parent.mkdir(parents=True, exist_ok=True)
        src = out / 'files' / row['path']
        tmp = dst.with_name(dst.name + '.sar20tmp')
        with open(src, 'rb') as fi, open(tmp, 'wb') as fo:
            for block in iter(lambda: fi.read(1 << 20), b''):
                fo.write(block)
        os.replace(tmp, dst)
        require(sha_file(dst) == row['sha256'], 'restored file differs: %s' % row['path'])
        restored.append(row['path'])
    for d in backup.get('empty_dirs', []):
        p = root / d
        if not p.exists():
            p.mkdir(parents=True, exist_ok=True)
    check_baseline(root, baseline, manifest)
    receipt = {'schema': 'sar20-ou-rollback/v1', 'status': 'rolled_back_to_baseline',
               'root': str(root), 'removed_added': removed, 'restored_files': len(restored),
               'model_sha256': sha_file(root / 'current' / 'models' / 'SarAdc.slx'),
               'state_sha256': sha_file(root / 'state' / 'applied_config.json')}
    (out / 'ROLLBACK_RECEIPT.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n',
                                               encoding='utf-8')
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='command', required=True)
    for name in ('verify', 'backup', 'install', 'rollback'):
        p = sub.add_parser(name)
        p.add_argument('--root', required=True, type=Path)
        p.add_argument('--manifest', type=Path)
        p.add_argument('--baseline', type=Path)
        p.add_argument('--release', type=Path)
        p.add_argument('--out', type=Path)
    args = ap.parse_args()
    if args.command == 'verify':
        require(args.baseline and args.manifest, 'verify needs --baseline and --manifest')
        cmd_verify(args)
    elif args.command == 'backup':
        require(args.baseline and args.manifest and args.out, 'backup needs --baseline --manifest --out')
        cmd_backup(args)
    elif args.command == 'install':
        require(args.manifest and args.baseline and args.release and args.out,
                'install needs --manifest --baseline --release --out')
        cmd_install(args)
    else:
        require(args.baseline and args.manifest and args.out,
                'rollback needs --baseline --manifest --out')
        cmd_rollback(args)


if __name__ == '__main__':
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 - report exact failure, no silent fallback
        print('ERROR: %s: %s' % (type(exc).__name__, exc), file=sys.stderr)
        sys.exit(2)
