#!/usr/bin/env python3
"""Create one host's new external, SHA-verified data backup; never edit root.

Draft: not executed against either production host. It copies regular files,
relative paths and empty directories. Platform ACLs/resource forks/xattrs are
not claimed as verified; symlinks and reparse points are rejected.
"""
import argparse
import hashlib
import json
import os
import platform
import shutil
import stat
import sys
from pathlib import Path
from audit_overlay import audit, digest


def entries(root):
    rows=[];dirs=[]
    for part in ('current','config','state'):
        tree=root/part
        if not tree.is_dir():raise ValueError('Missing directory: '+str(tree))
        def fail_walk(error):
            raise error  # never silently omit an unreadable directory
        for directory,subdirs,files in os.walk(tree,followlinks=False,onerror=fail_walk):
            d=Path(directory);st=d.lstat()
            if stat.S_ISLNK(st.st_mode) or getattr(st,'st_file_attributes',0)&0x400:
                raise ValueError('Symlink/reparse directory: '+str(d))
            dirs.append(d.relative_to(root).as_posix())
            for n in subdirs+files:
                p=d/n;s=p.lstat()
                if stat.S_ISLNK(s.st_mode) or getattr(s,'st_file_attributes',0)&0x400:
                    raise ValueError('Symlink/reparse entry: '+str(p))
                if not (stat.S_ISREG(s.st_mode) or stat.S_ISDIR(s.st_mode)):
                    raise ValueError('Unsupported special file: '+str(p))
            for n in files:
                p=d/n;rows.append(p.relative_to(root).as_posix())
    rows.append('SAR20.m')
    latest=root/'runs/latest_behavior_run.json'
    if os.path.lexists(latest):
        st=latest.lstat()
        if not stat.S_ISREG(st.st_mode) or getattr(st,'st_file_attributes',0)&0x400:
            raise ValueError('Latest pointer is not a regular file')
        rows.append('runs/latest_behavior_run.json')
    return sorted(rows),sorted(dirs),latest.exists()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',required=True,type=Path);p.add_argument('--destination',required=True,type=Path)
    p.add_argument('--host-id',required=True,choices=['mac','windows']);a=p.parse_args()
    root=a.root.resolve(strict=True);destination=a.destination.resolve(strict=False)
    if destination==root or root in destination.parents or destination in root.parents:
        raise ValueError('Backup must be outside and non-overlapping with project')
    if os.path.lexists(destination):raise ValueError('Backup destination already exists')
    parent=destination.parent.resolve(strict=True)
    pre=audit(root);files,dirs,latest=entries(root)
    original={n:{'sha256':digest(root/n),'size':(root/n).stat().st_size} for n in files}
    required=sum(v['size'] for v in original.values())
    if shutil.disk_usage(parent).free<required+16*1024*1024:raise ValueError('Insufficient free space')
    destination.mkdir();payload=destination/'payload';payload.mkdir()
    for n in dirs:(payload/n).mkdir(parents=True,exist_ok=True)
    for n in files:
        src=root/n;dst=payload/n;dst.parent.mkdir(parents=True,exist_ok=True)
        if os.path.lexists(dst):raise ValueError('Backup target exists: '+str(dst))
        shutil.copy2(src,dst)
        if digest(dst)!=original[n]['sha256'] or digest(src)!=original[n]['sha256']:
            raise ValueError('Concurrent mutation or copy mismatch: '+n)
    after_files,after_dirs,after_latest=entries(root)
    if (after_files,after_dirs,after_latest)!=(files,dirs,latest):raise ValueError('Inventory changed during copy')
    for n in files:
        if digest(root/n)!=original[n]['sha256'] or digest(payload/n)!=original[n]['sha256']:
            raise ValueError('Final readback mismatch: '+n)
    audit(root)
    receipt={'schema':'sar20-ou-host-backup/v1','status':'data_backup_hash_verified',
        'host_id':a.host_id,'hostname':platform.node(),'os':platform.system(),
        'source_root':str(root),'destination':str(destination),'baseline_audit':pre,
        'latest_pointer_present':latest,'files':original,'directories':dirs,
        'scope':'Regular-file main data/relative paths/empty dirs and SHA only; ACL/xattr/resource-fork fidelity not proven.'}
    out=destination/'backup_receipt.json'
    with out.open('x',encoding='utf8') as f:json.dump(receipt,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    print(json.dumps({'status':receipt['status'],'host_id':a.host_id,'hostname':receipt['hostname'],
        'receipt':str(out),'receipt_sha256':digest(out),'files':len(files),'bytes':required,
        'scope':receipt['scope']},ensure_ascii=False,indent=2))

if __name__=='__main__':
    try:main()
    except Exception as e:
        print(json.dumps({'status':'backup_failed_partial_preserved','error':str(e)},ensure_ascii=False),file=sys.stderr);sys.exit(1)
