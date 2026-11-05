% SAR20 current-kernel profile, version 1 (2026-10-26).
% Host controller stages this file at <project>/runs/control/.
% Calls only SAR20('run'), using the already applied M8/N8/62.5ps configuration.
% No clear-all, class reset, parameter apply, solver edit or RNG reset.
% Resume preserves existing profiler counters; before/after tables are saved
% separately so analysis uses their difference rather than mixed totals.
run_profile_main;

function run_profile_main
    root=fileparts(fileparts(fileparts(mfilename('fullpath'))));
    folder=fullfile(root,'runs','control');
    receipt=fullfile(folder,'profile_result.json');
    report=struct('status','started','stage','guard','profile_started',false);
    ownsProfiler=false;
    try
        assert(feature('getpid')==14168,'SAR20Profile:pid','Existing MATLAB only.');
        if bdIsLoaded('PoolCt')
            assert(strcmp(get_param('PoolCt','SimulationStatus'),'stopped') && ...
                strcmp(get_param('PoolCt','Dirty'),'off'), ...
                'SAR20Profile:busy','Current model is busy or dirty.');
        end
        assert(strcmpi(which('SAR20'),fullfile(root,'SAR20.m')), ...
            'SAR20Profile:entry','Require the unique engineering entry.');
        q=jsondecode(fileread(fullfile(root,'config','parameters.json')));
        assert(q.record_length==8 && q.tracking_count==8 && ...
            q.AChanges.UGB_hz==1.2e9 && q.AChanges.max_step_s==62.5e-12 && ...
            strcmp(q.capture_mode,'compact') && isempty(q.source_override), ...
            'SAR20Profile:config','Require the saved N8/M8/62.5ps case.');
        status=profile('status');
        assert(strcmp(status.ProfilerStatus,'off'), ...
            'SAR20Profile:activeProfiler','An existing active profiler will not be interrupted.');
        beforeInfo=profile('info');
        save(fullfile(folder,'profile_before.mat'),'beforeInfo','-v7.3');
        beforeRng=rng;
        report.stage='run';
        write_json(receipt,report);
        profile('resume');
        ownsProfiler=true;
        report.profile_started=true;
        runResult=SAR20('run');
        profile('off');
        ownsProfiler=false;
        afterInfo=profile('info');
        save(fullfile(folder,'profile_after.mat'),'afterInfo','-v7.3');
        write_json(fullfile(folder,'profile_tables.json'), ...
            struct('before',beforeInfo.FunctionTable,'after',afterInfo.FunctionTable));
        report.run=runResult;
        report.global_rng_unchanged=isequaln(beforeRng,rng);
        assert(report.global_rng_unchanged,'SAR20Profile:rng','Global RNG changed.');
        report.stage='complete';
        report.status='actual_profile_complete_pending_bitwise_capture_gate';
        report.prior_profiler_counters_preserved=true;
        report.timing_scope='Instrumented diagnostic; not an unprofiled speed benchmark.';
        for name={'profile_before.mat','profile_after.mat','profile_tables.json'}
            copyfile(fullfile(folder,name{1}),fullfile(runResult.run_root,name{1}));
        end
        write_json(fullfile(runResult.run_root,'profile_receipt.json'),report);
    catch cause
        if ownsProfiler, profile('off'); end
        report.status='failed';
        report.identifier=cause.identifier;
        report.message=cause.message;
        report.stack=cause.stack;
    end
    write_json(receipt,report);
end

function write_json(file,value)
    fid=fopen(file,'w','n','UTF-8');
    assert(fid~=-1,'SAR20Profile:write','Cannot write profile evidence.');
    cleanup=onCleanup(@()fclose(fid)); %#ok<NASGU>
    fprintf(fid,'%s\n',jsonencode(value));
end
