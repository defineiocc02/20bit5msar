function events = behavior_calendar(p)
%BEHAVIOR_CALENDAR Build the fixed CNV-relative conversion event calendar.
%Version: v1 (2026-10-27). Caller: behavior initializer before event_groups/source.
%Input p.sample_period_s [s] (200 ns); output events with time_s/offset_s [s],
%tick [250 ps count], zero-based index/bit (-1 unused), type and integer priority.
%Equal-time order: CNV, due feedback, coarse latch, prepare, compare, completion.
%Stateless; caller attaches absolute_time_s/sample_id/epoch; no reset or RNG.
%Model: fixed coarse6/fine5, D2-12 and TA8/feedback7 timing; acquisition/Tx
%are separate scheduler responsibilities, not implicit events in this calendar.
    assert(isstruct(p)&&isscalar(p),'behavior:calendar:parameters','p must be a scalar struct.');
    if isfield(p,'sample_period_s')
        assert(abs(p.sample_period_s-200e-9)<1e-18,'behavior:calendar:period','Require 200 ns CNV period.');
    end
    proto=struct('time_s',0,'offset_s',0,'tick',0,'type','','index',-1,'bit',-1,'priority',0);
    events=repmat(proto,0,1);
    add(0,'cnv',-1,-1,0);
    add(12.5,'coarse_latch',-1,-1,20);
    for k=0:4
        add(12.5+3.75*k,'fine_prepare',k,4-k,30);
        add(15+3.75*k,'fine_decide',k,4-k,40);
        add(16.25+3.75*k,'fine_feedback',k,4-k,10);
    end
    add(31.25,'ra_start',-1,-1,60);
    for k=0:11
        add(43.75+2.5*k,'d2_prepare',k,11-k,30);
        add(45+2.5*k,'d2_decide',k,11-k,40);
        add(46.25+2.5*k,'d2_feedback',k,11-k,10);
    end
    add(73.75,'d2_end',-1,-1,60);
    for m=0:7
        add(75+1.25*m,'ta_compare',m,7-m,40);
        if m<7,add(76.25+1.25*m,'ta_feedback',m,7-m,10);end
    end
    add(85,'tracking_end',-1,-1,60);
    add(86.25,'raw_latch',-1,-1,80);
    add(90,'release',-1,-1,90);
    [~,order]=sortrows([[events.tick].' [events.priority].'],[1 2]);
    events=events(order);
    function add(ns,type,index,bit,priority)
        e=proto;e.time_s=ns*1e-9;e.offset_s=e.time_s;
        e.tick=round(ns/0.25);e.type=type;e.index=index;e.bit=bit;e.priority=priority;
        events(end+1,1)=e;
    end
end
