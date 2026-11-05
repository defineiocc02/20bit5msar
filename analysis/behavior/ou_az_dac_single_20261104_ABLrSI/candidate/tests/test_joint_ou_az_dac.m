function report=test_joint_ou_az_dac()
% MATLAB function-level draft; no model load, run, save, ADI or 10 MS/s run.
% Arbitrary test stimuli below are not paper/PDK parameter estimates.
    pkg=fileparts(fileparts(mfilename('fullpath')));
    baseline=fullfile(fileparts(pkg),'baseline','single_bank');
    assert(isfolder(baseline)&&~bdIsLoaded('SarAdc'),'jointTest:session', ...
        'Require the untouched sibling baseline and no loaded SarAdc model.');
    originalPath=path;restore=onCleanup(@()path(originalPath)); %#ok<NASGU>
    addpath(genpath(fullfile(pkg,'current','src')),fullfile(pkg,'config'),pkg,'-begin');rehash;
    require_path('behavior_backend_stage',pkg);
    initialRng=rng;

    P=adc_parameters();
    P.backend.ni.ra_noise=true;
    P.backend.ra_noise=struct('schema','sar20-ra-ou/v1', ...
        'sigma_vx_rms',1e-4,'seed_u64',uint64(9481));
    P.backend.az.mode='ordinary';P.backend.ni.az=true;P.digital.az_mode='ordinary';
    P.backend.ra.vos_input_v=1e-3;
    P.backend.az.write_tau_s=[3e-9;4e-9];
    P.backend.az.leak_tau_s=[25e-9;30e-9];
    P.backend.az.sense_injection_half_v=[2e-5;-3e-5];
    P.front.tau_dac_s(:)=8e-9;P.backend.dac_coupling.enabled=true;
    P=behavior_prepare_configuration(P);behavior_dac_backend_parameters(P);
    p=P.backend;
    assert(P.front.single_bank&&P.Ts_s==200e-9&&~P.training.enabled&& ...
        ~P.cal_cfg.enabled&&~P.frozen.enabled&&~P.bank.enabled, ...
        'jointTest:scope','Single-bank 5 MS/s and disabled calibration required.');

    % Construct the OLD FE and sole backend state from real public functions.
    % AZ writes while RA is off; finite DAC evolves in the same captured bank.
    ctx=@(t,id,event,d1,vtop)[t;id;P.epoch;event;d1;vtop];
    [xfe,~,~]=behavior_frontend_stage('advance',P.xFE0,ctx(0,0,1,0,0),P.front);
    [xfe,~,~]=behavior_frontend_stage('commit',xfe,ctx(12.5e-9,0,1,1234,0),P.front);
    t0=31.25e-9;t1=43.75e-9;
    [xfe,frontObs,~]=behavior_frontend_stage('advance',xfe,ctx(t0,0,0,0,0),P.front);
    ctop=p.dac_coupling.fixed_single_bank_ctop_f;
    azWrite=[0;ctop;zeros(19,1);0;1;1;0;P.epoch];
    [xbk,~]=behavior_backend_stage('commit',P.xBK0,0,azWrite,p);
    [xbk,~]=behavior_backend_stage('advance',xbk,t0,zeros(26,1),p,xfe);
    raStart=[frontObs(3);frontObs(5);zeros(19,1);1;0;0;0;P.epoch];
    [xbk,~]=behavior_backend_stage('commit',xbk,t0,raStart,p);
    old=behavior_backend_unpack(xbk);
    forcing=behavior_dac_forcing_from_frontend(xfe,old,t1,p);
    assert(old.az.valid&&~old.az.write_active&&old.command.ra_on&& ...
        any(forcing.delta_q_c~=0)&&~isequal(forcing.q0_c,forcing.q_endpoint_c), ...
        'jointTest:stimulus','AZ state and finite DAC must both have real interval dynamics.');

    pOff=p;pOff.ni.ra_noise=false;
    pZero=p;pZero.ra_noise.sigma_vx_rms=0;
    [xOff,oOff]=behavior_backend_stage('advance',xbk,t1,zeros(26,1),pOff,xfe);
    [xZero,oZero]=behavior_backend_stage('advance',xbk,t1,zeros(26,1),pZero,xfe);
    assert(bits(xOff,xZero)&&bits(oOff,oZero),'jointTest:zero', ...
        'Zero sigma and disabled OU must be bitwise equal for the finite-DAC interval.');
    [xOn,oOn]=behavior_backend_stage('advance',xbk,t1,zeros(26,1),p,xfe);
    [xAgain,oAgain]=behavior_backend_stage('advance',xbk,t1,zeros(26,1),p,xfe);
    assert(bits(xOn,xAgain)&&bits(oOn,oAgain),'jointTest:repeat','Exact key must repeat.');
    tau=(1+old.command.ctop_f/p.ra.Cf_f)/(2*pi*p.ra.UGB_hz);
    [expected,diag]=sar20_ra_ou_increment(xOff(2),t0,t1,tau, ...
        p.ra_noise.sigma_vx_rms,p.ra_noise.seed_u64,old.command.epoch,old.command.sample_id,true,true);
    assert(diag.applied&&bits(xOn(2),expected)&&bits(xOn([1 3:end]),xOff([1 3:end]))&& ...
        bits(xOn(12),forcing.q_endpoint_c)&&bits(xOn(1),t1), ...
        'jointTest:innovation','One keyed innovation must reach the existing VX before endpoint switching.');
    [~,d0]=sar20_ra_keyed_normal(p.ra_noise.seed_u64,P.epoch,0,t0,t1);
    [~,d1]=sar20_ra_keyed_normal(p.ra_noise.seed_u64,P.epoch,0,t0,t1+eps(t1));
    assert(P.epoch==1&&strcmp(d0,'3533785c8eb8494ce797a2edac3cea05adb0474480ef2bc3a55e5d130ca1fc06')&& ...
        ~strcmp(d0,d1)&&strcmp(d0,diag.digest_hex),'jointTest:timeKey', ...
        'Hash must include the exact original binary64 event endpoints.');

    % The original all-zero-DAC branch must also be bitwise sigma0 == OFF.
    pOff0=pOff;pOff0.dac_coupling.enabled=false;pOff0.dac_coupling.tau_dac_s(:)=0;
    pZero0=pZero;pZero0.dac_coupling.enabled=false;pZero0.dac_coupling.tau_dac_s(:)=0;
    [xOff0,oOff0]=behavior_backend_stage('advance',xbk,t1,zeros(26,1),pOff0);
    [xZero0,oZero0]=behavior_backend_stage('advance',xbk,t1,zeros(26,1),pZero0);
    assert(bits(xOff0,xZero0)&&bits(oOff0,oZero0),'jointTest:zeroNoDAC', ...
        'Zero sigma and disabled OU must be bitwise equal without DAC forcing.');

    % Keep boundary rejection explicit: no wrong mode, finite slew, Inf DAC,
    % invented AZ noise, missing exact endpoint, stale Ctop/plan or wrong FE time.
    bad=p;bad.az.mode='chop';expect(@()behavior_ra_noise_validate_backend(bad),'sar20RA:az');
    bad=p;bad.ra.slew_v_per_s=1e9;expect(@()behavior_ra_noise_validate_backend(bad),'sar20RA:finiteSlew');
    bad=p;bad.dac_coupling.tau_dac_s(1)=Inf;expect(@()behavior_ra_noise_validate_backend(bad),'sar20RA:finiteDAC');
    bad=p;bad.ni.az_noise=true;expect(@()behavior_ra_noise_validate_backend(bad),'sar20RA:unsupportedNI');
    expect(@()behavior_backend_step(old,old.command,t1-t0,p,forcing),'sar20RA:eventTime');
    fBad=forcing;fBad.tau_dac_s(1)=2*fBad.tau_dac_s(1);
    expect(@()behavior_backend_step(old,old.command,t1-t0,p,fBad,t1),'sar20RA:forcing');
    wrong=old.command;wrong.ctop_f=wrong.ctop_f+eps(wrong.ctop_f);
    expect(@()behavior_backend_step(old,wrong,0,p),'sar20RA:singleBankCtop');
    xBad=xfe;xBad(1)=xBad(1)-1e-12;
    expect(@()behavior_backend_stage('advance',xbk,t1,zeros(26,1),p,xBad),'behaviorDAC:time');
    badP=P;badP.backend.dac_coupling.public_plan(2,1)=2;
    expect(@()behavior_dac_backend_parameters(badP),'behaviorDAC:staleBinding');
    badP=P;badP.Ts_s=100e-9;expect(@()behavior_single_guard(badP,true),'singleBank:rate');

    % Independent original v2 functions, same initial state/forcing/parameters.
    % Only paths/functions are switched; neither baseline nor candidate is edited.
    candidatePath=path;
    addpath(genpath(fullfile(baseline,'current','src')),fullfile(baseline,'config'),baseline,'-begin');
    clear behavior_backend_stage behavior_backend_step behavior_ra_noise_validate_backend
    rehash;require_path('behavior_backend_stage',baseline);
    [xBase,oBase]=behavior_backend_stage('advance',xbk,t1,zeros(26,1),pOff,xfe);
    [xBase0,oBase0]=behavior_backend_stage('advance',xbk,t1,zeros(26,1),pOff0);
    assert(bits(xBase,xOff)&&bits(oBase,oOff)&&bits(xBase0,xOff0)&&bits(oBase0,oOff0), ...
        'jointTest:baseline','Disabled candidate must retain baseline v2 binary64 results.');
    path(candidatePath);clear behavior_backend_stage behavior_backend_step behavior_ra_noise_validate_backend
    rehash;require_path('behavior_backend_stage',pkg);
    assert(isequaln(initialRng,rng),'jointTest:rng','Global RNG state changed.');
    report=struct('status','passed','scope','MATLAB functions only; no Simulink graph run', ...
        'base_sha256','09e6c7c82635d8f6bf1cf4cc8e86f0ec42036524bfe6518dfcb37ea05fb06eb7', ...
        'time_key_sha256',d0,'single_bank_5Msps',true,'az_mode','ordinary', ...
        'finite_dac',true,'cinc_pre_kick_ou',true,'baseline_off_bitwise',true, ...
        'zero_sigma_bitwise',true,'rng_unchanged',true);
end

function expect(fun,id)
    try,fun();catch ex
        assert(strcmp(ex.identifier,id),'jointTest:errorID','Expected %s, got %s.',id,ex.identifier);return;
    end
    error('jointTest:noError','Expected %s.',id);
end
function yes=bits(a,b)
    yes=isa(a,'double')&&isa(b,'double')&&isequal(size(a),size(b))&& ...
        isequal(typecast(a(:),'uint64'),typecast(b(:),'uint64'));
end
function require_path(name,pkg)
    f=which(name);
    assert(~isempty(f)&&startsWith(lower(strrep(f,'\','/')), ...
        [lower(strrep(pkg,'\','/')) '/']),'jointTest:path','Unexpected %s: %s',name,f);
end
