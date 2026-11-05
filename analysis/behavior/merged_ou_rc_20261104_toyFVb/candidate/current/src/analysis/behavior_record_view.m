function V=behavior_record_view(out,P)
%BEHAVIOR_RECORD_VIEW Extract the public record stream from saved logs.
%
%   V = behavior_record_view(out, savedP)
%
% Pure IO boundary: no model run, no state, no fit, no interpolation, no RNG.
%
% INPUTS
%   out      actual SimulationOutput
%   savedP   saved P; N/first_id/epoch define the window, transport.enabled
%            selects the log source, training.reference/frozen.enabled pull the
%            optional reference and frozen diagnostics
%
% LOG SOURCES
%   New graph      record_log / record_ready_log   (public RX records)
%   Legacy runs    raw_log / ready_log             (ADC raw/ready, transport off)
%   A transport-enabled run MUST have the record logs; ADC raw/ready are not RX
%   records, so mixing them is rejected rather than silently accepted.
%
% OUTPUT V
%   V.raw, V.code20, V.time_s      records inside the [first_id, first_id+N) window
%   V.observed_raw/_code20/_ready_time_s
%                                  every observed record, window or not
%   V.readiness_boundary           'direct_raw' or 'serial_rx_n_minus_2'
%   V.reference_* / V.frozen_*     optional diagnostics, joined on exact ready times
%
% UNITS
%   RAW6 = [D1,D2,DT,ID,epoch,valid]; code20 unsigned 20-bit; times s; Ref4 V.
%
% Preserved intentionally: selected invalid/NaN words are NOT filtered out here.
% Acceptance and validity gating belong to the caller, so a failing sample still
% shows up in explanations instead of vanishing.
    assert(isa(out,'Simulink.SimulationOutput')&&isempty(out.ErrorMessage), ...
        'recordView:output','Require actual error-free Simulink output.');
    assert(isstruct(P)&&isscalar(P)&&all(isfield(P,{'N','first_id','epoch'})), ...
        'recordView:savedP','Pass the actual saved P, including transport mode.');
    on=isfield(P,'transport')&&isfield(P.transport,'enabled')&&P.transport.enabled;
    listed=out.who;
    if isstring(listed)
        listed=cellstr(listed);
    end
    % The new graph logs public RX records; legacy runs log ADC raw/ready instead.
    hasRaw=any(strcmp(listed,'record_log'));
    hasReady=any(strcmp(listed,'record_ready_log'));
    assert(hasRaw==hasReady,'recordView:partial','record_log and record_ready_log must both exist.');
    legacy=~hasRaw;
    assert(~(on&&legacy),'recordView:transportMissing', ...
        'Transport on requires actual record logs; ADC raw/ready are not RX records.');
    rawName='record_log';
    readyName='record_ready_log';
    if legacy
        rawName='raw_log';
        readyName='ready_log';
    end
    [tr,raw]=read_log(out,rawName,6);
    [tq,ready]=read_log(out,readyName,1);
    [tc,code]=read_log(out,'code_log',1);
    assert(all(ismember(ready,[0 1])),'recordView:ready','Actual record ready must be binary.');
    times=tq(ready==1);
    assert(numel(unique(times))==numel(times),'recordView:duplicateTime','Repeated actual ready time.');
    observed=at_times(tr,raw,times,rawName);
    observedCode=at_times(tc,code,times,'code_log');
    window=observed(:,4)>=P.first_id&observed(:,4)<P.first_id+P.N;
    rr=observed(window,:);
    cc=observedCode(window);
    rt=times(window);
    % Preserve selected invalid/NaN words. Acceptance, N/order/valid and code
    % gates belong to the caller; sample explanations must still show failures.
    boundary='direct_raw';
    if on
        boundary='serial_rx_n_minus_2';
    end
    V=struct('raw',rr,'code20',cc,'time_s',rt,'readiness_boundary',boundary, ...
        'legacy',legacy,'raw_log_source',rawName,'ready_log_source',readyName, ...
        'reference_enabled',false,'ref4',[],'observed_ref4',[],'reference_log_source','', ...
        'frozen_enabled',false,'frozen12',[],'observed_frozen12',[], ...
        'observed_ready_time_s',times,'observed_raw',observed,'observed_code20',observedCode);
    refOn=isfield(P,'training')&&isfield(P.training,'reference')&& ...
        isfield(P.training.reference,'enabled')&&P.training.reference.enabled;
    if refOn
        refName='paired_ref_log';
        if legacy
            refName='train_ref_log';
        end
        [tf,ref]=read_log(out,refName,4);
        allRef=at_times(tf,ref,times,refName);
        V.reference_enabled=true;
        V.ref4=allRef(window,:);
        V.observed_ref4=allRef;
        V.reference_log_source=refName;
    end
    frozenOn=isfield(P,'frozen')&&isfield(P.frozen,'enabled')&&P.frozen.enabled;
    if frozenOn
        [td,diag]=read_log(out,'frozen_log',12);
        allDiag=at_times(td,diag,times,'frozen_log');
        V.frozen_enabled=true;
        V.frozen12=allDiag(window,:);
        V.observed_frozen12=allDiag;
    end
end
function [t,x]=read_log(out,name,width)
    listed=out.who;
    if isstring(listed)
        listed=cellstr(listed);
    end
    assert(any(strcmp(listed,name)),'recordView:missing','Missing actual logger %s.',name);
    s=out.get(name);
    assert(isa(s,'timeseries'),'recordView:logger','Actual %s is not timeseries.',name);
    t=double(s.Time(:));
    d=double(s.Data);
    if s.IsTimeFirst
        x=reshape(d,numel(t),[]);
    else
        x=reshape(permute(d,[ndims(d) 1:ndims(d)-1]),numel(t),[]);
    end
    assert(isequal(size(x),[numel(t) width])&&isreal(x)&&all(isfinite(t))&& ...
        all(diff(t)>=0),'recordView:shape','Malformed actual logger %s.',name);
    % Non-consumed rows may contain startup/disabled NaN. Selection validates
    % real public records; it never turns those diagnostics into valid samples.
end
function x=at_times(t,data,wanted,name)
    [present,index]=ismember(wanted,t);
    assert(all(present),'recordView:time','%s lacks an exact actual ready timestamp.',name);
    for k=1:numel(wanted)
        assert(nnz(t==wanted(k))==1,'recordView:ambiguousTime', ...
            '%s has repeated rows at one actual ready timestamp.',name);
    end
    x=data(index,:);
end
