#!/usr/bin/env python3
"""Independent read-only gain/TA interpretation of archived simulation outputs."""
import sys,json,math,hashlib,zipfile
from pathlib import Path
import numpy as np,h5py
P=Path('/Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020')
sys.path.insert(0,str(P/'analysis/behavior/finite_dac_review_20261028'))
from verify_as_run import read_logs,read_calendar,val,at,pdiff,need,same,sha
D=P/'runs/az_probe_20261028T113441Z/gain_result';Z=P/'runs/az_probe_20261028T112407Z/zero_result';B=P/'runs/az_probe_20261028T110315Z/static_result';receipt=json.loads((D/'receipt.json').read_text());prior=json.loads((Z/'receipt.json').read_text())
need(receipt['status']=='four_actual_a0_points_complete_review_required' and receipt['stage']=='complete','New receipt is not complete')
need(prior['status']=='actual_multicode_jump_window_no_DNL','Original endpoint receipt is not complete')
for p,h in [(D/'sar20_ra_gain_probe_job.m',receipt['asrun_job_sha256']),(D/'SarAdc_factory.slx',receipt['model_sha256']),(D/'source_manifest.json',receipt['source_manifest_sha256']),(D/'source.zip',receipt['source_zip_sha256']),(Z/'point_001/P.mat',receipt['prior_negative_P_sha256']),(Z/'point_001/signals.mat',receipt['prior_negative_signals_sha256']),(B/'preflight_capped_simout.mat',receipt['prior_zero_simout_sha256'])]:need(sha(p)==h,'Pinned artifact mismatch: '+str(p))
pins={x['path'].replace('\\','/'):x['sha256'] for x in json.loads((D/'source_manifest.json').read_text())['files']}
with zipfile.ZipFile(D/'source.zip') as z:
 need(set(z.namelist())==set(pins),'Source ZIP differs from pinned manifest')
 for k,h in pins.items():need(hashlib.sha256(z.read(k)).hexdigest()==h,'Source mismatch '+k)

def signal_struct(path):
 with h5py.File(path,'r') as h:
  seq=[h[r] for r in h['#subsystem#/MCOS'][()].ravel()];s=h['signals'];names=[n for _,n in sorted((int(s[n][()].ravel()[4]),n) for n in s)];found=[]
  for i,d in enumerate(seq):
   if i<11 or not isinstance(d,h5py.Dataset) or d.dtype.kind not in 'fiu' or len(d.shape)<2:continue
   ns,t=seq[i-11],seq[i-9]
   if not(isinstance(ns,h5py.Dataset) and ns.dtype==np.dtype('float64') and ns.shape==(1,1) and isinstance(t,h5py.Dataset) and t.dtype==np.dtype('float64')):continue
   n=int(ns[()].item())
   if n>0 and t.shape==(1,n) and (n==1 or d.shape[-1]==n):found.append({'time':t[()].T[:,0],'data':d[()].reshape((-1,n)).T})
  need(len(names)==len(found)==9,'Unexpected old nine-series layout');return dict(zip(names,found))

baselineP=Z/'point_001/P.mat';zeroP=Z/'Pzero_reconstructed.mat';need(sha(zeroP)==prior['reused_anchors']['zero']['Pzero_reconstructed_sha256'],'Reconstructed zero P hash differs')
with h5py.File(baselineP) as f:
 times,groups,budget=read_calendar(f);cf=float(val(f,'P/backend/ra/Cf_f'));UGB=float(val(f,'P/backend/ra/UGB_hz'));G=float(val(f,'P/digital/ra_gain'));vref=float(val(f,'P/digital/vref_v'));fsr=float(val(f,'P/digital/fsr_diff_v'));lsb=fsr/2**20;weights=np.asarray(val(f,'P/digital/d2_weights_ra_v')).ravel();off=float(val(f,'P/digital/d2_offset_ra_v'));step=float(val(f,'P/digital/tracking_step_ra_v'))
 need(cf>0 and G==32 and UGB==1.2e9 and lsb==7.8125e-6 and val(f,'P/backend/ni/cinc_kick')==1 and val(f,'P/backend/ni/cap_mismatch')==0 and val(f,'P/backend/ct/replica_enabled')==1 and val(f,'P/backend/az/mode')=='off' and val(f,'P/backend/ra/vos_input_v')==0 and np.all(np.asarray(val(f,'P/front/tau_dac_s')).ravel()==0),'Model profile changed')
 ctpath='P/backend/ct/net_nominal/';net={k:np.asarray(val(f,ctpath+k)) for k in ['main_f','sub_f','track_f','cinc_f','bridge_f','dummy_f','parasitic_main_f','parasitic_sub_f']};vct=float(val(f,'P/backend/ct/reference_v'));qb=np.asarray(val(f,'P/backend/ct/initial_main_qb_c')).ravel();need(np.all(qb==0),'Nonzero initial CT B charge')

# Independent 2-node matrix reconstruction. Input signs are reconstructed
# from actual committed RAW and event order; no internal feedback tap was saved.
def ct(vx,reset,d2,dt,m):
 db=np.array([(d2>>n)&1 for n in range(11,-1,-1)]);ds=2*db-1;tb=np.array([(dt>>n)&1 for n in range(7,0,-1)]);ts=np.zeros(7);ts[:m]=2*tb[:m]-1
 nodes=[];alpha=[]
 for side in range(2):
  cs=float(net['cinc_f'].ravel()[side]);cb=float(net['bridge_f'].ravel()[side]);cm=net['main_f'][side];cl=net['sub_f'][side];tk=net['track_f'][side];a=cs+cm.sum()+cb+float(net['parasitic_main_f'].ravel()[side]);b=cl.sum()+tk.sum()+float(net['dummy_f'].ravel()[side])+cb+float(net['parasitic_sub_f'].ravel()[side]);M=np.array([[a,-cb],[-cb,b]]);pol=1 if side==0 else -1;qin=np.array([cs*pol*(vx-reset)/2,0]);qd=-pol*vct/2*np.array([cm@ds[:len(cm)],cl@ds[len(cm):]]);qt=-pol*vct/2*np.array([0,tk@ts]);node=np.linalg.solve(M,qin+qd+qt+np.array([-cb*qb[side]/b,qb[side]]));nodes.append(node);alpha.append(np.linalg.solve(M,np.array([cs,0]))[0])
 return float(nodes[0][0]-nodes[1][0]),float(np.mean(alpha)),ts.tolist()

spec=[('A1e4_negative',10000.,-3.0517578125e-8,baselineP,Z/'point_001/signals.mat',True),('A1e4_zero',10000.,0.,zeroP,B/'preflight_capped_simout.mat',False)]
for item in receipt['points']:
 folder=D/('point_'+str(len(spec)-1).zfill(2)+'_'+item['name']); # points 1..4 after two baseline entries
 need(folder.is_dir(),'Expected point directory missing '+str(folder))
 for filename,key in [('P.mat','P_sha256'),('simout.mat','simout_sha256'),('observed.mat','observed_sha256')]:need(sha(folder/filename)==item[key],'Point hash mismatch '+str(folder/filename))
 need(item['status']=='valid' and not item['error'] and item['rng_unchanged'],'Point failed or RNG changed')
 a=20000. if item['A0_label']=='A2e4' else math.inf
 spec.append((item['name'],a,float(item['input_offset_v']),folder/'P.mat',folder/'simout.mat',False))
need(len(spec)==6,'Expected two baseline and four new endpoints')
out=[];zero_series=[];negative_q=[]
for name,A,x,pp,ll,oldsignals in spec:
 L=signal_struct(ll) if oldsignals else read_logs(ll)
 if pp==zeroP:cfgroot='Pzero'
 else:cfgroot='P'
 with h5py.File(pp) as f:
  def v(k):return val(f,cfgroot+'/'+k)
  need(float(v('input/offset_v'))==x and float(v('input/amplitude_v'))==0 and float(v('backend/ra/A0'))==A and int(v('N'))==1 and int(v('first_id'))==4 and int(v('epoch'))==1 and int(v('n_cycles'))==5,'Point identity mismatch '+name)
 if pp!=zeroP:
  changes=pdiff(baselineP,pp);allowed=set()
  if x==0:allowed|={'P/input/offset_v','P/front/input/offset_v','P/xFE0'}
  if A!=10000:allowed.add('P/backend/ra/A0')
  if math.isinf(A):allowed.add('P/ni/ra_finite_gain')
  need(set(changes)==allowed,'Unexpected P changes '+name+': '+str(changes))
 else:changes=['reconstructed zero P; original zero P not independently saved']
 e=L['event_log']['data'];t=L['event_log']['time'];need(e.shape==(240,2) and np.array_equal(e[:,0],np.repeat(np.arange(5),48)) and np.array_equal(e[:,1],np.tile(np.arange(1,49),5)),'Event order mismatch '+name)
 need(same(t,np.array([i*2e-7+xg for i in range(5) for xg in times])),'Actual event times differ '+name)
 for k in ['raw_log','ready_log','record_log','record_ready_log','code_log','front_log','control_log','back_log']:need(same(t,L[k]['time']),'Event/log time mismatch '+name+' '+k)
 rdy=L['ready_log']['data'][:,0];need(same(rdy,L['record_ready_log']['data'][:,0]),'Record ready differs '+name);ri=np.flatnonzero(rdy==1);raw=L['raw_log']['data'][ri];need(len(ri)==5 and same(raw,L['record_log']['data'][ri]) and np.array_equal(raw[:,3],np.arange(5)) and np.all(raw[:,4]==1) and np.all(raw[:,5]==1),'RAW/ready mismatch '+name)
 raw=raw[-1];code=int(L['code_log']['data'][ri[-1],0]);d1,d2,dt=map(int,raw[:3]);c=at(L['control_log'],t,'control');b=at(L['back_log'],t,'backend');f=at(L['front_log'],t,'frontend')
 i0=4*48+11;ip=4*48+12;need(e[i0,1]==12 and e[ip,1]==13,'Bad RA groups');q=float(f[i0,2]);target=float(b[i0,3]);vx0=float(b[i0,0]);ng=float(b[i0,4]);tau=float(b[i0,5]);F=1. if math.isinf(A) else A/(A+ng);need(abs(target-q/cf)<1e-14 and abs(tau-ng/(2*math.pi*UGB))<1e-22,'RA formula mismatch '+name)
 def predict(i):return F*target+(vx0-F*target)*math.exp(-(float(t[i])-float(t[i0]))/tau)
 ra_first=float(b[ip,0]);ra_err=ra_first-predict(ip)
 tb=np.array([(dt>>n)&1 for n in range(7,-1,-1)]);db=np.array([(d2>>n)&1 for n in range(11,-1,-1)]);ta=[];max_ra=max_ct=0.
 for m in range(8):
  i=4*48+(38+m)-1;need(e[i,1]==38+m and 'ta_compare' in groups[37+m],'TA event mismatch '+name)
  expect_prefix=sum(int(tb[j])<<(7-j) for j in range(m+1));need(int(c[i,6])==expect_prefix,'Observed DT prefix mismatch '+name)
  bit=int(tb[m]);vy=float(b[i,1]);need(bit==int(vy>=0),'Actual comparator sign mismatch '+name)
  cv,alpha,ts=ct(float(b[i,0]),float(b[i,7]),d2,dt,m);rex=float(b[i,0])-predict(i);err=vy-cv;max_ct=max(max_ct,abs(err));max_ra=max(max_ra,abs(rex));ta.append({'m':m,'offset_ns':float((t[i]-4*2e-7)*1e9),'VX_V':float(b[i,0]),'VY_V':vy,'decision':bit,'prior_TA_signs_model_inferred':ts,'vy_mna_V':cv,'vy_minus_mna_V':err,'VX_minus_analytic_V':rex})
 iend=4*48+36; i85=4*48+45
 coarse,fine=divmod(d1,32);d1v=(32*coarse+2*fine-1039)*vref/1024-17*vref/1024;d2ra=float(off+np.sum(weights*db));d2v=d2ra/G;stat=int(np.sum(np.arange(8,0,-1)*(2*tb-1)));dtv=step*stat/(8*G);outv=(d1v+d2v)+dtv;unround=outv/lsb+2**19;need(math.floor(unround+.5)==code,'Digital reconstruction mismatch '+name)
 record={'name':name,'A0':'Inf' if math.isinf(A) else int(A),'input_V':x,'raw6':raw.tolist(),'code':code,'P_sha256':sha(pp),'log_sha256':sha(ll),'P_differences_vs_actual_negative_A1e4':changes,'Qres_C':q,'target_RA_V':target,'RA_start_VX_V':vx0,'NG':ng,'tau_RA_s':tau,'F':F,'RA_first_prepare_VX_V':ra_first,'RA_first_prepare_minus_analytic_V':ra_err,'RA_d2_end_VX_V':float(b[iend,0]),'RA_d2_end_VY_V':float(b[iend,1]),'RA_tracking_end_VX_V':float(b[i85,0]),'RA_tracking_end_VY_V':float(b[i85,1]),'TA':ta,'CT_alpha':alpha,'max_abs_TA_vy_minus_MNA_V':max_ct,'max_abs_TA_vx_minus_analytic_V':max_ra,'min_abs_TA_VY_V':min(abs(r['VY_V']) for r in ta),'decode':{'d1_input_V':d1v,'d2_RA_V':d2ra,'d2_input_V':d2v,'dt_statistic':stat,'dt_input_V':dtv,'voltage_V':outv,'unrounded_code':unround,'pre_round_error_to_input_V':outv-x}}
 out.append(record)
 if x==0:zero_series.append(L)
 else:negative_q.append(q)
need(np.array_equal(np.array(negative_q),np.repeat(negative_q[0],3)),'Negative RA charge differs between gain cases')
ref=zero_series[0];equal_zero={k:all(same(ref[k]['time'],l[k]['time']) and same(ref[k]['data'],l[k]['data']) for l in zero_series[1:]) for k in ['raw_log','ready_log','record_log','record_ready_log','code_log','front_log','control_log','back_log','event_log']}
need(all(equal_zero.values()),'Zero nine actual logs differ among gains')
by={x['name']:x for x in out};n0=by['A1e4_negative'];n2=by['A2e4_negative'];ni=by['Ainf_negative'];z0=by['A1e4_zero'];target=abs(n0['target_RA_V']);ng=n0['NG']
budgets=[]
for frac in [1.,.5,.25]:
 req=ng*(target/(G*frac*lsb)-1);budgets.append({'gain_error_allocation_lsb':frac,'linear_A0_min':req,'open_loop_gain_dB':20*math.log10(req),'relative_to_1e4':req/10000})
report={'schema':'sar20-zero-cross-a0-independent-physics/v1','status':'archived_six_endpoints_independently_read_no_new_simulation','receipt_sha256':sha(D/'receipt.json'),'asrun_job_sha256':sha(D/'sar20_ra_gain_probe_job.m'),'model_sha256':sha(D/'SarAdc_factory.slx'),'source_manifest_sha256':sha(D/'source_manifest.json'),'source_files_verified':len(pins),'source_cache_boundary':'Native run receipt and source hashes; cannot independently inspect MATLAB same-path cached bytecode after the run.','zero_P_boundary':'Original zero preflight P was reconstructed from pinned factory/source, not independently saved.', 'cases':out,'all_negative_Qres_same_binary64':True,'all_zero_nine_log_Time_Data_same_bits':equal_zero,'examples_fixed_target_gain_budget':budgets,'scope':'Physical-state trajectory and digital arithmetic within the exact two-point behavioral experiments; no unobserved intermediate-code, noise probability, full-range DNL/INL or PDK claim.'}
Path(__file__).with_name('gain_margin_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
print('negative Qres',negative_q[0]);print('same zero logs',equal_zero)
for r in out:print(r['name'],'RAW',r['raw6'][:3],'code',r['code'],'F',r['F'],'vx75',r['TA'][0]['VX_V'],'vy75',r['TA'][0]['VY_V'],'dt',r['decode']['dt_statistic'],'maxErrRA',r['max_abs_TA_vx_minus_analytic_V'],'maxErrCT',r['max_abs_TA_vy_minus_MNA_V'])
print('budgets',budgets)
