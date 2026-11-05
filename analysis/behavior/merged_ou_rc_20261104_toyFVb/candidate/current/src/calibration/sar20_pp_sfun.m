function sar20_pp_sfun(b)
%SAR20_PP_SFUN Actual-P-bound A/B pure prediction; external delay commits.
% Dialog: sar20_pp_parameters(P). Only its pinned real qualified context can
% enable behavior-test code. Fixture scope is rejected at the block boundary.
% Inputs: state64, Event2, Clock1, Record6, RecordReady1, FpgaCode1,
% RXFault1, EN1, command5, independent consumer ack7. Outputs: next64,
% code1, valid1, metadata9. No DWork/Update/file I/O in Outputs.
    b.NumDialogPrms=1;b.DialogPrmsTunable={'Nontunable'};q=b.DialogPrm(1).Data;
    assert(isstruct(q)&&isscalar(q)&&isfield(q,'enabled')&& ...
        (~q.enabled||(isfield(q,'scope')&&strcmp(q.scope,'SOURCE_CONTROLLED_BEHAVIOR_TEST_ONLY'))), ...
        'pp:blockScope','Actual-P qualified real RX context only; fixture cannot drive product output.');
    b.NumInputPorts=10;b.NumOutputPorts=4;
    b.SetPreCompInpPortInfoToDynamic;b.SetPreCompOutPortInfoToDynamic;
    iw=[64 2 1 6 1 1 1 1 5 7];ow=[64 1 1 9];
    for k=1:10
        b.InputPort(k).Dimensions=iw(k);b.InputPort(k).DatatypeID=0;
        b.InputPort(k).Complexity='Real';b.InputPort(k).DirectFeedthrough=true;
    end
    for k=1:4
        b.OutputPort(k).Dimensions=ow(k);b.OutputPort(k).DatatypeID=0;b.OutputPort(k).Complexity='Real';
    end
    b.SampleTimes=[-1 0];b.NumContStates=0;b.SimStateCompliance='HasNoSimState';
    b.RegBlockMethod('Outputs',@outputs);
    function outputs(block)
        time=block.InputPort(3).Data;assert(time==block.CurrentTime,'pp:actualTime','Clock must be actual engine time.');
        [xn,o]=sar20_pp_step(block.InputPort(1).Data,block.InputPort(2).Data,time, ...
            block.InputPort(4).Data,block.InputPort(5).Data,block.InputPort(6).Data, ...
            block.InputPort(7).Data,block.InputPort(8).Data,block.InputPort(9).Data,block.InputPort(10).Data,q);
        block.OutputPort(1).Data=xn;block.OutputPort(2).Data=o.code20;
        block.OutputPort(3).Data=double(o.code_valid);block.OutputPort(4).Data=o.meta9;
    end
end
