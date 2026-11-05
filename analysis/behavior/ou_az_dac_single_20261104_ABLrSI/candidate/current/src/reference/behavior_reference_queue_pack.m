function x=behavior_reference_queue_pack(s)
%BEHAVIOR_REFERENCE_QUEUE_PACK Explicit 22-word external UnitDelay ABI.
% 1:16 Ref4 columns (V,unitless ID/epoch/valid),17:20 occupied flags,
% 21 active_epoch,22 has_epoch. New epoch clears occupied; cold init clears all.
    x=[s.ref4(:);double(s.occupied(:));double(s.active_epoch);double(s.has_epoch)];
    assert(isequal(size(x),[22 1]),'referenceQueue:pack','Expected 22 words.');
end
