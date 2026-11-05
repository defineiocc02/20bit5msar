function behavior_frontend_sfun(block)
%BEHAVIOR_FRONTEND_SFUN Pure Level-2 frontend adapter, v1 2026-10-27.
% Dialog parameters: kind ('advance'/'commit'), normalized P.front.
% Inputs: state353, context6=[time,id,epoch,event,D1,vtop], external Driver4.
% Outputs: next state353, obs7 (order documented by behavior_frontend_stage).
% This block owns no retained state: no DWork, UserData, persistent or Update.
% One standard external UnitDelay owns the final state after both stages.
    setup(block);
end

function setup(block)
    block.NumDialogPrms=2;
    block.DialogPrmsTunable={'Nontunable','Nontunable'};
    kind=block.DialogPrm(1).Data;
    assert((ischar(kind)||isstring(kind))&&any(strcmp(char(kind),{'advance','commit'})), ...
        'behaviorFE:sfunKind','Frontend stage must be advance or commit.');
    p=block.DialogPrm(2).Data;
    assert(isstruct(p)&&isfield(p,'group_C_f')&&isfield(p,'schema'), ...
        'behaviorFE:sfunParameters','Pass normalized P.front returned by init.');
    block.NumInputPorts=3;block.NumOutputPorts=2;
    block.SetPreCompInpPortInfoToDynamic;
    block.SetPreCompOutPortInfoToDynamic;
    inputWidths=[353 6 4];outputWidths=[353 7];
    for k=1:3
        block.InputPort(k).Dimensions=inputWidths(k);
        block.InputPort(k).DatatypeID=0;
        block.InputPort(k).Complexity='Real';
        block.InputPort(k).DirectFeedthrough=true;
    end
    for k=1:2
        block.OutputPort(k).Dimensions=outputWidths(k);
        block.OutputPort(k).DatatypeID=0;
        block.OutputPort(k).Complexity='Real';
    end
    block.SampleTimes=[-1 0];
    block.NumContStates=0;
    block.SimStateCompliance='DefaultSimState';
    block.RegBlockMethod('Outputs',@(b)outputs(b,kind,p));
end

function outputs(block,kind,p)
    [next,obs]=behavior_frontend_stage(kind, ...
        block.InputPort(1).Data,block.InputPort(2).Data,p, ...
        block.InputPort(3).Data);
    block.OutputPort(1).Data=next;
    block.OutputPort(2).Data=obs;
end
