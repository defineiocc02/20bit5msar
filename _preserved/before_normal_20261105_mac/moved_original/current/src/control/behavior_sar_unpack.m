function s = behavior_sar_unpack(x)
%BEHAVIOR_SAR_UNPACK Restore named digital controller state from 51 words.
%Version: v1 (2026-10-27). Caller: SAR adapter before behavior_sar_step.
%Input x[51] finite real double; output s, inverse of behavior_sar_pack.
%Units: sample_v [V], pending.due_s [s]; remaining words unitless flags/tags/counts.
%Pure ABI inverse, not CNV/reset initialization; no hidden state/RNG/analog update.
%Model decisions and reset priorities remain in behavior_sar_step.
    assert(isa(x,'double')&&isreal(x)&&numel(x)==51&&all(isfinite(x(:))), ...
        'behavior:unpack:state','Require finite real double state[51].');
    x=x(:);
    fields={'active','sample_id','epoch','bank','sample_v','coarse','coarse_latched', ...
        'trial','d1raw','d1_feedback_word','fine_count','fine_attempt_count', ...
        'fine_pending','fine_bit','d2raw','d2_feedback_word','d2_trial','d2_count', ...
        'd2_pending','d2_bit','dtraw','track_count','feedback_count','ra_on','overrange','raw_latched'};
    logicalFields={'active','coarse_latched','fine_pending','d2_pending','ra_on','overrange','raw_latched'};
    s=struct();
    for k=1:26
        if any(strcmp(fields{k},logicalFields))
            assert(any(x(k)==[0 1]),'behavior:unpack:flag','Packed logical state must be 0/1.');
            s.(fields{k})=logical(x(k));
        else
            s.(fields{k})=x(k);
        end
    end
    assert(x(46)==floor(x(46))&&x(46)>=0&&x(46)<=3, ...
        'behavior:unpack:type','Invalid pending type code.');
    types={'','fine_feedback','d2_feedback','ta_feedback'};
    s.d2_signs=x(27:38);s.tracking_signs=x(39:45);
    s.pending=struct('type',types{x(46)+1},'index',x(47),'word',x(48), ...
        'decision',x(49),'count',x(50),'due_s',x(51));
end
