#!/usr/bin/env python3
"""Read archived local zero endpoints and model parameters only; no simulations."""
import sys,json,math,hashlib,zipfile
from pathlib import Path
import h5py,numpy as np
P=Path('/Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020')
sys.path.insert(0,str(P/'analysis/behavior/finite_dac_review_20261028'))
from verify_as_run import read_logs,read_calendar,val,at,fingerprint,sha,need
Z=P/'runs/az_probe_20261028T112407Z/zero_result'; B=P/'runs/az_probe_20261028T110315Z/static_result';rec=json.loads((Z/'receipt.json').read_text())
need(rec['status']=='actual_multicode_jump_window_no_DNL','Incorrect terminal receipt')
for path,expected in [(Z/'point_001/P.mat',rec['points'][0]['P_mat_sha256']),(Z/'point_001/signals.mat',rec['points'][0]['signals_sha256']),(Z/'Pzero_reconstructed.mat',rec['reused_anchors']['zero']['Pzero_reconstructed_sha256']),(B/'preflight_capped_simout.mat',rec['reused_anchors']['zero']['capped_simout_sha256']),(Z/'SarAdc_factory.slx',rec['model_sha256']),(Z/'source_manifest.json',rec['source_manifest_sha256']),(Z/'source.zip',rec['source_zip_sha256'])]:
 need(sha(path)==expected,'Source hash mismatch: '+str(path))
manifest=json.loads((Z/'source_manifest.json').read_text())['files']; pins={x['path'].replace('\\','/'):x['sha256'] for x in manifest}
with zipfile.ZipFile(Z/'source.zip') as z:
 need(set(z.namelist())==set(pins),'Source ZIP file list differs')
 for k,h in pins.items():need(hashlib.sha256(z.read(k)).hexdigest()==h,'Archive source mismatch '+k)

def signal_struct(path):
 with h5py.File(path,'r') as h:
  seq=[h[r] for r in h['#subsystem#/MCOS'][()].ravel()];s=h['signals'];names=[n for _,n in sorted((int(s[n][()].ravel()[4]),n) for n in s)];found=[]
  for i,d in enumerate(seq):
   if i<11 or not isinstance(d,h5py.Dataset) or d.dtype.kind not in 'fiu' or len(d.shape)<2:continue
   ns,t=seq[i-11],seq[i-9]
   if not(isinstance(ns,h5py.Dataset) and ns.dtype==np.dtype('float64') and ns.shape==(1,1) and isinstance(t,h5py.Dataset) and t.dtype==np.dtype('float64')):continue
   n=int(ns[()].item())
   if n>0 and t.shape==(1,n) and (n==1 or d.shape[-1]==n):found.append({'time':t[()].T[:,0],'data':d[()].reshape((-1,n)).T})
  need(len(names)==len(found)==9,'Unexpected nine-series MAT layout')
  return dict(zip(names,found))

def bits(a,b):
 a=np.asarray(a);b=np.asarray(b);return a.shape==b.shape and a.dtype==b.dtype and a.tobytes()==b.tobytes()

negp=Z/'point_001/P.mat'; zeroP=Z/'Pzero_reconstructed.mat'
with h5py.File(negp) as f,h5py.File(zeroP) as g:
 a={};b={};changed=[]
 def diff(x,y,path):
  if fingerprint(f,x,a)==fingerprint(g,y,b):return
  if isinstance(x,h5py.Group) and isinstance(y,h5py.Group):
   for k in sorted(set(x)|set(y)):
    if k not in x or k not in y:changed.append(path+'/'+k)
    else:diff(x[k],y[k],path+'/'+k)
  else:changed.append(path)
 diff(f['P'],g['Pzero'],'P');need(set(changed)=={'P/input/offset_v','P/front/input/offset_v','P/xFE0'},'Unexpected P differences')
 times,groups,_=read_calendar(f);Vref=float(val(f,'P/front/vref_v'));Cf=float(val(f,'P/backend/ra/Cf_f'));A=float(val(f,'P/backend/ra/A0'));UGB=float(val(f,'P/backend/ra/UGB_hz'));gain=float(val(f,'P/digital/ra_gain'));G=np.asarray(val(f,'P/front/group_C_f'));plan=np.asarray(val(f,'P/front/plan')).astype(int);cs=float(G[plan[4]-1,0].sum());Ctop=float(G[plan[4]-1,:].sum())+float(np.asarray(val(f,'P/front/Cp_f')).ravel()[plan[4]-1].sum());NG=1+Ctop/Cf;F=A/(A+NG);tau=NG/(2*math.pi*UGB)
 weights=np.asarray(val(f,'P/digital/d2_weights_ra_v')).ravel();off=float(val(f,'P/digital/d2_offset_ra_v'));step=float(val(f,'P/digital/tracking_step_ra_v'));fsr=float(val(f,'P/digital/fsr_diff_v'))
 need(A==10000 and gain==32 and all(np.asarray(val(f,'P/front/tau_dac_s')).ravel()==0) and val(f,'P/backend/ni/cinc_kick')==1 and val(f,'P/backend/ni/cap_mismatch')==0 and val(f,'P/backend/ct/replica_enabled')==1 and val(f,'P/backend/ra/vos_input_v')==0 and val(f,'P/backend/az/mode')=='off','Unexpected physical scenario')
 ctpath='P/backend/ct/net_nominal/'; net={k:np.asarray(val(f,ctpath+k)) for k in ['main_f','sub_f','track_f','cinc_f','bridge_f','dummy_f','parasitic_main_f','parasitic_sub_f']};ctV=float(val(f,'P/backend/ct/reference_v'));qb=np.asarray(val(f,'P/backend/ct/initial_main_qb_c')).ravel();need(np.all(qb==0),'CT floating charge is not zero')

def ct_vy(vx,reset,d2,dt,tracking):
 bit=np.array([(d2>>n)&1 for n in range(11,-1,-1)]);s=2*bit-1;tbit=np.array([(dt>>n)&1 for n in range(7,0,-1)]);ts=(2*tbit-1) if tracking else np.zeros(7)
 nodes=[];alpha=[]
 for side in range(2):
  cs0=float(net['cinc_f'].ravel()[side]);cb=float(net['bridge_f'].ravel()[side]);cm=net['main_f'][side];cl=net['sub_f'][side];ct=net['track_f'][side];a=cs0+cm.sum()+cb+float(net['parasitic_main_f'].ravel()[side]);b=cl.sum()+ct.sum()+float(net['dummy_f'].ravel()[side])+cb+float(net['parasitic_sub_f'].ravel()[side]);M=np.array([[a,-cb],[-cb,b]]);pol=1 if side==0 else -1;qin=np.array([cs0*pol*(vx-reset)/2,0]);qdac=-pol*ctV/2*np.array([cm@s[:len(cm)],cl@s[len(cm):]]);qt=-pol*ctV/2*np.array([0,ct@ts]);node=np.linalg.solve(M,qin+qdac+qt+np.array([-cb*qb[side]/b,qb[side]]));nodes.append(node);alpha.append(np.linalg.solve(M,np.array([cs0,0]))[0])
 return float(nodes[0][0]-nodes[1][0]),float(np.mean(alpha))

logs={'negative':signal_struct(Z/'point_001/signals.mat'),'zero':read_logs(B/'preflight_capped_simout.mat')};out={}
for name,L in logs.items():
 t=L['event_log']['time'];e=L['event_log']['data'];need(e.shape==(240,2),'Wrong event count')
 need(np.array_equal(e[:,0],np.repeat(np.arange(5),48)) and np.array_equal(e[:,1],np.tile(np.arange(1,49),5)),'Event groups differ')
 need(bits(t,np.array([i*2e-7+x for i in range(5) for x in times])),'Event times differ')
 for k in ['raw_log','ready_log','record_log','record_ready_log','code_log','front_log','control_log','back_log']:need(bits(t,L[k]['time']),'Logger time axis differs')
 ready=L['ready_log']['data'][:,0];need(bits(ready,L['record_ready_log']['data'][:,0]),'Ready mismatch');ix=np.flatnonzero(ready==1);raw=L['raw_log']['data'][ix];need(len(ix)==5 and bits(raw,L['record_log']['data'][ix]) and np.array_equal(raw[:,3],np.arange(5)) and np.all(raw[:,4]==1) and np.all(raw[:,5]==1),'Warmup/record mismatch')
 r=raw[-1];d1,d2,dt=map(int,r[:3]);code=int(L['code_log']['data'][ix[-1],0]);first=4*48
 def row(group):
  i=first+group-1;need(int(e[i,1])==group,'Group index mismatch');return i
 f=L['front_log']['data'];b=L['back_log']['data'];c=L['control_log']['data'];
 # First actual fine decision, the RAstart and first D2 interval endpoints.
 i15=row(3);i31=row(12);i43=row(13);iend=row(37);i85=row(46)
 x0=float(b[i31,0]);q=float(f[i31,2]);xinf=F*q/Cf;pred=xinf+(x0-xinf)*math.exp(-(t[i43]-t[i31])/tau)
 actual=float(b[i43,0]);ct_d2,alpha=ct_vy(float(b[iend,0]),float(b[iend,7]),d2,dt,False);ct_ta,_=ct_vy(float(b[i85,0]),float(b[i85,7]),d2,dt,True)
 coarse,fine=divmod(d1,32);dbit=np.array([(d2>>n)&1 for n in range(11,-1,-1)]);tb=np.array([(dt>>n)&1 for n in range(7,-1,-1)]);stat=int(np.sum(np.arange(8,0,-1)*(2*tb-1)));vdac=(32*coarse+2*fine-1039)*Vref/1024;vbias=-17*Vref/1024;d1v=vdac+vbias;d2ra=float(off+np.sum(weights*dbit));d2v=d2ra/gain;dtv=step*stat/8/gain;voltage=(d1v+d2v)+dtv;unsat=voltage*(2**20/fsr)+2**19;rounded=math.floor(unsat+0.5)
 need(rounded==code and (code,d1,d2,dt)==((524285,1039,3417,42) if name=='negative' else (524289,1040,2374,42)),'Raw-derived code differs')
 out[name]={'raw6':r.tolist(),'code':code,'ready_s':float(t[ix[-1]]),'held_input_V':float(f[ix[-1],0]),'fine_first_15ns':{'vres_V':float(f[i15,1]),'qres_C':float(f[i15,2]),'d1_word_after_compare':int(c[i15,4])},'RA_start_31p25ns':{'qres_C':q,'vres_V':float(f[i31,1]),'target_V':float(b[i31,3]),'vx_V':x0,'ctop_F':float(f[i31,4]),'ng':float(b[i31,4]),'tau_s':float(b[i31,5])},'first_D2_prepare_43p75ns':{'vx_actual_V':actual,'vx_analytic_V':pred,'actual_minus_analytic_V':actual-pred,'vy_actual_V':float(b[i43,1])},'D2_end_73p75ns':{'vx_V':float(b[iend,0]),'vy_V':float(b[iend,1]),'vy_independent_MNA_V':ct_d2,'actual_minus_MNA_V':float(b[iend,1])-ct_d2,'ct_reset_vx_V':float(b[iend,7])},'TA_end_85ns':{'vx_V':float(b[i85,0]),'vy_V':float(b[i85,1]),'vy_independent_MNA_V':ct_ta,'actual_minus_MNA_V':float(b[i85,1])-ct_ta,'ct_reset_vx_V':float(b[i85,7])},'decode':{'coarse':coarse,'fine':fine,'d2_bits':''.join(map(str,dbit)),'dt_bits':''.join(map(str,tb)),'d1_dac_V':vdac,'d1_bias_V':vbias,'d1_V':d1v,'d2_ra_V':d2ra,'d2_input_V':d2v,'dt_statistic':stat,'dt_input_V':dtv,'voltage_V':voltage,'unrounded_code':unsat},'CT_input_gain_alpha':alpha}

neg=out['negative']['decode'];zero=out['zero']['decode'];lsb=fsr/2**20
out['provenance']={'negative_P_sha':sha(negp),'negative_signals_sha':sha(Z/'point_001/signals.mat'),'zero_actual_preflight_simout_sha':sha(B/'preflight_capped_simout.mat'),'zero_P_reconstructed_sha':sha(zeroP),'model_sha':sha(Z/'SarAdc_factory.slx'),'source_manifest_sha':sha(Z/'source_manifest.json'),'archived_sources_checked':len(pins),'P_difference_to_zero_reconstruction':changed,'zero_P_caveat':'Pzero reconstructed from matching factory and pinned 110315 setup; prior zero preflight did not independently save actual P.'}
out['model']={'Cs_F':cs,'Ctop_F':Ctop,'Cf_F':Cf,'noise_gain':NG,'gain_factor':F,'tau_ra_s':tau,'RA_gain':gain,'nominal_lsb_V':lsb,'ct_reference_V':ctV,'CINC_enabled_and_matching_opposite_replica':True}
out['difference_zero_minus_negative']={'input_V':0-(-3.0517578125e-8),'D1_V':zero['d1_V']-neg['d1_V'],'D2_V':zero['d2_input_V']-neg['d2_input_V'],'DT_V':zero['dt_input_V']-neg['dt_input_V'],'decoded_V':zero['voltage_V']-neg['voltage_V'],'code':4}
out['gain_counterfactual']=[{'A0':'Inf' if math.isinf(A) else int(A),'F':1.0 if math.isinf(A) else A/(A+NG),'low_endpoint_fixed_target_gain_deficit_input_V':0.0 if math.isinf(A) else float((out['negative']['RA_start_31p25ns']['target_V']*(1-A/(A+NG)))/gain)} for A in [1e4,2e4,4e4,math.inf]]
out['scope']='Actual two endpoints and independent first RA interval/CT MNA; target/higher-gain values are frozen-Q analytic counterfactual, not simulated. No inference about unobserved intermediate codes.'
Path(__file__).with_name('zero_physics.json').write_text(json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
for k in ['model','negative','zero','difference_zero_minus_negative','gain_counterfactual']: print(k,json.dumps(out[k],ensure_ascii=False))
