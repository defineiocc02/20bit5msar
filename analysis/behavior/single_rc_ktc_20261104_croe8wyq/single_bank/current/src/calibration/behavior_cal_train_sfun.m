function behavior_cal_train_sfun(b)
%BEHAVIOR_CAL_TRAIN_SFUN Training-only collector with Update-owned digital state.
% CalCfg is EXACT collector opt; RAW6/Ready1/Ref4 are NOT direct feedthrough.
% NominalCode1 is direct, passed without arithmetic/type change to output1.
% Outputs reads ONLY NominalCode and committed status7/snapshot DWork.
% DWork4=[status7,Rawbuf6N,Refbuf4N,snapshot2624]; off large entries1dummy.
% N_train is explicit: supports predeclared2048 and short8 rank rejection.
% Immutable opt/s0/captureFile; no mutable closure/persistent/global/RNG.
% Dialog2 captureFile char path (default wiring TrainCaptureFile=''): only
% Terminate reads existing post-Update DWorks and writes one observation file;
% blank path has no I/O. No collection/fit/state submission in Terminate.
    b.NumDialogPrms=2;b.DialogPrmsTunable={'Nontunable','Nontunable'};
    opt=b.DialogPrm(1).Data;
    captureFile=b.DialogPrm(2).Data;
    assert(ischar(captureFile)&&(isempty(captureFile)||isrow(captureFile)), ...
        'calCollect:captureFile','Dialog2 must be a read-only char path or empty char.');
    [s0,o0]=behavior_cal_collector_step('init',[],0,[],[],opt);
    enabled=logical(opt.enabled);n=opt.N_train;
    snapshotWidth=1;if enabled,snapshotWidth=2624;end
    b.NumInputPorts=4;b.NumOutputPorts=3;b.SetPreCompPortInfoToDefaults;
    widths=[6 1 4 1];
    for k=1:4
        b.InputPort(k).Dimensions=widths(k);b.InputPort(k).DatatypeID=0;
        b.InputPort(k).Complexity='Real';b.InputPort(k).SamplingMode='Sample';
        b.InputPort(k).DirectFeedthrough=(k==4);
    end
    outputWidths=[1 7 snapshotWidth];
    for k=1:3
        b.OutputPort(k).Dimensions=outputWidths(k);b.OutputPort(k).DatatypeID=0;
        b.OutputPort(k).Complexity='Real';b.OutputPort(k).SamplingMode='Sample';
    end
    b.SampleTimes=[-1 0];b.NumContStates=0;
    b.RegBlockMethod('PostPropagationSetup',@dworks);
    b.RegBlockMethod('InitializeConditions',@initialize);
    b.RegBlockMethod('Outputs',@outputs);
    b.RegBlockMethod('Update',@update);
    b.RegBlockMethod('Terminate',@terminate);
    function dworks(block)
        count=[7 1 1 snapshotWidth];if enabled,count(2:3)=[6*n 4*n];end
        labels={'Status','RawBuffer','ReferenceBuffer','FitSnapshot'};
        block.NumDworks=4;
        for dw=1:4
            block.Dwork(dw).Name=labels{dw};block.Dwork(dw).Dimensions=count(dw);
            block.Dwork(dw).DatatypeID=0;block.Dwork(dw).Complexity='Real';
            block.Dwork(dw).UsedAsDiscState=true;
        end
    end
    function initialize(block)
        block.Dwork(1).Data=o0.status7;
        if enabled
            block.Dwork(2).Data=s0.raw_buffer(:);block.Dwork(3).Data=s0.reference_buffer(:);
        else
            block.Dwork(2).Data=0;block.Dwork(3).Data=0;
        end
        block.Dwork(4).Data=behavior_cal_collector_snapshot(o0.status7,[]);
    end
    function outputs(block)
        block.OutputPort(1).Data=block.InputPort(4).Data;
        block.OutputPort(2).Data=block.Dwork(1).Data;
        block.OutputPort(3).Data=block.Dwork(4).Data;
    end
    function update(block)
        if ~enabled,return;end
        status=block.Dwork(1).Data;
        if status(3)~=0,return;end
        ready=block.InputPort(2).Data;
        assert(isscalar(ready)&&ismember(ready,[0 1]),'calCollect:ready','RawReady must be binary.');
        if ready==0,return;end
        % These are the ONLY large DWork reads. No read/unpack on47 other hits.
        state=s0;state.n_collected=status(2);state.fit_calls=status(3);
        state.fit_status_code=status(4);state.fit_rank=status(5);
        state.ready_for_independent_holdout=logical(status(6));state.accepted=logical(status(7));
        state.raw_buffer=reshape(block.Dwork(2).Data,[n 6]);
        state.reference_buffer=reshape(block.Dwork(3).Data,[n 4]);
        [next,result]=behavior_cal_collector_step('update',state,ready, ...
            block.InputPort(1).Data,block.InputPort(3).Data,opt);
        block.Dwork(1).Data=result.status7;
        if result.record_collected_this_update
            block.Dwork(2).Data=next.raw_buffer(:);block.Dwork(3).Data=next.reference_buffer(:);
        end
        if result.fit_invoked_this_update
            block.Dwork(4).Data=behavior_cal_collector_snapshot(result.status7,result.fit_report_this_update);
        end
    end
    function terminate(block)
        if ~isempty(captureFile)
            assert(~isfile(captureFile)&&~isfolder(captureFile), ...
                'calCollect:captureExists','Refuse to overwrite an existing capture path.');
            % Observation only: preserve partial actual state BEFORE the existing
            % incomplete assertion; never append, fit or write any DWork here.
            raw=block.Dwork(2).Data;reference=block.Dwork(3).Data;
            if enabled,raw=reshape(raw,n,6);reference=reshape(reference,n,4);end
            committed=struct('extracted',true,'status7',block.Dwork(1).Data(:), ...
                'snapshot2624',block.Dwork(4).Data(:),'raw_buffer',raw, ...
                'reference_buffer',reference,'time_s',block.CurrentTime, ...
                'block_path',getfullname(block.BlockHandle), ...
                'source','actual Terminate post-Update DWorks');
            save(captureFile,'committed','-v7.3');
        end
        if ~enabled,return;end
        status=block.Dwork(1).Data;
        assert(status(2)==n&&status(3)==1,'calCollect:training_incomplete', ...
            'training_incomplete: collected %g/%g rows, fit_calls=%g.',status(2),n,status(3));
    end
end
