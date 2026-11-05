function report=test_comparator_single()
%TEST_COMPARATOR_SINGLE Single-bank M8 synthetic function-level test.
% Values below are deliberately small test fixtures, NOT paper/PDK normal
% parameters and NOT a performance experiment. No model is loaded or saved.
    assert(~bdIsLoaded('SarAdc'),'cmpSingle:model','Use a new headless process.');
    pkg=fileparts(fileparts(mfilename('fullpath')));
    oldPath=path;restore=onCleanup(@()path(oldPath)); %#ok<NASGU>
    names={'adc_parameters','behavior_prepare_configuration','behavior_dac_backend_parameters', ...
        'behavior_single_guard','behavior_ra_noise_guard','behavior_ra_noise_validate_backend', ...
        'behavior_backend_stage','behavior_backend_step','behavior_backend_pack','behavior_backend_unpack', ...
        'behavior_frontend_init','behavior_frontend_step','behavior_frontend_stage', ...
        'behavior_control_stage','behavior_sar_step','behavior_sar_pack','behavior_sar_unpack', ...
        'behavior_comparator_configuration','behavior_comparator_sample', ...
        'behavior_comparator_keyed_normal','sar20_ra_keyed_normal'};
    loaded=inmem('-completenames');
    for i=1:numel(loaded)
        [~,stem]=fileparts(loaded{i});
        assert(~any(strcmpi(stem,names)),'cmpSingle:cache', ...
            'Use a fresh process; candidate function %s is already cached.',stem);
    end
    addpath(genpath(fullfile(pkg,'current','src')),fullfile(pkg,'config'),pkg,'-begin');
    rehash;
    for i=1:numel(names),require_path(names{i},pkg);end
    before=rng;
    P=behavior_prepare_configuration(adc_parameters());
    assert(P.Ts_s==200e-9&&P.front.single_bank&&P.control.single_bank&& ...
        ~P.transport.enabled&&~P.front.dem_enabled&&~P.front.dither_enabled&& ...
        all(P.front.C_f(:,38)==0),'cmpSingle:base','Expected single-bank 5 MS/s baseline.');
    assert(~P.backend.ni.ra_noise&&~isfield(P.control,'comparator'), ...
        'cmpSingle:base','Baseline must be OU and comparator profile OFF.');
    profile=struct('enabled',true,'sar1_offset_v',0,'sar1_noise_rms_v',0, ...
        'sar2_offset_v',0,'sar2_noise_rms_v',1e-9, ...
        'seed_u64',uint64(20261104),'tie_decision',true);
    ou=struct('schema','sar20-ra-ou/v1','sigma_vx_rms',1e-9, ...
        'seed_u64',uint64(20261104));

    % Exercise the real prepare/check paths. The original P is never edited.
    zero=profile;zero.sar2_noise_rms_v=0;
    Z=P;Z.control.comparator=zero;Z=behavior_prepare_configuration(Z);
    behavior_dac_backend_parameters(Z);
    D=P;disabled=profile;disabled.enabled=false;D.control.comparator=disabled;
    D=behavior_prepare_configuration(D);behavior_dac_backend_parameters(D);
    C=P;C.control.comparator=profile;C=behavior_prepare_configuration(C);
    behavior_dac_backend_parameters(C);
    CZ=C;CZ.backend.ni.ra_noise=true;CZ.backend.ra_noise=ou;
    CZ.backend.ra_noise.sigma_vx_rms=0;
    CZ=behavior_prepare_configuration(CZ);behavior_dac_backend_parameters(CZ);
    assert(isequaln(C.control.comparator,CZ.control.comparator), ...
        'cmpSingle:crossProfile','CMP profile differs across the OU zero comparison.');
    R0=P;R0.backend.ni.ra_noise=true;R0.backend.ra_noise=ou;
    R0.backend.ra_noise.sigma_vx_rms=0;
    R0=behavior_prepare_configuration(R0);behavior_dac_backend_parameters(R0);
    J=P;J.backend.ni.ra_noise=true;J.backend.ra_noise=ou;J.control.comparator=profile;
    J=behavior_prepare_configuration(J);behavior_dac_backend_parameters(J);
    assert(J.ni.comparator_noise&&J.ni.comparator_noise_scope.sar2_and_tracking&& ...
        ~J.ni.comparator_noise_scope.sar1_fine&& ...
        ~J.ni.comparator_noise_scope.flash_preconvert&&J.ni.ra_noise, ...
        'cmpSingle:coverage','Combined scope must not claim fine/Flash noise.');
    % Small synthetic joint setup fixture only; this is not a normal profile.
    U=J;U.backend.az.mode='ordinary';U.backend.ni.az=true;U.digital.az_mode='ordinary';
    U.front.tau_dac_s(:)=1e-9;U.backend.dac_coupling.enabled=true;
    U.front.tau_sample_s(:)=1e-9;U.front.ktc_enabled=true;
    U=behavior_prepare_configuration(U);behavior_dac_backend_parameters(U);
    assert(U.backend.ni.ra_noise&&U.backend.ni.az&&U.front.ktc_enabled&& ...
        U.ni.sample_ktc&&U.ni.sample_settling&&U.ni.comparator_noise&& ...
        all(U.front.C_f(:,38)==0),'cmpSingle:jointSetup', ...
        'Joint setup lost OU/AZ/DAC/RC/kTC/CMP or the disconnected branch.');

    % Advance the one retained backend VX to the actual first D2 event.
    [g,e]=event_group(P,'d2_decide',0);t1=P.groups(g).time_s;
    t0=P.groups(g-1).time_s;
    s=behavior_backend_unpack(P.xBK0);s.time_s=t0;s.vx_v=0.01;
    s.command.ra_on=true;s.command.reset=false;s.command.sample_id=0;
    s.command.epoch=double(P.epoch);x=behavior_backend_pack(s);unused=zeros(26,1);
    [xoff,ooff]=behavior_backend_stage('advance',x,t1,unused,P.backend);
    [xzero,ozero]=behavior_backend_stage('advance',x,t1,unused,R0.backend);
    same_bits(xoff,xzero,'OU zero state');same_bits(ooff,ozero,'OU zero observation');
    [xon,oon]=behavior_backend_stage('advance',x,t1,unused,J.backend);
    [xon2,oon2]=behavior_backend_stage('advance',x,t1,unused,J.backend);
    same_bits(xon,xon2,'OU repeated state');same_bits(oon,oon2,'OU repeated observation');
    assert(~same_double(xoff(2),xon(2)),'cmpSingle:ouPath','OU fixture did not affect retained VX.');

    % Feed exactly the returned VY to the comparator; it is not a new sample
    % of VX, reconstructed RAW, or a separate ADC/RA state.
    obs=zeros(7,1);cmp=[0;double(oon(2)>=0);oon(2)];
    sc=behavior_sar_unpack(P.xSC0);sc.active=true;sc.sample_id=0;
    sc.epoch=double(P.epoch);sc.bank=0;sc.ra_on=true;
    sc.d2_count=0;sc.d2_pending=true;sc.d2_bit=11;
    old=behavior_sar_pack(sc);event=[0;g];
    [a,ya,sa]=behavior_control_stage('decide',old,event,obs,cmp,P);
    [b,yb,sb]=behavior_control_stage('decide',old,event,obs,cmp,Z);
    [d,yd,sd]=behavior_control_stage('decide',old,event,obs,cmp,D);
    same_bits(a,b,'CMP zero state');same_bits(ya,yb,'CMP zero output');same_bits(sa,sb,'CMP zero signs');
    same_bits(a,d,'CMP disabled state');same_bits(ya,yd,'CMP disabled output');same_bits(sa,sd,'CMP disabled signs');
    [n1,y1,u1]=behavior_control_stage('decide',old,event,obs,cmp,J);
    [n2,y2,u2]=behavior_control_stage('decide',old,event,obs,cmp,J);
    same_bits(n1,n2,'joint repeated state');same_bits(y1,y2,'joint repeated output');
    same_bits(u1,u2,'joint repeated signs');
    [co,yco,sco]=behavior_control_stage('decide',old,event,obs,cmp,C);
    [cz,ycz,scz]=behavior_control_stage('decide',old,event,obs,cmp,CZ);
    same_bits(co,cz,'CMP on OU zero state');same_bits(yco,ycz,'CMP on OU zero output');
    same_bits(sco,scz,'CMP on OU zero signs');
    cmpInput=struct('sample_v',0,'vres_v',0,'vy_v',oon(2), ...
        'decision1',cmp(1),'decision2',cmp(2),'valid',true,'late',false);
    e.absolute_time_s=t1;e.sample_id=0;e.epoch=double(P.epoch);
    [expected,diag]=behavior_comparator_sample(e,cmpInput,J.control.comparator);
    assert(same_double(diag.input_v,oon(2))&& ...
        bitget(uint32(y1(6)),12)==expected.decision2, ...
        'cmpSingle:vyPath','Actual backend VY must be the comparator input and decide RAW.');
    oldAgain=behavior_sar_unpack(old);
    assert(oldAgain.d2_pending&&oldAgain.d2_count==0, ...
        'cmpSingle:outputState','Outputs changed its input state.');

    % Controlled threshold-crossing TEST ONLY: cancel the actual returned VY
    % with an explicit offset; a fixed negative keyed draw must flip the native
    % high decision. This constructed offset is not a normal-P estimate.
    assert(oon(2)>0&&cmp(2)==1,'cmpSingle:flipFixture','Expected positive native VY.');
    zv=behavior_comparator_keyed_normal(profile.seed_u64,double(P.epoch),0,2,0);
    assert(zv<0,'cmpSingle:flipFixture','Selected deterministic test key must be negative.');
    F=J;F.control.comparator.sar2_offset_v=-oon(2);
    F=behavior_prepare_configuration(F);behavior_dac_backend_parameters(F);
    [flip,yflip,~]=behavior_control_stage('decide',old,event,obs,cmp,F);
    sf=behavior_sar_unpack(flip);sp=behavior_sar_unpack(a);
    assert(bitget(uint32(ya(6)),12)==1&&bitget(uint32(yflip(6)),12)==0&& ...
        strcmp(sf.pending.type,'d2_feedback')&&sf.pending.decision==0&& ...
        strcmp(sp.pending.type,'d2_feedback')&&sp.pending.decision==1, ...
        'cmpSingle:flip','Threshold crossing must change RAW and pending decision.');
    [gf,~]=event_group(P,'d2_feedback',0);
    [afterFlip,~,signFlip]=behavior_control_stage('due',flip,[0;gf],obs,cmp,F);
    [afterPlain,~,signPlain]=behavior_control_stage('due',a,[0;gf],obs,cmp,P);
    sf=behavior_sar_unpack(afterFlip);sp=behavior_sar_unpack(afterPlain);
    assert(sf.d2_signs(1)==-1&&sp.d2_signs(1)==1&& ...
        signFlip(1)==-1&&signPlain(1)==1, ...
        'cmpSingle:flipFeedback','Next due must commit the changed physical sign.');

    % Test the keyed domain separation; different SHA payload domains do not
    % prove physical noise independence or a statistical covariance bound.
    [~,raKey]=sar20_ra_keyed_normal(ou.seed_u64,double(P.epoch),0,t0,t1);
    [~,cmpKey]=behavior_comparator_keyed_normal(profile.seed_u64,double(P.epoch),0,2,0);
    assert(~strcmp(raKey,cmpKey),'cmpSingle:domains','RA and comparator key domains collided.');

    % Synthetic controller-only M8 sequence: due feedback first at each shared
    % tick, then next TA decision. Constant VY is deliberately not an analog
    % closed-loop replay; the later actual graph must validate CT kick timing.
    sc=behavior_sar_unpack(P.xSC0);sc.active=true;sc.sample_id=0;
    sc.epoch=double(P.epoch);sc.bank=0;sc.ra_on=true;sc.d2_count=12;
    state=behavior_sar_pack(sc);
    for k=0:7
        [gc,~]=event_group(P,'ta_compare',k);
        if k>0
            [gf,~]=event_group(P,'ta_feedback',k-1);
            assert(gc==gf,'cmpSingle:priority','Due feedback must share the next TA tick.');
            [state,~,~]=behavior_control_stage('due',state,[0;gf],obs,cmp,J);
        end
        [state,~,~]=behavior_control_stage('decide',state,[0;gc],obs,cmp,J);
    end
    final=behavior_sar_unpack(state);
    assert(final.track_count==8&&final.feedback_count==7&&isempty(final.pending.type), ...
        'cmpSingle:m8','Require eight decisions, seven feedbacks, and no pending eighth.');

    % M1 and coefficient/calibration activation remain explicitly unavailable.
    Q=J;Q.control.tracking_count=1;Q.digital.tracking_count=1;
    expect(@()behavior_comparator_configuration(Q,'check'),'sar20Cmp:m8Only');
    for name={'training','cal_cfg','frozen','bank'}
        Q=J;Q.(name{1}).enabled=true;
        expect(@()behavior_comparator_configuration(Q,'check'),'sar20Cmp:unqualifiedCalibration');
    end
    Q=J;Q.ni.comparator_noise_scope.flash_preconvert=true;
    expect(@()behavior_comparator_configuration(Q,'check'),'sar20Cmp:scope');
    Q=J;Q.ni.comparator_noise=false;
    expect(@()behavior_comparator_configuration(Q,'check'),'sar20Cmp:coverage');
    Q=J;Q.control=rmfield(Q.control,'comparator');Q.ni.comparator_noise=true;
    expect(@()behavior_comparator_configuration(Q,'check'),'sar20Cmp:coverage');
    Q=J;Q.backend.ra.slew_v_per_s=1e9;
    expect(@()behavior_ra_noise_validate_backend(Q.backend),'sar20RA:finiteSlew');
    Q=J;Q.backend.az.mode='chop';Q.backend.ni.az=true;
    expect(@()behavior_ra_noise_validate_backend(Q.backend),'sar20RA:az');
    Q=J;Q.backend.dac_coupling.fixed_single_bank_ctop_f= ...
        Q.backend.dac_coupling.fixed_single_bank_ctop_f+eps(Q.backend.dac_coupling.fixed_single_bank_ctop_f);
    expect(@()behavior_dac_backend_parameters(Q),'sar20Cmp:jointBinding');
    Q=J;Q.Ts_s=100e-9;
    expect(@()behavior_single_guard(Q,true),'singleBank:rate');
    Q=U;Q.front.tau_sample_s(1)=2*Q.front.tau_sample_s(1);
    expect(@()behavior_dac_backend_parameters(Q),'sar20RA:coverageKTC');
    Q=J;Q.front.C_f(:,38)=1e-18;
    expect(@()behavior_dac_backend_parameters(Q),'singleBank:geometry');
    assert(isequaln(before,rng),'cmpSingle:rng','Global RNG state changed.');
    for i=1:numel(names),require_path(names{i},pkg);end
    report=struct('status','passed','scope', ...
        'synthetic single-bank M8 function test only; no graph, normal-P claim, or spectrum', ...
        'cmp_off_zero_bits',true,'ou_off_zero_bits',true,'cmp_on_ou_zero_bits',true,'joint_reentrant',true, ...
        'vy_input_wired',true,'controlled_flip_to_feedback',true,'full_joint_setup_only',true, ...
        'distinct_key_domains',true,'ta_compare',8,'ta_feedback',7, ...
        'm1_cal_scope_rejections',true,'global_rng_unchanged',true);
end

function require_path(name,pkg)
    f=which(name);
    assert(~isempty(f)&&startsWith(lower(strrep(f,'\','/')), ...
        [lower(strrep(pkg,'\','/')) '/']),'cmpSingle:path','Unexpected %s: %s',name,f);
end

function [g,e]=event_group(P,name,index)
    g=[];e=[];hits=0;
    for i=1:numel(P.groups)
        events=P.groups(i).events;
        for k=1:numel(events)
            if strcmp(events(k).type,name)&&events(k).index==index,g=i;e=events(k);hits=hits+1;end
        end
    end
    assert(hits==1&&isscalar(g)&&isstruct(e),'cmpSingle:event','Expected exactly one event.');
end

function expect(f,id)
    try,f();catch err
        assert(strcmp(err.identifier,id),'cmpSingle:errorID','Expected %s got %s.',id,err.identifier);return;
    end
    error('cmpSingle:noError','Expected %s.',id);
end

function yes=same_double(a,b)
    yes=isa(a,'double')&&isa(b,'double')&&isequal(size(a),size(b))&& ...
        isequal(typecast(a(:),'uint64'),typecast(b(:),'uint64'));
end

function same_bits(a,b,label)
    assert(same_double(a,b),'cmpSingle:bits','Double bits differ: %s.',label);
end
