function s=behavior_reference_queue_unpack(x)
%BEHAVIOR_REFERENCE_QUEUE_UNPACK Pure inverse; no reset or reference evaluation.
    assert(isa(x,'double')&&isreal(x)&&numel(x)==22,'referenceQueue:unpack','Expected double state22.');
    % Exact ABI inverse of behavior_reference_queue_pack: 16 reference words
    % form a 4x4 ref4 block, then four occupancy flags and the epoch pair.
    x=x(:);
    s=struct('ref4',reshape(x(1:16),4,4),'occupied',logical(x(17:20)), ...
        'active_epoch',x(21),'has_epoch',logical(x(22)));
end
