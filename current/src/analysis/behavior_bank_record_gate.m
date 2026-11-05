function B=behavior_bank_record_gate(out,versions,records)
%BEHAVIOR_BANK_RECORD_GATE Public per-record output integrity, not authority.
% Caller provides the actual SimulationOutput, two already-applied versions,
% and exactly public records={raw,time_s}; no P, analog state or references.
% Each selected RAW valid1 must have same-time Bank valid1, fault0, matching
% ID/epoch/valid and slot/version. Any fault in the Bank metadata during this
% run rejects. This check does not qualify h or make a product acceptance.
    assert(isa(out,'Simulink.SimulationOutput')&&isempty(out.ErrorMessage), ...
        'bankRecord:output','Require completed actual simulation output.');
    assert(isstruct(records)&&isscalar(records)&&all(isfield(records,{'raw','time_s'})), ...
        'bankRecord:records','Public RAW6/time required.');
    names=out.who;if isstring(names),names=cellstr(names);end
    assert(all(ismember({'bank_code_valid_log','bank_meta_log'},names)), ...
        'bankRecord:missing','Bank ON requires both actual valid and metadata logs.');
    [tv,valid]=series(out.get('bank_code_valid_log'),1);[tm,meta]=series(out.get('bank_meta_log'),9);
    assert(all(ismember(valid,[0 1]))&&all(ismember(meta(:,8),[0 1]))&&all(meta(:,8)==0), ...
        'bankRecord:fault','Nonbinary valid/fault or actual Bank fault during run.');
    v=at(tv,valid,records.time_s);
    m=at(tm,meta,records.time_s);
    B=behavior_bank_validate_rows(versions,records,v,m);
end
function [t,d]=series(s,width)
    assert(isa(s,'timeseries')&&isa(s.Time,'double')&&isa(s.Data,'double')&& ...
        isreal(s.Time)&&isreal(s.Data),'bankRecord:series','Expected real double timeseries.');
    t=s.Time(:);
    data=s.Data;
    if s.IsTimeFirst
        d=reshape(data,numel(t),[]);
    else
        d=reshape(permute(data,[ndims(data) 1:ndims(data)-1]),numel(t),[]);
    end
    assert(isequal(size(d),[numel(t) width])&&all(isfinite(t))&&all(diff(t)>=0), ...
        'bankRecord:series','Malformed actual Bank timeseries.');
end
function d=at(t,data,wanted)
    [present,index]=ismember(wanted,t);assert(all(present),'bankRecord:time','Bank log lacks an exact selected RX time.');
    for k=1:numel(wanted),assert(nnz(t==wanted(k))==1,'bankRecord:time','Bank log has an ambiguous RX time.');end
    d=data(index,:);
end
