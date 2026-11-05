function result=behavior_sample_explain(runPath,id)
%BEHAVIOR_SAMPLE_EXPLAIN Write one Chinese explanation for a single sample.
%
%   r = behavior_sample_explain(runPath, id)     % id defaults to 4
%
% INPUTS (all read from an existing run directory; the model is never loaded)
%   simout.mat      actual SimulationOutput, used for every logged trace
%   parameters.mat  saved P (plan, calibration, decode contract)
%   summary.json    run verdict; only used to confirm the simulation completed
%
% OUTPUT
%   r.markdown      path of the written sample_<id>_explain.md
%   r.*             numeric verdict fields (raw id/epoch, code20, match flag, ...)
%   r.record        the public record chosen for this id/epoch
%   r.frozen        frozen-coefficient diagnostic, when that path was enabled
%   r.bank          Bank verdict, when Bank was enabled
%
% UNITS
%   Voltages V, charge C, time s, frequency Hz. RAW words and code20 are integers.
%
% SCOPE AND HONESTY
%   Everything shown is derived from the saved logs alone. No model state, no RNG,
%   no refitting. The frozen diagnostics are display-only. ADC event names come
%   from the saved adc_groups, while public records carry their own actual
%   record-ready time; the two are reported side by side and never conflated.
%   A sample that is invalid or unmatched is still written out with the reason,
%   rather than omitted.
    if nargin<2,id=4;end
    assert(isnumeric(id)&&isreal(id)&&isscalar(id)&&isfinite(id)&&id>=0&&id==floor(id), ...
        'BehaviorExplain:id','Sample ID must be a nonnegative integer.');
    runPath=char(runPath);
    a=load(fullfile(runPath,'simout.mat'),'simout');
    b=load(fullfile(runPath,'parameters.mat'),'P');
    meta=jsondecode(fileread(fullfile(runPath,'summary.json')));
    P=b.P;
    out=a.simout;

    assert(isfield(meta,'simulation_completed')&&meta.simulation_completed&& ...
        isa(out,'Simulink.SimulationOutput')&&isempty(out.ErrorMessage), ...
        'BehaviorExplain:run', ...
        'Require an actual completed simulation; its diagnostic verdict may be failed.');

    % Pull the shared per-sample view once; every later block reads from it.
    D=behavior_sample_debug(out,P,id);
    R=D.record;
    groups=D.groups;
    g=D.event(:,2);
    allTime=D.all_time;
    take=D.take;
    t=D.time;
    raw=D.raw;
    ready=D.ready;
    fe=D.front;
    bk=D.back;
    ctrl=D.control;
    latch=D.adc_latch;

    final=raw(latch,:);
    actual=R.code20;
    valid=final(6)==1;
    tagsMatch=final(4)==id && final(5)==P.epoch;

    d1v=R.d1_v;
    d2v=R.d2_v;
    dtv=R.dt_v;

    % Locate named phases by the actual group index; no epsilon time matching.
    cnv=phase_rows(groups,g,'cnv');
    ra=phase_rows(groups,g,'ra_start');
    release=phase_rows(groups,g,'release');
    assert(isscalar(cnv),'BehaviorExplain:cnv','Expected one CNV group.');
    t0=t(cnv);
    held=fe(cnv,1);
    nd2=numel(phase_rows(groups,g,'d2_decide'));
    nta=numel(phase_rows(groups,g,'ta_compare'));
    nfeedback=numel(phase_rows(groups,g,'ta_feedback'));
    % Optional compact diagnostics are read only when they actually exist.
    listed=out.who;
    if isstring(listed)
        listed=cellstr(listed);
    end
    az=D.az;
    route=D.route;
    hasAz=~isempty(az);
    hasRoute=~isempty(route);
    assert(strcmp(P.digital.schema,'sar20-behavior-decode/v1'),'BehaviorExplain:decode', ...
        'Unknown saved public dither/decode contract.');
    dith=public_dither(id,P.digital);
    voltage=((d1v+d2v)+dtv)+dith;
    formula=NaN;
    if isfinite(voltage)
        formula=min(2^20-1,max(0,round(voltage*2^20/P.digital.fsr_diff_v+2^19)));
    end
    nominalVoltage=voltage;
    nominalFormula=formula;
    frozen=D.frozen;
    bank=D.bank;
    if frozen.used
        voltage=frozen.voltage_v;
        formula=min(2^20-1,max(0,round(voltage*2^20/frozen.fsr_v+2^19)));
    end
    match=formula==actual;
    if bank.enabled
        % The logged nominal branches do not expose the Bank's internal equation,
        % so neither a formula nor a match verdict is claimed under Bank.
        formula=NaN;
        match=NaN;
    end
    result=struct('markdown',fullfile(runPath,sprintf('sample_%g_explain.md',id)), ...
        'sample_id',id,'raw_id',final(4),'epoch',final(5),'raw_valid',valid, ...
        'tags_match',tagsMatch,'actual_code20',actual,'formula_code20',formula, ...
        'contribution_identity_matches',match,'AZ_log_present',hasAz,'route_log_present',hasRoute, ...
        'scope','Run-directory logs only; summary hashes do not bind simout; no anti-mixing proof or transport acceptance');
    result.record=R;result.adc_raw_ready_time_s=D.adc_ready_time_s;
    result.actual_record_ready_time_s=R.time_s;
    if frozen.enabled,result.frozen=frozen;end
    if bank.enabled,result.bank=bank;result.nominal_formula_code20=nominalFormula;end
    assert(all(isfield(meta,{'model_sha256','config_sha256'})), ...
        'BehaviorExplain:identity','Actual summary must record model/config SHA.');
    generated=char(datetime('now','TimeZone','UTC','Format','yyyy-MM-dd''T''HH:mm:ss.SSS''Z'''));
    d2Trace=decision_trace(event_rows(groups,g,'d2_decide'),t,t0,raw(:,2),ctrl(:,6),bk(:,2),12);
    taTrace=decision_trace(event_rows(groups,g,'ta_compare'),t,t0,raw(:,3),ctrl(:,7),bk(:,2),8);
    result.model_sha256=char(meta.model_sha256);result.config_sha256=char(meta.config_sha256);
    result.generated_utc=generated;result.d2_observations=d2Trace;result.ta_observations=taTrace;
    result.control_counter_source='Not recorded: Control13 has raw words/flags, no D2/TA/feedback counters';
    % Read only the actual optional tap; disabled one-row/all-NaN logs are not maps.
    adi=struct('enabled',false,'logger_present',any(strcmp(listed,'adi_wire_log')), ...
        'used',false,'reason','P.debug.adi_enabled未开启');
    if isfield(P,'debug')&&isfield(P.debug,'adi_enabled')
        adi.enabled=logical(P.debug.adi_enabled);
    end
    if adi.enabled&&adi.logger_present
        [tw,w]=series(out.get('adi_wire_log'),58,true);
        if isequal(tw,allTime)
            adi=read_adi_map(w(take,:),cnv,t);adi.enabled=true;adi.logger_present=true;
        else,adi.reason='已开启但实际tap时间轴不完整，未生成物理映射表';end
    elseif adi.enabled
        adi.reason='已开启但adi_wire_log缺失，未生成物理映射表';
    end
    result.adi_map=adi;
    if adi.used
        result.control_counter_source=['Control13 has no counters; adi_wire_log52:54 separately ' ...
            'record actual controller counters; the existing tables retain their Control13 column'];
    end
    aperture=aperture_view(out,P,allTime,take,groups,final(4),final(5), ...
        @(ts)series(ts,28,true));
    if aperture.enabled,result.aperture=aperture;end
    lines={};
    add('# Sample ID %.0f：真实日志解释',id);
    add('');
    verdict='ADC原字有效';if ~valid,verdict='**ADC原字无效，仅供诊断**';end
    if ~R.available||~R.valid,verdict=[verdict '；**record缺失/无效，保留观察**'];end
    if bank.enabled&&~bank.valid,verdict=[verdict '；**Bank码未证实有效，仅供诊断**'];end
    status='未记录';if isfield(meta,'status'),status=char(meta.status);end
    add('ID=%.0f，epoch=%.0f，code20=**%.0f**，%s；run=%s；生成UTC：%s。', ...
        final(4),final(5),actual,verdict,status,generated);
    add('模型SHA：`%s`；配置SHA：`%s`。',char(meta.model_sha256),char(meta.config_sha256));
    add('来源边界：仅解释当前run目录内日志；模型和配置SHA抄自summary，本函数未将simout与可信回执哈希绑定，不能证明文件未混档。');
    add('实际run：`%s`。',strrep(runPath,'`',''));
    add('ADC RawReady=%.17g s（距CNV %.9g ns）；公开record=%s，实际时刻=%s s（距CNV %s ns）。', ...
        D.adc_ready_time_s,1e9*(D.adc_ready_time_s-t0),R.readiness_boundary,num(R.time_s),num(1e9*(R.time_s-t0)));
    add('record状态：%s；available=%g、valid=%g；原字与早ADC RawReady逐位相同：%s。', ...
        R.reason,R.available,R.valid,yesno(R.raw_equals_adc));
    if bank.enabled
        add('Bank实际日志：available=%g、RAW范围有效=%s、code_valid=%s、slot=%s、version=%s、fault=%s；%s。', ...
            bank.available,num(bank.raw_words_valid),num(bank.code_valid),num(bank.slot),num(bank.version),num(bank.fault),bank.reason);
    end
    add('');add('| 实际record候选时间 / s | D1 / D2 / DT | ID / epoch / valid | code_log观察值 |');
    add('|---|---|---|---|');
    for j=1:size(R.candidate_raw,1)
        q=R.candidate_raw(j,:);
        add('| %s | %s / %s / %s | %s / %s / %s | %s |', ...
            num(R.candidate_time_s(j)),num(q(1)),num(q(2)),num(q(3)),num(q(4)),num(q(5)),num(q(6)),num(R.candidate_code20(j)));
    end
    if isempty(R.candidate_time_s),add('| 未记录 | 未记录 | 未记录 | 未记录 |');end
    add('缺失、重复、invalid及NaN不由ADC原字填补；表中code是实际观察，valid=0不称有效转换结果。');
    add('');
    add('## 六阶段摘要');add('');
    add('| 阶段 | 距实际CNV / ns | 本次真实观察 |');
    add('|---|---:|---|');
    add('| capture | 0 | held=%s V；CNV日志时间=%.17g s |',num(held),t0);
    if isscalar(ra)
        add('| D1 / 残差 | %.9g | D1=%.0f，coarse=%.0f/fine=%.0f；FrontLog residual=%s V |', ...
            (t(ra)-t0)*1e9,ctrl(ra,5),floor(ctrl(ra,5)/32),mod(ctrl(ra,5),32),num(fe(ra,2)));
    else,add('| D1 / 残差 | 未定位RA-start | 最终D1=%.0f |',final(1));end
    if ~isempty(d2Trace)
        row=d2Trace(1).row;
        add('| RA / 首D2观察 | %.9g | VX=%.15g V，VY=%.15g V，AZdiff=%.15g V |', ...
            (t(row)-t0)*1e9,bk(row,1),bk(row,2),bk(row,7));
    else,add('| RA | 未记录D2关联行 | RawReady VX=%.15g V / VY=%.15g V |',bk(latch,1),bk(latch,2));end
    add('| CT / D2-TA | %.9g | D2=%.0f (`%s`)，DT=%.0f (`%s`) |', ...
        (t(latch)-t0)*1e9,final(2),dec2bin(final(2),12),final(3),dec2bin(final(3),8));
    if bank.enabled
        add('| Bank输出 / 独立record | %s | code_log=%s；record valid=%s；Bank原始code_valid=%s；Bank日志检查综合有效=%s；Bank内部电压未记录 |', ...
            num(1e9*(R.time_s-t0)),num(actual),num(R.raw(6)),num(bank.code_valid),num(double(bank.valid)));
    else
        add('| FPGA重构 / 独立record | %s | Vhat=%s V；code_log=%s；record valid=%s |', ...
            num(1e9*(R.time_s-t0)),num(voltage),num(actual),num(R.raw(6)));
    end
    if isscalar(release)&&hasRoute
        add('| return | %.9g | local Vtop=%.15g V；实际返回=%.15g V；POL=%g |', ...
            (t(release)-t0)*1e9,bk(release,3),route(release,6),route(release,1));
    elseif isscalar(release),add('| return | %.9g | 返回命令探针未记录 |',1e9*(t(release)-t0));
    else,add('| return | 未定位唯一release组 | 不推造返回过程 |');end
    add('');
    add('FPGA record行来自独立数字时间线；RX时刻不是本sample新增的RA/CT/返回端点，物理观察仍为48个ADC事件。');
    add('保存配置：AZ=%s，A0=%g，UGB=%g Hz；kTC flag=%g，DEM flag=%g，dither flag=%g/幅度=%.9g V。', ...
        char(P.backend.az.mode),P.backend.ra.A0,P.backend.ra.UGB_hz,P.front.ktc_enabled, ...
        P.front.dem_enabled,P.digital.dither_enabled,P.digital.dither_amplitude_v);
    if isfield(P.front,'temperature_K'),add('采样温度=%.9g K。',P.front.temperature_K);end
    if hasRoute&&isscalar(ra)
        add('RA-start实际Qres：原始=%.15g C → 已换向命令=%.15g C，公开POL=%g。', ...
            route(ra,2),route(ra,3),route(ra,1));
    end
    if hasAz
        add('RawReady时AZ final-next：AZdiff=%.15g V，valid=%g，pair=%g/epoch=%g，age=%.9g ns，writing=%g，累计writes=%g。', ...
            az(latch,1),az(latch,2),az(latch,3),az(latch,4),az(latch,5)*1e9,az(latch,6),az(latch,7));
    end
    add('');
    if adi.used
        add('');add('## DEM / dither：实际8片映射');add('');
        add('CNV捕获观察t=%.17g s；首次hasDAC观察t=%s s，physicalD1=%s（该时刻DAC trial/反馈命令，不是最终D1）。', ...
            adi.capture_time_s,num(adi.first_dac_time_s),num(adi.physical_d1));
        add('CNV实际active ID/epoch=%s/%s；首次hasDAC实际active ID/epoch=%s/%s；两相实际IDs一致：%s。', ...
            num(adi.capture_tags(1)),num(adi.capture_tags(2)),num(adi.dac_tags(1)),num(adi.dac_tags(2)),yesno(adi.ids_match));
        add('');
        add('| 观察槽 | 实际ID：CNV / 首次DAC | 实际DEM shift | CNV capture tail B / C | 首次DAC signal target / C | physicalD1 |');
        add('|---|---|---:|---:|---:|---:|');
        for j=1:8
            add('| %d | %s / %s | %s | %s | %s | %s |',j, ...
                num(adi.capture_ids(j)),num(adi.dac_ids(j)),num(adi.dem_shift(j)), ...
                num(adi.capture_tail_c(j)),num(adi.dac_signal_target_c(j)),num(adi.physical_d1));
        end
        add('');
        add('来源为同run的adi_wire_log58；槽只表示观察顺序，IDs均来自实际tap，不由plan重建。缺失/NaN原样标记，不以理论电荷填补。');
    end
    add('');
    if aperture.enabled
        add('## Signal孔径：实际8片观察');add('');
        if aperture.used
            add('来源：actual aperture_log28的CNV行/Sample.next353；ID=%g、epoch=%g、valid=%g；事件CNV=%.17g s，日志名义CNV=%.17g s。', ...
                aperture.sample_id,aperture.epoch,aperture.valid,aperture.event_cnv_s,aperture.nominal_cnv_s);
            add('');
            add('| 观察槽 | 实际物理片号 | 实际signal孔径 / s | 孔径−CNV / ps | 实际开采 / s | 开采−CNV / ps |');
            add('|---|---|---|---|---|---|');
            for j=1:8
                add('| %d | %s | %s | %s | %s | %s |',j,num(aperture.physical_ids(j)), ...
                    num(aperture.actual_tap_s(j)),num(aperture.actual_tap_from_cnv_ps(j)), ...
                    num(aperture.acquire_open_s(j)),num(aperture.acquire_open_from_cnv_ps(j)));
            end
            add('');
        else
            add('未生成8片表：%s。',aperture.reason);add('');
        end
        add('signal endpoint aperture端点近似：只移动signal输入的取值孔径；其余事件仍用名义日历，tail/bias预充不随jitter移动。表来自实际日志，未知/NaN标为未记录，不从seed或plan重建。');
        add('');
    end
    add('## 逐次D2：%d条关联观察',numel(d2Trace));add('');trace_table(d2Trace,'D2');
    add('');
    add('## 逐次TA：%d条关联观察',numel(taTrace));add('');trace_table(taTrace,'DT');
    add('实际EventLog行关联的保存日历含%d个D2、%d个TA比较、%d个TA反馈token；不把它们当内部执行计数。',nd2,nta,nfeedback);
    add('');
    if bank.enabled
        add('## 名义支路对照（不是Bank最终码来源）');add('');
    elseif frozen.used
        add('## 冻结候选：实际重构到最终码');add('');
        add('来源：公开record-ready同一实际时刻的frozen_log12；valid=%g，used=%g。', ...
            frozen.diag(10),frozen.diag(11));add('');
        add('| 实际量 | 数值 | 单位 / 来源 |');add('|---|---:|---|');
        add('| u | %.15g | RA域V / diag1 |',frozen.u_ra_v);
        add('| Bh canonical | %.15g | RA域V / diag7 |',frozen.bh_canonical_ra_v);
        add('| den | %.15g | 无量纲 / diag8 |',frozen.den);
        add('| 最终输入参考V | %.15g | V / diag9 |',frozen.voltage_v);add('');
        add('实际线值(u+Bh)/den与diag9的差=%.15g V；最终电压直接取diag9。',frozen.wire_equation_delta_v);
        add('FSR=%.15g V；clip(round(diag9×2^20/FSR+2^19))=%.0f；实际code_log=%.0f；匹配：%s。', ...
            frozen.fsr_v,formula,actual,yesno(match));
        add('冻结h SHA-256（保存cache元数据）：`%s`。',frozen.coefficient_sha256);
        add('');add('## 名义支路对照（不是最终calcode来源）');add('');
    else
        add('## 贡献到最终码');add('');
    end
    add('| 输入参考项 | 贡献 / V | 来源 |');
    add('|---|---:|---|');
    add('| D1 | %.15g | d1_log |',d1v);
    add('| D2 | %.15g | d2_log，已POL恢复 |',d2v);
    add('| DT | %.15g | dt_log，已POL恢复 |',dtv);
    add('| dither | %.15g | 保存数字配置＋公开ID计数规则 |',dith);
    add('');
    if bank.enabled
        add('名义对照V=((%.15g + %.15g) + %.15g) + %.15g = %.15g V；名义公式码=%s；实际Bank code_log=%s。', ...
            d1v,d2v,dtv,dith,nominalVoltage,num(nominalFormula),num(actual));
        add('Bank内部u/Bh/den和最终电压未记录；不将名义分项归因给Bank输出。');
    elseif frozen.used
        add('名义对照V=((%.15g + %.15g) + %.15g) + %.15g = %.15g V；不据此重建最终calcode。', ...
            d1v,d2v,dtv,dith,nominalVoltage);
    else
        add('Vhat=((%.15g + %.15g) + %.15g) + %.15g = %.15g V。', ...
            d1v,d2v,dtv,dith,voltage);
        add('FSR=%.15g V；clip(round(Vhat×2^20/FSR+2^19))=%.0f；实际code_log=%.0f；支路恒等式匹配：%s。', ...
            P.digital.fsr_diff_v,formula,actual,yesno(match));
    end
    add('DT为MSB-first bipolar符号按8…1加权再除8；第8次比较有数字权重，没有第8次物理反馈。D1/dither不随POL翻转。');
    add('');
    add('## 观察来源与归因边界');add('');
    if bank.enabled
        add('- Bank只引用同一record-ready时刻的code_log、valid和meta9；这些不是内部电压探针或产品接受证据。');
    elseif frozen.used
        add('- 冻结候选diag2:6是RA域分组诊断；diag12（分组Bh−canonical）=%.15g V，不用分组和替代canonical Bh，不再另加dither。', ...
            frozen.group_bh_minus_canonical_ra_v);
        add('- h哈希仅抄自本run保存cache；不读actualC、不重算h或fitted weights。本页为日志解释，不表示holdout/校准已验收。');
    elseif frozen.enabled
        add('- 冻结诊断未用于有效恒等式：%s；保留实际record与名义支路观察，不宣称旁路或校准有效。',frozen.reason);
    end
    if adi.used
        add('- 8片表的tail B来自CNV时Sample的下一状态；shift、signal target和physicalD1来自首次hasDAC的DacTrial的下一状态。DAC目标不是实际B建立轨迹，也不是每个电容的开关掩码。');
        add('- tap另含真实控制计数52:54；原20次表的ctrl计数栏特指Control13，未把派生计数填入。');
    else
        add('- ADI映射表未生成：%s；停用的单行NaN日志不算物理观察。',adi.reason);
    end
    add('- EventLog提供实际组号/时间；表中index/bit来自保存ADC groups。VY、raw与ctrl字取该实际行，未由最终字回填历史。');
    add('- Control13=[trial,RAon,active,RawReady,D1raw,D2raw,DTraw,raw_valid,ID,epoch,CNV,release,dac_changed]，没有内部计数；表中计数明确为“未记录”。');
    add('- VY>=0为标准比较块规则派生对照，raw bit从该行实际字拆出；不是另测内部时间戳。异常行保留。');
    add('- BackLog为due/trial后、decide/reset前的actual端点；y.predicted未记录。AZ final-next为RaReset输出/UnitDelay输入、待锁存，不是最终锁存后的独立状态轨迹。');
    add('- FrontLog来自ChargeReturn支路，release行可仍为返回前观察。ReturnContext为decide后、ChargeReturn前的实际命令，仅release消费，非连续物理节点。');
    if hasRoute&&isscalar(release)
        add('- release坐标恢复差=%.15g V（actual return − POL×local probe）。', ...
            route(release,6)-route(release,1)*bk(release,3));
    end
    if ~hasAz,add('- AZ final-next日志未记录，不从日历重建存储状态。');end
    if ~hasRoute,add('- Qres/return命令线未记录，不由残差/POL派生值虚构探针。');end
    if isfield(P,'input')&&all(isfield(P.input,{'offset_v','amplitude_v','frequency_hz','phase_rad'}))
        u=P.input;
        x=u.offset_v+u.amplitude_v*sin(2*pi*u.frequency_hz*t0+u.phase_rad);
        add('- 保存输入配置在CNV时刻的正弦值=%.15g V，只是声明输入计算值，不是独立外部reference。',x);
    end
    add('- kTC、DEM、dither互不等同；零温度/零dither幅度不代表非零激励覆盖。d_n为输入参考V，tail源标度为(1024/15)d_n，预充取负、数字加回一次。');
    add('- 贡献检查仅为DUT日志自洽，不是独立oracle、FFT或校准验收；invalid仍展示。RawReady不证明LVDS/RXready/N−2传输。');
    add('- 数字支路取actual record-ready行：%s；%s；%s。',R.branch_reasons{:});
    add('- ADC RawReady ID/epoch与所选事件及保存P匹配：%s；run verdict=%s。',yesno(tagsMatch),status);
    text=strjoin(lines,newline);
    fid=fopen(result.markdown,'w','n','UTF-8');
    assert(fid>=0,'BehaviorExplain:write','Cannot write sample explanation.');
    closeFile=onCleanup(@()fclose(fid)); %#ok<NASGU>
    count=fprintf(fid,'%s\n',text);
    assert(count>0,'BehaviorExplain:write','No explanation bytes were written.');
    function trace_table(trace,wordName)
        add('| 日历index/bit | 实际组/相对ns | VY / V | 实际%s字 / bit | ctrl同名字 | ctrl计数 | bit=VY>=0* |',wordName);
        add('|---|---|---:|---|---:|---|---|');
        if isempty(trace),add('未记录关联观察，不作符号一致性判断。');return;end
        for j=1:numel(trace)
            q=trace(j);
            mark='';
            if q.word~=q.ctrl_word
                mark='（raw/ctrl不一致）';
            end
            add('| %g/%g | %g / %.9g | %.15g | %.0f / %g | %.0f%s | 未记录 | %s |', ...
                q.index,q.bit_index,q.group,q.relative_ns,q.vy_v,q.word,q.raw_bit,q.ctrl_word,mark,yesno(q.sign_matches));
        end
        add('');
        bad=find(~[trace.sign_matches],1);
        if isempty(bad),add('本表未见raw bit与VY>=0派生符号不一致。');
        else,add('首个符号不一致位于实际group=%g，日历index=%g；保留该行供定位。',trace(bad).group,trace(bad).index);end
    end
    function add(format,varargin)
    % Append one markdown line. Kept nested so the long explanation body can
    % build `lines` without threading it through every helper argument list.
        lines{end+1}=sprintf(format,varargin{:});
    end
end
function [t,x]=series(ts,width,allowNaN)
    assert(isa(ts,'timeseries'),'BehaviorExplain:series','Expected actual timeseries logger.');
    t=double(ts.Time(:));
    d=double(ts.Data);
    if ts.IsTimeFirst
        x=reshape(d,numel(t),[]);
    else
        order=[ndims(d) 1:ndims(d)-1];
        x=reshape(permute(d,order),numel(t),[]);
    end
    finite=isfinite(x);
    if allowNaN
        finite=finite|isnan(x);
    end
    assert(isequal(size(x),[numel(t) width])&&isreal(x)&&all(finite(:))&& ...
        all(isfinite(t))&&all(diff(t)>=0),'BehaviorExplain:shape','Malformed actual logger data.');
end
function rows=phase_rows(groups,g,kind)
% Indices (into g) of the executed groups that contain an event of this type.
% Matches on the event name only; never on a time epsilon.
    rows=[];
    for k=1:numel(g)
        if any(strcmp({groups(g(k)).events.type},kind)),rows(end+1)=k;end %#ok<AGROW>
    end
end
function x=public_dither(id,p)
% Derived public sequence v1 only; it is not a sampled analog/reference trace.
    x=0;
    if ~p.dither_enabled
        return;
    end
    % Park-Miller, advanced by sample id: reproducible from public values only.
    m=uint64(2147483647);
    a=uint64(16807);
    word=uint64(mod(double(p.dither_seed),double(m)-1)+1);
    n=uint64(id+1);
    while n>0
        if bitand(n,uint64(1))~=0
            word=mod(word*a,m);
        end
        a=mod(a*a,m);
        n=bitshift(n,-1);
    end
    x=(floor(4*double(word)/double(m))-1.5)*p.dither_amplitude_v;
end
function text=yesno(value)
    if value,text='是';else,text='否';end
end
function text=num(value)
    if isnan(value),text='未记录（NaN保留）';else,text=sprintf('%.15g',value);end
end

function events=event_rows(groups,g,kind)
    events=zeros(0,4);
    for row=1:numel(g)
        tokens=groups(g(row)).events;
        for j=1:numel(tokens)
            if strcmp(tokens(j).type,kind)
                events(end+1,:)=[row,g(row),tokens(j).index,tokens(j).bit]; %#ok<AGROW>
            end
        end
    end
end
function trace=decision_trace(events,t,t0,word,ctrlWord,vy,width)
    proto=struct('row',0,'group',0,'index',0,'bit_index',0,'time_s',0, ...
        'relative_ns',0,'vy_v',0,'word',0,'raw_bit',0,'ctrl_word',0, ...
        'ctrl_count',NaN,'sign_derived',0,'sign_matches',false);
    trace=repmat(proto,size(events,1),1);
    for j=1:size(events,1)
        r=events(j,1);
        bit=events(j,4);
        assert(bit>=0&&bit<width&&bit==floor(bit)&&word(r)>=0&& ...
            word(r)<2^width&&word(r)==floor(word(r)), ...
            'BehaviorExplain:decisionWord','Invalid recorded word or declared bit index.');
        q=proto;q.row=r;q.group=events(j,2);q.index=events(j,3);q.bit_index=bit;
        q.time_s=t(r);q.relative_ns=(t(r)-t0)*1e9;q.vy_v=vy(r);
        q.word=word(r);q.raw_bit=double(bitget(uint32(word(r)),bit+1));q.ctrl_word=ctrlWord(r);
        q.sign_derived=double(vy(r)>=0);q.sign_matches=q.raw_bit==q.sign_derived;
        trace(j)=q;
    end
end

function map=read_adi_map(w,cnv,t)
% adi-wire58/v1 only: direct named slices of actual tap data, no expected-plan math.
    map=struct('used',true,'reason','','schema','adi-wire58/v1', ...
        'capture_time_s',t(cnv),'capture_ids',w(cnv,1:8), ...
        'capture_tail_c',w(cnv,25:32),'capture_tags',w(cnv,57:58), ...
        'first_dac_time_s',NaN,'dac_ids',nan(1,8),'dem_shift',nan(1,8), ...
        'dac_signal_target_c',nan(1,8),'physical_d1',NaN,'dac_tags',nan(1,2), ...
        'ids_match',false);
    ids=map.capture_ids;
    if ~all(isfinite(ids))||~all(ids>=1&ids<=18&ids==floor(ids))||numel(unique(ids))~=8
        map.used=false;map.reason='CNV实际IDs缺失或非法，未生成8片物理映射表';return;
    end
    first=find(w(:,56)==1,1); % First actual hasDAC, not a guessed calendar offset.
    if ~isempty(first)
        map.first_dac_time_s=t(first);map.dac_ids=w(first,1:8);
        map.dem_shift=w(first,9:16);map.dac_signal_target_c=w(first,17:24);
        map.physical_d1=w(first,55);map.dac_tags=w(first,57:58);
        map.ids_match=all(isfinite(map.capture_ids))&&all(isfinite(map.dac_ids))&& ...
            isequal(map.capture_ids,map.dac_ids);
    end
end

function aperture=aperture_view(out,P,allTime,take,groups,id,epoch,reader)
% aperture-log28: Sample.next353 at actual CNV only; all other rows may be NaN.
% Read saved actual seconds/IDs only. No plan, seed or aperture reconstruction.
    aperture=struct('enabled',false,'used',false,'reason','保存P未启用jitter');
    if ~isfield(P.front,'jitter')||~isfield(P.front.jitter,'enabled')|| ...
            ~P.front.jitter.enabled,return;end
    aperture.enabled=true;
    listed=out.who;
    if isstring(listed)
        listed=cellstr(listed);
    end
    if ~any(strcmp(listed,'aperture_log'))
        aperture.reason='aperture_log未记录';return;
    end
    [ta,z]=reader(out.get('aperture_log'));
    if ~isequal(ta,allTime)
        aperture.reason='实际aperture_log轴不完整或不同轴，未记录本sample孔径';return;
    end
    cnv=[];
    for g=1:numel(groups)
        tokens=groups(g).events;
        if any(strcmp({tokens.type},'cnv')),cnv(end+1)=g;end %#ok<AGROW>
    end
    if ~isscalar(cnv)
        aperture.reason='保存日历未定位唯一实际CNV组，未记录本sample孔径';return;
    end
    z=z(take,:);
    q=z(cnv,:);
    eventTimes=allTime(take);
    if q(3)~=1||q(1)~=id||q(2)~=epoch||~isfinite(q(4))
        aperture.reason='实际CNV行无有效且ID/epoch匹配的孔径记录；不读取其它事件代替';return;
    end
    aperture.used=true;aperture.reason='实际CNV的Sample.next353观察';
    aperture.sample_id=q(1);aperture.epoch=q(2);aperture.valid=q(3);
    aperture.event_cnv_s=eventTimes(cnv);aperture.nominal_cnv_s=q(4);
    aperture.physical_ids=q(5:12);aperture.actual_tap_s=q(13:20);
    aperture.acquire_open_s=q(21:28);
    aperture.actual_tap_from_cnv_ps=(q(13:20)-q(4))*1e12;
    aperture.acquire_open_from_cnv_ps=(q(21:28)-q(4))*1e12;
end
