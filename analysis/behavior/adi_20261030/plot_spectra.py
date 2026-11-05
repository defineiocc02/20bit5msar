"""Recompute spectra from saved Simulink output codes; no sample generation."""
from pathlib import Path
import json,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path(__file__).resolve().parents[3]
ids=['f6ed1267-fc88-4005-bc59-442bed4aac21','390aefe9-57d8-4f21-80d2-e362051f30bb','2d1c3ea0-ff5c-420e-aa9f-e47b46d92ceb','2f1b3c80-310e-4b05-a458-4e0b3a60d632']
fig,axes=plt.subplots(2,2,figsize=(11,6.5),sharex=True,sharey=True,layout='constrained')
for i,(ax,runid) in enumerate(zip(axes.flat,ids)):
 p=root/'runs'/('behavior_'+runid);s=json.loads((p/'summary.json').read_text());q=json.loads((p/'parameters.json').read_text())
 c=np.asarray(s['code20'],dtype=np.float64);n=len(c);fs=q['fs_hz'];fsr=q['fsr_diff_v'];k=round(q['input']['frequency_hz']*n/fs);assert n==256 and k==5
 v=((c+.5)/(2**20)-.5)*fsr;x=np.fft.rfft(v-v.mean())/n;power=abs(x)**2;power[1:-1]*=2
 sig=power[k];other=power.copy();other[[0,k]]=0;harm=np.unique(np.minimum((np.arange(2,11)*k)%n,n-(np.arange(2,11)*k)%n));harm=harm[(harm!=0)&(harm!=k)]
 hp=power[harm].sum();nd=other.sum();vals={'snr_db':10*np.log10(sig/(nd-hp)),'sndr_db':10*np.log10(sig/nd),'sfdr_db':10*np.log10(sig/other.max()),'thd_db':10*np.log10(hp/sig)};vals['enob']=(vals['sndr_db']-1.76)/6.02
 for name,value in vals.items():assert abs(value-s[name])<1e-8
 f=np.arange(n//2+1)*fs/n/1e6;db=10*np.log10(np.maximum(power/(fsr**2/8),np.finfo(float).tiny))
 ax.plot(f[1:],db[1:],color='#176b86',lw=.8);ax.scatter([f[k]],[db[k]],color='#b94b3e',s=13,zorder=3);ax.grid(alpha=.25);ax.set_ylim(-180,5);ax.set_xlim(0,2.5)
 ax.set_title(f'DEM {i//2}, dither {i%2}   SNDR {vals["sndr_db"]:.3f} dB',fontsize=10)
 if i in (0,2):ax.set_ylabel('Power (dBFS / bin)')
 if i>=2:ax.set_xlabel('Frequency (MHz)')
fig.suptitle('Same-chip mismatch stress: actual 256-code spectra\nFs 5 MS/s, Fin 97.65625 kHz, unit sigma 0.1%, seed 20261030',fontsize=11)
fig.savefig(Path(__file__).with_name('adi_four_spectra.png'),dpi=200);plt.close(fig)
print('Four independently recomputed FFT metrics agree with saved run summaries.')
