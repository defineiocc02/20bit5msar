function report=test_ra_dense_observer(candidateRoot)
%TEST_RA_DENSE_OBSERVER Synthetic offline test DRAFT; not yet run in MATLAB.
% Only validates function plumbing and negative gates, not a real ADC trace.
    assert(~bdIsLoaded('SarAdc'),'raDenseTest:model','No model may be loaded.');
    local=fileparts(mfilename('fullpath'));oldPath=path;
    restore=onCleanup(@()path(oldPath)); %#ok<NASGU>
    addpath(local,genpath(fullfile(candidateRoot,'current','src')), ...
        fullfile(candidateRoot,'config'),candidateRoot,'-begin');rehash;
    before=rng;
    P=adc_parameters();
    P.backend.ni.ra_noise=true;
    P.backend.ra_noise=struct('schema','sar20-ra-ou/v1', ...
        'sigma_vx_rms',1e-4,'seed_u64',uint64(9481));
    P.backend.az.mode='ordinary';P.backend.ni.az=true;P.digital.az_mode='ordinary';
    P.backend.ra.vos_input_v=1e-3;P.backend.az.write_tau_s=[3e-9;4e-9];
    P.backend.az.leak_tau_s=[25e-9;30e-9];
    P.backend.az.sense_injection_half_v=[2e-5;-3e-5];
    P.front.tau_dac_s(:)=8e-9;P.backend.dac_coupling.enabled=true;
    P=behavior_prepare_configuration(P);behavior_dac_backend_parameters(P);
    g0=find(arrayfun(@(g)any(strcmp({g.events.type},'ra_start')),P.groups));
    assert(isscalar(g0),'raDenseTest:calendar','Expected one RA-start group.');
    t0=P.groups(g0).time_s;t1=P.groups(g0+1).time_s;
    ctx=@(t,id,event,d1,vtop)[t;id;P.epoch;event;d1;vtop];
    [fe,~,~]=behavior_frontend_stage('advance',P.xFE0,ctx(0,0,1,0,0),P.front);
    [fe,~,~]=behavior_frontend_stage('commit',fe,ctx(12.5e-9,0,1,1234,0),P.front);
    [fe,front,~]=behavior_frontend_stage('advance',fe,ctx(t0,0,0,0,0),P.front);
    ctop=P.backend.dac_coupling.fixed_single_bank_ctop_f;
    az=[0;ctop;zeros(19,1);0;1;1;0;P.epoch];
    [bk,~]=behavior_backend_stage('commit',P.xBK0,0,az,P.backend);
    [bk,~]=behavior_backend_stage('advance',bk,t0,zeros(26,1),P.backend,fe);
    command=[front(3);front(5);zeros(19,1);1;0;0;0;P.epoch];
    [bk,~]=behavior_backend_stage('commit',bk,t0,command,P.backend);
    [endBk,endObs]=behavior_backend_stage('advance',bk,t1,zeros(26,1),P.backend,fe);
    rec=struct('t_start_s',t0,'t_stop_s',t1,'fe_after_start353',fe, ...
        'ra_after_start48',bk,'fe_old_at_stop353',fe,'ra_old_at_stop48',bk, ...
        'ra_advance_stop48',endBk,'ra_advance_obs_stop8',endObs);
    q=[t0;t0+(t1-t0)/3;t0+2*(t1-t0)/3];
    oldP=P;oldRec=rec;
    a=ra_dense_observer(P,rec,q,candidateRoot);
    b=ra_dense_observer(P,rec,q,candidateRoot);
    assert(bits(a.deterministic_drift_obs8,b.deterministic_drift_obs8)&& ...
        bits(a.start_qres_over_cf_v,front(3)/P.backend.ra.Cf_f)&& ...
        ~bits(a.start_qres_over_cf_v,a.recorded_endpoint_qres_over_cf_v)&& ...
        bits(a.deterministic_drift_obs8(1,1),bk(2))&& ...
        a.original_endpoint_replay_bitwise&&~a.new_interior_ou_innovations, ...
        'raDenseTest:drift','Repeated drift, target, VX or endpoint contract differs.');
    assert(isequaln(P,oldP)&&isequaln(rec,oldRec)&&isequaln(rng,before), ...
        'raDenseTest:purity','P, trace or global RNG changed.');
    wrong=rec;wrong.fe_old_at_stop353(1)=wrong.fe_old_at_stop353(1)+eps(wrong.fe_old_at_stop353(1));
    expect(@()ra_dense_observer(P,wrong,q,candidateRoot),'raDense:retention');
    wrong=rec;wrong.ra_advance_obs_stop8(1)=wrong.ra_advance_obs_stop8(1)+eps(wrong.ra_advance_obs_stop8(1));
    expect(@()ra_dense_observer(P,wrong,q,candidateRoot),'raDense:endpointMismatch');
    expect(@()ra_dense_observer(P,rec,t1,candidateRoot),'raDense:query');

    % Verify the exact one-based 2015-column mapping without claiming this
    % synthetic timeseries is a recorded simulation trace.
    rows=zeros(2,2015);rows(:,1)=0;rows(:,2)=[g0;g0+1];
    rows(1,1415:1767)=fe.';rows(1,1960:2007)=bk.';
    rows(2,3:355)=fe.';rows(2,1768:1815)=bk.';
    rows(2,1816:1863)=endBk.';rows(2,2008:2015)=endObs.';
    tap=timeseries(rows,[t0;t1]);
    viaTap=ra_dense_from_tap(P,tap,0,q,candidateRoot);
    assert(bits(viaTap.deterministic_drift_obs8,a.deterministic_drift_obs8)&& ...
        viaTap.ra_start_row==1&&viaTap.first_d2_prepare_row==2, ...
        'raDenseTest:layout','2015-column extraction differs.');
    report=struct('status','passed','scope','synthetic function test only; no model/real trace', ...
        'source_manifest','73867eabe50b70920cd3373190832e2d78426c59b0116d6062ff94c4c903f14c', ...
        'endpoint_bitwise',true,'same_start_inputs',true,'layout_width',2015, ...
        'global_rng_unchanged',true,'no_interior_ou_key',true);
end
function expect(fun,id)
    try,fun();catch e
        assert(strcmp(e.identifier,id),'raDenseTest:errorID','Expected %s, got %s',id,e.identifier);return;
    end
    error('raDenseTest:noError','Expected %s',id);
end
function yes=bits(a,b)
    yes=isa(a,'double')&&isa(b,'double')&&isequal(size(a),size(b))&& ...
        isequal(typecast(a(:),'uint64'),typecast(b(:),'uint64'));
end
