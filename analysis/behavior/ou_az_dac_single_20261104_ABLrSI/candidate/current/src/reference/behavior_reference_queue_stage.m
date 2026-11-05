function [next,ref,diag]=behavior_reference_queue_stage(x,ref4,event2,raw6,ready,p)
%BEHAVIOR_REFERENCE_QUEUE_STAGE Pure next-state adapter for one UnitDelay22.
% ready input is Transport.ready3(2)=raw_ready, never frame_ready.
    s=behavior_reference_queue_unpack(x);
    [s,ref,diag]=behavior_reference_queue_step(s,ref4,event2,raw6,ready,p);
    next=behavior_reference_queue_pack(s);
end
