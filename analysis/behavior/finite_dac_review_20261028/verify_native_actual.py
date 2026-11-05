"""Read actual saved native endpoints; Decimal90 ODE solution, no ADC simulation."""
from pathlib import Path
from decimal import Decimal,localcontext
import sys,json,hashlib,struct,math
import numpy as np,h5py
from scipy.io import loadmat
P=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(P/'analysis'));from mat_reader import variable
run=P/'runs/az_probe_20261027T020421Z'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def bits(a,b):
 a=np.asarray(a,dtype=np.float64);b=np.asarray(b,dtype=np.float64);return a.shape==b.shape and a.tobytes()==b.tobytes()
def hx(x):return struct.pack('>d',float(x)).hex()
def D(x):return Decimal.from_float(float(x))
with h5py.File(run/'actual_base_parameters.mat') as f:base={'backend':{'ra':{k:float(f['P/backend/ra/'+k][()][0,0]) for k in ['Cf_f','A0','vos_input_v']}},'epoch':float(f['P/epoch'][()][0,0])}
receipt=json.loads((run/'receipt.json').read_text());rc=receipt['native']['independent_formula_cases']
rows=[]
for path in sorted((run/'native_detail').glob('partial_case_*.mat')):
 p=loadmat(path,simplify_cells=True)['partial'];one=p['one'];k=int(p['case_index']);old=p['old_backend_state48'];new=p['actual_backend_state48'];fe=p['old_FE_state353'];endfe=p['actual_FE_state353'];f=p['forcing'];obs=p['obs8'];end=p['actual_FE_endpoint']
 h=float(new[0]-old[0]);R=float(p['tau_RA_s']);tau=float(p['tau_DAC_s']);Cf=base['backend']['ra']['Cf_f'];NG=1+old[12]/Cf;A0=base['backend']['ra']['A0'];F=1. if math.isinf(A0) else A0/(A0+NG)
 assert h==f['dt_s']==one['dt_s'];assert hx(h).upper()==one['dt_uint64_hex'];assert hx(R).upper()==one['tau_RA_uint64_hex'];assert hx(tau).upper()==one['tau_DAC_uint64_hex']
 assert bits(new[1],one['actual_vx_V']) and bits(obs[0],new[1]);assert bits(f['q_endpoint_c'],end['qres_c']);assert bits(obs[3],end['qres_c']/Cf);assert bits(obs[2],(obs[0]-end['qres_c']/Cf)/NG)
 ids=np.asarray(f['physical_ids'],dtype=int)-1;B=fe[24:78].reshape((18,3),order='F');T=fe[78:132].reshape((18,3),order='F');deltas=np.sum(B[ids]-T[ids],axis=1)
 assert np.array_equal(deltas,f['delta_q_c']);assert np.all(fe[6:24][ids]==2);assert np.all(fe[204:222][ids]==4);assert np.all(fe[222:240][ids]==base['epoch']);assert old[0]==fe[0] and new[0]==endfe[0]
 for key in ['actual_vx_V','q0_C','q_endpoint_C','delta_sum_C','actual_vtop_V','actual_target_V','dt_s']:
  assert bits(one[key],rc[k-1][key]),(k,key)
 with localcontext() as c:
  c.prec=90;x=D(h)/D(R);er=(-x).exp()
  if math.isinf(tau):J=Decimal(0)
  elif tau==R:J=1-(1+x)*er
  else:
   t=D(tau);J=1-er-t/(t-D(R))*((-D(h)/t).exp()-er)
  # Mathematical interval uses actual binary64 retained inputs, not candidate H/J.
  v=D(old[1])*er+D(F)*(D(f['q0_c'])/D(Cf)+D(NG)*D(base['backend']['ra']['vos_input_v']))*(1-er)+D(F)*sum(D(v) for v in f['delta_q_c'])/D(Cf)*J
  rows.append({'case':p['case_name'],'h_hex':hx(h),'R_hex':hx(R),'D_hex':hx(tau),'J_Decimal90':str(J),'VX_Decimal90':str(v),'actual_VX_V':float(new[1]),'actual_VX_minus_Decimal90_V':float(new[1])-float(v),'actual_J_from_VX':one['actual_ramp_J_from_VX'],'actual_J_minus_Decimal90':one['actual_ramp_J_from_VX']-float(J),'actual_minus_native_expm_V':one['vx_formula_delta_V'],'old_FE_sha256':hashlib.sha256(fe.tobytes()).hexdigest(),'partial_sha256':sha(path),'endpoint_q_target_vtop_uint64':True})
near=[v for v in rows if 'ulp' in v['case']];eq=next(v for v in rows if v['case']=='equal_RA_DAC_poles')
# Full actual saved P identity, memoized by HDF5 node so repeated aliases do not expand.
prior=P/'runs/behavior_f346bc5e-867f-48be-b3ac-085fa7e1bcfa/parameters.mat'
def fingerprint(file,node,memo):
 key=h5py.h5o.get_info(node.id).addr
 if key in memo:return memo[key]
 cls=node.attrs.get('MATLAB_class',b'');cls=cls.decode() if isinstance(cls,bytes) else str(cls)
 if isinstance(node,h5py.Group):payload=('group',cls,tuple((k,fingerprint(file,node[k],memo)) for k in sorted(node.keys())))
 else:
  a=node[()]
  if h5py.check_dtype(ref=node.dtype) is not None:payload=('refs',cls,a.shape,tuple(None if not r else fingerprint(file,file[r],memo) for r in a.reshape(-1)))
  else:payload=('data',cls,a.shape,a.dtype.str,hashlib.sha256(a.tobytes()).hexdigest())
 v=hashlib.sha256(repr(payload).encode()).hexdigest();memo[key]=v;return v
with h5py.File(prior) as f,h5py.File(run/'actual_base_parameters.mat') as g:
 fm={};gm={};before=fingerprint(f,f['P'],fm);actual=fingerprint(g,g['P'],gm)
 assert before==actual,'Full saved P differs from the identified prior off run'
 config={'prior_run':str(prior.parent),'prior_mat_sha256':sha(prior),'full_P_semantic_class_shape_data_sha256':actual,'full_P_class_shape_rawbits_same':True,'fingerprinted_unique_HDF_nodes':[len(fm),len(gm)],'boundary':'This confirms saved input P identity. Same loaded P/model/RNG after native is the actual job assertion, not a separately saved after-snapshot.'}
report={'schema':'actual-native-finite-DAC-independent/v1','run':str(run),'files_sha256':{n:sha(run/n) for n in ['actual_base_parameters.mat','native_results.mat','receipt.json','candidate.zip']},'source_sha256':{str(p.relative_to(run/'candidate')):sha(p) for p in [run/'candidate/src/physics/behavior_backend_step.m',run/'candidate/validation/validate_finite_dac_native.m']},'actual_partial_count':len(rows),'actual_partials_receipt_selected_fields_uint64_equal':True,'saved_endpoint_q_target_vtop_uint64_equal':True,'max_actual_minus_Decimal90_V':max(abs(v['actual_VX_minus_Decimal90_V']) for v in rows),'max_actual_J_minus_Decimal90':max(abs(v['actual_J_minus_Decimal90']) for v in rows),'max_actual_minus_native_expm_V':max(abs(v['actual_minus_native_expm_V']) for v in rows),'max_neighbor_J_change_from_equal':max(abs(v['actual_J_from_VX']-eq['actual_J_from_VX']) for v in near),'cases':rows,'old_off_allzero_gate':'Actual native assertion compares full48 state/obs8 uint64 against frozen old backend, 96 calls per flag; closed-path tolerance remains absent. Raw intermediate96 calls were not persisted, so this is native assertion evidence, not independently replayed bit histories.','defaultP_identity':config,'no_new_tolerance':True,'ADC_simulation_run':False,'script_sha256':sha(Path(__file__))}
model=P/'current/models/SarAdc.slx';mh=sha(model)
report['current_model_readback']={'path':str(model),'sha256':mh,'equals_native_bound_model':mh==receipt['model_sha256'],'boundary':'Read-only local current model hash at review time; no native after-file copy exists.'}
parts=[]
for rel in ['src/physics/behavior_backend_step.m','baseline/behavior_backend_step.m']:
 text=(run/'candidate'/rel).read_text();a=text.index('function k=exponential_response(');b=text.index('\nfunction ',a+1);parts.append(text[a:b])
assert parts[0]==parts[1]
report['legacy_AZ_H_source_exact_same_as_frozen_baseline']={'same':True,'function_text_sha256':hashlib.sha256(parts[0].encode()).hexdigest(),'boundary':'Near-pole legacy H numerical corner remains unverified; existing measured AZ evidence is not changed.'}
print(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False))
