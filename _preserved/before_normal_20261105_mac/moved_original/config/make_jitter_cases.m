function cases=make_jitter_cases(base)
%MAKE_JITTER_CASES Six N8 aperture cases; pure configuration, no ADC samples.
% Returns6x1 struct(name,P,modified_fields,requires_prepare). Caller must apply
% each P through the real prepare/entry; saved derived state is NOT regenerated
% here. Preserve base input/C/epoch/kTC/DEM/dither/other flags, including seeds.
% Refuse active calibration or unsupported finite sampling; never reset them.
    assert(isstruct(base)&&isscalar(base)&&isfield(base,'front')&& ...
        isfield(base,'control')&&isfield(base,'digital'),'jitterCases:base','Need explicit saved base P.');
    assert(isfield(base.digital,'calibration_mode')&& ...
        strcmp(base.digital.calibration_mode,'off'),'jitterCases:calibration', ...
        'Base digital calibration_mode must be off; do not silently disable it.');
    for key={'training','frozen'}
        if isfield(base,key{1})
            q=base.(key{1});
            assert(isstruct(q)&&isscalar(q)&&isfield(q,'enabled')&& ...
                isscalar(q.enabled)&&ismember(q.enabled,[0 1])&&~q.enabled, ...
                'jitterCases:calibration','Base %s.enabled must be explicitly false.',key{1});
        end
    end
    assert(isfield(base.front,'tau_sample_s')&&all(base.front.tau_sample_s(:)==0), ...
        'jitterCases:finiteSampling','These on cases require settled sampling; preserve/reject finite RC, never reset it.');
    assert(isfield(base,'first_id')&&isfield(base.front,'plan')&& ...
        size(base.front.plan,1)>=base.first_id+9,'jitterCases:plan', ...
        'Existing public plan must already cover N8 and next acquisition; no plan regeneration here.');
    if isfield(base,'calendar'),calendar=base.calendar;
    else,calendar=behavior_calendar(base.control);end
    coarse=calendar(strcmp({calendar.type},'coarse_latch'));
    assert(isscalar(coarse)&&isscalar(coarse.time_s)&&isfinite(coarse.time_s)&&coarse.time_s>0, ...
        'jitterCases:calendar','Need one actual coarse-latch event offset.');
    names={'jitter_off','jitter_common25ps','jitter_local10ps', ...
        'jitter_fixed18_pm8ps','jitter_combined','jitter_combined_repeat'};
    common=[0 25e-12 0 0 25e-12 25e-12];
    local=[0 0 10e-12 0 10e-12 10e-12];
    fixed=linspace(-8e-12,8e-12,18).';
    prototype=struct('name','','P',struct(),'modified_fields',{{}},'requires_prepare',true);
    cases=repmat(prototype,6,1);
    for k=1:6
        P=base;P.N=8;
        if ~isfield(P,'debug'),P.debug=struct();end
        assert(isstruct(P.debug)&&isscalar(P.debug),'jitterCases:debug','Preserve a scalar existing debug struct.');
        P.debug.aperture_enabled=true;P.debug.aperture_max_points=Inf;
        jitter=behavior_jitter_parameters();jitter.enabled=k~=1;
        jitter.common_sigma_s=common(k);jitter.local_sigma_s=local(k);
        if k>=4,jitter.fixed_slice_skew_s=fixed;end
        jitter.seed=20261029;jitter.first_coarse_offset_s=coarse.time_s;
        P.front.jitter=behavior_jitter_parameters(jitter);
        changed={'N','front.jitter','debug.aperture_enabled','debug.aperture_max_points'};
        if isfield(P,'ni')
            assert(isstruct(P.ni)&&isscalar(P.ni),'jitterCases:ni','Preserve scalar existing NI flags.');
            if isfield(P.ni,'jitter')
                P.ni.jitter=logical(jitter.enabled);changed{end+1}='ni.jitter'; %#ok<AGROW>
            end
        end
        cases(k)=struct('name',names{k},'P',P,'modified_fields',{changed},'requires_prepare',true);
    end
    assert(isequaln(cases(5).P,cases(6).P),'jitterCases:repeat','Combined repeat must be exactly the same P/seed.');
end
