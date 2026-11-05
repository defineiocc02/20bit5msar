#!/usr/bin/env python3
"""Read-only candidate checks; this does not execute MATLAB or Simulink."""
from pathlib import Path
from zipfile import ZipFile
import csv,hashlib,json,math
r=Path(__file__).resolve().parents[1]
prod=Path('/Users/zhaoyi/Obsidan/项目库产物文件夹/sar20_5_simulink_20261020/analysis/behavior/ni_dither_20261104/production_n8_run')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(prod/'source.zip')=='d8d15f864dc23b44d617899465f6ab5b962beac93a5780a9db616b9aa1da4e1f'
assert sha(r/'current/models/SarAdc.slx')=='48537818b3212e1e4c8231dec433d1fde36d95814cdcce8c529bb2898eb097d3'
assert sha(r/'fixtures/production_pool_i2_n8.mat')=='7ba67f7f579b159be309565547dc5efdc2b9376857eb7b10e251a008c2b944e0'
assert sha(r/'fixtures/d1_codebook_2048.csv')=='284598ca08207dba3332175861c8851deffa18c572141ea3e8a811c61d31e582'
with ZipFile(prod/'source.zip') as z:
 paths=[x for x in z.namelist() if not x.endswith('/')]
 changed=[x for x in paths if hashlib.sha256(z.read(x)).hexdigest()!=sha(r/x)]
expected={'SAR20.m','config/adc_parameters.m','current/src/control/behavior_sar_step.m',
 'current/src/frontend/behavior_frontend_init.m','current/src/frontend/behavior_frontend_stage.m',
 'current/src/frontend/behavior_frontend_step.m','current/src/model/behavior_prepare_configuration.m',
 'current/src/model/behavior_training_configuration.m','current/src/model/behavior_dac_backend_parameters.m',
 'current/src/model/behavior_applied_note.m','current/src/model/behavior_ra_noise_guard.m',
 'current/src/digital/behavior_decode_parameters.m','current/src/digital/behavior_decode.m',
 'current/src/model/behavior_dac_coupling_configuration.m',
 'current/src/physics/behavior_ra_noise_validate_backend.m',
 'current/src/physics/behavior_backend_stage.m','current/src/physics/behavior_backend_step.m'}
assert set(changed)==expected,(set(changed)-expected,expected-set(changed))
assert (r/'current/src/model/behavior_single_guard.m').is_file()
assert hashlib.sha256((r/'current/src/control/behavior_calendar.m').read_bytes()).hexdigest()==hashlib.sha256(ZipFile(prod/'source.zip').read('current/src/control/behavior_calendar.m')).hexdigest()
source=(r/'current/src/frontend/behavior_frontend_stage.m').read_text()
assert "[s,out]=behavior_frontend_step(s,cmd,p);\n                if isfield(p,'single_bank')" in source
assert "[s,~]=behavior_frontend_step(s,cmd,p);" in source
front=(r/'current/src/frontend/behavior_frontend_step.m').read_text()
assert "'singleBank:disconnectedCharge'" in front and "out.v_return_v=nan(size(returned))" in front
init=(r/'current/src/frontend/behavior_frontend_init.m').read_text()
assert 'if p.single_bank,nominal(:,38)=0;end' in init
noise=(r/'current/src/model/behavior_ra_noise_guard.m').read_text()
assert "if isfield(P.front,'single_bank')&&P.front.single_bank,nominal(:,38)=0;end" in noise
model=(r/'current/models/SarAdc.slx')
with ZipFile(model) as z:
 x=z.read('simulink/systems/system_123.xml').decode()
 assert '<P Name="Bias">DecodeP.d1_bias_v</P>' in x
assert "'DecodeP.d1_bias_v'" in (r/'current/src/model/behavior_single_guard.m').read_text()
with (r/'fixtures/d1_codebook_2048.csv').open(newline='') as f:
 rows=list(csv.DictReader(f))
assert len(rows)==2048
for n,row in enumerate(rows):
 c,ff=divmod(n,32);b,k=divmod(c,32)
 levels=([-1]*(31-k)+[0]*k) if b==0 else ([1]*k+[0]*(31-k))
 fine=[2*((ff>>i)&1)-1 for i in range(4,-1,-1)]
 mask=[2*b-1]+levels+fine; weights=[16]+[32]*31+[16,8,4,2,1]
 value=sum(a*b for a,b in zip(weights,mask))
 assert int(row['D1raw'])==n and value==int(row['target_charge_CuVR'])==32*c+2*ff-1039
cu=27e-15
result={'status':'static_checks_pass_only','reference_source_files':len(paths),'modified_source_files':sorted(changed),
 'added_source_files':['current/src/model/behavior_single_guard.m'],'unchanged_calendar':True,
 'model_sha256':sha(model),'model_has_rebound_bias_but_workspace_requires_runtime_check':True,
 'exact_codebook_entries_crosschecked':len(rows),'numeric_assumptions':{'unit_cap_f':cu,'ctop_f':1039*cu,'csignal_f':1024*cu,'cf_f':1024*cu/32},
 'actual_matlab_simulink_execution':'NOT_RUN','scope':'source and independent rational codebook checks; not candidate execution or paper reproduction'}
print(json.dumps(result,indent=2))
