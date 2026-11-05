function out=ra_dense_from_tap(P,physical_state_tap,sampleId,queryTimes,candidateRoot)
%RA_DENSE_FROM_TAP Select two actual rows from the 2015-column trace.
% Trace layout was separately specified in layout.json SHA-256
% fab1aa95520b2e9af897cfe93e539083c8b3afbb8524bae5eedb574559393b31.
% This wrapper reads supplied data only, never runs or modifies the model.
% The input is still required to be bound externally to the actual model,
% parameters, source manifest, run ID and baseline-vs-tapped equivalence.
    assert(isa(physical_state_tap,'timeseries'),'raDense:tapType','Expected physical_state_tap timeseries.');
    assert(isa(sampleId,'double')&&isreal(sampleId)&&isscalar(sampleId)&& ...
        isfinite(sampleId)&&sampleId>=0&&sampleId==floor(sampleId), ...
        'raDense:sample','sampleId must be an exact nonnegative double integer.');
    t=physical_state_tap.Time(:);d=physical_state_tap.Data;
    assert(isa(t,'double')&&isreal(t)&&all(isfinite(t))&&isa(d,'double')&&isreal(d), ...
        'raDense:tapType','Trace Time/Data must be real binary64.');
    if physical_state_tap.IsTimeFirst
        x=reshape(d,numel(t),[]);
    else
        x=reshape(permute(d,[ndims(d) 1:ndims(d)-1]),numel(t),[]);
    end
    assert(isequal(size(x),[numel(t),2015])&&all(isfinite(x(:,1:2)),'all'), ...
        'raDense:tapShape','Trace needs 2015 columns and finite event IDs.');
    groups=P.groups;
    g0=find(arrayfun(@(g)any(strcmp({g.events.type},'ra_start')),groups));
    assert(isscalar(g0)&&g0<numel(groups),'raDense:tapEvent','Missing unique ra_start.');
    i=find(x(:,1)==sampleId & x(:,2)==g0);
    j=find(x(:,1)==sampleId & x(:,2)==g0+1);
    assert(isscalar(i)&&isscalar(j)&&j==i+1,'raDense:tapEvent', ...
        'Require exactly one ra_start row followed by the first D2 prepare row.');
    record=struct('t_start_s',t(i),'t_stop_s',t(j), ...
        'fe_after_start353',x(i,1415:1767).', ...
        'ra_after_start48',x(i,1960:2007).', ...
        'fe_old_at_stop353',x(j,3:355).', ...
        'ra_old_at_stop48',x(j,1768:1815).', ...
        'ra_advance_stop48',x(j,1816:1863).', ...
        'ra_advance_obs_stop8',x(j,2008:2015).');
    out=ra_dense_observer(P,record,queryTimes,candidateRoot);
    assert(out.sample_id==sampleId,'raDense:tapEvent','Recorded RA command/sample row mismatch.');
    out.trace_variable='physical_state_tap';
    out.trace_width=2015;
    out.ra_start_row=i;out.first_d2_prepare_row=j;
    out.layout_sha256='fab1aa95520b2e9af897cfe93e539083c8b3afbb8524bae5eedb574559393b31';
end
