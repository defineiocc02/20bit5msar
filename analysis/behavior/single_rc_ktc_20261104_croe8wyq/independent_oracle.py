#!/usr/bin/env python3
"""Independent convolution/covariance checks. Not MATLAB execution or signoff."""
from math import atan, cos, exp, expm1, hypot, isinf, log, pi, sin, sqrt
from statistics import fmean
import json

KB=1.380649e-23
TEMP=298.15
C_HALF=27.648e-12

def coeff(duration,tau):
    if tau == 0: return 0.0,1.0
    if isinf(tau): return 1.0,0.0
    return exp(-duration/tau),-expm1(-2*duration/tau)

def drive(t):
    return -0.12+0.6*sin(2*pi*1.31e6*t+0.37)

def sinusoid_formula(v0,t0,t1,tau):
    w=2*pi*1.31e6
    a=w*tau
    particular=lambda t: -0.12+0.6/hypot(1,a)*sin(w*t+0.37-atan(a))
    return particular(t1)+(v0-particular(t0))*exp(-(t1-t0)/tau)

def convolution_simpson(v0,t0,t1,tau,n=16384):
    h=(t1-t0)/n
    def integrand(t):
        return exp(-(t1-t)/tau)*drive(t)/tau
    total=integrand(t0)+integrand(t1)
    total+=4*sum(integrand(t0+i*h) for i in range(1,n,2))
    total+=2*sum(integrand(t0+i*h) for i in range(2,n,2))
    return exp(-(t1-t0)/tau)*v0+h*total/3

# Different spelling/language from MATLAB; only used to assess the frozen keyed
# Gaussian tuple's empirical correlation, not to assert mathematical independence.
def mix(x):
    mask=0xffffffff
    x^=x>>16; x=x*2246822507 & mask
    x^=x>>13; x=x*3266489909 & mask
    return (x^(x>>16)) & mask

def normal(seed,j,ident,epoch):
    b=mix(seed ^ 2654435769)
    x=mix(b ^ ident)
    x=mix(x ^ ((epoch+2246822507)&0xffffffff))
    x=mix(x ^ (j+3266489909))
    w1=mix(x ^ 668265263);w2=mix(x ^ 374761393)
    return sqrt(-2*log((w1+0.5)/4294967296))*cos(2*pi*((w2+0.5)/4294967296))

def var(values):
    mu=fmean(values)
    return fmean((v-mu)**2 for v in values)

def cov(x,y):
    a=fmean(x);b=fmean(y)
    return fmean((xx-a)*(yy-b) for xx,yy in zip(x,y))

if __name__=='__main__':
    comparisons=[]
    for tau in (1e-9,5e-9,20e-9,100e-9,1e-6):
        a=sinusoid_formula(0.27,5e-9,110e-9,tau)
        b=convolution_simpson(0.27,5e-9,110e-9,tau)
        comparisons.append({'tau_s':tau,'formula_v':a,'convolution_v':b,'abs_error_v':abs(a-b)})
    assert max(item['abs_error_v'] for item in comparisons)<1e-10
    assert coeff(105e-9,0.0)==(0.0,1.0)
    assert coeff(105e-9,float('inf'))==(1.0,0.0)
    assert coeff(0.0,20e-9)==(1.0,0.0)
    # The weighted sum of 8 independent segment innovations: with C_j=C/8,
    # sum((C_j/C)^2*(2kT/C_j)*(1-a^2)) == (2kT/C)*(1-a^2).
    duration=20e-9;tau=20e-9
    alpha,factor=coeff(duration,tau)
    eqvar=2*KB*TEMP/C_HALF
    cap=C_HALF/8
    segment_sum=sum((cap/C_HALF)**2*(2*KB*TEMP/cap)*factor for _ in range(8))
    aggregate=eqvar*factor
    assert abs(segment_sum/aggregate-1)<1e-14
    # Known, nonstationary previous-state variance: exact covariance derivation.
    previous_var=0.37*eqvar
    theoretical_cross=alpha*previous_var
    theoretical_next=alpha*alpha*previous_var+aggregate
    assert theoretical_next<eqvar and theoretical_cross>0
    # Empirical stress of the frozen keyed generator, using consecutive IDs.
    count=200000;burn=2000
    segment=[[] for _ in range(8)]; aggregate_z=[]; state=[];previous=0.0
    for ident in range(count):
        zs=[normal(20261027,j,ident,1) for j in range(1,9)]
        z=sum(zs)/sqrt(8)
        previous=alpha*previous+sqrt(factor)*z
        if ident>=burn:
            for j in range(8):segment[j].append(zs[j])
            aggregate_z.append(z);state.append(previous)
    max_cross=max(abs(cov(segment[j],segment[k])) for j in range(8) for k in range(j+1,8))
    zvar=var(aggregate_z);xvar=var(state);lag=cov(state[1:],state[:-1])
    assert abs(fmean(aggregate_z))<0.02 and abs(zvar-1)<0.03
    assert max_cross<0.02 and abs(xvar-1)<0.04 and abs(lag-alpha)<0.03
    normal_duration=105e-9;normal_tau=5e-9
    normal_alpha,normal_factor=coeff(normal_duration,normal_tau)
    example={'status':'illustrative assumption, NOT measured or circuit qualified',
             'Csignal_half_F':C_HALF,'temperature_K':TEMP,'T_acq_s':normal_duration,
             'tau_s':normal_tau,'R_effective_ohm_if_lumped':normal_tau/C_HALF,
             'retained_voltage_factor':normal_alpha,'innovation_variance_factor':normal_factor,
             'differential_innovation_rms_V':sqrt(eqvar*normal_factor)}
    print(json.dumps({'status':'PASS_math_and_independent_python_only',
        'scope':'not MATLAB, not Simulink, no circuit validation',
        'convolution':comparisons,'max_convolution_abs_error_v':max(c['abs_error_v'] for c in comparisons),
        'aggregate_variance':{'segment_sum_V2':segment_sum,'one_bank_V2':aggregate},
        'conditional_covariance':{'previous_variance_V2':previous_var,'cross_V2':theoretical_cross,
                                  'next_variance_V2':theoretical_next,'alpha':alpha},
        'keyed_empirical':{'count':count-burn,'seed':20261027,'epoch':1,
            'aggregate_mean_z':fmean(aggregate_z),'aggregate_variance':zvar,
            'max_abs_segment_pair_cov':max_cross,'stationary_state_variance':xvar,
            'stationary_lag1_cov':lag,'expected_lag1_cov':alpha},
        'illustrative_5ms':example},indent=2))
