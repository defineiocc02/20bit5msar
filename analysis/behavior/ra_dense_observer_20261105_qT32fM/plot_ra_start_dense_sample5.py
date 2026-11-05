#!/usr/bin/env python3
"""Plot saved conditional RA drift and separate actual model-event endpoints."""
from __future__ import annotations
import argparse,csv,hashlib,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
import h5py,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];RUN=HERE/'actual_n8'
READER=ROOT/'analysis/behavior/finite_dac_review_20261028/verify_as_run.py'
STYLE=ROOT/'analysis/behavior/single_bank_1039_20261104/figures/fig01_02_actual_n8_20261104/author_style.py'
sys.path.insert(0,str(READER.parent));import verify_as_run as u
sys.path.insert(0,str(STYLE.parent));import author_style
BASE=ROOT/'analysis/behavior/normal_workpoint_20261104/windows_main_actual/normal_merged_n8'
PINS={'observed_model':'e13bd2529024346f510446de5c9046689c62c4d61b6e9869dea0d5da1cb86bfb',
 'source_manifest':'73867eabe50b70920cd3373190832e2d78426c59b0116d6062ff94c4c903f14c',
 'P_used':'6814e2b18bed35405a0ff17573724662878f0000c8509c23c775e1e2c5d93e55',
 'simout':'d6c33eed9831b7aaef889de5de369e906fbedff021dfaa50753ad6546609eaff',
 'physical_tap':'281647a8aa6af3ede88004beb1dd567470e1d632ec46931a0876e6f7dae1613e',
 'observer':'80857951cc64995ee56193102d9a197cb2500e5dd3e416571d2f59eaab86c77b',
 'complete':'9317c5abfe2d884b2b7bc13f172eca182d1670fa2a8dbfc8514d1e28e0893e1c',
 'baseline_P':'e42b739ed7c465845ed0e415a9f2fdfdd1afa0caaf0c18055c3f77fbfe683b61',
 'baseline_simout':'2267e645ebc3000e1ad8e2ff56eec2f7c58d9205922cb9746c98b855792db705',
 'reader':'3ca8dc8a6f553e75466438a0d74b9bf6a0a6ab5f65b8c151429981af330f7467'}
BLUE='#0072B2';GREEN='#009E73';ORANGE='#D55E00';BLACK='#1c1c1c';RED='#B2182B'
def need(v,m):
    if not v:raise ValueError(m)
def sha(p):
    need(p.is_file() and not p.is_symlink() and p.stat().st_size<=300_000_000,f'bad/missing/>300 MB: {p}')
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True,type=Path);a=ap.parse_args();out=a.out.resolve()
    need(not out.exists() or out.is_dir(),'output is not a directory')
    for name in ('ra_start_dense_sample5.png','ra_start_dense_sample5.csv','ra_start_dense_sample5_metadata.json'):
        need(not (out/name).exists(),f'refuse overwrite: {name}')
    files={'observed_model':HERE/'actual_build/SarAdc.slx',
      'source_manifest':ROOT/'analysis/behavior/merged_ou_rc_20261104_toyFVb/candidate/MANIFEST.json',
      'P_used':RUN/'P_used.mat','simout':RUN/'simout.mat','physical_tap':RUN/'physical_state_tap.mat',
      'observer':RUN/'observer_sample5.mat','complete':RUN/'complete.json',
      'baseline_P':BASE/'P_used.mat','baseline_simout':BASE/'simout.mat','reader':READER}
    for name,p in files.items():need(sha(p)==PINS[name],f'input SHA mismatch: {name}')
    receipt=json.loads(files['complete'].read_text())
    for key,pin in [('observed_model_sha256','observed_model'),('simout_sha256','simout'),
                    ('tap_sha256','physical_tap'),('observer_sha256','observer'),('input_P_sha256','baseline_P')]:
        need(receipt[key]==PINS[pin],f'receipt does not bind {pin}')
    need(not u.pdiff(files['P_used'],files['baseline_P']),'actual used P differs from pinned original')
    old=u.read_logs(files['baseline_simout']);L=u.read_logs(files['simout']);need(set(L)==set(old)|{'physical_state_tap'},'log inventory')
    for key in old:
        x,y=old[key],L[key];need(x['class']==y['class'] and x['storage_shape']==y['storage_shape'] and
          u.same(x['time'],y['time']) and u.same(x['data'],y['data']),f'instrument changed log {key}')
    e=L['event_log']['data'];te=L['event_log']['time'];tap=L['physical_state_tap'];D=tap['data']
    need(D.shape==(576,2015) and u.same(te,tap['time']) and u.same(D[:,:2],e),'2015-wire tap axis/tags')
    with h5py.File(files['physical_tap'],'r') as f:
        seq=[f[x] for x in f['#subsystem#/MCOS'][()].ravel()]
        d=[x for x in seq if isinstance(x,h5py.Dataset) and x.shape==(2015,576)]
        q=[x for x in seq if isinstance(x,h5py.Dataset) and x.shape==(1,576) and x.dtype==np.dtype('float64')]
        need(len(d)==1 and any(u.same(x[()].ravel(),te) for x in q) and u.same(d[0][()].T,D),
             'standalone tap does not match logged data')
    i=np.flatnonzero((e[:,0]==5)&(e[:,1]==12));j=np.flatnonzero((e[:,0]==5)&(e[:,1]==13))
    k=np.flatnonzero((e[:,0]==5)&(e[:,1]==14));need(len(i)==len(j)==len(k)==1,'sample/event identity')
    i,j,k=int(i[0]),int(j[0]),int(k[0]);need(j==i+1,'interval events not adjacent')
    need(u.same(D[i,1414:1767],D[j,2:355]) and u.same(D[i,1959:2007],D[j,1767:1815]),
         't0 next != t1 old FE/RA state bits')
    with h5py.File(files['observer'],'r') as f:
        g=lambda x:u.val(f,'out1/'+x)
        q=np.asarray(g('query_time_s')).ravel();obs=np.asarray(g('deterministic_drift_obs8'))
        end=np.asarray(g('recorded_endpoint_obs8')).ravel();t0=float(g('t_start_s'));t1=float(g('t_stop_s'))
        start=np.asarray(u.val(f,'t0_check/observer_obs8')).ravel();back0=np.asarray(u.val(f,'t0_check/back_log_obs8')).ravel()
        need(g('candidate_manifest_sha256')==PINS['source_manifest'] and int(g('sample_id'))==5 and int(g('epoch'))==1 and
          int(g('new_interior_ou_innovations'))==0 and int(g('interior_is_actual_ou_path'))==0,
          'observer scope/identity mismatch')
        need(int(g('same_start_next_old_bitwise'))==1 and int(g('original_endpoint_replay_bitwise'))==1,
          'observer own recorded bit gates failed')
        need(u.same(np.array([t0,t1]),np.array([te[i],te[j]])) and len(q)==125 and obs.shape==(125,8) and
          u.same(q[:1],np.array([t0])) and np.all(np.diff(q)>0) and np.all((q>=t0)&(q<t1)),
          'query bounds/t0/t1 mismatch')
        need(u.same(obs[0],start) and u.same(start,back0) and u.same(start,L['back_log']['data'][i]),
          't0 observer/back bits differ')
        need(u.same(end,D[j,2007:2015]) and u.same(end,L['back_log']['data'][j]),
          't1 actual RaAdvance endpoint bits differ')
        need(u.same(np.array([float(g('start_qres_over_cf_v'))]),obs[:1,3]) and
          u.same(np.array([float(g('recorded_endpoint_qres_over_cf_v'))]),end[3:4]),'target endpoint mismatch')
    with h5py.File(files['P_used'],'r') as f:
        get=lambda p:u.val(f,'P/'+p)
        A0=float(get('backend/ra/A0'));vos=float(get('backend/ra/vos_input_v'));Ts=float(get('Ts_s'))
        need(A0==10000 and vos==.001 and Ts==200e-9 and float(get('fsr_diff_v'))==10 and
          np.all(np.asarray(get('front/tau_dac_s'))==.5e-9),'unexpected RA P')
    ng=obs[:,4];F=A0/(A0+ng);equilibrium=F*(obs[:,3]+ng*(vos-obs[:,6]))
    event_obs=np.stack((L['back_log']['data'][i],end,L['back_log']['data'][k]));et=te[[i,j,k]]
    eq_events=(A0/(A0+event_obs[:,4]))*(event_obs[:,3]+event_obs[:,4]*(vos-event_obs[:,6]))
    x=(q-5*Ts)*1e9;xe=(et-5*Ts)*1e9;rel=(q-t0)*1e9
    imin=int(np.argmin(obs[:,0]));nz=np.flatnonzero(obs[1:,0]>=0);need(len(nz)>0,'no later nonnegative drift sample');iz=int(nz[0]+1)
    need(abs(rel[imin]-.8)<1e-8 and abs(obs[imin,0]*1e3+16.6137786667)<1e-7 and
         abs(rel[iz]-2.6)<1e-8 and abs(end[0]*1e3-45.6436481)<1e-5,'unexpected reference points')
    rows=[]
    for z in range(125):rows.append({'kind':'conditional_grid','event':'',
      't_abs_s':format(q[z],'.17g'),'t_from_cnv_ns':format(x[z],'.17g'),'t_from_ra_start_ns':format(rel[z],'.17g'),
      'conditional_vx_v':format(obs[z,0],'.17g'),'qres_over_cf_v':format(obs[z,3],'.17g'),
      'frozen_equilibrium_v':format(equilibrium[z],'.17g'),'event_vx_v':'','event_qres_over_cf_v':''})
    for name,z in zip(('ra_start','first_d2_prepare','first_d2_decide'),range(3)):
        rows.append({'kind':'recorded_event','event':name,'t_abs_s':format(et[z],'.17g'),
          't_from_cnv_ns':format(xe[z],'.17g'),'t_from_ra_start_ns':format((et[z]-t0)*1e9,'.17g'),
          'conditional_vx_v':'','qres_over_cf_v':'','frozen_equilibrium_v':'',
          'event_vx_v':format(event_obs[z,0],'.17g'),'event_qres_over_cf_v':format(event_obs[z,3],'.17g')})
    rows.sort(key=lambda z:(float(z['t_abs_s']),z['kind']!='recorded_event'))
    out.mkdir(parents=True,exist_ok=True);table=out/'ra_start_dense_sample5.csv'
    with table.open('x',encoding='utf8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    author_style.apply();fig,(ax1,ax2)=plt.subplots(2,1,sharex=True,figsize=(146/25.4,6.15),gridspec_kw={'height_ratios':[.88,1]})
    fig.subplots_adjust(left=.17,right=.96,top=.80,bottom=.31,hspace=.25)
    fig.text(.015,.982,'RA 启动：条件漂移与模型事件点（ID 5）',fontname='PingFang SC',size=9,weight='bold',va='top')
    fig.text(.015,.946,'从实际左端态出发，区间内无新增 OU 创新；并非已观测的随机噪声路径。',fontname='PingFang SC',size=7,va='top')
    fig.text(.015,.916,'125 prediction samples: 31.25–43.65 ns · recorded t1 = 43.75 ns kept separate',size=7,va='top')
    ax1.plot(x,obs[:,3]*1e3,color=BLUE,lw=1,label='Qres/Cf driving target')
    ax1.plot(x,equilibrium*1e3,color=BLACK,lw=.9,ls='--',label='Frozen equilibrium (A0/NG/AZ)')
    ax1.scatter(xe,event_obs[:,3]*1e3,color=BLUE,marker='o',edgecolors='black',linewidths=.5,s=17,zorder=5,label='Recorded model events')
    ax1.axvline(xe[1],color='#888888',ls=':',lw=.6);ax1.set_ylabel('Target / equilibrium (mV)')
    ax1.text(0,1.04,'(a) DAC charge forcing and finite-gain equilibrium reference',transform=ax1.transAxes,va='bottom',size=7)
    ax1.legend(loc='lower right',frameon=False,fontsize=6.5);ax1.grid(True,alpha=.2)
    ax2.plot(x,obs[:,0]*1e3,color=GREEN,lw=1.1,label='Conditional drift (no new OU innovation)')
    ax2.scatter(xe[:2],event_obs[:2,0]*1e3,color=ORANGE,marker='o',edgecolors='black',linewidths=.5,s=22,zorder=6,label='Recorded RA event VX')
    ax2.scatter(xe[2:],event_obs[2:,0]*1e3,color=ORANGE,marker='^',edgecolors='black',linewidths=.5,s=25,zorder=6,label='First D2 event VX')
    ax2.scatter([x[imin]],[obs[imin,0]*1e3],color=RED,marker='*',s=42,zorder=7)
    ax2.annotate(f'grid min {obs[imin,0]*1e3:.2f} mV\n+{rel[imin]:.1f} ns',xy=(x[imin],obs[imin,0]*1e3),
      xytext=(33.1,-19),textcoords='data',fontsize=6.5,arrowprops={'arrowstyle':'-','lw':.5,'color':RED},color=RED)
    ax2.scatter([x[iz]],[obs[iz,0]*1e3],facecolors='white',edgecolors=GREEN,s=24,zorder=7)
    ax2.annotate(f'first grid ≥0: +{rel[iz]:.1f} ns',xy=(x[iz],obs[iz,0]*1e3),
      xytext=(34.4,8),textcoords='data',fontsize=6.5,arrowprops={'arrowstyle':'-','lw':.5})
    ax2.axhline(0,color=BLACK,lw=.5);ax2.axvline(xe[1],color='#888888',ls=':',lw=.6)
    ax2.set_xlim(31,45.5);ax2.set_ylim(-24,58);ax2.set_ylabel('RA output VX (mV)');ax2.set_xlabel('Time from CNV (ns)')
    ax2.text(0,1.04,'(b) Conditional prediction and separate recorded event points',transform=ax2.transAxes,va='bottom',size=7)
    ax2.legend(loc='lower right',frameon=False,fontsize=6.3);ax2.grid(True,alpha=.2)
    fig.text(.015,.235,'t0 = 1.031250 µs · t1 = 1.043750 µs · first D2 = 1.045000 µs · FSRdiff = 10 V',size=6.5)
    fig.text(.015,.213,'t1 is outside the prediction grid; the t1-to-last-grid difference is not an OU-innovation measurement.',size=6.3)
    for z,(name,key) in enumerate([('Observed SLX','observed_model'),('Source manifest','source_manifest'),
      ('P-used','P_used'),('Observer MAT','observer'),('Physical tap MAT','physical_tap'),('Actual simout','simout')]):
        fig.text(.015,.183-.022*z,f'{name} SHA256: {PINS[key]}',size=5.8,va='center')
    author_style.finish(fig);png=out/'ra_start_dense_sample5.png';fig.savefig(png,dpi=400,facecolor='white');plt.close(fig)
    meta={'schema':'ra-start-conditional-drift-figure/v1','inputs_sha256':PINS,'sample_id':5,'epoch':1,
      't_start_s':t0,'t_stop_s':t1,'first_d2_event_s':float(te[k]),'conditional_grid_points':len(q),
      'last_grid_s':float(q[-1]),'grid_min_vx_v':float(obs[imin,0]),'grid_min_delay_ns':float(rel[imin]),
      'first_nonnegative_grid_delay_ns':float(rel[iz]),'recorded_endpoint_vx_v':float(end[0]),
      'start_qres_over_cf_v':float(obs[0,3]),'recorded_endpoint_qres_over_cf_v':float(end[3]),
      'frozen_equilibrium_formula':'A0/(A0+NG) * (Qres/Cf + NG*(Vos-AZdiff))',
      'recorded_events':[{'name':name,'time_s':float(et[z]),'obs8':event_obs[z].tolist()} for z,name in enumerate(('ra_start','first_d2_prepare','first_d2_decide'))],
      'verified':['source hashes and receipt bindings','P value identity with baseline','32 preexisting logs time/data bit equal',
        'standalone tap equals simout tap','FE/RA group-end next equals next event old bits',
        't0 conditional obs8 equals actual back_log bits','t1 recorded obs8 equals actual tap and back_log bits'],
      'limitations':['Conditional drift starts from actual t0 state but injects no new interior OU innovations; it is not an observed OU sample path.',
        'Original t1 endpoint is outside the 125 point grid; difference to last grid is not itself an innovation measurement.',
        'Frozen equilibrium is a calculated reference, not a recorded VX trajectory.',
        'RA event points are model stage observations, not transistor or silicon waveforms.'],
      'plot_script_sha256':sha(Path(__file__)),'style_helper_sha256':sha(STYLE),
      'outputs_sha256':{png.name:sha(png),table.name:sha(table)}}
    (out/'ra_start_dense_sample5_metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('Saved',out,'grid min mV',obs[imin,0]*1e3,'first nonnegative ns',rel[iz],'endpoint mV',end[0]*1e3)
if __name__=='__main__':main()
