"""Plot actual sampled DC codes; no interpolation or missing-code claim."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
p=Path(__file__).with_name('zero15_independent.json');data=json.loads(p.read_text())
x=[s['held_v']*1e9 for s in data['samples']];y=[s['code20'] for s in data['samples']]
assert len(x)==17 and len(y)==17
fig,ax=plt.subplots(figsize=(9,4.4),layout='constrained');ax.scatter(x,y,color='#13677e',s=34,zorder=3)
ax.set(xlabel='Actual held input (nV)',ylabel='Actual output code',title='Near-zero DC samples: 17 measured points only')
ax.set_yticks([524285,524286,524287,524288,524289]);ax.ticklabel_format(axis='y',style='plain',useOffset=False)
ax.grid(alpha=.25);ax.text(.02,.95,'No interpolation; unsampled codes and monotonicity are unknown.',transform=ax.transAxes,va='top',fontsize=9)
fig.savefig(Path(__file__).with_name('zero_samples.png'),dpi=200);plt.close(fig)
