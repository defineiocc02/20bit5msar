function R=behavior_calibration_workflow(action,artifact)
%BEHAVIOR_CALIBRATION_WORKFLOW Explicit TRAIN -> FREEZE -> EVALUATE operations.
% Version v1.1 (2026-10-27): orchestration/evidence only, no ADC or fit algorithm.
% Public caller: SAR20('calibration',action[,project_relative_artifact]).
% train: one preregistered main2048 run, nominal output, Update-owned fit.
% freeze: lock one completed train candidate; no ADC run or holdout read.
% evaluate: one registered main1024 holdout using locked h; no refit or h write.
% Every operation gets a fresh evidence folder. Model/config restoration uses
% the ACTUAL starting P, not factory guesses. No model construction or algorithm copy.
    if nargin<2,artifact='';end
    assert((ischar(action)&&isrow(action))||(isstring(action)&&isscalar(action)), ...
        'calFlow:action','Action must be one scalar phase label.');action=char(action);
    assert(any(strcmp(action,{'train','freeze','evaluate'})),'calFlow:action','Use train, freeze, or evaluate.');
    root=canonical(fileparts(which('SAR20')));SAR20('setup');
    entry=which('SAR20','-all');if ischar(entry),entry=cellstr(entry);end
    assert(numel(entry)==1&&strcmp(canonical(entry{1}),canonical(fullfile(root,'SAR20.m'))), ...
        'calFlow:entry','Resolve one project SAR20.m; do not add archived source folders to path.');
    require_entry('make_training_case',fullfile(root,'config'));
    require_entry('make_training_protocol',fullfile(root,'config'));
    runDir=fullfile(root,'runs',['calibration_' action '_' char(java.util.UUID.randomUUID())]);mkdir(runDir);
    R=struct('schema','sar20-calibration-workflow/v1','action',action,'status','started', ...
        'workflow_path',relative(runDir,root),'accepted',false,'activation','none', ...
        'configuration_restored',true,'workflow_source_sha256',sha([mfilename('fullpath') '.m']));
    receiptFile=fullfile(runDir,'receipt.json');write_json(receiptFile,R);
    original=[];restoreNeeded=false;restored=true;
    cleanup=onCleanup(@restore_once); %#ok<NASGU>
    try
        switch action
            case 'train'
                assert(isempty(artifact),'calFlow:trainInput','Train does not accept a prior model, h, or holdout artifact.');
                original=starting_configuration();
                protocol=make_training_protocol();write_json(fullfile(runDir,'protocol.json'),protocol);
                R.protocol_sha256=sha(fullfile(runDir,'protocol.json'));
                provenance=['Declared ideal external calibrated source; registered protocol SHA256=' R.protocol_sha256];
                [q,p]=make_training_case(original,'train',provenance);
                assert(isequaln(p,protocol),'calFlow:protocol','Complete registered protocol differs.');
                q.frozen=struct('enabled',false,'cache',[]); % TRAIN output stays nominal
                restoreNeeded=true;restored=false;SAR20('apply',q);SAR20('check');
                beforeNames=run_names(root);R.stage='actual_training_run';write_json(receiptFile,R);
                run=SAR20('run');R.actual_run=relative(run.run_path,root);R.run_receipt=run;
                R.training_mat_sha256=sha(fullfile(run.run_path,'training.mat'));
                R.parameters_mat_sha256=sha(fullfile(run.run_path,'parameters.mat'));
                T=load(fullfile(run.run_path,'training.mat'),'training');T=T.training;
                assert(run.records==protocol.train.records&&T.rows==protocol.train.records&&T.fit_calls==1&& ...
                    ~T.accepted&&isempty(T.frozen),'calFlow:training','Incomplete or wrongly accepted training capture.');
                R.training=T;R.status='training_rejected';
                if T.ready_for_independent_holdout,R.status='training_candidate_ready_for_explicit_freeze';end
                R.protocol_file='protocol.json';
            case 'freeze'
                % Accept either this workflow's train folder OR one explicit
                % existing actual-run/protocol pair. Never synthesize a train receipt.
                if isstruct(artifact)
                    keys={'training_run';'registered_protocol'};
                    assert(isscalar(artifact)&&isequal(sort(fieldnames(artifact)),sort(keys)), ...
                        'calFlow:trainingArtifact','Existing-run input has exactly training_run and registered_protocol.');
                    trainDir=resolve_relative(root,artifact.training_run);
                    protocolFile=resolve_relative(root,artifact.registered_protocol);
                    previous='';train=[];importKind='existing_actual_run';
                else
                    previous=resolve_relative(root,artifact);train=read_json(fullfile(previous,'receipt.json'));
                    assert(is_workflow(train,'train')&& ...
                        strcmp(train.status,'training_candidate_ready_for_explicit_freeze'), ...
                        'calFlow:trainingArtifact','Use a completed workflow train candidate or explicit actual-run/protocol pair.');
                    trainDir=resolve_relative(root,train.actual_run);
                    protocolFile=fullfile(previous,'protocol.json');importKind='workflow_train';
                end
                summary=read_json(fullfile(trainDir,'summary.json'));
                assert(isstruct(summary)&&isscalar(summary)&&strcmp(summary.status,'complete')&& ...
                    summary.simulation_completed&&isfield(summary,'training'), ...
                    'calFlow:trainingArtifact','Actual run must contain completed native training.');
                copyfile(protocolFile,fullfile(runDir,'protocol.json'));
                protocolHash=sha(fullfile(runDir,'protocol.json'));protocol=read_json(fullfile(runDir,'protocol.json'));
                assert(strcmp(protocolHash,sha(protocolFile)),'calFlow:protocolHash','Registered protocol copy changed.');
                if ~isempty(train)
                    assert(strcmp(protocolHash,train.protocol_sha256)&& ...
                        strcmp(sha(fullfile(trainDir,'training.mat')),train.training_mat_sha256)&& ...
                        strcmp(sha(fullfile(trainDir,'parameters.mat')),train.parameters_mat_sha256), ...
                        'calFlow:trainingIdentity','Workflow training artifacts changed before locking.');
                end
                assert(strcmp(sha(fullfile(trainDir,'parameters.mat')),summary.config_sha256)&& ...
                    strcmp(sha(fullfile(trainDir,'SarAdc.slx')),summary.model_sha256)&& ...
                    strcmp(sha(fullfile(trainDir,'source.zip')),summary.source_zip_sha256)&& ...
                    strcmp(sha(fullfile(trainDir,'selected.mat')),summary.selected_sha256), ...
                    'calFlow:trainingIdentity','Actual training source/model/config/selected identity differs.');
                saved=load(fullfile(trainDir,'training.mat'),'training');T=saved.training;
                savedP=load(fullfile(trainDir,'parameters.mat'),'P');
                verify_training_registration(savedP.P,T,summary.training,protocol,protocolHash);
                assert(T.ready_for_independent_holdout&&T.rank==684&&T.condition_scaled<=1e8&& ...
                    T.training_rms_v<=7.8125e-6&&T.rows==2048&&T.fit_calls==1&& ...
                    strcmp(T.status,'training_candidate_requires_independent_holdout')&& ...
                    ~T.accepted&&isempty(T.frozen),'calFlow:freezeGate','Existing training candidate did not pass fixed gates.');
                require_entry('behavior_frozen_setup',fullfile(root,'current','src'));
                C=behavior_frozen_setup(T.public_config,T.h_candidate);
                assert(strcmp(C.lifecycle,'frozen_for_holdout')&&strcmp(C.acceptance,'NOT_ACCEPTED'), ...
                    'calFlow:lifecycle','Lock must remain NOT_ACCEPTED.');
                workflow='';if ~isempty(previous),workflow=relative(previous,root);end
                origin=struct('training_workflow',workflow,'training_import',importKind, ...
                    'registered_protocol',relative(protocolFile,root),'training_run',relative(trainDir,root), ...
                    'training_mat_sha256',sha(fullfile(trainDir,'training.mat')), ...
                    'model_sha256',sha(fullfile(trainDir,'SarAdc.slx')), ...
                    'parameters_mat_sha256',sha(fullfile(trainDir,'parameters.mat')), ...
                    'source_zip_sha256',sha(fullfile(trainDir,'source.zip')), ...
                    'protocol_sha256',protocolHash,'accepted',false,'activation','none');
                save(fullfile(runDir,'frozen_coefficients.mat'),'C','origin','-v7.3');
                R.status='locked_candidate_for_registered_holdout';R.origin=origin;
                R.protocol_sha256=origin.protocol_sha256;R.coefficient_sha256=C.coefficient_sha256;
                R.coefficient_file_sha256=sha(fullfile(runDir,'frozen_coefficients.mat'));
                R.public_cfg_sha256=C.public_cfg_sha256;R.holdout_read=false;
            case 'evaluate'
                previous=resolve_relative(root,artifact);lock=read_json(fullfile(previous,'receipt.json'));
                assert(is_workflow(lock,'freeze')&&strcmp(lock.status,'locked_candidate_for_registered_holdout')&& ...
                    ~lock.accepted,'calFlow:lock','Use an explicit locked candidate, not an unfitted/retuned h.');
                coeffFile=fullfile(previous,'frozen_coefficients.mat');
                assert(strcmp(sha(coeffFile),lock.coefficient_file_sha256),'calFlow:hHash','Locked coefficient artifact changed.');
                locked=load(coeffFile,'C','origin');C=locked.C;origin=locked.origin;
                assert(strcmp(C.coefficient_sha256,lock.coefficient_sha256)&& ...
                    strcmp(C.public_cfg_sha256,lock.public_cfg_sha256)&& ...
                    strcmp(C.schema,'sar20-public-frozen-cache/v2')&& ...
                    strcmp(C.lifecycle,'frozen_for_holdout')&&strcmp(C.acceptance,'NOT_ACCEPTED')&& ...
                    strcmp(origin.protocol_sha256,lock.protocol_sha256),'calFlow:lockIdentity','Locked h/cfg/lifecycle differs.');
                copyfile(fullfile(previous,'protocol.json'),fullfile(runDir,'protocol.json'));
                assert(strcmp(sha(fullfile(runDir,'protocol.json')),lock.protocol_sha256), ...
                    'calFlow:protocolHash','Locked holdout protocol changed.');
                protocol=read_json(fullfile(runDir,'protocol.json'));
                trainDir=resolve_relative(root,origin.training_run);
                assert(strcmp(sha(fullfile(trainDir,'training.mat')),origin.training_mat_sha256)&& ...
                    strcmp(sha(fullfile(trainDir,'parameters.mat')),origin.parameters_mat_sha256), ...
                    'calFlow:trainingIdentity','Training data/config identity changed after lock.');
                trainingP=load(fullfile(trainDir,'parameters.mat'),'P');
                original=starting_configuration();
                provenance=['Independent declared ideal external source; registered protocol SHA256=' lock.protocol_sha256];
                [q,p]=make_training_case(trainingP.P,'holdout',provenance);
                assert(isequaln(p,protocol),'calFlow:protocol','Complete registered holdout protocol differs.');
                q.frozen=struct('enabled',true,'cache',C);q=behavior_prepare_configuration(q);
                assert(~q.training.enabled&&q.training.reference.enabled&& ...
                    isequaln(q.cal_cfg.public_cfg,C.public_cfg),'calFlow:holdoutBoundary','Collect must be off; reference on; public cfg unchanged.');
                require_entry('behavior_holdout_result',fullfile(root,'current','src'));
                restoreNeeded=true;restored=false;SAR20('apply',q);SAR20('check');
                beforeNames=run_names(root);R.stage='actual_registered_holdout_run';write_json(receiptFile,R);
                run=SAR20('run');R.actual_run=relative(run.run_path,root);R.run_receipt=run;
                saved=load(fullfile(run.run_path,'parameters.mat'),'P');data=load(fullfile(run.run_path,'simout.mat'),'simout');
                [evaluation,holdout_data]=behavior_holdout_result(data.simout,saved.P.cal_cfg, ...
                    saved.P.training.reference,C,protocol.thresholds,saved.P);
                assert(strcmp(sha(coeffFile),lock.coefficient_file_sha256)&& ...
                    isequaln(saved.P.frozen.cache,C),'calFlow:immutable','h changed during holdout.');
                save(fullfile(runDir,'holdout.mat'),'evaluation','holdout_data','-v7.3');
                write_json(fullfile(runDir,'holdout.json'),evaluation);
                R.status=evaluation.status;R.evaluation=evaluation;
                R.evaluation_scope='Registered independent holdout only; not wider nonideal/transport or product acceptance';
                R.registered_holdout_passed=logical(evaluation.passed);
                R.accepted=false;R.locked_artifact=relative(previous,root);
                R.coefficient_sha256=lock.coefficient_sha256;R.coefficient_file_sha256=lock.coefficient_file_sha256;
                R.protocol_sha256=lock.protocol_sha256;R.refit=false;
                % C remains immutable NOT_ACCEPTED; this receipt records only
                % holdout validation. No coefficient bank is activated afterwards.
        end
        restore_once();R.configuration_restored=restored;
        R.stage='complete';write_json(receiptFile,R);
    catch cause
        R.status='failed';R.error=getReport(cause,'extended','hyperlinks','off');
        if exist('beforeNames','var')&&~isfield(R,'actual_run')
            fresh=setdiff(run_names(root),beforeNames);
            R.partial_runs=cellfun(@(n)['runs/' n],fresh,'UniformOutput',false);
        end
        try,restore_once();R.configuration_restored=restored;
        catch failure,R.configuration_restored=false;R.restore_error=failure.message;end
        write_json(receiptFile,R);rethrow(cause);
    end
    function P=starting_configuration()
        SAR20('open');model='SarAdc';
        assert(strcmp(get_param(model,'SimulationStatus'),'stopped')&&strcmp(get_param(model,'Dirty'),'off'), ...
            'calFlow:busy','Only a stopped saved target may run calibration experiments.');
        ws=get_param(model,'ModelWorkspace');P=getVariable(ws,'P');
        assert(isequaln(P.digital,getVariable(ws,'DecodeP')),'calFlow:startingP','Starting P/DecodeP differs; apply or save intentional edits first.');
        behavior_applied_note('check',model);
        save(fullfile(runDir,'starting_parameters.mat'),'P','-v7.3');
        R.starting_parameters_sha256=sha(fullfile(runDir,'starting_parameters.mat'));
    end
    function restore_once()
        if restoreNeeded
            restoreNeeded=false;SAR20('apply',original);
            restored=isequaln(original,getVariable(get_param('SarAdc','ModelWorkspace'),'P'));
            assert(restored,'calFlow:restore','Actual starting configuration was not restored.');
        end
    end
end
function p=resolve_relative(root,rel)
    assert((ischar(rel)&&isrow(rel))||(isstring(rel)&&isscalar(rel)), ...
        'calFlow:path','Supply a project-relative workflow artifact path.');
    rel=char(rel);assert(~isempty(rel)&&~java.io.File(rel).isAbsolute()&& ...
        isempty(regexp(rel,'^[A-Za-z]:','once')),'calFlow:path','Absolute artifact paths are not accepted.');
    p=canonical(fullfile(root,rel));a=p;b=root;if ispc,a=lower(a);b=lower(b);end
    assert(startsWith(a,[b filesep]), ...
        'calFlow:path','Artifact must stay inside this project.');
end
function require_entry(name,folder)
    p=which(name,'-all');if ischar(p),p=cellstr(p);end
    assert(numel(p)==1,'calFlow:source','%s must resolve uniquely.',name);
    a=canonical(p{1});b=canonical(folder);if ispc,a=lower(a);b=lower(b);end
    assert(startsWith(a,[b filesep]), ...
        'calFlow:source','%s must resolve uniquely inside its project source/config folder.',name);
end
function p=canonical(p),p=char(java.io.File(p).getCanonicalPath());end
function rel=relative(p,root)
    p=canonical(p);a=p;b=root;if ispc,a=lower(a);b=lower(b);end
    assert(startsWith(a,[b filesep]));rel=strrep(p(numel(root)+2:end),'\','/');
end
function names=run_names(root),d=dir(fullfile(root,'runs','behavior_*'));names={d.name};end
function s=read_json(file),s=jsondecode(fileread(file));end
function write_json(file,value)
    f=fopen(file,'w','n','UTF-8');assert(f>=0);c=onCleanup(@()fclose(f)); %#ok<NASGU>
    fprintf(f,'%s\n',jsonencode(value));
end
function value=sha(file)
    f=fopen(file,'rb');assert(f>=0);c=onCleanup(@()fclose(f)); %#ok<NASGU>
    md=java.security.MessageDigest.getInstance('SHA-256');md.update(fread(f,inf,'*uint8'));
    value=lower(reshape(dec2hex(typecast(md.digest(),'uint8'),2).',1,[]));
end

function ok=is_workflow(x,action)
    ok=isstruct(x)&&isscalar(x)&&isfield(x,'schema')&& ...
        strcmp(x.schema,'sar20-calibration-workflow/v1')&&isfield(x,'action')&&strcmp(x.action,action);
end
function verify_training_registration(P,T,S,protocol,protocolHash)
% v1.1 2026-10-27. Verify saved native data against the pre-existing registration;
% never call make_training_protocol here or regenerate a protocol after training.
    assert(isstruct(protocol)&&isscalar(protocol)&&strcmp(protocol.schema,'sar20-training-protocol/v1'), ...
        'calFlow:protocolType','Supply the original registered protocol file.');
    t=protocol.train;r=P.training.reference;
    tokens=regexp(char(r.provenance),'(?i)protocol SHA256=([0-9a-f]{64})','tokens');
    assert(numel(tokens)==1&&strcmpi(tokens{1}{1},protocolHash)&& ...
        strcmp(P.cal_cfg.reference_provenance,r.provenance)&& ...
        strcmp(T.reference_declaration.provenance,r.provenance), ...
        'calFlow:registeredProvenance','Protocol SHA is not the one committed in the actual pre-run reference declaration.');
    assert(P.N==t.records&&P.first_id==t.first_id&&P.epoch==t.epoch&& ...
        P.Ts_s==protocol.sample_period_s&&isequaln(P.input,t.source)&& ...
        P.training.enabled&&r.enabled&&strcmp(r.source,'declared_external_reference')&& ...
        r.records==t.records&&r.first_id==t.first_id&&r.epoch==t.epoch&& ...
        r.sample_period_s==protocol.sample_period_s,'calFlow:trainingProtocol','Saved training tags/source/window differ.');
    names=fieldnames(t.source);
    for k=1:numel(names),assert(isequaln(r.(names{k}),t.source.(names{k})),'calFlow:referenceSource','Reference source differs.');end
    assert(P.front.plan_rows==protocol.public_plan_rows&& ...
        size(P.front.plan,1)==protocol.public_plan_rows&& ...
        P.cal_cfg.public_cfg.plan_rows==protocol.public_plan_rows&& ...
        logical(P.front.dem_enabled)==logical(protocol.DEM)&& ...
        logical(P.front.dither_enabled)==logical(protocol.dither)&& ...
        isequaln(P.cal_cfg.public_cfg,T.public_config),'calFlow:publicConfig','Training public configuration differs.');
    names=fieldnames(P.cal_cfg.thresholds);
    for k=1:numel(names),assert(isequaln(P.cal_cfg.thresholds.(names{k}),protocol.thresholds.(names{k})),'calFlow:thresholds','Training thresholds differ.');end
    assert(strcmp(S.status,T.status)&&S.rows==T.rows&&S.fit_calls==T.fit_calls&&S.rank==T.rank&& ...
        S.condition_scaled==T.condition_scaled&&S.training_rms_v==T.training_rms_v&& ...
        isequal(double(S.h_candidate(:)),double(T.h_candidate(:))), ...
        'calFlow:nativeSnapshot','Training MAT differs from the actual run summary snapshot.');
end
