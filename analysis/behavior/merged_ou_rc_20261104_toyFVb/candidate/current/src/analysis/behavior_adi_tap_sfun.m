function behavior_adi_tap_sfun(b)
%BEHAVIOR_ADI_TAP_SFUN Optional read-only actual-wire observation, 58 doubles.
% Parameter P: only debug.adi_enabled/N/groups captured, no physical state.
% Inputs Sample.next353,DacTrial.next353,Sar2Tracking.next51,RaCommand26,Event2.
% out=[actualIDs8;DEMshift8;DACsignalTarget8;CNVcaptureTailB8;D2sign12;
%      TAsign7;D2decideCount;TAcompareCount;TAfeedbackCount;actualD1;hasDAC;activeID;activeEpoch]. IDs physical ascending.
% Actual IDs require phase2 AND valid capture tags matching actual active tags.
% Disabled: allNaN; before first actual DAC: shift/target NaN; nonCNV: tail NaN.
% No state/RNG/Update. Sample/DacTrial precede release; controller follows decide.
    b.NumDialogPrms=1;b.DialogPrmsTunable={'Nontunable'};p=b.DialogPrm(1).Data;
    assert(isfield(p,'debug')&&isfield(p.debug,'adi_enabled')&& ...
        isscalar(p.debug.adi_enabled)&&ismember(p.debug.adi_enabled,[0 1]),'adi:debug','Explicit P.debug.adi_enabled required.');
    enabled=logical(p.debug.adi_enabled);assert(~enabled||p.N==8,'adi:debugN8','Enabled tap is restricted to N8 diagnostic runs.');
    cnvGroup=false(numel(p.groups),1);
    for g=1:numel(p.groups),cnvGroup(g)=any(strcmp({p.groups(g).events.type},'cnv'));end
    b.NumInputPorts=5;b.NumOutputPorts=1;b.SetPreCompPortInfoToDefaults;w=[353 353 51 26 2];
    for k=1:5
        b.InputPort(k).Dimensions=w(k);b.InputPort(k).DatatypeID=0;
        b.InputPort(k).Complexity='Real';b.InputPort(k).DirectFeedthrough=true;
    end
    b.OutputPort(1).Dimensions=58;b.OutputPort(1).DatatypeID=0;
    b.OutputPort(1).Complexity='Real';b.SampleTimes=[-1 0];b.NumContStates=0;
    b.RegBlockMethod('Outputs',@observe);
    function observe(block)
        y=nan(58,1);
        if enabled
            captured=block.InputPort(1).Data;dac=block.InputPort(2).Data;
            control=block.InputPort(3).Data;command=block.InputPort(4).Data;e=block.InputPort(5).Data;
            ids=find(captured(7:24)==2&captured(241:258)~=0& ...
                captured(205:222)==captured(277)&captured(223:240)==captured(278));
            assert(numel(ids)==8,'adi:tapOwnership','Actual Sample state must have eight valid active conversion slices.');
            y(1:8)=ids;
            if dac(280)~=0,y(9:16)=dac(281+ids);y(17:24)=dac(78+ids);end
            if cnvGroup(e(2)),y(25:32)=captured(42+ids);end
            y(33:51)=command(3:21);y(52:54)=control([18 22 23]);
            y(55:58)=dac([279 280 277 278]);
        end
        block.OutputPort(1).Data=y;
    end
end
