#!/usr/bin/env python3
"""Render paper Fig.1/2-related plots from saved single-bank N8 event data.

No model, MATLAB, random-data generation, interpolation, or ADC simulation is
performed. Event names come from the saved calendar; times/voltages/words and
stage counters come from the actual tap simout. Run from any working directory:
  <project>/dependencies/analysis_env/bin/python plot_actual_n8.py --out NEW_DIR
Existing output files are never overwritten. Set --project if relocated.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,sys
from pathlib import Path
sys.dont_write_bytecode=True
import h5py,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import author_style
LIMIT=300_000_000
PINS={
 'model':'48537818b3212e1e4c8231dec433d1fde36d95814cdcce8c529bb2898eb097d3',
 'parameters':'9ea34cfd83187fff350ea266dabd79d377e48d99c292bba3fbbb4a84445b07e6',
 'simout':'df04c47373902db44a2082e5c5e6ade994cd9d4313735ff9a602c5b518cd4f28',
 'source_zip':'09e6c7c82635d8f6bf1cf4cc8e86f0ec42036524bfe6518dfcb37ea05fb06eb7',
 'source_manifest':'2cbdffe537b694cef6107ce893ea8bca7f8ef5d95f6ff7d993f020150c6dd514',
 'paper':'7ef975d3d689436880cc049296b68d44eec8c1063897041bb569f3f7017f9167',
 'reader':'3ca8dc8a6f553e75466438a0d74b9bf6a0a6ab5f65b8c151429981af330f7467',
}
BLUE='#0072B2'; ORANGE='#D55E00'; GREEN='#009E73'; BLACK='#1c1c1c'; GREY='#b7b7b7'


def need(value,message):
    if not value:raise ValueError(message)


def sha(path):
    path=Path(path);need(path.is_file() and not path.is_symlink() and path.stat().st_size<=LIMIT,f'missing/symlink/over 300 MB: {path}')
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def signed_bit(word,bit):return (int(word)>>bit)&1


def secondary_time(ax,t0):
    sec=ax.secondary_xaxis('top',functions=(lambda ns:(t0+ns*1e-9)*1e6,lambda us:(us*1e-6-t0)*1e9))
    sec.xaxis.set_major_formatter(FormatStrFormatter('%.3f'))
    sec.set_xlabel('Absolute time (µs)',labelpad=3)
    sec.tick_params(length=2,pad=1)
    return sec


def footer(fig,cfg):
    fig.text(.015,.149,f"P: single bank · A0={cfg['backend/ra/A0']:.0f} · UGB={cfg['backend/ra/UGB_hz']/1e9:.4g} GHz · Cf={cfg['backend/ra/Cf_f']*1e12:.4g} pF · guard=0",
             family='Arial',size=6.3,ha='left',va='center')
    fig.text(.015,.128,f"P: Fin={cfg['input/frequency_hz']/1e3:.6g} kHz · input peak={cfg['input/amplitude_v']:.6g} V · FSRdiff={cfg['fsr_diff_v']:.6g} V · tau sample/DAC=0 s",
             family='Arial',size=6.3,ha='left',va='center')
    lines=[('SLX',PINS['model']),('P-used',PINS['parameters']),('Source ZIP',PINS['source_zip']),('Actual simout',PINS['simout'])]
    for i,(label,value) in enumerate(lines):
        fig.text(.015,.105-i*.021,f'{label} SHA256: {value}',family='Arial',size=6.0,ha='left',va='center')


def title(fig,name,subtitle):
    fig.text(.015,.983,name,family='Arial',size=8,weight='bold',ha='left',va='top')
    fig.text(.015,.949,subtitle,family='Arial',size=8,ha='left',va='top')
    fig.text(.015,.918,'Event samples only; lines are visual guides, not simulated continuous waveforms.',
             family='Arial',size=7,ha='left',va='top')


def savefig(fig,out,stem):
    for ext in ('pdf','svg','png'):
        dest=out/f'{stem}.{ext}';need(not dest.exists(),f'refuse overwrite {dest}')
        fig.savefig(dest,dpi=400,facecolor='white')
    plt.close(fig)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--project',type=Path,default=HERE.parents[4])
    parser.add_argument('--out',required=True,type=Path);parser.add_argument('--sample-id',type=int,default=5)
    a=parser.parse_args();root=a.project.resolve();out=a.out.resolve();sample=a.sample_id
    need(4<=sample<=11,'Only actually recorded selected IDs 4..11 are supported')
    need(not out.exists() or (out.is_dir() and not any(out.iterdir())),'output directory must be new or empty')
    out.mkdir(parents=True,exist_ok=True)
    project=root/'analysis/behavior/single_bank_1039_20261104';tap=project/'n8_tap/tap'
    files={'model':project/'graph_v2/SarAdc.slx','parameters':tap/'P_used.mat','simout':tap/'simout.mat',
       'source_zip':project/'single_bank_1039_candidate_20261104_v2.zip','source_manifest':project/'MANIFEST_v2.json',
       'paper':root/'docs/PAPERS/01_CICC2026/A_3.6mW_5MS_s_100dB-SNDR_2-Step_SAR_ADC_with_Continuous-Time_Second-Stage_and_Tracking_Averaging.pdf',
       'reader':root/'analysis/behavior/finite_dac_review_20261028/verify_as_run.py'}
    for key,path in files.items():need(sha(path)==PINS[key],f'{key} SHA differs')
    sys.path.insert(0,str(files['reader'].parent));import verify_as_run as u
    L=u.read_logs(files['simout']);need(len(L)==32,'Unexpected actual timeseries inventory')
    with h5py.File(files['parameters'],'r') as h:
        v=lambda k:u.val(h,'P/'+k)
        times,groups,budget=u.read_calendar(h)
        cfg={k:v(k) for k in ('N','first_id','epoch','Ts_s','fs_hz','fsr_diff_v','input/frequency_hz','input/amplitude_v',
             'front/single_bank','front/single_guard_s','front/dem_enabled','front/dither_enabled','front/ktc_enabled',
             'front/jitter/enabled','front/mismatch_enabled','ni/comparator_noise','ni/reference_recovery','backend/ra/A0','backend/ra/UGB_hz','backend/ra/Cf_f','backend/ni/ra_noise','backend/ni/az','backend/ni/az_noise','backend/ni/reference_noise','backend/az/mode','control/sar1/coarse_noise_rms_v')}
        need(int(cfg['N'])==8 and int(cfg['epoch'])==1 and cfg['Ts_s']==200e-9 and int(cfg['front/single_bank'])==1,'Unexpected N8/single configuration')
        need(all(int(cfg[k])==0 for k in ('front/dem_enabled','front/dither_enabled','front/ktc_enabled','front/jitter/enabled','front/mismatch_enabled','ni/comparator_noise','ni/reference_recovery','backend/ni/ra_noise','backend/ni/az','backend/ni/az_noise','backend/ni/reference_noise')) and cfg['backend/az/mode']=='off' and cfg['control/sar1/coarse_noise_rms_v']==0 and cfg['front/single_guard_s']==0,'Unexpected enabled nonideality or guard')
        need(int(v('debug/adi_enabled'))==1 and int(v('debug/aperture_enabled'))==1,'Required actual tap disabled')
        for k in ('front/tau_sample_s','front/tau_precharge_s','front/tau_dac_s'):
            need(np.all(np.asarray(v(k))==0),'This figure requires stored ideal acquisition/DAC time constants')
    ev=L['event_log']['data'];te=L['event_log']['time'];expected=np.column_stack((np.repeat(np.arange(12),48),np.tile(np.arange(1,49),12)))
    need(np.array_equal(ev,expected) and len(te)==576,'Actual 12x48 event sequence differs')
    for name in ('front_log','back_log','control_log','raw_log','ready_log','record_log','record_ready_log','code_log','d1_log','d2_log','dt_log','adi_wire_log','aperture_log'):
        need(u.same(L[name]['time'],te),'Actual log axis differs: '+name)
    ix=np.flatnonzero(ev[:,0]==sample);need(len(ix)==48,'Actual sample is incomplete')
    f=L['front_log']['data'];b=L['back_log']['data'];c=L['control_log']['data'];w=L['adi_wire_log']['data'];aP=L['aperture_log']['data']
    tokens=[groups[int(ev[i,1])-1] for i in ix]
    one=lambda typ:[int(ix[j]) for j,ts in enumerate(tokens) if typ in ts]
    cnv=one('cnv');coarse=one('coarse_latch');fine=one('fine_decide');ra=one('ra_start');d2=one('d2_decide');d2fb=one('d2_feedback');ta=one('ta_compare');tafb=one('ta_feedback');ready=one('raw_latch');release=one('release')
    need(tuple(map(len,(cnv,coarse,fine,ra,d2,d2fb,ta,tafb,ready,release)))==(1,1,5,1,12,12,8,7,1,1),'Selected event token inventory differs')
    t0=float(te[cnv[0]]);ns=(te-t0)*1e9
    need(np.all(w[ix,:8]==np.arange(1,9)) and np.array_equal(w[ready[0],51:54],[12,8,7]),'Actual stage IDs/counters differ')
    ap=aP[cnv[0]];need(np.array_equal(ap[:3],[sample,1,1]) and np.array_equal(ap[4:12],np.arange(1,9)),'Actual aperture tags differ')
    need(u.same(ap[12:20],np.full(8,t0)),'Actual sampled apertures differ from CNV')
    open_s=float(ap[20]);need(np.all(ap[20:28]==open_s) and open_s<t0,'Invalid state-stored acquisition opening')
    raw=L['record_log']['data'][ready[0]];code=L['code_log']['data'][ready[0],0]
    need(np.array_equal(raw[3:],[sample,1,1]) and L['record_ready_log']['data'][ready[0],0]==1,'Actual RAW/ready invalid')
    final=[int(raw[0]),int(raw[1]),int(raw[2]),int(code)]
    dbits=[];tbits=[]
    for j,i in enumerate(d2):
        bit=signed_bit(c[i,5],11-j);vy=float(b[i,1]);need(vy!=0 and bit==int(vy>0),'D2 actual nonzero VY/bit mismatch');dbits.append(bit)
    for j,i in enumerate(ta):
        bit=signed_bit(c[i,6],7-j);vy=float(b[i,1]);need(vy!=0 and bit==int(vy>0),'TA actual nonzero VY/bit mismatch');tbits.append(bit)
    need(int(raw[1])==sum(x<<(11-j) for j,x in enumerate(dbits)) and int(raw[2])==sum(x<<(7-j) for j,x in enumerate(tbits)),'Registered word differs from observed decisions')
    print('Actual selected sample',sample,'tCNV',t0,'RAW D1/D2/DT/code',final,'TA bits',tbits)
    # Preserve numeric binary64 values with 17 significant digits; no resampling.
    events=[]
    for j,i in enumerate(ix):
        events.append({'sample_id':sample,'epoch':1,'group':int(ev[i,1]),'time_abs_s':format(float(te[i]),'.17g'),
           'time_rel_ns':format(float(ns[i]),'.17g'),'saved_calendar_tokens':';'.join(tokens[j]),
           'held_v':format(float(f[i,0]),'.17g'),'vres_v':format(float(f[i,1]),'.17g'),
           'qres_c':format(float(f[i,2]),'.17g'),'vx_v':format(float(b[i,0]),'.17g'),
           'vy_v':format(float(b[i,1]),'.17g'),'d1_word':int(c[i,4]),'d2_word':int(c[i,5]),
           'dt_word':int(c[i,6]),'d2_count':int(w[i,51]),'ta_compare_count':int(w[i,52]),'ta_feedback_count':int(w[i,53])})
    with (out/'events_sample.csv').open('x',encoding='utf8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(events[0]));writer.writeheader();writer.writerows(events)
    decisions=[]
    for typ,indices,bits,start in (('D2',d2,dbits,11),('TA',ta,tbits,7)):
        for j,(i,bit) in enumerate(zip(indices,bits)):
            decisions.append({'sample_id':sample,'phase':typ,'sequence_1based':j+1,'word_bit':start-j,
               'time_abs_s':format(float(te[i]),'.17g'),'time_rel_ns':format(float(ns[i]),'.17g'),
               'vy_v':format(float(b[i,1]),'.17g'),'decision_bit':bit,
               'sinc2_numerator_if_TA':8-j if typ=='TA' else '',
               'sinc2_denominator_if_TA':8 if typ=='TA' else ''})
    with (out/'decisions_sample.csv').open('x',encoding='utf8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(decisions[0]));writer.writeheader();writer.writerows(decisions)
    author_style.apply();W=146/25.4
    subtitle=(f'ID {sample}, epoch 1 · CNV {t0*1e6:.6f} µs · N=8, 5 MS/s · AZ/noise/DEM/dither/jitter OFF')
    # Fig. 1 evidence: event endpoints of the actual M=8 sample, not M sweep.
    fig,(ax1,ax2)=plt.subplots(2,1,figsize=(W,5.95),gridspec_kw={'height_ratios':[1.05,1]})
    fig.subplots_adjust(left=.16,right=.96,top=.83,bottom=.25,hspace=.43)
    title(fig,'Fig. 1 model evidence — one actual M=8 conversion',subtitle);footer(fig,cfg)
    mask=[i for i in ix if te[i]>=te[d2[0]]-1.25e-9 and te[i]<=te[ready[0]]]
    ax1.plot(ns[mask],b[mask,0]*1e3,color=ORANGE,marker='o',markersize=2.1,lw=.8,label='Vx: RA output')
    ax1.plot(ns[mask],b[mask,1]*1e3,color=BLUE,marker='s',markersize=2.1,lw=.8,ls='--',label='Vy: DAC2 top')
    ax1.axvline(ns[ta[0]],color=GREY,lw=.6,ls=':');ax1.text(ns[ta[0]]+.3,.78,'TA starts',transform=ax1.get_xaxis_transform(),va='top',size=7)
    ax1.set_ylabel('Vx / Vy (mV)');ax1.set_xlabel('Time relative to CNV (ns)');ax1.grid(True,alpha=.27);ax1.legend(loc='lower right',frameon=False,ncol=2,fontsize=7)
    ax1.text(-.08,1.02,'(a)',transform=ax1.transAxes,va='bottom',size=8,clip_on=False)
    secondary_time(ax1,t0)
    y=b[ta,1]*1e6
    ax2.plot(ns[ta],y,color=BLUE,lw=.8,ls='--',marker='s',markersize=3,label='Vy at TA compare; labels are DT bits')
    ax2.axhline(0,color=BLACK,lw=.5)
    for xx,yy,bit in zip(ns[ta],y,tbits):ax2.annotate(str(bit),(xx,yy),xytext=(0,7),textcoords='offset points',ha='center',size=7)
    bottom=min(-130.,float(np.min(y))-40);top=max(430.,float(np.max(y))+110);ax2.set_ylim(bottom,top)
    ax2.scatter(ns[tafb],np.full(len(tafb),bottom+14),marker='|',s=50,color=ORANGE,label='7 feedback events (raster)')
    ax2.text(-.08,1.02,'(b)',transform=ax2.transAxes,va='bottom',size=8,clip_on=False)
    ax2.set_ylabel('Vy at compare (µV)');ax2.set_xlabel('Time relative to CNV (ns)');ax2.grid(True,alpha=.27);ax2.legend(loc='upper right',frameon=False,fontsize=7)
    author_style.finish(fig);savefig(fig,out,'fig01_tracking_M8_actual')

    # Fig. 2 evidence: discrete scheduling/observed-stage event raster.
    fig,ax=plt.subplots(figsize=(W,5.55));fig.subplots_adjust(left=.25,right=.97,top=.80,bottom=.32)
    title(fig,'Fig. 2 model evidence — actual event timeline',subtitle);footer(fig,cfg)
    lanes=[('Capture',cnv,'o',BLACK),('Coarse',coarse,'s',BLACK),('SAR1 compare',fine,'|',BLUE),('RA start',ra,'^',ORANGE),
           ('D2 compare',d2,'o',BLUE),('D2 feedback',d2fb,'|',ORANGE),('TA compare',ta,'o',BLUE),('TA feedback',tafb,'|',ORANGE),
           ('RAW ready',ready,'s',GREEN),('Release',release,'D',BLACK)]
    for pos,(label,ii,marker,color) in enumerate(lanes[::-1]):
        ax.axhline(pos,color='#dddddd',lw=.45,zorder=0);ax.scatter(ns[ii],np.full(len(ii),pos),marker=marker,c=color,s=18 if marker!='|' else 50,lw=.8,zorder=3)
    ax.set_yticks(range(len(lanes)),[x[0] for x in lanes[::-1]]);ax.set_xlim(-2,92);ax.set_ylim(-.7,len(lanes)-.3)
    ax.set_xlabel('Time relative to CNV (ns)');ax.grid(axis='x',alpha=.22);secondary_time(ax,t0)
    fig.text(.255,.237,f'Stored t_open = {1e6*open_s:.6f} µs ({(open_s-t0)*1e9:.2f} ns); aperture = {t0*1e6:.6f} µs.',size=7,ha='left')
    fig.text(.255,.213,'Opening is state metadata; no switch waveform or AZ phase is plotted.',size=7,ha='left')
    author_style.finish(fig);savefig(fig,out,'fig02_timing_actual')

    # Fig.2 evidence: recorded endpoint voltages throughout the same sample.
    fig,axs=plt.subplots(3,1,sharex=True,figsize=(W,6.15));fig.subplots_adjust(left=.18,right=.96,top=.83,bottom=.24,hspace=.17)
    title(fig,'Fig. 2 model evidence — DAC1 residual and CT endpoints',subtitle);footer(fig,cfg)
    vals=((f[:,1]*1e3,'Vres (mV)',GREEN),(b[:,0]*1e3,'Vx (mV)',ORANGE),(b[:,1]*1e3,'Vy (mV)',BLUE))
    for k,(value,label,color) in enumerate(vals):
        ax=axs[k];ax.plot(ns[ix],value[ix],color=color,lw=.7,ls='--',marker='o',markersize=2.2)
        ax.axhline(0,color=BLACK,lw=.45);ax.grid(True,alpha=.25);ax.set_ylabel(label)
        ax.axvline(ns[ra[0]],color=GREY,lw=.55,ls=':');ax.axvline(ns[ta[0]],color=GREY,lw=.55,ls=':')
    axs[0].text(.01,.88,'(a) DAC1 residual',transform=axs[0].transAxes,va='top',size=8)
    axs[1].text(.01,.88,'(b) RA output',transform=axs[1].transAxes,va='top',size=8)
    axs[2].text(.01,.88,'(c) CT DAC top plate',transform=axs[2].transAxes,va='top',size=8)
    axs[-1].set_xlim(-2,92);axs[-1].set_xlabel('Time relative to CNV (ns)');secondary_time(axs[0],t0)
    author_style.finish(fig);savefig(fig,out,'fig02_nodes_actual')

    images=sorted(out.glob('*.png'))+sorted(out.glob('*.pdf'))+sorted(out.glob('*.svg'))
    manifest={'schema':'single-bank-fig01-02-actual-n8/v1','sample_id':sample,'epoch':1,'t_cnv_s':t0,
      'source_file_sha256':PINS,'data_scope':'48 actual event rows; metadata from saved P; no interpolation for data',
      'raw_words':{'D1':final[0],'D2':final[1],'DT':final[2],'code20':final[3]},'ta_bits_first_to_last':tbits,
      'actual_stage_counts_at_raw':[12,8,7],'actual_event_token_counts':{'fine_decide':5,'d2_decide':12,'d2_feedback':12,'ta_compare':8,'ta_feedback':7},
      'configuration':{'fs_hz':float(cfg['fs_hz']),'full_scale_diff_v':float(cfg['fsr_diff_v']),
          'input_frequency_hz':float(cfg['input/frequency_hz']),'input_peak_v':float(cfg['input/amplitude_v']),
          'single_bank':True,'single_guard_s':float(cfg['front/single_guard_s']),
          'ra_A0':float(cfg['backend/ra/A0']),'ra_UGB_hz':float(cfg['backend/ra/UGB_hz']),
          'ra_Cf_f':float(cfg['backend/ra/Cf_f']),'sample_tau_s':0,'dac_tau_s':0,
          'noise_az_dem_dither_jitter_mismatch':'off in this P'},
      'stored_open_s':open_s,'capture_time_s':t0,'stored_window_s':t0-open_s,
      'source_semantics':{'front_log':'ChargeReturn FE_retobs event-stage observation; Vres=column 2, not a continuous waveform',
          'back_log':'RaAzCt observation before decision/reset: VX column 1, VY column 2; event samples only',
          'adi_wire_log':'actual stage-next control and command-wire counter; not independent committed analog-state evidence',
          'calendar':'event label derived from saved calendar joined to actual event_log group/time'},
      'reference_style':'User-selected CICC paper Fig1/2; Arial plot labels, 146 mm width; no copied paper plots',
      'limitations':['M=8 only; no M sweep, SNR improvement, PSD or FFT was measured.',
          'No independently measured transistor clock waveform; AZ is off.',
          'Opening time is saved state metadata, not a sampled switch waveform.',
          'Return charge and full FE state are not present in these N8 logs.',
          'Currents, topology and PDK/silicon performance are not inferred.'],
      'outputs':{x.name:sha(x) for x in images},'tables':{x.name:sha(x) for x in (out/'events_sample.csv',out/'decisions_sample.csv')},
      'plot_script_sha256':sha(Path(__file__)),'style_helper_sha256':sha(HERE/'author_style.py')}
    (out/'figure_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('Saved',len(images),'figure files and two CSV tables to',out)


if __name__=='__main__':main()
