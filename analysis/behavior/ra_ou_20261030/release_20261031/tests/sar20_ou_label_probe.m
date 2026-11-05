function note=sar20_ou_label_probe(P,note)
% Isolated probe: conditional/helper copied exactly from overlay source.
    if isfield(P.backend.ni,'ra_noise')&&P.backend.ni.ra_noise
        note=[note ra_noise_suffix(P)];
    end
end

function text=ra_noise_suffix(P)
% A model assumption; do not imply measured noise or calibration acceptance.
    behavior_ra_noise_guard(P);
    q=P.backend.ra_noise;
    if q.sigma_vx_rms>0,coverage='已启用（行为假设）';
    else,coverage='零激励，不计噪声覆盖';end
    if isinf(P.control.sar2.limit_v),coverage=[coverage ' | SAR2过量程检测关闭(+Inf)'];end
    seedHex=upper(dec2hex(q.seed_u64,16));
    text=sprintf('\nRA OU=ON | sigmaVX(差分VX固定极点稳态RMS)=%.17g V rms | seed=0x%s | %s', ...
        q.sigma_vx_rms,seedHex,coverage);
end
