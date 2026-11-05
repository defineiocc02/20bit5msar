function report=test_single_rc_ktc()
% Draft function-only verification. NOT yet executed in MATLAB or Simulink.
% One bank, eight numerical segments, 5 MS/s. No ADI and no 10M.
    pkg=fileparts(fileparts(mfilename('fullpath')));
    assert(~bdIsLoaded('SarAdc'),'rcKtcTest:model','Do not load a model for this function test.');
    oldPath=path;restore=onCleanup(@()path(oldPath)); %#ok<NASGU>
    addpath(genpath(fullfile(pkg,'current','src')),fullfile(pkg,'config'),pkg, ...
        fullfile(pkg,'tests','baseline_v2'),'-begin');rehash;
    rngBefore=rng;
    P0=adc_parameters();f=P0.front;
    f=rmfield(f,'group_C_f');f.plan=[];f.plan_rows=8194;
    f.single_guard_s=5e-9;
    f.input=struct('offset_v',-0.12,'amplitude_v',0.6,'frequency_hz',1.31e6,'phase_rad',0.37);
    ids=(1:8).';

    % Original v2 bytewise packed-state/output comparison: all OFF modes,
    % plus tau=0 equilibrium ON. All event inputs are identical.
    cases=[0 0;20e-9 0;Inf 0;0 1];
    for k=1:size(cases,1)
        g=f;g.tau_sample_s=cases(k,1);g.ktc_enabled=logical(cases(k,2));
        [a,pa]=behavior_frontend_init_v2(g);[b,pb]=behavior_frontend_init(g);
        assert(isequaln(pa,pb),'rcKtcTest:legacyParameters','Normalized parameters changed.');
        cmds=legacy_commands();
        for m=1:numel(cmds)
            [a,oa]=behavior_frontend_step_v2(a,cmds{m},pa);
            [b,ob]=behavior_frontend_step(b,cmds{m},pb);
            assert(bits(behavior_frontend_pack(a),behavior_frontend_pack(b))&&deep_bits(oa,ob), ...
                'rcKtcTest:legacyOutput','Legacy mismatch at case %d event %d.',k,m);
        end
    end

    % Retained charge remains constant through the guard; a true input-change
    % event splits the deterministic convolution, not the thermal innovation.
    g=f;g.tau_sample_s=20e-9;g.ktc_enabled=false;
    [s,p]=behavior_frontend_init(g);
    v0=linspace(-0.3,0.3,8).';s.B_c(ids,1)=p.group_C_f(ids,1).*v0;
    [s,~]=behavior_frontend_step(s,command('acquire_open',0,0,1),p);
    held=s.B_c(ids,1);
    [s,~]=behavior_frontend_step(s,command('observe',3e-9,0,1),p);
    assert(bits(held,s.B_c(ids,1)),'rcKtcTest:guardHold','B changed before the physical open.');
    tChange=45e-9;tCapture=110e-9;
    u2=struct('offset_v',0.2,'amplitude_v',0.4,'frequency_hz',0.93e6,'phase_rad',0.11);
    change=command('input_change',tChange,0,1);change.input=u2;
    [s,~]=behavior_frontend_step(s,change,p);
    [s,~]=behavior_frontend_step(s,command('capture',tCapture,0,1),p);
    expected=rc_integral_oracle(v0,5e-9,tChange,20e-9,f.input);
    expected=rc_integral_oracle(expected,tChange,tCapture,20e-9,u2);
    assert(max(abs(s.v_capture_v(ids)-expected))<1e-12, ...
        'rcKtcTest:piecewiseRC','Piecewise input convolution or retained initial charge differs.');

    % Isolate the innovation with zero signal and identical tuple/key. For tau=0
    % the original equilibrium noise is reused, then scaled by sqrt(1-a^2).
    g=f;g.input=struct('offset_v',0,'amplitude_v',0,'frequency_hz',0,'phase_rad',0);
    g.ktc_enabled=true;g.tau_sample_s=0;
    [settled,~]=capture_from(g,zeros(8,1),110e-9,0,1);
    g.tau_sample_s=20e-9;
    [finite,pfinite]=capture_from(g,zeros(8,1),110e-9,0,1);
    scale=sqrt(-expm1(-2*105e-9/20e-9));
    assert(max(abs(finite.v_capture_v(ids)-scale*settled.v_capture_v(ids)))<1e-18, ...
        'rcKtcTest:innovationScale','Finite time scaling differs from the independent formula.');
    assert(bits(finite.q_initial_c(ids),sum(finite.B_c(ids,:),2)), ...
        'rcKtcTest:sameCharge','Noise must be injected before the captured charge latch.');
    % Identical keyed draws cancel from the difference between two returned B
    % initial states, proving that the old contribution only decays once.
    prior=linspace(-1e-3,1e-3,8).';
    [retained,~]=capture_from(g,prior,110e-9,0,1);
    observed=retained.v_capture_v(ids)-finite.v_capture_v(ids);
    assert(max(abs(observed-prior*exp(-105e-9/20e-9)))<1e-15, ...
        'rcKtcTest:returnedNoise','The returned contribution was lost or counted twice.');

    % Infinite tau: retain every signal-charge bit and add no innovation.
    g.tau_sample_s=Inf;
    [hold,phold,before]=capture_from(g,prior,110e-9,0,1);
    assert(bits(hold.B_c(ids,1),before)&&all(hold.actual_aperture_s(ids)==110e-9), ...
        'rcKtcTest:infiniteHold','Infinite tau must hold B without new noise.');
    assert(numel(behavior_frontend_pack(hold))==353&& ...
        numel(behavior_frontend_pack(finite))==353,'rcKtcTest:ABI','FE state ABI changed.');
    assert(all(isinf(phold.tau_sample_s(ids))),'rcKtcTest:infiniteTau','Wrong hold config.');
    % T=0: no signal innovation. Preserve numeric equality; exact signed-zero
    % identity is not asserted for adding zero to an enabled-noise path.
    g.tau_sample_s=20e-9;g.temperature_K=0;
    [cold,~]=capture_from(g,prior,110e-9,0,1);
    g.ktc_enabled=false;[disabled,~]=capture_from(g,prior,110e-9,0,1);
    assert(isequal(cold.B_c(ids,1),disabled.B_c(ids,1)), ...
        'rcKtcTest:zeroTemperature','T=0 produced a nonzero thermal innovation.');

    % Same direct call and same tuple are deterministic; the global RNG does
    % not advance even though the stateless key is evaluated in Outputs.
    g.ktc_enabled=true;g.temperature_K=298.15;
    [s,p]=behavior_frontend_init(g);[s,~]=behavior_frontend_step(s,command('acquire_open',0,0,1),p);
    [a,oa]=behavior_frontend_step(s,command('capture',110e-9,0,1),p);
    [b,ob]=behavior_frontend_step(s,command('capture',110e-9,0,1),p);
    assert(bits(behavior_frontend_pack(a),behavior_frontend_pack(b))&&deep_bits(oa,ob), ...
        'rcKtcTest:repeatedOutputs','Repeated evaluation produced a different next state.');
    assert(isequaln(rngBefore,rng),'rcKtcTest:rng','Global RNG advanced.');

    % Unequal segment taus and finite-RC+jitter must remain rejected even if
    % a previously normalized p is edited after initialization.
    bad=g;bad.tau_sample_s=repmat(20e-9,18,1);bad.tau_sample_s(2)=21e-9;
    expect_error(@()behavior_frontend_init(bad),'singleBank:ktcUnequalTau');
    badp=p;badp.tau_sample_s(2)=21e-9;
    expect_error(@()behavior_frontend_step(s,command('capture',110e-9,0,1),badp), ...
        'singleBank:ktcUnequalTau');
    badp=p;badp.jitter.enabled=true;
    expect_error(@()behavior_frontend_step(s,command('capture',110e-9,0,1),badp), ...
        'behaviorFE:jitterFiniteSamplingUnsupported');
    beforeOpen=command('reset',3e-9,0,1);
    [resetOk,~]=behavior_frontend_step(s,beforeOpen,p);
    assert(all(resetOk.phase==0),'rcKtcTest:preopenReset','Pre-open reset should remain safe.');
    expect_error(@()behavior_frontend_step(s,command('reset',6e-9,0,1),p), ...
        'singleBank:ktcInterruptedAcquisition');

    % Real preparation/coverage path and repeated stage evaluation; no model.
    P=P0;P.front.single_guard_s=5e-9;P.front.ktc_enabled=true;P.front.tau_sample_s(:)=20e-9;
    P=behavior_prepare_configuration(P);behavior_ra_noise_guard(P,'check');
    assert(P.ni.sample_ktc&&P.ni.sample_settling&&~P.ni.jitter&&numel(P.xFE0)==353, ...
        'rcKtcTest:coverage','Finite-RC and kTC coverage/ABI differ.');
    c=[0;0;P.epoch;1;0;0];
    [x1,o1]=behavior_frontend_stage('advance',P.xFE0,c,P.front);
    [x2,o2]=behavior_frontend_stage('advance',P.xFE0,c,P.front);
    assert(bits(x1,x2)&&bits(o1,o2),'rcKtcTest:stage','Repeated stage output differs.');
    P.front.tau_sample_s(:)=Inf;P=behavior_prepare_configuration(P);behavior_ra_noise_guard(P,'check');
    assert(~P.ni.sample_ktc&&~P.ni.sample_settling,'rcKtcTest:holdCoverage', ...
        'Inf tau may not report new thermal innovation or finite settling.');
    P.front.tau_sample_s(9)=20e-9;P=behavior_prepare_configuration(P);
    behavior_ra_noise_guard(P,'check');
    assert(~P.ni.sample_ktc&&~P.ni.sample_settling,'rcKtcTest:inactiveRows', ...
        'Inactive rows 9:18 must not claim sampling coverage for this bank.');

    % Empirical covariance of the ACTUAL MATLAB function in a controlled
    % return-to-open AR(1) fixture, not an actual backend conversion run.
    g.input=struct('offset_v',0,'amplitude_v',0,'frequency_hz',0,'phase_rad',0);
    g.tau_sample_s=20e-9;g.temperature_K=298.15;g.ktc_enabled=true;
    [s0,p]=behavior_frontend_init(g);eqvar=2*1.380649e-23*g.temperature_K/sum(p.group_C_f(ids,1));
    alpha=exp(-1);count=8192;burn=1024;series=zeros(count-burn,1);x=0;
    for k=1:count
        q=s0;q.B_c(ids,1)=p.group_C_f(ids,1)*x;
        [q,~]=behavior_frontend_step(q,command('acquire_open',0,k-1,1),p);
        [q,~]=behavior_frontend_step(q,command('capture',25e-9,k-1,1),p);
        x=sum(q.B_c(ids,1))/sum(p.group_C_f(ids,1));
        if k>burn,series(k-burn)=x/sqrt(eqvar);end
    end
    y=series-mean(series);sampleVar=mean(y.^2);lag1=mean(y(2:end).*y(1:end-1));
    assert(abs(mean(series))<0.08&&abs(sampleVar-1)<0.12&&abs(lag1-alpha)<0.08, ...
        'rcKtcTest:covariance','Sample variance/covariance differs from AR(1) oracle.');
    assert(isequaln(rngBefore,rng),'rcKtcTest:rng','Global RNG changed.');
    report=struct('status','passed','scope','MATLAB function-only; no Simulink and no analog signoff', ...
        'physical_banks',1,'numerical_segments',8,'no_ADI_or_10M',true, ...
        'stat_n',count-burn,'stationary_var',sampleVar,'lag1_cov',lag1,'expected_lag1',alpha);
end

function [s,p,openingB]=capture_from(f,v0,t,id,epoch)
    [s,p]=behavior_frontend_init(f);ids=(1:8).';
    s.B_c(ids,1)=p.group_C_f(ids,1).*v0;
    [s,~]=behavior_frontend_step(s,command('acquire_open',0,id,epoch),p);
    openingB=s.B_c(ids,1);
    [s,~]=behavior_frontend_step(s,command('capture',t,id,epoch),p);
end
function cmds=legacy_commands()
    u=struct('offset_v',0.2,'amplitude_v',0.4,'frequency_hz',0.93e6,'phase_rad',0.11);
    ch=command('input_change',8e-9,0,1);ch.input=u;
    dac=command('dac_commit',130e-9,0,1);dac.d1_code=512;
    release=command('release',200e-9,0,1);release.vtop_v=0.1;
    cmds={command('acquire_open',0,0,1),command('observe',3e-9,0,1),ch, ...
        command('capture',110e-9,0,1),command('convert_join',110e-9,0,1),dac,release, ...
        command('acquire_open',200e-9,1,1),command('capture',310e-9,1,1)};
end
function c=command(event,t,id,epoch),c=struct('event',event,'t_s',t,'id',id,'epoch',epoch);end
function result=rc_integral_oracle(v0,t0,t1,tau,u)
% Independent closed-form convolution of a DC + sine waveform.
    a=2*pi*u.frequency_hz*tau;decay=exp(-(t1-t0)/tau);
    shape=@(t)sin(2*pi*u.frequency_hz*t+u.phase_rad)- ...
        a*cos(2*pi*u.frequency_hz*t+u.phase_rad);
    result=decay.*v0+u.offset_v*(1-decay)+ ...
        u.amplitude_v/(1+a*a)*(shape(t1)-decay*shape(t0));
end
function expect_error(fun,id)
    try,fun();catch ex,assert(strcmp(ex.identifier,id),'rcKtcTest:errorID', ...
            'Expected %s, got %s.',id,ex.identifier);return;end
    error('rcKtcTest:noError','Expected %s.',id);
end
function yes=bits(a,b)
    yes=isa(a,'double')&&isa(b,'double')&&isequal(size(a),size(b))&& ...
        isequal(typecast(a(:),'uint64'),typecast(b(:),'uint64'));
end

function yes=deep_bits(a,b)
    if isa(a,'double')||isa(b,'double'),yes=bits(a,b);return;end
    if isstruct(a)&&isstruct(b)
        yes=isequal(size(a),size(b))&&isequal(fieldnames(a),fieldnames(b));
        if ~yes,return;end
        names=fieldnames(a);
        for i=1:numel(a)
            for j=1:numel(names)
                name=names{j};
                if ~deep_bits(a(i).(name),b(i).(name)),yes=false;return;end
            end
        end
    else,yes=isequaln(a,b);end
end
