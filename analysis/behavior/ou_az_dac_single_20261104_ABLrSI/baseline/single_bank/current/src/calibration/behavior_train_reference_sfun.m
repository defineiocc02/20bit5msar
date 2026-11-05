function behavior_train_reference_sfun(b)
%BEHAVIOR_TRAIN_REFERENCE_SFUN v1 2026-10-27, ideal external source reference.
% RefCfg is separately declared BEFORE the ADC run, not inferred from its
% samples/codes. Input Event2 supplies CNV group and public sample ID only.
% Output Ref4=[Vdiff;ID;epoch;valid] locks at actual CNV and holds to RawReady.
% One external instrument DWork owner; ADC analog state is never read/changed.
% Outputs may preview this CNV's value but only Update commits it. No RNG/I/O.
    b.NumDialogPrms=1;b.DialogPrmsTunable={'Nontunable'};p=b.DialogPrm(1).Data;
    keys={'enabled';'source';'provenance';'sample_period_s';'epoch';'first_id';'records'; ...
        'offset_v';'amplitude_v';'frequency_hz';'phase_rad'};
    assert(isstruct(p)&&isscalar(p)&&isequal(sort(fieldnames(p)),sort(keys)), ...
        'trainRef:boundary','Use the independent reference declaration only.');
    assert(isscalar(p.enabled)&&ismember(p.enabled,[0 1])&& ...
        strcmp(p.source,'declared_external_reference')&&ischar(p.provenance)&&~isempty(p.provenance), ...
        'trainRef:source','Reference source/provenance must be explicit.');
    a=[p.sample_period_s p.epoch p.first_id p.records p.offset_v p.amplitude_v p.frequency_hz p.phase_rad];
    assert(isreal(a)&&numel(a)==8&&all(isfinite(a))&&p.sample_period_s>0&& ...
        p.amplitude_v>=0&&p.frequency_hz>=0&&p.frequency_hz<.5/p.sample_period_s&& ...
        all(a(2:4)==floor(a(2:4)))&&all(a(2:4)>=0),'trainRef:parameters','Invalid SI reference parameters.');
    b.NumInputPorts=1;b.NumOutputPorts=1;b.SetPreCompPortInfoToDefaults;
    b.InputPort(1).Dimensions=2;b.InputPort(1).DatatypeID=0;
    b.InputPort(1).Complexity='Real';b.InputPort(1).DirectFeedthrough=true;
    b.OutputPort(1).Dimensions=4;b.OutputPort(1).DatatypeID=0;b.OutputPort(1).Complexity='Real';
    b.SampleTimes=[-1 0];b.NumContStates=0;
    b.RegBlockMethod('PostPropagationSetup',@work);
    b.RegBlockMethod('InitializeConditions',@init);
    b.RegBlockMethod('Outputs',@outputs);b.RegBlockMethod('Update',@update);
    function work(block)
        block.NumDworks=1;block.Dwork(1).Name='ExternalReference';block.Dwork(1).Dimensions=4;
        block.Dwork(1).DatatypeID=0;block.Dwork(1).Complexity='Real';block.Dwork(1).UsedAsDiscState=true;
    end
    function init(block),block.Dwork(1).Data=[0;-1;-1;0];end
    function outputs(block)
        e=block.InputPort(1).Data;y=block.Dwork(1).Data;
        if p.enabled&&e(2)==1,y=capture(e,block.CurrentTime,p);end
        block.OutputPort(1).Data=y;
    end
    function update(block)
        e=block.InputPort(1).Data;
        if p.enabled&&e(2)==1,block.Dwork(1).Data=capture(e,block.CurrentTime,p);end
    end
end
function y=capture(e,time,p)
    id=e(1);assert(isfinite(id)&&id>=0&&id==floor(id)&&time==id*p.sample_period_s, ...
        'trainRef:aperture','Reference must latch at its declared nominal CNV, not RawReady.');
    value=p.offset_v+p.amplitude_v*sin(2*pi*p.frequency_hz*time+p.phase_rad);
    valid=id>=p.first_id&&id<p.first_id+p.records;
    y=[value;id;p.epoch;double(valid)];
end
