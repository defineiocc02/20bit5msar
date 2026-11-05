function [ta,common_s,local_s]=behavior_aperture_times(tcnv,ids,id,epoch,p)
%BEHAVIOR_APERTURE_TIMES Pure keyed endpoint aperture times.
%
%   [ta, common_s, local_s] = behavior_aperture_times(tcnv, ids, id, epoch, p)
%
% Returns the actual aperture time per physical slice: the nominal CNV time plus
% a common term, a per-slice local term, and the fixed slice skew.
%
% KEYS
%   common term  (seed, id, epoch, lane 'COMM')
%   local term   (seed, id, epoch, physical slice 1..18, lane 'LOCL')
%   The sample ID/epoch is shared by all eight slices. DEM order never keys the
%   local jitter: it is the physical slice index that matters, not the rotated
%   position.
%
% DETERMINISM
%   No RNG stream is touched or advanced. Every value comes from a keyed integer
%   hash (mix32) followed by Box-Muller, so results are reproducible from the
%   public seed alone. Statistical quality is NOT certified here.
%
% OFF PATH
%   When p.enabled is false the additions are bypassed entirely, including signed
%   zero and roundoff effects on tcnv: ta is exactly the nominal time.
    ids=double(ids(:));
    assert(isscalar(tcnv)&&isreal(tcnv)&&isfinite(tcnv)&& ...
        all(ids>=1&ids<=18&ids==floor(ids)), ...
        'behaviorFE:apertureInput','Need finite nominal time and physical slice IDs.');
    for v=[id epoch]
        assert(isfinite(v)&&v>=0&&v<=2^32-1&&v==floor(v), ...
            'behaviorFE:apertureTag','Sample ID/epoch must be uint32-valued.');
    end
    % Default result when jitter is off: every aperture equals the nominal time.
    common_s=0;
    local_s=zeros(size(ids));
    ta=repmat(double(tcnv),size(ids));
    if ~p.enabled
        return;
    end
    common_s=p.common_sigma_s*normal_key(p.seed,id,epoch,0,hex2dec('434F4D4D'));
    for k=1:numel(ids)
        local_s(k)=p.local_sigma_s*normal_key(p.seed,id,epoch,ids(k),hex2dec('4C4F434C'));
    end
    ta=tcnv+common_s+local_s+p.fixed_slice_skew_s(ids);
    assert(all(isfinite(ta)),'behaviorFE:apertureFinite','Nonfinite aperture time.');
end

function z=normal_key(seed,id,epoch,slice,lane)
% Domain-separated 32-bit integer hash, Box-Muller; statistical quality is not
% certified by deterministic native smoke tests. Independent of kTC seed/key.
    % Domain separation: each key component is folded in through mix32 so that
    % changing any one of (seed,lane,id,epoch,slice) changes the whole output.
    m=uint64(4294967296);
    x=mix32(bitxor(uint64(seed),uint64(lane)));
    x=mix32(bitxor(x,uint64(id)));
    x=mix32(bitxor(x,mod(uint64(epoch)+uint64(2246822507),m)));
    x=mix32(bitxor(x,uint64(slice)+uint64(3266489909)));
    % Two independent uniforms from the same mixed state, then Box-Muller.
    % The +0.5 shift keeps u,v strictly inside (0,1) so log/cos never see an edge.
    a=mix32(bitxor(x,uint64(668265263)));
    b=mix32(bitxor(x,uint64(374761393)));
    u=(double(a)+0.5)/4294967296;
    v=(double(b)+0.5)/4294967296;
    z=sqrt(-2*log(u))*cos(2*pi*v);
end
function x=mix32(x)
    m=uint64(4294967296);
    % Three xor-shift / multiply rounds. Order matters: do not reorder these.
    x=bitxor(x,bitshift(x,-16));
    x=mod(x*uint64(2246822507),m);
    x=bitxor(x,bitshift(x,-13));
    x=mod(x*uint64(3266489909),m);
    x=bitxor(x,bitshift(x,-16));
end
