function behavior_dither_sfun(block)
%BEHAVIOR_DITHER_SFUN One-input/one-output stateless public dither adapter.
% Dialog DecodeP; input public sample ID; output input-referred addback [V].
% Inherits event sample hits; Outputs is pure, no DWork/Update/PRNG state.
    block.NumDialogPrms=1;block.DialogPrmsTunable={'Nontunable'};
    block.NumInputPorts=1;block.NumOutputPorts=1;
    block.SetPreCompInpPortInfoToDynamic;block.SetPreCompOutPortInfoToDynamic;
    block.InputPort(1).Dimensions=1;block.InputPort(1).DatatypeID=0;
    block.InputPort(1).Complexity='Real';block.InputPort(1).DirectFeedthrough=true;
    block.OutputPort(1).Dimensions=1;block.OutputPort(1).DatatypeID=0;
    block.OutputPort(1).Complexity='Real';
    block.SampleTimes=[-1 0];block.NumContStates=0;
    block.SimStateCompliance='DefaultSimState';
    block.RegBlockMethod('Outputs',@outputs);
end
function outputs(block)
    block.OutputPort(1).Data=behavior_public_dither(block.InputPort(1).Data,block.DialogPrm(1).Data);
end
