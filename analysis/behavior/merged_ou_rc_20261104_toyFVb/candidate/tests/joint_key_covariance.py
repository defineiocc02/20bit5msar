#!/usr/bin/env python3
"""Finite-seed cross-key check, not a MATLAB run or proof of independence."""
import json
import math
import hashlib
import struct

from joint_math_oracle import z_key
from rc_ktc_math_oracle import normal


def cmp_key(seed,epoch,ident,event_code,event_index):
    payload=(b'SAR20-COMPARATOR-v1\0'+struct.pack('>QQQQQ',
        seed,epoch,ident,event_code,event_index))
    a,b=struct.unpack('>QQ',hashlib.sha256(payload).digest()[:16])
    u1=((a>>12)+0.5)/2**52;u2=((b>>12)+0.5)/2**52
    assert 0<u1<1 and 0<u2<1
    return math.sqrt(-2*math.log(u1))*math.cos(2*math.pi*u2)


def main():
    n=30000
    # Fixtures only. This does not choose a normal operating profile.
    ktc_seed,ou_seed,epoch=20261027,9481,1
    sx=sy=sxx=syy=sxy=0.0
    for ident in range(n):
        t0=ident*200e-9+31.25e-9
        t1=ident*200e-9+43.75e-9
        x=z_key(ou_seed,epoch,ident,t0,t1)
        y=sum(normal(ktc_seed,j,ident,epoch) for j in range(1,9))/math.sqrt(8)
        sx+=x;sy+=y;sxx+=x*x;syy+=y*y;sxy+=x*y
    mx,my=sx/n,sy/n
    vx=sxx/n-mx*mx;vy=syy/n-my*my;cov=sxy/n-mx*my
    corr=cov/math.sqrt(vx*vy)
    assert abs(mx)<0.03 and abs(my)<0.03
    assert abs(vx-1)<0.04 and abs(vy-1)<0.04 and abs(corr)<0.04
    ncmp=8192
    ax=ay=axx=ayy=axy=0.0
    for ident in range(ncmp):
        t0=ident*200e-9+43.75e-9;t1=ident*200e-9+45e-9
        x=z_key(20261104,epoch,ident,t0,t1)
        y=cmp_key(20261104,epoch,ident,3,0)
        ax+=x;ay+=y;axx+=x*x;ayy+=y*y;axy+=x*y
    ax/=ncmp;ay/=ncmp
    cmp_corr=(axy/ncmp-ax*ay)/math.sqrt((axx/ncmp-ax*ax)*(ayy/ncmp-ay*ay))
    assert abs(cmp_corr)<0.05
    print(json.dumps({'status':'python_cross_key_sample_check_passed','count':n,
        'mean_ou':mx,'mean_ktc_aggregate':my,'variance_ou':vx,
        'variance_ktc_aggregate':vy,'covariance':cov,'correlation':corr,
        'ou_comparator_same_seed_count':ncmp,'ou_comparator_same_seed_correlation':cmp_corr,
        'limitations':'One fixed pair of fixture seeds, Python translation, no MATLAB, no proof of independence, no closed-loop claim.'},indent=2))


if __name__=='__main__':
    main()
