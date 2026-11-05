function [report,P]=test_single_bank()
% Isolated function test only: no Simulink model load/run/save, no production.
% The 1039Cu geometry and 8 numerical segments are explicit assumptions.
    pkg=fileparts(fileparts(mfilename('fullpath')));
    assert(feature('getpid')~=27628&&~usejava('desktop'),'singleTest:session', ...
        'Start a new headless MATLAB batch process.');
    assert(~bdIsLoaded('SarAdc'),'singleTest:model','No model may be loaded.');
    oldPath=path;restore=onCleanup(@()path(oldPath)); %#ok<NASGU>
    src=fullfile(pkg,'current','src');addpath(genpath(src),fullfile(pkg,'config'),pkg,'-begin');rehash;
    names={'SAR20','adc_parameters','behavior_single_guard','behavior_prepare_configuration', ...
        'behavior_frontend_init','behavior_frontend_step','behavior_frontend_stage', ...
        'behavior_frontend_pack','behavior_frontend_unpack','behavior_sar_step', ...
        'behavior_dac_backend_parameters'};
    for k=1:numel(names)
        f=which(names{k});assert(~isempty(f)&&startsWith(lower(strrep(f,'\','/')), ...
            [lower(strrep(pkg,'\','/')) '/']),'singleTest:path','Unexpected function path: %s',names{k});
    end
    rngBefore=rng;
    P=adc_parameters();
    assert(P.front.single_bank&&P.front.single_guard_s==0&& ...
        ~P.front.dem_enabled&&~P.front.dither_enabled&&~P.front.jitter.enabled, ...
        'singleTest:factory','Factory must select one unshuffled bank.');
    assert(isequal(P.front.plan,repmat(1:8,P.front.plan_rows,1)), ...
        'singleTest:plan','The one numerical group must remain fixed.');
    P=behavior_prepare_configuration(P);P_for_model=P;
    assert(P.control.single_bank&&~P.transport.enabled&&~P.training.enabled&& ...
        ~P.cal_cfg.enabled&&~P.frozen.enabled&&~P.bank.enabled&& ...
        P.digital.d1_bias_v==0&&strcmp(P.cal_cfg.public_cfg.pool_schedule,'inactive_single_bank_uncalibrated'), ...
        'singleTest:boundary','Legacy pool-derived calibration and bank must remain off.');
    behavior_dac_backend_parameters(P);
    initialBk=behavior_backend_unpack(P.xBK0);ids=P.front.plan(1,:);
    initialCtop=sum(P.front.group_C_f(ids,:),'all')+sum(P.front.Cp_f(ids));
    assert(bits(initialBk.command.ctop_f,initialCtop)&& ...
        abs(initialCtop-28.053e-12)<1e-24&&abs(P.backend.ra.Cf_f-0.864e-12)<1e-24, ...
        'singleTest:backendC','New single-bank Ctop/Cf must initialize the backend.');
    stale=P;stale.xBK0(13)=stale.xBK0(13)+1e-15;
    expect_error(@()behavior_dac_backend_parameters(stale),'singleBank:backendInitial');
    rel=P.calendar(strcmp({P.calendar.type},'release')).time_s;
    assert(isscalar(rel)&&abs(rel-90e-9)<1e-18&&P.Ts_s==200e-9, ...
        'singleTest:time','Expected original 90 ns release and 200 ns CNV.');
    s0=behavior_frontend_unpack(P.xFE0,P.front);
    assert(s0.time_s==-P.Ts_s+rel&&all(s0.phase(1:8)==1)&&all(s0.phase(9:18)==0)&& ...
        all(s0.acquire_open_s(1:8)==s0.time_s),'singleTest:startup','Wrong cold acquisition start.');
    for id=0:1
        e=struct('type','cnv','sample_id',id,'epoch',P.epoch);
        [s,~]=behavior_sar_step([],e,struct('sample_v',0),P.control);
        assert(s.bank==0,'singleTest:bankLabel','Controller bank label must stay zero.');
    end
    % Positive guard and finite RC exercise actual retained return charge.
    P=adc_parameters();P.front.single_guard_s=5e-9;P.front.tau_sample_s(:)=20e-9;
    P=behavior_prepare_configuration(P);p=P.front;
    context=@(t,id,ev,d1,vt)[t;id;P.epoch;ev;d1;vt];
    [x,~,out]=behavior_frontend_stage('advance',P.xFE0,context(0,0,1,0,0),p);
    s=behavior_frontend_unpack(x,p);
    assert(out.valid&&all(s.phase(1:8)==2)&&~any(s.phase==1)&& ...
        all(s.capture_id(1:8)==0),'singleTest:cnv','CNV must capture the sole group without opening another.');
    captured=s;bad=s;bad.B_c(1,3)=1e-18;
    cmdBad=struct('event','observe','t_s',0,'id',0,'epoch',P.epoch);
    expect_error(@()behavior_frontend_step(bad,cmdBad,p),'singleBank:disconnectedCharge');
    bad=s;bad.B_target_c(1,3)=1e-18;
    expect_error(@()behavior_frontend_step(bad,cmdBad,p),'singleBank:disconnectedCharge');
    tOpen=-P.Ts_s+rel+p.single_guard_s;u=P.input;w=2*pi*u.frequency_hz;a=w*20e-9;
    particular=@(t)u.offset_v+u.amplitude_v/hypot(1,a)*sin(w*t+u.phase_rad-atan(a));
    expectedV=particular(0)-particular(tOpen)*exp(-(-tOpen)/20e-9);
    assert(max(abs(s.v_capture_v(1:8)-expectedV))<2e-14, ...
        'singleTest:rc','Initial 105 ns finite-RC sample differs from independent closed form.');
    tDac=12.5e-9;[x,~,~]=behavior_frontend_stage('commit',x,context(tDac,0,1,512,0),p);
    [xPre,~,~]=behavior_frontend_stage('advance',x,context(rel,0,0,0,0),p);
    before=behavior_frontend_unpack(xPre,p);vt=0.1;
    expect=before.B_c(1:8,:)-p.group_C_f(1:8,:)*vt;
    [xPost,releaseObs,returned]=behavior_frontend_stage('commit',xPre,context(rel,0,2,0,vt),p);
    after=behavior_frontend_unpack(xPost,p);
    assert(returned.released&&bits(returned.q_return_c,expect)&& ...
        all(isnan(returned.v_return_v(:,3)))&&bits(after.B_c(1:8,:),expect)&& ...
        all(after.phase(1:8)==1)&&all(after.target_id(1:8)==1)&&after.active_id==-1&& ...
        all(after.B_c(:,3)==0)&&all(after.B_target_c(:,3)==0)&&all(isfinite(releaseObs)), ...
        'singleTest:return','Release must commit actual Vtop charge before reserving next acquisition.');
    assert(all(after.acquire_open_s(1:8)==rel+p.single_guard_s), ...
        'singleTest:guard','Physical opening must be release plus guard.');
    [xHold,~,~]=behavior_frontend_stage('advance',xPost,context(rel+2e-9,1,0,0,0),p);
    held=behavior_frontend_unpack(xHold,p);
    assert(bits(held.B_c(1:8,:),expect),'singleTest:guardHold','Charge changed inside guard.');
    [xOpen,~,~]=behavior_frontend_stage('advance',xHold,context(rel+p.single_guard_s,1,0,0,0),p);
    opened=behavior_frontend_unpack(xOpen,p);
    assert(bits(opened.B_c(1:8,1),expect(:,1))&& ...
        bits(opened.B_c(1:8,2:3),opened.B_target_c(1:8,2:3)), ...
        'singleTest:openEdge','Finite-RC signal must hold while zero-tau precharge takes its target.');
    [xNext,~,out]=behavior_frontend_stage('advance',xOpen,context(P.Ts_s,1,1,0,0),p);
    next=behavior_frontend_unpack(xNext,p);
    assert(out.valid&&all(next.phase(1:8)==2)&&all(next.capture_id(1:8)==1)&& ...
        ~any(next.phase==1),'singleTest:next','Next CNV must reuse only the same bank.');
    % One 1039Cu bank, with the 38th legacy ABI column physically absent.
    combinedCu=8*p.unit_cap_f;switched=8*sum(p.C_f(1,1:37));bias=8*p.C_f(1,38);
    assert(abs(switched/combinedCu-1039)<1e-9&&bias==0&& ...
        abs(combinedCu-27e-15)<1e-26&&all(p.C_f(:,38)==0), ...
        'singleTest:geometry','Require 1039 nominal units and no 17Cu bias capacitor.');
    assert(~P.ni.cap_mismatch,'singleTest:nominalCap','Disconnected column is not mismatch.');
    % Oracle fixture was generated independently using exact rational charge masks.
    csv=fullfile(pkg,'fixtures','d1_codebook_2048.csv');
    assert(strcmp(sha(csv),'284598ca08207dba3332175861c8851deffa18c572141ea3e8a811c61d31e582'), ...
        'singleTest:oracle','Independent codebook identity differs.');
    oracle=readtable(csv,'TextType','string');
    assert(height(oracle)==2048&&isequal(oracle.D1raw,(0:2047).'), ...
        'singleTest:oracle','Oracle raw-code order differs.');
    % All 2048 D1 words: actual grouped charge versus independent codebook.
    for d1=0:2047
        cmd=struct('event','dac_commit','t_s',0,'id',0,'epoch',P.epoch,'d1_code',d1);
        [~,q]=behavior_frontend_step(captured,cmd,p);
        c=floor(d1/32);fine=mod(d1,32);signedWeight=oracle.target_charge_CuVR(d1+1);
        assert(signedWeight==32*c+2*fine-1039,'singleTest:oracle','Codebook entry differs.');
        expectedQ=sum(captured.q_initial_c(1:8))-combinedCu*p.vref_v*signedWeight;
        assert(abs(q.qres_c-expectedQ)<1e-25,'singleTest:chargeCodebook','D1 %d charge mismatch',d1);
        raw=struct('raw_D1',d1,'raw_D2',0,'raw_DT',0,'sample_id',0,'epoch',P.epoch,'valid',1);
        decoded=behavior_decode(raw,P.digital);
        expectedD1=signedWeight*P.digital.vref_v/1024;
        assert(abs(decoded.d1_v-expectedD1)<1e-14&&decoded.d1_capture_bias_v==0, ...
            'singleTest:decodeCodebook','D1 %d decode mismatch',d1);
    end
    expect_error(@()try_pool(P),'singleBank:only');
    expect_error(@()try_feature(P,'dem'),'singleBank:unsupportedNI');
    expect_error(@()try_feature(P,'dither'),'singleBank:unsupportedNI');
    expect_error(@()try_feature(P,'jitter'),'singleBank:unsupportedNI');
    expect_error(@()try_feature(P,'bank'),'singleBank:calibration');
    expect_error(@()try_feature(P,'rate'),'singleBank:rate');
    expect_error(@()SAR20('calibration','freeze','not_used'),'singleBank:calibrationUnavailable');
    fixture=fullfile(pkg,'fixtures','production_pool_i2_n8.mat');
    assert(strcmp(sha(fixture),'7ba67f7f579b159be309565547dc5efdc2b9376857eb7b10e251a008c2b944e0'), ...
        'singleTest:fixture','Historical pool P changed.');
    old=load(fixture,'P');expect_error(@()behavior_dac_backend_parameters(old.P),'singleBank:only');
    assert(isequaln(rngBefore,rng),'singleTest:rng','Global RNG changed.');
    report=struct('status','passed','scope','function-level only, no Simulink or analog signoff', ...
        'segments',8,'physical_banks',1,'release_s',rel,'sample_period_s',P.Ts_s, ...
        'guard_s',p.single_guard_s,'active_window_s',P.Ts_s-rel-p.single_guard_s, ...
        'nominal_cu',1039,'unit_cap_f',combinedCu,'bias_cap_f',bias, ...
        'codebook_checked',2048,'codebook_sha256',sha(csv),'no_ADI_or_10M',true);
    P=P_for_model; % Actual standard prepared single-bank P for isolated graph work.
end
function try_pool(P),P.front.single_bank=false;behavior_dac_backend_parameters(P);end
function try_feature(P,kind)
    switch kind
        case 'dem',P.front.dem_enabled=true;
        case 'dither',P.front.dither_enabled=true;
        case 'jitter',P.front.jitter.enabled=true;
        case 'bank',P.bank.enabled=true;
        case 'rate',P.Ts_s=100e-9;
    end
    behavior_dac_backend_parameters(P);
end
function expect_error(fun,id)
    try,fun();catch ex,assert(strcmp(ex.identifier,id),'singleTest:errorID', ...
            'Expected %s, got %s.',id,ex.identifier);return;end
    error('singleTest:noError','Expected %s.',id);
end
function yes=bits(a,b)
    yes=isa(a,'double')&&isa(b,'double')&&isequal(size(a),size(b))&& ...
        isequal(typecast(a(:),'uint64'),typecast(b(:),'uint64'));
end
function h=sha(file)
    d=dir(file);assert(isscalar(d)&&~d.isdir&&d.bytes<=300e6,'singleTest:file','Missing or oversized file.');
    f=fopen(file,'rb');assert(f>=0,'singleTest:file','Cannot open file.');
    c=onCleanup(@()fclose(f)); %#ok<NASGU>
    b=fread(f,Inf,'*uint8');md=java.security.MessageDigest.getInstance('SHA-256');
    md.update(typecast(b(:),'int8'));h=lower(reshape(dec2hex(typecast(md.digest(),'uint8'),2).',1,[]));
end
