function report=sb_validate_plain(out,P)
% Actual logged event/RAW/return-voltage checks; no hidden FE state claimed.
    assert(isa(out,'Simulink.SimulationOutput')&&isempty(out.ErrorMessage),'sbN8:output','Need error-free actual output.');
    [te,e]=sb_series(out,'event_log',2);[tr,raw]=sb_series(out,'raw_log',6);
    [ty,ready]=sb_series(out,'ready_log',1);[tc,ctrl]=sb_series(out,'control_log',13);
    [tb,back]=sb_series(out,'back_log',8);[tv,route]=sb_series(out,'az_route_log',6);
    for axis={tr,ty,tc,tb,tv}
        assert(sb_same_bits(te,axis{1}),'sbN8:axis','Actual log time axes differ.');
    end
    G=numel(P.groups);cycles=P.schedule.n_cycles;
    assert(G==48&&cycles==12&&isequal(e,[repelem((0:cycles-1).',G) repmat((1:G).',cycles,1)]), ...
        'sbN8:events','Need exactly 12 x 48 actual event groups.');
    expectTime=zeros(size(te));rawRows=false(size(te));releaseRows=false(size(te));
    inventory=zeros(1,5);
    for g=1:G
        items=P.groups(g).events;types={items.type};mask=e(:,2)==g;
        expectTime(mask)=e(mask,1)*P.Ts_s+P.groups(g).time_s;
        rawRows(mask)=any(strcmp(types,'raw_latch'));releaseRows(mask)=any(strcmp(types,'release'));
        keys={'d2_decide','d2_feedback','ta_compare','ta_feedback','raw_latch'};
        for k=1:numel(keys),inventory(k)=inventory(k)+sum(strcmp(types,keys{k}));end
    end
    assert(sb_same_bits(te,expectTime)&&isequal(inventory,[12 12 8 7 1]), ...
        'sbN8:calendar','Actual time axis or scheduled token inventory differs.');
    assert(isequal(double(ready),double(rawRows))&&nnz(rawRows)==cycles&&nnz(releaseRows)==cycles, ...
        'sbN8:ready','Actual RawReady or release count differs.');
    r=raw(rawRows,:);c=ctrl(rawRows,:);
    assert(isequal(r(:,4),(0:cycles-1).')&&all(r(:,5)==P.epoch)&&all(r(:,6)==1)&& ...
        isequal(r(:,1:3),c(:,5:7))&&all(c(:,8)==1), ...
        'sbN8:raw','Actual RAW/ID/valid/control must match on every cycle.');
    selection=r(:,4)>=P.first_id&r(:,4)<P.first_id+P.N;
    assert(nnz(selection)==8&&isequal(r(selection,4),(4:11).'), ...
        'sbN8:selected','Require all eight selected actual IDs 4–11.');
    pol=route(releaseRows,1);expected=back(releaseRows,3);expected(pol<0)=-expected(pol<0);
    assert(sb_same_bits(route(releaseRows,6),expected), ...
        'sbN8:returnRoute','Actual return Vtop is not the routed backend coordinate.');
    report=struct('status','plain_logged_checks_pass','cycles',cycles,'event_rows',size(e,1), ...
        'all_raw',r,'selected_raw',r(selection,:), ...
        'scheduled_tokens_per_cycle',inventory,'actual_feedback_counts','UNOBSERVED_WITH_TAP_OFF', ...
        'return_vtop','OBSERVED_RETURN_CONTEXT_VERSUS_BACK_LOG', ...
        'release_charge','UNOBSERVED_NO_DIRECT_FE_STATE_PROBE', ...
        'scope','Actual event/RAW wires plus schedule; not committed FE state or paper performance.');
end
