function v=behavior_public_dither(id,p)
%BEHAVIOR_PUBLIC_DITHER Public ID-only nominal dither. No state, no RNG calls.
%
%   v = behavior_public_dither(id, p)
%
% id must be a uint32-valued integer. The epoch identifies the record but NEVER
% shifts the word: two runs with the same id and seed get the same dither.
%
% The value is (floor(4*w/m) - 1.5) * amplitude, i.e. four equally spaced levels
% centred on zero. Disabled dither returns exactly 0 without touching the seed.
    assert(isnumeric(id)&&isreal(id)&&isscalar(id)&&isfinite(id)&& ...
        id>=0&&id<=2^32-1&&id==floor(id),'behaviorDecode:ditherID','Require uint32-valued public ID.');
    assert(isscalar(p.dither_enabled)&&ismember(p.dither_enabled,[0 1])&& ...
        isscalar(p.dither_seed)&&isfinite(p.dither_seed)&&p.dither_seed>=0&& ...
        p.dither_seed<=2^32-1&&p.dither_seed==floor(p.dither_seed)&& ...
        isscalar(p.dither_amplitude_v)&&isfinite(p.dither_amplitude_v)&&p.dither_amplitude_v>=0, ...
        'behaviorDecode:ditherConfig','Require explicit public dither parameters.');
    v=0;
    if ~p.dither_enabled
        return;
    end
    % Park-Miller generator: the seed is the starting word and the sample ID is
    % the exponent, so the value is reproducible from public fields alone with no
    % RNG stream touched. Exponentiating by squaring keeps it O(log id).
    modulus=uint64(2147483647);
    a=uint64(16807);
    word=uint64(mod(double(p.dither_seed),double(modulus)-1)+1);
    exponent=uint64(id+1);
    while exponent>0
        if bitand(exponent,uint64(1))~=0
            word=mod(word*a,modulus);
        end
        a=mod(a*a,modulus);
        exponent=bitshift(exponent,-1);
    end
    v=(floor(4*double(word)/double(modulus))-1.5)*p.dither_amplitude_v;
end
