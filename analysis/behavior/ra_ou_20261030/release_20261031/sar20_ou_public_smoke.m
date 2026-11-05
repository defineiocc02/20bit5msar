function report=sar20_ou_public_smoke(projectRoot,referenceRoot,manifestPath,baselineManifestPath,jobDir)
%SAR20_OU_PUBLIC_SMOKE Frozen public-entry acceptance for the RA OU release.
% Call only after the guarded install on the run host and the targeted cache
% clearing; it owns two actual public N8 runs and restores OFF afterwards. This function never closes a user model and never installs sources.
% On failure it preserves the main model, path and any completed raw runs.
    strict_equal_selftest();
    projectRoot=canon(projectRoot);referenceRoot=canon(referenceRoot);jobDir=canon(jobDir);
    manifestPath=canon(manifestPath);baselineManifestPath=canon(baselineManifestPath);
    assert(feature('getpid')==27628&&isfolder(projectRoot)&&isfolder(referenceRoot)&& ...
        ~isfile(jobDir)&&~isfolder(jobDir)&&~inside(jobDir,projectRoot), ...
        'sar20OU:smokePaths','Need existing idle PID and a new external job directory.');
    model='SarAdc';modelFile=canon(fullfile(projectRoot,'current','models','SarAdc.slx'));
    assert(bdIsLoaded(model)&&strcmpi(canon(get_param(model,'FileName')),modelFile)&& ...
        strcmp(get_param(model,'SimulationStatus'),'stopped')&&strcmp(get_param(model,'Dirty'),'off'), ...
        'sar20OU:smokeMain','Preload the exact clean stopped user model; never auto-close it.');
    allModels=find_system('SearchDepth',0,'Type','block_diagram');
    for k=1:numel(allModels)
        if ~bdIsLibrary(allModels{k}),assert(strcmp(get_param(allModels{k},'SimulationStatus'),'stopped'), ...
                'sar20OU:smokeBusy','All non-library models must be stopped.');end
    end
    M=jsondecode(fileread(manifestPath));B=jsondecode(fileread(baselineManifestPath));
    assert(strcmp(sha(manifestPath),'d714bff5f09e3edd796c6a177f8ae122486d3bc048c84373b411d1a263179ac1')&& ...
        strcmp(sha(baselineManifestPath),'0d9dbb7132357967d0d9a930911436898d038b3f2d2c1e38fb3f088dd9356642')&& ...
        numel(M.files)==12&&numel(B.files)==105,'sar20OU:smokeManifest','Manifest identity differs.');
    assert(strcmp(sha(modelFile),M.baseline_model_sha256)&& ...
        strcmp(sha(fullfile(projectRoot,'state','applied_config.json')),M.baseline_state_sha256), ...
        'sar20OU:smokeBaseline','Model/state changed before public smoke.');
    verify_installed(projectRoot,B.files,M.files);
    % Outer installer must clear precisely the modified/new source functions
    % after installation and before this check; current disk SHA alone cannot
    % prove the bytes of an already cached same-path function.
    targetNames=cell(1,numel(M.files));
    for k=1:numel(M.files),[~,targetNames{k}]=fileparts(char(M.files(k).path));end
    targetNames=[targetNames {'sar20_ou_label_probe','sar20_ou_label_selftest','sar20_ou_guard_selftest'}];
    loaded=inmem('-completenames');
    for k=1:numel(loaded),[~,n]=fileparts(loaded{k});
        assert(~any(strcmp(n,targetNames)),'sar20OU:smokeCache', ...
            'Target function %s is still cached; use separately reviewed targeted cache handling.',n);end
    p0=fullfile(referenceRoot,'off','P.mat');s0=fullfile(referenceRoot,'off','simout.mat');
    p1=fullfile(referenceRoot,'on','P.mat');s1=fullfile(referenceRoot,'on','simout.mat');
    assert(strcmp(sha(p0),'dc064aa8fa204ac36d3f06ad128bbfd90da672c40c052de21530e7db378c353d')&& ...
        strcmp(sha(s0),'5887b6a6cabb20dbd27308c94ac2bad431787cddbc340db1d02aaa3151377e3a')&& ...
        strcmp(sha(p1),'d7e9a3757ae30330e7f09039747614145fb0701449695566629aca221bca1894')&& ...
        strcmp(sha(s1),'cd8b3faf295e508bb19d1d18f900a61fa0a7d7ce981f74a47b317629310d2a00'), ...
        'sar20OU:smokeReference','Historical isolated N8 references differ.');
    oldPath=path;oldCwd=pwd;rng0=rng;ws=get_param(model,'ModelWorkspace');
    P0=getVariable(ws,'P');D0=getVariable(ws,'DecodeP');capture0=getVariable(ws,'TrainCaptureFile');
    note0=get_param([model '/EventStep'],'AttributesFormatString');
    a=load(p0,'P');b=load(s0,'simout');c=load(p1,'P');d=load(s1,'simout');
    [same,where,why]=strict_equal(P0,a.P,'factory');
    assert(same&&isequaln(P0.digital,D0)&&ischar(capture0)&&isempty(capture0)&& ...
        ~P0.backend.ni.ra_noise&&~P0.bank.enabled,'sar20OU:smokeP', ...
        'Saved factory P differs from validated OFF P at %s (%s).',where,why);
    Pon=c.P;assert(Pon.backend.ni.ra_noise&&Pon.ni.ra_noise&& ...
        Pon.backend.ra_noise.sigma_vx_rms==0.001&&isequal(Pon.backend.ra_noise.seed_u64,uint64(20261030)), ...
        'sar20OU:smokeON','Reference ON configuration differs.');
    mkdir(jobDir);snapshot=struct('P0',P0,'DecodeP0',D0,'TrainCaptureFile',capture0, ...
        'note0',note0,'model_sha_before',sha(modelFile),'state_sha_before',M.baseline_state_sha256, ...
        'path_before',oldPath,'cwd_before',oldCwd,'rng_before',rng0); %#ok<NASGU>
    save(fullfile(jobDir,'before.mat'),'snapshot','-v7.3');
    try
        cd(jobDir);cfg=Simulink.fileGenControl('getConfig');
        assert(inside(resolve_folder(char(cfg.CacheFolder)),jobDir)&&inside(resolve_folder(char(cfg.CodeGenFolder)),jobDir), ...
            'sar20OU:smokeFilegen','Cache/codegen do not follow isolated cwd.');
        addpath(genpath(fullfile(projectRoot,'current','src')),fullfile(projectRoot,'config'),'-begin');rehash;
        verify_resolved(projectRoot,M.files);
        testsRoot=fullfile(fileparts(manifestPath),'tests');
        assert(isfield(M,'tests')&&numel(M.tests)==3,'sar20OU:smokeTests','Pinned unit tests missing.');
        for k=1:numel(M.tests)
            f=fullfile(fileparts(manifestPath),strrep(char(M.tests(k).path),'/',filesep));
            assert(isfile(f)&&strcmp(sha(f),char(M.tests(k).sha256)), ...
                'sar20OU:smokeTests','Unit test source differs: %s.',f);
        end
        addpath(testsRoot,'-begin');rehash;
        for k=1:numel(M.tests)
            f=fullfile(fileparts(manifestPath),strrep(char(M.tests(k).path),'/',filesep));
            [~,n]=fileparts(f);resolved=which(n);
            assert(~isempty(resolved)&&strcmpi(canon(resolved),canon(f))&& ...
                strcmp(sha(resolved),char(M.tests(k).sha256)), ...
                'sar20OU:smokeTests','Unit test path binding differs: %s.',n);
        end
        labelUnit=sar20_ou_label_selftest(Pon);guardUnit=sar20_ou_guard_selftest(Pon); %#ok<NASGU>
        save(fullfile(jobDir,'units_pass.mat'),'labelUnit','guardUnit','-v7.3');
        assert(strcmpi(canon(which('SAR20')),canon(fullfile(projectRoot,'SAR20.m'))), ...
            'sar20OU:smokeEntry','SAR20 does not resolve to the intended project.');
        % OFF: actual public entry, fixed P, compile, run and original bit gate.
        offApply=SAR20('apply',P0);offCheck=SAR20('check');behavior_applied_note('check',model); %#ok<NASGU>
        assert(strcmp(get_param([model '/EventStep'],'AttributesFormatString'),note0), ...
            'sar20OU:smokeOffLabel','OFF visible note changed.');
        verify_P(ws,P0,'off');offRun=SAR20('run');check_run(offRun,projectRoot);
        verify_run_manifest(offRun.run_path,B.files,M.files);
        offActual=load(fullfile(offRun.run_path,'simout.mat'),'simout');
        assert_same_logs(offActual.simout,b.simout);assert_same_roots(offActual.simout,b.simout);
        save(fullfile(jobDir,'off_pass.mat'),'offApply','offCheck','offRun','-v7.3');
        % ON: actual public apply/check/run; same saved P/seed as isolated ON.
        onApply=SAR20('apply',Pon);onCheck=SAR20('check');behavior_applied_note('check',model); %#ok<NASGU>
        verify_P(ws,Pon,'on');noteOn=get_param([model '/EventStep'],'AttributesFormatString');
        suffix=expected_suffix(Pon);assert(endsWith(noteOn,suffix),'sar20OU:smokeOnLabel', ...
            'Actual ON note must expose sigma, seed and behavior-only coverage.');
        onRun=SAR20('run');check_run(onRun,projectRoot);
        verify_run_manifest(onRun.run_path,B.files,M.files);
        onActual=load(fullfile(onRun.run_path,'simout.mat'),'simout');
        assert_same_logs(onActual.simout,d.simout);assert_same_roots(onActual.simout,d.simout);
        save(fullfile(jobDir,'on_pass.mat'),'onApply','onCheck','onRun','noteOn','-v7.3');
        % σ0 is an annotation/apply/check test only, not another simulation.
        Pzero=Pon;Pzero.backend.ra_noise.sigma_vx_rms=0;Pzero.ni.ra_noise=false;
        zeroApply=SAR20('apply',Pzero);zeroCheck=SAR20('check');behavior_applied_note('check',model); %#ok<NASGU>
        verify_P(ws,Pzero,'zero');
        noteZero=get_param([model '/EventStep'],'AttributesFormatString');
        assert(endsWith(noteZero,expected_suffix(Pzero))&&contains(noteZero,'零激励，不计噪声覆盖'), ...
            'sar20OU:smokeZeroLabel','Actual sigma-zero note is wrong.');
        save(fullfile(jobDir,'zero_label_pass.mat'),'zeroApply','zeroCheck','noteZero','-v7.3');
        % Restore OFF through public entry; this is apply/check, not a new sim.
        restoreApply=SAR20('apply',P0);restoreCheck=SAR20('check');behavior_applied_note('check',model); %#ok<NASGU>
        verify_P(ws,P0,'restored');
        assert(isequaln(getVariable(ws,'TrainCaptureFile'),capture0), ...
            'sar20OU:smokeRestore','TrainCaptureFile changed during public smoke.');
        assert(strcmp(get_param([model '/EventStep'],'AttributesFormatString'),note0), ...
            'sar20OU:smokeRestoreLabel','Restored OFF note differs from the original.');
        assert(strcmp(get_param(model,'SimulationStatus'),'stopped')&&strcmp(get_param(model,'Dirty'),'off'), ...
            'sar20OU:smokeRestore','Restored model is not stopped/clean.');
        verify_installed(projectRoot,B.files,M.files);
        assert(isequaln(rng0,rng),'sar20OU:smokeRNG','Global RNG changed.');
        restoredModelSha=sha(modelFile);restoredStateSha=sha(fullfile(projectRoot,'state','applied_config.json'));
        path(oldPath);cd(oldCwd);
        assert(strcmp(path,oldPath)&&strcmp(pwd,oldCwd)&&isequaln(rng,rng0), ...
            'sar20OU:smokeSession','Path/cwd/RNG restoration failed.');
        report=struct('status','public_off_on_zero_label_restore_pending_independent_review', ...
            'off_run',offRun.run_path,'on_run',onRun.run_path,'restored_model_sha256',restoredModelSha, ...
            'restored_state_sha256',restoredStateSha,'restored_off_simulation_run',false, ...
            'scope','Two actual public N8 runs; no N256 rerun, PSD or production signoff.');
        save(fullfile(jobDir,'result.mat'),'report','restoreApply','restoreCheck','-v7.3');
    catch e
        % Do not close, reset, clear, or silently restore a potentially dirty
        % main model. Preserve its live state and all completed public runs.
        failure=struct('identifier',e.identifier,'report',getReport(e,'extended','hyperlinks','off'), ...
            'model_loaded',bdIsLoaded(model),'path_at_failure',path,'cwd_at_failure',pwd); %#ok<NASGU>
        save(fullfile(jobDir,'failure.mat'),'failure','-v7.3');rethrow(e);
    end
end

function suffix=expected_suffix(P)
    q=P.backend.ra_noise;if q.sigma_vx_rms>0,c='已启用（行为假设）';else,c='零激励，不计噪声覆盖';end
    suffix=sprintf('\nRA OU=ON | sigmaVX(差分VX固定极点稳态RMS)=%.17g V rms | seed=0x%s | %s', ...
        q.sigma_vx_rms,upper(dec2hex(q.seed_u64,16)),c);
end
function verify_P(ws,P,tag)
    actual=getVariable(ws,'P');decode=getVariable(ws,'DecodeP');
    [same,where,why]=strict_equal(actual,P,tag);
    assert(same,'sar20OU:smokeAppliedP','Applied P differs at %s (%s).',where,why);
    [same,where,why]=strict_equal(decode,P.digital,[tag '.DecodeP']);
    assert(same,'sar20OU:smokeAppliedP','Applied DecodeP differs at %s (%s).',where,why);
end
function check_run(r,root)
    assert(isstruct(r)&&strcmp(r.status,'complete')&&r.simulation_completed&& ...
        inside(canon(r.run_path),canon(fullfile(root,'runs')))&&isfile(fullfile(r.run_path,'simout.mat'))&& ...
        isfile(fullfile(r.run_path,'parameters.mat'))&&isfile(fullfile(r.run_path,'source.zip'))&& ...
        isfile(fullfile(r.run_path,'source_manifest.json'))&&isfile(fullfile(r.run_path,'selected.mat'))&& ...
        isfield(r,'global_rng_unchanged')&&r.global_rng_unchanged, ...
        'sar20OU:smokeRun','Missing actual completed public run artifacts or RNG guard.');
    assert(isfield(r,'config_sha256')&&strcmp(sha(fullfile(r.run_path,'parameters.mat')),r.config_sha256)&& ...
        isfield(r,'source_zip_sha256')&&strcmp(sha(fullfile(r.run_path,'source.zip')),r.source_zip_sha256), ...
        'sar20OU:smokeRunIdentity','Saved public P/source archive hash differs from report.');
end
function verify_run_manifest(runDir,base,overlay)
    m=jsondecode(fileread(fullfile(runDir,'source_manifest.json')));rows=m.files;
    assert(numel(rows)==109,'sar20OU:smokeRunManifest','Expected 109 actual source entries.');
    paths=cell(numel(rows),1);
    for i=1:numel(rows),paths{i}=strrep(char(rows(i).path),char(92),'/');end
    assert(numel(unique(paths))==109,'sar20OU:smokeRunManifest','Duplicate actual source paths.');
    for i=1:numel(base)
        n=char(base(i).path);want=char(base(i).sha256);j=find(strcmp(n,{overlay.path}));
        if ~isempty(j),assert(numel(j)==1);want=char(overlay(j).target_sha256);end
        q=find(strcmp(n,paths));assert(numel(q)==1&&strcmp(char(rows(q).sha256),want), ...
            'sar20OU:smokeRunManifest','Actual run source mismatch: %s.',n);
    end
    for i=1:numel(overlay)
        if strcmp(overlay(i).operation,'add')
            n=char(overlay(i).path);q=find(strcmp(n,paths));
            assert(numel(q)==1&&strcmp(char(rows(q).sha256),char(overlay(i).target_sha256)), ...
                'sar20OU:smokeRunManifest','Actual run added source mismatch: %s.',n);
        end
    end
    % SHA of source.zip is saved and checked against the public run report.
    % Independent ZIP-entry byte readback remains a post-run acceptance gate.
end

function verify_installed(root,base,overlay)
    for i=1:numel(base)
        path=char(base(i).path);want=char(base(i).sha256);
        j=find(strcmp(path,{overlay.path}));if ~isempty(j),assert(numel(j)==1);want=char(overlay(j).target_sha256);end
        f=fullfile(root,strrep(path,'/',filesep));assert(isfile(f)&&strcmp(sha(f),want), ...
            'sar20OU:smokeSource','Installed file differs: %s.',path);
    end
    for i=1:numel(overlay)
        if strcmp(overlay(i).operation,'add')
            f=fullfile(root,strrep(char(overlay(i).path),'/',filesep));
            assert(isfile(f)&&strcmp(sha(f),char(overlay(i).target_sha256)), ...
                'sar20OU:smokeSource','Added file differs: %s.',char(overlay(i).path));
        end
    end
end
function verify_resolved(root,rows)
    for i=1:numel(rows)
        [~,n,e]=fileparts(char(rows(i).path));f=which(n);
        want=fullfile(root,strrep(char(rows(i).path),'/',filesep));
        assert(~isempty(f)&&strcmpi(canon(f),canon(want))&&strcmp(sha(f),char(rows(i).target_sha256)), ...
            'sar20OU:smokeWhich','%s resolves outside the intended installed source.',n);
    end
end

function [same,badField,reason]=strict_equal(a,b,field)
%STRICT_EQUAL Recursive field-set, MATLAB class/shape and numeric bit check.
% Real numeric arrays are compared as raw bytes (including signed zero/NaN
% payloads); complex numeric arrays compare real/imaginary byte streams. No
% unsupported sparse/object values are silently accepted.
    same=false;badField=field;reason='';
    if ~strcmp(class(a),class(b)),reason='class';return;end
    if ~isequal(size(a),size(b)),reason='shape';return;end
    if (isnumeric(a)||islogical(a))&&(issparse(a)||issparse(b)),reason='unsupported_sparse';return;end
    if isstruct(a)
        names=sort(fieldnames(a));other=sort(fieldnames(b));
        if ~isequal(names,other),reason='field_set';return;end
        for j=1:numel(a)
            for k=1:numel(names)
                n=names{k};child=sprintf('%s(%d).%s',field,j,n);
                [ok,badField,reason]=strict_equal(a(j).(n),b(j).(n),child);
                if ~ok,return;end
            end
        end
    elseif iscell(a)
        for j=1:numel(a)
            [ok,badField,reason]=strict_equal(a{j},b{j},sprintf('%s{%d}',field,j));
            if ~ok,return;end
        end
    elseif isnumeric(a)
        if issparse(a)||issparse(b),reason='unsupported_sparse';return;end
        if isreal(a)~=isreal(b),reason='real_complex_storage';return;end
        if isreal(a)
            sameBits=isequal(typecast(a(:),'uint8'),typecast(b(:),'uint8'));
        else
            sameBits=isequal(typecast(real(a(:)),'uint8'),typecast(real(b(:)),'uint8'))&& ...
                isequal(typecast(imag(a(:)),'uint8'),typecast(imag(b(:)),'uint8'));
        end
        if ~sameBits,reason='numeric_bits';return;end
    elseif islogical(a)||ischar(a)
        if ~isequal(a,b),reason='value';return;end
    elseif isstring(a)
        if ~isequaln(a,b),reason='string_value';return;end
    else
        reason='unsupported_class';return;
    end
    same=true;badField='';reason='';
end

function strict_equal_selftest()
% Exercise the required distinctions before any model/session mutation.
    a=struct();a.b=struct('q',[1 2]);a.a=single(3);
    b=struct();b.a=single(3);b.b=struct('q',[1 2]);
    assert(strict_equal(a,b,'self')&&strict_equal([],[],'self')&& ...
        strict_equal({[],{1}}, {[],{1}},'self')&& ...
        ~strict_equal(zeros(0,1),zeros(1,0),'self'),'sar20RA:strictTest','Field sets or empty/cell values failed.');
    minusZero=typecast(bitshift(uint64(1),63),'double');
    n1=typecast(bitor(bitshift(uint64(hex2dec('7FF80000')),32),uint64(1)),'double');
    n2=typecast(bitor(bitshift(uint64(hex2dec('7FF80000')),32),uint64(2)),'double');
    assert(strict_equal(n1,n1,'self')&&~strict_equal(n1,n2,'self')&& ...
        ~strict_equal(0,minusZero,'self')&&~strict_equal(single(1),double(1),'self')&& ...
        ~strict_equal(zeros(1,2),zeros(2,1),'self')&& ...
        ~strict_equal(sparse(logical(eye(2))),sparse(logical(eye(2))),'self')&& ...
        ~strict_equal(struct('a',1),struct('b',1),'self'), ...
        'sar20RA:strictTest','Class/shape/field/numeric-bit negative tests failed.');
end


function names=log_names()
    names={'adc_executed_log','adi_wire_log','aperture_log','az_commit_log','az_route_log', ...
      'back_log','bank_code_valid_log','bank_meta_log','cal_fit_log','cal_status_log','code_log', ...
      'control_log','d1_log','d2_log','dac_ra_pre_log','dt_log','event_log','frame_ready_log', ...
      'front_log','frozen_log','nominal_code_log','paired_ref_log','raw_log','ready_log', ...
      'record_log','record_ready_log','ref_queue_log','sample_ready_log','train_ref_log', ...
      'transport_frame_log','transport_pin_trace_log','transport_trace_rows_log'};
end
function assert_same_logs(a,b)
    names=log_names();
    for k=1:numel(names)
        x=a.get(names{k});y=b.get(names{k});
        assert(isa(x,'timeseries')&&isa(y,'timeseries')&&bits(x.Time,y.Time)&&bits(x.Data,y.Data), ...
            'sar20RA:logs','Time/Data differ for %s.',names{k});
    end
end
function assert_same_roots(a,b)
    x=a.get('yout');y=b.get('yout');
    assert(isa(x,'Simulink.SimulationData.Dataset')&&isa(y,'Simulink.SimulationData.Dataset')&& ...
        numElements(x)==3&&numElements(y)==3,'sar20RA:roots','Require 3 root outputs.');
    for k=1:3
        p=x.getElement(k);q=y.getElement(k);
        assert(isa(p.Values,'timeseries')&&isa(q.Values,'timeseries')&& ...
            bits(p.Values.Time,q.Values.Time)&&bits(p.Values.Data,q.Values.Data), ...
            'sar20RA:roots','Root %d differs.',k);
    end
end

function yes=bits(a,b)
    yes=strcmp(class(a),class(b))&&isequal(size(a),size(b))&&isreal(a)&&isreal(b);
    if ~yes,return;end
    if isa(a,'double'),yes=isequal(typecast(a(:),'uint64'),typecast(b(:),'uint64'));
    elseif islogical(a),yes=isequal(a,b);
    else,yes=isequal(typecast(a(:),'uint8'),typecast(b(:),'uint8'));end
end
function s=resolve_folder(s)
    f=java.io.File(char(s));if ~f.isAbsolute(),s=fullfile(pwd,char(s));end;s=canon(s);
end
function s=canon(s)
    s=char(java.io.File(char(s)).getCanonicalPath());
end
function yes=inside(child,parent)
    child=strrep(lower(char(child)),char(92),'/');parent=strrep(lower(char(parent)),char(92),'/');
    yes=strcmp(child,parent)||startsWith(child,[parent '/']);
end
function h=sha(p)
    fid=fopen(p,'rb');assert(fid>=0,'sar20OU:sha','Cannot open %s.',p);c=onCleanup(@()fclose(fid)); %#ok<NASGU>
    md=java.security.MessageDigest.getInstance('SHA-256');while ~feof(fid),md.update(fread(fid,1048576,'*uint8'));end
    h=lower(reshape(dec2hex(typecast(md.digest(),'uint8'),2).',1,[]));
end
