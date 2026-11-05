"""Plot actual recorded MATLAB codes for the preregistered Bank comparison."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path(__file__).resolve().parents[3]
names=['nominal_bank_off','legacy_frozen_bank_off','bank_on_same_h_AB']
ids=['314ea73c-c0e0-454e-8812-879e5943b674','20b1e412-edb9-4bb6-a871-65bf15cd120a','302c58b3-52b4-42ac-b6c9-fbe09674156e']
fig,axes=plt.subplots(3,1,figsize=(10,8),sharex=True,sharey=True,layout='constrained')
for ax,name,runid in zip(axes,names,ids):
 run=root/'runs'/('behavior_'+runid)
 s=json.loads((run/'summary.json').read_text());p=json.loads((run/'parameters.json').read_text())
 c=np.asarray(s['code20'],float);fs=p['fs_hz'];n=c.size;fsr=p['fsr_diff_v'];assert n==256 and s['records']==256
 assert p['input']['frequency_hz']==996093.75 and p['epoch']==4
 v=((c+.5)/(2**20)-.5)*fsr;X=np.fft.rfft(v-v.mean())/n;power=abs(X)**2;power[1:-1]*=2
 k=round(p['input']['frequency_hz']*n/fs);signal=power[k];other=power.copy();other[[0,k]]=0
 harmonics=np.unique(np.minimum((np.arange(2,11)*k)%n,n-(np.arange(2,11)*k)%n));harmonics=harmonics[(harmonics!=0)&(harmonics!=k)]
 hp=power[harmonics].sum();nd=other.sum();sndr=10*np.log10(signal/nd)
 snr=10*np.log10(signal/(nd-hp));sfdr=10*np.log10(signal/other.max());thd=10*np.log10(hp/signal);enob=(sndr-1.76)/6.02
 for key,value in [('snr_db',snr),('sndr_db',sndr),('sfdr_db',sfdr),('thd_db',thd),('enob',enob)]:assert abs(value-s[key])<1e-8
 freq=np.arange(n//2+1)*fs/n/1e6;db=10*np.log10(np.maximum(power/(fsr**2/8),np.finfo(float).tiny))
 ax.plot(freq[1:],db[1:],lw=.9,color='#176b86');ax.scatter([freq[k]],[db[k]],s=18,color='#bd473d',zorder=3)
 ax.text(.012,.08,name.replace('_',' ')+f'   SNDR {sndr:.3f} dB   SFDR {sfdr:.3f} dB',transform=ax.transAxes,fontsize=9,bbox={'facecolor':'white','alpha':.9,'edgecolor':'#cccccc'})
 ax.grid(alpha=.23);ax.set_ylim(-180,5);ax.set_ylabel('dBFS / bin')
axes[-1].set_xlabel('Frequency (MHz)');axes[-1].set_xlim(0,fs/2/1e6)
fig.suptitle('Actual 256-code spectra: one fixed chip, same-h A/B, epoch 4\nFs = 5 MS/s, Fin = 996.09375 kHz; mismatch, DEM and dither enabled',fontsize=11)
fig.savefig(Path(__file__).with_name('bank_three_spectra.png'),dpi=200);plt.close(fig)
print('Recomputed metrics agree with each actual run summary (<1e-8).')
