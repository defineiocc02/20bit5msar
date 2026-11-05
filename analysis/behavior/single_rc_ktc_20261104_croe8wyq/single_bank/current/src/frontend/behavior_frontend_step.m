function [s,out] = behavior_frontend_step(s,cmd,p)
%BEHAVIOR_FRONTEND_STEP Advance frontend charge and apply one named event.
%Version: v1 (2026-10-27). Caller: behavior event scheduler/advance-commit adapter.
%Inputs: explicit s, normalized p from init; cmd.event/t_s [s]/id/epoch [integers].
%Events: acquire_open/capture/convert_join/dac_commit/observe/release/reset/input_change.
%dac_commit.d1_code is an 11-bit physical trial/feedback word; release.vtop_v [V]
%is the actual backend top voltage at release, scalar or 18-vector, not vtop_equiv_v.
%Outputs: next s; out qres [C], cs/cp/ctop [F], held/residual/top equivalents [V].
%First advance old conditions to t_s. Reset cancels ownership/valid tags, retains
%analog B and source; active conversion must release with actual vtop before reset.
%Init alone cold-clears state. No hidden state or RNG.
%Model: analytic grouped RC; release returns charge into the next acquisition.
    assert(isstruct(s)&&strcmp(s.schema,p.schema)&&isfield(p,'group_C_f'), ...
        'behaviorFE:state','Use init and its returned normalized p.');
    if isfield(p,'single_bank')&&p.single_bank
        assert(all(s.B_c(:,3)==0)&&all(s.B_target_c(:,3)==0), ...
            'singleBank:disconnectedCharge','Disconnected bias charge/target must already be zero.');
    end
    assert(isstruct(cmd)&&isscalar(cmd)&&all(isfield(cmd,{'event','t_s','id','epoch'})), ...
        'behaviorFE:command','cmd requires event,t_s,id,epoch.');
    event=char(cmd.event);allowed={'acquire_open','capture','convert_join','dac_commit','observe','release','reset','input_change'};
    assert(any(strcmp(event,allowed)),'behaviorFE:event','Unknown frontend event.');
    assert(isnumeric(cmd.t_s)&&isreal(cmd.t_s)&&isscalar(cmd.t_s)&&isfinite(cmd.t_s), ...
        'behaviorFE:time','t_s must be finite real seconds.');
    for key={'id','epoch'}
        v=cmd.(key{1});assert(isnumeric(v)&&isreal(v)&&isscalar(v)&&isfinite(v)&& ...
            v>=0&&v<=2^32-1&&v==floor(v),'behaviorFE:tag','id/epoch must be uint32-valued.');
    end
    cmd.id=double(cmd.id);cmd.epoch=double(cmd.epoch);cmd.t_s=double(cmd.t_s);
    assert(cmd.id<size(p.plan,1),'behaviorFE:planBound','ID is outside the public plan.');
    assert(~s.has_time||cmd.t_s>=s.time_s,'behaviorFE:backwardTime','Events cannot go backwards.');
    if isfield(cmd,'input')
        check_input(cmd.input);
        assert(strcmp(event,'input_change')||isequaln(cmd.input,s.input), ...
            'behaviorFE:inputChange','Change the source only through an explicit input_change event.');
    end
    if s.has_time,s=advance(s,cmd.t_s,p);else,s.time_s=cmd.t_s;s.has_time=true;end
    ids=p.plan(cmd.id+1,:).';releaseOut=[];returned=[];
    switch event
        case 'acquire_open'
            assert(all(s.phase(ids)==0),'behaviorFE:acquireOwnership','Release selected slices before acquiring again.');
            assert(~any(s.phase==1),'behaviorFE:acquireWidth','Only one eight-slice acquisition group may be open.');
            dn=dither_value(cmd.id,p);vd=dn*(1024/15);
            s.phase(ids)=1;s.target_id(ids)=cmd.id;s.target_epoch(ids)=cmd.epoch;
            s.capture_valid(ids)=false;
            s.acquire_open_s(ids)=cmd.t_s;
            if is_single(p),s.acquire_open_s(ids)=cmd.t_s+p.single_guard_s;end
            s.B_target_c(ids,2)=-p.group_C_f(ids,2)*vd;
            s.B_target_c(ids,3)=p.group_C_f(ids,3)*p.vref_v;
            s.dither_input_v(ids)=dn;
            if ~is_single(p)||p.single_guard_s==0
                s=apply_ideal_acquire(s,ids,cmd.t_s,p);
            end
        case 'capture'
            assert(all(s.phase(ids)==1)&&all(s.target_id(ids)==cmd.id)&&all(s.target_epoch(ids)==cmd.epoch), ...
                'behaviorFE:captureOwnership','Capture requires the same target eight-slice acquisition group.');
            if is_single(p)
                assert(all(cmd.t_s>s.acquire_open_s(ids)), ...
                    'singleBank:apertureBeforeOpen','Capture must follow the physical acquisition opening.');
            end
            % Recheck the sampling/jitter boundary here as callers can alter a
            % normalized parameter struct after init. Never overwrite an RC state
            % with an ideal endpoint under an unsupported jitter configuration.
            assert(~p.jitter.enabled||all(p.tau_sample_s(ids)==0), ...
                'behaviorFE:jitterFiniteSamplingUnsupported', ...
                'Finite-RC sampling with displaced aperture is not implemented.');
            if is_single(p)
                assert(~p.jitter.enabled,'singleBank:unsupportedNI', ...
                    'This isolated RC+kTC candidate keeps single-bank jitter OFF.');
            end
            s=apply_ideal_acquire(s,ids,cmd.t_s,p);
            if p.jitter.enabled
                [ta,~,~]=behavior_aperture_times(cmd.t_s,ids,cmd.id,cmd.epoch,p.jitter);
                assert(all(ta>s.acquire_open_s(ids))&&all(ta<cmd.t_s+p.jitter.first_coarse_offset_s), ...
                    'behaviorFE:apertureBounds','Actual aperture must lie strictly between acquire_open and first coarse latch; no clipping/redraw.');
                % Endpoint aperture error changes the SAME retained signal charge.
                % Global event time, capture tags and downstream timing stay nominal.
                for k=1:numel(ids)
                    j=ids(k);s.B_c(j,1)=p.group_C_f(j,1)*input_value(ta(k),s.input);
                end
                s.actual_aperture_s(ids)=ta;
            else
                s.actual_aperture_s(ids)=cmd.t_s;
            end
            if p.ktc_enabled
                tau=p.tau_sample_s(ids);
                if is_single(p)
                    assert(all(~isnan(tau)&tau>=0)&&all(tau==tau(1)), ...
                        'singleBank:ktcUnequalTau', ...
                        'Sampling kTC requires one nonnegative tau for all bank segments.');
                else
                    assert(all(tau==0), ...
                        'behaviorFE:ktcFiniteSamplingUnsupported', ...
                        'Finite-RC kTC is qualified only for a single bank.');
                end
                % Existing equilibrium keyed sample and exact tau=0 arithmetic
                % are retained. For finite tau, scale only the independent NEW
                % innovation. Old stochastic charge already in B was propagated
                % by advance() and must not be injected again. Inf means no new
                % thermal innovation and leaves the retained B bit-for-bit held.
                if ~all(isinf(tau))
                    dv=sample_ktc_diff(ids,cmd.id,cmd.epoch,p);
                    finiteMask=tau>0 & isfinite(tau);
                    if any(finiteMask)
                        duration=cmd.t_s-s.acquire_open_s(ids);
                        dv(finiteMask)=dv(finiteMask).* ...
                            sqrt(-expm1(-2*duration(finiteMask)./tau(finiteMask)));
                    end
                    s.B_c(ids,1)=s.B_c(ids,1)+p.group_C_f(ids,1).*dv;
                end
            end
            s.q_initial_c(ids)=sum(s.B_c(ids,:),2);
            s.v_capture_v(ids)=s.B_c(ids,1)./p.group_C_f(ids,1);
            s.capture_id(ids)=cmd.id;s.capture_epoch(ids)=cmd.epoch;s.capture_valid(ids)=true;
            s.aperture_s(ids)=cmd.t_s;s.phase(ids)=3;
        case 'convert_join'
            assert(~any(s.phase==2),'behaviorFE:convertWidth','Release the previous conversion group first.');
            require_capture(s,ids,cmd);
            assert(all(s.phase(ids)==3),'behaviorFE:joinOwnership','Join requires captured, unjoined slices.');
            s.phase(ids)=2;s.active_id=cmd.id;s.active_epoch=cmd.epoch;
            s.B_target_c(ids,:)=s.B_c(ids,:); % Hold until an explicit DAC command.
            % Preserve precharge B; first DAC transition starts from these states.
            s.has_dac_command=false;
        case 'dac_commit'
            require_active(s,ids,cmd);
            assert(isfield(cmd,'d1_code')&&isnumeric(cmd.d1_code)&&isreal(cmd.d1_code)&& ...
                isscalar(cmd.d1_code)&&isfinite(cmd.d1_code)&&cmd.d1_code>=0&& ...
                cmd.d1_code<=2047&&cmd.d1_code==floor(cmd.d1_code), ...
                'behaviorFE:D1','d1_code must be the registered raw integer 0..2047.');
            cmd.d1_code=double(cmd.d1_code);
            c=floor(cmd.d1_code/32);f=mod(cmd.d1_code,32);b=floor(c/32);k=mod(c,32);
            g=zeros(1,31);if b==0,g(1:31-k)=-1;else,g(1:k)=1;end
            fine=2*double(bitget(uint32(f),5:-1:1))-1;
            for j=ids.'
                shift=0;if p.dem_enabled,shift=mod(17*cmd.id+7*cmd.epoch+11*(j-1)+p.dem_seed,31);end
                map=mod((0:30)+shift,31)+1;physical=zeros(1,31);physical(map)=g;
                levels=[2*b-1,physical,fine,0];
                s.B_target_c(j,:) = p.vref_v*[sum(p.C_f(j,1:33).*levels(1:33)), ...
                    sum(p.C_f(j,34:37).*levels(34:37)),0];
                s.dem_shift(j)=shift;
                if p.tau_dac_s(j)==0,s.B_c(j,:)=s.B_target_c(j,:);end
            end
            s.d1_code=cmd.d1_code;s.has_dac_command=true;
        case 'observe'
            % Read only after analytic advancement to this observation time.
        case 'release'
            require_active(s,ids,cmd);
            assert(isfield(cmd,'vtop_v')&&isnumeric(cmd.vtop_v)&&isreal(cmd.vtop_v)&& ...
                (isscalar(cmd.vtop_v)||numel(cmd.vtop_v)==18)&&all(isfinite(cmd.vtop_v(:))), ...
                'behaviorFE:return','release requires the same backend post-conversion vtop_v, V.');
            vt=cmd.vtop_v;if isscalar(vt),vt=repmat(vt,18,1);else,vt=vt(:);end
            releaseOut=readout(s,ids,cmd,p);
            returned=s.B_c(ids,:)-p.group_C_f(ids,:).*vt(ids);
            % Acquisition top is clamped to 0 V: B_return=q_bottom_return.
            s.B_c(ids,:)=returned;s.B_target_c(ids,:)=returned;
            s.phase(ids)=0;s.capture_valid(ids)=false;
            s.active_id=-1;s.active_epoch=-1;s.has_dac_command=false;
        case 'reset'
            % An interrupted finite-RC acquisition would need an additional
            % stochastic endpoint. This capture-only model refuses to silently
            % discard that innovation; no new event/key/state is introduced.
            if p.ktc_enabled&&is_single(p)&&p.temperature_K>0
                active=find(s.phase==1 & s.acquire_open_s<cmd.t_s);
                tau=p.tau_sample_s(active);
                assert(~any(tau>0 & isfinite(tau)), ...
                    'singleBank:ktcInterruptedAcquisition', ...
                    'Finite-RC thermal acquisition must complete before reset.');
            end
            % An active RA/top-node return must be committed before reset.
            assert(~any(s.phase==2),'behaviorFE:resetReturn','Release active slices with backend vtop before reset.');
            % Digital reset cancels ownership/tags; analog B is deliberately retained.
            s.phase(:)=0;s.capture_valid(:)=false;s.target_id(:)=-1;s.target_epoch(:)=-1;
            s.active_id=-1;s.active_epoch=-1;s.has_dac_command=false;
        case 'input_change'
            assert(~p.jitter.enabled||(~any(s.phase==1)&& ...
                ~any(s.capture_valid & s.actual_aperture_s>cmd.t_s)), ...
                'behaviorFE:jitterSourceChangeUnsupported', ...
                'Keep the analytic source descriptor fixed during acquisition and until all valid future apertures have elapsed.');
            assert(isfield(cmd,'input'),'behaviorFE:inputChange','input_change requires cmd.input.');
            s.input=cmd.input;idsOpen=find(s.phase==1);
            if is_single(p)&&p.single_guard_s>0
                idsOpen=idsOpen(s.acquire_open_s(idsOpen)<=cmd.t_s);
            end
            s=apply_ideal_acquire(s,idsOpen,cmd.t_s,p);
    end
    out=readout(s,ids,cmd,p);
    if ~isempty(releaseOut)
        out=releaseOut;out.released=true;out.return_ids=ids;out.q_return_c=returned;
        if is_single(p)
            % A disconnected capacitor has no meaningful bottom voltage.
            caps=p.group_C_f(ids,:);out.v_return_v=nan(size(returned));
            present=caps>0;out.v_return_v(present)=returned(present)./caps(present);
        else
            out.v_return_v=returned./p.group_C_f(ids,:);
        end
    end
    s.event_count=s.event_count+1;
end

function s=advance(s,t,p)
    dt=t-s.time_s;if dt==0,return;end
    acq=find(s.phase==1);
    for j=acq.'
        C=p.group_C_f(j,:);tau=p.tau_sample_s(j);
        if is_single(p)&&p.single_guard_s>0
            % Reserve at release but hold the returned charge until actual open.
            if t<s.acquire_open_s(j),continue;end
            t0=max(s.time_s,s.acquire_open_s(j));
            if ~isinf(tau)&&(t>t0||tau==0)
                v0=s.B_c(j,1)/C(1);v=rc_sine(v0,t0,t,tau,s.input);
                s.B_c(j,1)=C(1)*v;
            end
            if t>t0||p.tau_precharge_s(j)==0
                s.B_c(j,2:3)=relax(s.B_c(j,2:3),s.B_target_c(j,2:3),t-t0,p.tau_precharge_s(j));
            end
        else
            v0=s.B_c(j,1)/C(1);v=rc_sine(v0,s.time_s,t,tau,s.input);
            s.B_c(j,1)=C(1)*v;
            s.B_c(j,2:3)=relax(s.B_c(j,2:3),s.B_target_c(j,2:3),dt,p.tau_precharge_s(j));
        end
    end
    conv=find(s.phase==2);
    for j=conv.'
        s.B_c(j,:)=relax(s.B_c(j,:),s.B_target_c(j,:),dt,p.tau_dac_s(j));
    end
    s.time_s=t;
end

function s=apply_ideal_acquire(s,ids,t,p)
    for j=ids(:).'
        if p.tau_sample_s(j)==0,s.B_c(j,1)=p.group_C_f(j,1)*input_value(t,s.input);end
        if p.tau_precharge_s(j)==0,s.B_c(j,2:3)=s.B_target_c(j,2:3);end
    end
end

function v=rc_sine(v0,t0,t1,tau,u)
% Exact sinusoidal particular solution plus homogeneous transient.
    if tau==0,v=input_value(t1,u);return;end
    if isinf(tau),v=v0;return;end
    w=2*pi*u.frequency_hz;a=w*tau;
    particular=@(t) u.offset_v+u.amplitude_v/hypot(1,a)*sin(w*t+u.phase_rad-atan(a));
    v=particular(t1)+(v0-particular(t0))*exp(-(t1-t0)/tau);
end

function yes=is_single(p)
    yes=isfield(p,'single_bank')&&p.single_bank;
end

function y=relax(x,target,dt,tau)
    if tau==0,y=target;elseif isinf(tau),y=x;else,y=target+(x-target)*exp(-dt/tau);end
end

function y=input_value(t,u)
    y=u.offset_v+u.amplitude_v*sin(2*pi*u.frequency_hz*t+u.phase_rad);
end

function require_capture(s,ids,c)
    assert(all(s.capture_valid(ids))&&all(s.capture_id(ids)==c.id)&&all(s.capture_epoch(ids)==c.epoch), ...
        'behaviorFE:captureTags','Selected slices do not have the requested valid capture tags.');
end

function require_active(s,ids,c)
    require_capture(s,ids,c);
    assert(all(s.phase(ids)==2)&&s.active_id==c.id&&s.active_epoch==c.epoch, ...
        'behaviorFE:activeTags','Operation is not for the active conversion.');
end

function out=readout(s,ids,c,p)
    cs=sum(p.group_C_f(ids,1));cp=sum(p.Cp_f(ids));ct=sum(p.group_C_f(ids,:),'all')+cp;
    valid=all(s.capture_valid(ids))&&all(s.capture_id(ids)==c.id)&&all(s.capture_epoch(ids)==c.epoch)&& ...
        all(ismember(s.phase(ids),[2 3]));
    qr=NaN;vh=NaN;
    if valid
        qr=sum(s.q_initial_c(ids)-sum(s.B_c(ids,:),2));
        vh=sum(p.group_C_f(ids,1).*s.v_capture_v(ids))/cs;
    end
    nxt=[];if c.id+2<=size(p.plan,1),nxt=p.plan(c.id+2,:).';end
    conv=ids;park=setdiff((1:18).',[ids;nxt]);
    if is_single(p)
        conv=find(ismember(s.phase,[2 3]));nxt=find(s.phase==1);park=find(s.phase==0);
    end
    out=struct('event',char(c.event),'t_s',c.t_s,'id',c.id,'epoch',c.epoch,'valid',valid, ...
        'qres_c',qr,'cs_f',cs,'cp_f',cp,'ctop_f',ct,'vheld_v',vh,'vres_v',qr/cs, ...
        'vtop_equiv_v',-qr/ct,'conv_ids',conv,'acq_ids',nxt,'park_ids',park, ...
        'phase',s.phase,'d1_code',s.d1_code,'has_dac_command',s.has_dac_command, ...
        'coarse_code',floor(s.d1_code/32),'fine_code',mod(s.d1_code,32), ...
        'coarse_input_v',vh,'dem_shift',s.dem_shift(ids),'dither_input_v',dither_value(c.id,p), ...
        'tail_source_v',dither_value(c.id,p)*(1024/15),'released',false, ...
        'return_ids',zeros(0,1),'q_return_c',zeros(0,3),'v_return_v',zeros(0,3));
end

function v=dither_value(id,p)
% Same public PM modular exponent and 2-bit levels as sar20_dither_value.
    v=0;if ~p.dither_enabled,return;end
    modulus=uint64(2147483647);a=uint64(16807);
    word=uint64(mod(double(p.dither_seed),double(modulus)-1)+1);exponent=uint64(id+1);
    while exponent>0
        if bitand(exponent,uint64(1))~=0,word=mod(word*a,modulus);end
        a=mod(a*a,modulus);exponent=bitshift(exponent,-1);
    end
    v=(floor(4*double(word)/double(modulus))-1.5)*p.dither_input_amplitude_v;
end

function check_input(u)
    keys={'offset_v';'amplitude_v';'frequency_hz';'phase_rad'};
    assert(isstruct(u)&&isscalar(u)&&isequal(sort(fieldnames(u)),sort(keys)), ...
        'behaviorFE:input','input requires offset/amplitude/frequency/phase scalars.');
    for k=1:numel(keys)
        x=u.(keys{k});assert(isnumeric(x)&&isreal(x)&&isscalar(x)&&isfinite(x), ...
            'behaviorFE:input','Input must contain finite real scalars.');
    end
    assert(u.amplitude_v>=0&&u.frequency_hz>=0,'behaviorFE:input','Negative amplitude/frequency.');
end

% In a single bank, the existing j key identifies a numerical segment, not a converter.
function dv=sample_ktc_diff(ids,id,epoch,p)
% Analog-only keyed noise. No rand/randn/RandStream or mutable RNG state.
% Tuple lanes: explicit ktc_seed, physical slice, sample ID, epoch. Uniforms
% are open-interval 32-bit words; Box-Muller gives a differential Gaussian.
% This noncryptographic counter hash needs statistical acceptance separately.
    kB=1.380649e-23;dv=zeros(numel(ids),1);modulus=uint64(4294967296);
    base=mix32(bitxor(uint64(p.ktc_seed),uint64(2654435769)));
    for k=1:numel(ids)
        j=ids(k);x=mix32(bitxor(base,uint64(id)));
        x=mix32(bitxor(x,mod(uint64(epoch)+uint64(2246822507),modulus)));
        x=mix32(bitxor(x,uint64(j)+uint64(3266489909)));
        w1=mix32(bitxor(x,uint64(668265263)));
        w2=mix32(bitxor(x,uint64(374761393)));
        u1=(double(w1)+0.5)/4294967296;
        u2=(double(w2)+0.5)/4294967296;
        z=sqrt(-2*log(u1))*cos(2*pi*u2);
        sigma=sqrt((2*kB*p.temperature_K)/p.group_C_f(j,1));
        dv(k)=sigma*z;
    end
    assert(all(isfinite(dv)),'behaviorFE:ktcFinite','Sample noise is nonfinite; check analog C/T.');
end

function x=mix32(x)
% Each 32x32 product is <2^64; mod explicitly wraps rather than saturates.
    modulus=uint64(4294967296);
    x=bitxor(x,bitshift(x,-16));x=mod(x*uint64(2246822507),modulus);
    x=bitxor(x,bitshift(x,-13));x=mod(x*uint64(3266489909),modulus);
    x=bitxor(x,bitshift(x,-16));
end
