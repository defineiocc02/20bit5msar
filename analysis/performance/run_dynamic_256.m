% SAR20 N256 actual dynamic capture, version 1 (2026-10-26).
% Public apply/run only; compact observers and the accepted physical kernel.
% The saved source is retained. The native capture gate rejects incoherence.
% A spectrum is preliminary evidence, not independent physical/NI signoff.
run_dynamic_256_main;

function run_dynamic_256_main
    root=fileparts(fileparts(fileparts(mfilename('fullpath'))));
    folder=fullfile(root,'runs','control');out=fullfile(folder,'dynamic_256_result.json');
    report=struct('status','started','stage','guard');
    previousPath=path;restorePath=onCleanup(@()path(previousPath)); %#ok<NASGU>
    addpath(root,'-begin');
    try
        assert(feature('getpid')==25440,'SAR20Dynamic:pid','Require the verified desktop MATLAB.');
        if bdIsLoaded('PoolCt')
            assert(strcmp(get_param('PoolCt','SimulationStatus'),'stopped')&& ...
                strcmp(get_param('PoolCt','Dirty'),'off'), ...
                'SAR20Dynamic:busy','An open model must be stopped and saved.');
        end
        assert(strcmpi(which('SAR20'),fullfile(root,'SAR20.m')), ...
            'SAR20Dynamic:entry','Require the unique engineering entry.');
        baselineFile=fullfile(root,'runs', ...
            'run_tp8d3ea108_5620_44f6_b4bb_bfd421d82725','compact_trial_receipt.json');
        baseline=jsondecode(fileread(baselineFile));
        assert(strcmp(baseline.status,'actual_cache_compact_capture_bitwise_pass'), ...
            'SAR20Dynamic:baseline','Require the accepted compact short capture.');
        q=jsondecode(fileread(fullfile(root,'config','parameters.json')));
        assert(q.record_length==256&&q.tracking_count==8&&q.AChanges.UGB_hz==1.2e9&& ...
            q.AChanges.max_step_s==62.5e-12&&strcmp(q.capture_mode,'compact')&&isempty(q.source_override), ...
            'SAR20Dynamic:config','Require explicit M8/N256/62.5ps compact with retained source.');
        assert(strcmp(profile('status').ProfilerStatus,'off'), ...
            'SAR20Dynamic:profile','Profiler must be off.');
        before=rng;report.parameters=q;report.baseline_receipt=baselineFile;
        report.stage='apply';write_json(out,report);report.apply=SAR20('apply');
        report.stage='run';write_json(out,report);report.run=SAR20('run');
        report.global_rng_unchanged=isequaln(before,rng);
        assert(report.global_rng_unchanged,'SAR20Dynamic:rng','Global RNG changed.');
        rr=report.run.run_report;
        assert(rr.records==256&&numel(rr.code20)==256&&~isempty(rr.spectrum), ...
            'SAR20Dynamic:records','Require 256 actual integer codes and native spectrum.');
        short=baseline.run.run_report.code20;
        % Normalize orientation only, never alter numerical values or precision.
        report.first_eight_codes_match_closed_short=isequal(rr.code20(1:8), ...
            reshape(short,size(rr.code20(1:8))));
        assert(report.first_eight_codes_match_closed_short, ...
            'SAR20Dynamic:prefix','Long-run prefix differs from the accepted short capture.');
        report.status='actual_n256_capture_complete_pending_independent_analysis';
        report.stage='complete';
        write_json(fullfile(report.run.run_root,'dynamic_256_receipt.json'),report);
    catch cause
        report.status='failed';report.identifier=cause.identifier;
        report.message=cause.message;report.stack=cause.stack;
    end
    write_json(out,report);
end

function write_json(file,value)
    fid=fopen(file,'w','n','UTF-8');assert(fid~=-1,'SAR20Dynamic:write','Cannot write receipt.');
    cleanup=onCleanup(@()fclose(fid)); %#ok<NASGU>
    fprintf(fid,'%s\n',jsonencode(value));
end
