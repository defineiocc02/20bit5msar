function [z, digest_hex] = sar20_ra_keyed_normal(seed_u64, epoch, sample_id, t0_s, t1_s)
%SAR20_RA_KEYED_NORMAL Deterministic, domain-separated interval Gaussian.
%   All inputs are scalar; seed_u64 must be uint64. epoch and sample_id are
%   nonnegative integer doubles < flintmax. t0_s/t1_s are binary64 seconds,
%   finite, nonnegative, and strictly increasing. Full binary64 endpoint bits
%   enter the hash, NOT rounded decimal text or s.time+dt reconstruction.
%
%   Payload = ASCII 'SAR20-RA-OU-v1' + NUL, then 5 big-endian uint64 words:
%       seed, epoch, sample_id, IEEE754(t0_s), IEEE754(t1_s).
%   SHA-256's first 16 bytes yield two 52-bit open-interval uniforms and a
%   Box-Muller normal. The random-access key is not a global RNG or persistent
%   stream. Hashing compresses the full tuple: collisions are possible in
%   principle; finite 52-bit uniforms limit normal tails. No BER claim follows.
%
%   Same seed/epoch/ID/endpoint bit patterns imply repeatable digest; floating
%   log/cos may still vary in their last bits across platforms/libraries.
    assert(isa(seed_u64,'uint64') && isscalar(seed_u64), ...
        'sar20RA:seed', 'seed_u64 must be scalar uint64.');
    epoch64 = exact_nonnegative_double(epoch, 'epoch');
    id64 = exact_nonnegative_double(sample_id, 'sample_id');
    assert(isa(t0_s,'double') && isreal(t0_s) && isscalar(t0_s) && ...
        isfinite(t0_s) && t0_s >= 0 && isa(t1_s,'double') && ...
        isreal(t1_s) && isscalar(t1_s) && isfinite(t1_s) && t1_s > t0_s, ...
        'sar20RA:time', 'Require finite increasing nonnegative binary64 seconds.');
    if t0_s == 0, t0_s = 0; end % canonicalize -0 to +0
    if t1_s == 0, t1_s = 0; end
    w0 = typecast(t0_s, 'uint64');
    w1 = typecast(t1_s, 'uint64');
    payload = [uint8('SAR20-RA-OU-v1'), uint8(0), ...
        big_endian_u64(seed_u64), big_endian_u64(epoch64), ...
        big_endian_u64(id64), big_endian_u64(w0), big_endian_u64(w1)];
    assert(usejava('jvm'), 'sar20RA:jvm', 'The SHA-256 candidate requires a MATLAB JVM.');
    md = java.security.MessageDigest.getInstance('SHA-256');
    md.update(typecast(payload(:), 'int8'));
    raw = md.digest();
    digest = typecast(raw(:), 'uint8');
    assert(numel(digest) == 32, 'sar20RA:digest', 'SHA-256 digest must be 32 bytes.');
    a = read_big_endian_u64(digest(1:8));
    b = read_big_endian_u64(digest(9:16));
    scale = 4503599627370496; % 2^52, exactly representable in binary64
    u1 = (double(bitshift(a, -12)) + 0.5) / scale;
    u2 = (double(bitshift(b, -12)) + 0.5) / scale;
    assert(u1 > 0 && u1 < 1 && u2 > 0 && u2 < 1, ...
        'sar20RA:uniform', 'Both 52-bit uniforms must be strictly inside (0,1).');
    z = sqrt(-2*log(u1))*cos(2*pi*u2);
    assert(isfinite(z), 'sar20RA:normal', 'Generated normal must be finite.');
    if nargout > 1
        digest_hex = lower(reshape(dec2hex(digest,2).', 1, []));
    end
end

function v = exact_nonnegative_double(x, name)
    assert(isa(x,'double') && isreal(x) && isscalar(x) && isfinite(x) && ...
        x >= 0 && x < flintmax && x == fix(x), ...
        'sar20RA:tag', '%s must be a nonnegative exact integer double.', name);
    v = uint64(x);
end

function b = big_endian_u64(w)
    b = zeros(1,8,'uint8');
    for k = 1:8
        b(k) = uint8(bitand(bitshift(w,-8*(8-k)),uint64(255)));
    end
end

function w = read_big_endian_u64(b)
    w = uint64(0);
    for k = 1:8
        w = bitor(bitshift(w,8),uint64(b(k)));
    end
end
