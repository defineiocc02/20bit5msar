function sar20_pp_command_sfun(b)
%SAR20_PP_COMMAND_SFUN Public predeclared low-rate commands, no state.
% Dialog sar20_pp_parameters(P), input Event2; output command5. Only existing
% event hits may carry commands; no added event, runtime file or random source.
    b.NumDialogPrms=1;b.DialogPrmsTunable={'Nontunable'};q=b.DialogPrm(1).Data;
    b.NumInputPorts=1;b.NumOutputPorts=1;b.SetPreCompPortInfoToDefaults;
    b.InputPort(1).Dimensions=2;b.InputPort(1).DatatypeID=0;b.InputPort(1).DirectFeedthrough=true;
    b.OutputPort(1).Dimensions=5;b.OutputPort(1).DatatypeID=0;
    b.SampleTimes=[-1 0];b.NumContStates=0;b.SimStateCompliance='HasNoSimState';b.RegBlockMethod('Outputs',@outputs);
    function outputs(block)
        cmd=zeros(5,1);
        if q.enabled
            e=block.InputPort(1).Data;hit=e(1)*q.n_groups+e(2)-1;
            rows=find(q.command_schedule(:,1)==hit);
            assert(numel(rows)<=1,'pp:duplicateScheduledCommand','At most one command per actual hit.');
            if ~isempty(rows),cmd=q.command_schedule(rows,2:6).';end
        end
        block.OutputPort(1).Data=cmd;
    end
end
