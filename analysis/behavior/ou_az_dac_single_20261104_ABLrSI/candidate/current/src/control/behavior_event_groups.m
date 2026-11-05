function groups = behavior_event_groups(events,includeFrameReady)
%BEHAVIOR_EVENT_GROUPS Group exact calendar ticks into one scheduler hit.
%
%   groups = behavior_event_groups(events, includeFrameReady)
%
% INPUTS
%   events             struct array from behavior_calendar with tick/priority/time_s
%   includeFrameReady  optional logical (default false). When true, a frame_ready
%                      event at +138 ns (tick 552, priority 70) is appended so the
%                      router can see it. The router must NOT send that event to
%                      sar_step; it is a framing signal, not a conversion step.
%
% OUTPUT
%   groups   relative time_s / offset_s [s], tick (250 ps count), and the events
%            of that exact tick. Grouping is by EXACT tick equality: no epsilon
%            time matching, and the model timing comes from the calendar rather
%            than being inferred here.
%
% Pure sort/group conversion: no reset, no RNG, no state.
    if nargin<2
        includeFrameReady=false;
    end
    assert(islogical(includeFrameReady)&&isscalar(includeFrameReady), ...
        'behavior:groups:frameFlag','includeFrameReady must be scalar logical.');
    assert(isstruct(events)&&all(isfield(events,{'tick','priority','time_s'})), ...
        'behavior:groups:events','Require behavior_calendar events.');
    if includeFrameReady
        assert(~isempty(events),'behavior:groups:empty','A CNV calendar is required for frame grouping.');
        e=events(1);e.time_s=138e-9;e.offset_s=e.time_s;e.tick=552;
        e.type='frame_ready';e.index=-1;e.bit=-1;e.priority=70;events(end+1,1)=e;
    end
    proto=struct('time_s',0,'offset_s',0,'tick',0,'events',events([]));
    groups=repmat(proto,0,1);
    if isempty(events)
        return;
    end
    % Order by tick, then by priority. Coarse priority decides which events run
    % first inside the same tick; the tick alone is the grouping key.
    [~,ix]=sortrows([[events.tick].' [events.priority].'],[1 2]);
    events=events(ix);
    first=1;
    while first<=numel(events)
        last=first;
        while last<numel(events) && events(last+1).tick==events(first).tick
            last=last+1;
        end
        g=proto;
        g.time_s=events(first).time_s;
        g.offset_s=g.time_s;
        g.tick=events(first).tick;
        g.events=events(first:last);
        groups(end+1,1)=g;
        first=last+1;
    end
end
