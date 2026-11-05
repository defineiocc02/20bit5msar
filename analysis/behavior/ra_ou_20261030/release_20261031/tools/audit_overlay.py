#!/usr/bin/env python3
"""Read-only baseline audit of a single host. Writes nothing."""
import argparse
import hashlib
import json
import os
import stat
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent

def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()

def safe(root,rel,allow_missing=False):
    rel=Path(rel)
    if rel.is_absolute() or '..' in rel.parts or not rel.parts:
        raise ValueError('Unsafe relative path: '+str(rel))
    p=root
    for i,part in enumerate(rel.parts):
        p=p/part
        try:s=p.lstat()
        except FileNotFoundError:
            if allow_missing and i==len(rel.parts)-1:return p
            raise
        if stat.S_ISLNK(s.st_mode) or getattr(s,'st_file_attributes',0)&0x400:
            raise ValueError('Symlink/reparse point rejected: '+str(p))
    return p

def audit(root):
    root=Path(root).resolve(strict=True)
    m=json.loads((HERE/'overlay_manifest.json').read_text(encoding='utf8'))
    b=json.loads((HERE/'baseline_manifest.json').read_text(encoding='utf8'))
    if len(b['files'])!=105 or len(m['files'])!=12:raise ValueError('Unexpected manifest count')
    if digest(safe(root,'current/models/SarAdc.slx'))!=m['baseline_model_sha256']:
        raise ValueError('Current model SHA changed')
    if digest(safe(root,'state/applied_config.json'))!=m['baseline_state_sha256']:
        raise ValueError('Applied state SHA changed')
    for row in b['files']:
        p=safe(root,row['path'])
        if not p.is_file() or digest(p)!=row['sha256']:raise ValueError('Baseline source changed: '+row['path'])
    for row in m['files']:
        stage=safe(HERE/'overlay',row['path'])
        if not stage.is_file() or digest(stage)!=row['target_sha256']:raise ValueError('Candidate changed: '+row['path'])
        target=safe(root,row['path'],allow_missing=row['operation']=='add')
        if row['operation']=='replace':
            if not target.is_file() or digest(target)!=row['baseline_sha256']:raise ValueError('Replace target changed: '+row['path'])
        elif row['operation']=='add':
            if os.path.lexists(target):raise ValueError('New target already exists: '+row['path'])
        else:raise ValueError('Unexpected operation')
    return {'status':'read_only_baseline_and_overlay_match','project_root':str(root),
            'model_sha256':m['baseline_model_sha256'],'state_sha256':m['baseline_state_sha256'],
            'baseline_source_count':len(b['files']),'replace_count':8,'add_count':4,
            'overlay_manifest_sha256':digest(HERE/'overlay_manifest.json'),
            'scope':'Disk identity only; no claim about MATLAB loaded model, paths, caches, or remote host.'}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',required=True,type=Path);a=p.parse_args()
    print(json.dumps(audit(a.root),ensure_ascii=False,indent=2))
if __name__=='__main__':
    try:main()
    except Exception as e:
        print(json.dumps({'status':'audit_failed','error':str(e)},ensure_ascii=False),file=sys.stderr);sys.exit(1)
