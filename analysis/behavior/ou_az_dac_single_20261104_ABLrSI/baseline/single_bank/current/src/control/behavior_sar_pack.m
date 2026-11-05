function x = behavior_sar_pack(s)
%BEHAVIOR_SAR_PACK Convert named digital controller state to fixed UnitDelay words.
%Version: v1 (2026-10-27). Caller: SAR initializer/commit adapter.
%Input s; output x[51,1] finite double: 1:26 named scalars, 27:38 D2 signs,
%39:45 TA signs, 46:51 pending[type,index,word,decision,count,due_s].
%Only sample_v is [V] and due_s [s]; all other words are flags/tags/counts/signs.
%Pure ABI conversion; no controller event/reset, analog update, RNG or hidden state.
%State layout is module-specific and independent of the old full-node model.
    fields={'active','sample_id','epoch','bank','sample_v','coarse','coarse_latched', ...
        'trial','d1raw','d1_feedback_word','fine_count','fine_attempt_count', ...
        'fine_pending','fine_bit','d2raw','d2_feedback_word','d2_trial','d2_count', ...
        'd2_pending','d2_bit','dtraw','track_count','feedback_count','ra_on','overrange','raw_latched'};
    x=zeros(51,1);
    for k=1:26
        assert(isfield(s,fields{k})&&isscalar(s.(fields{k})), ...
            'behavior:pack:field','Missing scalar state.%s.',fields{k});
        x(k)=double(s.(fields{k}));
    end
    assert(isequal(size(s.d2_signs),[12 1])&&isequal(size(s.tracking_signs),[7 1]), ...
        'behavior:pack:signs','Require 12 D2 and 7 TA sign entries.');
    types={'','fine_feedback','d2_feedback','ta_feedback'};
    code=find(strcmp(s.pending.type,types),1);
    assert(~isempty(code),'behavior:pack:type','Unknown pending feedback type.');
    x(27:38)=s.d2_signs;x(39:45)=s.tracking_signs;
    x(46:51)=[code-1;s.pending.index;s.pending.word;s.pending.decision;s.pending.count;s.pending.due_s];
    assert(isreal(x)&&all(isfinite(x)),'behavior:pack:finite','Packed state must be finite real.');
end
