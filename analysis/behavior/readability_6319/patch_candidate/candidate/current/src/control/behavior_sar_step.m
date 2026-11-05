function [s,out] = behavior_sar_step(s,event,comparison,p)
%BEHAVIOR_SAR_STEP Update explicit coarse6/fine5, D2 and tracking controller state.
%Version: v1 (2026-10-27). Caller: behavior scheduler at named calendar events.
%Inputs s/event/p; comparison.sample_v [V] is required at CNV, vres_v [V] for
%fine decisions, vy_v [V] for D2/TA. Relational Operator decision1/2 bits override
%standalone >=0 comparison; valid/late are optional comparator flags.
%Output next s and out trial/feedback-change flags, signs, RAW words and record.
%D1[10:5]=coarse[5:0], D1[4:0]=fine; D2 has12 bits, DT8 bits/7 physical updates.
%CNV/reset initialize only digital SAR state; release clears active/ra_on, not
%frontend/RA/AZ charge. RA enable is s.ra_on/out.ra_on. No hidden state/RNG/truth decode.
%Model: coarse thresholds q=8+16*j; DAC weights [512 256 128 64 32 16 16 8 4 2 1].
%RAW changes at decisions; physical feedback prefixes change only when due.
%The controller does not advance analog states or accept frame_ready events.
    assert(isstruct(event)&&isscalar(event)&&isfield(event,'type'), ...
        'behavior:sar:event','Supply one named event struct.');
    assert(isstruct(comparison)&&isscalar(comparison),'behavior:sar:comparison','Supply a named physical comparison struct.');
    if isempty(s)
        assert(any(strcmp(event.type,{'cnv','reset'})),'behavior:sar:init','First event must be cnv or reset.');
        s=initial_state();
    end
    out=struct('feedback_changed',false,'trial_changed',false,'record_ready',false, ...
        'decision',-1,'valid',false,'record',struct());
    switch event.type
        case 'reset'
            s=initial_state();
        case 'cnv'
            assert(isfield(event,'sample_id')&&isfield(event,'epoch'), ...
                'behavior:sar:tags','CNV requires sample_id and epoch.');
            assert(isempty(s.pending.type),'behavior:sar:pendingAtCNV','Uncommitted feedback at CNV.');
            s=initial_state();s.active=true;s.sample_id=event.sample_id;s.epoch=event.epoch;
            % Sample-ID parity tag only; not a calibration coefficient bank.
            s.bank=mod(s.sample_id,2);s.sample_v=physical(comparison,'sample_v');
        case 'coarse_latch'
            require_active(s);
            delta=p.sar1.delta_v;fsr=1024*delta;
            offset=0;if isfield(p.sar1,'coarse_offset_v'),offset=p.sar1.coarse_offset_v;end
            if isfield(p.sar1,'coarse_noise_rms_v')
                assert(p.sar1.coarse_noise_rms_v==0,'behavior:sar:coarseNoise', ...
                    'Coarse noise must be an explicit physical sample input, not controller RNG.');
            end
            q=(s.sample_v+offset+fsr/2)/delta;
            s.coarse=sum(q>=(8+16*(0:62)));
            s.d1raw=s.coarse*32;s.d1_feedback_word=s.d1raw;s.trial=s.d1raw;
            s.coarse_latched=true;s.overrange=s.sample_v < -fsr/2 || s.sample_v >= fsr/2;
            out.feedback_changed=true;out.trial_changed=true;
        case 'fine_prepare'
            require_active(s);
            assert(s.coarse_latched&&~s.fine_pending&&event.index==s.fine_attempt_count&&event.bit==4-s.fine_attempt_count, ...
                'behavior:sar:fineOrder','Fine prepare must follow coarse and previous decision.');
            assert(isempty(s.pending.type),'behavior:sar:fineFeedback','Prior fine feedback must be committed first.');
            s.fine_bit=event.bit;s.fine_pending=true;
            s.trial=setword(s.d1raw,event.bit,1);out.trial_changed=true;
        case 'fine_decide'
            require_active(s);
            assert(s.fine_pending&&event.bit==s.fine_bit,'behavior:sar:finePending','Fine decision without matching prepare.');
            [decision,valid,late]=compare_physical(comparison,'vres_v','decision1');out.decision=decision;
            if valid
                s.d1raw=setword(s.d1raw,event.bit,decision);s.fine_count=s.fine_count+1;
            else,s.overrange=true;end
            s.overrange=s.overrange||late;s.fine_pending=false;s.fine_attempt_count=s.fine_attempt_count+1;
            s.pending=make_pending('fine_feedback',event,s.d1raw,decision,s.fine_count);
        case 'fine_feedback'
            s=commit_feedback(s,event);s.d1_feedback_word=s.pending.word;s.trial=s.pending.word;
            s.pending=empty_pending();out.feedback_changed=true;out.trial_changed=true;
        case 'ra_start'
            assert(s.coarse_latched&&s.fine_attempt_count==5&&~s.fine_pending&&isempty(s.pending.type), ...
                'behavior:sar:fineDone','RA requires all five fine decisions and feedback.');
            s.overrange=s.overrange||s.fine_count~=5;s.ra_on=true;
        case 'd2_prepare'
            require_active(s);
            assert(~s.d2_pending&&s.d2_count==event.index&&event.bit==11-s.d2_count, ...
                'behavior:sar:d2Order','D2 must prepare bit 11 down to 0 exactly once.');
            assert(isempty(s.pending.type),'behavior:sar:d2Feedback','Prior D2 feedback must commit before prepare.');
            s.d2_pending=true;s.d2_bit=event.bit;s.d2_trial=s.d2_feedback_word;
            % Current candidate remains neutral; do not set its trial bit to 1.
        case 'd2_decide'
            require_active(s);
            assert(s.d2_pending&&s.d2_bit==event.bit,'behavior:sar:d2Pending','D2 decision without matching prepare.');
            [decision,valid,late]=compare_physical(comparison,'vy_v','decision2');out.decision=decision;
            if isfield(p,'sar2')&&isfield(p.sar2,'limit_v')&&isfield(comparison,'vy_v')&&abs(comparison.vy_v)>p.sar2.limit_v,s.overrange=true;end
            if ~valid,decision=0;s.overrange=true;end
            s.d2raw=setword(s.d2raw,event.bit,decision);s.d2_count=s.d2_count+1;
            s.d2_pending=false;s.overrange=s.overrange||late;
            s.pending=make_pending('d2_feedback',event,s.d2raw,decision,s.d2_count);
        case 'd2_feedback'
            s=commit_feedback(s,event);s.d2_feedback_word=s.pending.word;
            s.d2_signs(s.pending.index+1)=2*s.pending.decision-1;
            s.pending=empty_pending();out.feedback_changed=true;
        case 'd2_end'
            assert(s.d2_count==12&&~s.d2_pending&&isempty(s.pending.type), ...
                'behavior:sar:d2Done','D2 must finish twelve decisions and feedback.');
        case 'ta_compare'
            require_active(s);
            assert(s.d2_count==12&&s.track_count==event.index&&isempty(s.pending.type), ...
                'behavior:sar:trackOrder','TA must compare m=0..7 after twelve D2 decisions.');
            [decision,valid,late]=compare_physical(comparison,'vy_v','decision2');out.decision=decision;
            if isfield(p,'sar2')&&isfield(p.sar2,'limit_v')&&isfield(comparison,'vy_v')&&abs(comparison.vy_v)>p.sar2.limit_v,s.overrange=true;end
            if valid,s.dtraw=setword(s.dtraw,event.bit,decision);else,s.overrange=true;end
            s.overrange=s.overrange||late;s.track_count=s.track_count+1;
            if event.index<7
                s.pending=make_pending('ta_feedback',event,s.dtraw,decision,s.track_count);
            end
        case 'ta_feedback'
            s=commit_feedback(s,event);
            assert(s.pending.index<7,'behavior:sar:eighthFeedback','There is no eighth physical TA update.');
            % Invalid TA leaves its RAW bit zero, matching active CICC semantics.
            bit=bitget(uint32(s.pending.word),8-s.pending.index);
            s.tracking_signs(s.pending.index+1)=2*double(bit)-1;
            s.feedback_count=s.feedback_count+1;s.pending=empty_pending();out.feedback_changed=true;
        case 'tracking_end'
            assert(s.track_count==8&&s.feedback_count==7&&isempty(s.pending.type), ...
                'behavior:sar:trackDone','Require eight comparisons and seven physical feedback commits.');
        case 'raw_latch'
            assert(s.fine_attempt_count==5&&s.d2_count==12&&s.track_count==8&&s.feedback_count==7, ...
                'behavior:sar:rawCounts','RAW requires fine5/D2-12/TA8/feedback7.');
            s.raw_latched=true;out.record_ready=true;out.valid=~s.overrange;
            out.record=struct('raw_D1',s.d1raw,'raw_D2',s.d2raw,'raw_DT',s.dtraw, ...
                'valid',double(~s.overrange),'sample_id',s.sample_id,'epoch',s.epoch, ...
                'commit_time_s',event_time(event));
        case 'release'
            assert(s.raw_latched,'behavior:sar:release','Release before RAW latch.');
            s.active=false;s.ra_on=false;
        otherwise
            error('behavior:sar:eventType','Unknown controller event: %s.',event.type);
    end
    out.ra_on=s.ra_on;out.active=s.active;out.raw_latched=s.raw_latched;
    out.trial=s.trial;out.d1raw=s.d1raw;out.d2raw=s.d2raw;out.dtraw=s.dtraw;
    out.d2_signs=s.d2_signs;out.tracking_signs=s.tracking_signs;
end

function s=initial_state()
    s=struct('active',false,'sample_id',-1,'epoch',-1,'bank',0,'sample_v',0, ...
        'coarse',0,'coarse_latched',false,'trial',0,'d1raw',0,'d1_feedback_word',0, ...
        'fine_count',0,'fine_attempt_count',0,'fine_pending',false,'fine_bit',-1,'d2raw',0, ...
        'd2_feedback_word',0,'d2_trial',0,'d2_count',0,'d2_pending',false,'d2_bit',-1, ...
        'dtraw',0,'track_count',0,'feedback_count',0,'d2_signs',zeros(12,1), ...
        'tracking_signs',zeros(7,1),'pending',empty_pending(), ...
        'ra_on',false,'overrange',false,'raw_latched',false);
end
function pending=empty_pending()
    pending=struct('type','','index',-1,'word',0,'decision',0,'count',0,'due_s',0);
end
function q=make_pending(type,event,word,decision,count)
    q=struct('type',type,'index',event.index,'word',word,'decision',decision, ...
        'count',count,'due_s',event_time(event)+1.25e-9);
end
function s=commit_feedback(s,event)
    assert(strcmp(s.pending.type,event.type)&&s.pending.index==event.index, ...
        'behavior:sar:pendingType','Feedback has no matching pending decision.');
    assert(abs(event_time(event)-s.pending.due_s)<=16*eps(max(abs(s.pending.due_s),1e-9)), ...
        'behavior:sar:feedbackTime','Feedback must occur decision +1.25 ns.');
end
function require_active(s)
    assert(s.active,'behavior:sar:inactive','Conversion event while inactive.');
end
function v=physical(c,name)
    assert(isfield(c,name)&&isnumeric(c.(name))&&isreal(c.(name))&&isscalar(c.(name))&&isfinite(c.(name)), ...
        'behavior:sar:physicalInput','Missing finite physical comparison.%s.',name);
    v=double(c.(name));
end
function [d,valid,late]=compare_physical(c,name,decisionName)
    if isfield(c,decisionName)
        d=double(binary_flag(c.(decisionName),decisionName));
    else
        d=double(physical(c,name)>=0);
    end
    valid=true;late=false;
    if isfield(c,'valid'),valid=binary_flag(c.valid,'valid');end
    if isfield(c,'late'),late=binary_flag(c.late,'late');end
end
function b=binary_flag(v,name)
    assert((islogical(v)||isnumeric(v))&&isreal(v)&&isscalar(v)&&isfinite(v)&&any(v==[0 1]), ...
        'behavior:sar:flag','comparison.%s must be scalar 0/1.',name);b=logical(v);
end
function w=setword(w,bit,decision)
    w=double(bitset(uint32(w),bit+1,decision));
end
function t=event_time(e)
    if isfield(e,'absolute_time_s'),t=e.absolute_time_s;else,t=e.time_s;end
end
