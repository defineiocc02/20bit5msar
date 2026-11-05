function s=behavior_reference_queue_init()
%BEHAVIOR_REFERENCE_QUEUE_INIT Cold digital/instrument state, no analog state.
% ref4 columns=[V;ID;epoch;valid]. Occupied distinguishes missing from valid0.
    s=struct('ref4',repmat([NaN;-1;-1;0],1,4),'occupied',false(4,1), ...
        'active_epoch',-1,'has_epoch',false);
end
