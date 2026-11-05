% SAR20 short full-state reference, version 1 (2026-10-26).
% Host-only capture via the sole SAR20 apply/run API. config/parameters.json
% must explicitly select physics, M8, N8 and the saved 62.5ps experiment.
% Heavy state/charge logging is for this numerical check, not the daily default.
run_physics_main;

function run_physics_main
    root=fileparts(fileparts(fileparts(mfilename('fullpath'))));
    out=fullfile(root,'runs','control','physics_result.json');
    report=struct('status','started','stage','guard');
    previousPath=path;
    restorePath=onCleanup(@()path(previousPath)); %#ok<NASGU>
    addpath(root,'-begin'); % run() enters runs/control; expose only the public entry.
    try
        assert(feature('getpid')==25440,'SAR20Physics:pid','Existing MATLAB only.');
        if bdIsLoaded('PoolCt')
            assert(strcmp(get_param('PoolCt','SimulationStatus'),'stopped') && ...
                strcmp(get_param('PoolCt','Dirty'),'off'), ...
                'SAR20Physics:busy','Current model is busy or dirty.');
        end
        assert(strcmpi(which('SAR20'),fullfile(root,'SAR20.m')), ...
            'SAR20Physics:entry','Require the unique engineering entry.');
        assert(strcmpi(which('compare_captures'),fullfile(root,'runs','control','compare_captures.m')), ...
            'SAR20Physics:comparer','Require the staged capture comparator.');
        assert(strcmp(profile('status').ProfilerStatus,'off'), ...
            'SAR20Physics:profile','Physics capture requires profiler off.');
        q=jsondecode(fileread(fullfile(root,'config','parameters.json')));
        assert(q.record_length==8 && q.tracking_count==8 && ...
            q.AChanges.UGB_hz==1.2e9 && q.AChanges.max_step_s==62.5e-12 && ...
            strcmp(q.capture_mode,'physics') && isempty(q.source_override), ...
            'SAR20Physics:config','Require explicit M8/N8/62.5ps physics capture.');
        before=rng;
        report.parameters=q;
        report.stage='apply';write_json(out,report);
        report.apply=SAR20('apply');
        report.stage='run';write_json(out,report);
        report.run=SAR20('run');
        report.global_rng_unchanged=isequaln(before,rng);
        assert(report.global_rng_unchanged,'SAR20Physics:rng','Global RNG changed.');
        report.stage='compare_observers';write_json(out,report);
        compact=fullfile(root,'runs','run_tp394bdae9_7cbe_4949_9cd7_da5d4830e619','direct_run');
        profiled=fullfile(root,'runs','run_tp1c8c00ea_f0ad_41cd_959f_9684f26cd599','direct_run');
        report.profile_comparison=compare_captures(compact,profiled,false);
        assert(report.profile_comparison.logger_count==54&& ...
            ~report.profile_comparison.full_analog_state_in_comparison, ...
            'SAR20Physics:profileScope','Profile comparison must cover all 54 compact loggers.');
        report.physics_common_comparison=compare_captures(compact, ...
            fullfile(report.run.run_root,'direct_run'),true);
        assert(report.physics_common_comparison.logger_count==54&& ...
            numel(report.physics_common_comparison.excluded_candidate_loggers)==5&& ...
            isempty(report.physics_common_comparison.excluded_reference_loggers), ...
            'SAR20Physics:observerScope','Physics observation comparison must cover 54 common loggers and exactly five added heavy logs.');
        assert(strcmp(report.profile_comparison.status,'bitwise_capture_pass') && ...
            strcmp(report.physics_common_comparison.status,'bitwise_capture_pass'), ...
            'SAR20Physics:comparison','Profile or physics observer change affected saved common behavior.');
        report.status='actual_full_state_capture_complete_pending_independent_gate';
        report.stage='complete';
        write_json(fullfile(report.run.run_root,'physics_receipt.json'),report);
    catch cause
        report.status='failed';report.identifier=cause.identifier;
        report.message=cause.message;report.stack=cause.stack;
    end
    write_json(out,report);
end

function write_json(file,value)
    fid=fopen(file,'w','n','UTF-8');
    assert(fid~=-1,'SAR20Physics:write','Cannot write receipt.');
    cleanup=onCleanup(@()fclose(fid)); %#ok<NASGU>
    fprintf(fid,'%s\n',jsonencode(value));
end
