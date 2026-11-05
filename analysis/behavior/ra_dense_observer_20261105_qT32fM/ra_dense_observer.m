function out=ra_dense_observer(P,record,queryTimes,candidateRoot)
%RA_DENSE_OBSERVER Offline counterfactual RA drift from recorded old states.
% Pure read-only analysis: never called by the model, never commits an output
% state, never adds solver/event hits and never mutates RNG or its arguments.
% record must contain SAME-RUN values:
%   t_start_s, t_stop_s                         exact binary64 event times
%   fe_after_start353, ra_after_start48         group-end delay INPUTS at t_start
%   fe_old_at_stop353, ra_old_at_stop48         delay OUTPUTS at next event
%   ra_advance_stop48, ra_advance_obs_stop8     actual RaAdvance outputs at stop
% For OU ON the interior is a no-NEW-OU-innovation deterministic continuation
% from the recorded TOTAL initial VX. It is not an actual OU path or a bridge.
% A single endpoint replay uses only the ORIGINAL [start,stop] key; it must be
% bitwise identical to the actual recorded RaAdvance state/obs before output.

    assert(ischar(candidateRoot)&&isrow(candidateRoot)&&isfolder(candidateRoot), ...
        'raDense:root','candidateRoot must be the existing frozen candidate directory.');
    assert(~bdIsLoaded('SarAdc'),'raDense:model','Use an offline process with no loaded SarAdc.');
    verify_sources(candidateRoot);
    assert(isstruct(P)&&isscalar(P)&&isstruct(record)&&isscalar(record), ...
        'raDense:input','Prepared P and the recorded trace must be scalar structs.');
    keys={'t_start_s','t_stop_s','fe_after_start353','ra_after_start48', ...
        'fe_old_at_stop353','ra_old_at_stop48','ra_advance_stop48','ra_advance_obs_stop8'};
    assert(all(isfield(record,keys)),'raDense:record','Require the complete same-run trace.');
    t0=record.t_start_s;t1=record.t_stop_s;
    assert(isa(t0,'double')&&isreal(t0)&&isscalar(t0)&&isfinite(t0)&&t0>=0&& ...
        isa(t1,'double')&&isreal(t1)&&isscalar(t1)&&isfinite(t1)&&t1>t0, ...
        'raDense:time','Require the original ordered binary64 event timestamps.');
    assert(isa(queryTimes,'double')&&isreal(queryTimes)&&isvector(queryTimes)&& ...
        ~isempty(queryTimes)&&all(isfinite(queryTimes(:)))&& ...
        all(queryTimes(:)>=t0 & queryTimes(:)<t1), ...
        'raDense:query','Queries must satisfy start <= t < original stop.');
    fe0=checkvec(record.fe_after_start353,353);
    bk0=checkvec(record.ra_after_start48,48);
    assert(bits(fe0,checkvec(record.fe_old_at_stop353,353))&& ...
        bits(bk0,checkvec(record.ra_old_at_stop48,48)), ...
        'raDense:retention','Group-end next state must equal the next hit old state bitwise.');
    endState=checkvec(record.ra_advance_stop48,48);
    endObs=checkvec(record.ra_advance_obs_stop8,8);
    assert(bits(endState(1),t1),'raDense:endTime', ...
        'Recorded RaAdvance state time must equal the original event Time bits.');

    % This checks the actual applied single-bank/5M/OU/AZ/DAC/coverage P; it
    % returns P.backend without normalizing it or touching a model/state.
    p=behavior_dac_backend_parameters(P);
    assert(P.front.single_bank&&~P.transport.enabled&& ...
        isfinite(p.ra.UGB_hz)&&p.ra.UGB_hz>0&&isinf(p.ra.slew_v_per_s)&& ...
        p.ra.slew_v_per_s>0&&all(isfinite(p.dac_coupling.tau_dac_s(:)))&& ...
        any(strcmp(p.az.mode,{'off','ordinary'})), ...
        'raDense:scope','Require single bank, linear finite-UGB RA and ordinary/off AZ.');
    expected=behavior_event_groups(behavior_calendar(P.control),false);
    assert(numel(expected)==48&&isequaln(P.adc_groups,expected)&&isequaln(P.groups,expected), ...
        'raDense:calendar','Use the unchanged actual 48-group 5 MS/s calendar.');
    g0=find(arrayfun(@(x)any(strcmp({x.events.type},'ra_start')),expected));
    assert(isscalar(g0)&&g0<numel(expected),'raDense:calendar','Missing unique ra_start.');
    events=expected(g0+1).events;
    assert(numel(events)==1&&strcmp(events.type,'d2_prepare')&&events.index==0, ...
        'raDense:calendar','The next group must be the first D2 prepare.');
    bk=behavior_backend_unpack(bk0);fe=behavior_frontend_unpack(fe0,P.front);
    id=bk.command.sample_id;epoch=bk.command.epoch;
    assert(id>=0&&id==floor(id)&&epoch==P.epoch&&bk.command.ra_on&& ...
        ~bk.command.reset&&~bk.command.az_on&&fe.has_time&& ...
        bits(bk.time_s,t0)&&bits(fe.time_s,t0)&& ...
        bits(t0,id*P.Ts_s+expected(g0).time_s)&& ...
        bits(t1,id*P.Ts_s+expected(g0+1).time_s), ...
        'raDense:start','Trace is not the post-ra_start/next-event state for this sample/epoch.');

    rngBefore=rng;
    % Preserve actual OU enable and all its forcing/Ctop guards. sigma=0 on
    % this local copy exits sar20_ra_ou_increment before hashing any key.
    pNoNewOu=p;
    if p.ni.ra_noise,pNoNewOu.ra_noise.sigma_vx_rms=0;end
    % Same-command local invocation may not conceal a pending CINC kick.
    [~,atStart]=behavior_backend_step(bk,bk.command,0,pNoNewOu);
    assert(all(atStart.kick_half_v==0)&&bits(atStart.predicted.vx_v,atStart.actual.vx_v), ...
        'raDense:pendingKick','Start state is not post-commit: a CINC kick remains.');
    % This is the one existing full-interval key, not a new interior draw.
    [replayedState,replayedObs]=behavior_backend_stage('advance',bk0,t1,zeros(26,1),p,fe0);
    assert(bits(replayedState,endState)&&bits(replayedObs,endObs), ...
        'raDense:endpointMismatch','Original-key replay does not match actual RaAdvance state/obs bitwise.');
    [repeatState,repeatObs]=behavior_backend_stage('advance',bk0,t1,zeros(26,1),p,fe0);
    assert(bits(replayedState,repeatState)&&bits(replayedObs,repeatObs), ...
        'raDense:reentrant','Original-key replay is not repeatable.');

    q=queryTimes(:);drift=zeros(numel(q),8);
    for k=1:numel(q)
        % Every query starts from exactly the SAME recorded xBK0/xFE0. All
        % internally returned xNext values are discarded, never fed back.
        [~,y]=behavior_backend_stage('advance',bk0,q(k),zeros(26,1),pNoNewOu,fe0);
        drift(k,:)=y.';
    end
    assert(isequaln(rngBefore,rng),'raDense:rng','Global MATLAB RNG changed.');
    noiseOn=logical(p.ni.ra_noise);
    noiseSigma=0;if noiseOn,noiseSigma=p.ra_noise.sigma_vx_rms;end
    out=struct('scope','offline deterministic drift; no interior OU sample and no state commit', ...
        'sample_id',id,'epoch',epoch,'t_start_s',t0,'t_stop_s',t1, ...
        'query_time_s',q,'obs_columns',{{'VX_V','VY_V','Vtop_V','target_V','NG','tau_s','AZdiff_V','resetVX_V'}}, ...
        'start_qres_over_cf_v',bk.command.qres_c/p.ra.Cf_f, ...
        'recorded_endpoint_qres_over_cf_v',endObs(4), ...
        'deterministic_drift_obs8',drift,'recorded_endpoint_obs8',endObs, ...
        'original_endpoint_replay_bitwise',true,'same_start_next_old_bitwise',true, ...
        'new_interior_ou_innovations',false,'original_endpoint_key_replayed',noiseOn&&noiseSigma>0, ...
        'interior_is_actual_ou_path',false,'global_rng_unchanged',true, ...
        'candidate_manifest_sha256','73867eabe50b70920cd3373190832e2d78426c59b0116d6062ff94c4c903f14c');
end

function v=checkvec(v,n)
    assert(isa(v,'double')&&isreal(v)&&isvector(v)&&numel(v)==n, ...
        'raDense:width','Recorded state/observation has invalid width or type.');
    v=v(:);
    if n==353
        % Parked/unopened FE aperture, DEM and open-time slots intentionally
        % carry NaN sentinels. Preserve their exact binary payload in bit checks.
        sentinel=false(353,1);sentinel([259:276 282:299 318:353])=true;
        assert(all(isfinite(v(~sentinel)))&&all(~isinf(v(sentinel))), ...
            'raDense:finite','FE physical/command fields must be finite; only documented metadata may be NaN.');
    else
        assert(all(isfinite(v)),'raDense:finite','RA state/observation must be finite.');
    end
end
function yes=bits(a,b)
    yes=isa(a,'double')&&isa(b,'double')&&isequal(size(a),size(b))&& ...
        isequal(typecast(a(:),'uint64'),typecast(b(:),'uint64'));
end
function verify_sources(root)
    expected='73867eabe50b70920cd3373190832e2d78426c59b0116d6062ff94c4c903f14c';
    assert(strcmp(sha(fullfile(root,'MANIFEST.json')),expected),'raDense:manifest','Wrong frozen source manifest.');
    pins=fullfile(fileparts(mfilename('fullpath')),'SOURCE_PINS.json');
    assert(strcmp(sha(pins),'4926aa0182de94450d6ae9c3c178d97dfa46c21418d47fdc9dbe9806f313f120'), ...
        'raDense:pins','Observer source-pin file differs.');
    meta=jsondecode(fileread(pins));
    assert(strcmp(meta.candidate_manifest_sha256,expected)&&numel(meta.items)==20, ...
        'raDense:pins','Source-pin metadata differs.');
    loaded=inmem('-completenames');
    for k=1:numel(meta.items)
        f=fullfile(root,strrep(meta.items(k).path,'/',filesep));
        assert(strcmp(sha(f),meta.items(k).sha256),'raDense:source','Source hash changed: %s',f);
        resolved=which(meta.items(k).name);
        assert(~isempty(resolved)&&strcmpi(char(java.io.File(resolved).getCanonicalPath()), ...
            char(java.io.File(f).getCanonicalPath())),'raDense:path','Unexpected source path: %s',resolved);
        for j=1:numel(loaded)
            [~,stem]=fileparts(loaded{j});
            if strcmpi(stem,meta.items(k).name)
                assert(strcmpi(char(java.io.File(loaded{j}).getCanonicalPath()), ...
                    char(java.io.File(f).getCanonicalPath())), ...
                    'raDense:cache','Wrong cached source: %s',loaded{j});
            end
        end
    end
end
function h=sha(file)
    d=dir(file);assert(isscalar(d)&&~d.isdir&&d.bytes<=300000000,'raDense:file','Missing/oversized: %s',file);
    f=fopen(file,'rb');assert(f>=0,'raDense:file','Cannot read: %s',file);c=onCleanup(@()fclose(f)); %#ok<NASGU>
    x=fread(f,Inf,'*uint8');md=java.security.MessageDigest.getInstance('SHA-256');
    md.update(typecast(x(:),'int8'));h=lower(reshape(dec2hex(typecast(md.digest(),'uint8'),2).',1,[]));
end
