function q = behavior_control_parameters(p)
%BEHAVIOR_CONTROL_PARAMETERS Extract the small explicit controller parameter set.
%Version: v1 (2026-10-27). Caller: behavior model initializer before sar_step.
%Input saved p; output q with sample_period_s [s], SAR1 delta/offset/noise [V]
%and optional SAR2 limit [V]. No full saved parameter/state tree is retained.
%Stateless; no reset, RNG or calibration. This helper copies engineering values,
%not an analog transistor/settling model; coarse noise is not generated here.
    assert(isstruct(p)&&isfield(p,'sar1')&&isfield(p.sar1,'delta_v'), ...
        'behavior:control:parameters','Require saved p.sar1.delta_v.');
    q=struct('sample_period_s',200e-9,'sar1',struct('delta_v',double(p.sar1.delta_v)), ...
        'sar2',struct());
    if isfield(p,'sample_period_s'),q.sample_period_s=double(p.sample_period_s);end
    for f={'coarse_offset_v','coarse_noise_rms_v'}
        if isfield(p.sar1,f{1}),q.sar1.(f{1})=double(p.sar1.(f{1}));end
    end
    if isfield(p,'sar2')&&isfield(p.sar2,'limit_v'),q.sar2.limit_v=double(p.sar2.limit_v);end
    assert(isfinite(q.sar1.delta_v)&&isscalar(q.sar1.delta_v)&&q.sar1.delta_v>0, ...
        'behavior:control:delta','delta_v must be finite positive scalar [V].');
end
