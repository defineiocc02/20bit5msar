#!/usr/bin/env python3
"""Independently audit actual N256 MAT data and draw its Fig.7-context spectrum.

No MATLAB, model simulation, fabricated data, interpolation or raw-file writes.
The --out path must be new or empty. Project root is resolved from this file.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,sys
from pathlib import Path
sys.dont_write_bytecode=True
import h5py,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
PRJ=ROOT/'analysis/behavior/single_bank_1039_20261104'
RUN=PRJ/'n256_actual/n256'
N8=PRJ/'n8_plain/plain'
READER=ROOT/'analysis/behavior/finite_dac_review_20261028/verify_as_run.py'
STYLE=PRJ/'figures/fig01_02_actual_n8_20261104/author_style.py'
sys.path.insert(0,str(READER.parent));import verify_as_run as u
sys.path.insert(0,str(STYLE.parent));import author_style
PINS={
 'N256_P_used.mat':'e01e7f45344091eb704755585a4c27bf7a5d13057223b06e7f330a62e53b310d',
 'N256_P_diff.mat':'c58f0c7fbcfaf3768324f6b16d651ebcc465799f4dd11fb97742bd21627306bd',
 'N256_P_difference.json':'b92f9e3dd880b6a2c19224347bb052c310c5461f74e5137f87126dd06fe386c1',
 'N256_simout.mat':'17017f1a50caea4a54aa485adf18c5be27863976e63667f4f9e61633b64abf59',
 'N256_selected.mat':'a091850bd779a5c2aa61999a29e02b8fc7c9085abdf87695af24fce3bc7b2c66',
 'N256_spectrum.mat':'5f60479a83caa12f962ad80845141707c8c6c4174418d715a650abfbb7cee51f',
 'N256_complete.json':'ef02e0478ef8d24b2e834bbd4eaa15b3a445e6316c9e0f8ee5bd058025f3d910',
 'N8_P_used.mat':'236ddfb427dfc07e7f7e27dd58746deb30946891717d255b53789aa8127a1e9f',
 'N8_simout.mat':'d472f01a80a832cd483783e4ceca0640a692e0094d1a64f5400411e5201a934c',
 'model.slx':'48537818b3212e1e4c8231dec433d1fde36d95814cdcce8c529bb2898eb097d3',
 'source.zip':'09e6c7c82635d8f6bf1cf4cc8e86f0ec42036524bfe6518dfcb37ea05fb06eb7',
 'reader.py':'3ca8dc8a6f553e75466438a0d74b9bf6a0a6ab5f65b8c151429981af330f7467',
}

def need(v,msg):
    if not v:raise ValueError(msg)

def sha(path):
    need(path.is_file() and not path.is_symlink() and path.stat().st_size<=300_000_000,
         f'missing, symbolic link, or over 300 MB: {path}')
    h=hashlib.sha256()
    with path.open('rb') as f:
        for data in iter(lambda:f.read(1024*1024),b''):h.update(data)
    return h.hexdigest()

def field_order(h,root):
    """MATLAB field-order metadata of all direct nested P structs."""
    out={}
    def visit(name,node):
        if not isinstance(node,h5py.Group) or 'MATLAB_fields' not in node.attrs:return
        out[name]=tuple(bytes(np.asarray(x).tobytes()) for x in node.attrs['MATLAB_fields'])
    visit('',h[root]);h[root].visititems(visit)
    return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    out=a.out.resolve();need(not out.exists() or (out.is_dir() and not any(out.iterdir())),
                             'Output directory must be new or empty.')
    files={
      'N256_P_used.mat':RUN/'P_used.mat','N256_P_diff.mat':RUN/'P_diff.mat',
      'N256_P_difference.json':RUN/'P_difference.json','N256_simout.mat':RUN/'simout.mat',
      'N256_selected.mat':RUN/'selected.mat','N256_spectrum.mat':RUN/'spectrum.mat',
      'N256_complete.json':RUN/'complete.json','N8_P_used.mat':N8/'P_used.mat',
      'N8_simout.mat':N8/'simout.mat','model.slx':PRJ/'graph_v2/SarAdc.slx',
      'source.zip':PRJ/'single_bank_1039_candidate_20261104_v2.zip','reader.py':READER}
    for name,path in files.items():need(sha(path)==PINS[name],f'Pinned input changed: {name}')
    receipt=json.loads((RUN/'complete.json').read_text(encoding='utf-8'))
    need(receipt['model_sha256']==PINS['model.slx'] and receipt['simout_sha256']==PINS['N256_simout.mat'],
         'Receipt is not bound to actual SLX and simout.')

    # Independently compare every serialized P value, not just P_difference.json.
    difference=u.pdiff(RUN/'P_used.mat',N8/'P_used.mat')
    diffjson=json.loads((RUN/'P_difference.json').read_text(encoding='utf-8'))
    expected=sorted(x.replace('.','/') for x in diffjson['paths'])
    need(difference==expected and len(difference)==11,'Full P difference differs from recorded 11 paths.')
    need(set(diffjson['paths'])<=set(diffjson['allowed']),'Unexpected physical P change.')
    changed={}
    with h5py.File(RUN/'P_used.mat','r') as pn,h5py.File(N8/'P_used.mat','r') as po, \
         h5py.File(RUN/'P_diff.mat','r') as pd:
        need(u.fingerprint(pn,pn['P0'],{})==u.fingerprint(po,po['P'],{}),
             'N256 P0 differs from actual N8 P.')
        need(field_order(pn,'P0')==field_order(po,'P')==field_order(pn,'P'),
             'Nested P struct field order differs.')
        changes=[]
        for j in range(len(expected)):
            name=''.join(map(chr,pd[pd['changes'][j,0]][()].ravel()));changes.append(name)
            leaf=name[2:].replace('.','/')
            before=pd[pd['before'][j,0]];after=pd[pd['after'][j,0]]
            need(u.fingerprint(pd,before,{})==u.fingerprint(pn,pn['P0/'+leaf],{}) and
                 u.fingerprint(pd,after,{})==u.fingerprint(pn,pn['P/'+leaf],{}),
                 f'P_diff saved values differ: {name}')
            old=u.val(pn,'P0/'+leaf);new=u.val(pn,'P/'+leaf)
            if np.asarray(old).size==1 and np.asarray(new).size==1:
                changed[name]={'before':float(old),'after':float(new)}
            else:changed[name]={'before_shape':list(np.asarray(old).shape),'after_shape':list(np.asarray(new).shape)}
        need(sorted(changes)==sorted(diffjson['paths']),'P_diff saved path inventory differs.')
        for key in ('front/plan','backend/dac_coupling/public_plan'):
            plan=np.asarray(u.val(pn,'P/'+key));old=np.asarray(u.val(pn,'P0/'+key))
            need(plan.shape==(264,8) and old.shape==(32,8) and
                 np.array_equal(plan,np.tile(np.arange(1.,9.),(264,1))) and u.same(plan[:32],old),
                 f'Single-bank plan/prefix differs: {key}')
        get=lambda k:u.val(pn,'P/'+k)
        fs=float(get('fs_hz'));fsr=float(get('fsr_diff_v'));fin=float(get('input/frequency_hz'))
        amp=float(get('input/amplitude_v'));Ts=float(get('Ts_s'))
        need(fs==5e6 and fin==97656.25 and fsr==8.192 and int(get('N'))==256 and
             int(get('n_cycles'))==260 and int(get('first_id'))==4 and int(get('epoch'))==1,
             'Unexpected record or stimulus parameters.')
        need(all(not bool(get(k)) for k in ('front/ktc_enabled','front/dem_enabled','front/dither_enabled',
             'front/jitter/enabled','front/mismatch_enabled','backend/ni/ra_noise','backend/ni/az',
             'backend/ni/az_noise','backend/ni/reference_noise','ni/comparator_noise',
             'ni/reference_recovery','debug/adi_enabled','debug/aperture_enabled','training/enabled',
             'transport/enabled','cal_cfg/enabled','bank/enabled')) and get('backend/az/mode')=='off',
             'Unexpected nonideality, observation or calibration enabled.')
        need(float(get('control/sar1/coarse_noise_rms_v'))==0 and
             np.all(np.asarray(get('front/tau_sample_s'))==0) and
             np.all(np.asarray(get('front/tau_dac_s'))==0) and get('front/single_guard_s')==0,
             'Unexpected noise or acquisition parameter.')
        cfg={'fs_hz':fs,'fsr_diff_v':fsr,'fin_hz':fin,'input_peak_v':amp,
             'input_phase_rad':float(get('input/phase_rad')),'A0':float(get('backend/ra/A0')),
             'UGB_hz':float(get('backend/ra/UGB_hz')),'Cf_f':float(get('backend/ra/Cf_f')),
             'single_bank':bool(get('front/single_bank')),'guard_s':float(get('front/single_guard_s'))}
        offsets,groups,budget=u.read_calendar(pn)

    L=u.read_logs(RUN/'simout.mat');B=u.read_logs(N8/'simout.mat')
    te=L['event_log']['time'];ev=L['event_log']['data'];ncyc=260;ng=48
    need(np.array_equal(ev,np.column_stack((np.repeat(np.arange(ncyc),ng),np.tile(np.arange(1,ng+1),ncyc)))),
         'Actual event ID/group sequence differs.')
    need(u.same(te,np.repeat(np.arange(ncyc)*Ts,ng)+np.tile(offsets,ncyc)),
         'Actual event timestamps differ from actual P calendar.')
    for name in ('raw_log','ready_log','record_log','record_ready_log','code_log','control_log'):
        need(u.same(te,L[name]['time']),f'Time axis differs: {name}')
    raw=L['raw_log']['data'];ready=L['ready_log']['data'][:,0]
    rec=L['record_log']['data'];rec_ready=L['record_ready_log']['data'][:,0]
    ctl=L['control_log']['data'];codes=L['code_log']['data'][:,0]
    expected_groups=[j+1 for j,v in enumerate(groups) if 'raw_latch' in v]
    need(len(expected_groups)==1,'Actual saved raw-latch schedule malformed.')
    expected_ready=(ev[:,1]==expected_groups[0]).astype(ready.dtype)
    need(u.same(ready,expected_ready) and u.same(rec_ready,expected_ready),'Actual RAW ready mismatch.')
    ix=np.flatnonzero(ready==1)
    need(len(ix)==260 and u.same(raw[ix],rec[ix]) and
         np.array_equal(raw[ix,3],np.arange(260)) and np.all(raw[ix,4]==1) and np.all(raw[ix,5]==1) and
         u.same(raw[ix,:3],ctl[ix,4:7]) and np.all(ctl[ix,7]==1),
         'Actual RAW/control/ID/epoch/valid mismatch.')
    sraw=raw[ix][4:];scodes=codes[ix][4:];stimes=te[ix][4:]
    need(len(scodes)==256 and np.array_equal(sraw[:,3],np.arange(4,260)) and
         np.all(np.isfinite(scodes)) and np.all(scodes==np.floor(scodes)) and
         np.all((scodes>=0)&(scodes<2**20)),'Invalid selected actual 20-bit codes.')
    with h5py.File(RUN/'selected.mat','r') as f:
        selected={'observed_raw':raw[ix],'observed_ready_time_s':te[ix],
                  'raw':sraw,'code20':scodes,'time_s':stimes}
        for k,x in selected.items():
            y=np.asarray(u.val(f,'selected/'+k)).reshape(x.shape)
            need(u.same(y,x),f'Saved selected.mat differs from actual wire: {k}')
    bix=np.flatnonzero(B['record_ready_log']['data'][:,0]==1)
    need(len(bix)==12 and u.same(sraw[:8],B['record_log']['data'][bix][4:12]) and
         u.same(scodes[:8],B['code_log']['data'][bix,0][4:12]) and
         u.same(stimes[:8],B['record_log']['time'][bix][4:12]),
         'Same-P same-graph N8 first eight RAW/code/time bits differ.')

    with h5py.File(RUN/'spectrum.mat','r') as f:
        power=np.asarray(u.val(f,'metrics/power_v2')).ravel()
        freq=np.asarray(u.val(f,'metrics/frequency_hz')).ravel()
        saved={k:float(u.val(f,'metrics/'+k)) for k in ('snr_db','sndr_db','sfdr_db','thd_db','enob')}
        hb=np.asarray(u.val(f,'metrics/harmonic_bins')).ravel().astype(int)
        need(int(u.val(f,'metrics/record_length'))==256 and int(u.val(f,'metrics/fundamental_bin'))==5 and
             float(u.val(f,'metrics/full_scale_diff_v'))==fsr,'Stored FFT metadata mismatch.')
    need(len(power)==len(freq)==129 and np.all(np.isfinite(power)) and np.all(power>=0) and
         np.array_equal(freq,np.arange(129)*fs/256),'Actual saved spectrum invalid.')
    v=((scodes+.5)/2**20-.5)*fsr;transform=np.fft.rfft(v-np.mean(v))/256
    independent=np.abs(transform)**2;independent[1:-1]*=2
    rel=np.max(np.abs(independent[1:]-power[1:])/np.maximum(power[1:],np.finfo(float).tiny))
    need(rel<1e-7,'Independently recomputed FFT differs from saved powers.')
    folded=np.minimum(np.mod(np.arange(2,11)*5,256),256-np.mod(np.arange(2,11)*5,256))
    need(len(np.unique(folded))==9 and not np.any(np.isin(folded,[0,5])) and
         np.array_equal(hb,folded),'H2-H10 harmonic collision or bin mismatch.')
    sig=independent[5];other=independent.copy();other[[0,5]]=0
    nd=float(np.sum(other));hp=float(np.sum(independent[folded]));noise=nd-hp
    need(sig>0 and nd>0 and noise>0 and hp>0,'Degenerate FFT metrics.')
    calc={'snr_db':float(10*np.log10(sig/noise)), 'sndr_db':float(10*np.log10(sig/nd)),
          'sfdr_db':float(10*np.log10(sig/np.max(other))), 'thd_db':float(10*np.log10(hp/sig))}
    calc['enob']=(calc['sndr_db']-1.76)/6.02
    need(all(abs(calc[k]-saved[k])<1e-8 for k in saved),'FFT metric does not independently agree.')
    need(np.all(power[1:]>0),'This run unexpectedly has zero-power non-DC bins.')
    reference=(fsr/2)**2/2;dbfs=10*np.log10(power[1:]/reference)
    ymin=math.floor(float(np.min(dbfs))/10)*10-5;ymax=math.ceil(float(np.max(dbfs))/10)*10+5
    need(np.all((dbfs>ymin)&(dbfs<ymax)),'Y limits crop a non-DC bin.')

    out.mkdir(parents=True,exist_ok=True)
    with (out/'spectrum_non_dc.csv').open('x',encoding='utf8',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(['bin','frequency_hz','saved_power_v2','single_bin_dbfs'])
        for k in range(1,129):writer.writerow([k,format(freq[k],'.17g'),format(power[k],'.17g'),format(dbfs[k-1],'.17g')])
    author_style.apply()
    fig,ax=plt.subplots(figsize=(146/25.4,4.85));fig.subplots_adjust(left=.15,right=.96,top=.77,bottom=.34)
    fig.text(.015,.977,'Fig. 7 context — actual single-bank behavioral spectrum',size=8,weight='bold',va='top')
    fig.text(.015,.942,'N=256 · Fs=5 MS/s · Fin=97.65625 kHz (bin 5) · input −1 dBFS',size=8,va='top')
    fig.text(.015,.907,'Noise and AZ OFF; behavioral model, not the paper’s 20k-point measurement.',size=7,va='top')
    fig.text(.015,.870,f"SNR {saved['snr_db']:.2f} dB  ·  SNDR {saved['sndr_db']:.2f} dB  ·  "
             f"SFDR {saved['sfdr_db']:.2f} dB  ·  THD {saved['thd_db']:.2f} dBc  ·  ENOB {saved['enob']:.2f} bit",
             size=7,va='top')
    x=freq[1:]/1e6
    ax.vlines(x,ymin,dbfs,color='#0072B2',linewidth=.65)
    ax.scatter(x,dbfs,color='#0072B2',s=3,zorder=3)
    ax.set_xlim(0,fs/2e6+.55*fs/256e6);ax.set_ylim(ymin,ymax);ax.set_xlabel('Frequency (MHz)')
    ax.set_ylabel('Single-bin power (dBFS)');ax.grid(True,alpha=.22,linewidth=.5)
    fig.text(.015,.235,'Rectangular window · one-sided bins 1–128 · DC excluded · H2–H10 separated for SNR',size=6.5)
    fig.text(.015,.209,'P: A0=10000 · UGB=1.2 GHz · Cf=0.864 pF · sample/DAC tau=0 · guard=0',size=6.5)
    footer=[('SLX',PINS['model.slx']),('P-used',PINS['N256_P_used.mat']),
            ('Source ZIP',PINS['source.zip']),('Actual simout',PINS['N256_simout.mat'])]
    for i,(name,digest) in enumerate(footer):fig.text(.015,.174-i*.026,f'{name} SHA256: {digest}',size=6,ha='left',va='center')
    author_style.finish(fig)
    for ext in ('png','pdf','svg'):fig.savefig(out/f'fig07_behavior_n256.{ext}',dpi=400,facecolor='white')
    plt.close(fig)
    report={'schema':'sar20-independent-n256-review/v1','source_sha256':PINS,
      'P0_matches_N8_P_values_and_field_order':True,'full_P_changed_paths_and_saved_values':changed,
      'all_P_diff_mat_values_checked':True,'single_bank_plan':'264 rows of 1..8; first 32 match prior P',
      'configuration':cfg,'actual_event_rows':len(ev),'actual_cycles':ncyc,'event_groups_per_cycle':ng,
      'actual_event_time_and_id_bits_match_calendar':True,'scheduled_events_per_cycle':budget,
      'physical_feedback_counter':'UNOBSERVED_DEBUG_OFF',
      'actual_RAW_count':len(ix),'actual_RAW_ID_range':[0,259],'selected_count':len(scodes),
      'selected_ID_range':[4,259],'selected_and_observed_record_wires_bit_equal':True,
      'first_eight_N8_raw_code_time_bit_equal':True,'first_eight_actual_codes':scodes[:8].astype(int).tolist(),
      'endpoint_code_count':int(np.count_nonzero((scodes==0)|(scodes==2**20-1))),
      'saved_metrics':saved,'independent_fft_metrics':calc,'max_nonDC_relative_power_delta':float(rel),
      'spectrum_scope':{'total_bins':129,'plotted_nonDC_bins':128,'zero_power_nonDC_bins':0,
         'frequency_hz_range':[float(freq[1]),float(freq[-1])],
         'bin_dbfs_range':[float(np.min(dbfs)),float(np.max(dbfs))],'y_limits_dbfs':[ymin,ymax],
         'full_scale_sine_power_v2':reference,'DC_power_v2_excluded':float(power[0]),
         'normalization':'DC-removed code-centre voltage, rectangular FFT; single-sided bin power divided by (FSRdiff/2)^2/2',
         'harmonic_bins_H2_to_H10':folded.tolist(),'enob':'(SNDR-1.76)/6.02; no amplitude correction'},
      'limitations':['256-point actual behavioral run, not the paper 20k-point silicon spectrum.',
         'Noise/AZ off; no yield, nonideality sweep, linearity or PDK signoff.',
         '12/8/7 counts are calendar tokens; physical feedback counter is not observed.',
         'Return charge not directly observed in these N256 logs.'],
      'plot_script_sha256':sha(Path(__file__)),'style_helper_sha256':sha(STYLE),
      'outputs_sha256':{p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file()}}
    (out/'independent_review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Saved',out,'; independent metrics',calc,'; non-DC range',float(min(dbfs)),float(max(dbfs)))

if __name__=='__main__':main()
