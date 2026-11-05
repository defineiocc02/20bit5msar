function behavior_control_stage_sfun(block)
%BEHAVIOR_CONTROL_STAGE_SFUN v1 (2026-10-27): stateless SLX adapter.
% Dialog: kind ('due'|'prepare'|'decide'), P; four direct-feedthrough double
% inputs[51,2,7,3], three double outputs[51,13,19]. Inherited sample time.
% Only the parent numeric Unit Delay retains SAR state; this block has no DWork.
    block.NumDialogPrms=2;block.DialogPrmsTunable={'Nontunable','Nontunable'};
    kind=block.DialogPrm(1).Data;P=block.DialogPrm(2).Data;
    % Inspect actual dialog P before simulation; never rebuild/rebind stale P.
    if isstruct(P)&&isfield(P,'control')&&isstruct(P.control)
        behavior_comparator_configuration(P,'check');
    end
    assert(any(strcmp(kind,{'due','prepare','decide'})), ...
        'behavior:stageSfun:kind','Unknown controller stage kind.');
    block.NumInputPorts=4;block.NumOutputPorts=3;
    block.SetPreCompPortInfoToDefaults;
    iw=[51 2 7 3];ow=[51 13 19];
    for k=1:4
        block.InputPort(k).Dimensions=iw(k);block.InputPort(k).DatatypeID=0;
        block.InputPort(k).Complexity='Real';block.InputPort(k).DirectFeedthrough=true;
    end
    for k=1:3
        block.OutputPort(k).Dimensions=ow(k);block.OutputPort(k).DatatypeID=0;
        block.OutputPort(k).Complexity='Real';
    end
    block.SampleTimes=[-1 0];block.NumContStates=0;
    block.SimStateCompliance='DefaultSimState';
    block.RegBlockMethod('Outputs',@outputs);
    function outputs(b)
        [x,y,z]=behavior_control_stage(kind,double(b.InputPort(1).Data), ...
            double(b.InputPort(2).Data),double(b.InputPort(3).Data), ...
            double(b.InputPort(4).Data),P);
        b.OutputPort(1).Data=x;b.OutputPort(2).Data=y;b.OutputPort(3).Data=z;
    end
end
