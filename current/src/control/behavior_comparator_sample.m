function [c,diag]=behavior_comparator_sample(event,c,p)
%BEHAVIOR_COMPARATOR_SAMPLE Stateless comparator input-referred perturbation.
% The event is an actual scheduled fine_decide, d2_decide, or ta_compare.
% c is the existing physical comparison struct; only its selected decision bit
% can change. SAR1 uses vres_v; SAR2 and TA share the physical vy_v comparator.
% No input waveform, ADC state, scheduler time, valid/late flag or RNG mutates.
% With zero offset and zero RMS, retain the actual native decision bit,
% including its zero-tie behavior. With a perturbation yielding EXACTLY zero,
% tie_decision is an explicit engineering assumption, not a claim about the SLX.
    diag=struct('applied',false,'channel',0,'event_code',0,'input_v',NaN, ...
        'offset_v',0,'noise_v',0,'effective_v',NaN,'decision',NaN);
    switch event.type
        case 'fine_decide'
            ch=1;ev=1;voltage='vres_v';decision='decision1';
            offset=p.sar1_offset_v;sigma=p.sar1_noise_rms_v;limit=5;
        case 'd2_decide'
            ch=2;ev=2;voltage='vy_v';decision='decision2';
            offset=p.sar2_offset_v;sigma=p.sar2_noise_rms_v;limit=12;
        case 'ta_compare'
            ch=2;ev=3;voltage='vy_v';decision='decision2';
            offset=p.sar2_offset_v;sigma=p.sar2_noise_rms_v;limit=8;
        otherwise
            error('sar20Cmp:event','Expected an actual comparator event.');
    end
    assert(isfield(event,'sample_id')&&isfield(event,'epoch')&& ...
        isfield(event,'index')&&isscalar(event.index)&&isfinite(event.index)&& ...
        event.index==floor(event.index)&&event.index>=0&&event.index<limit, ...
        'sar20Cmp:eventKey','Event requires valid sample/epoch/index keys.');
    assert(isfield(c,voltage)&&isfield(c,decision)&& ...
        isnumeric(c.(voltage))&&isreal(c.(voltage))&&isscalar(c.(voltage))&& ...
        isfinite(c.(voltage))&&isscalar(c.(decision))&& ...
        ismember(c.(decision),[0 1]),'sar20Cmp:input','Require physical input and native decision.');
    v=double(c.(voltage));native=double(c.(decision));
    diag.channel=ch;diag.event_code=ev;diag.input_v=v;diag.offset_v=offset;
    diag.effective_v=v;diag.decision=native;
    if ~p.enabled || (offset==0 && sigma==0)
        return; % no added arithmetic and no RNG/hash: exact native decision
    end
    noise=0;
    if sigma>0
        z=behavior_comparator_keyed_normal(p.seed_u64,event.epoch,event.sample_id,ev,event.index);
        noise=sigma*z;
    end
    effective=(v+offset)+noise;
    assert(isfinite(effective),'sar20Cmp:nonfinite','Comparator effective input must be finite.');
    if effective>0
        bit=1;
    elseif effective<0
        bit=0;
    else
        bit=double(p.tie_decision);
    end
    c.(decision)=bit;
    diag.applied=true;diag.noise_v=noise;diag.effective_v=effective;diag.decision=bit;
end
