function [next51,signals,signs] = behavior_control_stage(kind,state51,eventvec2,obs7,cmpvec3,P)
%BEHAVIOR_CONTROL_STAGE v1 (2026-10-27): pure ordered SLX stage adapter.
% Inputs: state51=behavior_sar_pack ABI; event=[zero-based cycle;1-based group];
% obs[7], with sample_v=obs(1), vres_v=obs(2), other five words unconsumed;
% cmp=[native decision1;native decision2;physical vy_V].
% P.control=minimal controller parameters, P.groups=grouped calendar,
% P.Ts_s=CNV period [s], optional P.epoch=1; each run uses one fixed epoch.
% This adapter does not implement runtime global-reset/epoch transitions.
% Outputs: numeric state51; signals[13] in the order stated below; signs[19].
% No DWork/persistent/RNG/I/O. State commits only via the parent numeric delay.
    assert(any(strcmp(kind,{'due','prepare','decide'})), ...
        'behavior:stage:kind','kind must be due, prepare, or decide.');
    assert(isa(eventvec2,'double')&&numel(eventvec2)==2&&all(isfinite(eventvec2(:))), ...
        'behavior:stage:event','event must be finite double[2].');
    portsValid=isnumeric(obs7)&&isreal(obs7)&&numel(obs7)==7&&all(isfinite(obs7(:)))&& ...
        isnumeric(cmpvec3)&&isreal(cmpvec3)&&numel(cmpvec3)==3&&all(isfinite(cmpvec3(:)));
    if ~portsValid
        assert(portsValid,'behavior:stage:ports','Stage %s event %s requires finite obs=%s cmp=%s.', ...
            kind,mat2str(eventvec2(:).'),mat2str(obs7(:).'),mat2str(cmpvec3(:).'));
    end
    assert(isstruct(P)&&isscalar(P)&&all(isfield(P,{'control','groups','Ts_s'})), ...
        'behavior:stage:parameters','P requires control, groups, Ts_s.');
    s=behavior_sar_unpack(state51);
    rawReady=false;
    isCnv=false;
    isRelease=false;
    dacChanged=false;
    cycle=eventvec2(1);
    groupIndex=eventvec2(2);
    if cycle==-1&&groupIndex==0
        [next51,signals,signs]=emit(s,rawReady,isCnv,isRelease,dacChanged);return;
    end
    assert(cycle==floor(cycle)&&cycle>=0&&groupIndex==floor(groupIndex)&& ...
        groupIndex>=1&&groupIndex<=numel(P.groups), ...
        'behavior:stage:indices','Invalid zero-based cycle/one-based group.');
    assert(isscalar(P.Ts_s)&&isfinite(P.Ts_s)&&P.Ts_s>0, ...
        'behavior:stage:period','Ts_s must be finite positive seconds.');
    group=P.groups(groupIndex);
    assert(isfield(group,'time_s')&&isfield(group,'events'), ...
        'behavior:stage:group','Require behavior_event_groups group fields.');
    switch kind
        case 'due',accepted={'fine_feedback','d2_feedback','ta_feedback'};
        case 'prepare',accepted={'cnv','coarse_latch','fine_prepare','ra_start', ...
                'd2_prepare','d2_end','tracking_end'};
        case 'decide',accepted={'fine_decide','d2_decide','ta_compare','raw_latch','release'};
    end
    comparison=struct('sample_v',double(obs7(1)),'vres_v',double(obs7(2)), ...
        'vy_v',double(cmpvec3(3)),'decision1',double(cmpvec3(1)), ...
        'decision2',double(cmpvec3(2)),'valid',true,'late',false);
    epoch=1;if isfield(P,'epoch'),epoch=P.epoch;end
    for k=1:numel(group.events)
        event=group.events(k);
        if ~any(strcmp(event.type,accepted)),continue;end
        event.absolute_time_s=cycle*P.Ts_s+group.time_s;
        event.sample_id=cycle;event.epoch=epoch;
        % Optional comparator input perturbation: pure, keyed by the actual
        % event. Missing/disabled configuration preserves the native bits exactly.
        eventComparison=comparison;
        if strcmp(kind,'decide') && isfield(P.control,'comparator') && ...
                P.control.comparator.enabled && ...
                any(strcmp(event.type,{'fine_decide','d2_decide','ta_compare'}))
            eventComparison=behavior_comparator_sample(event,comparison,P.control.comparator);
        end
        [s,out]=behavior_sar_step(s,event,eventComparison,P.control);
        rawReady=rawReady||out.record_ready;
        isCnv=isCnv||strcmp(event.type,'cnv');
        isRelease=isRelease||strcmp(event.type,'release');
        dacChanged=dacChanged||out.feedback_changed||out.trial_changed;
    end
    [next51,signals,signs]=emit(s,rawReady,isCnv,isRelease,dacChanged);
end

function [next51,signals,signs]=emit(s,ready,cnv,release,changed)
    next51=behavior_sar_pack(s);
    signals=[s.trial;double(s.ra_on);double(s.active);double(ready); ...
        s.d1raw;s.d2raw;s.dtraw;double(s.raw_latched&&~s.overrange); ...
        s.sample_id;s.epoch;double(cnv);double(release);double(changed)];
    signs=[s.d2_signs;s.tracking_signs];
end
