function [code20,log12]=behavior_frozen_step(raw6,ready,nominalCode,enabled,C)
%BEHAVIOR_FROZEN_STEP Pure sample decoder; no Ref4/train buffer/state mutation.
% raw6=[D1,D2,DT,id,epoch,valid]. Disabled: exact NominalCode pass-through.
% Enabled: decode ONLY Ready && valid. Otherwise pass NominalCode, log valid=0.
% log12=[uRA,MSBRA,groupsRA,fineRA,biasRA,ditherRA,BhRA,den,vActual,valid,used,groupedMinusCanonicalBhRA].
% RA terms are volts; den dimensionless; vActual input V. Invalid terms NaN.
% Per valid sample: canonical P/B row only, no Nx684 rebuild or plan replay.
    if nargin<4||isempty(enabled),enabled=false;end
    if nargin<5,C=[];end
    assert(isscalar(enabled)&&any(enabled==[0 1])&&isscalar(ready)&&any(ready==[0 1]), ...
        'frozenCal:flags','Enabled and Ready must be explicit binary scalars.');
    assert(isnumeric(nominalCode)&&isreal(nominalCode)&&isscalar(nominalCode), ...
        'frozenCal:nominal','Scalar actual nominal decoder output required.');
    assert(isnumeric(raw6)&&isreal(raw6)&&numel(raw6)==6,'frozenCal:rawShape','Require RAW6.');
    code20=nominalCode;log12=[nan(9,1);0;0;NaN];
    if ~ready,return;end
    r=double(raw6(:));
    assert(isfinite(r(6))&&any(r(6)==[0 1]),'frozenCal:valid','Ready RAW validity must be binary.');
    if ~enabled,log12(10)=r(6);return;end
    if ~r(6),return;end
    assert(isstruct(C)&&isscalar(C)&&strcmp(C.schema,'sar20-public-frozen-cache/v2')&& ...
        strcmp(C.lifecycle,'frozen_for_holdout')&&strcmp(C.acceptance,'NOT_ACCEPTED'), ...
        'frozenCal:cache','Require pre-frozen holdout cache; production acceptance is separate.');
    cfg=C.public_cfg;lim=[2047;4095;255;cfg.plan_rows-2;2^32-1;1];
    assert(all(isfinite(r))&&all(r==floor(r))&&all(r>=0)&&all(r<=lim), ...
        'frozenCal:rawRange','Ready valid RAW range/calendar mismatch.');
    id=r(4);epoch=r(5);slices=double(C.plan(id+1,:));
    coarse=floor(r(1)/32);fine=mod(r(1),32);b=floor(coarse/32);count=mod(coarse,32);
    g=zeros(1,31);if b==0,g(1:31-count)=-1;else,g(1:count)=1;end
    fineBits=2*double(bitget(uint32(fine),5:-1:1))-1;
    dither=0;
    if cfg.dither_enabled
        m=uint64(2147483647);a=uint64(16807);word=uint64(mod(double(cfg.dither_seed),double(m)-1)+1);e=uint64(id+1);
        while e>0
            if bitand(e,uint64(1))~=0,word=mod(word*a,m);end
            a=mod(a*a,m);e=bitshift(e,-1);
        end
        dither=(floor(4*double(word)/double(m))-1.5)*cfg.dither_input_amplitude_v;
    end
    vd=dither*(1024/15);terms=zeros(5,1);Prow=zeros(1,684);Brow=zeros(1,684);
    for slot=1:8
        j=slices(slot);h=C.h_by_slice(j,:);shift=0;
        if cfg.dem_enabled,shift=mod(17*id+7*epoch+11*(j-1)+double(cfg.dem_seed),31);end
        map=mod((0:30)+shift,31)+1;physical=zeros(1,31);physical(map)=g;
        columns=(j-1)*38+(1:38);Prow(columns(1:33))=1;
        Brow(columns)=cfg.vref_v*[2*b-1,physical,fineBits,-1];
        Brow(columns(34:37))=Brow(columns(34:37))+vd; % canonical: add tail first
        % Grouped terms below are DIAGNOSTICS ONLY and never feed code.
        terms=terms+[cfg.vref_v*(2*b-1)*h(1); ...
            cfg.vref_v*(physical*h(2:32).');cfg.vref_v*(fineBits*h(33:37).'); ...
            -cfg.vref_v*h(38);vd*sum(h(34:37))];
    end
    pol=1;if any(strcmp(cfg.az_mode,{'chop','hold_chop'})),seq=[1 -1 -1 1];pol=seq(mod(id,4)+1);end
    d2=double(bitget(uint32(r(2)),12:-1:1));dt=2*double(bitget(uint32(r(3)),8:-1:1))-1;
    u=(pol*[1 d2 sum((8:-1:1).*dt)/8])*cfg.backend_weights_ra_v(:);
    bh=Brow*C.h;den=Prow*C.h;
    assert(isfinite(bh)&&isfinite(den)&&den>0,'frozenCal:finiteDot','Canonical dot overflow/invalid denominator.');
    voltage=(u+bh)/den;
    assert(isfinite(voltage),'frozenCal:finiteVoltage','Nonfinite canonical voltage.');
    groupedDelta=sum(terms)-bh;
    code20=min(2^20-1,max(0,round(voltage*(2^20/(2*cfg.vref_v))+2^19)));
    log12=[u;terms;bh;den;voltage;1;1;groupedDelta];
end
