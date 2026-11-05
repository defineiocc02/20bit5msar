function [pol,pair_id]=behavior_public_pol(sample_id,epoch,mode)
%BEHAVIOR_PUBLIC_POL Public FPGA chopping schedule, no analog/state input.
% [pol,pair]=behavior_public_pol(ID,epoch,mode). Integer unsigned32 tags.
% Modes off/ordinary/hold: +1; chop/hold_chop: [+1,-1,-1,+1] for mod(ID,4).
% pair=floor(ID/2). Epoch joins reset identity, never shifts or randomizes POL.
% System reset restarts ID0 at the new epoch; no hidden counter/RNG is used.
    for x={sample_id,epoch}
        v=x{1};assert(isnumeric(v)&&isreal(v)&&isscalar(v)&&isfinite(v)&& ...
            v>=0&&v<=2^32-1&&v==floor(v),'behaviorPol:tags','Require public uint32-valued ID/epoch.');
    end
    assert((ischar(mode)&&isrow(mode))||(isstring(mode)&&isscalar(mode)), ...
        'behaviorPol:mode','Mode must be a scalar label.');
    mode=char(mode);
    assert(any(strcmp(mode,{'off','ordinary','chop','hold','hold_chop'})), ...
        'behaviorPol:mode','Unknown AZ mode.');
    % Only the chopping modes flip polarity; off/ordinary/hold stay at +1.
    % The pattern repeats every four samples and is keyed by ID only, so the
    % epoch never shifts or randomises POL.
    pol=1;
    if any(strcmp(mode,{'chop','hold_chop'}))
        pattern=[1 -1 -1 1];
        pol=pattern(mod(double(sample_id),4)+1);
    end
    pair_id=floor(double(sample_id)/2);
end
