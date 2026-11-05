function C=behavior_frozen_setup(cfg,h)
%BEHAVIOR_FROZEN_SETUP Immutable public coefficients/calendar for HOLDOUT ONLY.
% One setup call before any holdout is read. Inputs are cfg17 and fitted h684;
% NO analog P, training buffers, references or holdout values accepted.
% Owner saves C and both hashes before holdout. No acceptance or bank swap here.
    dummy=struct('raw_D1',0,'raw_D2',0,'raw_DT',0,'sample_id',0,'epoch',0,'valid',0);
    behavior_public_cal_features(dummy,cfg); % reuse exact cfg17 validation, once
    assert(isa(h,'double')&&isreal(h)&&isequal(size(h),[684 1])&& ...
        all(isfinite(h))&&all(h>0),'frozenCal:h','Require positive finite fitted double h684.');
    [~,~,endian]=computer;assert(endian=='L','frozenCal:endian','Hash ABI is little-endian float64.');
    plan=zeros(cfg.plan_rows,8,'uint8');plan(1,:)=uint8(1:8);seed=double(cfg.pool_seed);
    for row=2:cfg.plan_rows
        a=setdiff(1:18,double(plan(row-1,:)),'stable');
        for k=numel(a):-1:2
            seed=mod(16807*(mod(seed,2147483646)+1),2147483647);q=1+mod(floor(seed),k);
            tmp=a(k);a(k)=a(q);a(q)=tmp;
        end
        plan(row,:)=uint8(a(1:8));
    end
    hs=reshape(h,38,18).'; % diagnostic grouping only; NOT canonical code arithmetic
    cfgText=jsonencode(orderfields(cfg));
    C=struct('schema','sar20-public-frozen-cache/v2','public_cfg',cfg,'h',h, ...
        'h_by_slice',hs,'plan',plan, ...
        'coefficient_sha256',sha256(typecast(h(:),'uint8')), ...
        'public_cfg_sha256',sha256(unicode2native(cfgText,'UTF-8')), ...
        'lifecycle','frozen_for_holdout','acceptance','NOT_ACCEPTED');
end
function hex=sha256(bytes)
    md=java.security.MessageDigest.getInstance('SHA-256');md.update(uint8(bytes(:)));
    hex=lower(reshape(dec2hex(typecast(md.digest(),'uint8'),2).',1,[]));
end
