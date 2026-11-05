"""Plot actual saved RA-noise ON codes, independently check FFT metrics."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path(__file__).resolve().parents[3]
r=json.loads((root/'runs/work_20261030T161056Z/outer_receipt.json').read_text())
c=r['candidate'];s=c['spectrum'];code=np.asarray(c['code20'],dtype=float)
n=len(code);fs=s['sample_rate_hz'];fsr=s['full_scale_diff_v'];k=s['fundamental_bin'];assert n==256 and k==5
v=((code+.5)/(2**20)-.5)*fsr;x=np.fft.rfft(v-v.mean())/n;p=abs(x)**2;p[1:-1]*=2
sig=p[k];other=p.copy();other[[0,k]]=0;hs=np.unique(np.minimum((np.arange(2,11)*k)%n,n-(np.arange(2,11)*k)%n));hs=hs[(hs!=0)&(hs!=k)]
hp=p[hs].sum();nd=other.sum();m={'snr_db':10*np.log10(sig/(nd-hp)),'sndr_db':10*np.log10(sig/nd),'sfdr_db':10*np.log10(sig/other.max()),'thd_db':10*np.log10(hp/sig)};m['enob']=(m['sndr_db']-1.76)/6.02
for key,val in m.items():assert abs(val-s[key])<1e-8
freq=np.arange(n//2+1)*fs/n/1e6;db=10*np.log10(np.maximum(p/(fsr**2/8),np.finfo(float).tiny))
fig,ax=plt.subplots(figsize=(10,4.8),layout='constrained');ax.plot(freq[1:],db[1:],lw=.9,color='#146b86');ax.scatter([freq[k]],[db[k]],s=25,color='#bf4a3b',zorder=3)
ax.set(xlabel='Frequency (MHz)',ylabel='Power (dBFS / bin)',xlim=(0,2.5),ylim=(-180,5),title='Isolated RA OU ON: actual 256-code spectrum')
ax.grid(alpha=.25);ax.text(.02,.05,'Fs = 5 MS/s, Fin = 97.65625 kHz\nVX stationary RMS = 1 mV (test assumption)\nSNDR = %.3f dB, SFDR = %.3f dB, ENOB = %.3f bit'%(m['sndr_db'],m['sfdr_db'],m['enob']),transform=ax.transAxes,va='bottom',fontsize=9,bbox={'facecolor':'white','edgecolor':'#cccccc','alpha':.9})
fig.savefig(Path(__file__).with_name('ou_on_spectrum.png'),dpi=200);plt.close(fig)
print('Independent FFT matches saved MATLAB spectrum (<1e-8).')
