function behavior_aperture_tap_sfun(b)
%BEHAVIOR_APERTURE_TAP_SFUN Read-only real capture observation, 28 doubles.
% Parameter P: only debug.aperture_enabled/N/groups/front.schema are read.
% Inputs: Sample.next353 AFTER capture/join/open-next, Event2=[cycle;group].
% Output at CNV only: [id;epoch;valid;nominalCNV;IDs8;tAp8;tOpen8], seconds.
% IDs come from actual valid capture tags, ascending; accepts phase2 or phase3.
% Disabled/non-CNV allNaN. No state, Update, DWork, UserData, RNG or mutation.
% ToWorkspace MaxDataPoints is set by caller using debug.aperture_max_points;
% this pure block does not count, store, truncate or advance sample ownership.
    b.NumDialogPrms=1;b.DialogPrmsTunable={'Nontunable'};p=b.DialogPrm(1).Data;
    assert(isfield(p,'debug')&&isfield(p.debug,'aperture_enabled')&& ...
        isscalar(p.debug.aperture_enabled)&&ismember(p.debug.aperture_enabled,[0 1]), ...
        'aperture:debug','Explicit P.debug.aperture_enabled required.');
    enabled=logical(p.debug.aperture_enabled);
    assert(~enabled||p.N==8,'aperture:debugN8','Full aperture observation is restricted to N8.');
    cnvGroup=false(numel(p.groups),1);
    for g=1:numel(p.groups)
        cnvGroup(g)=any(strcmp({p.groups(g).events.type},'cnv'));
    end
    % Unpack needs only schema; observer neither accesses nor stores analog C.
    feSchema=struct('schema',p.front.schema);
    b.NumInputPorts=2;b.NumOutputPorts=1;b.SetPreCompPortInfoToDefaults;
    widths=[353 2];
    for k=1:2
        b.InputPort(k).Dimensions=widths(k);b.InputPort(k).DatatypeID=0;
        b.InputPort(k).Complexity='Real';b.InputPort(k).DirectFeedthrough=true;
    end
    b.OutputPort(1).Dimensions=28;b.OutputPort(1).DatatypeID=0;
    b.OutputPort(1).Complexity='Real';b.SampleTimes=[-1 0];b.NumContStates=0;
    b.RegBlockMethod('Outputs',@observe);
    function observe(block)
        y=nan(28,1);
        if enabled
            e=block.InputPort(2).Data;
            assert(all(isfinite(e))&&e(1)>=0&&e(1)==floor(e(1))&& ...
                e(2)>=1&&e(2)<=numel(cnvGroup)&&e(2)==floor(e(2)), ...
                'aperture:event','Event2 must be [nonnegative cycle;valid one-based group].');
            if cnvGroup(e(2))
                s=behavior_frontend_unpack(block.InputPort(1).Data,feSchema);
                assert(s.active_id==e(1)&&s.active_epoch>=0, ...
                    'aperture:tapStage','Connect current Sample.next353 after capture/join, before release.');
                y=behavior_aperture_diagnostic(s,s.active_id,s.active_epoch);
                assert(y(3)==1,'aperture:tapOwnership', ...
                    'CNV Sample state must contain exactly eight valid capture-tagged slices.');
            end
        end
        block.OutputPort(1).Data=y;
    end
end
