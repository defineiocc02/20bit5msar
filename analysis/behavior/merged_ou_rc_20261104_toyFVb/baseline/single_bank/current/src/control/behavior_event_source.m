function behavior_event_source(block)
%BEHAVIOR_EVENT_SOURCE Emit one variable-time scheduler hit per exact event group.
%Version: v1 (2026-10-27). Caller: Level-2 MATLAB S-Function block in behavior model.
%Dialog P: sample_period_s [s]=200 ns, n_cycles [integer], groups, optional stop_time_s [s].
%Output double[2]=[zero-based cycle_id; one-based group_index]; no input ports.
%No DWork/Update: Outputs derives its event from CurrentTime and an immutable
%calendar, so repeated Outputs before/after any Update at the same t are stable.
%No analog/SAR reset, RNG or hidden cache; no epsilon or event-time shift.
%Sample time [-2 0]; optional frame_ready +138 ns is routed outside sar_step.
%Model is a declared calendar, not base-rate polling; native Simulink compile/run
%is still required. API: mathworks.com/help/simulink/sfg/mdlgettimeofnextvarhit.html
    block.NumDialogPrms=1;
    block.DialogPrmsTunable={'Nontunable'};
    P=block.DialogPrm(1).Data;
    validate_parameters(P);
    period=double(P.sample_period_s);
    offsets=reshape(double([P.groups.time_s]),[],1);
    groupCount=numel(offsets);
    hitTimes=reshape(offsets+(0:double(P.n_cycles)-1)*period,[],1);
    assert(all(diff(hitTimes)>0),'behavior:source:calendarOrder','Absolute event times must increase strictly.');
    if isfield(P,'stop_time_s'),stopTime=double(P.stop_time_s);
    else,stopTime=double(P.n_cycles)*period;end
    lastHit=(double(P.n_cycles)-1)*period+offsets(end);
    assert(isscalar(stopTime)&&isfinite(stopTime)&&stopTime>=lastHit, ...
        'behavior:source:stopTime','stop_time_s must include the final scheduled hit.');
    block.NumInputPorts=0;block.NumOutputPorts=2;
    block.SetPreCompPortInfoToDefaults;
    block.OutputPort(1).Dimensions=2;
    block.OutputPort(1).DatatypeID=0;
    block.OutputPort(1).Complexity='Real';
    block.OutputPort(1).SamplingMode='Sample';
    block.OutputPort(2).Dimensions=1;block.OutputPort(2).DatatypeID=0;
    block.OutputPort(2).Complexity='Real';block.OutputPort(2).SamplingMode='Sample';
    block.SampleTimes=[-2 0];
    block.NumContStates=0;
    block.SimStateCompliance='DefaultSimState';
    block.RegBlockMethod('Start',@start);
    block.RegBlockMethod('Outputs',@outputs);

    function start(b)
        assert(b.CurrentTime==0,'behavior:source:start','Event source requires model StartTime=0.');
    end
    function outputs(b)
        now=b.CurrentTime;
        % The same physical t always selects the same event, independently of
        % the engine's Outputs/Update evaluation count or external state delay.
        ordinal=find(hitTimes<=now,1,'last');
        assert(~isempty(ordinal),'behavior:source:beforeStart','CurrentTime precedes the first event.');
        hit=ordinal-1;
        cycle=floor(hit/groupCount);group=mod(hit,groupCount)+1;
        b.OutputPort(1).Data=[cycle;group];
        b.OutputPort(2).Data=1-2*mod(hit,2);
        future=find(hitTimes>now,1,'first');
        if isempty(future),nextHit=stopTime+period;else,nextHit=hitTimes(future);end
        assert(nextHit>now,'behavior:source:strictFuture', ...
            'NextTimeHit must be strictly future; no epsilon or shifted event is permitted.');
        b.NextTimeHit=nextHit;
    end
end

function validate_parameters(P)
    assert(isstruct(P)&&isscalar(P)&&all(isfield(P,{'sample_period_s','n_cycles','groups'})), ...
        'behavior:source:parameters','P requires sample_period_s, n_cycles and groups.');
    assert(isscalar(P.sample_period_s)&&isfinite(P.sample_period_s)&& ...
        abs(double(P.sample_period_s)-200e-9)<1e-18, ...
        'behavior:source:period','Require sample_period_s=200 ns.');
    assert(isscalar(P.n_cycles)&&isfinite(P.n_cycles)&&P.n_cycles>=1&& ...
        P.n_cycles==floor(P.n_cycles), ...
        'behavior:source:cycles','n_cycles must be a positive integer including warmup and flush.');
    assert(isstruct(P.groups)&&~isempty(P.groups)&&all(isfield(P.groups,{'time_s','events'})), ...
        'behavior:source:groups','Require ordered grouped event structs.');
    times=double([P.groups.time_s]);
    assert(isreal(times)&&all(isfinite(times))&&times(1)==0&& ...
        all(diff(times)>0)&&times(end)<P.sample_period_s, ...
        'behavior:source:offsets','Group times must start at zero and increase strictly within one CNV period.');
end
