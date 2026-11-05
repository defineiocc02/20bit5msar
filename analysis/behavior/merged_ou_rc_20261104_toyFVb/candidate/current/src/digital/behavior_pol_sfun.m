function behavior_pol_sfun(b)
%BEHAVIOR_POL_SFUN Pure public ID/epoch to POL adapter; dialog DecodeP.az_mode.
% Inputs ID[1],epoch[1]; output POL[1], all double. No DWork/Update/RNG.
% Only timing inherited from the parent's event-triggered frame; no new hits.
    b.NumDialogPrms=1;b.DialogPrmsTunable={'Nontunable'};
    b.NumInputPorts=2;b.NumOutputPorts=1;b.SetPreCompPortInfoToDefaults;
    for k=1:2
        b.InputPort(k).Dimensions=1;b.InputPort(k).DatatypeID=0;
        b.InputPort(k).Complexity='Real';b.InputPort(k).DirectFeedthrough=true;
    end
    b.OutputPort(1).Dimensions=1;b.OutputPort(1).DatatypeID=0;b.OutputPort(1).Complexity='Real';
    b.SampleTimes=[-1 0];b.NumContStates=0;b.SimStateCompliance='DefaultSimState';
    b.RegBlockMethod('Outputs',@outputs);
end
function outputs(b)
    p=b.DialogPrm(1).Data;
    assert(isfield(p,'az_mode'),'behaviorPol:configuration','Save explicit DecodeP.az_mode.');
    b.OutputPort(1).Data=behavior_public_pol(b.InputPort(1).Data,b.InputPort(2).Data,p.az_mode);
end
