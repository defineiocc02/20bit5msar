function behavior_reference_queue_sfun(b)
%BEHAVIOR_REFERENCE_QUEUE_SFUN Only Outputs predicts; external UnitDelay commits.
% Parameter normalized queue config. Inputs state22,TrainRef4,Event2,RXRaw6,
% raw_ready1=Transport.ready3(2), NOT frame_ready; all DirectFeedthrough.
% Outputs next22,pairedRef4,diag4. Startup -2/-1 is retained with valid0.
% No DWork, Update, UserData, persistent state, instrument model or RNG.
    b.NumDialogPrms=1;b.DialogPrmsTunable={'Nontunable'};
    p=behavior_reference_queue_parameters(b.DialogPrm(1).Data);
    b.NumInputPorts=5;b.NumOutputPorts=3;b.SetPreCompPortInfoToDefaults;
    widths=[22 4 2 6 1];outputs=[22 4 4];
    for k=1:5
        b.InputPort(k).Dimensions=widths(k);b.InputPort(k).DatatypeID=0;
        b.InputPort(k).Complexity='Real';b.InputPort(k).DirectFeedthrough=true;
    end
    for k=1:3
        b.OutputPort(k).Dimensions=outputs(k);b.OutputPort(k).DatatypeID=0;
        b.OutputPort(k).Complexity='Real';
    end
    b.SampleTimes=[-1 0];b.NumContStates=0;b.RegBlockMethod('Outputs',@predict);
    function predict(block)
        [x,r,d]=behavior_reference_queue_stage(block.InputPort(1).Data, ...
            block.InputPort(2).Data,block.InputPort(3).Data,block.InputPort(4).Data, ...
            block.InputPort(5).Data,p);
        block.OutputPort(1).Data=x;block.OutputPort(2).Data=r;block.OutputPort(3).Data=d;
    end
end
