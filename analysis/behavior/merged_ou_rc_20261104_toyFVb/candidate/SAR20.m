function report=SAR20(action,varargin)
%SAR20 v2 — sole public entry for the editable behavioral Simulink project.
% SAR20 / SAR20('open'|'setup'|'apply'|'check'|'run')
% SAR20('apply',P) explicitly prepares/applies P; no-P apply uses adc_parameters.
% SAR20('sample',id[,runPath]) explains and plots one actual saved sample.
% SAR20('calibration','train'|'freeze'|'evaluate'[,artifact]) runs explicit phases.
% Root-relative current/models/SarAdc.slx, current/src and config/adc_parameters.m.
% apply derives parameters; run ALWAYS uses the saved model workspace P.
% SHA records identity; editing source/model does not require hash rebasing.
    if nargin==0||isempty(action),action='open';end
    action=lower(char(action));
    assert(ismember(action,{'setup','open','apply','check','run','sample','calibration'}), ...
        'SAR20:action','Unknown action.');
    if ~any(strcmp(action,{'apply','sample','calibration'}))
        assert(isempty(varargin),'SAR20:arguments','Only apply accepts an explicit configuration; run uses saved P.');
    end
    root=fileparts(mfilename('fullpath'));src=fullfile(root,'current','src');
    config=fullfile(root,'config');model='SarAdc';modelFile=fullfile(root,'current','models',[model '.slx']);
    assert(isfolder(src)&&isfolder(config),'SAR20:layout','Missing current/src or config.');
    % Remove only this project's retired runtime paths; preserve other work.
    oldPaths=strsplit(path,pathsep);
    for k=1:numel(oldPaths)
        item=oldPaths{k};
        if isempty(item),continue;end
        retired=under(item,fullfile(root,'current')) && ~under(item,src) && ~strcmpi(canon(item),canon(src));
        staging=startsWith(strrep(lower(item),'\','/'),'d:/temp/sar20behavior/') && ...
            ~startsWith(strrep(lower(root),'\','/'),'d:/temp/sar20behavior/');
        if retired||staging,rmpath(item);end
    end
    addpath(genpath(src),config,'-begin');
    report=struct('action',action,'status','setup_complete','project_root',root);
    if strcmp(action,'setup'),return;end
    if strcmp(action,'calibration')
        error('singleBank:calibrationUnavailable', ...
            'Single-bank calibration is not validated; do not freeze or apply legacy pool coefficients.');
    end
    if strcmp(action,'sample')
        assert(~isempty(varargin),'SAR20:sampleID','Use SAR20(''sample'',id[,runPath]).');
        id=varargin{1};assert(isscalar(id)&&isfinite(id)&&id>=0&&id==floor(id),'SAR20:sampleID','ID must be nonnegative integer.');
        if numel(varargin)>=2,runPath=char(varargin{2});else
            pointer=fullfile(root,'runs','latest_behavior_run.json');
            assert(isfile(pointer),'SAR20:noRun','No completed behavioral run has been recorded.');
            latest=jsondecode(fileread(pointer));runPath=latest.run_path;
        end
        runtime_entry('behavior_sample_plot',src);
        runtime_entry('behavior_sample_explain',src);
        runtime_entry('behavior_record_view',src);
        runtime_entry('behavior_sample_debug',src);
        files=behavior_sample_plot(runPath,id);
        files.explanation=behavior_sample_explain(runPath,id);
        report=struct('action','sample','status','sample_debug_created','run_path',runPath,'sample_id',id,'files',files);return;
    end
    assert(isfile(modelFile),'SAR20:model','Missing unique current/models/SarAdc.slx.');
    guard_model(model,modelFile);
    wasLoaded=bdIsLoaded(model);
    if strcmp(action,'open'),open_system(modelFile);report.status='model_opened';return;end
    if ~wasLoaded,load_system(modelFile);end
    cleanup=onCleanup(@()close_owned(model,wasLoaded)); %#ok<NASGU>
    ws=get_param(model,'ModelWorkspace');
    switch action
        case 'apply'
            assert(numel(varargin)<=1,'SAR20:arguments','Use apply or apply with one scalar P.');
            runtime_entry('behavior_prepare_configuration',src);
            runtime_entry('behavior_applied_note',src);
            if isempty(varargin)
                runtime_entry('adc_parameters',config);P=adc_parameters();source='factory';
            else
                P=varargin{1};source='explicit';
                assert(isstruct(P)&&isscalar(P),'SAR20:parameters','Explicit P must be a scalar struct.');
            end
            P=behavior_prepare_configuration(P);
            assert(isstruct(P)&&isscalar(P)&&isfield(P,'digital'),'SAR20:parameters','Prepared P must contain digital settings.');
            assignin(ws,'P',P);assignin(ws,'DecodeP',P.digital);
            assignin(ws,'TrainCaptureFile',''); % independent model default, never stored in P

            behavior_applied_note('update',model);
            save_system(model,modelFile,'SaveModelWorkspace',true);
            applied=struct('utc',utc_now(),'model_sha256',sha(modelFile),'configuration_source',source,'config',P);
            state=fullfile(root,'state');if ~isfolder(state),mkdir(state);end
            write_json(fullfile(state,'applied_config.json'),applied);
            report=struct('action','apply','status','parameters_applied','model_sha256',applied.model_sha256,'configuration_source',source);
        case 'check'
            P=getVariable(ws,'P'); %#ok<NASGU>
            set_param(model,'SimulationCommand','update');
            report=struct('action','check','status','actual_model_update_pass','model_sha256',sha(modelFile),'simulation_run',false);
        case 'run'
            P=getVariable(ws,'P');
            DecodeP=getVariable(ws,'DecodeP');
            assert(isequaln(DecodeP,P.digital)&& ...
                strcmp(P.backend.az.mode,P.digital.az_mode)&& ...
                P.backend.ni.az==~strcmp(P.backend.az.mode,'off')&& ...
                P.ni.az==P.backend.ni.az,'SAR20:modeJoin', ...
                'Saved analog, digital and coverage configurations differ; apply consistent parameters before running.');
            runtime_entry('behavior_applied_note',src);
            behavior_applied_note('check',model);
            runtime_entry('behavior_spectrum',src);
            report=run_saved(model,modelFile,P,root,src,config);
    end
end

function report=run_saved(model,modelFile,P,root,src,config)
    runPath=fullfile(root,'runs',['behavior_' char(java.util.UUID.randomUUID())]);mkdir(runPath);
    report=struct('action','run','status','started','utc',utc_now(),'run_path',runPath, ...
        'model_kind','behavioral','simulation_completed',false,'model_sha256',sha(modelFile), ...
        'capture_boundary','direct_raw');
    if isfield(P,'transport')&&isfield(P.transport,'enabled')&&P.transport.enabled
        report.capture_boundary='serial_rx';
    end
    report.decode_mode='nominal';
    if isfield(P,'frozen')&&P.frozen.enabled
        report.decode_mode='immutable_candidate_for_holdout';
        report.coefficient_sha256=P.frozen.cache.coefficient_sha256;
        report.calibration_accepted=false;
    elseif isfield(P,'bank')&&isstruct(P.bank)&&isfield(P.bank,'enabled')&&P.bank.enabled
        report.decode_mode='prequalified_dual_version_behavior_only';
        report.calibration_accepted=false;
        report.bank_scope='same-h prequalified behavior simulation; not product acceptance';
        report.bank_versions=double([P.bank.slots.version]);
        report.bank_coefficient_sha256=P.bank.slots(1).cache.coefficient_sha256;
    end
    file=fullfile(runPath,'summary.json');write_json(file,report);
    try
        save(fullfile(runPath,'parameters.mat'),'P','-v7.3');
        write_json(fullfile(runPath,'parameters.json'),P);
        report.config_sha256=sha(fullfile(runPath,'parameters.mat'));
        report.config_identity='parameters.mat preserves full resolved P; JSON is a readable projection';
        copyfile(modelFile,fullfile(runPath,'SarAdc.slx'));
        assert(strcmp(sha(fullfile(runPath,'SarAdc.slx')),report.model_sha256), ...
            'SAR20:snapshot','Copied model differs from the actual source.');
        report.source_files=snapshot_source(root,src,config,runPath);
        report.source_zip_sha256=sha(fullfile(runPath,'source.zip'));
        if isfield(P,'bank')&&isstruct(P.bank)&&isfield(P.bank,'enabled')&&P.bank.enabled
            bankQ=char(P.bank.qualification_file);bankQCopy=fullfile(runPath,'bank_qualification.json');
            assert(isfile(bankQ)&&copyfile(bankQ,bankQCopy),'SAR20:bankQualification','Cannot snapshot the applied Bank qualification.');
            report.bank_qualification_sha256=sha(bankQCopy);
            assert(strcmp(report.bank_qualification_sha256,'a9cfaaefed217e5f6d6e7e1a2faa5586e78dbf8f6808523a9c5185c19ab9778f'), ...
                'SAR20:bankQualification','Applied qualification differs from the fixed reviewed bytes.');
        end
        report.status='running';write_json(file,report);
        trainingRun=isfield(P,'cal_cfg')&&P.cal_cfg.enabled;
        committed=[];
        if trainingRun
            trainPath=actual_train_state_path(model);
            trainParams=get_param(trainPath,'Parameters');
            assert(strcmp(regexprep(trainParams,'\s',''),'P.cal_cfg,TrainCaptureFile'), ...
                'SAR20:trainCaptureParameters','Actual Train must use P.cal_cfg,TrainCaptureFile dialogs.');
            captureDefault=getVariable(get_param(model,'ModelWorkspace'),'TrainCaptureFile');
            assert(ischar(captureDefault)&&isempty(captureDefault), ...
                'SAR20:trainCaptureDefault','Saved ModelWorkspace TrainCaptureFile must be empty.');
            captureFile=fullfile(runPath,'training_committed.mat');
            assert(~isfile(captureFile)&&~isfolder(captureFile),'SAR20:trainCaptureExists','Refuse existing run capture path.');
            simInput=Simulink.SimulationInput(model);
            simInput=simInput.setVariable('TrainCaptureFile',captureFile,'Workspace',model);
            simInput=simInput.setModelParameter('ReturnWorkspaceOutputs','on','CaptureErrors','on');
            report.training_capture_variable='TrainCaptureFile';
            report.training_capture_workspace=model;
            report.training_capture_file='training_committed.mat';
            report.training_capture_saved_default='';
            report.training_capture_override_only=true;
            report.training_capture_parameters=trainParams;
            report.training_capture_verified=false;
            write_json(file,report);
        end
        rngBefore=rng;
        started=tic;
        if trainingRun
            simout=sim(simInput);
        else
            simout=sim(model,'ReturnWorkspaceOutputs','on','CaptureErrors','on');
        end
        report.elapsed_s=toc(started);
        report.global_rng_unchanged=isequal(rngBefore,rng);
        % Preserve actual simout before any capture read/validation, including
        % failed/stopped simulations. A Terminate file alone is not success.
        save(fullfile(runPath,'simout.mat'),'simout','-v7.3');
        if trainingRun
            report.training_capture_present=isfile(captureFile);
            if report.training_capture_present,report.training_capture_sha256=sha(captureFile);end
            report.training_capture_default_unchanged=isequal(captureDefault, ...
                getVariable(get_param(model,'ModelWorkspace'),'TrainCaptureFile'));
            report.training_capture_P_unchanged=isequaln(P,getVariable(get_param(model,'ModelWorkspace'),'P'));
            report.training_capture_SLX_unchanged=strcmp(report.model_sha256,sha(modelFile));
        end
        if isprop(simout,'ErrorMessage')&&~isempty(simout.ErrorMessage)
            error('SAR20:simulation','%s',simout.ErrorMessage);
        end
        if trainingRun
            assert(report.training_capture_default_unchanged&&report.training_capture_P_unchanged&& ...
                report.training_capture_SLX_unchanged,'SAR20:trainCaptureMutation','Capture override changed saved defaults/P/SLX.');
            assert(report.training_capture_present,'SAR20:trainCaptureMissing', ...
                'Training Terminate capture missing; Outputs/finalOP are not post-Update substitutes.');
            captured=load(captureFile,'committed');
            assert(isfield(captured,'committed'),'SAR20:trainCaptureVariable','Actual capture must contain committed.');
            committed=captured.committed;
            validate_train_capture(committed,simout,P,trainPath);
            report.training_capture_verified=true;
            report.training_capture_source=committed.source;
            report.training_capture_block=committed.block_path;
            report.training_capture_time_s=committed.time_s;
            report.training_capture_status7=committed.status7;
        end
        report.simulation_completed=true;
        if isfield(P,'bank')&&isstruct(P.bank)&&isfield(P.bank,'enabled')&&P.bank.enabled
            assert(strcmp(sha(bankQ),report.bank_qualification_sha256)&& ...
                strcmp(sha(bankQCopy),report.bank_qualification_sha256), ...
                'SAR20:bankQualification','Qualification changed during the actual run.');
        end
        runtime_entry('behavior_record_view',src);
        V=behavior_record_view(simout,P);
        runtime_entry('behavior_record_ready_summary',src);
        report.record_ready_summary=behavior_record_ready_summary(struct( ...
            'observed_raw',V.observed_raw,'raw',V.raw,'readiness_boundary',V.readiness_boundary));
        write_json(file,report); % retained even when selected validity later rejects
        [selected,metadata]=select_actual(simout,P,V);
        save(fullfile(runPath,'selected.mat'),'selected','metadata','-v7.3');
        report.records=numel(selected.code20);report.sample_ids=selected.raw(:,4).';
        report.raw_words=selected.raw;report.code20=selected.code20.';
        report.selected_sha256=sha(fullfile(runPath,'selected.mat'));
        if isfield(P,'cal_cfg')&&P.cal_cfg.enabled
            [training,public_training_data]=behavior_training_result(simout,P.cal_cfg,P.training.reference,committed,P);
            save(fullfile(runPath,'training.mat'),'training','public_training_data','-v7.3');
            write_json(fullfile(runPath,'training.json'),training);
            report.training=training;
        end
        if P.N>=256
            metrics=behavior_spectrum(selected.code20,metadata);
            save(fullfile(runPath,'spectrum.mat'),'metrics','-v7.3');
            report.spectrum_status=metrics.status;
            for field={'snr_db','sndr_db','sfdr_db','thd_db','enob'}
                if isfield(metrics,field{1}),report.(field{1})=metrics.(field{1});end
            end
        else,report.spectrum_status='not_run_short_capture';end
        report.status='complete';report.finished_utc=utc_now();write_json(file,report);
        write_json(fullfile(root,'runs','latest_behavior_run.json'),struct('run_path',runPath,'summary_sha256',sha(file)));
    catch cause
        if exist('started','var'),report.elapsed_s=toc(started);end
        report.partial_output_saved=isfile(fullfile(runPath,'simout.mat'));
        report.status='failed';report.error_identifier=cause.identifier;
        report.error=getReport(cause,'extended','hyperlinks','off');write_json(file,report);rethrow(cause);
    end
end

function [selected,metadata]=select_actual(simout,P,V)
% Actual public record boundary: bypass direct RAW or pin-only received RAW.
% V is the same public record view already summarized before selection. 
    r=V.raw;c=V.code20;t=V.time_s;
    assert(size(r,1)==P.N&&isequal(r(:,4),(P.first_id:P.first_id+P.N-1).')&& ...
        all(r(:,5)==P.epoch),'SAR20:records','Expected exactly N consecutive ready IDs with matching epoch.');
    assert(all(r(:,6)==1),'SAR20:invalid','Selected capture contains invalid RAW; keep simout and diagnose.');
    assert(all(isfinite(c)&c==floor(c)&c>=0&c<2^20),'SAR20:code','Code20 outside unsigned20 range.');
    selected=struct('raw',r,'code20',c,'time_s',t,'raw_fields',{{'D1','D2','DT','ID','epoch','valid'}});
    metadata=struct('fs_hz',P.fs_hz,'fsr_diff_v',P.fsr_diff_v,'stimulus',P.input);
    if isfield(P,'bank')&&isstruct(P.bank)&&isfield(P.bank,'enabled')&&P.bank.enabled
        runtime_entry('behavior_bank_record_gate',fullfile(fileparts(mfilename('fullpath')),'current','src'));
        runtime_entry('behavior_bank_validate_rows',fullfile(fileparts(mfilename('fullpath')),'current','src'));
        versions=double([P.bank.slots.version]);
        bank=behavior_bank_record_gate(simout,versions,struct('raw',r,'time_s',t));
        selected.bank_valid=bank.valid;selected.bank_slot=bank.slot;selected.bank_version=bank.version;
        metadata.bank_scope=bank.scope;
    end
end
function [x,t]=series(ts,width)
    assert(isa(ts,'timeseries'),'SAR20:logger','Expected native timeseries logger.');
    t=double(ts.Time(:));d=double(ts.Data);
    if ts.IsTimeFirst,x=reshape(d,numel(t),[]);else
        order=[ndims(d) 1:ndims(d)-1];x=reshape(permute(d,order),numel(t),[]);
    end
    assert(isequal(size(x),[numel(t) width]),'SAR20:loggerWidth','Unexpected logger width.');
end
function rows=snapshot_source(root,src,config,runPath)
    files=[dir(fullfile(src,'**','*.m'));dir(fullfile(config,'*.m'));dir(fullfile(config,'*.mat'))];
    names=cell(numel(files)+1,1);rows=struct('path',{},'sha256',{});
    for k=1:numel(files)
        path=fullfile(files(k).folder,files(k).name);names{k}=relative(path,root);
        rows(end+1)=struct('path',names{k},'sha256',sha(path)); %#ok<AGROW>
    end
    names{end}='SAR20.m';rows(end+1)=struct('path','SAR20.m','sha256',sha(fullfile(root,'SAR20.m')));
    zip(fullfile(runPath,'source.zip'),names,root);
    write_json(fullfile(runPath,'source_manifest.json'),struct('files',rows));
end
function guard_model(model,file)
    if ~bdIsLoaded(model),return;end
    assert(strcmpi(canon(get_param(model,'FileName')),canon(file)),'SAR20:sameName','A different same-name model is loaded.');
    assert(strcmp(get_param(model,'SimulationStatus'),'stopped'),'SAR20:busy','Target model is busy; finish its run first.');
    assert(strcmp(get_param(model,'Dirty'),'off'),'SAR20:dirty','Save or discard target model edits explicitly first.');
end
function close_owned(model,wasLoaded)
    if ~wasLoaded&&bdIsLoaded(model)&&strcmp(get_param(model,'SimulationStatus'),'stopped')
        close_system(model,0);
    end
end
function runtime_entry(name,folder)
    path=which(name);assert(~isempty(path)&&under(path,folder),'SAR20:runtimePath','%s resolves outside the current runtime.',name);
end
function tf=under(path,folder)
    path=canon(path);folder=canon(folder);tf=startsWith(lower(path),[lower(folder) filesep]);
end
function p=relative(path,root),p=char(extractAfter(string(path),strlength(string(root))+1));end
function p=canon(p),p=char(java.io.File(p).getCanonicalPath());end
function s=sha(path)
    fid=fopen(path,'rb');assert(fid>=0,'SAR20:read','Cannot read %s.',path);cleanup=onCleanup(@()fclose(fid)); %#ok<NASGU>
    md=java.security.MessageDigest.getInstance('SHA-256');
    while ~feof(fid),bytes=fread(fid,1024*1024,'*uint8');md.update(bytes);end
    s=lower(reshape(dec2hex(typecast(md.digest(),'uint8'),2).',1,[]));
end
function write_json(path,value)
    fid=fopen(path,'w','n','UTF-8');assert(fid>=0,'SAR20:write','Cannot write %s.',path);
    cleanup=onCleanup(@()fclose(fid)); %#ok<NASGU>
    fprintf(fid,'%s\n',jsonencode(value));
end
function s=utc_now(),s=char(datetime('now','TimeZone','UTC','Format','yyyy-MM-dd''T''HH:mm:ss.SSS''Z'''));end

function path=actual_train_state_path(model)
% SID resolved by Simulink to the real current name/path, never concatenated hierarchy.
    path=Simulink.ID.getFullName([model ':383']);
    assert(strcmp(bdroot(path),model)&&strcmp(get_param(path,'Name'),'Train')&& ...
        strcmp(get_param(path,'FunctionName'),'behavior_cal_train_sfun'), ...
        'SAR20:trainStateIdentity','SID383 must resolve to actual Train behavior_cal_train_sfun; inspect actual model_read after structural edits.');
end

function validate_train_capture(committed,simout,P,trainPath)
% Read-only postprocess: no fitting/commit/state mutation. Partial files remain.
    keys={'extracted';'status7';'snapshot2624';'raw_buffer';'reference_buffer';'time_s';'block_path';'source'};
    assert(isstruct(committed)&&isscalar(committed)&&isequal(sort(fieldnames(committed)),sort(keys))&& ...
        isequal(committed.extracted,true)&&strcmp(committed.source,'actual Terminate post-Update DWorks'), ...
        'SAR20:trainCaptureSchema','Require actual eight-field Terminate DWork capture.');
    assert(strcmp(committed.block_path,trainPath),'SAR20:trainCapturePath','Capture is not from actual Train block.');
    actualTout=simout.get('tout');
    assert(isnumeric(actualTout)&&isreal(actualTout)&&~isempty(actualTout)&& ...
        actualTout(end)==P.stop_time_s&&isscalar(committed.time_s)&& ...
        committed.time_s==actualTout(end),'SAR20:trainCaptureTime', ...
        'Actual simulation/capture did not reach the unchanged declared StopTime; a stopped/partial file is not success.');
    n=P.cal_cfg.N_train;
    assert(isa(committed.raw_buffer,'double')&&isequal(size(committed.raw_buffer),[n 6])&& ...
        isa(committed.reference_buffer,'double')&&isequal(size(committed.reference_buffer),[n 4])&& ...
        isa(committed.status7,'double')&&isequal(size(committed.status7),[7 1])&& ...
        isa(committed.snapshot2624,'double')&&isequal(size(committed.snapshot2624),[2624 1]), ...
        'SAR20:trainCaptureDimensions','Actual capture buffer/status/snapshot dimensions differ from saved N.');
    st=committed.status7;fit=committed.snapshot2624;
    assert(st(1)==1&&st(2)==n&&st(3)==1&&st(7)==0&& ...
        isequaln(st(1:5),fit(1:5))&&st(6)==fit(8)&&st(7)==fit(9), ...
        'SAR20:trainCaptureIncomplete','Actual Terminate capture must show N rows and exactly one fit; no acceptance claim.');
end
