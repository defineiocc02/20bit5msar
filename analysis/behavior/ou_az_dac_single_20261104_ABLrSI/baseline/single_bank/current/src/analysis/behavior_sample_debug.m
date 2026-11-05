function D=behavior_sample_debug(out,P,id)
%BEHAVIOR_SAMPLE_DEBUG Read one ADC trace sample and its public record.
%
%   D = behavior_sample_debug(actualOut, savedP, id)
%
% Times are seconds, voltages are volts. This function is read-only: it never
% touches the model, the RNG, or any file.
%
% WHAT IT RETURNS
%   D.time / D.event        times and event words of the executed ADC groups
%   D.raw / D.ready / D.front / D.back / D.control
%                           the five per-sample logs, aligned on the same times
%   D.adc_raw               the RAW words latched by the ADC for this sample
%   D.record                the public record matching this id/epoch, if unique
%   D.frozen                the frozen-coefficient diagnostic for that record
%   D.bank                  the Bank verdict for that record (when Bank is on)
%
% TWO INDEPENDENT AXES
%   "ADC48 executed" and "record-ready published" are separate facts. A record
%   can exist while the ADC path did not execute, and vice versa. This function
%   reports both and never invents the missing one.
%
% WHAT IT DELIBERATELY DOES NOT DO
%   No interpolation, no held-49 physical rows, no ideal reconstruction, and no
%   acceptance decision. Invalid records stay visible with their reason string
%   so the caller can see exactly why a sample is not usable.

    % ---- Bank configuration ------------------------------------------------
    % Legacy P may omit `bank` entirely. If present it must carry an explicit
    % scalar 0/1; a malformed value is an error, never a silent OFF.
    bankOn=false;
    if isfield(P,'bank')
        assert(isstruct(P.bank)&&isscalar(P.bank)&&isfield(P.bank,'enabled'), ...
            'sampleDebug:bankMode','Present bank requires an explicit scalar enabled flag.');
        flag=P.bank.enabled;
        assert((isnumeric(flag)||islogical(flag))&&isreal(flag)&&isscalar(flag)&& ...
            isfinite(double(flag))&&any(double(flag)==[0 1]), ...
            'sampleDebug:bankMode','Bank enabled must be a real scalar 0 or 1.');
        bankOn=logical(flag);
    end

    versions=[];
    if bankOn
        assert(isfield(P.bank,'slots')&&isstruct(P.bank.slots)&&numel(P.bank.slots)==2&& ...
            isfield(P.bank.slots,'version'),'sampleDebug:bankVersion', ...
            'Enabled Bank requires two explicitly versioned slots.');
        versions=zeros(1,2);
        for k=1:2
            v=P.bank.slots(k).version;
            assert(isnumeric(v)&&isreal(v)&&isscalar(v),'sampleDebug:bankVersion', ...
                'Bank version must be a real numeric scalar.');
            v=double(v);
            assert(isfinite(v)&&v==floor(v)&&v>=1&&v<=2^32-1,'sampleDebug:bankVersion', ...
                'Bank version must be a nonzero uint32-range integer.');
            versions(k)=v;
        end
        assert(versions(1)<versions(2),'sampleDebug:bankVersion', ...
            'Bank slot versions must be strictly increasing.');
    end

    % ---- Which sample groups were actually executed -----------------------
    on=isfield(P,'transport')&&isfield(P.transport,'enabled')&&P.transport.enabled;
    if isfield(P,'adc_groups')
        groups=P.adc_groups;
    else
        assert(~on,'sampleDebug:adcGroups','Transport run requires saved P.adc_groups.');
        groups=P.groups;
    end

    [te,event]=read_log(out,'event_log',2);
    executed=event(:,2)>=1 & event(:,2)<=numel(groups);

    listed=out.who;
    if isstring(listed)
        listed=cellstr(listed);
    end

    if any(strcmp(listed,'parent_event_log'))
        [tp,parent]=read_log(out,'parent_event_log',2);
        pe=at_times(tp,parent,te,'parent_event_log');
        executed=executed & pe(:,2)>=1 & pe(:,2)<=numel(groups);
    end

    allTime=te(executed);
    allEvent=event(executed,:);
    take=allEvent(:,1)==id;
    assert(any(take)&&isequal(allEvent(take,2),(1:numel(groups)).'), ...
        'sampleDebug:ADC48', ...
        ['Require unique executed ADC groups; held49 needs actual ' ...
         'parent_event_log, never deduplicate by value.']);

    D=struct('time',allTime(take),'event',allEvent(take,:),'all_time',allTime, ...
        'take',take,'groups',groups,'transport_enabled',logical(on));

    % ---- Align the five per-sample logs onto the executed times -----------
    names={'raw_log','ready_log','front_log','back_log','control_log'};
    fields={'raw','ready','front','back','control'};
    widths=[6 1 7 8 13];
    for k=1:numel(names)
        [t,x]=read_log(out,names{k},widths(k));
        x=at_times(t,x,allTime,names{k});
        D.(fields{k})=x(take,:);
    end

    assert(all(ismember(D.ready,[0 1])),'sampleDebug:ADCready','ADC Ready is not binary.');
    D.adc_latch=find(D.ready==1);
    assert(isscalar(D.adc_latch),'sampleDebug:ADClatch', ...
        'Require one actual ADC RawReady for this physical sample.');
    D.adc_raw=D.raw(D.adc_latch,:);
    D.adc_ready_time_s=D.time(D.adc_latch);

    % ---- Optional AZ logs (present only in AZ-enabled runs) ---------------
    D.az=[];
    D.route=[];
    for name={'az_commit_log','az_route_log'}
        if any(strcmp(listed,name{1}))
            width=8;
            field='az';
            if strcmp(name{1},'az_route_log')
                width=6;
                field='route';
            end
            [t,x]=read_log(out,name{1},width);
            x=at_times(t,x,allTime,name{1});
            D.(field)=x(take,:);
        end
    end

    % ---- Match the public record for this id/epoch -------------------------
    V=behavior_record_view(out,P);
    matches=find(V.observed_raw(:,4)==id & V.observed_raw(:,5)==P.epoch);
    candidates=find(V.observed_raw(:,4)==id);

    R=struct('available',false,'valid',false,'time_s',NaN,'raw',nan(1,6), ...
        'code20',NaN,'d1_v',NaN,'d2_v',NaN,'dt_v',NaN, ...
        'branch_reasons',{{'无唯一record','无唯一record','无唯一record'}}, ...
        'readiness_boundary',V.readiness_boundary,'reason','未记录同ID/epoch的record', ...
        'candidate_raw',V.observed_raw(candidates,:), ...
        'candidate_time_s',V.observed_ready_time_s(candidates), ...
        'candidate_code20',V.observed_code20(candidates), ...
        'raw_equals_adc',false,'frozen12',[]);

    if numel(matches)>1
        R.reason='同ID/epoch有重复record，未擅选一行';
    end
    if isempty(matches)&&~isempty(candidates)
        R.reason='仅有同ID但epoch不匹配的record';
    end

    if isscalar(matches)
        R.available=true;
        R.time_s=V.observed_ready_time_s(matches);
        R.raw=V.observed_raw(matches,:);
        R.code20=V.observed_code20(matches);
        R.valid=R.raw(6)==1;
        R.raw_equals_adc=words(R.raw,D.adc_raw);
        R.reason='实际record（仍需核valid与码）';

        branchNames={'d1_log','d2_log','dt_log'};
        branchFields={'d1_v','d2_v','dt_v'};
        for k=1:3
            [value,why]=optional_scalar(out,branchNames{k},R.time_s);
            R.(branchFields{k})=value;
            R.branch_reasons{k}=why;
        end

        if V.frozen_enabled
            R.frozen12=V.observed_frozen12(matches,:);
        end
    end
    D.record=R;

    % ---- Frozen-coefficient diagnostic ------------------------------------
    % The frozen path reports its own valid/used flags. We only surface the
    % numbers when the record itself says the decode was used; otherwise the
    % reason string explains why nothing is claimed.
    f=struct('enabled',V.frozen_enabled,'used',false,'reason','未使用实际冻结诊断');
    if V.frozen_enabled&&R.available
        q=R.frozen12;
        f.diag=q;
        f.used=q(10)==1 && q(11)==1 && all(isfinite(q([1 7 8 9]))) && q(8)>0;
        if f.used
            C=P.frozen.cache;
            f.coefficient_sha256=char(C.coefficient_sha256);
            f.fsr_v=2*C.public_cfg.vref_v;
            f.u_ra_v=q(1);
            f.bh_canonical_ra_v=q(7);
            f.den=q(8);
            f.voltage_v=q(9);
            f.group_bh_minus_canonical_ra_v=q(12);
            f.wire_equation_delta_v=(q(1)+q(7))/q(8)-q(9);
            f.reason='实际record时刻的valid/used冻结诊断';
        else
            f.reason='实际record冻结诊断invalid/unused/NaN，未冒充有效calcode';
        end
    elseif V.frozen_enabled
        f.reason='无唯一record，未选择冻结诊断';
    end
    D.frozen=f;

    % ---- Bank verdict ------------------------------------------------------
    % Bank has its own valid/fault/slot/version. RAW validity alone does NOT
    % prove the observed Bank code is valid, and internal u/Bh/den are never
    % invented here.
    b=struct('enabled',bankOn,'available',false,'code_valid',NaN,'fault',NaN, ...
        'slot',NaN,'version',NaN,'tags_match',false,'version_match',false, ...
        'raw_words_valid',NaN,'valid',false,'meta9',nan(1,9),'reason','Bank未启用');

    if bankOn
        b.reason='Bank日志或唯一record缺失；不将code_log视为有效Bank码';

        if R.available
            word=R.raw(1:3);
            b.raw_words_valid=all(isfinite(word)) && all(word==floor(word)) && ...
                all(word>=0) && all(word<=[2047 4095 255]);
        end

        if R.available&&all(ismember({'bank_code_valid_log','bank_meta_log'},listed))
            [tv,v]=read_log(out,'bank_code_valid_log',1);
            [tm,m]=read_log(out,'bank_meta_log',9);
            iv=find(tv==R.time_s);
            im=find(tm==R.time_s);

            if isscalar(iv)&&isscalar(im)
                b.available=true;
                b.code_valid=v(iv);
                b.meta9=m(im,:);
                b.slot=b.meta9(6);
                b.version=b.meta9(7);
                b.fault=b.meta9(8);
                b.tags_match=b.meta9(2)==R.time_s && isequal(b.meta9(3:5),R.raw(4:6));
                if ismember(b.slot,[1 2])
                    b.version_match=b.version==versions(b.slot);
                end

                goodCode=isfinite(R.code20) && R.code20==floor(R.code20) && ...
                    R.code20>=0 && R.code20<2^20;
                b.valid=R.valid && b.raw_words_valid && b.code_valid==1 && ...
                    b.fault==0 && b.tags_match && b.version_match && goodCode;
                b.reason='Bank行缺失有效性、标识、版本或无fault条件；仅供诊断';

                if ~b.raw_words_valid
                    b.reason='record的D1/D2/DT非有限、非整数或超范围；仅供诊断';
                elseif b.valid
                    b.reason='同record时刻的RAW及Bank valid/tag/version/fault已对齐';
                end
            else
                b.reason='Bank日志在record时刻缺失或重复；仅供诊断';
            end
        end
    end
    D.bank=b;
end

% =========================================================================
% Local helpers
% =========================================================================

function [t,x]=read_log(out,name,width)
% Pull one logger as a [nSamples x width] numeric matrix.
    listed=out.who;
    if isstring(listed)
        listed=cellstr(listed);
    end
    assert(any(strcmp(listed,name)),'sampleDebug:missing','Missing actual logger %s.',name);
    s=out.get(name);
    assert(isa(s,'timeseries'),'sampleDebug:logger','Expected timeseries %s.',name);
    t=double(s.Time(:));
    d=double(s.Data);
    if s.IsTimeFirst
        x=reshape(d,numel(t),[]);
    else
        x=reshape(permute(d,[ndims(d) 1:ndims(d)-1]),numel(t),[]);
    end
    assert(isequal(size(x),[numel(t) width]) && isreal(x) && all(isfinite(t)) && ...
        all(diff(t)>=0) && all(isfinite(x)|isnan(x),'all'), ...
        'sampleDebug:shape','Malformed actual logger %s.',name);
end

function x=at_times(t,data,wanted,label)
% Reorder logger rows to `wanted` times; every wanted time must be unique.
    [found,index]=ismember(wanted,t);
    assert(all(found),'sampleDebug:time','Missing exact actual ADC time in %s.',label);
    for k=1:numel(wanted)
        assert(nnz(t==wanted(k))==1,'sampleDebug:time', ...
            'Ambiguous actual time in %s.',label);
    end
    x=data(index,:);
end

function [x,reason]=optional_scalar(out,name,t)
% Read a one-word logger row at time t; returns NaN and a reason when absent.
    x=NaN;
    reason=[name '未记录消费时刻'];
    listed=out.who;
    if isstring(listed)
        listed=cellstr(listed);
    end
    if ~any(strcmp(listed,name))
        return;
    end
    [ta,data]=read_log(out,name,1);
    row=find(ta==t);
    if ~isscalar(row)
        return;
    end
    x=data(row);
    reason=[name ' actual record-ready行'];
end

function yes=words(a,b)
% Bit-exact comparison of two RAW word vectors.
    yes=isequal(size(a),size(b)) && ...
        isequal(typecast(a(:),'uint64'),typecast(b(:),'uint64'));
end
