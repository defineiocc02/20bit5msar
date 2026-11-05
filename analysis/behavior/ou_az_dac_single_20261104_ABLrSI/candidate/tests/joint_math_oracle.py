#!/usr/bin/env python3
"""Independent high-precision quadrature and keyed-sample statistics.

This runs Python only. The float candidate formula is a transcription, not an
execution of MATLAB source; use test_joint_ou_az_dac.m for the actual functions.
"""
import hashlib
import json
import math
import struct
from pathlib import Path

import mpmath as mp

mp.mp.dps = 70


def decay(h, tau):
    return math.exp(-h / tau)


def h_response(h, tau, ti):
    if ti == 0:
        return 0.0
    if math.isinf(ti):
        return -math.expm1(-h / tau)
    if ti == tau:
        return (h / tau) * math.exp(-h / tau)
    q = h * (1 / tau - 1 / ti)
    if abs(q) < 0.5:
        return math.exp(-h / tau) * math.expm1(q) / (1 - tau / ti)
    return ti / (ti - tau) * (decay(h, ti) - decay(h, tau))


def az_response(h, tau, ti):
    if math.isfinite(ti) and ti > 0 and ti != tau and abs(ti - tau) <= max(ti, tau) * 2**-20:
        x = h / tau
        base = x * math.exp(-x)
        d = x - h / ti
        return base if d == 0 else base * math.expm1(d) / d
    return h_response(h, tau, ti)


def dac_response(h, tr, td):
    x, y = h / tr, h / td
    if max(x, y) < 0.01:
        r, denominator = 0.0, 1.0
        for degree in range(2, 13):
            denominator *= degree
            homogeneous = sum(x**k * y**(degree - 2 - k) for k in range(degree - 1))
            r += (-1)**degree * x * y * homogeneous / denominator
        return r
    if abs(x - y) < 0.5:
        d = x - y
        hval = x * math.exp(-x) if d == 0 else x * math.exp(-x) * math.expm1(d) / d
        return -math.expm1(-x) - hval
    if min(x, y) > 0.1:
        return -math.expm1(-x) - h_response(h, tr, td)
    return (-x * math.expm1(-y) + y * math.expm1(-x)) / (x - y)


def float_mean(h, tau, poles, dac_poles):
    # Dimensionless but nontrivial affine drive and two AZ and three DAC terms.
    x0, gain, ng, q0, cf, vos = 0.23, 0.91, 3.2, -0.17, 0.8, 0.011
    initial, target = (0.021, -0.004), (0.005, -0.002)
    dq = (0.03, -0.012, 0.009)
    xinf = gain * (q0 / cf + ng * (vos - target[0] + target[1]))
    x = xinf + (x0 - xinf) * decay(h, tau)
    for amp, ti in zip((-gain * ng * (initial[0] - target[0]),
                        gain * ng * (initial[1] - target[1])), poles):
        x += amp * az_response(h, tau, ti)
    for d, td in zip(dq, dac_poles):
        x += gain * d / cf * dac_response(h, tau, td)
    return x


def quadrature_mean(h, tau, poles, dac_poles):
    h, tau = mp.mpf(h), mp.mpf(tau)
    poles, dac_poles = [mp.mpf(x) for x in poles], [mp.mpf(x) for x in dac_poles]
    x0, gain, ng, q0, cf, vos = map(mp.mpf, (0.23, 0.91, 3.2, -0.17, 0.8, 0.011))
    initial = list(map(mp.mpf, (0.021, -0.004)))
    target = list(map(mp.mpf, (0.005, -0.002)))
    dq = list(map(mp.mpf, (0.03, -0.012, 0.009)))

    def integrand(u):
        az = [target[k] + (initial[k] - target[k]) * mp.exp(-u / poles[k]) for k in range(2)]
        q = q0 + sum(dq[k] * (1 - mp.exp(-u / dac_poles[k])) for k in range(3))
        drive = gain * (q / cf + ng * (vos - az[0] + az[1]))
        return mp.exp(-(h - u) / tau) * drive / tau

    return mp.exp(-h / tau) * x0 + mp.quad(integrand, [0, h])


def z_key(seed, epoch, sample_id, t0, t1):
    payload = b'SAR20-RA-OU-v1\0' + struct.pack('>QQQdd', seed, epoch, sample_id, t0, t1)
    digest = hashlib.sha256(payload).digest()
    a, b = struct.unpack('>QQ', digest[:16])
    u1, u2 = ((a >> 12) + 0.5) / 2**52, ((b >> 12) + 0.5) / 2**52
    assert 0 < u1 < 1 and 0 < u2 < 1
    return math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)


def main():
    tau = 7e-9
    cases = []
    for ratio in (0.005, 0.8, 2.0, 10.0):
        for pole in (tau, math.nextafter(tau, 0.0), math.nextafter(tau, math.inf), 0.3*tau, 12*tau):
            h = ratio * tau
            poles = (pole, math.inf)
            dacs = (pole, tau * 0.2, tau * 8)
            got = float_mean(h, tau, poles, dacs)
            ref = float(quadrature_mean(h, tau, poles, dacs))
            cases.append(abs(got - ref))
    max_error = max(cases)
    assert max_error < 2e-13, max_error

    # Stationary N0, then two distinct keyed intervals. This is a finite
    # empirical check over seeds, not proof that SHA-derived keys are IID.
    n = 40000
    h1, h2 = 12.5e-9, 6.25e-9
    a1, a2 = math.exp(-h1 / tau), math.exp(-h2 / tau)
    b1, b2 = math.sqrt(-math.expm1(-2*h1/tau)), math.sqrt(-math.expm1(-2*h2/tau))
    sums = [0.0]*6
    # A second experiment starts with deterministic X0 and superimposes the
    # very same nonconstant AZ+DAC mean verified by quadrature above.
    sigma = 0.03
    mean1 = float(quadrature_mean(h1,tau,(tau,math.inf),(tau,0.2*tau,8*tau)))
    mean2 = float(quadrature_mean(h1+h2,tau,(tau,math.inf),(tau,0.2*tau,8*tau)))
    joint = [0.0]*5
    cross_z = 0.0
    for seed in range(n):
        z0 = z_key(seed, 1, 0, 0.0, 1e-9)
        z1 = z_key(seed, 1, 0, 31.25e-9, 43.75e-9)
        z2 = z_key(seed, 1, 0, 43.75e-9, 50e-9)
        n0 = z0
        n1 = a1*n0+b1*z1
        n2 = a2*n1+b2*z2
        for i, v in enumerate((n0,n1,n2,n1*n1,n2*n2,n1*n2)):
            sums[i] += v
        v1=b1*z1
        v2=a2*v1+b2*z2
        x1=mean1+sigma*v1
        x2=mean2+sigma*v2
        for i,v in enumerate((x1,x2,x1*x1,x2*x2,x1*x2)):
            joint[i] += v
        cross_z += z1*z2
    means = [v/n for v in sums[:3]]
    var1 = sums[3]/n-means[1]**2
    var2 = sums[4]/n-means[2]**2
    cov12 = sums[5]/n-means[1]*means[2]
    assert max(map(abs,means)) < 0.025
    assert abs(var1-1) < 0.04 and abs(var2-1) < 0.04
    assert abs(cov12-a2) < 0.04 and abs(cross_z/n) < 0.025
    jm1,jm2 = joint[0]/n,joint[1]/n
    jv1=(joint[2]/n-jm1*jm1)/sigma**2
    jv2=(joint[3]/n-jm2*jm2)/sigma**2
    jc=(joint[4]/n-jm1*jm2)/sigma**2
    theory_v1=1-a1*a1
    theory_v2=1-(a1*a2)**2
    theory_c=a2*theory_v1
    assert abs((jm1-mean1)/sigma)<0.025 and abs((jm2-mean2)/sigma)<0.025
    assert abs(jv1-theory_v1)<0.04 and abs(jv2-theory_v2)<0.04 and abs(jc-theory_c)<0.04
    result = {
        'status': 'python_quadrature_and_empirical_checks_passed',
        'matlab_source_executed': False,
        'deterministic_cases': len(cases),
        'max_absolute_quadrature_difference': max_error,
        'quadrature_precision_decimal_digits': 70,
        'independent_seed_count': n,
        'stationary_means_over_sigma': means,
        'stationary_variances_over_sigma2': [var1,var2],
        'lag_covariance_over_sigma2': cov12,
        'theory_lag_covariance_over_sigma2': a2,
        'innovation_product_mean': cross_z/n,
        'joint_az_dac_zero_noise_initial_mean': [jm1,jm2],
        'joint_az_dac_independent_quadrature_mean': [mean1,mean2],
        'joint_az_dac_variances_over_sigma2': [jv1,jv2],
        'joint_az_dac_theory_variances_over_sigma2': [theory_v1,theory_v2],
        'joint_az_dac_covariance_over_sigma2': jc,
        'joint_az_dac_theory_covariance_over_sigma2': theory_c,
        'limitations': 'Python transcription; finite seed ensemble; does not prove IID or execute MATLAB/Simulink.'
    }
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
