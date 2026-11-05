function report=profile_normal_n8(projectRoot,p8File,sourceManifest,releaseReceipt,referenceSimout,outDir)
%PROFILE_NORMAL_N8 Profile one N8 sim of the installed normal single-bank model.
% Run ONLY in a fresh, private headless MATLAB worker after releaseN256 passes.
% Inputs: installed project root, archived e42 P_used.mat, pinned release
% SOURCE_MANIFEST.json, passed release_receipt.json, archived 2267 N8 simout.mat,
% and a NEW private output directory outside the project. All paths are explicit.
% The installed model is copied byte-for-byte, loaded privately, and receives P8
% and DecodeP through SimulationInput; no model/workspace/source is saved.
% Profile is enabled only around sim (plus its adjacent tic/toc); all hashing,
% setup, saves and reference comparison happen with profiling OFF.
%
% Outputs in outDir: profile_info.mat, simout.mat, actual_P.mat, SarAdc.slx,
% source_bindings.mat and report.{mat,json}. Raw profiler FunctionTable times
% are inclusive and overlap. Cold N8 and profiler overhead do not predict 20k
% runtime, and profiling does not time the later FFT or file post-processing.
    assert(nargin==6&&ispc&&~usejava('desktop')&&~bdIsLoaded('SarAdc'), ...
        'profileN8:session','Use six explicit paths and a fresh headless worker.');
    projectRoot=canon(projectRoot);p8File=canon(p8File);sourceManifest=canon(sourceManifest);
    releaseReceipt=canon(releaseReceipt);referenceSimout=canon(referenceSimout);outDir=canon(outDir);
    assert(isfolder(projectRoot)&&~isfile(outDir)&&~isfolder(outDir)&& ...
        ~same_path(outDir,projectRoot)&&~under(outDir,projectRoot), ...
        'profileN8:output','Output must be a new directory outside the installed project.');
    [ok,msg,id]=mkdir(outDir);assert(ok&&isempty(id),'profileN8:mkdir','%s',msg);
    report=struct('schema','sar20-profile-normal-n8/v1','status','started', ...
        'phase','preflight','pid',feature('getpid'),'matlab_version',version, ...
        'matlab_release',version('-release'),'project_root',projectRoot, ...
        'output_dir',outDir,'scope','cold profiled N8 sim only; no FFT or 20k extrapolation');
    try
        assert(strcmp(sha(p8File),'e42b739ed7c465845ed0e415a9f2fdfdd1afa0caaf0c18055c3f77fbfe683b61'), ...
            'profileN8:P8','Archived N8 P_used differs from the fixed e42 reference.');
        assert(strcmp(sha(referenceSimout),'2267e645ebc3000e1ad8e2ff56eec2f7c58d9205922cb9746c98b855792db705'), ...
            'profileN8:reference','Archived normal N8 simout differs from the fixed reference.');
        manifestSha=sha(sourceManifest);
        assert(strcmp(manifestSha,'082af93336b119850cec12af565609db0c3d00fdafaf8234f576a8e03c3c398d'), ...
            'profileN8:manifest','The 117-source release manifest differs.');
        manifest=jsondecode(fileread(sourceManifest));receipt=jsondecode(fileread(releaseReceipt));
        assert(strcmp(manifest.schema,'sar20-release-n256-sources/v1')&& ...
            manifest.source_count==117&&numel(manifest.sources)==117, ...
            'profileN8:manifest','Expected the exact 117-source release manifest.');
        assert(strcmp(receipt.status,'passed')&&receipt.factory_p_exact&& ...
            receipt.cold_p_exact&&receipt.output_exact&&receipt.global_rng_unchanged&& ...
            strcmp(receipt.simulation_status,'completed')&&isfield(receipt,'model_sha256'), ...
            'profileN8:release','The normal installed N256 release gate must already have passed.');
        resultFile=fullfile(fileparts(releaseReceipt),'release_result','report.mat');
        assert(strcmp(sha(resultFile),receipt.report_sha256),'profileN8:release','Release report SHA differs.');
        modelFile=fullfile(projectRoot,'current','models','SarAdc.slx');
        assert(strcmp(sha(modelFile),receipt.model_sha256),'profileN8:model','Installed model differs from passed release.');
        privateModel=fullfile(outDir,'SarAdc.slx');
        assert(copyfile(modelFile,privateModel)&&strcmp(sha(privateModel),receipt.model_sha256), ...
            'profileN8:copy','Private model copy differs.');
        q=load(p8File,'P');assert(isfield(q,'P'),'profileN8:P8','Missing archived P.');
        P8=q.P;
        assert(P8.N==8&&P8.Ts_s==200e-9&&P8.front.single_bank&&~P8.transport.enabled&& ...
            ~P8.front.dem_enabled&&~P8.front.dither_enabled&&~P8.front.jitter.enabled&& ...
            ~P8.training.enabled&&~P8.cal_cfg.enabled&&~P8.frozen.enabled&&~P8.bank.enabled&& ...
            P8.backend.ni.ra_noise&&P8.control.comparator.enabled, ...
            'profileN8:scope','Expected the actual normal single-bank N8 P.');

        % This path reset and all profiler operations affect the private worker
        % only. A matching project function already in memory is a hard stop.
        loaded=inmem('-completenames');stems=cell(1,0);
        for k=1:numel(manifest.sources)
            [~,name,ext]=fileparts(char(manifest.sources(k).path));
            if strcmpi(ext,'.m'),stems{end+1}=lower(name);end %#ok<AGROW>
        end
        for k=1:numel(loaded)
            [~,name]=fileparts(loaded{k});
            assert(~any(strcmp(lower(name),stems)),'profileN8:cache', ...
                'Project function %s is already cached; use a fresh worker.',name);
        end
        restoredefaultpath;rehash;cd(outDir);
        src=fullfile(projectRoot,'current','src');config=fullfile(projectRoot,'config');
        addpath(genpath(src),config,projectRoot,'-begin');rehash;
        sourceBefore=source_bindings(manifest,projectRoot);
        save(fullfile(outDir,'source_bindings_before.mat'),'sourceBefore','-v7.3');
        Simulink.fileGenControl('set','CacheFolder',fullfile(outDir,'cache'), ...
            'CodeGenFolder',fullfile(outDir,'codegen'),'keepPreviousPath',true,'createDir',true);
        fgc=Simulink.fileGenControl('getConfig');
        assert(under(fgc.CacheFolder,outDir)&&under(fgc.CodeGenFolder,outDir), ...
            'profileN8:filegen','Cache or codegen escaped the private directory.');
        load_system(privateModel);closer=onCleanup(@()close_private(privateModel)); %#ok<NASGU>
        assert(same_path(get_param('SarAdc','FileName'),privateModel), ...
            'profileN8:model','Loaded model is not the private byte-identical copy.');
        ws=get_param('SarAdc','ModelWorkspace');savedP=getVariable(ws,'P');
        savedDecode=getVariable(ws,'DecodeP');savedCapture=getVariable(ws,'TrainCaptureFile');
        assert(savedP.N==256&&same_bits(savedDecode,savedP.digital)&& ...
            ischar(savedCapture)&&isempty(savedCapture), ...
            'profileN8:default','Private copy must retain the installed N256 workspace.');
        diffs=diff_paths(P8,savedP,'P');
        allowed={'P.N','P.front.plan_rows','P.front.plan','P.n_cycles','P.stop_time_s', ...
            'P.schedule.n_cycles','P.schedule.stop_time_s','P.backend.dac_coupling.public_plan', ...
            'P.training.reference.records','P.cal_cfg.N_train','P.cal_cfg.public_cfg.plan_rows'};
        assert(all(ismember(diffs,allowed)), ...
            'profileN8:physicalJoin','N8 and installed N256 differ outside record/schedule fields.');
        assert(size(savedP.front.plan,1)>=size(P8.front.plan,1)&& ...
            same_bits(savedP.front.plan(1:size(P8.front.plan,1),:),P8.front.plan), ...
            'profileN8:plan','N8 public plan is not the prefix of installed N256.');
        save(fullfile(outDir,'actual_P.mat'),'P8','savedP','savedDecode','diffs','-v7.3');
        rngBefore=rng;
        si=Simulink.SimulationInput('SarAdc');
        si=si.setVariable('P',P8,'Workspace','SarAdc');
        si=si.setVariable('DecodeP',P8.digital,'Workspace','SarAdc');
        si=si.setVariable('TrainCaptureFile','','Workspace','SarAdc');
        si=si.setModelParameter('ReturnWorkspaceOutputs','on','CaptureErrors','on');
        report.phase='sim';report.p8_input_sha256=sha(p8File);
        report.reference_simout_sha256=sha(referenceSimout);
        report.installed_model_sha256=receipt.model_sha256;
        report.source_manifest_sha256=manifestSha;report.release_receipt_sha256=sha(releaseReceipt);
        report.source_count=117;report.default_workspace_N=double(savedP.N);
        report.parameter_differences=diffs;

        % Only sim and its immediately adjacent tic/toc are profiled.
        profilerStatusBefore=profile('status');
        assert(strcmp(profilerStatusBefore.ProfilerStatus,'off'), ...
            'profileN8:profilerState','Private worker profiler must be initially OFF.');
        profile('clear');profileCleanup=onCleanup(@()profile('off')); %#ok<NASGU>
        profile('on');timer=tic;
        try
            simout=sim(si);
            report.profiled_sim_wall_s=toc(timer);
        catch simError
            report.profiled_sim_wall_s=toc(timer);profile('off');
            profilerStatusAfter=profile('status');profileInfo=profile('info'); %#ok<NASGU>
            save(fullfile(outDir,'profile_info.mat'),'profileInfo','profilerStatusBefore','profilerStatusAfter','-v7.3');
            report.profile_info_sha256=sha(fullfile(outDir,'profile_info.mat'));
            rethrow(simError);
        end
        profile('off');profilerStatusAfter=profile('status');profileInfo=profile('info'); %#ok<NASGU>
        save(fullfile(outDir,'profile_info.mat'),'profileInfo','profilerStatusBefore','profilerStatusAfter','-v7.3');
        save(fullfile(outDir,'simout.mat'),'simout','-v7.3');
        report.profile_info_sha256=sha(fullfile(outDir,'profile_info.mat'));
        report.simout_sha256=sha(fullfile(outDir,'simout.mat'));
        report.actual_P_sha256=sha(fullfile(outDir,'actual_P.mat'));
        sourceAfter=source_bindings(manifest,projectRoot);
        save(fullfile(outDir,'source_bindings.mat'),'sourceBefore','sourceAfter','-v7.3');
        report.source_bindings_sha256=sha(fullfile(outDir,'source_bindings.mat'));
        report.model_and_default_workspace_unchanged= ...
            same_bits(getVariable(ws,'P'),savedP)&&same_bits(getVariable(ws,'DecodeP'),savedDecode)&& ...
            isequaln(getVariable(ws,'TrainCaptureFile'),savedCapture)&& ...
            strcmp(sha(modelFile),receipt.model_sha256)&&strcmp(sha(privateModel),receipt.model_sha256);
        report.global_rng_unchanged=isequaln(rngBefore,rng);
        report.phase='validate';
        assert(report.model_and_default_workspace_unchanged,'profileN8:unchanged', ...
            'Saved N256 workspace or either model file changed.');
        assert(report.global_rng_unchanged,'profileN8:rng','Global RNG changed during the sim.');
        assert(isa(simout,'Simulink.SimulationOutput')&&isempty(simout.ErrorMessage), ...
            'profileN8:sim','Simulation failed; raw output and profile remain saved.');
        [te,e]=series(simout.get('event_log'),2);[tr,raw]=series(simout.get('raw_log'),6);
        [ty,ready]=series(simout.get('ready_log'),1);
        G=numel(P8.groups);cycles=P8.n_cycles;
        assert(G==48&&cycles==12&&same_bits(te,tr)&&same_bits(te,ty)&& ...
            isequal(e,[repelem((0:cycles-1).',G) repmat((1:G).',cycles,1)])&& ...
            same_bits(te(end),P8.stop_time_s), ...
            'profileN8:events','Expected all twelve frames of the original 48-group N8 calendar.');
        assert(all(ismember(ready,[0 1]))&&nnz(ready)==cycles, ...
            'profileN8:ready','Expected one RAW-ready event per frame.');
        records=raw(logical(ready),:);selected=records(:,4)>=P8.first_id&records(:,4)<P8.first_id+P8.N;
        assert(isequal(records(:,4),(0:cycles-1).')&&all(records(:,5)==P8.epoch)&& ...
            all(records(:,6)==1)&&nnz(selected)==8&& ...
            isequal(records(selected,4),(P8.first_id:P8.first_id+7).'), ...
            'profileN8:records','Actual tags, validity, or selected N8 records differ.');
        reference=load(referenceSimout,'simout');old=reference.simout;
        assert(isa(old,'Simulink.SimulationOutput')&&isempty(old.ErrorMessage), ...
            'profileN8:reference','Reference output is not complete.');
        logs={'raw_log','ready_log','record_log','record_ready_log','event_log', ...
            'front_log','back_log','control_log','code_log'};
        assert(all(ismember([logs {'tout','yout'}],simout.who))&& ...
            all(ismember([logs {'tout','yout'}],old.who)), ...
            'profileN8:logs','Required log/root output missing.');
        for k=1:numel(logs),same_value(simout.get(logs{k}),old.get(logs{k}),logs{k});end
        same_value(simout.get('tout'),old.get('tout'),'tout');
        y=simout.get('yout');yref=old.get('yout');
        assert(isa(y,'Simulink.SimulationData.Dataset')&& ...
            isa(yref,'Simulink.SimulationData.Dataset')&&y.numElements==3&&yref.numElements==3, ...
            'profileN8:root','Expected three actual root outputs.');
        same_value(y,yref,'yout');
        report.actual_event_rows=numel(te);report.all_frame_count=cycles;report.selected_record_count=nnz(selected);
        report.reference_nine_logs_tout_yout_bit_equal=true;
        report.profiler_status_before=profilerStatusBefore;
        report.profiler_status_after=profilerStatusAfter;
        report.profiler_total_inclusive_not_additive=true;
        report.profiler_top_inclusive=top_functions(profileInfo,30);
        report.simulation_timing=timing_summary(simout);
        report.status='passed';report.phase='complete';
        save(fullfile(outDir,'report.mat'),'report','-v7.3');
        report.report_mat_sha256=sha(fullfile(outDir,'report.mat'));
        write_json(fullfile(outDir,'report.json'),report);
    catch err
        report.status='failed';report.error_id=err.identifier;
        report.error=getReport(err,'extended','hyperlinks','off');
        try,write_json(fullfile(outDir,'failed.json'),report);catch nested
            fprintf(2,'%s\n',getReport(nested,'extended','hyperlinks','off'));
        end
        rethrow(err);
    end
end

function rows=source_bindings(manifest,root)
    rows=struct('path',{},'sha256',{},'which',{});seen=cell(1,0);
    for k=1:numel(manifest.sources)
        item=manifest.sources(k);rel=char(item.path);
        assert(~startsWith(rel,'/')&&~contains(rel,'\')&& ...
            isempty(regexp(rel,'(^|/)\.\.(/|$)','once'))&&~any(strcmp(rel,seen)), ...
            'profileN8:sourcePath','Unsafe or duplicate source path.');
        seen{end+1}=rel;f=fullfile(root,strrep(rel,'/',filesep)); %#ok<AGROW>
        assert(under(f,root)&&strcmp(sha(f),char(item.after_sha256)), ...
            'profileN8:sourceHash','Installed source differs: %s.',rel);
        [~,name,ext]=fileparts(f);w='';
        if strcmpi(ext,'.m')
            w=which(name);assert(~isempty(w)&&same_path(w,f), ...
                'profileN8:sourcePath','%s resolves outside the installed source.',name);
        end
        rows(end+1)=struct('path',rel,'sha256',char(item.after_sha256),'which',w); %#ok<AGROW>
    end
    assert(numel(rows)==117,'profileN8:sourceCount','Expected exactly 117 source entries.');
end
function top=top_functions(info,n)
    assert(isstruct(info)&&isfield(info,'FunctionTable')&&~isempty(info.FunctionTable), ...
        'profileN8:profiler','Profiler returned no function data.');
    f=info.FunctionTable;[~,order]=sort([f.TotalTime],'descend');order=order(1:min(n,numel(order)));
    top=struct('name',{},'file',{},'calls',{},'inclusive_seconds',{},'partial_data',{});
    for k=1:numel(order)
        x=f(order(k));partial=[];
        if isfield(x,'PartialData'),partial=logical(x.PartialData);end
        top(end+1)=struct('name',x.FunctionName,'file',x.FileName, ...
            'calls',double(x.NumCalls),'inclusive_seconds',double(x.TotalTime), ...
            'partial_data',partial); %#ok<AGROW>
    end
end
function out=timing_summary(simout)
    out=struct('status','unavailable','fields',struct(),'error','');
    try
        t=simout.SimulationMetadata.TimingInfo;
        keys={'InitializationElapsedWallTime','ExecutionElapsedWallTime', ...
            'TerminationElapsedWallTime','TotalElapsedWallTime'};
        for k=1:numel(keys)
            name=keys{k};exists=(isstruct(t)&&isfield(t,name))||(isobject(t)&&isprop(t,name));
            if exists
                v=t.(name);if isnumeric(v)&&isscalar(v)&&isfinite(v),out.fields.(name)=double(v);end
            end
        end
        if ~isempty(fieldnames(out.fields)),out.status='available';end
    catch err
        out.error=[err.identifier ': ' err.message];
    end
end
function [t,x]=series(s,width)
    assert(isa(s,'timeseries')&&isnumeric(s.Time)&&isnumeric(s.Data), ...
        'profileN8:series','Expected numeric timeseries.');
    t=s.Time(:);d=s.Data;
    if s.IsTimeFirst,x=reshape(d,numel(t),[]);
    else,x=reshape(permute(d,[ndims(d) 1:ndims(d)-1]),numel(t),[]);end
    assert(isequal(size(x),[numel(t),width])&&all(isfinite(t)), ...
        'profileN8:series','Unexpected timeseries width or times.');
end
function out=diff_paths(a,b,prefix)
    if same_bits(a,b),out={};return;end
    if isstruct(a)&&isscalar(a)&&isstruct(b)&&isscalar(b)
        ak=fieldnames(a);bk=fieldnames(b);
        if isequal(sort(ak),sort(bk))&&~isequal(ak,bk),out={prefix};return;end
        keys=union(ak,bk);out={};
        for k=1:numel(keys)
            key=keys{k};where=[prefix '.' key];
            if ~isfield(a,key)||~isfield(b,key),out{end+1}=where; %#ok<AGROW>
            else,out=[out diff_paths(a.(key),b.(key),where)];end %#ok<AGROW>
        end
    else,out={prefix};end
end
function yes=same_bits(a,b)
    yes=strcmp(class(a),class(b))&&isequal(size(a),size(b));if ~yes,return;end
    if isstruct(a)
        names=fieldnames(a);yes=isequal(names,fieldnames(b));if ~yes,return;end
        for i=1:numel(a),for k=1:numel(names)
            if ~same_bits(a(i).(names{k}),b(i).(names{k})),yes=false;return;end
        end,end
    elseif iscell(a)
        for i=1:numel(a),if ~same_bits(a{i},b{i}),yes=false;return;end,end
    elseif isa(a,'double')||isa(a,'single')
        if ~isreal(a)||~isreal(b),yes=same_bits(real(a),real(b))&&same_bits(imag(a),imag(b));return;end
        kind='uint64';if isa(a,'single'),kind='uint32';end
        yes=isequal(typecast(a(:),kind),typecast(b(:),kind));
    elseif isnumeric(a)||islogical(a)||ischar(a)||isstring(a),yes=isequaln(a,b);
    else,error('profileN8:type','Unsupported equality class %s.',class(a));end
end
function same_value(a,b,where)
    assert(strcmp(class(a),class(b))&&isequal(size(a),size(b)), ...
        'profileN8:logType','Class or shape differs: %s.',where);
    if isa(a,'timeseries')
        assert(a.IsTimeFirst==b.IsTimeFirst,'profileN8:timeFirst','Time orientation differs: %s.',where);
        same_value(a.Time,b.Time,[where '.Time']);same_value(a.Data,b.Data,[where '.Data']);
    elseif isa(a,'Simulink.SimulationData.Dataset')
        assert(a.numElements==b.numElements,'profileN8:dataset','Root element count differs.');
        for j=1:a.numElements
            x=a.getElement(j);y=b.getElement(j);
            assert(strcmp(class(x),class(y))&&isprop(x,'Name')&&isprop(x,'Values')&& ...
                isequal(x.Name,y.Name),'profileN8:signal','Root signal differs: %s.',where);
            same_value(x.Values,y.Values,sprintf('%s[%d]',where,j));
        end
    elseif isnumeric(a)
        assert(isreal(a)==isreal(b)&& ...
            isequal(typecast(real(a(:)),'uint8'),typecast(real(b(:)),'uint8')), ...
            'profileN8:bits','Real data bits differ: %s.',where);
        if ~isreal(a),assert(isequal(typecast(imag(a(:)),'uint8'),typecast(imag(b(:)),'uint8')), ...
                'profileN8:bits','Imaginary data bits differ: %s.',where);end
    elseif islogical(a)||ischar(a)||isstring(a)
        assert(isequaln(a,b),'profileN8:value','Value differs: %s.',where);
    else,error('profileN8:logType','Unsupported output class %s at %s.',class(a),where);end
end
function close_private(file)
    if bdIsLoaded('SarAdc')&&same_path(get_param('SarAdc','FileName'),file)&& ...
            strcmp(get_param('SarAdc','SimulationStatus'),'stopped'),close_system('SarAdc',0);end
end
function p=canon(p),p=char(java.io.File(char(p)).getCanonicalPath());end
function yes=same_path(a,b),yes=strcmpi(canon(a),canon(b));end
function yes=under(p,r),yes=startsWith(lower(canon(p)),[lower(canon(r)) filesep]);end
function h=sha(file)
    d=dir(file);assert(isscalar(d)&&~d.isdir&&d.bytes<300e6,'profileN8:size','Missing or oversized: %s.',file);
    f=fopen(file,'rb');assert(f>=0,'profileN8:read','Cannot read: %s.',file);c=onCleanup(@()fclose(f)); %#ok<NASGU>
    b=fread(f,Inf,'*uint8');md=java.security.MessageDigest.getInstance('SHA-256');
    md.update(typecast(b(:),'int8'));h=lower(reshape(dec2hex(typecast(md.digest(),'uint8'),2).',1,[]));
end
function write_json(file,value)
    assert(~isfile(file)&&~isfolder(file),'profileN8:exists','Refuse to overwrite receipt.');
    f=fopen(file,'w','n','UTF-8');assert(f>=0,'profileN8:write','Cannot write receipt.');c=onCleanup(@()fclose(f)); %#ok<NASGU>
    fprintf(f,'%s\n',jsonencode(value));
end
