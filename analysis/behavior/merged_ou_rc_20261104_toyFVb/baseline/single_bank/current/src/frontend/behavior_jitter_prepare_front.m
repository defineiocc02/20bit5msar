function f=behavior_jitter_prepare_front(f,calendar)
%BEHAVIOR_JITTER_PREPARE_FRONT Bind aperture bound to actual coarse event.
% Caller: prepare_configuration after behavior_calendar, before frontend_init.
% No timing/event insertion. Remains an explicit rejection of finite-RC jitter.
    if ~isfield(f,'jitter'),f.jitter=behavior_jitter_parameters();end
    c=calendar(strcmp({calendar.type},'coarse_latch'));
    assert(isscalar(c),'behaviorFE:jitterCalendar','Need one first coarse-latch event.');
    f.jitter.first_coarse_offset_s=c.time_s;
    f.jitter=behavior_jitter_parameters(f.jitter);
    assert(~f.jitter.enabled||all(f.tau_sample_s==0), ...
        'behaviorFE:jitterFiniteSamplingUnsupported', ...
        'Endpoint aperture mode requires fully settled sampling; finite-RC aperture propagation is not implemented.');
    assert(~f.ktc_enabled||all(f.tau_sample_s==0), ...
        'behaviorFE:ktcFiniteSamplingUnsupported', ...
        'Full equilibrium kTC cannot be combined with finite sampling RC.');
end
