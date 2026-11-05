function behavior_frozen_sfun(block)
%BEHAVIOR_FROZEN_SFUN Pure three-input holdout decoder, no DWork/UserData/state.
% Dialog (enabled=0 default at wiring, frozenCache=[] if off).
% Inputs RAW6, Ready1, NominalCode1. Outputs code1, diagnostic12.
    block.NumDialogPrms=2;
    block.DialogPrmsTunable={'Nontunable','Nontunable'};
    enabled=block.DialogPrm(1).Data;
    C=block.DialogPrm(2).Data; % immutable setup capture; never reassigned
    block.NumInputPorts=3;block.NumOutputPorts=2;
    block.SetPreCompInpPortInfoToDynamic;block.SetPreCompOutPortInfoToDynamic;
    dims=[6 1 1];
    for k=1:3
        block.InputPort(k).Dimensions=dims(k);block.InputPort(k).DatatypeID=0;
        block.InputPort(k).Complexity='Real';block.InputPort(k).DirectFeedthrough=true;
    end
    block.OutputPort(1).Dimensions=1;block.OutputPort(2).Dimensions=12;
    for k=1:2,block.OutputPort(k).DatatypeID=0;block.OutputPort(k).Complexity='Real';end
    block.SampleTimes=[-1 0];block.NumContStates=0;block.SimStateCompliance='HasNoSimState';
    block.RegBlockMethod('Outputs',@outputs);
    function outputs(runtimeBlock)
        % Read-only immutable capture. No closure mutation or per-hit DialogPrm read.
        [code,diag]=behavior_frozen_step(runtimeBlock.InputPort(1).Data, ...
            runtimeBlock.InputPort(2).Data,runtimeBlock.InputPort(3).Data,enabled,C);
        runtimeBlock.OutputPort(1).Data=code;runtimeBlock.OutputPort(2).Data=diag;
    end
end
