#!/usr/bin/env python3
"""Stage 8 replacements + 4 additions in a NEW external folder; no project edits."""
import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from audit_overlay import audit,digest


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',required=True,type=Path)
    ap.add_argument('--destination',required=True,type=Path)
    a=ap.parse_args();root=a.root.resolve(strict=True);dest=a.destination.resolve(strict=False)
    if dest==root or root in dest.parents or dest in root.parents or os.path.lexists(a.destination):
        raise ValueError('Stage destination must be new and non-overlapping with project')
    dest.parent.resolve(strict=True)
    pre=audit(root);here=Path(__file__).resolve().parent
    M=json.loads((here/'overlay_manifest.json').read_text(encoding='utf8'))
    dest.mkdir();payload=dest/'overlay';payload.mkdir()
    for row in M['files']:
        name=row['path'];src=here/'overlay'/name;dst=payload/name;dst.parent.mkdir(parents=True,exist_ok=True)
        if os.path.lexists(dst):raise ValueError('Unexpected existing stage path: '+name)
        shutil.copy2(src,dst)
        if digest(src)!=row['target_sha256'] or digest(dst)!=row['target_sha256']:
            raise ValueError('Candidate copy mismatch: '+name)
    after=audit(root)
    if pre!=after:raise ValueError('Project baseline changed during staging')
    receipt={'schema':'sar20-ou-source-stage/v1','status':'stage_only_verified_no_install',
        'baseline':pre,'files':M['files'],'scope':'No project write; install/rollback remain separate reviewed operations.'}
    p=dest/'stage_receipt.json'
    with p.open('x',encoding='utf8') as f:json.dump(receipt,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    print(json.dumps({'status':receipt['status'],'destination':str(dest),
        'receipt_sha256':digest(p),'files':len(M['files'])},ensure_ascii=False,indent=2))
if __name__=='__main__':
    try:main()
    except Exception as e:
        print(json.dumps({'status':'stage_failed_partial_preserved','error':str(e)},ensure_ascii=False),file=sys.stderr);sys.exit(1)
