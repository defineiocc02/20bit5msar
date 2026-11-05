#!/usr/bin/env python3
"""Draw actual ordinary-AZ N8 event evidence; never run MATLAB or edit raw data."""
from __future__ import annotations
import argparse,csv,hashlib,json,math,sys
from pathlib import Path
sys.dont_write_bytecode=True
import h5py,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
PRJ=ROOT/'analysis/behavior/single_bank_1039_20261104'
AZ=PRJ/'ordinary_az_actual/az_pair';PLAIN=PRJ/'n8_plain/plain'
READER=ROOT/'analysis/behavior/finite_dac_review_20261028/verify_as_run.py'
STYLE=PRJ/'figures/fig01_02_actual_n8_20261104/author_style.py'
sys.path.insert(0,str(READER.parent));import verify_as_run as u
sys.path.insert(0,str(STYLE.parent));import author_style
PINS={'zeroVos_simout':'d472f01a80a832cd483783e4ceca0640a692e0094d1a64f5400411e5201a934c',
 'offset_only_simout':'1ddd21542873c8e249c3e101e57d1b9f7193ed5975f9729415111df11a0f16d6',
 'ordinary_az_simout':'4d015eb879c0666d1697d2fa77e79c94cf644b701ddd47c19fc3bf45756f6964',
 'zeroVos_P':'236ddfb427dfc07e7f7e27dd58746deb30946891717d255b53789aa8127a1e9f',
 'offset_only_P':'b5ff829b18c1a7658218295c44858eeafdafd00e5cfefa726d4742aa671e9cbe',
 'ordinary_az_P':'c7580a4ba9d7bfef97726164b64a4080964c7f99e542e55960192d20c2172c5c',
 'model':'48537818b3212e1e4c8231dec433d1fde36d95814cdcce8c529bb2898eb097d3',
 'source_zip':'09e6c7c82635d8f6bf1cf4cc8e86f0ec42036524bfe6518dfcb37ea05fb06eb7',
 'reader':'3ca8dc8a6f553e75466438a0d74b9bf6a0a6ab5f65b8c151429981af330f7467',
 'slide_pdf':'3b85bbbfc0fd4cbf071187bbccc8b3487c640094ddccb867a7f1dd2c7bdefce0'}
BLUE='#0072B2';ORANGE='#D55E00';GREEN='#009E73';BLACK='#1c1c1c'

def need(c,m):
    if not c:raise ValueError(m)

def sha(p):
    need(p.is_file() and not p.is_symlink() and p.stat().st_size<=300_000_000,f'bad input or >300 MB: {p}')
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def write_csv(path,fields,rows):
    with path.open('x',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def main():
    a=argparse.ArgumentParser();a.add_argument('--out',type=Path,required=True);args=a.parse_args()
    out=args.out.resolve();need(not out.exists() or (out.is_dir() and not any(out.iterdir())),'out must be new/empty')
    files={'zeroVos_simout':PLAIN/'simout.mat','offset_only_simout':AZ/'offset_only/simout.mat',
      'ordinary_az_simout':AZ/'ordinary_az/simout.mat','zeroVos_P':PLAIN/'P_used.mat',
      'offset_only_P':AZ/'offset_only/P_used.mat','ordinary_az_P':AZ/'ordinary_az/P_used.mat',
      'model':PRJ/'graph_v2/SarAdc.slx','source_zip':PRJ/'single_bank_1039_candidate_20261104_v2.zip',
      'reader':READER,'slide_pdf':Path('/Users/zhaoyi/Desktop/13-6_Jin.pdf')}
    for k,p in files.items():need(sha(p)==PINS[k],f'Identity mismatch: {k}')
    need(u.pdiff(files['zeroVos_P'],files['offset_only_P'])==['P/backend/ra/vos_input_v'],
         'Unexpected differences from zero-offset baseline.')
    wanted=sorted(['P/backend/az/mode','P/backend/ni/az','P/cal_cfg/public_cfg/az_mode',
                   'P/digital/az_mode','P/ni/az','P/xBK0'])
    need(u.pdiff(files['offset_only_P'],files['ordinary_az_P'])==wanted,'Unexpected ordinary-AZ P differences.')
    with h5py.File(files['ordinary_az_P'],'r') as f:
        get=lambda k:u.val(f,'P/'+k)
        need(get('backend/ra/vos_input_v')==.001 and np.all(np.asarray(get('backend/az/write_tau_s'))==1e-9)
             and np.all(np.isinf(np.asarray(get('backend/az/leak_tau_s')))) and
             get('backend/az/mode')=='ordinary' and get('backend/ni/az')==1,'AZ parameter mismatch')
        need(get('N')==8 and get('fs_hz')==5e6 and get('first_id')==4 and get('epoch')==1,
             'N8 sample configuration mismatch')
        offsets,groups,budget=u.read_calendar(f)
        cfg={'write_tau_s':1e-9,'hold_leak_tau_s':'Inf','injected_Vos_v':.001,
          'A0':float(get('backend/ra/A0')),'nominal_G':float(get('digital/ra_gain')),
          'fsr_diff_v':float(get('digital/fsr_diff_v')),'sample_period_s':float(get('Ts_s'))}
    def gi(token):
        values=[i+1 for i,g in enumerate(groups) if token in g];need(len(values)==1,f'{token} calendar')
        return values[0]
    cnv,ra,rawready=map(gi,('cnv','ra_start','raw_latch'))
    logs=[u.read_logs(files[k]) for k in ('zeroVos_simout','offset_only_simout','ordinary_az_simout')]
    times=[];raw_codes=[]
    expected=np.column_stack((np.repeat(np.arange(12),48),np.tile(np.arange(1,49),12)))
    for L in logs:
        te=L['event_log']['time'];ev=L['event_log']['data'];need(np.array_equal(ev,expected),'event order')
        for n in ('az_commit_log','az_route_log','back_log','code_log','raw_log','ready_log'):
            need(u.same(te,L[n]['time']),f'event axis {n}')
        route=L['az_route_log']['data'];need(np.all(route[:,0]==1) and not np.any((route[:,3]!=0)&(route[:,4]!=0)),
                                              'route polarity or AZ/RA overlap')
        idx=np.flatnonzero((ev[:,1]==rawready)&(L['ready_log']['data'][:,0]==1))
        raw=L['raw_log']['data'][idx];need(len(idx)==12 and np.array_equal(raw[:,3],np.arange(12)) and
              np.all(raw[:,4:]==1),'actual RAW IDs/valid')
        raw_codes.append(L['code_log']['data'][idx,0]);times.append(te)
    need(u.same(times[0],times[1]) and u.same(times[0],times[2]),'case event times differ')
    d_off=raw_codes[1]-raw_codes[0];d_on=raw_codes[2]-raw_codes[0]
    need(np.all(np.isin(d_off,[133,134])) and np.all(d_on==0),'unexpected actual code differences')
    t=times[0];ev=expected;first=np.flatnonzero(ev[:,0]==0);s5=np.flatnonzero(ev[:,0]==5)
    on=logs[2]['az_commit_log']['data'];off=logs[1]['az_commit_log']['data']
    route=logs[2]['az_route_log']['data'];n0=first[np.flatnonzero(ev[first,1]==cnv)[0]]
    q0=first[np.flatnonzero(ev[first,1]==ra)[0]]
    need(route[n0,4]==1 and route[n0,3]==0 and route[q0,4]==0 and route[q0,3]==1,
         'actual write/RA route boundaries differ')
    duration=float(t[q0]-t[n0]);need(abs(duration-31.25e-9)<1e-18,'wrong AZ duration')
    need(off[n0,0]==0 and off[q0,0]==0 and abs(on[q0,0]-.001)<1e-12 and on[q0,1]==1,
         'AZ final-next write values differ')
    relative=(t[first]-t[n0])*1e9
    write=relative<=duration*1e9+1e-8
    predicted=.001*(1-np.exp(-relative[write]*1e-9/cfg['write_tau_s']))
    need(np.max(np.abs(on[first[write],0]-predicted))<1e-15,'logged final-next differs from finite write')
    need(np.all(on[first[~write],0]==on[q0,0]),'infinite-leak hold differs from logged final-next')
    vx=[L['back_log']['data'][s5,0] for L in logs];t5=(t[s5]-t[s5[0]])*1e9
    ng=float(logs[2]['back_log']['data'][s5[-1],4]);F=cfg['A0']/(cfg['A0']+ng)
    theoretical=.001*F*ng/cfg['nominal_G']*2**20/cfg['fsr_diff_v']
    need(abs(theoretical-133.4284317175952)<1e-9,'unexpected model-theory value')
    out.mkdir(parents=True,exist_ok=True)
    rows=[]
    for j,i in enumerate(first):
        rows.append({'event_group':int(ev[i,1]),'t_abs_s':format(t[i],'.17g'),
          't_relative_ns':format(relative[j],'.17g'),'az_off_final_next_v':format(off[i,0],'.17g'),
          'az_on_final_next_v':format(on[i,0],'.17g'),'RA_route_flag':int(route[i,3]),
          'AZ_write_route_flag':int(route[i,4])})
    write_csv(out/'az_final_next_id0.csv',list(rows[0]),rows)
    rows=[]
    for j,i in enumerate(s5):
        rows.append({'event_group':int(ev[i,1]),'t_abs_s':format(t[i],'.17g'),
          't_relative_ns':format(t5[j],'.17g'),'vx_zeroVos_v':format(vx[0][j],'.17g'),
          'vx_offset_AZ_off_v':format(vx[1][j],'.17g'),'vx_offset_AZ_on_v':format(vx[2][j],'.17g')})
    write_csv(out/'ra_output_id5.csv',list(rows[0]),rows)
    rows=[{'sample_id':i,'kind':'warmup' if i<4 else 'selected','zeroVos_code20':int(raw_codes[0][i]),
        'offset_AZ_off_code20':int(raw_codes[1][i]),'offset_AZ_on_code20':int(raw_codes[2][i]),
        'offset_AZ_off_minus_zeroVos_lsb':int(d_off[i]),'offset_AZ_on_minus_zeroVos_lsb':int(d_on[i])} for i in range(12)]
    write_csv(out/'code_difference_12.csv',list(rows[0]),rows)
    author_style.apply();fig,axs=plt.subplots(3,1,figsize=(146/25.4,7.25),gridspec_kw={'height_ratios':[1,1,1.05]})
    fig.subplots_adjust(left=.17,right=.96,top=.86,bottom=.25,hspace=.54)
    fig.text(.015,.98,'RA行为模型普通AZ验证，非三级晶体管环放',fontname='PingFang SC',size=9,weight='bold',va='top')
    fig.text(.015,.947,'Fig. 4 / slide 39 context · Vos=+1 mV · write τ=1 ns · hold leakage τ=∞ · Fs=5 MS/s',size=7,va='top')
    fig.text(.015,.918,'Dots are logged event endpoints; connecting lines are guides. AZ final-next is not committed-state history.',size=7,va='top')
    ax=axs[0];ax.axvspan(0,duration*1e9,facecolor='#e7f1f8',edgecolor='none',zorder=0)
    ax.plot(relative,on[first,0]*1e3,color=GREEN,marker='o',markersize=2,ls='--',lw=.7,label='AZ on: final-next')
    ax.plot(relative,off[first,0]*1e3,color=ORANGE,marker='x',markersize=2,ls='--',lw=.7,label='AZ off: final-next')
    ax.axvline(duration*1e9,color='#777777',lw=.6,ls=':')
    ax.set_xlim(-2,92);ax.set_ylim(-.12,1.22);ax.set_ylabel('Stored AZ (mV)');ax.set_xlabel('ID 0: time from CNV (ns)')
    ax.text(.0,1.06,'(a) Write route: 0–31.25 ns; then hold',transform=ax.transAxes,va='bottom',size=7)
    ax.legend(loc='center right',frameon=False,fontsize=6.5,ncol=2);ax.grid(True,alpha=.2)
    ax=axs[1]
    for y,color,label,ls,mark in ((vx[0],BLACK,'zero-Vos baseline',':','o'),(vx[1],ORANGE,'Vos, AZ off','--','x'),(vx[2],GREEN,'Vos, AZ on','--','o')):
        ax.plot(t5,y*1e3,color=color,ls=ls,marker=mark,markersize=3.5 if label=='zero-Vos baseline' else 2,
                markerfacecolor='none' if label=='zero-Vos baseline' else color,lw=.8,label=label)
    ax.set_xlim(29,92);ax.set_ylabel('RA output VX (mV)');ax.set_xlabel('ID 5: time from CNV (ns)')
    ax.text(.0,1.06,'(b) RA backend pre-decision event output',transform=ax.transAxes,va='bottom',size=7)
    ax.legend(loc='lower right',frameon=False,fontsize=6.3,ncol=3);ax.grid(True,alpha=.2)
    ax=axs[2];x=np.arange(12);ax.axvspan(-.5,3.5,facecolor='#f2f2f2',edgecolor='none',zorder=0)
    ax.bar(x,d_off,width=.66,color=ORANGE,label='Vos, AZ off − baseline')
    ax.scatter(x,d_on,color=GREEN,marker='o',s=10,zorder=4,label='Vos, AZ on − baseline')
    ax.axhline(theoretical,color=BLACK,ls='--',lw=.7,label=f'Model theory {theoretical:.3f} LSB')
    for i,y in zip(x,d_off):ax.text(i,y+3,str(int(y)),ha='center',va='bottom',size=6)
    ax.set_xlim(-.6,11.6);ax.set_ylim(-55,153);ax.set_xticks(x);ax.set_xlabel('Sample ID: warmup 0–3; selected 4–11')
    ax.set_ylabel('Code error (LSB)');ax.text(.0,1.06,'(c) Relative to actual zero-Vos baseline',transform=ax.transAxes,va='bottom',size=7)
    ax.legend(loc='lower left',frameon=False,fontsize=6,ncol=3);ax.grid(axis='y',alpha=.18)
    fig.text(.015,.158,f'Theory: Vos × F × NG / G / LSB; F={F:.6f}, NG={ng:.5g}, G={cfg["nominal_G"]:.0f}.',size=6.5)
    footer=[('SLX',PINS['model']),('Zero-Vos simout',PINS['zeroVos_simout']),
            ('AZ-off simout',PINS['offset_only_simout']),('AZ-on simout',PINS['ordinary_az_simout'])]
    for i,(name,value) in enumerate(footer):fig.text(.015,.133-i*.022,f'{name} SHA256: {value}',size=6,va='center')
    author_style.finish(fig)
    for ext in ('png','pdf','svg'):fig.savefig(out/f'fig04_ordinary_az_n8.{ext}',dpi=400,facecolor='white')
    plt.close(fig)
    report={'schema':'sar20-ordinary-az-figure-n8/v1','input_sha256':PINS,'parameters':cfg,
      'actual_group_tokens':budget,'actual_event_rows_per_run':576,
      'sample0_write_duration_ns':duration*1e9,'sample0_final_next_at_ra_start_v':float(on[q0,0]),
      'actual_zeroVos_code20':raw_codes[0].astype(int).tolist(),
      'actual_offset_AZ_off_code20':raw_codes[1].astype(int).tolist(),
      'actual_offset_AZ_on_code20':raw_codes[2].astype(int).tolist(),
      'actual_AZ_off_minus_zeroVos_lsb':d_off.astype(int).tolist(),
      'actual_AZ_on_minus_zeroVos_lsb':d_on.astype(int).tolist(),
      'theory':{'NG_from_saved_backend':ng,'F_A0_over_A0_plus_NG':F,'G_nominal':cfg['nominal_G'],
          'predicted_offset_lsb':theoretical,'scope':'model linear predictor, not observed data'},
      'scope':['AZ values are RaReset final-next prior to UnitDelay, not independent committed-state history.',
        'RA VX is actual pre-decision event endpoint; lines only guide the eye.',
        '12 records include 4 warmup and 8 selected; 1mV is a model test assumption.',
        'Ordinary AZ/RA behavior is not a 3-stage ringamp transistor, power or chip measurement.'],
      'plot_script_sha256':sha(Path(__file__)),'style_helper_sha256':sha(STYLE),
      'outputs_sha256':{p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file()}}
    (out/'figure_manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('Saved',out,'actual code differences AZ off/on:',d_off.astype(int).tolist(),d_on.astype(int).tolist())

if __name__=='__main__':main()
