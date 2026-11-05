#!/usr/bin/env python3
"""Plot the actual same-FSR10 normal and added-NI-off N256 spectra.

Read-only MAT/CSV verification and plotting only; no MATLAB or model execution.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,sys
from pathlib import Path
sys.dont_write_bytecode=True
import h5py,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
RUN=HERE/'windows_main_actual'
READER=ROOT/'analysis/behavior/finite_dac_review_20261028/verify_as_run.py'
STYLE=ROOT/'analysis/behavior/single_bank_1039_20261104/figures/fig01_02_actual_n8_20261104/author_style.py'
sys.path.insert(0,str(READER.parent));import verify_as_run as u
sys.path.insert(0,str(STYLE.parent));import author_style
PINS={
 'normal':{'P_used.mat':'14e24420b15bdf89cacec3af91fb1f29ccf51ae7166e6cd2673e6119e3120c50',
   'simout.mat':'ae7fe4a36606bb08796cf734c9769cfb222adcaa85a02ebb71bf41c5902b4540',
   'selected.mat':'250008db50e34e42a23e85fa89fb771249244d17aad81fe793b967594dc82bfe',
   'spectrum.mat':'afc638378fb8458c5fe9c5b1cf58b9f58bb076e3cdb6b2ff8f9637e782ce12ec',
   'public_records.csv':'450c0cf2c7607c99507de608f5839c0ea4515b2aee3c4d104bc3522ec8770134',
   'complete.json':'b3b99d78b86f45a700bf0d2e60b1cf42eb4630319026971e625bae7760a1ca3c'},
 'baseline':{'P_used.mat':'c018907732a2bd03424458d209d3b464f1d26df110879f04aaaa06c443fa8fc4',
   'simout.mat':'d46d95ed7fc5cbab2b1bcc29e374c0980a45ba16888d7d0683d9223a6cdda3ce',
   'selected.mat':'fa9da404629966190a4264d4ad3a7d7fa4d5135a83cf5a67dc6fb8ab39d13844',
   'spectrum.mat':'999b5bd562ec0bf8549001fbe2ee275214126c889b5436dd19c8d70edd743655',
   'public_records.csv':'2d6beff0bb80e1b46af743ee3002908dce0a025d0fa4c9ec7106372dde73d87a',
   'complete.json':'59b17b05c0317997b0f113115f84f2d307cfdac74dcaad8ccfb96c8e93887067'},
 'model':'48537818b3212e1e4c8231dec433d1fde36d95814cdcce8c529bb2898eb097d3',
 'source_manifest':'73867eabe50b70920cd3373190832e2d78426c59b0116d6062ff94c4c903f14c',
 'dynamic_review':'fe34b72d834dd7a5941e95b1b36f5f18dd6afdfabbbee8ce530775a108b1881e',
 'reader':'3ca8dc8a6f553e75466438a0d74b9bf6a0a6ab5f65b8c151429981af330f7467'}
BLUE='#0072B2';ORANGE='#D55E00'
def need(v,m):
    if not v:raise ValueError(m)
def sha(p):
    need(p.is_file() and not p.is_symlink() and p.stat().st_size<=300_000_000,f'bad/missing/>300 MB {p}')
    h=hashlib.sha256()
    with p.open('rb') as f:
        for c in iter(lambda:f.read(1048576),b''):h.update(c)
    return h.hexdigest()
def run_case(label,folder):
    for name,pin in PINS[label].items():need(sha(folder/name)==pin,f'{label} input SHA {name}')
    receipt=json.loads((folder/'complete.json').read_text())
    for name,field in [('P_used.mat','P_used_sha256'),('simout.mat','simout_sha256'),
      ('selected.mat','selected_sha256'),('spectrum.mat','spectrum_sha256'),('public_records.csv','public_records_sha256')]:
        need(receipt[field]==PINS[label][name],f'{label} receipt binding {name}')
    need(receipt['model_sha256']==PINS['model'] and receipt['candidate_manifest_sha256']==PINS['source_manifest'],
         f'{label} model/source receipt mismatch')
    with h5py.File(folder/'P_used.mat') as f:
        v=lambda k:u.val(f,'P/'+k)
        config={'N':int(v('N')),'fs_hz':float(v('fs_hz')),'fsr_diff_v':float(v('fsr_diff_v')),
          'vref_v':float(v('front/vref_v')),'fin_hz':float(v('input/frequency_hz')),
          'input_peak_v':float(v('input/amplitude_v')),'input_phase_rad':float(v('input/phase_rad')),
          'period_s':float(v('Ts_s')),'A0':float(v('backend/ra/A0')),'UGB_hz':float(v('backend/ra/UGB_hz')),
          'sample_ktc':bool(v('front/ktc_enabled')),'cap_mismatch':bool(v('front/mismatch_enabled')),
          'ra_noise':bool(v('backend/ni/ra_noise')),'comparator_noise':bool(v('ni/comparator_noise')),
          'az':bool(v('backend/ni/az')),'jitter':bool(v('front/jitter/enabled')),
          'observer_adi':bool(v('debug/adi_enabled')),'calibration_mode':v('digital/calibration_mode')}
        offsets,_,_=u.read_calendar(f)
    need(config['N']==256 and config['fs_hz']==5e6 and config['fsr_diff_v']==10 and config['vref_v']==5 and
      config['fin_hz']==97656.25 and config['A0']==10000 and config['UGB_hz']==1.2e9 and
      not config['jitter'] and not config['observer_adi'] and config['calibration_mode']=='off',f'{label} configuration')
    flags=[config[k] for k in ('sample_ktc','cap_mismatch','ra_noise','comparator_noise','az')]
    need(all(flags) if label=='normal' else not any(flags),f'{label} NI flags')
    L=u.read_logs(folder/'simout.mat');e=L['event_log']['data'];t=L['event_log']['time'];ncyc=260
    need(np.array_equal(e,np.column_stack((np.repeat(np.arange(ncyc),48),np.tile(np.arange(1,49),ncyc)))) and
      u.same(t,np.repeat(np.arange(ncyc)*config['period_s'],48)+np.tile(offsets,ncyc)),f'{label} event calendar')
    for key in ('record_log','record_ready_log','code_log'):
        need(u.same(t,L[key]['time']),f'{label} time axis {key}')
    ix=np.flatnonzero(L['record_ready_log']['data'][:,0]==1);raw=L['record_log']['data'][ix];code=L['code_log']['data'][ix,0]
    need(len(ix)==260 and np.array_equal(raw[:,3],np.arange(260)) and np.all(raw[:,4:]==1),f'{label} actual RAW')
    raw=raw[4:];code=code[4:];times=t[ix][4:]
    need(len(code)==256 and np.all((code>=0)&(code<2**20)) and np.all(code==np.floor(code)),f'{label} codes')
    with h5py.File(folder/'selected.mat') as f:
        for key,val in [('raw',raw),('code20',code),('time_s',times)]:
            need(u.same(np.asarray(u.val(f,'selected/'+key)).reshape(val.shape),val),f'{label} selected {key}')
    with (folder/'public_records.csv').open(newline='',encoding='utf8') as f:records=list(csv.DictReader(f))
    need(len(records)==256 and all(int(x['ID'])==int(raw[i,3]) and int(x['code20'])==int(code[i]) and
      float(x['time_s'])==times[i] for i,x in enumerate(records)),f'{label} public CSV differs')
    with h5py.File(folder/'spectrum.mat') as f:
        power=np.asarray(u.val(f,'metrics/power_v2')).ravel();freq=np.asarray(u.val(f,'metrics/frequency_hz')).ravel()
        metrics={k:float(u.val(f,'metrics/'+k)) for k in ('snr_db','sndr_db','sfdr_db','thd_db','enob')}
        need(int(u.val(f,'metrics/record_length'))==256 and int(u.val(f,'metrics/fundamental_bin'))==5 and
          float(u.val(f,'metrics/full_scale_diff_v'))==10,f'{label} FFT metadata')
    need(len(power)==len(freq)==129 and np.all(power[1:]>0) and np.all(np.isfinite(power)) and
      np.array_equal(freq,np.arange(129)*5e6/256),f'{label} FFT bins')
    x=((code+.5)/2**20-.5)*10;y=np.fft.rfft(x-x.mean())/256;test=np.abs(y)**2;test[1:-1]*=2
    rel=float(np.max(np.abs(test[1:]-power[1:])/power[1:]));need(rel<1e-7,f'{label} independent FFT powers')
    sig=test[5];other=test.copy();other[[0,5]]=0;nd=float(other.sum());hp=float(test[np.arange(2,11)*5].sum())
    independent={'snr_db':float(10*np.log10(sig/(nd-hp))),'sndr_db':float(10*np.log10(sig/nd)),
      'sfdr_db':float(10*np.log10(sig/max(other))),'thd_db':float(10*np.log10(hp/sig))}
    independent['enob']=(independent['sndr_db']-1.76)/6.02
    need(all(abs(independent[k]-metrics[k])<1e-8 for k in metrics),f'{label} independent FFT metrics')
    return {'config':config,'freq':freq,'power':power,'metrics':metrics,'independent':independent,
      'max_relative_power_difference':rel,'code_range':[int(np.min(code)),int(np.max(code))]}
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True,type=Path);a=ap.parse_args();out=a.out.resolve()
    need(not out.exists() or out.is_dir(),'output path invalid')
    for name in ('normal_fft256.png','normal_fft256_bins.csv','normal_fft256_metadata.json'):
        need(not (out/name).exists(),f'refuse overwrite {name}')
    model=ROOT/'analysis/behavior/single_bank_1039_20261104/graph_v2/SarAdc.slx'
    manifest=ROOT/'analysis/behavior/merged_ou_rc_20261104_toyFVb/candidate/MANIFEST.json'
    for key,p in [('model',model),('source_manifest',manifest),('dynamic_review',HERE/'DYNAMIC_ACTUAL_256.json'),('reader',READER)]:
        need(sha(p)==PINS[key],f'{key} SHA mismatch')
    base=run_case('baseline',RUN/'ideal_merged_n256');normal=run_case('normal',RUN/'normal_merged_n256')
    for key in ('fs_hz','fsr_diff_v','fin_hz','input_peak_v','input_phase_rad','A0','UGB_hz'):
        need(base['config'][key]==normal['config'][key],f'baseline/normal input identity {key}')
    need(np.array_equal(base['freq'],normal['freq']),'different FFT grids')
    review=json.loads((HERE/'DYNAMIC_ACTUAL_256.json').read_text())
    for label,data in [('ideal_merged_n256',base),('normal_merged_n256',normal)]:
        for k,v in data['metrics'].items():need(abs(v-review[label]['metrics'][k])<1e-8,f'{label} review {k}')
    ref=(10/2)**2/2;fb=base['freq'][1:];db=10*np.log10(base['power'][1:]/ref);dn=10*np.log10(normal['power'][1:]/ref)
    all_db=np.r_[db,dn];bottom=math.floor(float(np.min(all_db))/10)*10-5;top=math.ceil(float(np.max(all_db))/10)*10+5
    need(np.all((all_db>bottom)&(all_db<top)),'display crops bins')
    out.mkdir(parents=True,exist_ok=True);table=out/'normal_fft256_bins.csv'
    with table.open('x',encoding='utf8',newline='') as f:
        w=csv.writer(f);w.writerow(['bin','frequency_hz','baseline_power_v2','baseline_dbfs','normal_power_v2','normal_dbfs'])
        for i in range(128):w.writerow([i+1,format(fb[i],'.17g'),format(base['power'][i+1],'.17g'),format(db[i],'.17g'),
                                       format(normal['power'][i+1],'.17g'),format(dn[i],'.17g')])
    author_style.apply();fig,ax=plt.subplots(figsize=(146/25.4,5.15));fig.subplots_adjust(left=.15,right=.96,top=.76,bottom=.34)
    fig.text(.015,.979,'估算正常工作点：N256 实际模型频谱对照',fontname='PingFang SC',size=9,weight='bold',va='top')
    fig.text(.015,.946,'Fs 5 MS/s · Fin 97.65625 kHz (bin 5) · input −1 dBFS · FSRdiff 10 V',size=7,va='top')
    fig.text(.015,.915,'Calibration / physical ADI OFF · estimated parameters, not foundry-typical or silicon data',size=7,va='top')
    fig.text(.015,.883,f"Added-NI-off baseline: SNDR {base['metrics']['sndr_db']:.2f} dB, SFDR {base['metrics']['sfdr_db']:.2f} dB",
             size=7,color=BLUE,va='top')
    fig.text(.015,.853,f"Normal assumptions: SNDR {normal['metrics']['sndr_db']:.2f} dB, SFDR {normal['metrics']['sfdr_db']:.2f} dB",
             size=7,color=ORANGE,va='top')
    freq=fb/1e6
    ax.scatter(freq,db,s=11,marker='o',facecolors='none',edgecolors=BLUE,linewidths=.7,label='Added-NI-off baseline')
    ax.scatter(freq,dn,s=9,marker='x',color=ORANGE,linewidths=.7,label='Estimated normal NI ON')
    ax.set_xlim(0,2.5+.55*5e6/256e6);ax.set_ylim(bottom,top);ax.set_xlabel('Frequency (MHz)')
    ax.set_ylabel('Single-bin power (dBFS)');ax.grid(True,alpha=.2);ax.legend(loc='upper right',frameon=False,fontsize=6.5)
    fig.text(.015,.245,'128 actual non-DC bins each · rectangular one-sided FFT · RA A0=10000, UGB=1.2 GHz in both',size=6.4)
    fig.text(.015,.221,'Normal: kT/C, C mismatch, RA OU, SAR2/TA CMP noise, RC/DAC and ordinary AZ; jitter OFF',size=6.4)
    footer=[('SLX',PINS['model']),('Source manifest',PINS['source_manifest']),
      ('Baseline simout',PINS['baseline']['simout.mat']),('Normal simout',PINS['normal']['simout.mat'])]
    for i,(name,v) in enumerate(footer):fig.text(.015,.188-.025*i,f'{name} SHA256: {v}',size=6,va='center')
    author_style.finish(fig);png=out/'normal_fft256.png';fig.savefig(png,dpi=400,facecolor='white');plt.close(fig)
    meta={'schema':'normal-fft256-two-actual-runs/v1','input_sha256':PINS,
      'baseline_configuration':base['config'],'normal_configuration':normal['config'],
      'baseline_metrics_native':base['metrics'],'normal_metrics_native':normal['metrics'],
      'baseline_metrics_independent':base['independent'],'normal_metrics_independent':normal['independent'],
      'max_relative_power_error':{'baseline':base['max_relative_power_difference'],'normal':normal['max_relative_power_difference']},
      'one_sided_nonDC_bins_each':128,'full_scale_sine_power_v2':ref,'y_limits_dbfs':[bottom,top],
      'baseline_dbfs_range':[float(np.min(db)),float(np.max(db))],
      'normal_dbfs_range':[float(np.min(dn)),float(np.max(dn))],
      'scope':['Actual code spectra, one 256-point record per case; not paper FFT or silicon measurement.',
        'Baseline retains finite A0/UGB and other inherited modeled behavior; it is not a fully ideal converter.',
        'Normal model parameters are estimates; not PDK-typical or foundry data. Comparator noise is SAR2/TA only.',
        'P was saved/injected; runtime dialog was not independently probed.',
        'Calibration and physical ADI are off; no noise-population, DNL/INL or signoff conclusion.'],
      'plot_script_sha256':sha(Path(__file__)),'style_helper_sha256':sha(STYLE),
      'outputs_sha256':{png.name:sha(png),table.name:sha(table)}}
    (out/'normal_fft256_metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('Saved',out,'baseline SNDR',base['metrics']['sndr_db'],'normal SNDR',normal['metrics']['sndr_db'])
if __name__=='__main__':main()
