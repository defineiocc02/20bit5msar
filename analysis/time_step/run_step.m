% SAR20 numerical-step capture harness, version 1 (2026-10-26).
% Purpose: apply the single config/parameters.json, then run the sole SAR20 entry.
% This harness is not an ADC model. It does not edit kernels, clocks, feedback,
% random state, or tolerances. The existing Windows MATLAB instance is required.
% Host controller stages this same file in <project>/runs/control/.
run_step_main;

function run_step_main
    root=fileparts(fileparts(fileparts(mfilename('fullpath'))));
    out=fullfile(root,'runs','control','native_step_result.json');
    report=struct('status','started','stage','guard');
    try
        assert(feature('getpid')==14168,'SAR20Step:pid','Existing MATLAB only.');
        if bdIsLoaded('PoolCt')
            assert(strcmp(get_param('PoolCt','SimulationStatus'),'stopped') && ...
                strcmp(get_param('PoolCt','Dirty'),'off'), ...
                'SAR20Step:busy','Target model is busy or dirty.');
        end
        assert(strcmpi(which('SAR20'),fullfile(root,'SAR20.m')), ...
            'SAR20Step:entry','The unique public entry must resolve.');
        params=jsondecode(fileread(fullfile(root,'config','parameters.json')));
        assert(params.record_length==8 && params.tracking_count==8 && ...
            strcmp(params.capture_mode,'compact') && isempty(params.source_override), ...
            'SAR20Step:config','Require M8 N8 compact with the saved input.');
        assert(params.AChanges.UGB_hz==1.2e9 && ...
            ismember(params.AChanges.max_step_s,[250e-12 125e-12 62.5e-12]), ...
            'SAR20Step:step','Require the explicit same-UGB step experiment.');
        report.parameters=params;
        before=rng;
        report.stage='apply';write_json(out,report);
        report.apply=SAR20('apply');
        report.stage='run';write_json(out,report);
        report.run=SAR20('run');
        report.global_rng_unchanged=isequaln(before,rng);
        assert(report.global_rng_unchanged,'SAR20Step:rng','Global RNG changed.');
        report.stage='complete';
        report.status='actual_run_complete_pending_independent_comparison';
        write_json(fullfile(report.run.run_root,'native_step_receipt.json'),report);
    catch cause
        report.status='failed';
        report.identifier=cause.identifier;
        report.message=cause.message;
        report.stack=cause.stack;
    end
    write_json(out,report);
end

function write_json(file,value)
    fid=fopen(file,'w','n','UTF-8');
    assert(fid~=-1,'SAR20Step:write','Cannot write receipt.');
    cleanup=onCleanup(@()fclose(fid)); %#ok<NASGU>
    fprintf(fid,'%s\n',jsonencode(value));
end
