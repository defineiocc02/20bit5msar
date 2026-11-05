function behavior_transport_pp_sfun(block)
%BEHAVIOR_TRANSPORT_PP_SFUN Pure Outputs; external UnitDelay owns finite97 state.
% Dialog cfg only, immutable capture. Inputs x97/context2/chipRaw6/RawReady/EN.
% Outputs xnext97/RXRaw6/ready3/frame12/trace69x8/nRows1/RX resync fault1. Unused trace rows NaN.
% Put this digital owner inside standard Enabled core. OFF holds97 and uses
% RAW bypass; don't add49 close event when off. No DWork/Update/UserData/RNG.
    block.NumDialogPrms=1;block.DialogPrmsTunable={'Nontunable'};
    cfg=block.DialogPrm(1).Data;
    assert(isequaln(cfg,behavior_transport_config()),'transport97:cfg','Fixed public cfg required.');
    block.NumInputPorts=5;block.NumOutputPorts=7;
    block.SetPreCompInpPortInfoToDynamic;block.SetPreCompOutPortInfoToDynamic;
    iw=[97 2 6 1 1];ow=[97 6 3 12];
    for k=1:5
        block.InputPort(k).Dimensions=iw(k);block.InputPort(k).DatatypeID=0;
        block.InputPort(k).Complexity='Real';block.InputPort(k).DirectFeedthrough=true;
    end
    for k=1:4,block.OutputPort(k).Dimensions=ow(k);end
    block.OutputPort(5).Dimensions=[69 8];block.OutputPort(6).Dimensions=1;block.OutputPort(7).Dimensions=1;
    for k=1:7,block.OutputPort(k).DatatypeID=0;block.OutputPort(k).Complexity='Real';end
    block.SampleTimes=[-1 0];block.NumContStates=0;block.SimStateCompliance='HasNoSimState';
    block.RegBlockMethod('Outputs',@outputs);
    function outputs(b)
        ctx=b.InputPort(2).Data;
        assert(ctx(1)==b.CurrentTime,'transport97:actualClock','Context time must be actual Simulink Clock, not inferred from sample ID.');
        [xn,o]=behavior_transport_step_pp(b.InputPort(1).Data,ctx,b.InputPort(3).Data, ...
            b.InputPort(4).Data,b.InputPort(5).Data,cfg);
        b.OutputPort(1).Data=xn;b.OutputPort(2).Data=o.raw6;b.OutputPort(3).Data=o.ready3;
        b.OutputPort(4).Data=o.frame12;b.OutputPort(5).Data=o.trace;b.OutputPort(6).Data=o.nRows;
        b.OutputPort(7).Data=o.rx_fault;
    end
end
