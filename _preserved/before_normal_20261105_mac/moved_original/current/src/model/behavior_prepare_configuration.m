function P=behavior_prepare_configuration(P)
%BEHAVIOR_PREPARE_CONFIGURATION Pure schedule and UnitDelay IC construction.
% Version v1 2026-10-27. Caller: public run/build entry after adc_parameters.
% Inputs named P; output P plus calendar/groups/schedule/n_cycles/stop_time_s
% and xFE0/xBK0/xSC0 numeric initial states. SI units, integer event IDs.
% Acquisition is genuinely opened at -Ts; no old captured state is loaded.
    assert(isstruct(P)&&isscalar(P)&&isfinite(P.Ts_s)&&P.Ts_s>0&& ...
        isfinite(P.N)&&P.N>=1&&P.N==floor(P.N)&& ...
        isfinite(P.first_id)&&P.first_id>=0&&P.first_id==floor(P.first_id), ...
        'adc:configuration','Need positive Ts, integer N>=1 and first_id>=0.');
    assert(P.control.sample_period_s==P.Ts_s,'adc:samplePeriod', ...
        'Controller and configuration sample periods must agree.');
    % Optional wire observation changes storage only, never ADC state/timing.
    % Old saved experiments omit debug; replay them with the observer disabled.
    if ~isfield(P,'debug'),P.debug=struct('adi_enabled',false);end
    assert(isstruct(P.debug)&&isscalar(P.debug)&&isfield(P.debug,'adi_enabled')&& ...
        isscalar(P.debug.adi_enabled)&&ismember(P.debug.adi_enabled,[0 1]), ...
        'adc:debug','debug.adi_enabled must be one logical flag.');
    assert(~P.debug.adi_enabled||P.N==8,'adc:debugN8', ...
        'Full ADI wire observation is restricted to eight output codes.');
    P=behavior_aperture_debug_configuration(P);
    % Optional pure RAadvance output observation; only explicit N8 stores all.
    if ~isfield(P.debug,'dac_enabled'),P.debug.dac_enabled=false;end
    v=P.debug.dac_enabled;
    assert(isscalar(v)&&isreal(v)&&ismember(v,[0 1]),'adc:dacDebug','dac_enabled must be one logical flag.');
    P.debug.dac_enabled=logical(v);
    assert(~v||P.N==8,'adc:dacDebugN8','Full RAadvance observation is restricted to N8.');
    P.debug.dac_max_points=1;if v,P.debug.dac_max_points=Inf;end
    P.debug.adi_max_points=1;
    if P.debug.adi_enabled,P.debug.adi_max_points=Inf;end
    assert(isfield(P.backend.az,'mode')&& ...
        strcmp(P.backend.az.mode,P.digital.az_mode)&& ...
        P.backend.ni.az==~strcmp(P.backend.az.mode,'off'),'adc:azModeJoin', ...
        'Analog mode, NI flag and public digital demodulation must agree.');
    % v1 2026-10-27: transport adds scheduler hits, never ADC calendar events.
    if ~isfield(P,'transport'),P.transport=struct('enabled',false);end
    assert(isstruct(P.transport)&&isscalar(P.transport)&&isfield(P.transport,'enabled')&& ...
        isscalar(P.transport.enabled)&&isreal(P.transport.enabled)&& ...
        ismember(P.transport.enabled,[0 1]),'adc:transport','transport.enabled must be one logical flag.');
    P.transport.enabled=logical(P.transport.enabled);
    P.calendar=behavior_calendar(P.control);
    P.adc_groups=behavior_event_groups(P.calendar,false);
    P.groups=behavior_event_groups(P.calendar,P.transport.enabled);
    P.transport.adc_group_count=numel(P.adc_groups);
    assert(P.transport.adc_group_count==48&& ...
        isequaln(P.groups(1:48),P.adc_groups),'adc:transportPrefix','Original 48 ADC groups must remain exact.');
    assert(numel(P.groups)==48+double(P.transport.enabled),'adc:transportGroups','Only one transport-close group may be appended.');
    % AZ uses existing event boundaries. A new phase allocation requires a
    % deliberate calendar design change, not an implicit interpolated event.
    raStart=P.calendar(strcmp({P.calendar.type},'ra_start')).time_s;
    assert(isscalar(raStart)&&P.backend.az.write_start_s==0&& ...
        P.backend.az.write_end_s==raStart,'adc:azWindow', ...
        'AZ starts at CNV and must end at the existing RA-start event.');
    behavior_az_schedule(0,P.epoch,struct('offset_s',0,'ra_on',false),P);
    P.ni.az=P.backend.ni.az;
    P.transport.flush_cycles=2*double(P.transport.enabled);
    P.n_cycles=P.first_id+P.N+P.transport.flush_cycles;
    P.stop_time_s=(P.n_cycles-1)*P.Ts_s+P.groups(end).time_s;
    P.schedule=struct('sample_period_s',P.Ts_s,'n_cycles',P.n_cycles, ...
        'groups',P.groups,'stop_time_s',P.stop_time_s);

    f=P.front;
    if isfield(f,'group_C_f'),f=rmfield(f,'group_C_f');end
    f.input=P.input;
    f=behavior_jitter_prepare_front(f,P.calendar);
    [fe,P.front]=behavior_frontend_init(f);
    % v1 2026-10-27: bind normalized FE metadata before allowing finite DAC tau.
    % Missing legacy flag is OFF; nonzero tau+OFF is rejected by this helper.
    if ~isfield(P.backend,'dac_coupling'),P.backend.dac_coupling=struct('enabled',false);end
    assert(isstruct(P.backend.dac_coupling)&&isscalar(P.backend.dac_coupling)&& ...
        isfield(P.backend.dac_coupling,'enabled'),'adc:dacCoupling','Need explicit backend.dac_coupling.enabled.');
    P=behavior_dac_coupling_configuration(P,P.backend.dac_coupling.enabled);
    P.ni.dac_settling=P.backend.dac_coupling.enabled&& ...
        any(isfinite(P.front.tau_dac_s)&P.front.tau_dac_s>0);
    % Coverage summary: frontend Cp OR active fixed RA-output load; not a scan.
    P.ni.parasitic=any(P.front.Cp_f>0)|| ...
        (P.backend.ni.cinc_kick&&any(P.backend.ct.output_parasitic_half_f>0));
    P.ni.sample_ktc=P.front.ktc_enabled&&P.front.temperature_K>0;
    P.ni.jitter=P.front.jitter.enabled&&(P.front.jitter.common_sigma_s>0|| ...
        P.front.jitter.local_sigma_s>0||any(P.front.jitter.fixed_slice_skew_s~=0));
    assert(size(P.front.plan,1)>=P.n_cycles+1,'adc:planLength', ...
        'Frontend plan must cover requested records, explicit transport flush CNVs and next acquisition; extend the same seeded plan before apply.');
    cmd=struct('event','acquire_open','t_s',-P.Ts_s,'id',0,'epoch',P.epoch);
    [fe,~]=behavior_frontend_step(fe,cmd,P.front);
    P.xFE0=behavior_frontend_pack(fe);

    initialIds=P.front.plan(1,:);
    initialCtop=sum(P.front.group_C_f(initialIds,:),'all')+sum(P.front.Cp_f(initialIds));
    cmd=struct('qres_c',0,'ctop_f',initialCtop, ...
        'd2_signs',zeros(12,1),'ta_signs',zeros(7,1), ...
        'ra_on',false,'az_on',false,'reset',true,'sample_id',-1,'epoch',P.epoch);
    [bk,~]=behavior_backend_step([],cmd,0,P.backend);
    P.xBK0=behavior_backend_pack(bk);
    [sc,~]=behavior_sar_step([],struct('type','reset'),struct(),P.control);
    P.xSC0=behavior_sar_pack(sc);
    P=behavior_transport_configuration(P);
    P=behavior_reference_configuration(P);
    P=behavior_training_configuration(P);
    % Legacy/factory configurations without bank are explicitly OFF. A
    % present but incomplete flag is an error, never a silent fallback.
    if ~isfield(P,'bank'),P.bank=struct('enabled',false);end
    assert(isstruct(P.bank)&&isscalar(P.bank)&&isfield(P.bank,'enabled'), ...
        'pp:bankMode','Bank configuration must contain an explicit enabled flag.');
    value=P.bank.enabled;
    assert((isnumeric(value)||islogical(value))&&isreal(value)&&isscalar(value)&& ...
        isfinite(double(value))&&any(double(value)==[0 1]), ...
        'pp:bankMode','Bank enabled must be a binary scalar.');
    % Preserve exact legacy P shape when OFF. ON records actual noise coverage;
    % sigma=0 is an explicit zero-noise diagnostic, not NI coverage.
    if P.backend.ni.ra_noise||isfield(P.ni,'ra_noise')
        P.ni.ra_noise=logical(P.backend.ni.ra_noise)&& ...
            P.backend.ra_noise.sigma_vx_rms>0;
    end
    % Derive from actual normalized physical parameters for OU ON and OFF.
    % The actual RaAdvance dialog uses check mode and rejects stale labels.
    P=behavior_ra_noise_guard(P,'derive');
    if value,sar20_pp_verified_parameters(P);end % actual prepared P, fail closed
end
