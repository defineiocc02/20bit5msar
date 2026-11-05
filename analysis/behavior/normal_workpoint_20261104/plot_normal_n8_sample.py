#!/usr/bin/env python3
"""Plot one actual normal N8 sample from saved event logs; no MATLAB execution."""
from __future__ import annotations
import argparse,csv,hashlib,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
import h5py,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
RUN=HERE/'windows_main_actual/normal_merged_n8_tap'
READER=ROOT/'analysis/behavior/finite_dac_review_20261028/verify_as_run.py'
STYLE=ROOT/'analysis/behavior/single_bank_1039_20261104/figures/fig01_02_actual_n8_20261104/author_style.py'
sys.path.insert(0,str(READER.parent));import verify_as_run as u
sys.path.insert(0,str(STYLE.parent));import author_style
PINS={'P':'f64746e06a0c76a64290cd8eb0fda73ba904c03b91d97da619fa0be52faee0fb',
 'simout':'be907306df49f21798dac118fc65f6b77aa38cd2bef3aa37a5d07d0d9110759f',
 'complete':'108430f70f5517df02953b8f8c4bbb487bb8c7c3d5627fe4f1af9d980f0cb6f8',
 'model':'48537818b3212e1e4c8231dec433d1fde36d95814cdcce8c529bb2898eb097d3',
 'source_manifest':'73867eabe50b70920cd3373190832e2d78426c59b0116d6062ff94c4c903f14c',
 'assumptions':'a93a899e9c914cdfcfc01bb3b334c4d86875f7eb20d84552328993c996e2ea47',
 'cmp_audit':'e028373b03109f55dd73d1c14dd918f3c18c190e418a66e522b59e0d9c8b96f2',
 'reader':'3ca8dc8a6f553e75466438a0d74b9bf6a0a6ab5f65b8c151429981af330f7467'}
BLUE='#0072B2';ORANGE='#D55E00';GREEN='#009E73';RED='#B2182B';GREY='#777777'
def need(x,m):
    if not x:raise ValueError(m)
def sha(p):
    need(p.is_file() and not p.is_symlink() and p.stat().st_size<=300_000_000,f'bad/missing/>300 MB: {p}')
    h=hashlib.sha256()
    with p.open('rb') as f:
        for c in iter(lambda:f.read(1048576),b''):h.update(c)
    return h.hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True,type=Path);a=ap.parse_args();out=a.out.resolve()
    need(not out.exists() or (out.is_dir() and not any(out.iterdir())),'output must be new or empty')
    files={'P':RUN/'P_used.mat','simout':RUN/'simout.mat','complete':RUN/'complete.json',
      'model':ROOT/'analysis/behavior/single_bank_1039_20261104/graph_v2/SarAdc.slx',
      'source_manifest':ROOT/'analysis/behavior/merged_ou_rc_20261104_toyFVb/candidate/MANIFEST.json',
      'assumptions':HERE/'windows_gate_asrun/profile/assumptions.mat',
      'cmp_audit':HERE/'review/normal_n8_cmp_audit.json','reader':READER}
    for key,path in files.items():need(sha(path)==PINS[key],f'hash mismatch {key}')
    receipt=json.loads((RUN/'complete.json').read_text());need(receipt['P_used_sha256']==PINS['P'] and
      receipt['simout_sha256']==PINS['simout'] and receipt['candidate_manifest_sha256']==PINS['source_manifest'] and
      receipt['model_sha256']==PINS['model'],'receipt input binding')
    L=u.read_logs(files['simout']);e=L['event_log']['data'];t=L['event_log']['time'];sample=5
    need(np.array_equal(e,np.column_stack((np.repeat(np.arange(12),48),np.tile(np.arange(1,49),12)))),
      'event sequence is not 12×48')
    for name in ('front_log','back_log','control_log','adi_wire_log','aperture_log','raw_log','ready_log','code_log'):
        need(u.same(t,L[name]['time']),f'event/log axis mismatch {name}')
    ix=np.flatnonzero(e[:,0]==sample);need(len(ix)==48,'sample event count')
    with h5py.File(files['P'],'r') as h:
        g=lambda k:u.val(h,'P/'+k);offsets,groups,budget=u.read_calendar(h)
        ts=float(g('Ts_s'));need(u.same(t,np.repeat(np.arange(12)*ts,48)+np.tile(offsets,12)),
                                'actual times differ from saved event calendar')
        cfg={'fs_hz':float(g('fs_hz')),'fsr_diff_v':float(g('fsr_diff_v')),
          'vref_v':float(g('front/vref_v')),'input_frequency_hz':float(g('input/frequency_hz')),
          'input_amplitude_v':float(g('input/amplitude_v')),'input_phase_rad':float(g('input/phase_rad')),
          'temperature_K':float(g('front/temperature_K')),'A0':float(g('backend/ra/A0')),
          'UGB_hz':float(g('backend/ra/UGB_hz')),'ra_ou_sigma_vx_v':float(g('backend/ra_noise/sigma_vx_rms')),
          'comparator_sigma_vy_v':float(g('control/comparator/sar2_noise_rms_v')),
          'sample_tau_s':float(np.asarray(g('front/tau_sample_s')).ravel()[0]),
          'dac_tau_s':float(np.asarray(g('front/tau_dac_s')).ravel()[0]),
          'az_write_tau_s':float(np.asarray(g('backend/az/write_tau_s')).ravel()[0]),
          'az_hold_tau_s':float(np.asarray(g('backend/az/leak_tau_s')).ravel()[0]),
          'guard_s':float(g('front/single_guard_s')),'sample_ktc_on':bool(g('front/ktc_enabled')),
          'cap_mismatch_on':bool(g('front/mismatch_enabled')),'az_mode':g('backend/az/mode'),
          'comparator_on':bool(g('control/comparator/enabled')),'ra_ou_on':bool(g('backend/ni/ra_noise')),
          'jitter_on':bool(g('front/jitter/enabled')),'calibration_mode':g('digital/calibration_mode'),
          'observer_adi_wire_on':bool(g('debug/adi_enabled'))}
        need(cfg['fs_hz']==5e6 and cfg['fsr_diff_v']==10 and cfg['vref_v']==5 and
          cfg['input_frequency_hz']==97656.25 and cfg['temperature_K']==298.15 and cfg['guard_s']==2e-9 and
          cfg['sample_ktc_on'] and cfg['cap_mismatch_on'] and cfg['comparator_on'] and cfg['ra_ou_on'] and
          cfg['observer_adi_wire_on'] and not cfg['jitter_on'] and cfg['az_mode']=='ordinary' and
          cfg['calibration_mode']=='off','unexpected normal P')
    with h5py.File(files['assumptions'],'r') as h:
        cfg['cap_unit_relative_sigma_assumed']=float(u.val(h,'assumptions/unit_relative_sigma'))
    need(abs(cfg['cap_unit_relative_sigma_assumed']-0.0006804138)<1e-10,'unit mismatch assumption')
    def which(token):return [int(i) for i in ix if token in groups[int(e[i,1])-1]]
    cnv=which('cnv');ra=which('ra_start');d2=which('d2_decide');ta=which('ta_compare');
    tafb=which('ta_feedback');raw=which('raw_latch');release=which('release')
    need(tuple(map(len,(cnv,ra,d2,ta,tafb,raw,release)))==(1,1,12,8,7,1,1),'event inventory')
    tc=float(t[cnv[0]]);tr=float(t[raw[0]]);tl=float(t[release[0]]);next_open=tl+cfg['guard_s']
    need(abs(tc-1e-6)<1e-20 and abs(tr-1.08625e-6)<1e-20 and abs(tl-1.09e-6)<1e-20 and
      abs(next_open-1.092e-6)<1e-20,'unexpected absolute timing')
    apdata=L['aperture_log']['data'];next_cnv=np.flatnonzero((e[:,0]==6)&(e[:,1]==1))[0]
    need(np.all(apdata[next_cnv,20:28]==apdata[next_cnv,20]) and
         abs(apdata[next_cnv,20]-next_open)<1e-18,'derived next open versus saved metadata')
    ctrl=L['control_log']['data'];back=L['back_log']['data'];front=L['front_log']['data'];w=L['adi_wire_log']['data']
    need(np.array_equal(w[raw[0],51:54],[12,8,7]),'next-wire counts mismatch')
    d2bits=[(int(ctrl[i,5])>>(11-j))&1 for j,i in enumerate(d2)]
    tabits=[(int(ctrl[i,6])>>(7-j))&1 for j,i in enumerate(ta)]
    rawword=L['raw_log']['data'][raw[0]];code=int(L['code_log']['data'][raw[0],0])
    need(np.array_equal(rawword,[1924,2473,19,5,1,1]) and code==979623 and
      sum(bit<<(11-j) for j,bit in enumerate(d2bits))==2473 and
      sum(bit<<(7-j) for j,bit in enumerate(tabits))==19,'actual RAW/bit/code mismatch')
    audit=json.loads(files['cmp_audit'].read_text());need(audit['pins_sha256']['simout']==PINS['simout'],
      'comparator audit belongs to a different run')
    for label,inds,bits in [('d2_decide',d2,d2bits),('ta_compare',ta,tabits)]:
        observed=[x for x in audit['rows'] if x['sample_id']==sample and x['event_type']==label]
        need(len(observed)==len(inds) and all(int(z['group'])==int(e[i,1]) and int(z['actual_bit'])==bit
             for z,i,bit in zip(observed,inds,bits)),'independent actual comparator-bit audit mismatch')
    d2flip=[int(bit!=(back[i,1]>=0)) for i,bit in zip(d2,d2bits)]
    taflip=[int(bit!=(back[i,1]>=0)) for i,bit in zip(ta,tabits)]
    need(sum(d2flip)==1 and sum(taflip)==2,'unexpected sign comparisons')
    ns=(t-tc)*1e9;evrows=[]
    for i in ix:
        tokens=groups[int(e[i,1])-1];didx=d2.index(i) if i in d2 else None;tidx=ta.index(i) if i in ta else None
        evrows.append({'sample_id':5,'event_group':int(e[i,1]),'t_abs_s':format(t[i],'.17g'),
          't_from_cnv_ns':format(ns[i],'.17g'),'event_tokens':';'.join(tokens),
          'vres_v':format(front[i,1],'.17g'),'vx_v':format(back[i,0],'.17g'),'vy_v':format(back[i,1],'.17g'),
          'D2_word_next':int(ctrl[i,5]),'DT_word_next':int(ctrl[i,6]),
          'D2_decision_bit_next':'' if didx is None else d2bits[didx],
          'TA_decision_bit_next':'' if tidx is None else tabits[tidx],
          'bit_differs_from_vy_sign':'' if didx is None and tidx is None else d2flip[didx] if didx is not None else taflip[tidx],
          'D2_count_next':int(w[i,51]),'TA_compare_count_next':int(w[i,52]),'TA_feedback_count_next':int(w[i,53])})
    out.mkdir(parents=True,exist_ok=True);csvpath=out/'normal_n8_sample5_events.csv'
    with csvpath.open('x',encoding='utf8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(evrows[0]));writer.writeheader();writer.writerows(evrows)
    author_style.apply();fig,(ax1,ax2,ax3)=plt.subplots(3,1,figsize=(146/25.4,7.65),
      gridspec_kw={'height_ratios':[1.1,.72,1]});fig.subplots_adjust(left=.17,right=.96,top=.85,bottom=.27,hspace=.48)
    fig.text(.015,.982,'正常工作点（估算）行为仿真：关键节点与判决（ID 5）',fontname='PingFang SC',size=9,weight='bold',va='top')
    fig.text(.015,.954,'FSRdiff 10 V · Vref 5 V · Fs 5 MS/s · Fin 97.65625 kHz · input −1 dBFS',size=7,va='top')
    fig.text(.015,.929,'Event endpoints only; connecting lines are guides. Control/counters are next wires, not committed state.',size=7,va='top')
    fig.text(.015,.905,'Comparator noise ON: * means actual decision differs from sign(VY); no internal effective input probe.',size=7,va='top')
    ax1.plot(ns[ix],front[ix,1]*1e3,color=GREEN,ls='--',lw=.7,marker='o',markersize=1.8,label='Vres: FE event')
    ax1.plot(ns[ix],back[ix,0]*1e3,color=ORANGE,ls='--',lw=.7,marker='o',markersize=1.8,label='VX: RA event')
    ax1.plot(ns[ix],back[ix,1]*1e3,color=BLUE,ls='--',lw=.7,marker='s',markersize=1.8,label='VY: pre-decision')
    for x in (ns[ra[0]],ns[raw[0]],ns[release[0]],(next_open-tc)*1e9):ax1.axvline(x,color='#b0b0b0',lw=.5,ls=':')
    ax1.set_xlim(-2,95);ax1.set_ylabel('Node value (mV)');ax1.set_xlabel('Time from CNV (ns)');ax1.grid(True,alpha=.2)
    ax1.legend(loc='lower right',frameon=False,fontsize=6.5,ncol=3)
    ax1.text(-.075,1.02,'(a)',transform=ax1.transAxes,va='bottom',size=7,clip_on=False)
    sec=ax1.secondary_xaxis('top',functions=(lambda ns:(tc+ns*1e-9)*1e6,lambda us:(us*1e-6-tc)*1e9))
    sec.set_xlabel('Absolute time (µs)',labelpad=2);sec.xaxis.set_major_formatter(FormatStrFormatter('%.3f'))
    ax2.scatter(ns[d2],d2bits,color=BLUE,s=15,zorder=3)
    for i,bit,flip in zip(d2,d2bits,d2flip):
        ax2.annotate(str(bit)+('*' if flip else ''),(ns[i],bit),xytext=(0,5 if bit else -10),
          textcoords='offset points',ha='center',size=7,color=RED if flip else 'black')
    ax2.set_xlim(43.5,74);ax2.set_ylim(-.32,1.32);ax2.set_yticks([0,1]);ax2.set_ylabel('D2 bit next')
    ax2.set_xlabel('Time from CNV (ns)');ax2.grid(True,alpha=.2)
    ax2.text(0,1.08,'(b) 12 D2 decisions · final D2 = 2473 (100110101001)',transform=ax2.transAxes,va='bottom',size=7)
    yy=back[ta,1]*1e6;ax3.plot(ns[ta],yy,color=BLUE,ls='--',lw=.7,marker='s',markersize=3,label='VY at TA compare')
    for x,y,bit,flip in zip(ns[ta],yy,tabits,taflip):
        ax3.annotate(str(bit)+('*' if flip else ''),(x,y),xytext=(0,6),textcoords='offset points',
          ha='center',size=7,color=RED if flip else 'black')
    ymin=min(-400.,float(np.min(yy))-150);ymax=max(700.,float(np.max(yy))+190)
    ax3.axhline(0,color='black',lw=.5);ax3.scatter(ns[tafb],np.full(7,ymin+40),marker='|',s=55,color=ORANGE,label='7 feedback events')
    ax3.set_ylim(ymin,ymax);ax3.set_xlim(74.5,84.5);ax3.set_ylabel('VY at TA (µV)');ax3.set_xlabel('Time from CNV (ns)')
    ax3.legend(loc='upper right',frameon=False,fontsize=6.5);ax3.grid(True,alpha=.2)
    ax3.text(0,1.08,'(c) 8 TA decisions · final DT = 19 (00010011); 7 feedbacks',transform=ax3.transAxes,va='bottom',size=7)
    fig.text(.015,.205,'CNV 1.000000 µs · RAW 1.086250 µs · release 1.090000 µs · next open 1.092000 µs (derived)',size=6.5)
    fig.text(.015,.183,'RAW D1/D2/DT = 1924 / 2473 / 19 · reconstructed CODE20 = 979623',size=6.5)
    fig.text(.015,.161,'P: kT/C ON · unit σ 0.0680% assumed · RA OU σVX 0.5128 mV · comparator σVY 0.2869 mV',size=6.4)
    fig.text(.015,.139,'P: τsample 0.563 ns · τDAC 0.5 ns · AZ τwrite 1 ns / τleak 10 ms · cal/physical ADI/jitter OFF; tap ON',size=6.3)
    for i,(name,key) in enumerate([('SLX','model'),('Source manifest','source_manifest'),('P-used','P'),('Actual simout','simout')]):
        fig.text(.015,.112-.020*i,f'{name} SHA256: {PINS[key]}',size=6,va='center')
    author_style.finish(fig);png=out/'normal_n8_sample5.png';fig.savefig(png,dpi=400,facecolor='white');plt.close(fig)
    report={'schema':'normal-n8-sample5-event-figure/v1','source_sha256':PINS,'configuration_in_saved_P':cfg,
      'sample_id':5,'epoch':1,'cnv_s':tc,'raw_ready_s':tr,'release_s':tl,
      'next_open_s':next_open,'next_open_scope':'release + saved guard; also matches stored next-sample open metadata, not switch waveform',
      'raw':{'D1':1924,'D2':2473,'DT':19,'code20':code},'d2_bits_next':d2bits,'ta_bits_next':tabits,
      'd2_bit_vs_vy_sign_disagreement_count':sum(d2flip),'ta_bit_vs_vy_sign_disagreement_count':sum(taflip),
      'scheduled_and_next_wire_counts':[12,8,7],
      'source_scope':{'front_log':'FE_retobs event-stage Vres','back_log':'RA backend pre-decision event endpoints',
        'control_and_adi_wire':'observed next command/counter wires, not a direct committed-state history',
        'comparator_noise':'ON; decision bits taken from actual next words, not inferred from sign(VY)',
        'adi_wire':'observer ON only; no physical ADI architecture','config':'P injected for run; runtime dialog not independently probed'},
      'limitations':['One N8 model sample; no FFT, statistics, PDK or silicon claim.',
        'Normal component values are engineering assumptions, not foundry-typical measurements.',
        'No continuous CT waveform inferred; connecting lines are guides.',
        'Next sample open is derived from release+guard and cross-checked against saved state metadata.'],
      'plot_script_sha256':sha(Path(__file__)),'style_helper_sha256':sha(STYLE),
      'outputs_sha256':{png.name:sha(png),csvpath.name:sha(csvpath)}}
    (out/'normal_n8_sample5_metadata.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('Saved',out,'D2 bits',d2bits,'TA bits',tabits,'sign mismatches',sum(d2flip),sum(taflip))

if __name__=='__main__':main()
