"""Plot and independently check the recorded MATLAB ADC output spectrum.

Input is the unmodified production run's summary.json and parameters.json.
This performs post-processing only; it does not simulate or generate ADC codes.
"""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

project=Path(__file__).resolve().parents[3]
run=project/'runs/behavior_9058b834-83be-4415-946c-7f3b3ef8c7eb'
s=json.loads((run/'summary.json').read_text())
p=json.loads((run/'parameters.json').read_text())
codes=np.asarray(s['code20'],dtype=np.float64)
assert len(codes)==256 and s['records']==256 and len(s['sample_ids'])==256
fs=p['fs_hz']; fsr=p['fsr_diff_v']; n=len(codes)
bin_no=round(p['input']['frequency_hz']*n/fs)
assert bin_no==5 and abs(bin_no-p['input']['frequency_hz']*n/fs)<1e-9
v=((codes+0.5)/(2**20)-0.5)*fsr
spec=np.fft.rfft(v-v.mean())/n
power=np.abs(spec)**2;power[1:-1]*=2
signal=power[bin_no];other=power.copy();other[[0,bin_no]]=0
harm=np.unique(np.minimum((np.arange(2,11)*bin_no)%n,n-(np.arange(2,11)*bin_no)%n))
harm=harm[(harm!=0)&(harm!=bin_no)]
hp=power[harm].sum();nd=other.sum()
metrics={'snr_db':10*np.log10(signal/(nd-hp)), 'sndr_db':10*np.log10(signal/nd),
         'sfdr_db':10*np.log10(signal/other.max()), 'thd_db':10*np.log10(hp/signal)}
metrics['enob']=(metrics['sndr_db']-1.76)/6.02
for key,value in metrics.items():
 assert abs(float(value)-float(s[key]))<1e-8, (key,value,s[key])
freq=np.arange(n//2+1)*fs/n/1e6
# Full-scale sine RMS power: (FSR/2)^2 / 2.
db=10*np.log10(np.maximum(power/(fsr**2/8),np.finfo(float).tiny))
fig,ax=plt.subplots(figsize=(10,4.8),layout='constrained')
ax.plot(freq[1:],db[1:],lw=1,color='#146b86')
ax.scatter([freq[bin_no]],[db[bin_no]],color='#ba4538',s=24,zorder=3,label='Fundamental')
ax.set(xlabel='Frequency (MHz)',ylabel='Power (dBFS / bin)',xlim=(0,fs/2/1e6),ylim=(-180,5),
       title='SAR20-5: actual 256-code spectrum, Bank OFF')
ax.grid(alpha=.25);ax.legend(loc='upper right')
ax.text(.02,.05,'Fs = 5 MS/s, Fin = 97.65625 kHz, N = 256\n'
        'SNDR = %.3f dB   SFDR = %.3f dB   ENOB = %.3f bit' %
        (metrics['sndr_db'],metrics['sfdr_db'],metrics['enob']),transform=ax.transAxes,
        fontsize=9,va='bottom',bbox=dict(facecolor='white',alpha=.9,edgecolor='#cccccc'))
out=Path(__file__).with_name('actual_spectrum_256.png');fig.savefig(out,dpi=200);plt.close(fig)
print(json.dumps({k:float(x) for k,x in metrics.items()},indent=2))
