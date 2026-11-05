function behavior_backend_sfun(block)
%BEHAVIOR_BACKEND_SFUN Pure Level-2 backend adapter, v1 2026-10-27.
% Dialog parameters: kind ('advance' or 'commit'), P.backend (named parameters).
% Inputs: advance=[state48,time1,command26,OLD FE353]; commit keeps3 inputs.
% Outputs next48/obs8. Advance port4 is fixed across enable changes.
% Off/all-zero tau never reads port4; finite enabled uses it read-only.
% Numerical definitions and reset behavior: behavior_backend_stage/step.
% Caller: current SarAdc SLX. No DWork/UserData/persistent/RNG or Update method;
% standard UnitDelay outside these stages is the sole retained state owner.
    setup(block);
end

function setup(block)
    block.NumDialogPrms=2;
    block.DialogPrmsTunable={'Nontunable','Nontunable'};
    kind=block.DialogPrm(1).Data;
    p=block.DialogPrm(2).Data;
    assert((ischar(kind)||isstring(kind))&&any(strcmp(char(kind),{'advance','commit'})), ...
        'behavior:sfunKind','Backend stage must be advance or commit.');
    % Validate every ON configuration at native setup, including dt=0/sigma=0.
    % OFF follows the legacy setup unchanged.
    if isstruct(p)&&isscalar(p)&&isfield(p,'ni')&&isstruct(p.ni)&& ...
            isfield(p.ni,'ra_noise')&&isscalar(p.ni.ra_noise)&& ...
            isreal(p.ni.ra_noise)&&isequal(double(p.ni.ra_noise),1)
        behavior_ra_noise_validate_backend(p);
    end
    isAdvance=strcmp(char(kind),'advance');
    block.NumInputPorts=3+double(isAdvance);block.NumOutputPorts=2;
    block.SetPreCompInpPortInfoToDynamic;
    block.SetPreCompOutPortInfoToDynamic;
    inputWidths=[48 1 26];if isAdvance,inputWidths(4)=353;end
    outputWidths=[48 8];
    for k=1:numel(inputWidths)
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
    block.NumContStates=0;block.SimStateCompliance='DefaultSimState';
    block.RegBlockMethod('Outputs',@(b)outputs(b,kind,p));
end

function outputs(block,kind,p)
    finiteCoupling=strcmp(char(kind),'advance')&&isfield(p,'dac_coupling')&& ...
        p.dac_coupling.enabled&&any(p.dac_coupling.tau_dac_s>0);
    if finiteCoupling
        [next,obs]=behavior_backend_stage(kind, ...
            block.InputPort(1).Data,block.InputPort(2).Data, ...
            block.InputPort(3).Data,p,block.InputPort(4).Data);
    else
        % Keep the original call and do not evaluate InputPort(4).Data.
        [next,obs]=behavior_backend_stage(kind, ...
            block.InputPort(1).Data,block.InputPort(2).Data, ...
            block.InputPort(3).Data,p);
    end
    block.OutputPort(1).Data=next;
    block.OutputPort(2).Data=obs;
end
