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
    if f.ktc_enabled&&any(f.tau_sample_s(:)~=0)
        % The following frontend_init performs full type/range validation.
        % This binding guard only allows the equal-tau single-bank extension.
        t=f.tau_sample_s;
        single=isfield(f,'single_bank')&&isscalar(f.single_bank)&& ...
            (isequal(f.single_bank,true)||isequal(f.single_bank,1));
        equalTau=isscalar(t)||(numel(t)==18&&all(t(1:8)==t(1)));
        assert(single&&equalTau,'behaviorFE:ktcFiniteSamplingUnsupported', ...
            'Finite-RC kTC requires one tau for the single bank numerical segments.');
    end
end
