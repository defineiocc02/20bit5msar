% SAR20 compact acceptance, version 1 (2026-10-26).
% Restore the daily compact observers using the public apply/run API.
% Physical parameters, samples, random seeds and timing stay unchanged.
run_compact_trial_main;

function run_compact_trial_main
    root=fileparts(fileparts(fileparts(mfilename('fullpath'))));
    folder=fullfile(root,'runs','control');out=fullfile(folder,'compact_trial_result.json');
    report=struct('status','started','stage','guard');
    previousPath=path;restorePath=onCleanup(@()path(previousPath)); %#ok<NASGU>
    addpath(root,'-begin');
    try
        assert(feature('getpid')==25440,'SAR20Compact:pid','Require the verified desktop MATLAB.');
        if bdIsLoaded('PoolCt')
            assert(strcmp(get_param('PoolCt','SimulationStatus'),'stopped')&& ...
                strcmp(get_param('PoolCt','Dirty'),'off'), ...
                'SAR20Compact:busy','An open model must be stopped and saved.');
        end
        assert(strcmpi(which('SAR20'),fullfile(root,'SAR20.m'))&& ...
            strcmpi(which('compare_captures'),fullfile(folder,'compare_captures.m')), ...
            'SAR20Compact:entry','Require the unique entry and staged comparer.');
        gate=jsondecode(fileread(fullfile(folder,'cache_trial_result.json')));
        assert(strcmp(gate.status,'actual_cache_trial_full_state_bitwise_pass'), ...
            'SAR20Compact:fullState','Require the completed 59-logger cache gate.');
        q=jsondecode(fileread(fullfile(root,'config','parameters.json')));
        assert(q.record_length==8&&q.tracking_count==8&&q.AChanges.UGB_hz==1.2e9&& ...
            q.AChanges.max_step_s==62.5e-12&&strcmp(q.capture_mode,'compact')&&isempty(q.source_override), ...
            'SAR20Compact:config','Require unchanged M8/N8/62.5ps and compact observers.');
        assert(strcmp(profile('status').ProfilerStatus,'off'),'SAR20Compact:profile','Profiler must be off.');
        before=rng;report.parameters=q;
        report.stage='apply_compact';write_json(out,report);report.apply=SAR20('apply');
        report.stage='run';write_json(out,report);report.run=SAR20('run');
        report.global_rng_unchanged=isequaln(before,rng);
        assert(report.global_rng_unchanged,'SAR20Compact:rng','Global RNG changed.');
        report.stage='compare_compact';write_json(out,report);
        report.comparison=compare_captures(fullfile(root,'runs', ...
            'run_tp394bdae9_7cbe_4949_9cd7_da5d4830e619','direct_run'), ...
            fullfile(report.run.run_root,'direct_run'),false);
        write_json(out,report);
        assert(strcmp(report.comparison.status,'bitwise_capture_pass')&& ...
            report.comparison.logger_count==54&&~report.comparison.full_analog_state_in_comparison, ...
            'SAR20Compact:comparison','Compact actual capture changed after the cache patch.');
        report.status='actual_cache_compact_capture_bitwise_pass';report.stage='complete';
        write_json(fullfile(report.run.run_root,'compact_trial_receipt.json'),report);
    catch cause
        report.status='failed';report.identifier=cause.identifier;
        report.message=cause.message;report.stack=cause.stack;
    end
    write_json(out,report);
end

function write_json(file,value)
    fid=fopen(file,'w','n','UTF-8');assert(fid~=-1,'SAR20Compact:write','Cannot write receipt.');
    cleanup=onCleanup(@()fclose(fid)); %#ok<NASGU>
    fprintf(fid,'%s\n',jsonencode(value));
end
