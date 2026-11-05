function F=behavior_public_cal_features(raw,cfg)
%BEHAVIOR_PUBLIC_CAL_FEATURES Stateless public RAW -> 18x38 effective basis.
% Adapts archive features SHA ce33523c...b7894386 to current event frontend.
% raw is EXACTLY six column arrays D1/D2/DT/sample_id/epoch/valid; cfg contains
% EXACTLY the listed public fields. No full P/front/actual C/held/Qres/reference.
% P coefficients dimensionless; B coefficients V; u is nominal RA-domain V.
% h=C_half/Cf_effective. P*h input gain, B*h stage1/bias/tail term; x=(u+B*h)/(P*h).
% Physical tail voltage is d_n*1024/15; CT u alone is POL demodulated.
    rawFields={'raw_D1';'raw_D2';'raw_DT';'sample_id';'epoch';'valid'};
    cfgFields={'schema';'vref_v';'fs_hz';'plan_rows';'pool_seed';'pool_schedule'; ...
        'dem_enabled';'dem_seed';'dem_schedule';'dither_enabled';'dither_seed'; ...
        'dither_input_amplitude_v';'dither_schedule';'az_mode'; ...
        'backend_weights_ra_v';'nominal_ra_gain';'tracking_mode'};
    assert(isstruct(raw)&&isscalar(raw)&&isequal(sort(fieldnames(raw)),sort(rawFields)), ...
        'publicCal:rawBoundary','Only six public raw arrays are accepted.');
    assert(isstruct(cfg)&&isscalar(cfg)&&isequal(sort(fieldnames(cfg)),sort(cfgFields)), ...
        'publicCal:configBoundary','Use exactly the 17 declared public configuration fields, not P/front.');
    assert(strcmp(cfg.schema,'sar20-behavior-public-cal/v1')&& ...
        strcmp(cfg.pool_schedule,'causal_18_8_8_2_pm_v1')&& ...
        strcmp(cfg.dem_schedule,'pool_cyclic_shift31_v1')&& ...
        strcmp(cfg.dither_schedule,'input_counter_tail1024_over15_v1')&& ...
        strcmp(cfg.tracking_mode,'finite_sinc2'), ...
        'publicCal:version','Unknown public schedule or tracking version.');
    assert(isnumeric(cfg.vref_v)&&isreal(cfg.vref_v)&&isscalar(cfg.vref_v)&&isfinite(cfg.vref_v)&&cfg.vref_v>0&& ...
        isequal(double(cfg.fs_hz),5e6)&&isequal(double(cfg.nominal_ra_gain),32), ...
        'publicCal:nominalScale','Require declared positive Vref, Fs=5MHz and fixed nominal RA gain32.');
    assert(isnumeric(cfg.plan_rows)&&isreal(cfg.plan_rows)&&isscalar(cfg.plan_rows)&&isfinite(cfg.plan_rows)&& ...
        cfg.plan_rows==floor(cfg.plan_rows)&&cfg.plan_rows>=2&&cfg.plan_rows<=1e6, ...
        'publicCal:planRows','Public plan_rows must be 2..1e6.');
    for key={'pool_seed','dem_seed','dither_seed'}
        v=cfg.(key{1});assert(isnumeric(v)&&isreal(v)&&isscalar(v)&&isfinite(v)&& ...
            v==floor(v)&&v>=0&&v<=2^32-1,'publicCal:seed','Seeds must be uint32-valued.');
    end
    for key={'dem_enabled','dither_enabled'}
        v=cfg.(key{1});assert((isnumeric(v)||islogical(v))&&isreal(v)&&isscalar(v)&& ...
            isfinite(double(v))&&any(double(v)==[0 1]),'publicCal:flag','Explicit 0/1 feature flags required.');
    end
    a=cfg.dither_input_amplitude_v;
    assert(isnumeric(a)&&isreal(a)&&isscalar(a)&&isfinite(a)&&a>=0&& ...
        (~cfg.dither_enabled||a>0),'publicCal:dither','Input-equivalent amplitude must be nonnegative V (on requires >0).');
    assert(any(strcmp(cfg.az_mode,{'off','ordinary','chop','hold','hold_chop'})), ...
        'publicCal:azMode','Unknown public AZ/POL mode.');
    weights=cfg.backend_weights_ra_v;
    assert(isnumeric(weights)&&isreal(weights)&&numel(weights)==14&&all(isfinite(weights(:)))&& ...
        all(weights(2:13)>0)&&weights(14)>0,'publicCal:backend','Require nominal [offset,D2(12),TA] RA-domain V.');
    n=numel(raw.sample_id);assert(n>=1,'publicCal:empty','Empty raw batch.');
    lim=[2047 4095 255 cfg.plan_rows-2 2^32-1 1];
    for k=1:6
        v=raw.(rawFields{k});assert((isnumeric(v)||islogical(v))&&isreal(v)&&isvector(v)&&numel(v)==n&& ...
            all(isfinite(v(:)))&&all(v(:)==floor(v(:)))&&all(v(:)>=0)&&all(v(:)<=lim(k)), ...
            'publicCal:rawRange','Malformed or out-of-plan public field %s.',rawFields{k});
        raw.(rawFields{k})=double(v(:));
    end
    ids=raw.sample_id;epoch=raw.epoch;valid=logical(raw.valid);
    plan=public_plan(max(ids)+1,double(cfg.pool_seed));
    P=nan(n,684);B=nan(n,684);u=nan(n,1);slices=zeros(n,8);shifts=nan(n,8);
    dn=nan(n,1);vd=dn;pol=dn;basis=nan(n,14);
    for row=1:n
        id=ids(row);slices(row,:)=plan(id+1,:);
        if ~valid(row),continue;end
        c=floor(raw.raw_D1(row)/32);f=mod(raw.raw_D1(row),32);b=floor(c/32);count=mod(c,32);
        g=zeros(1,31);if b==0,g(1:31-count)=-1;else,g(1:count)=1;end
        fine=2*double(bitget(uint32(f),5:-1:1))-1;
        dn(row)=public_dither(id,cfg);vd(row)=dn(row)*(1024/15);
        pol(row)=1;if any(strcmp(cfg.az_mode,{'chop','hold_chop'})),seq=[1 -1 -1 1];pol(row)=seq(mod(id,4)+1);end
        P(row,:)=0;B(row,:)=0;
        for slot=1:8
            j=slices(row,slot);shift=0;
            if cfg.dem_enabled,shift=mod(17*id+7*epoch(row)+11*(j-1)+double(cfg.dem_seed),31);end
            map=mod((0:30)+shift,31)+1;physical=zeros(1,31);physical(map)=g;
            columns=(j-1)*38+(1:38);P(row,columns(1:33))=1;
            B(row,columns)=cfg.vref_v*[2*b-1,physical,fine,-1];
            B(row,columns(34:37))=B(row,columns(34:37))+vd(row);
            shifts(row,slot)=shift;
        end
        d2=double(bitget(uint32(raw.raw_D2(row)),12:-1:1));
        dt=2*double(bitget(uint32(raw.raw_DT(row)),8:-1:1))-1;
        statistic=sum((8:-1:1).*dt)/8;
        basis(row,:)=pol(row)*[1 d2 statistic];u(row)=basis(row,:)*weights(:);
    end
    local=[16 32*ones(1,31) 16 8 4 2 1 17];
    names=[{'msb16'},arrayfun(@(k)sprintf('group32_%02d',k),1:31,'UniformOutput',false), ...
        {'fine16','fine8','fine4','fine2','fine1','bias17'}];
    columns=cell(1,684);for j=1:18,columns((j-1)*38+(1:38))=strcat(sprintf('slice%02d_',j),names);end
    F=struct('schema','sar20-behavior-public-features/v1','sample_id',ids,'epoch',epoch,'valid',valid, ...
        'raw_D1',raw.raw_D1,'raw_D2',raw.raw_D2,'raw_DT',raw.raw_DT, ...
        'sample_coefficients',P,'code_coefficients_v',B,'backend_residual_ra_v',u, ...
        'backend_basis',basis,'slice_ids',slices,'dem_shift',shifts,'public_pol',pol, ...
        'dither_input_v',dn,'dither_tail_v',vd,'column_names',{columns}, ...
        'nominal_h',repmat(local(:)/(8*1024/cfg.nominal_ra_gain),18,1), ...
        'public_config',cfg,'coefficient_units','effective C_half/Cf_effective, fixed nominal backend voltage scale', ...
        'state','none; no random stream, mutable cursor or coefficient update', ...
        'scope','Public static charge basis only; no proof finite RA/settling/AZ errors fit fixed h');
end
function plan=public_plan(n,seed)
% Same current frontend / archived public PM Fisher-Yates calendar.
    plan=zeros(n,8);plan(1,:)=1:8;
    for row=2:n
        a=setdiff(1:18,plan(row-1,:),'stable');
        for k=numel(a):-1:2
            seed=mod(16807*(mod(seed,2147483646)+1),2147483647);q=1+mod(floor(seed),k);
            tmp=a(k);a(k)=a(q);a(q)=tmp;
        end
        plan(row,:)=a(1:8);
    end
end
function v=public_dither(id,cfg)
    v=0;if ~cfg.dither_enabled,return;end
    m=uint64(2147483647);a=uint64(16807);word=uint64(mod(double(cfg.dither_seed),double(m)-1)+1);e=uint64(id+1);
    while e>0
        if bitand(e,uint64(1))~=0,word=mod(word*a,m);end
        a=mod(a*a,m);e=bitshift(e,-1);
    end
    v=(floor(4*double(word)/double(m))-1.5)*cfg.dither_input_amplitude_v;
end
