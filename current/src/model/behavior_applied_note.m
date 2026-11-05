function report=behavior_applied_note(action,model)
%BEHAVIOR_APPLIED_NOTE Visible applied-P snapshot; no model computation/state.
% v1 2026-10-27. apply: call update after assigning P/DecodeP, before saving.
% run: call check before sim; this only reads P/labels, never factory or SATK.
% update discovers IDs with model_read and configures existing block annotations.
    assert(any(strcmp(action,{'update','check'})),'adc:noteAction','Use update or check.');
    assert(bdIsLoaded(model)&&strcmp(get_param(model,'SimulationStatus'),'stopped'), ...
        'adc:noteModel','Expected the loaded stopped target model.');
    names={'Driver','EventStep','Adc','Fpga'};
    paths={[model '/Driver'],[model '/EventStep'], ...
        [model '/EventStep/Adc'],[model '/EventStep/Fpga']};
    ws=get_param(model,'ModelWorkspace');P=getVariable(ws,'P');
    assert(strcmp(P.backend.az.mode,P.digital.az_mode)&& ...
        logical(P.backend.ni.az)==~strcmp(P.backend.az.mode,'off'), ...
        'adc:noteMode','Applied analog/digital AZ settings disagree.');
    k=ktc_text(P.front);
    note=sprintf(['已应用 P | N=%d | Fs=%.6g MS/s\n' ...
        'AZ=%s | kTC=%s\n' ...
        'DEM=%s | dither=%s | RA A0=%g(%s), UGB=%g Hz(%s)\n' ...
        '%s\n' ...
        '%s\n' ...
        '%s\n' ...
        '%s\n' ...
        '内部:片内 ADC → 片外 FPGA / Raw接口；Run用保存P，改参数先apply'], ...
        P.N,1e-6/P.Ts_s,char(P.backend.az.mode),k, ...
        dem_text(P.front.dem_enabled),dither_text(P.front), ...
        P.backend.ra.A0,finite_text(P.backend.ra.A0), ...
        P.backend.ra.UGB_hz,finite_text(P.backend.ra.UGB_hz),dac_text(P),cal_text(P),aperture_text(P.front),transport_text(P));
    if isfield(P.front,'single_bank')&&P.front.single_bank
        note=strrep(note,' | Bank=',' | 数字系数Bank=');
        cArray=sum(P.front.group_C_f(1:8,:),'all');
        note=[note sprintf('\n前端: 单bank(8数值分段) | guard=%.6g ns | C阵列=%.6g pF/半(口径假设)', ...
            P.front.single_guard_s*1e9,cArray*1e12)];
    end
    % Leave the pre-existing OFF note byte-for-byte untouched. ON/zero input
    % displays the actual prepared P and is separately validated by the guard.
    if isfield(P.backend.ni,'ra_noise')&&P.backend.ni.ra_noise
        note=[note ra_noise_suffix(P)];
    end
    % Optional comparator profile is visible; absent profile keeps prior text.
    if isfield(P.control,'comparator')
        behavior_comparator_configuration(P,'check');
        c=P.control.comparator;seedHex=upper(dec2hex(c.seed_u64,16));
        note=[note sprintf(['\nCMP=%s | SAR1 fine offset=%.17g V, sigma=%.17g V rms' ...
            '\nSAR2/TA offset=%.17g V, sigma=%.17g V rms' ...
            '\nFlash comparator noise not modeled | seed=0x%s | tie=%d'], ...
            flagtext(c.enabled),c.sar1_offset_v,c.sar1_noise_rms_v, ...
            c.sar2_offset_v,c.sar2_noise_rms_v,seedHex,double(c.tie_decision))];
    end
    texts={'片外 Driver：输入源配置 [V,Hz,rad]',note, ...
        '片内 ADC：Sample / DAC / RA-AZ / CT / SAR-Tracking', ...
        fpga_text(P)};
    if strcmp(action,'update')
        projectRoot=project_root();
        tools=fullfile(projectRoot,'dependencies','toolkit','tools');
        oldPath=path;restorePath=onCleanup(@()path(oldPath)); %#ok<NASGU>
        addpath(fullfile(tools,'common'),fullfile(tools,'common','autolayout'), ...
            fullfile(tools,'model_read'),fullfile(tools,'model_edit'),fullfile(tools,'model_check'));
        gateReady=false;scope='root';lastReply='';
        try
            gate=library.settingsLookup();
            assert(~gate.found||gate.gatePass,'adc:noteLibraryGate','SATK library policy failed.');
            gateReady=true;
            rootView=model_read(model,'root','0');lastReply=rootView;okay(rootView,'read');
            ids=cell(1,4);
            ids{1}=view_id(rootView,model,paths{1});
            ids{2}=view_id(rootView,model,paths{2});
            scope=ids{2};
            innerView=model_read(model,scope,'0');lastReply=innerView;okay(innerView,'read');
            ids{3}=view_id(innerView,model,paths{3});
            ids{4}=view_id(innerView,model,paths{4});
            scopes={'root',ids{2}};sets={1:2,3:4};
            for n=1:2
                ops=cell(1,2);
                for j=1:2
                    index=sets{n}(j);
                    ops{j}=struct('op','configure','target',ids{index}, ...
                        'params',struct('AttributesFormatString',texts{index}));
                end
                scope=scopes{n};
                result=model_edit(model,scope,jsonencode(ops),'incremental');
                lastReply=result;okay(result,'edit');
            end
            verify_notes(model,names,paths,texts);
        catch cause
            try
                folder=diagnose(model,projectRoot,scope,lastReply,P,gateReady,cause);
            catch diagnosticCause
                error('adc:noteDiagnosticWrite', ...
                    'Note update failed: %s\nDiagnostic capture also failed: %s', ...
                    getReport(cause,'extended','hyperlinks','off'), ...
                    getReport(diagnosticCause,'extended','hyperlinks','off'));
            end
            failure=MException('adc:noteUpdateFailed', ...
                'Applied-note update failed; actual read/check diagnostics saved in %s',folder);
            failure=addCause(failure,cause);throw(failure);
        end
    end
    if strcmp(action,'check'),verify_notes(model,names,paths,texts);end
    report=struct('status','applied_note_matches_P','action',action, ...
        'source','ModelWorkspace.P','text',note,'factory_called',false, ...
        'scope','displayed configuration fields; not noise/coverage acceptance');
end
function id=view_id(view,model,path)
    candidates=unique(regexp(char(view),'blk_[0-9]+','match'),'stable');
    found={};
    for n=1:numel(candidates)
        full=Simulink.ID.getFullName([model ':' extractAfter(candidates{n},'blk_')]);
        if strcmp(full,path),found{end+1}=candidates{n};end %#ok<AGROW>
    end
    assert(numel(found)==1,'adc:noteDiscovery', ...
        'model_read must identify exactly one block at %s.',path);
    id=found{1};
end
function text=ktc_text(front)
    enabled=logical(front.ktc_enabled);T=[];seed=[];
    if isfield(front,'temperature_K'),T=front.temperature_K;end
    if isfield(front,'ktc_seed'),seed=front.ktc_seed;end
    if enabled
        assert(isscalar(T)&&isfinite(T)&&T>=0&&isscalar(seed)&& ...
            isfinite(seed)&&seed>=0&&seed==floor(seed), ...
            'adc:noteKtc','kTC requires applied temperature_K and ktc_seed.');
        if T>0&&isfield(front,'single_bank')&&front.single_bank&& ...
                isfield(front,'tau_sample_s')&&isinf(front.tau_sample_s(1))
            text=sprintf('OFF注入(采样保持, flag=1), seed=%.0f',seed);
        elseif T>0,text=sprintf('ON, T=%.6g K, seed=%.0f',T,seed);
        else,text=sprintf('OFF注入(T=0对照, flag=1), seed=%.0f',seed);end
    elseif ~isempty(T)&&~isempty(seed)
        text=sprintf('OFF, T=%.6g K, seed=%.0f',T,seed);
    else
        text='OFF (温度/seed未配置)';
    end
end
function text=ra_noise_suffix(P)
% A model assumption; do not imply measured noise or calibration acceptance.
    behavior_ra_noise_guard(P);
    q=P.backend.ra_noise;
    if q.sigma_vx_rms>0,coverage='已启用（行为假设）';
    else,coverage='零激励，不计噪声覆盖';end
    if isinf(P.control.sar2.limit_v),coverage=[coverage ' | SAR2过量程检测关闭(+Inf)'];end
    seedHex=upper(dec2hex(q.seed_u64,16));
    text=sprintf('\nRA OU=ON | sigmaVX(差分VX固定极点稳态RMS)=%.17g V rms | seed=0x%s | %s', ...
        q.sigma_vx_rms,seedHex,coverage);
end
function text=flagtext(value)
    assert(isscalar(value)&&ismember(value,[0 1]),'adc:noteFlag','Expected an applied boolean flag.');
    if value,text='ON';else,text='OFF';end
end
function text=dem_text(value)
% Existing DEM rotates only the 31 whole groups by ID/epoch/slice/seed.
% This is neither independent random selection nor a DWA accumulator.
    text=flagtext(value);
    if value,text='ON 循环移位31组(非独立随机/非DWA)';end
end
function text=dither_text(front)
% a_in is the declared input-reference scale, not tail voltage or a fitted
% per-bank analog amplitude. Levels are [-1.5,-0.5,0.5,1.5]*a_in; tail scale
% is (1024/15)*d_n, precharge is negative, digital addback is +d_n once.
    text=flagtext(front.dither_enabled);
    if ~front.dither_enabled,return;end
    a=front.dither_input_amplitude_v;
    assert(isnumeric(a)&&isreal(a)&&isscalar(a)&&isfinite(a)&&a>=0, ...
        'adc:noteDither','Expected nonnegative input-reference dither amplitude in V.');
    if a==0,text='OFF注入(零激励对照; flag=1, a_in=0 V)';
    else,text=sprintf('ON a_in=%.6g V (四电平峰值=%.6g V)',a,1.5*a);end
end
function text=finite_text(value)
    assert(isscalar(value)&&isreal(value)&&value>0,'adc:noteRA','Expected positive RA value or Inf.');
    if isfinite(value),text='有限';else,text='理想Inf';end
end
function okay(result,kind)
    firstLine=strtrim(strtok(char(result),newline));
    assert(any(strcmp(firstLine,{'status: ok','status: success','status: healthy'})), ...
        'adc:noteSATK','SATK %s failed: %s',kind,char(result));
end

function root=project_root()
% Runtime file may live directly under current/src or one named subdirectory.
    root=fileparts(mfilename('fullpath'));
    while ~(isfile(fullfile(root,'SAR20.m'))&& ...
            isfolder(fullfile(root,'dependencies','toolkit','tools')))
        parent=fileparts(root);
        assert(~strcmp(root,parent)&&~isempty(parent),'adc:noteProjectRoot', ...
            'Install this helper beneath the intended SAR20 project with dependencies/toolkit.');
        root=parent;
    end
end
function folder=diagnose(model,root,scope,lastReply,P,gateReady,cause)
% Preserve real responses even if one diagnostic operation itself fails.
    runs=fullfile(root,'runs');if ~isfolder(runs),mkdir(runs);end
    folder=fullfile(runs,['note_diagnostic_' char(java.util.UUID.randomUUID())]);mkdir(folder);
    diag=struct('model',model,'scope',scope,'model_file',get_param(model,'FileName'), ...
        'dirty',get_param(model,'Dirty'),'last_reply',char(lastReply), ...
        'error',getReport(cause,'extended','hyperlinks','off'),'P',P, ...
        'library_gate_passed',gateReady);
    if gateReady
        try,diag.model_read=char(model_read(model,scope,'inf'));
        catch e,diag.model_read_error=getReport(e,'extended','hyperlinks','off');end
        try,diag.model_check=char(model_check(model,scope,'["unconnected_ports","unconnected_lines"]'));
        catch e,diag.model_check_error=getReport(e,'extended','hyperlinks','off');end
    end
    save(fullfile(folder,'diagnostic.mat'),'diag','-v7');
    fields={'error','last_reply','model_read','model_read_error','model_check','model_check_error'};
    for k=1:numel(fields)
        if isfield(diag,fields{k})
            fid=fopen(fullfile(folder,[fields{k} '.txt']),'w','n','UTF-8');
            assert(fid>=0,'adc:noteDiagnosticWrite','Cannot write diagnostic file.');
            closeFile=onCleanup(@()fclose(fid)); %#ok<NASGU>
            fprintf(fid,'%s',diag.(fields{k}));clear closeFile;
        end
    end
end

function verify_notes(model,names,paths,texts)
    for n=1:4
        % Exact paths and actual SIDs are read afresh; no cached block IDs/state.
        assert(strcmp(get_param(paths{n},'Name'),names{n})&& ...
            startsWith(Simulink.ID.getSID(paths{n}),[model ':']), ...
            'adc:noteBlock','Expected exact block %s.',paths{n});
        assert(strcmp(get_param(paths{n},'AttributesFormatString'),texts{n}), ...
            'adc:staleAppliedNote', ...
            'Visible configuration differs from applied P; use consistent apply before run.');
    end
end

function text=cal_text(P)
% Missing legacy fields mean off; only saved applied-P flags/hash are displayed.
    train=false;frozen=false;reference=false;h='未记录';
    if isfield(P,'training')
        if isfield(P.training,'enabled'),train=logical(P.training.enabled);end
        if isfield(P.training,'reference')&&isfield(P.training.reference,'enabled')
            reference=logical(P.training.reference.enabled);
        end
    end
    if isfield(P,'frozen')
        if isfield(P.frozen,'enabled'),frozen=logical(P.frozen.enabled);end
        if frozen&&isfield(P.frozen,'cache')&&isstruct(P.frozen.cache)&& ...
                isfield(P.frozen.cache,'coefficient_sha256')
            hash=char(P.frozen.cache.coefficient_sha256);h=hash(1:min(12,numel(hash)));
        end
    end
    bank=false;
    if isfield(P,'bank')&&isstruct(P.bank)&&isscalar(P.bank)&&isfield(P.bank,'enabled')
        value=P.bank.enabled;assert(isscalar(value)&&ismember(value,[0 1]),'adc:noteBank','Expected an applied Bank flag.');
        bank=logical(value);
    end
    states={'OFF','ON'};
    text=sprintf('Train=%s | Frozen=%s | Ref=片外仪器(%s) | Bank=%s', ...
        states{1+train},states{1+frozen},states{1+reference},states{1+bank});
    if frozen,text=sprintf('%s | h=%s',text,h);end
    if bank,text=sprintf('%s (同h双版本行为级；非验收)',text);end
end

function text=aperture_text(front)
% Saved signal endpoint aperture parameters only; never modifies event timing.
    text='signal aperture=OFF (非全时钟抖动)';
    if ~isfield(front,'jitter')||~isfield(front.jitter,'enabled')|| ...
            ~front.jitter.enabled,return;end
    j=front.jitter;
    if ~all(isfield(j,{'common_sigma_s','local_sigma_s','fixed_slice_skew_s'}))
        text='signal aperture=OFF(参数未完整记录; flag=1; 非全时钟抖动)';return;
    end
    common=1e12*j.common_sigma_s;local=1e12*j.local_sigma_s;
    skew=1e12*max(abs(j.fixed_slice_skew_s(:)));
    if common==0&&local==0&&skew==0
        state='OFF注入(零激励对照; flag=1)';
    else,state='ON';end
    text=sprintf('signal aperture=%s | common RMS=%g ps, local RMS=%g ps, max|skew|=%g ps (非全时钟抖动)', ...
        state,common,local,skew);
end

function text=transport_text(P)
% v1 2026-10-27: display saved public transport mode; legacy P means off.
    on=isfield(P,'transport')&&isfield(P.transport,'enabled')&&logical(P.transport.enabled);
    if on,text='transport=true | on RX N−2, sample+538 ns';
    else,text='transport=false | off ADC RawReady';end
end
function text=fpga_text(P)
% Display boundary only; no mode normalization or apply/check guard change.
    on=isfield(P,'transport')&&isfield(P.transport,'enabled')&&logical(P.transport.enabled);
    if on,text='片外 FPGA：RX Raw重构 | N−2, sample+538 ns；非LVDS电气/CDC签核';
    else,text='片外 FPGA：公开Raw重构 | off ADC RawReady；开关显示不代表扫描覆盖';end
end

function text=dac_text(P)
% Display configured physical-slice tau only; this is not a simulation/coverage verdict.
    on=isfield(P.backend,'dac_coupling')&&isfield(P.backend.dac_coupling,'enabled')&& ...
        logical(P.backend.dac_coupling.enabled);
    states={'OFF','ON'};flag=states{1+on};
    if ~isfield(P.front,'tau_dac_s')
        text=sprintf('DAC建立耦合=%s | tau未记录（不计覆盖）',flag);return;
    end
    t=P.front.tau_dac_s;
    if ~isnumeric(t)||~isreal(t)||numel(t)~=18||any(isnan(t(:)))||any(t(:)<0)
        text=sprintf('DAC建立耦合=%s | tau[18]未完整记录（不计覆盖）',flag);return;
    end
    t=t(:);finite=t(isfinite(t)&t>0);holds=sum(isinf(t));
    if all(t==0)
        text=sprintf('DAC建立耦合=%s | tau=0 ns 理想即时（不计有限建立NI）',flag);
    elseif isempty(finite)
        text=sprintf('DAC建立耦合=%s | Inf保持负例=%d/18（无正有限tau，不计finite覆盖）',flag,holds);
    else
        text=sprintf('DAC建立耦合=%s | 正有限tau=%g..%g ns (%d/18), Inf保持=%d', ...
            flag,1e9*min(finite),1e9*max(finite),numel(finite),holds);
        if ~on,text=[text '（耦合OFF，不计耦合覆盖）'];end
    end
end
