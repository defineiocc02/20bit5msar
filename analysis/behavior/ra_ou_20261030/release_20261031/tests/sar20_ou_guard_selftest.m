function report=sar20_ou_guard_selftest(Pon)
%SAR20_OU_GUARD_SELFTEST Direct ON guard/setup contracts. NOT YET RUN.
% Pon is the actual prepared v3 N8 ON P; no model, files or RNG are changed.
    assert(isstruct(Pon)&&Pon.backend.ni.ra_noise,'sar20OU:guardTestP','Need actual ON P.');
    original=Pon;rng0=rng;behavior_ra_noise_validate_backend(Pon.backend);behavior_ra_noise_guard(Pon);
    for name={'az_noise','reference_noise','nonlinear_ra','replica_delay'}
        b=Pon.backend;b.ni.(name{1})=true;
        must_error(@()behavior_ra_noise_validate_backend(b),'sar20RA:unsupportedNI');
    end
    b=Pon.backend;b.ni.unknown=true;
    must_error(@()behavior_ra_noise_validate_backend(b),'sar20RA:niSchema');
    b=Pon.backend;b.ra.A0=0;
    must_error(@()behavior_ra_noise_validate_backend(b),'sar20RA:gain');
    b=Pon.backend;b.ct.net_nominal.tracking_count=1;
    must_error(@()behavior_ra_noise_validate_backend(b),'sar20RA:m8Network');
    b=Pon.backend;b.ct.net_nominal.track_f(:,7)=[];
    must_error(@()behavior_ra_noise_validate_backend(b),'sar20RA:m8Network');
    b=Pon.backend;b.ct.net_nominal.track_f(1,1)=0;
    must_error(@()behavior_ra_noise_validate_backend(b),'sar20RA:m8Network');
    b=Pon.backend;b.ni.cap_mismatch=true;b.ct.net_actual.tracking_count=1;
    must_error(@()behavior_ra_noise_validate_backend(b),'sar20RA:m8Network');
    b=Pon.backend;b.ni.cap_mismatch=true;b.ct.net_replica.tracking_count=1;
    must_error(@()behavior_ra_noise_validate_backend(b),'sar20RA:m8Network');
    b=Pon.backend;b.ct.net_nominal.cinc_f(1)=0;
    must_error(@()behavior_ra_noise_validate_backend(b),'sar20RA:ctNetwork');
    b=Pon.backend;b.ct.net_nominal.bridge_f(1)=0;
    must_error(@()behavior_ra_noise_validate_backend(b),'sar20RA:ctNetwork');
    b=Pon.backend;b.ct.net_nominal.main_f(1,1)=-1;
    must_error(@()behavior_ra_noise_validate_backend(b),'sar20RA:ctNetwork');
    b=Pon.backend;b.ct.net_nominal.sub_f(1,1)=0;
    must_error(@()behavior_ra_noise_validate_backend(b),'sar20RA:ctNetwork');
    b=Pon.backend;b.ct.net_nominal.parasitic_main_f(1)=-1;
    must_error(@()behavior_ra_noise_validate_backend(b),'sar20RA:ctNetwork');
    q=Pon;i=find(strcmp({q.calendar.type},'ta_compare'),1);q.calendar(i).bit=0;
    must_error(@()behavior_ra_noise_guard(q),'sar20RA:m8Calendar');
    q=Pon;q.groups(1).time_s=q.groups(1).time_s+1e-12;
    must_error(@()behavior_ra_noise_guard(q),'sar20RA:m8Calendar');
    q=Pon;q.ni.az=true;must_error(@()behavior_ra_noise_guard(q),'sar20RA:coverageAZ');
    q=Pon;q.schedule.n_cycles=q.schedule.n_cycles+1;
    must_error(@()behavior_ra_noise_guard(q),'transportConfig:schedule');
    q=Pon;q.n_cycles=q.n_cycles+1;
    must_error(@()behavior_ra_noise_guard(q),'transportConfig:flush');
    q=Pon;q.transport.kind_by_group(1)=0;
    must_error(@()behavior_ra_noise_guard(q),'sar20RA:transportBinding');
    q=Pon;q.backend.ra.A0=Inf;q.ni.ra_finite_gain=true;
    must_error(@()behavior_ra_noise_guard(q),'sar20RA:coverageGain');
    q.ni.ra_finite_gain=false;behavior_ra_noise_guard(q);
    q=Pon;q.ni.ra_finite_bandwidth=false;
    must_error(@()behavior_ra_noise_guard(q),'sar20RA:coverageBandwidth');
    q=Pon;q.ni.sample_settling=true;
    must_error(@()behavior_ra_noise_guard(q),'sar20RA:coverageSampling');
    q=Pon;q.front.tau_sample_s(:)=Inf;q.ni.sample_settling=true;
    must_error(@()behavior_ra_noise_guard(q),'sar20RA:coverageSampling');
    q.ni.sample_settling=false;behavior_ra_noise_guard(q); % Inf is hold, not finite settling
    q=Pon;q.front.tau_sample_s(1)=1e-9;q.ni.sample_settling=false;
    must_error(@()behavior_ra_noise_guard(q),'sar20RA:coverageSampling');
    q.ni.sample_settling=true;behavior_ra_noise_guard(q);
    q=Pon;q.ni.cap_mismatch=true;
    must_error(@()behavior_ra_noise_guard(q),'sar20RA:coverageCap');
    q=Pon;q.front.mismatch_enabled=true;q.ni.cap_mismatch=true; % flag ON but zero actual mismatch
    must_error(@()behavior_ra_noise_guard(q),'sar20RA:coverageCap');
    q.ni.cap_mismatch=false;behavior_ra_noise_guard(q);
    q=Pon;q.front.mismatch_enabled=true;q.front.C_f(1,1)=q.front.C_f(1,1)*(1+1e-6);
    q.ni.cap_mismatch=true;must_error(@()behavior_ra_noise_guard(q),'sar20RA:staleGroupC');
    q.front.group_C_f=[sum(q.front.C_f(:,1:33),2),sum(q.front.C_f(:,34:37),2),q.front.C_f(:,38)];
    q.ni.cap_mismatch=false;must_error(@()behavior_ra_noise_guard(q),'sar20RA:coverageCap');
    q.ni.cap_mismatch=true;behavior_ra_noise_guard(q);
    q=Pon;q.backend.ni.cap_mismatch=true;q.backend.ct.net_actual.main_f(1,1)= ...
        q.backend.ct.net_actual.main_f(1,1)*(1+1e-6);q.ni.cap_mismatch=false;
    must_error(@()behavior_ra_noise_guard(q),'sar20RA:coverageCap');
    q.ni.cap_mismatch=true;behavior_ra_noise_guard(q);
    q=Pon;q.ni.parasitic=false;
    must_error(@()behavior_ra_noise_guard(q),'sar20RA:coverageParasitic');
    q=Pon;q.control.sar1.delta_v=NaN;must_error(@()behavior_ra_noise_guard(q),'sar20RA:control');
    q=Pon;q.control.sar1.coarse_offset_v=NaN;must_error(@()behavior_ra_noise_guard(q),'sar20RA:control');
    q=Pon;q.control.sar2.limit_v=NaN;must_error(@()behavior_ra_noise_guard(q),'sar20RA:control');
    q=Pon;q.control.sar2.limit_v=0;must_error(@()behavior_ra_noise_guard(q),'sar20RA:control');
    q=Pon;q.control.sar2.limit_v=Inf;behavior_ra_noise_guard(q); % explicitly disables range check
    q=Pon;q.digital.tracking_mode='not_finite_sinc2';
    must_error(@()behavior_ra_noise_guard(q),'sar20RA:m8Digital');
    % kT/C and jitter coverage track actual enable/temperature/amplitudes.
    q=Pon;q.front.ktc_enabled=true;q.ni.sample_ktc=false;
    must_error(@()behavior_ra_noise_guard(q),'sar20RA:coverageKTC');
    q.ni.sample_ktc=true;behavior_ra_noise_guard(q);
    q.front.temperature_K=0;must_error(@()behavior_ra_noise_guard(q),'sar20RA:coverageKTC');
    q.ni.sample_ktc=false;behavior_ra_noise_guard(q);
    q=Pon;q.front.jitter.enabled=true;q.front.jitter.common_sigma_s=1e-12;q.ni.jitter=false;
    must_error(@()behavior_ra_noise_guard(q),'sar20RA:coverageJitter');
    q.ni.jitter=true;behavior_ra_noise_guard(q);
    q.front.jitter.common_sigma_s=0;must_error(@()behavior_ra_noise_guard(q),'sar20RA:coverageJitter');
    q.ni.jitter=false;behavior_ra_noise_guard(q);
    % Direct workspace flag edits may not bypass the existing finite-RC ban.
    for tau=[1e-9 Inf]
        q=Pon;q.front.tau_sample_s(:)=tau;q.ni.sample_settling=isfinite(tau);
        q.front.ktc_enabled=true;q.front.temperature_K=0;q.ni.sample_ktc=false;
        must_error(@()behavior_dac_backend_parameters(q),'sar20RA:coverageKTC');
        q=Pon;q.front.tau_sample_s(:)=tau;q.ni.sample_settling=isfinite(tau);
        q.front.jitter.enabled=true;q.ni.jitter=false; % even zero amplitude is unsupported with RC
        must_error(@()behavior_dac_backend_parameters(q),'sar20RA:coverageJitter');
    end
    % Replica mismatch counts only if its real numerical path can affect VX.
    q=Pon;q.backend.ni.cap_mismatch=true;q.backend.ni.cinc_kick=false;
    q.backend.ct.net_replica.track_f(1,1)=q.backend.ct.net_replica.track_f(1,1)*(1+1e-4);
    q.ni.parasitic=false;q.ni.cap_mismatch=false;behavior_ra_noise_guard(q);
    q.ni.cap_mismatch=true;must_error(@()behavior_ra_noise_guard(q),'sar20RA:coverageCap');
    q.backend.ni.cinc_kick=true;q.ni.parasitic=true;behavior_ra_noise_guard(q);
    q.backend.ct.replica_enabled=false;behavior_ra_noise_guard(q); % passive replica load still acts
    % Explicit apply/prepare re-derives stale labels from physical values.
    q=Pon;q.backend.ra.A0=Inf;q.ni.ra_finite_gain=true;
    q=behavior_prepare_configuration(q);assert(~q.ni.ra_finite_gain,'sar20OU:deriveGain','Inf A0 must not count finite.');
    q=Pon;q.front.tau_sample_s(:)=Inf;q.ni.sample_settling=true;
    q=behavior_prepare_configuration(q);assert(~q.ni.sample_settling,'sar20OU:deriveSample','Inf hold must not count finite.');
    q=Pon;q.front.tau_sample_s(1)=1e-9;q.ni.sample_settling=false;
    q=behavior_prepare_configuration(q);assert(q.ni.sample_settling,'sar20OU:deriveSample','Positive finite sampling tau must count.');
    q=Pon;q.front.mismatch_enabled=true;q.ni.cap_mismatch=true; % C remains nominal
    q=behavior_prepare_configuration(q);assert(~q.ni.cap_mismatch,'sar20OU:deriveCap','Nominal C must not count mismatch.');
    q=Pon;q.front.mismatch_enabled=true;q.front.C_f(1,1)=q.front.C_f(1,1)*(1+1e-6);q.ni.cap_mismatch=false;
    q=behavior_prepare_configuration(q);assert(q.ni.cap_mismatch,'sar20OU:deriveCap','Selected nonnominal C must count.');
    q=Pon;q.front.ktc_enabled=true;q.front.temperature_K=0;q.ni.sample_ktc=true;
    q=behavior_prepare_configuration(q);assert(~q.ni.sample_ktc,'sar20OU:deriveKTC','Zero temperature must not count kT/C.');
    q=Pon;q.front.jitter.enabled=true;q.ni.jitter=true; % all amplitudes remain zero
    q=behavior_prepare_configuration(q);assert(~q.ni.jitter,'sar20OU:deriveJitter','Zero amplitudes must not count jitter.');
    % The real RaAdvance dialog calls behavior_dac_backend_parameters(P):
    % prove the same bad workspace P reaches the guard, not only direct calls.
    q=Pon;q.ni.sample_settling=true;
    must_error(@()behavior_dac_backend_parameters(q),'sar20RA:coverageSampling');
    q=Pon;q.front.mismatch_enabled=true;q.front.C_f(1,1)=q.front.C_f(1,1)*(1+1e-6);q.ni.cap_mismatch=true;
    must_error(@()behavior_dac_backend_parameters(q),'sar20RA:staleGroupC');
    q=Pon;q.backend.ct.net_nominal.tracking_count=1;
    must_error(@()behavior_dac_backend_parameters(q),'sar20RA:m8Network');
    q=Pon;q.backend.ni.reference_noise=true;
    must_error(@()behavior_dac_backend_parameters(q),'sar20RA:unsupportedNI');
    assert(isequaln(original,Pon)&&isequaln(rng0,rng),'sar20OU:guardMutation','P or RNG changed.');
    report=struct('status','candidate_ON_guard_contract_passed', ...
        'scope',['Only direct ON guard/setup behavior; actual S-function compile and ' ...
        'direct-workspace bypass tests require separately controlled native execution.']);
end
function must_error(fun,id)
    caught=false;
    try,fun();catch e,caught=true;assert(strcmp(e.identifier,id), ...
        'sar20OU:guardWrongError','Expected %s, got %s.',id,e.identifier);end
    assert(caught,'sar20OU:guardMissingError','Expected %s.',id);
end
