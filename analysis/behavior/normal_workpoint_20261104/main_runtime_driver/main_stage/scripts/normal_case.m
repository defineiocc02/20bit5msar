function result=normal_case(jobRoot,caseName)
% UNFROZEN SCRATCH; one isolated case per new headless MATLAB process.
% Job controller MUST first pin every helper/runtime file and reject reparse.
% 10 V is differential full-scale range; sampling remains 5 MS/s, no ADI.
    jobRoot=normal_jobroot(jobRoot);
    valid={'ideal_v2_n8','ideal_merged_n8','normal_merged_n8','normal_merged_n8_tap', ...
        'ideal_merged_n256','normal_merged_n256'};
    assert(ischar(caseName)&&any(strcmp(caseName,valid)),'normalCase:name','Unknown case.');
    assert(ispc&&feature('getpid')~=27628&&~usejava('desktop')&&~bdIsLoaded('SarAdc'), ...
        'normalCase:session','Require fresh private headless MATLAB with no loaded model.');
    scripts=fileparts(mfilename('fullpath'));
    candidate=fullfile(jobRoot,'candidate');baseline=fullfile(jobRoot,'baseline','single_bank');
    profile=fullfile(jobRoot,'profile');model=fullfile(jobRoot,'model','SarAdc.slx');
    pr=read_json(fullfile(profile,'complete.json'));
    assert(strcmp(pr.status,'prepared')&&strcmp(sha(fullfile(candidate,'MANIFEST.json')),pr.candidate_manifest_sha256)&& ...
        strcmp(sha(model),'48537818b3212e1e4c8231dec433d1fde36d95814cdcce8c529bb2898eb097d3'), ...
        'normalCase:identity','Profile/candidate/485 model identity differs.');
    isNormal=startsWith(caseName,'normal_');is256=endsWith(caseName,'n256');
    isTap=strcmp(caseName,'normal_merged_n8_tap');
    isV2=strcmp(caseName,'ideal_v2_n8');
    if isV2,runtime=baseline;else,runtime=candidate;end
    if isNormal,pFile=fullfile(profile,'normal_P.mat');expectedP=pr.normal_P_sha256;var='P';
    else,pFile=fullfile(profile,'ideal_P.mat');expectedP=pr.ideal_P_sha256;var='ideal';end
    assert(strcmp(sha(pFile),expectedP),'normalCase:profile','Prepared P bytes changed.');
    data=load(pFile,var);P8=data.(var);
    assert(P8.N==8&&P8.Ts_s==200e-9&&P8.fs_hz==5e6&&P8.fsr_diff_v==10&& ...
        P8.digital.fsr_diff_v==10&&P8.front.single_bank&&~P8.front.dem_enabled&& ...
        ~P8.front.dither_enabled&&~P8.front.jitter.enabled&&~P8.transport.enabled&& ...
        ~P8.training.enabled&&~P8.cal_cfg.enabled&&~P8.frozen.enabled&&~P8.bank.enabled&& ...
        ~P8.debug.adi_enabled&&~P8.debug.aperture_enabled&&~P8.debug.dac_enabled&& ...
        strcmp(P8.digital.calibration_mode,'off'), ...
        'normalCase:scope','Require the supplied FSR10, 5MS/s, single-bank no-ADI P.');
    if isNormal
        prior=read_json(fullfile(jobRoot,'ideal_merged_n8','complete.json'));
        assert(isfield(prior,'v2_comparison')&&strcmp(prior.v2_comparison,'PASS'), ...
            'normalCase:idealGate','Ideal v2 OFF comparison must pass first.');
    end
    if isTap
        plainDir=fullfile(jobRoot,'normal_merged_n8');plainReceipt=read_json(fullfile(plainDir,'complete.json'));
        assert(strcmp(plainReceipt.status,'passed')&&strcmp(plainReceipt.input_P_sha256,expectedP)&& ...
            strcmp(sha(fullfile(plainDir,'simout.mat')),plainReceipt.simout_sha256), ...
            'normalCase:plainGate','Normal N8 plain result is missing or changed.');
    end
    if is256
        if isNormal
            tapReceipt=read_json(fullfile(jobRoot,'normal_merged_n8_tap','complete.json'));
            assert(strcmp(tapReceipt.status,'passed')&&strcmp(tapReceipt.tap_nondisturbance,'PASS')&& ...
                strcmp(tapReceipt.input_P_sha256,expectedP),'normalCase:tapGate','Normal N8 tap gate is missing.');
        end
        if isNormal,n8dir=fullfile(jobRoot,'normal_merged_n8');else,n8dir=fullfile(jobRoot,'ideal_merged_n8');end
        n8receipt=read_json(fullfile(n8dir,'complete.json'));
        assert(strcmp(n8receipt.status,'passed')&&strcmp(n8receipt.input_P_sha256,expectedP)&& ...
            strcmp(sha(fullfile(n8dir,'simout.mat')),n8receipt.simout_sha256)&& ...
            strcmp(sha(fullfile(n8dir,'P_used.mat')),n8receipt.P_used_sha256), ...
            'normalCase:n8Gate','Corresponding FSR10 N8 is missing or changed.');
    end
    outdir=fullfile(jobRoot,caseName);assert(~isfolder(outdir)&&~isfile(outdir),'normalCase:exists','Case exists.');
    [ok,msg,id]=mkdir(outdir);assert(ok&&isempty(id),'normalCase:mkdir','%s',msg);
    result=struct('status','started','case_name',caseName,'pid',feature('getpid'), ...
        'input_P_sha256',expectedP,'model_sha256',sha(model),'candidate_manifest_sha256',pr.candidate_manifest_sha256, ...
        'scope','FSR10 assumption, 5MS/s single-bank behavioral model; no ADI or signoff');
    try
        restoredefaultpath;rehash;cd(jobRoot);
        reference=fullfile(jobRoot,'reference');addpath(reference,scripts,'-begin');
        indexFile=fullfile(jobRoot,'normal_runtime_index.json');
        assert(strcmp(sha(indexFile),'9aa4c6cd0473200d8e3c846cb60da372aebad399ae30b3acb33fae45e4ccc311'), ...
            'normalCase:index','Runtime index differs.');
        index=jsondecode(fileread(indexFile));
        assert(strcmp(index.candidate_manifest_sha256,pr.candidate_manifest_sha256)&& ...
            strcmp(index.baseline_manifest_sha256,'2cbdffe537b694cef6107ce893ea8bca7f8ef5d95f6ff7d993f020150c6dd514'), ...
            'normalCase:index','Runtime index provenance differs.');
        if isV2,entries=index.v2;else,entries=index.merged;end
        verify_sources(runtime,entries);bound=normal_bind_runtime(runtime,entries,true);
        save(fullfile(outdir,'binding_before.mat'),'bound','-v7.3');
        for name={'behavior_prepare_configuration','behavior_record_view','behavior_decode','behavior_public_pol','behavior_spectrum'}
            actual=which(name{1});assert(under(actual,runtime),'normalCase:path','Wrong source for %s: %s',name{1},actual);
        end
        if ~isV2,assert(under(which('behavior_comparator_sample'),runtime),'normalCase:path','Wrong comparator source.');end
        P=P8;
        if isTap
            P.debug.adi_enabled=true;P.debug.aperture_enabled=true;P.debug.dac_enabled=true;
            P=behavior_prepare_configuration(P);changes=sb256_diff_paths(P8,P,'P');
            allowed={'P.debug.adi_enabled','P.debug.adi_max_points','P.debug.aperture_enabled', ...
                'P.debug.aperture_max_points','P.debug.dac_enabled','P.debug.dac_max_points'};
            [before,after]=sb256_diff_values(P8,P,changes);save(fullfile(outdir,'P_diff.mat'),'changes','before','after','-v7.3');
            assert(all(ismember(changes,allowed)),'normalCase:tapDiff','Tap changed a non-observer field.');
        end
        if is256
            P.N=256;P.front.plan_rows=264;P.front.plan=[];P=behavior_prepare_configuration(P);
            changes=sb256_diff_paths(P8,P,'P');
            allowed={'P.N','P.front.plan_rows','P.front.plan','P.n_cycles','P.stop_time_s', ...
                'P.schedule.n_cycles','P.schedule.stop_time_s','P.backend.dac_coupling.public_plan', ...
                'P.training.reference.records','P.cal_cfg.N_train','P.cal_cfg.public_cfg.plan_rows'};
            [before,after]=sb256_diff_values(P8,P,changes);save(fullfile(outdir,'P_diff.mat'),'changes','before','after','-v7.3');
            assert(all(ismember(changes,allowed)),'normalCase:Pdiff','Unexpected N256 physical/source parameter change.');
            assert(P.N==256&&P.schedule.n_cycles==260&&P.input.frequency_hz*P.N/P.fs_hz==5, ...
                'normalCase:coherence','Expected N256 coherent bin 5.');
        end
        save(fullfile(outdir,'P_used.mat'),'P','P8','-v7.3');result.P_used_sha256=sha(fullfile(outdir,'P_used.mat'));
        cd(outdir);Simulink.fileGenControl('set','CacheFolder',fullfile(outdir,'cache'), ...
            'CodeGenFolder',fullfile(outdir,'codegen'),'keepPreviousPath',true,'createDir',true);
        cfg=Simulink.fileGenControl('getConfig');assert(under(cfg.CacheFolder,outdir)&&under(cfg.CodeGenFolder,outdir), ...
            'normalCase:fileGen','Cache/codegen escaped output.');
        closer=onCleanup(@()close_owned(model)); %#ok<NASGU>
        load_system(model);block=Simulink.ID.getFullName('SarAdc:185');
        assert(strcmpi(canon(get_param('SarAdc','FileName')),canon(model))&& ...
            strcmp(get_param(block,'Bias'),'DecodeP.d1_bias_v'),'normalCase:graph','Graph/bias differs.');
        ws=get_param('SarAdc','ModelWorkspace');savedP=getVariable(ws,'P');savedD=getVariable(ws,'DecodeP');
        savedCapture=getVariable(ws,'TrainCaptureFile');
        assert(ischar(savedCapture)&&isempty(savedCapture),'normalCase:trainingPath','Saved TrainCaptureFile must be empty.');
        result.saved_annotation_baseline_not_runtime=true;
        result.settings_scope='SimulationInput injected/intended; runtime dialog not independently probed';
        result.debug_scope='Observer flags only; physical ADI disabled; next wires are not committed-state probes';
        baseFile=fullfile(jobRoot,'inputs','P_used.mat');
        assert(strcmp(sha(baseFile),'236ddfb427dfc07e7f7e27dd58746deb30946891717d255b53789aa8127a1e9f'), ...
            'normalCase:base','Original N8 P identity differs.');
        base=load(baseFile,'P');assert(sb256_same_bits(savedP,base.P)&&sb256_same_bits(savedD,base.P.digital), ...
            'normalCase:workspace','Stored graph workspace differs from actual original N8 P.');
        for id=0:3,assert(behavior_public_pol(id,P.epoch,P.digital.az_mode)==1, ...
                'normalCase:pol','Ordinary/off mode must use public POL +1.');end
        result.retained_ra_finite=struct('A0',P.backend.ra.A0,'UGB_hz',P.backend.ra.UGB_hz);
        result.settings=struct('fs_hz',P.fs_hz,'fsr_diff_v',P.fsr_diff_v,'N',P.N, ...
            'input',P.input,'seed',P.seed,'ktc_seed',P.front.ktc_seed,'ni',P.ni, ...
            'training',P.training.enabled,'cal_cfg',P.cal_cfg.enabled,'frozen',P.frozen.enabled,'bank',P.bank.enabled);
        result.settings.single_guard_s=P.front.single_guard_s;
        result.settings.tau_sample_s=P.front.tau_sample_s;result.settings.tau_dac_s=P.front.tau_dac_s;
        result.settings.temperature_K=P.front.temperature_K;result.settings.ktc_enabled=P.front.ktc_enabled;
        result.settings.az_mode=P.backend.az.mode;result.settings.debug=P.debug;
        result.settings.ra_noise='OFF_OR_ABSENT';
        if isfield(P.backend,'ra_noise'),result.settings.ra_noise=P.backend.ra_noise;end
        result.settings.comparator='OFF_OR_ABSENT';
        if isfield(P.control,'comparator'),result.settings.comparator=P.control.comparator;end
        if isfield(P.ni,'comparator_noise_scope'),result.settings.comparator_noise_scope=P.ni.comparator_noise_scope;end
        if isNormal,result.settings.label='10V normal assumptions; not PDK-typical or measured';
        else,result.settings.label='10V original baseline, newly added NI OFF; finite A0/UGB remain';end
        sv=ver('simulink');result.matlab_version=version;result.matlab_release=version('-release');
        assert(isscalar(sv),'normalCase:simulink','Simulink version missing.');result.simulink_version=sv.Version;
        result.solver=struct('name',get_param('SarAdc','Solver'),'type',get_param('SarAdc','SolverType'), ...
            'mode',get_param('SarAdc','SimulationMode'),'start',get_param('SarAdc','StartTime'),'stop',get_param('SarAdc','StopTime'));
        write_new(fullfile(outdir,'started.json'),result);
        si=Simulink.SimulationInput('SarAdc');si=si.setVariable('P',P,'Workspace','SarAdc');
        si=si.setVariable('DecodeP',P.digital,'Workspace','SarAdc');
        si=si.setVariable('TrainCaptureFile','','Workspace','SarAdc');
        si=si.setModelParameter('ReturnWorkspaceOutputs','on','CaptureErrors','on');
        beforeRng=rng;save(fullfile(outdir,'rng_before.mat'),'beforeRng','-v7.3');
        result.rng_before_sha256=sha(fullfile(outdir,'rng_before.mat'));
        refDir='';
        if is256,refDir=n8dir;
        elseif isTap,refDir=plainDir;
        elseif strcmp(caseName,'ideal_merged_n8'),refDir=fullfile(jobRoot,'ideal_v2_n8');
        elseif strcmp(caseName,'normal_merged_n8'),refDir=fullfile(jobRoot,'ideal_merged_n8');end
        if ~isempty(refDir)
            rr=read_json(fullfile(refDir,'complete.json'));rf=fullfile(refDir,'rng_before.mat');
            assert(strcmp(rr.status,'passed')&&strcmp(sha(rf),rr.rng_before_sha256)&& ...
                strcmp(rr.matlab_version,result.matlab_version)&&strcmp(rr.matlab_release,result.matlab_release)&& ...
                strcmp(rr.simulink_version,result.simulink_version)&&sb256_same_bits(rr.solver,result.solver), ...
                'normalCase:runtime','Reference runtime, solver or RNG snapshot identity differs.');
            previous=load(rf,'beforeRng');
            assert(sb256_same_bits(beforeRng,previous.beforeRng),'normalCase:rng','Initial RNG differs from reference.');
        end
        timer=tic;simout=sim(si);result.sim_s=toc(timer);
        save(fullfile(outdir,'simout.mat'),'simout','-v7.3');result.simout_sha256=sha(fullfile(outdir,'simout.mat'));
        assert(isempty(simout.ErrorMessage)&&isequaln(beforeRng,rng),'normalCase:sim','Simulation/RNG failed: %s',simout.ErrorMessage);
        raw_log=simout.get('raw_log');ready_log=simout.get('ready_log');record_log=simout.get('record_log');
        record_ready_log=simout.get('record_ready_log');code_log=simout.get('code_log');
        event_log=simout.get('event_log');front_log=simout.get('front_log');back_log=simout.get('back_log');
        control_log=simout.get('control_log');az_route_log=simout.get('az_route_log');az_commit_log=simout.get('az_commit_log');
        if isTap
            adi_wire_log=simout.get('adi_wire_log');aperture_log=simout.get('aperture_log');dac_ra_pre_log=simout.get('dac_ra_pre_log');
            save(fullfile(outdir,'raw_capture.mat'),'raw_log','ready_log','record_log','record_ready_log','code_log', ...
                'event_log','front_log','back_log','control_log','az_route_log','az_commit_log', ...
                'adi_wire_log','aperture_log','dac_ra_pre_log','-v7.3');
        else
            save(fullfile(outdir,'raw_capture.mat'),'raw_log','ready_log','record_log','record_ready_log','code_log', ...
                'event_log','front_log','back_log','control_log','az_route_log','az_commit_log','-v7.3');
        end
        result.raw_capture_sha256=sha(fullfile(outdir,'raw_capture.mat'));
        verify_sources(runtime,entries);boundAfter=normal_bind_runtime(runtime,entries,false);
        save(fullfile(outdir,'binding_after.mat'),'boundAfter','-v7.3');
        assert(sb256_same_bits(getVariable(ws,'P'),savedP)&&sb256_same_bits(getVariable(ws,'DecodeP'),savedD)&& ...
            isequaln(getVariable(ws,'TrainCaptureFile'),savedCapture), ...
            'normalCase:workspace','Saved graph workspace changed.');
        V=behavior_record_view(simout,P);
        assert(size(V.raw,1)==P.N&&all(V.raw(:,6)==1)&& ...
            isequal(V.raw(:,4),(P.first_id:P.first_id+P.N-1).'),'normalCase:records','Invalid actual records.');
        public_code=public_decode(V.raw,P.digital);
        assert(isequal(public_code,double(V.code20(:))),'normalCase:decode','Actual codes differ from public RAW nominal formula.');
        csvFile=fullfile(outdir,'public_records.csv');write_public_csv(csvFile,V);
        digitalFile=fullfile(outdir,'public_digital.json');write_new(digitalFile,P.digital);
        result.public_records_sha256=sha(csvFile);result.public_digital_sha256=sha(digitalFile);
        sampling=sample_diagnostic(simout,P);
        save(fullfile(outdir,'sampling_diagnostic.mat'),'sampling','-v7.3');
        result.sampling_diagnostic_sha256=sha(fullfile(outdir,'sampling_diagnostic.mat'));
        result.public_digital_scope='Injected nominal DecodeP only; not an independently probed runtime dialog.';
        if is256
            n8=load(fullfile(n8dir,'simout.mat'),'simout');
            [selected,metadata,metrics,validation]=sb256_analyze(simout,P,n8.simout,P8);
            save(fullfile(outdir,'selected.mat'),'selected','metadata','-v7.3');
            save(fullfile(outdir,'spectrum.mat'),'metrics','validation','-v7.3');
            result.selected_sha256=sha(fullfile(outdir,'selected.mat'));result.spectrum_sha256=sha(fullfile(outdir,'spectrum.mat'));
        else
            if isTap,validation=normal_validate_tap(simout,P);else,validation=sb_validate_plain(simout,P);end
            save(fullfile(outdir,'validation.mat'),'validation','public_code','-v7.3');
            result.validation_sha256=sha(fullfile(outdir,'validation.mat'));
        end
        if isTap
            plain=load(fullfile(plainDir,'simout.mat'),'simout');
            tapComparison=normal_compare_outputs(plain.simout,simout,{'adi_wire_log','aperture_log','dac_ra_pre_log'});
            assert(strcmp(tapComparison.status,'PASS'),'normalCase:tapDiff','Tap perturbed non-observer outputs.');
            save(fullfile(outdir,'tap_comparison.mat'),'tapComparison','-v7.3');
            result.tap_nondisturbance='PASS';result.adi_wire_observer_only=true;result.physical_ADI=false;
        end
        if strcmp(caseName,'ideal_merged_n8')
            v2dir=fullfile(jobRoot,'ideal_v2_n8');v2r=read_json(fullfile(v2dir,'complete.json'));
            assert(strcmp(v2r.status,'passed')&&strcmp(v2r.input_P_sha256,expectedP)&& ...
                strcmp(v2r.model_sha256,result.model_sha256)&&strcmp(sha(fullfile(v2dir,'simout.mat')),v2r.simout_sha256), ...
                'normalCase:v2Gate','v2 ideal result missing or identity differs.');
            v2=load(fullfile(v2dir,'simout.mat'),'simout');comparison=normal_compare_outputs(v2.simout,simout);
            assert(strcmp(comparison.status,'PASS'),'normalCase:v2Diff','Ideal v2 OFF differs.');
            save(fullfile(outdir,'v2_comparison.mat'),'comparison','-v7.3');result.v2_comparison='PASS';
        end
        result.decode_scope='Actual integer code equals public nominal graph-order reconstruction; not internal-float bit equality or a runtime-parameter probe';
        result.status='passed';write_new(fullfile(outdir,'complete.json'),result);
    catch ex
        try,write_new(fullfile(outdir,'failed.json'),struct('status','failed','id',ex.identifier, ...
                'error',getReport(ex,'extended','hyperlinks','off'),'simout_saved',isfile(fullfile(outdir,'simout.mat'))));catch,end
        rethrow(ex)
    end
end
function verify_sources(runtime,entries)
    assert(isstruct(entries)&&~isempty(entries),'normalCase:source','Empty runtime index.');
    for k=1:numel(entries)
        rel=char(entries(k).path);
        assert(isempty(regexp(rel,'(^/|\\|:|(^|/)\.{1,2}(/|$)|//)','once')), ...
            'normalCase:source','Unsafe runtime path.');
        f=fullfile(runtime,strrep(rel,'/',filesep));
        assert(under(f,runtime)&&strcmp(sha(f),char(entries(k).sha256)), ...
            'normalCase:source','Runtime source identity differs: %s',rel);
    end
end
function write_public_csv(file,V)
    assert(~isfile(file)&&~isfolder(file),'normalCase:exists','CSV exists.');
    assert(size(V.raw,2)==6&&numel(V.time_s)==size(V.raw,1)&&numel(V.code20)==size(V.raw,1), ...
        'normalCase:csv','Public record dimensions differ.');
    f=fopen(file,'w','n','UTF-8');assert(f>=0,'normalCase:write','Cannot write public CSV.');c=onCleanup(@()fclose(f)); %#ok<NASGU>
    fprintf(f,'D1,D2,DT,ID,epoch,valid,time_s,code20\n');
    for k=1:size(V.raw,1)
        fprintf(f,'%.0f,%.0f,%.0f,%.0f,%.0f,%.0f,%.17g,%.0f\n',V.raw(k,:),V.time_s(k),V.code20(k));
    end
end
function d=sample_diagnostic(out,P)
% Model FE_retobs wire at CNV; reference/opening are derived, not physical probes.
    [te,e]=sb256_series(out,'event_log',2);[tf,front]=sb256_series(out,'front_log',7);
    assert(sb256_same_bits(te,tf),'normalCase:sampleAxis','Event/front time axes differ.');
    cnv=false(size(te));
    for g=1:numel(P.groups),cnv(e(:,2)==g)=any(strcmp({P.groups(g).events.type},'cnv'));end
    id=e(cnv,1);time=te(cnv);held=front(cnv,1);
    assert(numel(id)==P.schedule.n_cycles&&isequal(id,(0:P.schedule.n_cycles-1).'), ...
        'normalCase:sampleRows','Expected every modeled CNV row.');
    release=P.calendar(strcmp({P.calendar.type},'release'));assert(isscalar(release),'normalCase:release','One release required.');
    opening=(id-1)*P.Ts_s+release.time_s+P.front.single_guard_s;
    reference=P.input.offset_v+P.input.amplitude_v*sin(2*pi*P.input.frequency_hz*time+P.input.phase_rad);
    selected=id>=P.first_id&id<P.first_id+P.N;
    d=struct('id',id,'cnv_time_s',time,'selected',selected,'FE_retobs_at_cnv_v',held, ...
        'nominal_sine_at_cnv_v',reference,'held_minus_nominal_sine_v',held-reference, ...
        'calendar_open_s',opening,'calendar_window_s',time-opening, ...
        'scope','FE_retobs model wire and derived reference/calendar; not a direct physical state or isolated kTC measurement');
end
function code=public_decode(raw,p)
% Public RAW + nominal DecodeP only, matching the model operation order.
    assert(p.vref_v==5&&p.fsr_diff_v==10&&p.d1_bias_v==0&&~p.dither_enabled&& ...
        strcmp(p.calibration_mode,'off'),'normalCase:decodeConfig','Unexpected public DecodeP.');
    code=zeros(size(raw,1),1);
    for k=1:size(raw,1)
        w=raw(k,:);c=floor(double(w(1))/32);d1Units=2*double(w(1))-32*c;
        d2=double(bitget(uint32(w(2)),12:-1:1)).';dt=double(bitget(uint32(w(3)),8:-1:1)).';
        d1V=(d1Units-1039)*(p.vref_v/1024)+p.d1_bias_v;
        d2Weighted=reshape(p.d2_weights_ra_v,1,12)*d2;
        d2V=(d2Weighted+p.d2_offset_ra_v)*(1/p.ra_gain);
        dtBipolar=2*((8:-1:1)*dt)-36;
        dtV=dtBipolar*(p.tracking_step_ra_v/(8*p.ra_gain));
        v=((d1V+d2V)+dtV)+0;
        code(k)=max(0,min(2^20-1,round(v*(2^20/p.fsr_diff_v)+2^19)));
    end
end
function x=read_json(file),sha(file);x=jsondecode(fileread(file));end
function h=sha(file)
    d=dir(file);assert(isscalar(d)&&~d.isdir&&d.bytes<=300000000,'normalCase:size','Missing or oversized: %s',file);
    f=fopen(file,'rb');assert(f>=0,'normalCase:read','Cannot read: %s',file);c=onCleanup(@()fclose(f)); %#ok<NASGU>
    x=fread(f,Inf,'*uint8');md=java.security.MessageDigest.getInstance('SHA-256');md.update(typecast(x(:),'int8'));
    h=lower(reshape(dec2hex(typecast(md.digest(),'uint8'),2).',1,[]));
end
function x=canon(p),x=strrep(char(java.io.File(char(p)).getCanonicalPath()),'\','/');end
function yes=under(path,root)
    if isempty(path),yes=false;return;end
    a=lower(canon(path));b=lower(canon(root));yes=strcmp(a,b)||startsWith(a,[b '/']);
end
function close_owned(model)
    if ~bdIsLoaded('SarAdc'),return;end
    try,if strcmpi(canon(get_param('SarAdc','FileName')),canon(model))&& ...
            strcmp(get_param('SarAdc','Dirty'),'off')&&strcmp(get_param('SarAdc','SimulationStatus'),'stopped'),close_system('SarAdc',0);end,catch,end
end
function write_new(file,x)
    assert(~isfile(file)&&~isfolder(file),'normalCase:exists','Receipt exists.');
    f=fopen(file,'w','n','UTF-8');assert(f>=0,'normalCase:write','Cannot write receipt.');c=onCleanup(@()fclose(f)); %#ok<NASGU>
    fwrite(f,[jsonencode(x) newline],'char');
end
