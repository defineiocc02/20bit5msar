function [s,y] = behavior_backend_step(s,cmd,dt,p,forcing)
%BEHAVIOR_BACKEND_STEP Advance one RA/AZ state and apply endpoint CINC switching.
%Version: v2 AZ (2026-10-27). Caller: current SarAdc backend stage adapter.
%Inputs: s; NEW cmd.qres_c [C differential], ctop_f [F total front top load],
%d2_signs[12], ta_signs[7], ra_on/az_on/reset, sample_id/epoch; dt [s], p.
%Event routing schedules off/ordinary/chop/hold/hold_chop and signs Qres once; this kernel
%does NOT multiply Qres or DAC2 signs by polarity. AZ samples input-referred
%Vos in an isolated signal path, never Qres/ideal VX; deterministic source
%injection is latched once per write. Random noise remains unsupported.
%First advance dt under s.command, then latch cmd; s=[] requires dt=0 for cold init.
%Outputs: next s; y.predicted before new cmd/y.actual after it; vx/vy/vtop are
%differential [V], CT nodes[2,2] [V] have P/N rows and A/B columns; kick [V].
%RST_SIG (cmd.reset) relaxes vx, clamps A, retains B; epoch changes invalidate
%AZ service tags without clearing analog a. AZ independently
%follows az_on/ni.az. No persistent/global state, RNG, MNA or internal time steps.
%Model: target=Qres/Cf, NG=1+Ctop/Cf, gain=A0/(A0+NG), tau=NG/(2*pi*UGB).
%CINC kicks this same RA state; CT output loading is separate from front Ctop.
%Endpoint slew limiting is an engineering approximation, not a nonlinear ODE solve.
%Candidate optional forcing is derived read-only from the OLD FE owner. The
%off/all-zero-tau path supplies no forcing and retains the original arithmetic.
    validate_inputs(cmd,dt,p);
    cmd=normalize_command(cmd);
    cold=isempty(s);
    if cold
        assert(dt==0,'behavior:coldTime','Initialize with dt=0.');
        s=struct('schema','behavior-backend-state/v2','time_s',0, ...
            'units','time_s [s], vx_v [V differential], AZ [V input referred], qB [C]', ...
            'vx_v',0,'az_input_half_v',double(p.az.initial_input_half_v(:)), ...
            'ct_reset_vx_v',0,'main_qb_c',double(p.ct.initial_main_qb_c(:)), ...
            'replica_qb_c',double(p.ct.initial_replica_qb_c(:)), ...
            'previous_switch_charge_c',zeros(2,1),'command',cmd, ...
            'az',struct('valid',false,'pair_id',-1,'epoch',-1,'age_s',0, ...
            'write_active',false,'write_count',0,'last_write_sample_id',-1, ...
            'last_service_sample_id',-1,'write_source_half_v',zeros(2,1), ...
            'write_elapsed_s',0));
    else
        assert(strcmp(s.schema,'behavior-backend-state/v2')&& ...
            isscalar(s.time_s)&&isfinite(s.time_s)&& ...
            isscalar(s.vx_v)&&isfinite(s.vx_v)&& ...
            isequal(size(s.az_input_half_v),[2 1]), ...
            'behavior:state','Use this kernel retained state.');
    end
    old=s.command;
    useDac=nargin==5&&~isempty(forcing);
    if useDac
        assert(~cold&&old.ra_on&&~old.reset&&isequaln(cmd,old)&& ...
            isinf(p.ra.slew_v_per_s)&&forcing.dt_s==dt&& ...
            forcing.source_time_s==s.time_s&&forcing.sample_id==old.sample_id&&forcing.epoch==old.epoch, ...
            'behaviorDAC:forcingInterval','Forcing must describe this retained linear-RA interval, not a new endpoint command.');
    end
    % A cold AZ-on command is the first endpoint write edge, not a retained
    % interval that was already writing. Cold init has dt0 and never advances a.
    if cold,old.az_on=false;end
    oldTarget=target_parameters(old,p);
    startVx=s.vx_v;
    initialAz=s.az_input_half_v;
    [s,azPole,azAsymptote]=advance_az(s,old.az_on,dt,p);
    % The offset correction is a real stored AZ state, never a vx overwrite.
    % Its exponential variation is convolved analytically with the RA pole.
    if dt==0
        nextVx=startVx;
    elseif old.ra_on&&~old.reset
        factor=oldTarget.finite_gain;
        dcVos=double(p.ra.vos_input_v);
        constant=oldTarget.target_v+oldTarget.noise_gain*dcVos;
        if p.ni.az
            constant=constant-oldTarget.noise_gain*(azAsymptote(1)-azAsymptote(2));
        end
        xinf=factor*constant;
        tau=oldTarget.tau_s;
        if tau==0
            effectiveVos=dcVos;
            if p.ni.az,effectiveVos=effectiveVos-diff_pair(s.az_input_half_v);end
            if useDac
                nextVx=factor*(forcing.q_endpoint_c/p.ra.Cf_f+oldTarget.noise_gain*effectiveVos);
            else
                nextVx=factor*(oldTarget.target_v+oldTarget.noise_gain*effectiveVos);
            end
        else
            e=decay(dt,tau);
            nextVx=xinf+(startVx-xinf)*e;
            if p.ni.az
                amplitudes=-factor*oldTarget.noise_gain* ...
                    [initialAz(1)-azAsymptote(1);-(initialAz(2)-azAsymptote(2))];
                for k=1:2
                    if az_near_pole(tau,azPole(k))
                        nextVx=nextVx+amplitudes(k)*az_near_response(dt,tau,azPole(k));
                    else
                        nextVx=nextVx+amplitudes(k)*exponential_response(dt,tau,azPole(k));
                    end
                end
            end
            if useDac
                for k=1:numel(forcing.delta_q_c)
                    tauD=forcing.tau_dac_s(k);
                    if tauD==0||isinf(tauD)||forcing.delta_q_c(k)==0,continue;end
                    amplitude=factor*(forcing.delta_q_c(k)/p.ra.Cf_f);
                    nextVx=nextVx+amplitude*dac_ramp_response(dt,tau,tauD);
                end
            end
        end
    else
        nextVx=startVx*decay(dt,double(p.ra.tau_reset_s));
    end
    % Endpoint slew cap is an explicit large-signal engineering approximation;
    % it is not the exact solution of a nonlinear slew-limited differential eq.
    maximumChange=double(p.ra.slew_v_per_s)*dt;
    if isfinite(p.ra.slew_v_per_s)
        nextVx=startVx+max(-maximumChange,min(maximumChange,nextVx-startVx));
    end
    s.vx_v=nextVx;s.time_s=s.time_s+dt;
    if useDac
        % The point observation/return uses the FE's componentwise predicted
        % endpoint, not a regrouped exponential charge formula or stale q0.
        old.qres_c=forcing.q_endpoint_c;cmd.qres_c=forcing.q_endpoint_c;
    end
    predicted=observe(s,old,p);
    [main,replica]=switch_networks(cmd,p);
    switchCharge=main.cinc_injected_charge_c+replica.cinc_injected_charge_c;
    kickHalf=zeros(2,1);
    % Reset/off and RA enable capture the pre-switch baseline; this event's kick
    % must remain visible through CINC, rather than being subtracted away.
    if cmd.reset||~cmd.ra_on||(~old.ra_on&&cmd.ra_on)
        s.ct_reset_vx_v=s.vx_v;
    end
    if cmd.ra_on&&~cmd.reset&&p.ni.cinc_kick
        load=output_load(main,replica,p);
        kickHalf=(switchCharge-s.previous_switch_charge_c)./load;
        if any(kickHalf~=0)
            s.vx_v=s.vx_v+diff_pair(kickHalf);
        end
    end
    % A is ideally clamped during reset/off. B keeps its explicit free charge.
    % Baseline follows the actual continuously relaxing output, not its target.
    s=az_latch(s,cmd,p);
    s.previous_switch_charge_c=switchCharge;s.command=cmd;
    actual=observe(s,cmd,p);
    y=actual;y.predicted=predicted;y.actual=actual;
    y.kick_half_v=kickHalf;y.kick_diff_v=diff_pair(kickHalf);
    y.prediction_semantics='predicted=old-command endpoint; actual=new-command endpoint, both behavioral';
    y.units='voltages V; switch charge C; capacitances F; tau s';
    assert(all(isfinite([s.vx_v;s.az_input_half_v;y.vy_v;y.vtop_v])), ...
        'behavior:nonfinite','Behavior kernel produced nonfinite state/output.');
end

function [s,tau,target]=advance_az(s,write,dt,p)
% Exact RC solution of da/dt=(Vos_half+held_source-a)/tau during write.
% A signal reset never clears a; hold leakage uses its separate time constant.
    a=s.az_input_half_v;
    if ~p.ni.az,tau=[Inf;Inf];target=a;return;end
    assert(logical(write)==s.az.write_active,'behavior:azPhaseState', ...
        'Retained AZ phase and old command disagree.');
    if write
        tau=double(p.az.write_tau_s(:));
        target=[p.ra.vos_input_v/2;-p.ra.vos_input_v/2]+s.az.write_source_half_v;
    else
        tau=double(p.az.leak_tau_s(:));target=zeros(2,1);
    end
    if dt==0,return;end
    for k=1:2
        if isinf(tau(k)),continue;end
        a(k)=target(k)+(a(k)-target(k))*decay(dt,tau(k));
    end
    s.az_input_half_v=a;
    if write
        s.az.write_elapsed_s=s.az.write_elapsed_s+dt;
    elseif s.az.valid
        s.az.age_s=s.az.age_s+dt;
    end
end

function s=az_latch(s,c,p)
% Only actual command edges latch a sense-source realization and service tags.
% Metadata can invalidate at epoch changes; analog a is never zeroed here.
    if ~p.ni.az,return;end
    if c.epoch~=s.az.epoch
        s.az.valid=false;s.az.pair_id=-1;s.az.epoch=c.epoch;
        s.az.write_active=false;s.az.age_s=0;s.az.write_elapsed_s=0;
        s.az.last_write_sample_id=-1;s.az.last_service_sample_id=-1;
    end
    if c.sample_id<0
        assert(~c.az_on&&~c.ra_on,'behavior:azService','Active AZ/RA requires a service ID.');
        return;
    end
    if c.sample_id~=s.az.last_service_sample_id
        assert(~s.az.write_active,'behavior:azWriteCrossService','AZ write crossed a CNV service boundary.');
        s.az.last_service_sample_id=c.sample_id;
    end
    pair=floor(c.sample_id/2);
    if c.az_on && ~s.az.write_active
        assert(s.az.last_write_sample_id~=c.sample_id,'behavior:azDuplicateWrite', ...
            'A service may latch its write source only once.');
        paired=any(strcmp(p.az.mode,{'hold','hold_chop'}));
        assert(~paired||mod(c.sample_id,2)==0, ...
            'behavior:azUnexpectedWrite','Paired mode writes only even services; invalid odd services cannot repair a pair.');
        table=double(p.az.sense_injection_half_v);
        column=1+mod(c.sample_id,size(table,2));
        s.az.write_source_half_v=table(:,column);
        s.az.write_active=true;s.az.valid=false;s.az.pair_id=pair;
        s.az.write_elapsed_s=0;s.az.age_s=0;
        s.az.write_count=s.az.write_count+1;
        s.az.last_write_sample_id=c.sample_id;
    elseif ~c.az_on && s.az.write_active
        assert(s.az.write_elapsed_s>0,'behavior:azEmptyWrite','AZ write had no positive physical interval.');
        s.az.write_active=false;s.az.valid=true;s.az.age_s=0;
    end
    if c.ra_on && ~c.reset
        assert(s.az.valid&&s.az.pair_id==pair&&~s.az.write_active, ...
            'behavior:azReadout','RA readout requires a completed AZ write for this pair.');
        if any(strcmp(p.az.mode,{'ordinary','chop'}))
            assert(s.az.last_write_sample_id==c.sample_id,'behavior:azMissingWrite', ...
                'Per-service AZ mode requires this service to write.');
        end
    end
end

function z=target_parameters(c,p)
    z.target_v=c.qres_c/p.ra.Cf_f;
    z.noise_gain=1+c.ctop_f/p.ra.Cf_f;
    if isinf(p.ra.A0),z.finite_gain=1;
    else,z.finite_gain=p.ra.A0/(p.ra.A0+z.noise_gain);end
    z.tau_s=z.noise_gain/(2*pi*p.ra.UGB_hz);
end

function y=observe(s,c,p)
    z=target_parameters(c,p);
    net=select_main(p);
    active=c.ra_on&&~c.reset;
    d=c.d2_signs;t=c.ta_signs;
    if ~active,d=zeros(12,1);t=zeros(7,1);end
    actual=sar20_cdac2_network(net,s.vx_v-s.ct_reset_vx_v,d,t, ...
        p.ct.reference_v,zeros(2,1),s.main_qb_c);
    nominal=sar20_cdac2_network(p.ct.net_nominal,0,d,t,p.ct.reference_v);
    y=struct('vx_v',s.vx_v,'vy_v',double(active)*actual.vy, ...
        'vtop_v',(s.vx_v-z.target_v)/z.noise_gain, ...
        'target_v',z.target_v,'noise_gain',z.noise_gain,'finite_gain',z.finite_gain, ...
        'tau_ra_s',z.tau_s,'cinc_alpha',actual.alpha, ...
        'dac2_actual_ra_v',actual.dac_ra_v,'tracking_actual_ra_v',actual.track_ra_v, ...
        'dac2_nominal_ra_v',nominal.dac_ra_v,'tracking_nominal_ra_v',nominal.track_ra_v, ...
        'ct_nodes_half_v',actual.nodes_delta_v,'az_input_half_v',s.az_input_half_v, ...
        'time_s',s.time_s,'ra_on',active);
    y.az=s.az;
    y.az.sense_error_v=p.ra.vos_input_v-diff_pair(s.az_input_half_v);
    y.az.sense_error_with_source_v=y.az.sense_error_v+diff_pair(s.az.write_source_half_v);
    if ~active,y.ct_nodes_half_v(:,1)=0;end
end

function [main,replica]=switch_networks(c,p)
    d=c.d2_signs;t=c.ta_signs;
    if ~c.ra_on||c.reset,d=zeros(12,1);t=zeros(7,1);end
    main=sar20_cdac2_network(select_main(p),0,d,t,p.ct.reference_v);
    factor=double(p.ct.replica_enabled);
    replicaNet=p.ct.net_replica;
    if ~p.ni.cap_mismatch,replicaNet=p.ct.net_nominal;end
    replica=sar20_cdac2_network(replicaNet,0,-factor*d,-factor*t,p.ct.reference_v);
end
function n=select_main(p)
    if p.ni.cap_mismatch,n=p.ct.net_actual;else,n=p.ct.net_nominal;end
end
function c=output_load(main,replica,p)
    c=double(p.ct.output_parasitic_half_f(:))+ ...
        main.ra_load_per_output_f+replica.ra_load_per_output_f;
    assert(all(isfinite(c)&c>0),'behavior:load','Positive effective output loads required.');
end
function v=diff_pair(x),v=x(1)-x(2);end
function e=decay(dt,tau)
    if dt==0,e=1;elseif tau==0,e=0;elseif isinf(tau),e=1;else,e=exp(-dt/tau);end
end
function k=exponential_response(dt,tau,tauInput)
    if dt==0||tauInput==0,k=0;
    elseif isinf(tauInput),k=-expm1(-dt/tau);
    elseif tauInput==tau,k=(dt/tau)*exp(-dt/tau);
    else
        q=dt*(1/tau-1/tauInput);
        if abs(q)<0.5
            k=exp(-dt/tau)*expm1(q)/(1-tau/tauInput);
        else,k=tauInput/(tauInput-tau)*(decay(dt,tauInput)-decay(dt,tau));end
    end
end
function yes=az_near_pole(tau,tauInput)
% AZ-only gate. Exact, zero, Inf and non-near poles keep the original H call.
    yes=isfinite(tau)&&tau>0&&isfinite(tauInput)&&tauInput>0&& ...
        tauInput~=tau&&abs(tauInput-tau)<=max(tauInput,tau)*2^-20;
end
function k=az_near_response(dt,tau,tauInput)
% Stable AZ-only near-pole response; match the separately tested 074118 core.
    x=dt/tau;
    if isinf(x)
        k=0;
    else
        if x>700,base=exp(log(x)-x);else,base=x*exp(-x);end
        if base==0
            k=0;
        else
            d=x-dt/tauInput;
            if d==0,k=base;else,k=base*(expm1(d)/d);end
        end
    end
end
function r=dac_ramp_response(dt,tauR,tauD)
% Convolution of (1-exp(-t/tauD)) with the existing unit-gain RA pole.
% Reuse AZ exponential_response; a small-argument series prevents cancellation
% of two O(dt) terms when the physical response is O(dt^2).
    x=dt/tauR;y=dt/tauD;
    if max(x,y)<0.01
        r=0;denominator=1;
        for degree=2:12
            denominator=denominator*degree;
            homogeneous=0;
            for k=0:degree-2,homogeneous=homogeneous+x^k*y^(degree-2-k);end
            r=r+((-1)^degree)*(x*y)*homogeneous/denominator;
        end
    elseif isinf(x)
        r=-expm1(-y);
    elseif isinf(y)
        r=-expm1(-x);
    elseif abs(x-y)<0.5
        % Only the NEW DAC response takes this jointly rounded pole difference.
        % Keep the legacy AZ H unchanged, including the entire off path.
        d=x-y;
        if d==0,H=x*exp(-x);
        else,H=x*exp(-x)*expm1(d)/d;end
        r=-expm1(-x)-H;
    elseif min(x,y)>0.1
        r=-expm1(-x)-exponential_response(dt,tauR,tauD);
    else
        % Widely separated poles: avoid subtracting two almost equal O(1)
        % terms when one input pole is much slower than the RA.
        r=(-x*expm1(-y)+y*expm1(-x))/(x-y);
    end
end

function c=normalize_command(c)
    c.d2_signs=double(c.d2_signs(:));c.ta_signs=double(c.ta_signs(:));
    c.ra_on=logical(c.ra_on);c.az_on=logical(c.az_on);c.reset=logical(c.reset);
    if ~isfield(c,'sample_id'),c.sample_id=-1;end
    if ~isfield(c,'epoch'),c.epoch=0;end
    c.sample_id=double(c.sample_id);c.epoch=double(c.epoch);
end
function validate_inputs(c,dt,p)
    fields={'qres_c','ctop_f','d2_signs','ta_signs','ra_on','az_on','reset'};
    assert(isstruct(c)&&isscalar(c)&&all(isfield(c,fields)), ...
        'behavior:command','Supply the complete named command.');
    assert(isnumeric(dt)&&isreal(dt)&&isscalar(dt)&&isfinite(dt)&&dt>=0, ...
        'behavior:dt','dt must be finite nonnegative seconds.');
    assert(isscalar(c.qres_c)&&isscalar(c.ctop_f)&& ...
        isreal(c.qres_c)&&isreal(c.ctop_f)&&all(isfinite([c.qres_c;c.ctop_f]))&&c.ctop_f>=0, ...
        'behavior:charge','qres [C] and nonnegative total Ctop [F] must be explicit scalars.');
    assert(numel(c.d2_signs)==12&&numel(c.ta_signs)==7&& ...
        all(ismember([c.d2_signs(:);c.ta_signs(:)],[-1 0 1])), ...
        'behavior:signs','Require twelve D2 and seven TA physical signs.');
    flags=[c.ra_on;c.az_on;c.reset];
    assert(numel(flags)==3&&all(ismember(flags,[0 1])), ...
        'behavior:flags','ra_on/az_on/reset must be scalar booleans.');
    assert(isstruct(p)&&strcmp(p.schema,'behavior-backend-parameters/v1')&& ...
        isscalar(p.ra.A0)&&p.ra.A0>0&&isscalar(p.ra.UGB_hz)&&p.ra.UGB_hz>0&& ...
        isscalar(p.ra.Cf_f)&&isfinite(p.ra.Cf_f)&&p.ra.Cf_f>0&& ...
        isscalar(p.ra.tau_reset_s)&&isfinite(p.ra.tau_reset_s)&&p.ra.tau_reset_s>=0&& ...
        isscalar(p.ra.slew_v_per_s)&&p.ra.slew_v_per_s>0&& ...
        isscalar(p.ra.vos_input_v)&&isfinite(p.ra.vos_input_v), ...
        'behavior:parameters','Invalid explicit RA engineering parameters.');
    allowed={'cap_mismatch','cinc_kick','az','ra_noise','az_noise', ...
        'reference_noise','nonlinear_ra','replica_delay'};
    assert(isequal(sort(fieldnames(p.ni)),sort(allowed(:))), ...
        'behavior:niSchema','Unknown or missing NI flag.');
    for k=1:numel(allowed)
        v=p.ni.(allowed{k});assert(isscalar(v)&&ismember(v,[0 1]),'behavior:niFlag','NI flags must be booleans.');
    end
    unsupported={'ra_noise','az_noise','reference_noise','nonlinear_ra','replica_delay'};
    for k=1:numel(unsupported)
        assert(~p.ni.(unsupported{k}),'behavior:unsupportedNI', ...
            'NI %s is not implemented in this deterministic kernel.',unsupported{k});
    end
    for name={'write_tau_s','leak_tau_s'}
        v=p.az.(name{1});assert(numel(v)==2&&isreal(v)&&all(~isnan(v(:))&v(:)>=0), ...
            'behavior:azTau','AZ tau must contain two nonnegative seconds values.');
    end
    assert(numel(p.az.target_input_half_v)==2&&numel(p.az.initial_input_half_v)==2&& ...
        all(isfinite([p.az.target_input_half_v(:);p.az.initial_input_half_v(:)])), ...
        'behavior:az','AZ requires two finite input-referred half voltages.');
    assert(isscalar(p.ct.reference_v)&&isfinite(p.ct.reference_v)&&p.ct.reference_v>0&& ...
        numel(p.ct.output_parasitic_half_f)==2&& ...
        all(isfinite(p.ct.output_parasitic_half_f(:))&p.ct.output_parasitic_half_f(:)>=0)&& ...
        numel(p.ct.initial_main_qb_c)==2&&numel(p.ct.initial_replica_qb_c)==2&& ...
        all(isfinite([p.ct.initial_main_qb_c(:);p.ct.initial_replica_qb_c(:)]))&& ...
        isscalar(p.ct.replica_enabled)&&ismember(p.ct.replica_enabled,[0 1]), ...
        'behavior:ctParameters','Invalid CT reference/load/initial charge/replica parameters.');
    modes={'off','ordinary','chop','hold','hold_chop'};
    assert(isfield(p.az,'mode')&&any(strcmp(p.az.mode,modes))&& ...
        logical(p.ni.az)==~strcmp(p.az.mode,'off'), ...
        'behavior:azMode','AZ mode and ni.az flag must agree.');
    assert(~c.az_on||p.ni.az,'behavior:azOffWrite','AZoff cannot receive write commands.');
    if p.ni.az
        assert(all(isfield(c,{'sample_id','epoch'}))&&isscalar(c.sample_id)&& ...
            isfinite(c.sample_id)&&c.sample_id>=-1&&c.sample_id==floor(c.sample_id)&& ...
            isscalar(c.epoch)&&isfinite(c.epoch)&&c.epoch>=0&&c.epoch==floor(c.epoch), ...
            'behavior:azTags','AZ requires integer sample_id>=-1 and epoch>=0.');
        assert(~(c.az_on&&c.ra_on),'behavior:azReadoutCollision','AZ write and RA readout cannot overlap.');
        assert(all(isfinite(p.az.write_tau_s(:))&p.az.write_tau_s(:)>0), ...
            'behavior:azFiniteWrite','AZ requires a positive finite write tau; no ideal state assignment.');
        assert(all(p.az.target_input_half_v(:)==0),'behavior:azLegacyTarget', ...
            'Independent ideal correction targets are forbidden; AZ senses the analog Vos source.');
        v=p.az.sense_injection_half_v;
        assert(isa(v,'double')&&isreal(v)&&size(v,1)==2&&size(v,2)>=1&& ...
            all(isfinite(v(:))),'behavior:azSenseSource', ...
            'Use an explicit finite 2-by-K deterministic input-referred sense-injection table.');
    end
    assert(exist('sar20_cdac2_network','file')==2,'behavior:dependency', ...
        'Add the existing current/matlab folder containing sar20_cdac2_network.m.');
end
