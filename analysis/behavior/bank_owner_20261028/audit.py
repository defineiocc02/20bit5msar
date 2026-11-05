#!/usr/bin/env python3
"""Read-only physical and digital cross-check of archived 133342 N8 cases."""
import sys,json,math,hashlib
from pathlib import Path
import numpy as np,h5py
P=Path('/Users/zhaoyi/Obsidan/项目库/outputs/sar20_5_simulink_20261020');sys.path.insert(0,str(P/'analysis/behavior/finite_dac_review_20261028'))
from verify_as_run import val,read_calendar,read_logs,pdiff,graph,at,same,sha,fingerprint,need
R=P/'runs/az_probe_20261028T133342Z';whole=json.loads((R/'receipt.json').read_text());need(whole['status']=='SCRATCH_N8_FINALIZED_PREQUALIFIED_ROUTER_PASS_NOT_INTEGRATED','Wrong terminal status')
names=['rx_nominal','rx_old_frozen','rx_bank_on']; cases={};params={};source_manifests=[]
for name in names:
 d=R/name;rc=json.loads((d/'receipt.json').read_text());need(rc['status']=='completed_saved','Wrong case status')
 for file,key in [('parameters.mat','parameters_sha256'),('simout.mat','simout_sha256'),('SarPP.slx','model_sha256'),('source_manifest_actual.json','source_manifest_sha256')]:need(sha(d/file)==rc[key],'Artifact hash mismatch '+name+'/'+file)
 params[name]=d/'parameters.mat';cases[name]=read_logs(d/'simout.mat');source_manifests.append(sha(d/'source_manifest_actual.json'))
need(len(set(source_manifests))==1,'As-run source manifests differ')
nd=pdiff(params['rx_nominal'],params['rx_bank_on']);fd=pdiff(params['rx_nominal'],params['rx_old_frozen']);need(all(x.startswith('P/bank/') for x in nd) and all(x.startswith('P/frozen/') for x in fd),'Physical parameter drift')
with h5py.File(params['rx_nominal']) as a,h5py.File(params['rx_old_frozen']) as b,h5py.File(params['rx_bank_on']) as c:
 da=fingerprint(a,a['DecodeP'],{});need(fingerprint(b,b['DecodeP'],{})==da==fingerprint(c,c['DecodeP'],{}),'DecodeP changed')
 vals={x:val(c,'P/'+x) for x in ['N','first_id','epoch','seed','Ts_s','input/amplitude_v','input/frequency_hz','input/phase_rad','transport/enabled','front/pool_seed','front/plan_rows','front/mismatch_enabled','front/dem_enabled','front/dem_seed','front/dither_enabled','front/dither_seed','front/dither_input_amplitude_v','front/ktc_enabled','front/jitter/enabled','front/tau_dac_s','backend/az/mode','backend/ra/A0','backend/ra/UGB_hz','backend/ra/vos_input_v','backend/ra/Cf_f','backend/ni/cap_mismatch','backend/ni/cinc_kick','backend/ct/replica_enabled','backend/ct/reference_v','debug/adi_enabled','digital/fsr_diff_v']}
 need(vals['N']==8 and vals['first_id']==4 and vals['epoch']==1 and vals['transport/enabled']==1 and vals['front/mismatch_enabled']==1 and vals['front/dem_enabled']==1 and vals['front/dither_enabled']==1 and vals['front/ktc_enabled']==0 and vals['front/jitter/enabled']==0 and np.all(np.asarray(vals['front/tau_dac_s'])==0) and vals['backend/az/mode']=='off' and vals['backend/ni/cap_mismatch']==0 and vals['backend/ct/replica_enabled']==1 and vals['debug/adi_enabled']==0,'Unexpected physical profile')
 need(val(c,'P/digital/dither_enabled')==1 and val(c,'P/digital/dither_seed')==vals['front/dither_seed'] and val(c,'P/digital/dither_amplitude_v')==vals['front/dither_input_amplitude_v'],'Physical/digital public dither config mismatch')
 times,groups,budget=read_calendar(c); q=c['P/bank/slots/cache'][()].ravel(); versions=c['P/bank/slots/version'][()].ravel();
 h=[c[z]['h'][()].ravel() for z in q];hf=b['P/frozen/cache/h'][()].ravel();need(np.array_equal(h[0],h[1]) and np.array_equal(h[0],hf),'Slot/frozen payloads differ');digest=hashlib.sha256(np.asarray(h[0],dtype='<f8').tobytes()).hexdigest();need(digest=='a634c9a0c63c636a4c8966bc7d0e04d6d9ad4cf550156e6ed7ffe7806d6483ed','h content hash differs');need([int(c[z][()].item()) for z in versions]==[1,2],'Version labels differ')
 ct='P/backend/ct/net_nominal/';net={k:np.asarray(val(c,ct+k)) for k in ['main_f','sub_f','track_f','cinc_f','bridge_f','dummy_f','parasitic_main_f','parasitic_sub_f']};vct=float(val(c,'P/backend/ct/reference_v'));qb=np.asarray(val(c,'P/backend/ct/initial_main_qb_c')).ravel();need(np.all(qb==0),'Unknown CT floating charge')
fullGraph=[graph(R/n/'SarPP.slx') for n in names];need(all(fullGraph[0][i]==fullGraph[1][i]==fullGraph[2][i] for i in range(3)),'Graphs differ')
edges=fullGraph[0][1];ownerEdges=sorted((a,b) for a,b in edges if a.startswith('455#out:'));need(len(ownerEdges)>0 and all(x[1].split('#')[0] in {'454','137','458','459','460','461','462'} for x in ownerEdges),'Unexpected BankOwner output path')
physical=['adc_executed_log','event_log','front_log','back_log','control_log','raw_log','ready_log','record_log','record_ready_log','frame_ready_log','sample_ready_log','az_route_log','az_commit_log','transport_frame_log','transport_trace_rows_log','d1_log','d2_log','dt_log']
for k in physical:
 a=cases[names[0]][k]
 for name in names[1:]:need(a['class']==cases[name][k]['class'] and same(a['time'],cases[name][k]['time']) and same(a['data'],cases[name][k]['data']),'Physical Time/Data mismatch '+k+' '+name)
for name in names:need(cases[name]['adi_wire_log']['data'].shape==(1,58) and np.isnan(cases[name]['adi_wire_log']['data']).all(),'ADI observer not disabled')
L=cases['rx_bank_on'];e=L['event_log']['data'];t=L['event_log']['time'];need(e.shape==(14*49,2) and np.array_equal(e[:,0],np.repeat(np.arange(14),49)) and np.array_equal(e[:,1],np.tile(np.arange(1,50),14)),'Wrong RX event grid');
with h5py.File(params['rx_bank_on']) as c:
 grp=c['P/groups'];gt=[float(c[z][()][0,0]) for z in grp['time_s'][()].ravel()];need(len(gt)==49 and gt[:48]==times,'49 groups not ADC prefix')
need(same(t,np.array([i*float(vals['Ts_s'])+g for i in range(14) for g in gt])),'Actual 49-group times differ')
execute=at(L['adc_executed_log'],t,'execute')[:,0];need(np.all(execute[e[:,1]<=48]==1) and np.all(execute[e[:,1]==49]==0),'ADC advanced on transport-only group')
raw=at(L['raw_log'],t,'raw');rdy=at(L['ready_log'],t,'ready')[:,0];record=at(L['record_log'],t,'record');rrdy=at(L['record_ready_log'],t,'record_ready')[:,0];adc=raw[rdy==1];rx=record[rrdy==1];need(adc.shape==(14,6) and rx.shape==(12,6) and np.array_equal(adc[:,3],np.arange(14)) and np.array_equal(rx[:,3],np.arange(12)) and np.all(adc[:,5]==1) and np.all(rx[:,5]==1),'Invalid actual ADC/RX records')
for row in rx:
 match=adc[adc[:,3]==row[3]];need(match.shape==(1,6) and same(match[0],row),'RX raw differs from actual ADC ID')
meta=at(L['bank_meta_log'],t,'meta');bankValid=at(L['bank_code_valid_log'],t,'bankvalid')[:,0];sel=np.flatnonzero((rrdy==1)&(record[:,3]>=4)&(record[:,3]<=11));need(len(sel)==8 and np.array_equal(record[sel,3],np.arange(4,12)) and np.all(bankValid[sel]==1),'Selected valid RX records mismatch');
for i in np.flatnonzero(rrdy==1):
 id=int(record[i,3]);need(meta[i,2]==id and meta[i,3]==1 and meta[i,4]==1 and meta[i,5]==(1 if id<4 else 2) and meta[i,6]==(1 if id<4 else 2) and meta[i,7]==0,'Version/tag mismatch')
need(np.all(bankValid[rrdy!=1]==0),'Unexpected bank code valid outside ready')

# Independent CT equation; inferred previous feedback signs, not direct sign wires.
def mna(vx,reset,d2,dt,m):
 ds=np.array([2*((d2>>k)&1)-1 for k in range(11,-1,-1)]);ts=np.zeros(7)
 for j in range(m):ts[j]=2*((dt>>(7-j))&1)-1
 n=[]
 for side in range(2):
  cs=float(net['cinc_f'].ravel()[side]);cb=float(net['bridge_f'].ravel()[side]);cm=net['main_f'][side];cl=net['sub_f'][side];ct=net['track_f'][side];a=cs+cm.sum()+cb+float(net['parasitic_main_f'].ravel()[side]);b=cl.sum()+ct.sum()+float(net['dummy_f'].ravel()[side])+cb+float(net['parasitic_sub_f'].ravel()[side]);M=np.array([[a,-cb],[-cb,b]]);pol=1 if side==0 else -1;qin=np.array([cs*pol*(vx-reset)/2,0]);qd=-pol*vct/2*np.array([cm@ds[:len(cm)],cl@ds[len(cm):]]);qt=-pol*vct/2*np.array([0,ct@ts]);n.append(np.linalg.solve(M,qin+qd+qt+np.array([-cb*qb[side]/b,qb[side]])))
 return float(n[0][0]-n[1][0])

front=at(L['front_log'],t,'front');back=at(L['back_log'],t,'back');ctrl=at(L['control_log'],t,'control');adcready=at(L['ready_log'],t,'adc_ready')[:,0];A=float(vals['backend/ra/A0']);cf=float(vals['backend/ra/Cf_f']);UGB=float(vals['backend/ra/UGB_hz']);taErr=[];raErr=[];countTA=countD2=0;nodes=[]
for id in range(4,12):
 ar=np.flatnonzero((adcready==1)&(raw[:,3]==id));need(len(ar)==1,'Missing ADC source');a=raw[ar[0]];d1,d2,dt=map(int,a[:3]);i0=np.flatnonzero((e[:,0]==id)&(e[:,1]==12));i1=np.flatnonzero((e[:,0]==id)&(e[:,1]==13));need(len(i0)==len(i1)==1,'Missing RA interval');i0=i0[0];i1=i1[0];ng=float(back[i0,4]);tau=ng/(2*math.pi*UGB);F=A/(A+ng);target=float(back[i0,3]);pred=F*target+(float(back[i0,0])-F*target)*math.exp(-(t[i1]-t[i0])/tau);raErr.append(float(back[i1,0])-pred)
 for m,g in enumerate([j+1 for j,ev in enumerate(groups) if 'd2_decide' in ev]):
  i=np.flatnonzero((e[:,0]==id)&(e[:,1]==g))[0];bit=(int(ctrl[i,5])>>(11-m))&1;prefix=d2 & ((0xfff << (11-m)) & 0xfff);need(int(ctrl[i,5])==prefix and bit==((d2>>(11-m))&1) and bit==int(back[i,1]>=0),'Actual D2 decision trace mismatch');countD2+=1
 for m,g in enumerate([j+1 for j,ev in enumerate(groups) if 'ta_compare' in ev]):
  i=np.flatnonzero((e[:,0]==id)&(e[:,1]==g))[0];bit=(int(ctrl[i,6])>>(7-m))&1;prefix=dt & ((0xff << (7-m)) & 0xff);need(int(ctrl[i,6])==prefix and bit==((dt>>(7-m))&1) and bit==int(back[i,1]>=0),'Actual TA decision trace mismatch');taErr.append(float(back[i,1])-mna(float(back[i,0]),float(back[i,7]),d2,dt,m));countTA+=1
 ix=[np.flatnonzero((e[:,0]==id)&(e[:,1]==g))[0] for g in [1,12,13,37,38,45,47,48]]
 nodes.append({'id':id,'held_V':float(front[ix[0],0]),'Qres_RAstart_C':float(front[ix[1],2]),'vx_first_prepare_V':float(back[ix[2],0]),'vy_first_prepare_V':float(back[ix[2],1]),'vx_first_ta_V':float(back[ix[4],0]),'vy_first_ta_V':float(back[ix[4],1]),'vtop_release_V':float(back[ix[7],2])})
need(countD2==96 and countTA==64,'Actual decision count differs')

# Public nominal components are identical in all three; frozen output is NOT their sum.
m=2147483647; seed=int(vals['front/dither_seed']); amplitude=float(vals['front/dither_input_amplitude_v']);fsr=float(vals['digital/fsr_diff_v']);table=[]
for i in sel:
 id=int(record[i,3]); dither=(math.floor(4*((seed%(m-1)+1)*pow(16807,id+1,m)%m)/m)-1.5)*amplitude
 d1=float(L['d1_log']['data'][i,0]);d2=float(L['d2_log']['data'][i,0]);dt=float(L['dt_log']['data'][i,0]);nomv=((d1+d2)+dt)+dither;nomcode=int(cases['rx_nominal']['code_log']['data'][i,0]);frocode=int(cases['rx_old_frozen']['code_log']['data'][i,0]);bankcode=int(L['code_log']['data'][i,0]);fl=at(cases['rx_old_frozen']['frozen_log'],np.array([t[i]]),'frozen')[0];frozenv=float(fl[8]);expected=(float(fl[0])+float(fl[6]))/float(fl[7]);need(abs(frozenv-expected)<2e-14 and fl[9]==fl[10]==1,'Frozen arithmetic/log invalid');need(math.floor(nomv*(2**20/fsr)+2**19+.5)==nomcode and math.floor(frozenv*(2**20/fsr)+2**19+.5)==frocode==bankcode,'Actual code reconstruction mismatch');
 table.append({'id':id,'rx_time_s':float(t[i]),'raw6':record[i].tolist(),'nominal_code':nomcode,'frozen_code':frocode,'bank_code':bankcode,'bank_minus_nominal_codes':bankcode-nomcode,'nominal_d1_V':d1,'nominal_d2_V':d2,'nominal_dt_V':dt,'public_dither_V':dither,'nominal_voltage_V':nomv,'frozen_u_RA_V':float(fl[0]),'frozen_Bh_RA_V':float(fl[6]),'frozen_P_h':float(fl[7]),'frozen_voltage_V':frozenv,'frozen_voltage_minus_formula_V':frozenv-expected,'slot':int(meta[i,5]),'version':int(meta[i,6])})
need(all(x['bank_code']!=x['nominal_code'] for x in table),'Expected all eight differences to be data-driven')
example=next(x for x in table if x['id']==9);n9=next(x for x in nodes if x['id']==9);example['held_model_V']=n9['held_V'];example['nominal_minus_held_V']=example['nominal_voltage_V']-n9['held_V'];example['frozen_minus_held_V']=example['frozen_voltage_V']-n9['held_V']
training=P/'runs/behavior_a27903ef-c1c6-4e5e-b487-d2c1d468efef';train=read_logs(training/'simout.mat');tr=train['record_log']['data'];tready=train['record_ready_log']['data'][:,0];ti=np.flatnonzero((tready==1)&(tr[:,3]>=4)&(tr[:,3]<=11));need(len(ti)==8 and same(tr[ti],record[sel]) and same(train['record_log']['time'][ti],t[sel]),'The claimed training-prefix replay does not match')
trainingPdiff=pdiff(training/'parameters.mat',params['rx_nominal']);trainingAllowed={'P/N','P/bank','P/cal_cfg/N_train','P/cal_cfg/enabled','P/n_cycles','P/schedule/n_cycles','P/schedule/stop_time_s','P/stop_time_s','P/training/enabled','P/training/log_points','P/training/reference/enabled','P/training/reference/records','P/training/snapshot_width'};need(set(trainingPdiff)==trainingAllowed,'Training P differs beyond declared replay controls')
report={'schema':'sar20-bank-physical-digital-boundary/v1','status':'actual_saved_three_N8_cases_read_no_new_simulation','top_receipt_sha256':sha(R/'receipt.json'),'source_manifest_sha256':source_manifests[0],'mode_p_differences':{'old_frozen':fd,'bank_on':nd},'identical_graph_block_params_and_edges':True,'graph_edges_count':len(edges),'bank_owner_output_edges':ownerEdges,'same_Time_Data_class_logs':physical,'ADC_groups_per_cycle':48,'RX_groups_per_cycle':49,'budget_declared':budget,'actual_ADC_decisions_checked':{'D2':countD2,'TA':countTA},'ADI_observer':'disabled; actual sign wires and per-slice endpoint states were not independently logged','ta_CT_mna_max_abs_V':max(map(abs,taErr)),'first_RA_interval_max_abs_V':max(map(abs,raErr)),'coefficient_h_sha256':digest,'both_slots_same_h_and_match_frozen':True,'training_prefix_replay':{'training_simout_sha256':sha(training/'simout.mat'),'training_P_sha256':sha(training/'parameters.mat'),'ID4_11_RX_raw_and_times_bit_equal':True,'training_P_control_differences':trainingPdiff,'interpretation':'Replay of training conditions and records, not an independent holdout.'},'cases':table,'analog_nodes':nodes,'readiness_scope':'Compared only valid RX-ready records for code equality; non-ready Bank/Frozen code waveforms differ.','qualification_scope':'behavior-profile prequalified, NOT_ACCEPTED; no product authorization, fault injection, retirement drain or online retraining proven.','limitations':'Eight actual samples, no spectrum or overall performance; CT signs inferred, not physically probed; P/front/backend are offline audit inputs, never fed to BankOwner or fitter.'}
Path(__file__).with_name('audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
print('matched physical logs',len(physical),'actual decisions D2/TA',countD2,countTA,'maxRA',report['first_RA_interval_max_abs_V'],'maxCT',report['ta_CT_mna_max_abs_V']);print('codes',[(x['id'],x['nominal_code'],x['bank_code'],x['bank_minus_nominal_codes']) for x in table]);print('sample9',json.dumps(example));print('owner outgoing edges',ownerEdges)
