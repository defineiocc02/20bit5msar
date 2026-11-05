"""Plot ON-first/OFF-second 256-code scratch pair; no ADC data generation."""
from pathlib import Path
import json,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path(__file__).resolve().parents[3];r=json.loads((root/'runs/work_20261030T162714Z/outer_receipt.json').read_text())['candidate']
fig,axes=plt.subplots(2,1,figsize=(10,6.3),sharex=True,sharey=True,layout='constrained')
for ax,name in zip(axes,['off','on']):
 c=np.asarray(r[name+'_codes'],float);s=r[name+'_spectrum'];n=len(c);fs=s['sample_rate_hz'];fsr=s['full_scale_diff_v'];k=s['fundamental_bin'];assert n==256 and k==5
 v=((c+.5)/2**20-.5)*fsr;p=np.abs(np.fft.rfft(v-v.mean())/n)**2;p[1:-1]*=2;sig=p[k];other=p.copy();other[[0,k]]=0
 h=np.unique(np.minimum((np.arange(2,11)*k)%n,n-(np.arange(2,11)*k)%n));h=h[(h!=0)&(h!=k)];hp=p[h].sum();nd=other.sum();sndr=10*np.log10(sig/nd);snr=10*np.log10(sig/(nd-hp));sfdr=10*np.log10(sig/other.max());thd=10*np.log10(hp/sig);enob=(sndr-1.76)/6.02
 for key,val in [('snr_db',snr),('sndr_db',sndr),('sfdr_db',sfdr),('thd_db',thd),('enob',enob)]:assert abs(val-s[key])<1e-8
 f=np.arange(n//2+1)*fs/n/1e6;db=10*np.log10(np.maximum(p/(fsr**2/8),np.finfo(float).tiny));ax.plot(f[1:],db[1:],lw=.9,color='#176b86');ax.scatter([f[k]],[db[k]],color='#bf4a3b',s=18,zorder=3);ax.grid(alpha=.25);ax.set_ylim(-180,5);ax.set_xlim(0,2.5);ax.set_ylabel('Power (dBFS / bin)');ax.set_title('OU %s: SNDR %.3f dB, ENOB %.3f bit'%(name.upper(),sndr,enob),fontsize=10)
axes[-1].set_xlabel('Frequency (MHz)');fig.suptitle('Same-model RA OU comparison, ON first then OFF\nFs 5 MS/s, Fin 97.65625 kHz, N=256; σVX=1 mV is a test assumption',fontsize=11)
fig.savefig(Path(__file__).with_name('ou_matched_pair_spectra.png'),dpi=200);plt.close(fig)
print('Actual ON/OFF FFT values match saved MATLAB spectra (<1e-8).')
