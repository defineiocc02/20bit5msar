function [vx_next, diag] = sar20_ra_ou_increment(vx_deterministic, t0_s, t1_s, ...
        tau_ra_s, sigma_vx_rms, seed_u64, epoch, sample_id, enabled, ra_active)
%SAR20_RA_OU_INCREMENT Add one exact OU innovation to an already advanced VX.
%   This is an isolated prototype; it does not own state or modify SarAdc.
%   vx_deterministic [V, differential] must be the EXISTING RA calculation,
%   advanced from the previous TOTAL vx over [t0_s,t1_s]; do not pass a mean
%   propagated from a separate noise-free state. It must be computed before the
%   current endpoint CINC/replica switch kick. The caller's existing single vx
%   owner commits vx_next and then applies the current endpoint switching.
%
%   t0_s,t1_s [s] are exact old-state and event-time binary64 words. tau_ra_s
%   [s] is the constant positive linear RA pole over the interval. sigma_vx_rms
%   [V differential rms] is the fixed-point, stationary OU output deviation;
%   it is an explicit behavior assumption, not an identified circuit value.
%   enabled and ra_active are scalar booleans; ra_active MUST represent the OLD
%   command's ra_on && ~reset for the full interval. seed_u64, epoch, sample_id
%   are passed to sar20_ra_keyed_normal. Finite slew/nonlinear RA is unsupported.
%
%   For active noise-on dt>0: vx_next = vx_deterministic + sigma*sqrt(1-
%   exp(-2*dt/tau))*z. Stable expm1 form is used. For enabled=false, active=false,
%   sigma=0, or dt=0, vx_deterministic is returned directly and no hash runs.
%   Reset decay and digital epoch semantics remain the caller's responsibility.
%
%   No global RNG, persistent data, extra analog state, callbacks, or I/O is used.
    assert(isa(vx_deterministic,'double') && isreal(vx_deterministic) && ...
        isscalar(vx_deterministic) && isfinite(vx_deterministic), ...
        'sar20RA:vx', 'vx_deterministic must be finite scalar double volts.');
    assert(isa(t0_s,'double') && isreal(t0_s) && isscalar(t0_s) && ...
        isfinite(t0_s) && t0_s >= 0 && isa(t1_s,'double') && ...
        isreal(t1_s) && isscalar(t1_s) && isfinite(t1_s) && t1_s >= t0_s, ...
        'sar20RA:time', 'Require finite ordered nonnegative binary64 seconds.');
    assert(is_boolean(enabled) && is_boolean(ra_active), ...
        'sar20RA:flags', 'enabled and ra_active must be scalar 0/1.');
    vx_next = vx_deterministic;
    dt_s = t1_s - t0_s;
    diag = struct('applied',false,'dt_s',dt_s,'z',NaN,'innovation_v',0, ...
        'digest_hex','');
    if ~logical(enabled)
        return;
    end
    assert(isa(sigma_vx_rms,'double') && isreal(sigma_vx_rms) && ...
        isscalar(sigma_vx_rms) && isfinite(sigma_vx_rms) && sigma_vx_rms >= 0, ...
        'sar20RA:sigma', 'sigma_vx_rms must be finite nonnegative double volts.');
    if sigma_vx_rms == 0 || ~logical(ra_active) || dt_s == 0
        return;
    end
    assert(isa(tau_ra_s,'double') && isreal(tau_ra_s) && isscalar(tau_ra_s) && ...
        isfinite(tau_ra_s) && tau_ra_s > 0, ...
        'sar20RA:tau', 'Active noise requires a finite positive double tau in seconds.');
    [z,digest_hex] = sar20_ra_keyed_normal(seed_u64,epoch,sample_id,t0_s,t1_s);
    innovation_v = sigma_vx_rms*sqrt(-expm1(-2*(dt_s/tau_ra_s)))*z;
    vx_next = vx_deterministic + innovation_v;
    assert(isfinite(vx_next), 'sar20RA:finite', 'Noise advance produced nonfinite vx.');
    diag.applied = true;
    diag.z = z;
    diag.innovation_v = innovation_v;
    diag.digest_hex = digest_hex;
end

function yes = is_boolean(x)
    yes = (islogical(x) || isnumeric(x)) && isreal(x) && isscalar(x) && ...
        isfinite(double(x)) && (x == 0 || x == 1);
end
