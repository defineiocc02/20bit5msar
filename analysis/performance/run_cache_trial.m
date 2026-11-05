% SAR20 cache trial, version 1 (2026-10-26).
% Run only after the old-source physics reference is closed and archived.
% Code-only trial: no parameter apply, model edit, reseed or solver change.
run_cache_trial_main;

function run_cache_trial_main
    root=fileparts(fileparts(fileparts(mfilename('fullpath'))));
    folder=fullfile(root,'runs','control');out=fullfile(folder,'cache_trial_result.json');
    report=struct('status','started','stage','guard');
    previousPath=path;restorePath=onCleanup(@()path(previousPath)); %#ok<NASGU>
    addpath(root,'-begin');
    try
        assert(feature('getpid')==25440,'SAR20Cache:pid','Require the verified desktop MATLAB.');
        if bdIsLoaded('PoolCt')
            assert(strcmp(get_param('PoolCt','SimulationStatus'),'stopped')&& ...
                strcmp(get_param('PoolCt','Dirty'),'off'), ...
                'SAR20Cache:busy','An open model must be stopped and saved.');
        end
        assert(strcmpi(which('SAR20'),fullfile(root,'SAR20.m'))&& ...
            strcmpi(which('compare_captures'),fullfile(folder,'compare_captures.m')), ...
            'SAR20Cache:entry','Require unique entry and staged comparer.');
        q=jsondecode(fileread(fullfile(root,'config','parameters.json')));
        assert(q.record_length==8&&q.tracking_count==8&&q.AChanges.UGB_hz==1.2e9&& ...
            q.AChanges.max_step_s==62.5e-12&&strcmp(q.capture_mode,'physics')&&isempty(q.source_override), ...
            'SAR20Cache:config','Require the unchanged M8/N8/62.5ps physics configuration.');
        old=jsondecode(fileread(fullfile(folder,'physics_result.json')));
        assert(strcmp(old.status,'actual_full_state_capture_complete_pending_independent_gate'), ...
            'SAR20Cache:reference','Require the completed old-source full-state capture.');
        assert(strcmp(profile('status').ProfilerStatus,'off'),'SAR20Cache:profile','Profiler must be off.');
        clear pool_cached_predict pool_cached_matrix run_pool_ct compare_captures
        before=rng;report.parameters=q;report.reference_run=old.run.run_root;
        report.stage='check';write_json(out,report);report.check=SAR20('check');
        report.stage='run';write_json(out,report);report.run=SAR20('run');
        report.global_rng_unchanged=isequaln(before,rng);
        assert(report.global_rng_unchanged,'SAR20Cache:rng','Global RNG changed.');
        report.stage='compare_full_state';write_json(out,report);
        report.comparison=compare_captures(fullfile(old.run.run_root,'direct_run'), ...
            fullfile(report.run.run_root,'direct_run'),false);
        write_json(out,report);
        assert(strcmp(report.comparison.status,'bitwise_capture_pass')&& ...
            report.comparison.logger_count==59&&report.comparison.full_analog_state_in_comparison&& ...
            numel(report.comparison.state_word_comparisons)==2, ...
            'SAR20Cache:comparison','Full physics state/ledger/RNG comparison failed.');
        report.status='actual_cache_trial_full_state_bitwise_pass';report.stage='complete';
        write_json(fullfile(report.run.run_root,'cache_trial_receipt.json'),report);
    catch cause
        report.status='failed';report.identifier=cause.identifier;
        report.message=cause.message;report.stack=cause.stack;
    end
    write_json(out,report);
end

function write_json(file,value)
    fid=fopen(file,'w','n','UTF-8');assert(fid~=-1,'SAR20Cache:write','Cannot write receipt.');
    cleanup=onCleanup(@()fclose(fid)); %#ok<NASGU>
    fprintf(fid,'%s\n',jsonencode(value));
end
