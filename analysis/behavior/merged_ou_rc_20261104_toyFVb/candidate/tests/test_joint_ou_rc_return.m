function report=test_joint_ou_rc_return()
% Isolated MATLAB function-test DRAFT. Does not load/run/save a model.
% Test stimuli below are arbitrary fixtures, not a normal or measured profile.
    pkg=fileparts(fileparts(mfilename('fullpath')));
    assert(~bdIsLoaded('SarAdc'),'jointReturn:model','Require no loaded SarAdc model.');
    oldPath=path;restore=onCleanup(@()path(oldPath)); %#ok<NASGU>
    addpath(genpath(fullfile(pkg,'current','src')),fullfile(pkg,'config'),pkg,'-begin');rehash;
    rngBefore=rng;
    P=adc_parameters();
    P.front.single_guard_s=5e-9;
    P.front.tau_sample_s(:)=20e-9;P.front.ktc_enabled=true;
    P.front.tau_dac_s(:)=8e-9;P.backend.dac_coupling.enabled=true;
    P.backend.ni.ra_noise=true;
    P.backend.ra_noise=struct('schema','sar20-ra-ou/v1', ...
        'sigma_vx_rms',1e-3,'seed_u64',uint64(9481));
    P.backend.az.mode='ordinary';P.backend.ni.az=true;P.digital.az_mode='ordinary';
    P.backend.ra.vos_input_v=1e-3;
    P.backend.az.write_tau_s=[3e-9;4e-9];
    P.backend.az.leak_tau_s=[25e-9;30e-9];
    P.backend.az.sense_injection_half_v=[2e-5;-3e-5];
    P=behavior_prepare_configuration(P);behavior_dac_backend_parameters(P);
    assert(P.front.single_bank&&P.Ts_s==200e-9&&P.ni.sample_settling&& ...
        P.ni.sample_ktc&&P.ni.az&&P.ni.ra_noise&&P.ni.dac_settling&& ...
        ~P.front.jitter.enabled&&~P.transport.enabled&&~P.training.enabled&& ...
        ~P.cal_cfg.enabled&&~P.frozen.enabled&&~P.bank.enabled, ...
        'jointReturn:scope','Combined flags, one bank and 5 MS/s must be explicitly bound.');
    assert(numel(P.xFE0)==353&&numel(P.xBK0)==48&&numel(P.xSC0)==51, ...
        'jointReturn:abi','Existing FE353/RA48/SAR51 widths changed.');

    p=P.backend;pZero=p;pZero.ra_noise.sigma_vx_rms=0;
    ctx=@(t,id,event,d1,vtop)[t;id;P.epoch;event;d1;vtop];
    [xfe,~,~]=behavior_frontend_stage('advance',P.xFE0,ctx(0,0,1,0,0),P.front);
    [xfe,~,~]=behavior_frontend_stage('commit',xfe,ctx(12.5e-9,0,1,1234,0),P.front);
    t0=31.25e-9;t1=43.75e-9;tRelease=90e-9;tCapture=200e-9;
    [xfe,frontObs,~]=behavior_frontend_stage('advance',xfe,ctx(t0,0,0,0,0),P.front);
    ctop=p.dac_coupling.fixed_single_bank_ctop_f;
    azWrite=[0;ctop;zeros(19,1);0;1;1;0;P.epoch];
    [xbk,~]=behavior_backend_stage('commit',P.xBK0,0,azWrite,p);
    [xbk,~]=behavior_backend_stage('advance',xbk,t0,zeros(26,1),p,xfe);
    raStart=[frontObs(3);frontObs(5);zeros(19,1);1;0;0;0;P.epoch];
    [xbk,~]=behavior_backend_stage('commit',xbk,t0,raStart,p);
    old=behavior_backend_unpack(xbk);
    f=behavior_dac_forcing_from_frontend(xfe,old,t1,p);
    assert(old.az.valid&&any(f.delta_q_c~=0),'jointReturn:stimulus', ...
        'Ordinary AZ and a live finite-DAC transient are required.');

    % Two experiments start with the same complete old FE/RA states and keys;
    % only sigma differs. Each computation still uses one existing VX owner.
    [xbOn,~]=behavior_backend_stage('advance',xbk,t1,zeros(26,1),p,xfe);
    [xbZero,~]=behavior_backend_stage('advance',xbk,t1,zeros(26,1),pZero,xfe);
    [xfe,~,~]=behavior_frontend_stage('advance',xfe,ctx(t1,0,0,0,0),P.front);
    [~,oOn]=behavior_backend_stage('advance',xbOn,tRelease,zeros(26,1),p,xfe);
    [~,oZero]=behavior_backend_stage('advance',xbZero,tRelease,zeros(26,1),pZero,xfe);
    [xfe,~,~]=behavior_frontend_stage('advance',xfe,ctx(tRelease,0,0,0,0),P.front);
    dvReturn=oOn(3)-oZero(3);
    assert(abs(dvReturn)>1e-12,'jointReturn:ouStimulus','OU did not change release Vtop.');
    [xOn,~,onRelease]=behavior_frontend_stage('commit',xfe,ctx(tRelease,0,2,0,oOn(3)),P.front);
    [xZero,~,zeroRelease]=behavior_frontend_stage('commit',xfe,ctx(tRelease,0,2,0,oZero(3)),P.front);
    assert(onRelease.released&&zeroRelease.released,'jointReturn:release','Real FE return was not committed.');
    beforeOn=behavior_frontend_unpack(xOn,P.front);
    beforeZero=behavior_frontend_unpack(xZero,P.front);
    ids=(1:8).';
    qdiff=beforeOn.B_c(ids,1)-beforeZero.B_c(ids,1);
    expectedQ=-P.front.group_C_f(ids,1)*dvReturn;
    assert(max(abs(qdiff-expectedQ))<2e-26,'jointReturn:charge', ...
        'Release must return the actual noisy Vtop to the existing FE charge.');

    % The same next-capture tuple means the kTC innovation cancels in the
    % paired difference, exposing only the returned OU contribution after RC.
    [xcOn,~,~]=behavior_frontend_stage('advance',xOn,ctx(tCapture,1,1,0,0),P.front);
    [xcZero,~,~]=behavior_frontend_stage('advance',xZero,ctx(tCapture,1,1,0,0),P.front);
    cOn=behavior_frontend_unpack(xcOn,P.front);cZero=behavior_frontend_unpack(xcZero,P.front);
    alpha=exp(-(tCapture-tRelease-P.front.single_guard_s)/P.front.tau_sample_s(1));
    difference=cOn.v_capture_v(ids)-cZero.v_capture_v(ids);
    assert(max(abs(difference+alpha*dvReturn))<1e-13,'jointReturn:retained', ...
        'The returned OU contribution must decay through the true finite-RC window.');
    frontNoKtc=P.front;frontNoKtc.ktc_enabled=false;
    [xcNoKtc,~,~]=behavior_frontend_stage('advance',xOn,ctx(tCapture,1,1,0,0),frontNoKtc);
    noKtc=behavior_frontend_unpack(xcNoKtc,P.front);
    assert(any(cOn.v_capture_v(ids)~=noKtc.v_capture_v(ids)),'jointReturn:ktc', ...
        'A separate new kTC capture innovation must be present.');
    [xcRepeat,~,~]=behavior_frontend_stage('advance',xOn,ctx(tCapture,1,1,0,0),P.front);
    assert(bits(xcRepeat,xcOn)&&isequaln(rngBefore,rng),'jointReturn:repeat', ...
        'Repeated Outputs evaluation must replay the same state without global RNG mutation.');
    report=struct('status','passed','scope','function-only paired states; no graph or circuit validation', ...
        'single_bank_5Msps',true,'guard_s',P.front.single_guard_s, ...
        'return_delta_v',dvReturn,'sampling_decay',alpha, ...
        'max_capture_error_v',max(abs(difference+alpha*dvReturn)), ...
        'state_widths',[353 48 51],'global_rng_unchanged',true);
end
function yes=bits(a,b)
    yes=isa(a,'double')&&isa(b,'double')&&isequal(size(a),size(b))&& ...
        isequal(typecast(a(:),'uint64'),typecast(b(:),'uint64'));
end
