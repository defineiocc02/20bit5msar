function behavior_wiring_sfun(b)
%BEHAVIOR_WIRING_SFUN v1.0 — named bus adapters, no ADC calculation or state.
% Parameters kind,P. Only routing units/tags/commands, pure Outputs, all direct.
% clock: Event[2] -> time_s. context: Event,Control13,Backend8 -> FrontCmd6.
% backend: FrontObs7,Control13,Signs19,Event2 -> BackendCmd26.
% AZ routing changes full Qres polarity and restores release Vtop coordinates;
% digital RAW words and D2/TA feedback signs are not post-hoc flipped.
% raw: Control13 -> Raw6,ready. Backend command25/26 carry sample_id/epoch.
    b.NumDialogPrms=2;b.DialogPrmsTunable={'Nontunable','Nontunable'};
    kind=char(b.DialogPrm(1).Data);P=b.DialogPrm(2).Data;
    switch kind
        case 'clock',ins=2;outs=1;
        case {'cnv','due','trial','release'},ins=[2 13 8];outs=6;
        case 'backend',ins=[7 13 19 2];outs=26;
        case 'raw',ins=13;outs=[6 1];
        otherwise,error('behavior:wiringKind','Unknown wiring kind.');
    end
    b.NumInputPorts=numel(ins);b.NumOutputPorts=numel(outs);
    b.SetPreCompPortInfoToDefaults;
    for k=1:numel(ins)
        b.InputPort(k).Dimensions=ins(k);b.InputPort(k).DatatypeID=0;
        b.InputPort(k).Complexity='Real';b.InputPort(k).DirectFeedthrough=true;
    end
    for k=1:numel(outs)
        b.OutputPort(k).Dimensions=outs(k);b.OutputPort(k).DatatypeID=0;
        b.OutputPort(k).Complexity='Real';
    end
    b.SampleTimes=[-1 0];b.NumContStates=0;
    b.RegBlockMethod('Outputs',@output);
    function output(block)
        switch kind
            case 'backend'
                f=block.InputPort(1).Data;c=block.InputPort(2).Data;sg=block.InputPort(3).Data;
                e=block.InputPort(4).Data;g=P.groups(e(2));
                phase=struct('offset_s',g.time_s,'ra_on',c(2),'release',c(12));
                az=behavior_az_schedule(e(1),P.epoch,phase,P);
                qres=f(3);if az.polarity==-1,qres=-qres;end
                command=[qres;f(5);sg;c(2);double(az.az_on);double(az.reset_signal);e(1);P.epoch];
                if c(12)~=0,command(1)=0;command(3:21)=0;end
                block.OutputPort(1).Data=command;
            case 'raw'
                c=block.InputPort(1).Data;
                block.OutputPort(1).Data=[c(5:7);c(9:10);c(8)];
                block.OutputPort(2).Data=c(4);
            otherwise
                e=block.InputPort(1).Data;g=P.groups(e(2));
                t=e(1)*P.Ts_s+g.time_s;
                if strcmp(kind,'clock'),block.OutputPort(1).Data=t;return;end
                c=block.InputPort(2).Data;bk=block.InputPort(3).Data;
                event=0;
                if strcmp(kind,'cnv')&&any(strcmp({g.events.type},'cnv')),event=1;end
                if strcmp(kind,'due')&&any(strcmp({g.events.type},'fine_feedback')),event=1;end
                if strcmp(kind,'trial')&&c(13)~=0,event=1;end
                if strcmp(kind,'release')&&c(12)~=0,event=2;end
                vtop=bk(3);
                if strcmp(kind,'release')
                    phase=struct('offset_s',g.time_s,'ra_on',c(2),'release',c(12));
                    az=behavior_az_schedule(e(1),P.epoch,phase,P);
                    if az.polarity==-1,vtop=-vtop;end
                end
                block.OutputPort(1).Data=[t;e(1);P.epoch;event;c(1);vtop];
        end
    end
end
