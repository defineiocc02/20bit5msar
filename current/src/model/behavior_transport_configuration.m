function P=behavior_transport_configuration(P)
%BEHAVIOR_TRANSPORT_CONFIGURATION Derive PUBLIC transport parameters and IC.
%
%   P = behavior_transport_configuration(P)
%
% Called by engineering prepare AFTER the actual groups/cycles/stop/plan exist.
% This function derives transport configuration ONLY; it never rebuilds the
% schedule.
%
% OWNS
%   P.transport.enabled / core / public_en / startup_en / kind_by_group / log controls
%   and the single P.xTX0 initial condition (97 doubles). There is deliberately
%   no transport.xTX0 alias, and no RefQueue.
%
% NEVER TOUCHES
%   groups, calendar, cycles, stop, plan, or any FE/BK/SAR state. Actual event
%   timing comes from the standard Clock, never from a kind table or sample-ID
%   arithmetic.
%
% ON
%   Replays a bounded, explicit public EN prehistory ending before -Ts, then
%   verifies the derived epoch equals P.epoch. A hidden epoch is never assigned
%   into RX.
%
% OFF
%   Holds an opaque existing finite-97 IC, or finite zeros when absent. The
%   Enabled digital subsystem must not execute, so OFF does not replay or
%   initialise cores at all.
    assert(isstruct(P)&&isscalar(P)&&all(isfield(P,{'Ts_s','N','first_id','epoch','groups','n_cycles','stop_time_s','schedule'})), ...
        'transportConfig:P','Need engineering-prepared schedule and public labels.');
    assert(isequal(double(P.Ts_s),200e-9),'transportConfig:period','Require declared200ns public CNV period.');
    if ~isfield(P,'transport'),P.transport=struct('enabled',false);end
    tr=P.transport;assert(isstruct(tr)&&isscalar(tr)&&isfield(tr,'enabled')&& ...
        isscalar(tr.enabled)&&isreal(tr.enabled)&&ismember(tr.enabled,[0 1]), ...
        'transportConfig:enabled','Explicit transport.enabled logical required.');
    assert(~isfield(tr,'xTX0'),'transportConfig:ICOwner','Use the single P.xTX0 IC; no transport.xTX0 alias.');
    on=logical(tr.enabled);
    core=behavior_transport_config();
    if isfield(tr,'core')
        assert(isequaln(tr.core,core),'transportConfig:core', ...
            'Do not silently change public protocol constants.');
    end
    tr.enabled=on;
    tr.core=core;
    if ~isfield(tr,'public_en')
        tr.public_en=10;
    end
    assert(isnumeric(tr.public_en)&&isreal(tr.public_en)&&isscalar(tr.public_en)&& ...
        isfinite(tr.public_en)&&any(tr.public_en==[10 4]), ...
        'transportConfig:EN','Predeclare public normal1010 or test0100 EN.');
    if ~isfield(tr,'trace_enabled'),tr.trace_enabled=false;end
    assert(isscalar(tr.trace_enabled)&&isreal(tr.trace_enabled)&&ismember(tr.trace_enabled,[0 1]), ...
        'transportConfig:trace','trace_enabled must be explicit logical.');
    tr.trace_enabled=logical(tr.trace_enabled);
    assert(~tr.trace_enabled||P.N==8,'transportConfig:traceN8','Full pin trace logging is restricted to explicit N8.');
    groups=P.groups;assert(isstruct(groups)&&all(isfield(groups,{'events','time_s'}))&& ...
        numel(groups)==48+double(on),'transportConfig:groups','Engineering prepare must supply exactly48 bypass or49 transport groups.');
    kinds=zeros(numel(groups),1);
    for g=1:numel(groups)
        events=groups(g).events;
        assert(isstruct(events)&&all(isfield(events,'type')), ...
            'transportConfig:tokens','Group lacks actual event type.');
        % Classify this group by which transport token it carries. A group may
        % carry at most one of cnv / raw_latch / frame_ready.
        tokens={events.type};
        values=zeros(1,numel(tokens));
        values(strcmp(tokens,'cnv'))=1;
        values(strcmp(tokens,'raw_latch'))=2;
        values(strcmp(tokens,'frame_ready'))=3;
        selected=values(values~=0);
        assert(numel(selected)<=1,'transportConfig:ambiguousKind', ...
            'CNV/raw_latch/frame_ready must not collide or repeat in one group.');
        if ~isempty(selected)
            kinds(g)=selected;
        end
    end
    assert(nnz(kinds==1)==1&&nnz(kinds==2)==1&&nnz(kinds==3)==double(on), ...
        'transportConfig:kindCounts','Need exact actual tokens cnv/raw_latch and ON-only frame_ready.');
    assert(groups(find(kinds==1,1)).time_s==0,'transportConfig:cnvPhase','Declared CNV group must be offset0.');
    if on
        assert(find(kinds==3,1)==49&&abs(groups(49).time_s-core.tx.final_fall_s)<=1e-15&& ...
            numel(groups(49).events)==1,'transportConfig:closePhase','Engineering group49 must contain only frame_ready at138ns.');
    end
    % Verify engineering's flush/stop contract, NEVER normalize it here.
    expectedCycles=P.first_id+P.N+double(on)*core.tx.latency_samples;
    assert(P.n_cycles==expectedCycles,'transportConfig:flush','Engineering must supply exactly two additional ON CNV flush slots.');
    expectedStop=(P.n_cycles-1)*P.Ts_s+groups(end).time_s;
    assert(abs(P.stop_time_s-expectedStop)<=1e-15&&isequaln(P.schedule.groups,groups)&& ...
        P.schedule.n_cycles==P.n_cycles&&P.schedule.sample_period_s==P.Ts_s&& ...
        P.schedule.stop_time_s==P.stop_time_s,'transportConfig:schedule','Prepared schedule/stop must already match actual groups.');
    if on
        assert(isfield(P,'front')&&isfield(P.front,'plan')&&size(P.front.plan,1)>=P.n_cycles+1, ...
            'transportConfig:plan','Public plan must already cover flush plus next acquisition; no extension/reseed here.');
        assert(isnumeric(P.epoch)&&isreal(P.epoch)&&isscalar(P.epoch)&&isfinite(P.epoch)&& ...
            P.epoch==floor(P.epoch)&&P.epoch>=1&&P.epoch<=16, ...
            'transportConfig:epochBound','This prototype supports startup epochs1..16 only; reject larger epochs before allocation.');
        if ~isfield(tr,'startup_en')||isempty(tr.startup_en)
            % Bounded PUBLIC stimulus: one reset-entry per declared generation.
            % One reset-entry per declared generation, ending just before -Ts.
            % The final level is the public EN value so the prehistory settles
            % into the run's own protocol rather than a hard-coded constant.
            count=2*double(P.epoch);
            last=-P.Ts_s-100e-9;
            times=last-((count-1):-1:0).'*100e-9;
            levels=repmat([0;10],P.epoch,1);
            levels(end)=tr.public_en;
            tr.startup_en=[times,levels];
        end
        e=tr.startup_en;
        assert(isnumeric(e)&&isreal(e)&&size(e,2)==2&&size(e,1)>=2&&size(e,1)<=32&& ...
            all(isfinite(e(:)))&&all(e(:,1)<-P.Ts_s)&&e(end,2)==tr.public_en, ...
            'transportConfig:startupBound','Explicit startup EN must be at most32 events, finish strictly before -Ts and end at public_en.');
        [P.xTX0,info]=behavior_transport_init(core,e);
        assert(info.epoch_from_public_EN==P.epoch,'transportConfig:epochJoin', ...
            'Public EN reset history does not match ADC declared epoch; do not relabel/seed RX.');
        tr.boot_pin_trace=info.boot_pin_trace;
    else
        if ~isfield(P,'xTX0'),P.xTX0=zeros(97,1);end
        assert(isa(P.xTX0,'double')&&isreal(P.xTX0)&&isequal(size(P.xTX0),[97 1])&&all(isfinite(P.xTX0)), ...
            'transportConfig:opaqueIC','OFF opaque initial97 must remain finite and held, never executed.');
    end
    tr.kind_by_group=kinds;tr.log_points=1;tr.trace_max_points=1;
    if on,tr.log_points=Inf;if tr.trace_enabled,tr.trace_max_points=Inf;end,end
    P.transport=tr;
end
