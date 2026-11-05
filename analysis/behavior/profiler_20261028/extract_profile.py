#!/usr/bin/env python3
"""Read 122805 profile MAT/source evidence. Never calls MATLAB or writes project."""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
import hashlib, json, zipfile
import h5py

root=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path('/Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020')
d=root/'runs/az_probe_20261028T122805Z/validation'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
expected={'profile_before.mat':'3759b06419384439f5c75d5be15fdae9fab5cec278b051cfd40b4d5102ed118d',
          'profile_after.mat':'1b04ece02a31ce7d45bcfdc8d03b940a2e3a5de2ff8b7e74ab8b3c18c7f214a2',
          'profile_delta.mat':'988563421c074d42231037b9f282093058e49aae2b3fb33d47734da61912fd80'}
for k,v in expected.items(): assert sha(d/k)==v,k
receipt=json.loads((d/'receipt.json').read_text());assert receipt['status']=='profiled_scratch_N256_complete_pending_independent_review'
manifest={r['path'].replace('\\','/'):r['sha256'] for r in receipt['project_source_manifest']}
files=['current/src/physics/behavior_backend_step.m','current/src/physics/sar20_cdac2_network.m']
with zipfile.ZipFile(root/'runs/behavior_47c22b65-fdff-402b-b315-ea0599df6891/source.zip') as z:
 for name in files:
  assert sha(root/name)==manifest[name]==hashlib.sha256(z.read(name)).hexdigest(),name
with h5py.File(d/'profile_before.mat') as f:
 obj=f['beforeInfo/FunctionTable'];assert obj.attrs.get('MATLAB_empty')==1
before_empty=True
with h5py.File(d/'profile_after.mat') as f:
 table=f['afterInfo/FunctionTable'];n=table['FunctionName'].shape[1]
 def obj(key,i): return f[table[key][0,i]]
 def txt(item): return ''.join(chr(int(v)) for v in item[()].flatten())
 names=[txt(obj('FunctionName',i)) for i in range(n)]
 def scalars(group,key):
  a=group[key][()]
  return [float(f[ref][()].item()) for ref in a.flatten()] if a.dtype.kind=='O' else [float(v) for v in a.flatten()]
 result=[]
 for wanted in ['behavior_backend_step>validate_inputs','behavior_backend_step','behavior_backend_step>observe',
                'behavior_backend_step>switch_networks','sar20_cdac2_network']:
  assert names.count(wanted)==1,wanted;i=names.index(wanted)
  code=files[1] if wanted=='sar20_cdac2_network' else files[0];lines=(root/code).read_text().splitlines()
  executed=obj('ExecutedLines',i)[()];assert executed.shape[0]==3
  rows=[{'line':int(a),'executions':int(b),'total_s':float(c),'text':lines[int(a)-1].strip()}
        for a,b,c in zip(*executed)]
  children=obj('Children',i)
  cs=[{'name':names[int(idx)-1],'calls':int(calls),'inclusive_s':float(sec)} for idx,calls,sec in
      zip(scalars(children,'Index'),scalars(children,'NumCalls'),scalars(children,'TotalTime'))]
  partial=bool(obj('PartialData',i)[()].item());assert not partial
  result.append({'name':wanted,'file':code,'sha256':manifest[code],'calls':int(obj('NumCalls',i)[()].item()),
      'inclusive_s':float(obj('TotalTime',i)[()].item()),'partial_data':partial,
      'executed_lines':sorted(rows,key=lambda r:r['total_s'],reverse=True),'children':cs})
 out={'schema':'sar20-122805-profile-lines-readonly/v1','before_function_table_empty':before_empty,
      'profiler_timer':receipt['profiler_status_before']['Timer'],'history_shape':list(f['afterInfo/FunctionHistory'].shape),
      'profiled_sim_wall_s':receipt['sim_profiled_wall_s'], 'archive_hashes':expected,
      'scope':'Single profiled N256; line total may include child functions; no exclusive-time or speedup claim.',
      'functions':result}
 print(json.dumps(out,ensure_ascii=False,indent=2))
