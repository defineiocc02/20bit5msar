function test_ni_candidate()
%TEST_NI_CANDIDATE Pure MATLAB candidate tests; no SLX, sim, or production write.
% Run in a NEW batch MATLAB process. This file only adds the isolated candidate
% and renamed baseline source to that process; path, cwd and RNG are restored.
    testDir=fileparts(mfilename('fullpath'));
    root=fileparts(testDir);
    oldPath=path;oldDir=pwd;rngBefore=rng;
    cleanup=onCleanup(@()restore_env(oldPath,oldDir)); %#ok<NASGU>
    cd(testDir);
    addpath(genpath(fullfile(root,'candidate','current','src')),'-begin');
    addpath(fullfile(root,'candidate','config'),'-begin');
    addpath(fullfile(root,'baseline'),'-begin');
    expect_resolved('behavior_prepare_configuration',fullfile(root,'candidate','current','src','model','behavior_prepare_configuration.m'));
    expect_resolved('behavior_ra_noise_guard',fullfile(root,'candidate','current','src','model','behavior_ra_noise_guard.m'));
    expect_resolved('behavior_training_configuration',fullfile(root,'candidate','current','src','model','behavior_training_configuration.m'));
    expect_resolved('public_calibration_config',fullfile(root,'candidate','current','src','calibration','public_calibration_config.m'));
    expect_resolved('baseline_prepare_configuration',fullfile(root,'baseline','baseline_prepare_configuration.m'));

    for noise=[false true]
        P=make_base(noise);
        B=baseline_prepare_configuration(P);
        Q=behavior_prepare_configuration(P);
        assert(isequaln(B,Q),'candidateTest:defaultChanged','Default ON/OFF prepared P changed.');
        verify_same_physics(B,Q);
        assert(isequaln(behavior_dac_backend_parameters(Q),Q.backend),'candidateTest:dialog','Prepared profile rejected by actual backend accessor.');
        if noise,assert(Q.ni.ra_noise);end
        R=Q;R.ni=rmfield(R.ni,'sample_settling');
        must_error(@()behavior_dac_backend_parameters(R),'sar20RA:coverageFlags');
        Qmissing=behavior_prepare_configuration(R);
        assert(isfield(Qmissing.ni,'sample_settling')&&~Qmissing.ni.sample_settling, ...
            'candidateTest:legacyDerive','Reapply did not populate a missing summary field.');
        R=Q;R.ni.sample_settling=NaN;
        must_error(@()behavior_prepare_configuration(R),'sar20RA:coverageFlags');
        % prepare already re-derives these labels before the common guard;
        % their old values, including NaN, are intentionally overwritten.
        R=Q;R.ni.az=NaN;R.ni.dac_settling=NaN;R.ni.parasitic=NaN;
        R.ni.sample_ktc=NaN;R.ni.jitter=NaN;R.ni.ra_noise=NaN;
        T=behavior_prepare_configuration(R);
        assert(~T.ni.az&&~T.ni.dac_settling&&T.ni.parasitic&& ...
            ~T.ni.sample_ktc&&~T.ni.jitter&&T.ni.ra_noise==noise, ...
            'candidateTest:rederivedEarly','Previously derived summary labels not refreshed.');
        R=Q;R.ni.sample_ktc=NaN;
        must_error(@()behavior_dac_backend_parameters(R),'sar20RA:coverageFlags');

        % Old OFF left these two labels stale; ON already derived both.
        P.backend.ra.A0=Inf;
        P.front.tau_sample_s(:)=1e-9;
        P.ni.ra_finite_gain=true;P.ni.sample_settling=false;
        B=baseline_prepare_configuration(P);
        Q=behavior_prepare_configuration(P);
        assert(isinf(Q.backend.ra.A0)&&~Q.ni.ra_finite_gain&& ...
            all(Q.front.tau_sample_s==1e-9)&&Q.ni.sample_settling, ...
            'candidateTest:coverageDerive','A0 and finite sampling coverage do not reflect physical values.');
        if ~noise
            assert(B.ni.ra_finite_gain&&~B.ni.sample_settling, ...
                'candidateTest:baselineNotReproduced','Expected baseline OFF stale metadata.');
        end
        assert(isequaln(rmfield(B,'ni'),rmfield(Q,'ni')), ...
            'candidateTest:nonCoverageMutation','Prepare modified fields beyond coverage.');
        verify_same_physics(B,Q);
        R=Q;R.ni.ra_finite_gain=true;
        must_error(@()behavior_dac_backend_parameters(R),'sar20RA:coverageGain');
        R=Q;R.ni.sample_settling=false;
        must_error(@()behavior_dac_backend_parameters(R),'sar20RA:coverageSampling');

        % Inf is a held input, not finite settling; both nominal and physical
        % mismatched C are checked from actual arrays rather than flag alone.
        P=make_base(noise);P.front.tau_sample_s(:)=Inf;P.ni.sample_settling=true;
        Q=behavior_prepare_configuration(P);
        assert(all(isinf(Q.front.tau_sample_s))&&~Q.ni.sample_settling, ...
            'candidateTest:infiniteHold','Inf must remain hold and not count finite settling.');
        P=make_base(noise);P.front.mismatch_enabled=true;P.ni.cap_mismatch=true;
        Q=behavior_prepare_configuration(P);
        assert(~Q.ni.cap_mismatch,'candidateTest:nominalMismatch','Nominal arrays cannot count as mismatch.');
        P.front.C_f(1,1)=P.front.C_f(1,1)*(1+1e-4);P.ni.cap_mismatch=false;
        B=baseline_prepare_configuration(P);Q=behavior_prepare_configuration(P);
        assert(Q.ni.cap_mismatch&&Q.front.C_f(1,1)==P.front.C_f(1,1), ...
            'candidateTest:actualMismatch','Actual selected C mismatch was lost.');
        assert(isequaln(rmfield(B,'ni'),rmfield(Q,'ni')),'candidateTest:capMutation','Physical mismatch changed.');
        verify_same_physics(B,Q);

        P=make_base(noise);P.backend.ni.cap_mismatch=true;
        P.backend.ct.net_actual.main_f(1,1)=P.backend.ct.net_actual.main_f(1,1)*(1+1e-4);
        P.ni.cap_mismatch=false;Q=behavior_prepare_configuration(P);
        assert(Q.ni.cap_mismatch,'candidateTest:ctMismatch','Selected actual CT mismatch was not counted.');
        P=make_base(noise);P.front.ktc_enabled=true;P.ni.sample_ktc=false;
        Q=behavior_prepare_configuration(P);
        assert(Q.ni.sample_ktc,'candidateTest:ktc','Positive-temperature kT/C must count.');
        P.front.temperature_K=0;P.ni.sample_ktc=true;Q=behavior_prepare_configuration(P);
        assert(~Q.ni.sample_ktc,'candidateTest:zeroKtc','Zero-temperature injection is not coverage.');
        P=make_base(noise);P.front.jitter.enabled=true;P.front.jitter.common_sigma_s=1e-12;P.ni.jitter=false;
        Q=behavior_prepare_configuration(P);assert(Q.ni.jitter,'candidateTest:jitter','Nonzero aperture jitter must count.');
        P.front.jitter.common_sigma_s=0;P.ni.jitter=true;Q=behavior_prepare_configuration(P);
        assert(~Q.ni.jitter,'candidateTest:zeroJitter','Zero aperture injection is not coverage.');
        P=make_base(noise);P.backend.ni.cinc_kick=false;P.front.Cp_f(:)=0;P.ni.parasitic=true;
        Q=behavior_prepare_configuration(P);
        assert(~Q.ni.parasitic,'candidateTest:parasitic','Inactive output load is not parasitic coverage.');
        if noise
            P=make_base(true);P.backend.ra_noise.sigma_vx_rms=0;Q=behavior_prepare_configuration(P);
            assert(~Q.ni.ra_noise,'candidateTest:zeroRaNoise','Zero OU amplitude is not noise coverage.');
        else
            P=make_base(false);P.backend.ra.UGB_hz=Inf;P.ni.ra_finite_bandwidth=true;
            Q=behavior_prepare_configuration(P);
            assert(~Q.ni.ra_finite_bandwidth,'candidateTest:infiniteBandwidth','Infinite UGB is not finite bandwidth.');
            P=make_base(false);P.backend.dac_coupling.enabled=true;P.front.tau_dac_s(:)=1e-9;
            Q=behavior_prepare_configuration(P);
            assert(Q.ni.dac_settling&&all(Q.front.tau_dac_s==1e-9), ...
                'candidateTest:finiteDac','Finite enabled DAC must be counted without changing tau.');
            behavior_dac_backend_parameters(Q);
        end

        R=Q;R.ni.reference_recovery=true;
        must_error(@()behavior_ra_noise_guard(R),'sar20RA:referenceRecovery');
        R=Q;R.ni.comparator_noise=true;
        must_error(@()behavior_ra_noise_guard(R),'sar20RA:comparatorNoise');

        % Enabled zero amplitude is a valid ordinary diagnostic, while both
        % paths retain the exact real switch, seed and amplitude.
        Z=make_base(noise);Z.front.dither_enabled=true;
        Z.front.dither_input_amplitude_v=0;
        Z.digital.dither_enabled=true;Z.digital.dither_seed=Z.front.dither_seed;
        Z.digital.dither_amplitude_v=0;
        must_error(@()baseline_prepare_configuration(Z),'publicCalConfig:scaleJoin');
        Q=behavior_prepare_configuration(Z);
        assert(Q.front.dither_enabled&&Q.digital.dither_enabled&& ...
            Q.front.dither_input_amplitude_v==0&&Q.digital.dither_amplitude_v==0&& ...
            Q.front.dither_seed==Z.front.dither_seed&&Q.digital.dither_seed==Z.digital.dither_seed&& ...
            Q.cal_cfg.public_cfg.dither_enabled&&Q.cal_cfg.public_cfg.dither_input_amplitude_v==0, ...
            'candidateTest:zeroDitherProjection','Zero diagnostic altered physical/public config.');
        assert(~Q.cal_cfg.enabled&&~Q.frozen.enabled&&~Q.bank.enabled, ...
            'candidateTest:ordinaryOnly','Zero diagnostic enabled calibration.');
        for field={'training','cal_cfg','frozen','bank'}
            bad=Q;bad.(field{1}).enabled=true;
            must_error(@()behavior_dac_backend_parameters(bad),'calConfig:zeroDitherQualification');
        end
        bad=Q;bad.digital.dither_amplitude_v=1e-3;
        must_error(@()behavior_dac_backend_parameters(bad),'calConfig:ditherJoin');
        bad=Q;bad.front.dither_input_amplitude_v=1e-3;
        must_error(@()behavior_dac_backend_parameters(bad),'calConfig:ditherJoin');
        bad=Q;bad.front.dither_enabled=false;
        must_error(@()behavior_dac_backend_parameters(bad),'calConfig:ditherJoin');
        bad=Q;bad.front.dither_seed=bad.front.dither_seed+1;
        must_error(@()behavior_dac_backend_parameters(bad),'calConfig:ditherJoin');
        [collector,~]=behavior_cal_collector_step('init',[],0,[],[],Q.cal_cfg);
        assert(collector.n_collected==0&&collector.fit_calls==0&&isempty(collector.raw_buffer), ...
            'candidateTest:collectorNotOff','Inactive collector is not inactive.');
        direct=Q.cal_cfg;direct.enabled=true;
        must_error(@()behavior_cal_collector_step('init',[],0,[],[],direct),'publicCal:dither');
        Zoff=Z;Zoff.front.dither_enabled=false;Zoff.digital.dither_enabled=false;
        Qoff=behavior_prepare_configuration(Zoff);
        verify_zero_effect(Q,Qoff);
        bad=Z;bad.digital.dither_amplitude_v=1e-3;
        must_error(@()behavior_prepare_configuration(bad),'publicCalConfig:ditherJoin');
        bad=Z;bad.digital.dither_seed=bad.digital.dither_seed+1;
        must_error(@()behavior_prepare_configuration(bad),'publicCalConfig:ditherJoin');
        bad=Z;bad.digital.dither_enabled=false;
        must_error(@()behavior_prepare_configuration(bad),'publicCalConfig:ditherJoin');

        % Public projection is not qualification; feature/fitter and each
        % calibration lifecycle remain ineligible at enabled zero amplitude.
        dummy=struct('raw_D1',0,'raw_D2',0,'raw_DT',0,'sample_id',0,'epoch',0,'valid',0);
        must_error(@()behavior_public_cal_features(dummy,Q.cal_cfg.public_cfg),'publicCal:dither');
        must_error(@()behavior_public_cal_fit(dummy,Q.cal_cfg.public_cfg,[],Q.cal_cfg.thresholds),'publicCal:dither');
        bad=Z;bad.training=Q.training;bad.training.enabled=true;bad.training.reference.enabled=true;
        must_error(@()behavior_prepare_configuration(bad),'calConfig:zeroDitherTraining');
        bad=Z;bad.frozen=struct('enabled',true,'cache',[]);
        must_error(@()behavior_prepare_configuration(bad),'calConfig:zeroDitherFrozen');
        bad=Z;bad.bank=struct('enabled',true);
        must_error(@()behavior_prepare_configuration(bad),'calConfig:zeroDitherBank');

        % The existing incompatible combinations continue to fail closed.
        bad=make_base(noise);bad.front.ktc_enabled=true;bad.front.tau_sample_s(:)=1e-9;
        must_error(@()behavior_prepare_configuration(bad),'behaviorFE:ktcFiniteSamplingUnsupported');
        bad=make_base(noise);bad.front.jitter.enabled=true;bad.front.tau_sample_s(:)=1e-9;
        must_error(@()behavior_prepare_configuration(bad),'behaviorFE:jitterFiniteSamplingUnsupported');
        bad=make_base(noise);bad.front.tau_dac_s(:)=1e-9;
        must_error(@()behavior_prepare_configuration(bad),'behaviorDAC:uncoupledFinite');
    end

    % Historical OU-OFF kernels accept either valid 12-cap split independently
    % for the actual and nominal network. Verify both directions and replica.
    check_historical_split(10,6,10,true,true,true);
    check_historical_split(6,10,6,true,true,true);
    check_historical_split(10,10,6,true,true,true);
    check_historical_split(10,10,6,false,true,true);
    check_historical_split(10,10,6,false,false,false);
    check_bridge_orientation();
    Punselected=make_base(false);
    Punselected.backend.ct.net_actual=split_network(Punselected.backend.ct.net_actual,6);
    Q=behavior_prepare_configuration(Punselected);
    assert(~Q.ni.cap_mismatch,'candidateTest:unselectedCT','An unselected network is not active mismatch.');
    bad=make_base(false);bad.backend.ni.cap_mismatch=true;
    bad.backend.ct.net_actual=split_network(bad.backend.ct.net_actual,6);
    bad.backend.ct.net_actual.sub_f(:,end)=[];
    must_error(@()behavior_prepare_configuration(bad),'sar20:cdac2Layout');
    Psame=make_base(true);Psame.backend.ni.cap_mismatch=true;
    Psame.backend.ct.net_nominal=split_network(Psame.backend.ct.net_nominal,6);
    Psame.backend.ct.net_actual=split_network(Psame.backend.ct.net_actual,6);
    Psame.backend.ct.net_replica=split_network(Psame.backend.ct.net_replica,6);
    B=baseline_prepare_configuration(Psame);Q=behavior_prepare_configuration(Psame);
    assert(isequaln(B,Q),'candidateTest:ouOnSameSplit','Existing same-split OU ON configuration changed.');
    verify_same_physics(B,Q);
    Pon=make_base(true);Pon.backend.ni.cap_mismatch=true;
    Pon.backend.ct.net_nominal=split_network(Pon.backend.ct.net_nominal,10);
    Pon.backend.ct.net_actual=split_network(Pon.backend.ct.net_actual,6);
    Pon.backend.ct.net_replica=split_network(Pon.backend.ct.net_replica,10);
    % OU ON must retain the original, narrower same-shape qualification.
    must_error(@()baseline_prepare_configuration(Pon),'sar20RA:coverageCap');
    must_error(@()behavior_prepare_configuration(Pon),'sar20RA:coverageCap');

    % Existing finite nonzero public stimulus remains accepted. An 8-row fit
    % must return the preexisting 684-column rank-bound rejection without
    % reading a reference or creating accepted/frozen calibration.
    P=make_base(false);P.front.dither_enabled=true;P.digital.dither_enabled=true;
    P.digital.dither_seed=P.front.dither_seed;
    P.digital.dither_amplitude_v=P.front.dither_input_amplitude_v;
    B=baseline_prepare_configuration(P);Q=behavior_prepare_configuration(P);
    assert(isequaln(B,Q),'candidateTest:positiveDitherChanged','Positive dither profile changed.');
    bad=Q;bad.digital.dither_amplitude_v=0;
    must_error(@()behavior_dac_backend_parameters(bad),'calConfig:ditherJoin');
    direct=Q.cal_cfg;direct.enabled=true;
    [collector,~]=behavior_cal_collector_step('init',[],0,[],[],direct);
    assert(isequal(size(collector.raw_buffer),[8 6])&&collector.fit_calls==0, ...
        'candidateTest:positiveCollector','Valid nonzero dither collector did not initialize.');
    raw=struct('raw_D1',zeros(8,1),'raw_D2',zeros(8,1),'raw_DT',zeros(8,1), ...
        'sample_id',(0:7).','epoch',ones(8,1),'valid',ones(8,1));
    fit=behavior_public_cal_fit(raw,Q.cal_cfg.public_cfg,[],Q.cal_cfg.thresholds);
    assert(strcmp(fit.status,'rank_deficient_row_bound')&&fit.rank_upper_bound==8&& ...
        fit.parameter_count==684&&isempty(fit.h_fit)&&isempty(fit.frozen)&& ...
        ~fit.accepted&&~fit.reference_values_read, ...
        'candidateTest:rankBoundary','Training row/rank/information boundary changed.');
    assert(isequaln(rngBefore,rng),'candidateTest:rng','Candidate tests altered the global RNG.');
    fprintf('PASS: isolated NI/dither unit tests, OU OFF+ON. No Simulink simulation performed.\n');
end

function P=make_base(noise)
    P=adc_parameters();
    if noise
        P.backend.ni.ra_noise=true;
        P.backend.ra_noise=struct('schema','sar20-ra-ou/v1', ...
            'sigma_vx_rms',1e-3,'seed_u64',uint64(20261030));
    end
end

function check_historical_split(nominalMain,actualMain,replicaMain,replicaOn,kickOn,expected)
    P=make_base(false);P.backend.ni.cap_mismatch=true;
    P.backend.ct.net_nominal=split_network(P.backend.ct.net_nominal,nominalMain);
    P.backend.ct.net_actual=split_network(P.backend.ct.net_actual,actualMain);
    P.backend.ct.net_replica=split_network(P.backend.ct.net_replica,replicaMain);
    P.backend.ct.replica_enabled=replicaOn;P.backend.ni.cinc_kick=kickOn;
    P.ni.cap_mismatch=~expected;
    B=baseline_prepare_configuration(P);Q=behavior_prepare_configuration(P);
    assert(Q.ni.cap_mismatch==expected,'candidateTest:historicalSplitCoverage', ...
        'Different selected CT partitions must be treated as non-nominal.');
    assert(isequaln(rmfield(B,'ni'),rmfield(Q,'ni')), ...
        'candidateTest:historicalSplitConfig','Historical CT parameters changed.');
    verify_same_physics(B,Q);
    behavior_dac_backend_parameters(Q);
    R=Q;R.ni.cap_mismatch=~expected;
    must_error(@()behavior_dac_backend_parameters(R),'sar20RA:coverageCap');
end

function check_bridge_orientation()
    P=make_base(false);P.backend.ni.cap_mismatch=true;
    % Distinct half values ensure the test verifies each side, not symmetry.
    P.backend.ct.net_nominal.bridge_f=[1.8e-15;2.2e-15];
    P.backend.ct.net_actual.bridge_f=P.backend.ct.net_nominal.bridge_f;
    P.backend.ct.net_replica.bridge_f=P.backend.ct.net_nominal.bridge_f;
    P.ni.cap_mismatch=true;
    reference=behavior_prepare_configuration(P);
    assert(~reference.ni.cap_mismatch,'candidateTest:bridgeFixture','Identical CT networks must be nominal.');
    for name={'net_actual','net_replica'}
        changed=P;field=name{1};
        changed.backend.ct.(field).bridge_f=changed.backend.ct.(field).bridge_f.';
        B=baseline_prepare_configuration(changed);Q=behavior_prepare_configuration(changed);
        assert(isequaln(rmfield(B,'ni'),rmfield(Q,'ni')), ...
            'candidateTest:bridgePhysicalMutation','Bridge candidate modified physical parameters.');
        assert(~Q.ni.cap_mismatch,'candidateTest:bridgeOrientation', ...
            'OU OFF two-element bridge_f orientation alone is not mismatch.');
        assert(isequaln(Q.xBK0,reference.xBK0),'candidateTest:bridgeColdState', ...
            'Bridge orientation changed the prepared backend state.');
        verify_same_backend_state(reference,Q);
        behavior_dac_backend_parameters(Q);
    end
    changed=P;
    changed.backend.ct.net_actual.bridge_f=changed.backend.ct.net_actual.bridge_f.';
    changed.backend.ct.net_actual.bridge_f(1)=changed.backend.ct.net_actual.bridge_f(1)*1.01;
    Q=behavior_prepare_configuration(changed);
    assert(Q.ni.cap_mismatch,'candidateTest:bridgeValue','A real bridge value change must count as mismatch.');
    % CINC has shape-sensitive vector operations; retain its different-shape
    % treatment in the guard without claiming the malformed kernel is valid.
    changed=reference;changed.backend.ct.net_actual.cinc_f=changed.backend.ct.net_actual.cinc_f.';
    changed.ni.cap_mismatch=true;behavior_ra_noise_guard(changed);
    changed.ni.cap_mismatch=false;
    must_error(@()behavior_ra_noise_guard(changed),'sar20RA:coverageCap');
    % OU ON keeps the existing per-network two-column-vector validation.
    on=make_base(true);on.backend.ni.cap_mismatch=true;
    on.backend.ct.net_actual.bridge_f=on.backend.ct.net_actual.bridge_f.';
    must_error(@()baseline_prepare_configuration(on),'sar20RA:ctNetwork');
    must_error(@()behavior_prepare_configuration(on),'sar20RA:ctNetwork');
end

function verify_same_backend_state(B,Q)
    cmd=struct('qres_c',1e-13,'ctop_f',2e-11,'d2_signs',zeros(12,1), ...
        'ta_signs',zeros(7,1),'ra_on',true,'az_on',false,'reset',false,'sample_id',4,'epoch',Q.epoch);
    [sb,yb]=behavior_backend_step([],cmd,0,B.backend);
    [sq,yq]=behavior_backend_step([],cmd,0,Q.backend);
    assert(isequaln(sb,sq)&&isequaln(yb,yq),'candidateTest:bridgeCold','Cold backend changed.');
    cmd.d2_signs(1)=1;cmd.ta_signs(1)=-1;
    [sb,yb]=behavior_backend_step(sb,cmd,1.25e-9,B.backend);
    [sq,yq]=behavior_backend_step(sq,cmd,1.25e-9,Q.backend);
    assert(isequaln(sb,sq)&&isequaln(yb,yq),'candidateTest:bridgeSwitch','Switched backend changed.');
end

function net=split_network(net,mainCount)
    c=[net.main_f net.sub_f];
    assert(size(c,1)==2&&size(c,2)==12&&any(mainCount==[6 10]), ...
        'candidateTest:splitFixture','Expected the 12-cap network and 6/10 main split.');
    net.main_f=c(:,1:mainCount);net.sub_f=c(:,mainCount+1:end);
end

function verify_same_physics(B,Q)
    assert(isequaln(B.front,Q.front)&&isequaln(B.backend,Q.backend)&&isequaln(B.digital,Q.digital), ...
        'candidateTest:physicalValues','Front/backend/digital parameters changed.');
    driver=[Q.input.offset_v;Q.input.amplitude_v;Q.input.frequency_hz;Q.input.phase_rad];
    context=[0;0;Q.epoch;1;0;0];
    [xb,ob]=behavior_frontend_stage('advance',B.xFE0,context,B.front,driver);
    [xq,oq]=behavior_frontend_stage('advance',Q.xFE0,context,Q.front,driver);
    assert(bits_equal(xb,xq)&&bits_equal(ob,oq),'candidateTest:frontArithmetic','Frontend state/observation bits differ.');
    cmd=struct('qres_c',1e-13,'ctop_f',2e-11,'d2_signs',zeros(12,1), ...
        'ta_signs',zeros(7,1),'ra_on',true,'az_on',false,'reset',false,'sample_id',4,'epoch',Q.epoch);
    [sb,~]=behavior_backend_step([],cmd,0,B.backend);
    [sq,~]=behavior_backend_step([],cmd,0,Q.backend);
    dt=1.25e-9;
    [sb,yb]=behavior_backend_step(sb,cmd,dt,B.backend,[],dt);
    [sq,yq]=behavior_backend_step(sq,cmd,dt,Q.backend,[],dt);
    assert(isequaln(sb,sq)&&isequaln(yb,yq)&&bits_equal(sb.vx_v,sq.vx_v)&&bits_equal(yb.vy_v,yq.vy_v), ...
        'candidateTest:backendArithmetic','Backend physical state/observation differs.');
end

function verify_zero_effect(Q,Qoff)
    assert(behavior_public_dither(4,Q.digital)==0&&behavior_public_dither(4,Qoff.digital)==0, ...
        'candidateTest:zeroDigital','A zero amplitude produced digital dither.');
    raw=struct('raw_D1',1900,'raw_D2',3283,'raw_DT',234,'sample_id',4,'epoch',1,'valid',1);
    a=behavior_decode(raw,Q.digital);b=behavior_decode(raw,Qoff.digital);
    assert(a.code20==b.code20&&a.voltage_v==b.voltage_v&&a.dither_v==0&&b.dither_v==0, ...
        'candidateTest:zeroDecode','Zero dither changed decoded physical voltage or code.');
    driver=[Q.input.offset_v;Q.input.amplitude_v;Q.input.frequency_hz;Q.input.phase_rad];
    context=[0;0;Q.epoch;1;0;0];
    [x1,o1]=behavior_frontend_stage('advance',Q.xFE0,context,Q.front,driver);
    [x0,o0]=behavior_frontend_stage('advance',Qoff.xFE0,context,Qoff.front,driver);
    assert(isequaln(x1,x0)&&isequaln(o1,o0),'candidateTest:zeroFrontend','Zero dither changed physical frontend values.');
end

function yes=bits_equal(a,b)
    a=double(a(:));b=double(b(:));
    yes=isequal(size(a),size(b))&&isequal(typecast(a,'uint64'),typecast(b,'uint64'));
end

function must_error(f,id)
    caught=false;
    try
        f();
    catch err
        caught=true;
        assert(strcmp(err.identifier,id),'candidateTest:wrongError','Expected %s, got %s.',id,err.identifier);
    end
    assert(caught,'candidateTest:missingError','Expected %s.',id);
end

function expect_resolved(name,expected)
    found=which(name);
    assert(~isempty(found),'candidateTest:missingFunction','Missing %s.',name);
    f=javaObject('java.io.File',found);e=javaObject('java.io.File',expected);
    assert(strcmp(char(f.getCanonicalPath()),char(e.getCanonicalPath())), ...
        'candidateTest:wrongPath','%s resolved to %s.',name,found);
end

function restore_env(oldPath,oldDir)
    path(oldPath);
    cd(oldDir);
end
