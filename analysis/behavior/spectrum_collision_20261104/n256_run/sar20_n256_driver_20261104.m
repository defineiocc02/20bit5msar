function sar20_n256_driver_20261104
% Run the current main model with an archived, complete N256 configuration.
% SimulationInput overrides P/DecodeP only for this simulation: no apply/save.
    job='D:/Temp/SAR20N256_20261104_qfhxXr';
    root='D:/Academic/Projects/sar20m1/SAR20';
    hist=fullfile(root,'runs','behavior_9058b834-83be-4415-946c-7f3b3ef8c7eb');
    sourceRun=fullfile(root,'runs','behavior_0a3cc913-8a98-44f9-86c6-cf2ada1c9932');
    model='SarAdc';modelFile=fullfile(root,'current','models',[model '.slx']);
    pathBefore=path;rngBefore=rng;pathGuard=onCleanup(@()path(pathBefore)); %#ok<NASGU>
    wasLoaded=bdIsLoaded(model);didLoad=false;
    for name={'matlab_receipt.json','receipt_events.jsonl','parameters.mat','SarAdc.slx', ...
            'source_manifest.json','source.zip','simout.mat','selected.mat','spectrum.mat'}
        assert(~isfile(fullfile(job,name{1})),'SAR20N256:existingOutput', ...
            'Refuse to overwrite prior evidence: %s.',name{1});
    end
    assert(~isfolder(fullfile(job,'reference')),'SAR20N256:existingOutput', ...
        'Refuse to reuse an existing reference directory.');
    result=struct('status','started','stage','preflight','pid',feature('getpid'));
    try
        assert(result.pid==27628,'SAR20N256:pid','Unexpected MATLAB process.');
        write_receipt(job,result);
        systems=find_system('SearchDepth',0,'Type','block_diagram');
        for k=1:numel(systems)
            name=systems{k};if bdIsLibrary(name),continue;end
            assert(strcmp(get_param(name,'SimulationStatus'),'stopped'), ...
                'SAR20N256:busy','Model %s is not stopped.',name);
        end
        sourceManifest=fullfile(sourceRun,'source_manifest.json');
        assert(strcmp(sha(sourceManifest),'3a1ad6ffc97fc96709d4aa70eb2d64f55f939bb1f5e14209b65e6e4d7fb70f22'), ...
            'SAR20N256:manifestIdentity','N8 source manifest is not the recorded one.');
        assert_sources(root,sourceManifest);
        modelHash=sha(modelFile);
        assert(strcmp(modelHash,'d4e7fc99ab040857e535df07d73447e71c65e7d51dcadf7b17f4bad88594a6a0'), ...
            'SAR20N256:model','Current model changed after N8 baseline.');
        addpath(root,genpath(fullfile(root,'current','src')),fullfile(root,'config'),'-begin');
        result.stage='source_resolution';
        result.source_resolution=check_resolution(root,sourceManifest);write_receipt(job,result);
        if ~wasLoaded
            assert(~bdIsLoaded(model),'SAR20N256:modelRace','The model was opened by another actor.');
            load_system(modelFile);didLoad=true;
            modelGuard=onCleanup(@()close_ours(model,true)); %#ok<NASGU>
        end
        assert(strcmpi(strrep(get_param(model,'FileName'),'\','/'),strrep(modelFile,'\','/'))&& ...
            strcmp(get_param(model,'SimulationStatus'),'stopped')&&strcmp(get_param(model,'Dirty'),'off'), ...
            'SAR20N256:modelState','Current model is not the expected clean stopped model.');
        result.source_resolution_after_load=check_resolution(root,sourceManifest);
        ws=get_param(model,'ModelWorkspace');savedP=getVariable(ws,'P');savedDecode=getVariable(ws,'DecodeP');
        reference=fullfile(job,'reference');assert(~isfolder(reference),'SAR20N256:reference','Reference directory exists.');
        mkdir(reference);
        for filename={'parameters.mat','selected.mat','spectrum.mat','summary.json'}
            src=fullfile(hist,filename{1});dst=fullfile(reference,filename{1});
            originalHash=sha(src);[ok,msg]=copyfile(src,dst);assert(ok,'SAR20N256:copy','%s',msg);
            assert(strcmp(sha(dst),originalHash)&&strcmp(sha(src),originalHash), ...
                'SAR20N256:reference','Historical reference copy changed: %s.',filename{1});
        end
        historicalSummary=jsondecode(fileread(fullfile(reference,'summary.json')));
        assert(strcmp(historicalSummary.status,'complete')&&historicalSummary.simulation_completed&& ...
            strcmp(sha(fullfile(reference,'parameters.mat')),historicalSummary.config_sha256)&& ...
            strcmp(sha(fullfile(reference,'selected.mat')),historicalSummary.selected_sha256), ...
            'SAR20N256:historicalIdentity','Archived P or selected data differ from their run receipt.');
        historical=load(fullfile(reference,'parameters.mat'),'P');P=historical.P;
        old=load(fullfile(reference,'selected.mat'),'selected','metadata');
        oldMetrics=load(fullfile(reference,'spectrum.mat'),'metrics');
        assert(P.N==256&&P.fs_hz==5e6&&P.first_id==4&&P.transport.enabled, ...
            'SAR20N256:configuration','Unexpected archived test configuration.');
        assert(strcmpi(strrep(which('behavior_spectrum'),'\','/'), ...
            strrep(fullfile(root,'current','src','analysis','behavior_spectrum.m'),'\','/')), ...
            'SAR20N256:resolution','Spectrum function resolves outside the project.');
        save(fullfile(job,'parameters.mat'),'P','-v7.3');
        [ok,msg]=copyfile(modelFile,fullfile(job,'SarAdc.slx'));assert(ok,'SAR20N256:copy','%s',msg);
        [ok,msg]=copyfile(sourceManifest,fullfile(job,'source_manifest.json'));assert(ok,'SAR20N256:copy','%s',msg);
        sourceZip=fullfile(sourceRun,'source.zip');sourceZipHash=sha(sourceZip);
        n8=jsondecode(fileread(fullfile(sourceRun,'summary.json')));
        assert(isfield(n8,'source_zip_sha256')&&strcmp(sourceZipHash,n8.source_zip_sha256)&& ...
            strcmp(sourceZipHash,'5e28ead4b7f73bba3e77cb43b40606a8abff750fdcb81eaf19539ccfee6af37e'), ...
            'SAR20N256:sourceZip','N8 source archive differs from its own receipt.');
        [ok,msg]=copyfile(sourceZip,fullfile(job,'source.zip'));assert(ok,'SAR20N256:copy','%s',msg);
        assert(strcmp(sha(fullfile(job,'source.zip')),sourceZipHash), ...
            'SAR20N256:sourceZip','Source archive copy changed.');
        assert(strcmp(sha(fullfile(job,'SarAdc.slx')),modelHash), ...
            'SAR20N256:snapshot','Model snapshot mismatch.');
        result.stage='simulation_running';result.model_sha256=modelHash;
        result.historical_parameters_sha256=sha(fullfile(reference,'parameters.mat'));
        result.historical_selected_sha256=sha(fullfile(reference,'selected.mat'));
        result.historical_spectrum_sha256=sha(fullfile(reference,'spectrum.mat'));
        result.source_manifest_sha256=sha(sourceManifest);write_receipt(job,result);
        input=Simulink.SimulationInput(model);
        input=input.setVariable('P',P,'Workspace',model);
        input=input.setVariable('DecodeP',P.digital,'Workspace',model);
        input=input.setModelParameter('ReturnWorkspaceOutputs','on','CaptureErrors','on');
        started=tic;simout=sim(input);result.elapsed_s=toc(started);
        save(fullfile(job,'simout.mat'),'simout','-v7.3');
        assert(isempty(simout.ErrorMessage),'SAR20N256:simError','Simulink error: %s',simout.ErrorMessage);
        result.stage='simulation_returned';result.simout_sha256=sha(fullfile(job,'simout.mat'));
        result.simulation_completed=true;
        write_receipt(job,result);
        V=behavior_record_view(simout,P);
        eventSeries=simout.get('event_log');
        assert(isa(eventSeries,'timeseries')&&~isempty(eventSeries.Time), ...
            'SAR20N256:events','Expected actual event-log timestamps.');
        result.last_event_s=double(eventSeries.Time(end));result.requested_stop_s=P.stop_time_s;
        assert(abs(result.last_event_s-P.stop_time_s)<=16*eps(max(abs(P.stop_time_s),1e-9)), ...
            'SAR20N256:stopTime','Event stream does not reach the requested final event.');
        assert(size(V.raw,1)==256&&isequal(V.raw(:,4),(4:259).')&& ...
            all(V.raw(:,5)==P.epoch)&&all(V.raw(:,6)==1), ...
            'SAR20N256:records','Expected 256 valid IDs 4..259 of the same epoch.');
        selected=struct('raw',V.raw,'code20',V.code20,'time_s',V.time_s);
        metadata=struct('fs_hz',P.fs_hz,'fsr_diff_v',P.fsr_diff_v,'stimulus',P.input);
        metrics=behavior_spectrum(selected.code20,metadata);
        save(fullfile(job,'selected.mat'),'selected','metadata','-v7.3');
        save(fullfile(job,'spectrum.mat'),'metrics','-v7.3');
        result.selected_sha256=sha(fullfile(job,'selected.mat'));
        result.spectrum_sha256=sha(fullfile(job,'spectrum.mat'));
        result.records=256;result.valid_records=sum(V.raw(:,6)==1);
        result.raw_identical=bits_equal(V.raw,old.selected.raw);
        result.code_identical=bits_equal(V.code20,old.selected.code20);
        result.time_identical=bits_equal(V.time_s,old.selected.time_s);
        result.spectrum_equal_isequaln=isequaln(metrics,oldMetrics.metrics);
        result.comparison_scope='Archived selected data and metrics; historic and current SLX/source identities differ.';
        if result.raw_identical&&result.code_identical&&result.time_identical&&result.spectrum_equal_isequaln
            result.validation_status='matched_archived_selection';
        else
            result.validation_status='difference_requires_analysis';
        end
        result.spectrum_status=metrics.status;
        assert(strcmp(metrics.status,'actual_codes_characterized'),'SAR20N256:spectrum','Expected characterized bin5 spectrum.');
        for field={'snr_db','sndr_db','sfdr_db','thd_db','enob'}
            if isfield(metrics,field{1}),result.(field{1})=metrics.(field{1});end
        end
        assert_sources(root,sourceManifest);
        result.source_resolution_after_sim=check_resolution(root,sourceManifest);
        assert(strcmp(sha(modelFile),modelHash)&&isequaln(savedP,getVariable(ws,'P'))&& ...
            isequaln(savedDecode,getVariable(ws,'DecodeP'))&& ...
            strcmp(get_param(model,'Dirty'),'off')&&strcmp(get_param(model,'SimulationStatus'),'stopped'), ...
            'SAR20N256:modelChanged','Saved model or its workspace changed during the run.');
        assert(isequaln(rngBefore,rng),'SAR20N256:rng','MATLAB global RNG changed.');
        result.model_P_and_DecodeP_unchanged=true;result.rng_unchanged=true;
        close_ours(model,didLoad);
        if didLoad,assert(~bdIsLoaded(model),'SAR20N256:close','Task-owned clean model did not close.');end
        if didLoad,clear modelGuard;didLoad=false;end
        path(pathBefore);assert(strcmp(path,pathBefore),'SAR20N256:path','MATLAB path did not restore.');
        result.path_restored=true;result.original_model_was_loaded=wasLoaded;
        result.status='completed';result.stage='complete';
        write_receipt(job,result);
    catch cause
        result.status='failed';result.error_id=cause.identifier;
        result.error=getReport(cause,'extended','hyperlinks','off');
        result.rng_unchanged=isequaln(rngBefore,rng);
        try
            close_ours(model,didLoad);
            if didLoad,clear modelGuard;didLoad=false;end
            path(pathBefore);
            result.failure_path_restored=strcmp(path,pathBefore);
            result.failure_model_loaded=bdIsLoaded(model);
        catch cleanupCause
            result.cleanup_error=getReport(cleanupCause,'extended','hyperlinks','off');
        end
        write_receipt(job,result);rethrow(cause)
    end
end

function info=check_resolution(root,manifest)
    names={'behavior_frontend_sfun','behavior_frontend_stage','behavior_frontend_step', ...
        'behavior_backend_sfun','behavior_backend_stage','behavior_backend_step', ...
        'behavior_control_stage_sfun','behavior_control_stage','behavior_sar_step', ...
        'behavior_event_source','behavior_record_view','behavior_spectrum'};
    data=jsondecode(fileread(manifest));loaded=inmem('-completenames');
    info=struct('name',{},'primary',{},'all_paths',{},'cached_paths',{});
    for i=1:numel(names)
        name=names{i};match={};
        for j=1:numel(data.files)
            [~,stem,ext]=fileparts(char(data.files(j).path));
            if strcmpi(stem,name)&&strcmpi(ext,'.m'),match{end+1}=fullfile(root,char(data.files(j).path));end %#ok<AGROW>
        end
        assert(numel(match)==1,'SAR20N256:resolution','Manifest lacks unique %s.',name);
        expected=strrep(match{1},'\','/');actual=which(name);
        assert(strcmpi(strrep(actual,'\','/'),expected),'SAR20N256:resolution', ...
            '%s resolves to %s instead of %s.',name,actual,expected);
        cache={};
        for j=1:numel(loaded)
            [~,stem]=fileparts(loaded{j});
            if strcmpi(stem,name)
                cache{end+1}=loaded{j}; %#ok<AGROW>
                assert(strcmpi(strrep(loaded{j},'\','/'),expected), ...
                    'SAR20N256:cache','%s is cached from another path: %s.',name,loaded{j});
            end
        end
        info(end+1)=struct('name',name,'primary',actual,'all_paths',{which(name,'-all')},'cached_paths',{cache}); %#ok<AGROW>
    end
end

function yes=bits_equal(a,b)
    yes=strcmp(class(a),class(b))&&isequal(size(a),size(b))&&isnumeric(a)&&isreal(a)&&isreal(b);
    if yes,yes=isequal(typecast(a(:),'uint8'),typecast(b(:),'uint8'));end
end

function assert_sources(root,manifest)
    data=jsondecode(fileread(manifest));
    assert(isstruct(data)&&isfield(data,'files')&&~isempty(data.files), ...
        'SAR20N256:manifest','Missing as-run source list.');
    for k=1:numel(data.files)
        item=data.files(k);file=fullfile(root,char(item.path));
        assert(isfile(file)&&strcmp(sha(file),char(item.sha256)), ...
            'SAR20N256:source','Current source differs from N8 archive: %s.',file);
    end
end

function h=sha(file)
    f=fopen(file,'rb');assert(f>=0,'SAR20N256:file','Cannot read %s.',file);
    c=onCleanup(@()fclose(f)); %#ok<NASGU>
    d=dir(file);assert(isscalar(d)&&d.bytes<=300e6,'SAR20N256:largeFile','File exceeds the read limit.');
    bytes=fread(f,Inf,'*uint8');md=java.security.MessageDigest.getInstance('SHA-256');
    md.update(typecast(bytes(:),'int8'));h=lower(reshape(dec2hex(typecast(md.digest(),'uint8'),2).',1,[]));
end

function close_ours(model,didLoad)
    if didLoad&&bdIsLoaded(model)&&strcmp(get_param(model,'SimulationStatus'),'stopped')&& ...
            strcmp(get_param(model,'Dirty'),'off')&& ...
            strcmpi(strrep(get_param(model,'FileName'),'\','/'), ...
            'D:/Academic/Projects/sar20m1/SAR20/current/models/SarAdc.slx')
        close_system(model,0);
    end
end

function write_receipt(root,value)
    events=fopen(fullfile(root,'receipt_events.jsonl'),'a','n','UTF-8');
    assert(events>=0,'SAR20N256:receipt','Cannot append run event.');
    eventGuard=onCleanup(@()fclose(events)); %#ok<NASGU>
    fwrite(events,[jsonencode(value) newline],'char');
    clear eventGuard
    f=fopen(fullfile(root,'matlab_receipt.json'),'w','n','UTF-8');
    assert(f>=0,'SAR20N256:receipt','Cannot write run receipt.');
    c=onCleanup(@()fclose(f)); %#ok<NASGU>
    fwrite(f,[jsonencode(value) newline],'char');
end
