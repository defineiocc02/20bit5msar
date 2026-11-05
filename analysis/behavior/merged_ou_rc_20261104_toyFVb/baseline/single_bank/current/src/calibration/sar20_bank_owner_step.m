function [N,O]=sar20_bank_owner_step(S,E)
%SAR20_BANK_OWNER_STEP Pure A/B selection prediction; ISOLATED DIAGNOSTIC ONLY.
% E is exactly {hit,raw_ready,raw6,nominal_code,rx_fault,command}:
%   hit          monotonically increasing public event ordinal [integer]
%   raw_ready    public RX record-ready [0/1], NOT frame-ready
%   raw6         [D1;D2;DT;sample_id;epoch;valid], double[6x1], unitless
%   nominal_code nominal unsigned20 when valid=1; NaN allowed when not valid
%   rx_fault     public RX synchronization/fence failure [0/1]
%   command      low-rate none/load/qualify/publish/retire/arm command struct
%                (use struct('op','none') for none)
% Output predicts diagnostic_code20/diagnostic_valid and tag/version/meta.
% When no valid sample is consumed, diagnostic_code20 is the fixed NaN
% placeholder: ignored RAW/nominal values cannot change a repeated hit.
% code20 stays zero and code_valid is ALWAYS false: this unbound candidate
% cannot drive production; diagnostics are never a production-valid code.
% A future wrapper may call this for Outputs and discard N; only Update may
% commit N exactly once. There is no file, RNG, persistent or DWork mutation.
% Expected control rejections preserve all bank/command state while committing
% only event-deduplication metadata. Re-evaluating that same hit is idempotent;
% a different command payload at that same hit latches a conflict fault.
% Malformed fixed-port ABI is a fatal error. Same-run ARM is not implemented.
    assert(isstruct(S)&&isscalar(S)&&isfield(S,'schema')&& ...
        strcmp(S.schema,'sar20-bank-owner-state/v4')&& ...
        strcmp(S.scope,'ISOLATED_UNBOUND_DIAGNOSTIC_ONLY'), ...
        'bankOwner:state','Use the initialized isolated owner state.');
    if ~isempty(S.last_output)
        assert(isstruct(S.last_output)&&isscalar(S.last_output)&& ...
            isfield(S.last_output,'code20')&&isfield(S.last_output,'code_valid')&& ...
            isequal(S.last_output.code20,0)&&isequal(S.last_output.code_valid,false), ...
            'bankOwner:state','Cached output must remain isolated and production-invalid.');
    end
    fields={'hit';'raw_ready';'raw6';'nominal_code';'rx_fault';'command'};
    assert(isstruct(E)&&isscalar(E)&&isequal(sort(fieldnames(E)),sort(fields)), ...
        'bankOwner:event','Event must contain exactly the declared fixed ports.');
    assert(isnumeric(E.hit)&&isreal(E.hit)&&isscalar(E.hit)&&isfinite(E.hit)&& ...
        E.hit>=0&&E.hit==floor(E.hit)&&E.hit<=2^53-1,'bankOwner:hit','Bad public event ordinal.');
    assert(binary(E.raw_ready)&&binary(E.rx_fault),'bankOwner:flags','Ready/fault must be explicit binary scalars.');
    assert(isa(E.raw6,'double')&&isreal(E.raw6)&&isequal(size(E.raw6),[6 1]), ...
        'bankOwner:raw','Raw6 has a fixed double[6x1] ABI; values may be NaN when not valid.');
    assert(isnumeric(E.nominal_code)&&isreal(E.nominal_code)&&isscalar(E.nominal_code), ...
        'bankOwner:nominal','NominalCode must be one numeric scalar.');
    hasCmd=~is_none(E.command);N=S;O=blank_output();
    % Fault and raw-ready have priority. Ignore the entire control payload on a
    % sample; even an illegal command must return BUSY and cannot break RAW.
    if logical(E.rx_fault)||S.faulted
        signature=data_signature(E,false);
    elseif logical(E.raw_ready)
        signature=ready_signature(E,hasCmd);
    else
        assert(command_safe(E.command),'bankOwner:commandABI', ...
            'Non-ready command must contain only supported public plain values.');
        signature=command_signature(E);
    end
    if S.faulted
        O=blank_output();O.meta.fault=true;O.meta.fault_reason=S.fault_reason;
        O.command_status='FAULT';return;
    end
    if logical(E.rx_fault)
        [N,O]=latch_fault(S,'public_rx_fault');
        if E.hit>S.last_hit,N=remember(N,E.hit,signature,O);end
        return;
    end
    if E.hit==S.last_hit
        if signature.opaque||S.last_signature.opaque
            [N,O]=latch_fault(S,'unverifiable_same_hit_command');return;
        end
        if isequaln(signature,S.last_signature),O=S.last_output;return;end
        [N,O]=latch_fault(S,'conflicting_same_hit');return;
    end
    if E.hit<S.last_hit,[N,O]=latch_fault(S,'event_ordinal_reversed');return;end
    if logical(E.raw_ready)
        if hasCmd,O.command_status='CMD_BUSY';end
        [N,O]=process_raw(S,E,O);
        N=remember(N,E.hit,signature,O);return;
    end
    if ~hasCmd
        O.command_status='NONE';N=remember(N,E.hit,signature,O);return;
    end
    [shape,why]=command_shape(E.command);
    if ~shape,O.command_status=why;N=remember(S,E.hit,signature,O);return;end
    % A command with a new hit but the same accepted command_id is idempotent;
    % same ID / different payload or a decreasing ID is an ordinary rejection.
    check_context(S);c=E.command;id=double(c.command_id);hash=command_hash(c);
    if id==S.last_command_id
        if strcmp(hash,S.last_command_sha256),O.command_status='DUPLICATE';
        else,O.command_status='REJECT_COMMAND_ID_CONFLICT';end
        N=remember(S,E.hit,signature,O);
        return;
    elseif id<S.last_command_id
        O.command_status='REJECT_COMMAND_ID_STALE';N=remember(S,E.hit,signature,O);return;
    end
    [candidate,status]=process_command(S,c);
    O.command_status=status;
    if startsWith(status,'REJECT_'),N=remember(S,E.hit,signature,O);return;end
    N=candidate;N.last_command_id=id;N.last_command_sha256=hash;N.last_command_status=status;
    N=remember(N,E.hit,signature,O);
end

function [N,O]=process_raw(S,E,O)
    N=S;r=E.raw6;id=r(4);epoch=r(5);valid=r(6);tags=r(4:6);
    if any(~isfinite(tags))||any(tags~=floor(tags))||any(tags<0)|| ...
            id>double(S.cfg.plan_rows)-2||epoch>2^32-1||~any(valid==[0 1])||epoch~=S.epoch
        [N,O]=latch_fault(S,'malformed_raw_or_epoch');return;
    end
    if (~S.has_rx&&id~=S.first_id)||(S.has_rx&&id~=S.last_rx_id+1)
        [N,O]=latch_fault(S,'unexpected_first_id_gap_duplicate_or_wrap');return;
    end
    if valid==1
        b=r(1:3);limits=[2047;4095;255];
        if any(~isfinite(b))||any(b~=floor(b))||any(b<0)||any(b>limits)|| ...
                ~isfinite(E.nominal_code)||E.nominal_code~=floor(E.nominal_code)|| ...
                E.nominal_code<0||E.nominal_code>=2^20
            [N,O]=latch_fault(S,'malformed_valid_raw_or_nominal');return;
        end
    end % INVALID payload and nominal code are ignored, but tag still advances
    selected=S.active_slot;
    if S.transition.pending
        if id<S.transition.activation_id,selected=S.transition.old_slot;
        else
            selected=S.transition.new_slot;N.active_slot=selected;N.transition.switched=true;
            if valid==1&&N.transition.first_new_valid_id<0,N.transition.first_new_valid_id=id;end
        end
    end
    N.has_rx=true;N.last_rx_id=id;
    O.meta.sample_id=id;O.meta.epoch=epoch;O.meta.slot=selected;O.meta.valid=logical(valid);
    if selected==0
        O.meta.version=0;O.meta.proof_kind='explicit_nominal';
        if valid==1,O.diagnostic_code20=double(E.nominal_code);O.diagnostic_valid=true;end
        return;
    end
    if selected<1||selected>2||~strcmp(S.slots(selected).state,'qualified')
        [N,O]=latch_fault(S,'selected_version_unavailable');return;
    end
    slot=S.slots(selected);O.meta.version=slot.version;O.meta.proof_kind=slot.proof_kind;
    if valid==0,return;end
    C=struct('schema','sar20-public-frozen-cache/v2','public_cfg',S.cfg, ...
        'h',slot.h,'h_by_slice',reshape(slot.h,38,18).','plan',S.plan, ...
        'lifecycle','frozen_for_holdout','acceptance','NOT_ACCEPTED');
    try
        [code,diag]=behavior_frozen_step(r,1,double(E.nominal_code),true,C);
    catch cause
        if any(strcmp(cause.identifier,{'frozenCal:finiteDot','frozenCal:finiteVoltage'}))
            [N,O]=latch_fault(S,'numeric_decode_fault');return;
        end
        rethrow(cause); % unexpected ABI/programming failures remain visible
    end
    O.diagnostic_code20=code;O.diagnostic_valid=true;O.diag12=diag;O.meta.cal_used=true;
end

function [N,status]=process_command(S,c)
    N=S;status='REJECT_BAD_COMMAND';op=c.op;
    switch op
        case 'load'
            if ~valid_slot(c.slot,false)||~valid_version(c.version),return;end
            k=double(c.slot);version=double(c.version);
            if k==S.active_slot||slot_in_transition(S.transition,k)||~strcmp(S.slots(k).state,'empty')
                status='REJECT_SLOT_BUSY';return;
            end
            if version<=S.max_version,status='REJECT_VERSION';return;end
            [ok,status]=check_cache(S,c.cache);if ~ok,return;end
            [ok,status,certHash]=check_certificate(S,c.certificate,'training',version,c.cache.coefficient_sha256,'');
            if ~ok,return;end
            q=S.slots(k);q.state='candidate';q.version=version;q.h=c.cache.h;
            q.coefficient_sha256=c.cache.coefficient_sha256;q.training_certificate_sha256=certHash;
            q.protocol_sha256=c.certificate.protocol_sha256;q.proof_kind=c.certificate.kind;
            N.slots(k)=q;N.max_version=version;status=domain_status(S,'LOADED_CANDIDATE_NOT_QUALIFIED');
        case 'qualify'
            if ~valid_slot(c.slot,false)||~valid_version(c.version),return;end
            k=double(c.slot);q=S.slots(k);
            if ~strcmp(q.state,'candidate')||q.version~=c.version,status='REJECT_CANDIDATE';return;end
            [ok,status,certHash]=check_certificate(S,c.certificate,'qualification',q.version, ...
                q.coefficient_sha256,q.training_certificate_sha256);
            if ~ok,return;end
            if ~strcmp(c.certificate.protocol_sha256,q.protocol_sha256),status='REJECT_PROTOCOL';return;end
            q.state='qualified';q.qualification_certificate_sha256=certHash;N.slots(k)=q;
            status=domain_status(S,'QUALIFIED_NOT_ACTIVE');
        case 'publish'
            if ~valid_slot(c.slot,false)||~valid_version(c.version),return;end
            k=double(c.slot);
            if S.transition.pending||~S.has_rx||k==S.active_slot|| ...
                    ~strcmp(S.slots(k).state,'qualified')||S.slots(k).version~=c.version
                status='REJECT_PUBLISH_STATE';return;
            end
            a=c.activation_id;
            if ~integer_range(c.epoch,1,16)||c.epoch~=S.epoch|| ...
                    ~integer_range(a,0,double(S.cfg.plan_rows)-2)||a<=S.last_rx_id+S.guard_samples
                status='REJECT_PUBLISH_BOUNDARY';return;
            end
            N.transition=struct('pending',true,'old_slot',S.active_slot,'new_slot',k, ...
                'epoch',S.epoch,'activation_id',double(a),'switched',false,'first_new_valid_id',-1);
            status=domain_status(S,'PUBLISHED_FUTURE');
        case 'retire'
            if ~valid_slot(c.slot,true),return;end
            tr=S.transition;
            if ~tr.pending||~tr.switched||tr.old_slot~=c.slot||tr.first_new_valid_id<0
                status='REJECT_RETIRE_STATE';return;
            end
            [ok,status,bound]=check_drain_certificate(S,c.drain_certificate,tr);
            if ~ok,return;end
            if S.last_rx_id<tr.first_new_valid_id+bound,status='REJECT_DRAIN_NOT_REACHED';return;end
            old=double(c.slot);
            if old~=0
                q=S.slots(old);q.state='empty';q.version=0;q.h=zeros(684,1);
                q.coefficient_sha256='';q.training_certificate_sha256='';
                q.qualification_certificate_sha256='';q.protocol_sha256='';q.proof_kind='';N.slots(old)=q;
            end
            N.transition=empty_transition();status=domain_status(S,'RETIRED');
        case {'arm','rearm'}
            status='REJECT_REARM_UNSUPPORTED';
        otherwise
            status='REJECT_BAD_COMMAND';
    end
end

function [ok,status]=check_cache(S,C)
    ok=false;status='REJECT_CACHE';
    fields={'schema';'public_cfg';'h';'h_by_slice';'plan';'coefficient_sha256'; ...
        'public_cfg_sha256';'lifecycle';'acceptance'};
    if ~exact(C,fields)||~ischar(C.schema)||~strcmp(C.schema,'sar20-public-frozen-cache/v2')|| ...
            ~ischar(C.lifecycle)||~strcmp(C.lifecycle,'frozen_for_holdout')|| ...
            ~ischar(C.acceptance)||~strcmp(C.acceptance,'NOT_ACCEPTED')|| ...
            ~isa(C.h,'double')||~isreal(C.h)||~isequal(size(C.h),[684 1])|| ...
            any(~isfinite(C.h))||any(C.h<=0)||~isequaln(C.public_cfg,S.cfg)|| ...
            ~isa(C.plan,'uint8')||~isequal(C.plan,S.plan)|| ...
            ~isequal(C.h_by_slice,reshape(C.h,38,18).')|| ...
            ~ischar(C.public_cfg_sha256)||~strcmp(C.public_cfg_sha256,S.public_cfg_sha256)|| ...
            ~ischar(C.coefficient_sha256),return;end
    if ~strcmp(sar20_bank_sha256(typecast(C.h(:),'uint8')),C.coefficient_sha256),return;end
    ok=true;status='OK';
end

function [ok,status,digest]=check_certificate(S,c,phase,version,hsha,trainingDigest)
% Certificates are preverified/anchored by the external owner; hash equality
% alone is not authentication. Fixture evidence cannot authorize production.
    ok=false;status='REJECT_CERTIFICATE';digest='';
    common={'schema';'kind';'status';'version';'chip_id';'profile_id';'profile_sha256'; ...
        'coefficient_sha256';'public_cfg_sha256';'plan_sha256';'protocol_sha256';'acceptance';'activation'};
    if strcmp(phase,'training')
        fields=[common;{'training_receipt_sha256';'freeze_receipt_sha256';'coefficient_file_sha256'}];
        schema='sar20-bank-train-certificate/v1';wanted='trained';anchors=S.authority.approved_training_sha256;
    else
        fields=[common;{'training_certificate_sha256';'evaluation_receipt_sha256';'holdout_result_sha256'}];
        schema='sar20-bank-qualification-certificate/v1';wanted='passed';anchors=S.authority.approved_qualification_sha256;
    end
    if ~exact(c,fields),return;end
    strings=setdiff(fields,{'version'});
    for k=1:numel(strings),if ~text_scalar(c.(strings{k})),return;end,end
    if ~strcmp(c.schema,schema)||~strcmp(c.status,wanted)|| ...
            ~strcmp(c.acceptance,'NOT_ACCEPTED')||~strcmp(c.activation,'none')|| ...
            ~valid_version(c.version)||c.version~=version|| ...
            ~strcmp(c.chip_id,S.profile.chip_id)||~strcmp(c.profile_id,S.profile.profile_id)|| ...
            ~strcmp(c.profile_sha256,S.profile_sha256)||~strcmp(c.coefficient_sha256,hsha)|| ...
            ~strcmp(c.public_cfg_sha256,S.public_cfg_sha256)||~strcmp(c.plan_sha256,S.plan_sha256),return;end
    if strcmp(S.authority.mode,'fixture_only'),wantedKind='fixture_only';else,wantedKind='registered';end
    if ~strcmp(c.kind,wantedKind),status='REJECT_PROOF_DOMAIN';return;end
    hashes={'profile_sha256','coefficient_sha256','public_cfg_sha256','plan_sha256','protocol_sha256'};
    if strcmp(phase,'training')
        hashes=[hashes {'training_receipt_sha256','freeze_receipt_sha256','coefficient_file_sha256'}];
    else
        hashes=[hashes {'training_certificate_sha256','evaluation_receipt_sha256','holdout_result_sha256'}];
        if ~strcmp(c.training_certificate_sha256,trainingDigest),status='REJECT_TRAINING_BINDING';return;end
    end
    for k=1:numel(hashes),if ~hex64(c.(hashes{k})),return;end,end
    digest=sar20_bank_certificate_sha256(c);
    if ~any(strcmp(digest,anchors)),status='REJECT_UNTRUSTED_CERTIFICATE';return;end
    ok=true;status='OK';
end

function [ok,status,bound]=check_drain_certificate(S,c,tr)
% A declared delay alone is insufficient: require an externally preverified
% drain contract bound to this profile, old/new versions and activation tag.
    ok=false;status='REJECT_DRAIN_UNPROVEN';bound=NaN;
    fields={'schema';'kind';'status';'profile_sha256';'old_slot';'old_version'; ...
        'new_slot';'new_version';'epoch';'activation_id';'post_first_new_rx_slots';'evidence_sha256'};
    if ~exact(c,fields),return;end
    strings={'schema','kind','status','profile_sha256','evidence_sha256'};
    for k=1:numel(strings),if ~text_scalar(c.(strings{k})),return;end,end
    if strcmp(S.authority.mode,'fixture_only'),kind='fixture_only';else,kind='registered';end
    oldVersion=0;if tr.old_slot~=0,oldVersion=S.slots(tr.old_slot).version;end
    if ~strcmp(c.schema,'sar20-bank-drain-certificate/v1')||~strcmp(c.kind,kind)|| ...
            ~strcmp(c.status,'proved')||~strcmp(c.profile_sha256,S.profile_sha256)|| ...
            ~hex64(c.evidence_sha256)||~integer_range(c.old_slot,0,2)||c.old_slot~=tr.old_slot|| ...
            ~integer_range(c.old_version,0,2^32-1)||c.old_version~=oldVersion|| ...
            ~integer_range(c.new_slot,1,2)||c.new_slot~=tr.new_slot|| ...
            ~valid_version(c.new_version)||c.new_version~=S.slots(tr.new_slot).version|| ...
            ~integer_range(c.epoch,1,16)||c.epoch~=tr.epoch|| ...
            ~integer_range(c.activation_id,0,double(S.cfg.plan_rows)-2)||c.activation_id~=tr.activation_id|| ...
            ~integer_range(c.post_first_new_rx_slots,1,1e6),return;end
    digest=sar20_bank_certificate_sha256(c);
    if ~any(strcmp(digest,S.authority.approved_drain_sha256)),return;end
    bound=double(c.post_first_new_rx_slots);ok=true;status='OK';
end

function [ok,status]=command_shape(c)
    ok=false;status='REJECT_BAD_COMMAND';
    if is_none(c),ok=true;return;end
    if ~isstruct(c)||~isscalar(c)||~isfield(c,'op')||~text_scalar(c.op)|| ...
            ~isfield(c,'command_id')||~integer_range(c.command_id,1,2^32-1),return;end
    switch c.op
        case 'load',fields={'op';'command_id';'slot';'version';'cache';'certificate'};
        case 'qualify',fields={'op';'command_id';'slot';'version';'certificate'};
        case 'publish',fields={'op';'command_id';'slot';'version';'epoch';'activation_id'};
        case 'retire',fields={'op';'command_id';'slot';'drain_certificate'};
        case {'arm','rearm'},fields={'op';'command_id'};
        otherwise,return;
    end
    ok=exact(c,fields)&&command_safe(c);
end
function [N,O]=latch_fault(S,reason)
    N=S;N.faulted=true;N.fault_reason=reason;N.transition=empty_transition();
    O=blank_output();O.meta.fault=true;O.meta.fault_reason=reason;O.command_status='FAULT';
end
function T=empty_transition()
    T=struct('pending',false,'old_slot',0,'new_slot',0,'epoch',0, ...
        'activation_id',-1,'switched',false,'first_new_valid_id',-1);
end
function O=blank_output()
    meta=struct('sample_id',-1,'epoch',-1,'slot',0,'version',0,'cal_used',false, ...
        'valid',false,'fault',false,'fault_reason','','proof_kind','', ...
        'scope','ISOLATED_UNBOUND_DIAGNOSTIC_ONLY');
    O=struct('code20',0,'code_valid',false,'diagnostic_code20',NaN,'diagnostic_valid',false, ...
        'diag12',[nan(9,1);0;0;NaN],'command_status','NONE','meta',meta);
end
function N=remember(N,hit,signature,O)
    N.last_hit=double(hit);N.last_signature=signature;N.last_output=O;N.event_count=N.event_count+1;
end
function sig=data_signature(E,hasCmd)
    % Command payload is ignored on a ready/fault hit. Non-ready payload and
    % invalid-frame data/nominal are also ignored; only public tags matter.
    r=E.raw6;n=double(E.nominal_code);
    if logical(E.rx_fault)||~logical(E.raw_ready),r=zeros(6,1);n=0;
    elseif isfinite(r(6))&&r(6)==0,r(1:3)=0;n=0;end
    bytes=typecast([double(E.raw_ready);r(:);n;double(E.rx_fault);double(hasCmd)],'uint8');
    sig=struct('kind','data','bytes',bytes(:),'opaque',false);
end
function sig=ready_signature(E,hasCmd)
% The sample is processed even for an illegal same-hit command. A plain-value
% command is fingerprinted so changing it on the same hit is a conflict. An
% unsupported object is ignored/BUSY once; replay cannot establish identity
% and therefore faults rather than silently equating opaque payloads.
    sig=data_signature(E,hasCmd);
    if ~hasCmd,return;end
    if command_safe(E.command)
        digest=command_hash(E.command);sig.kind='data_command';sig.bytes=[sig.bytes;uint8(digest(:))];
    else
        sig.kind='data_opaque';sig.opaque=true;
    end
end
function sig=command_signature(E)
    if is_none(E.command),sig=data_signature(E,false);return;end
    bytes=typecast([double(E.raw_ready);double(E.rx_fault)],'uint8');
    digest=command_hash(E.command);sig=struct('kind','command','bytes',[bytes(:);uint8(digest(:))],'opaque',false);
end
function digest=command_hash(c)
    % Unlike JSON, this encoding includes numeric class and array shape, so a
    % row/column or type change with the same command_id cannot look identical.
    digest=sar20_bank_sha256(command_bytes(c));
end
function bytes=command_bytes(x)
    if isstruct(x)&&isscalar(x)
        names=sort(fieldnames(x));bytes=[uint8('S');pack_length(numel(names))];
        for k=1:numel(names)
            key=uint8(unicode2native(names{k},'UTF-8'));
            item=command_bytes(x.(names{k}));
            bytes=[bytes;pack_length(numel(key));key(:);pack_length(numel(item));item(:)]; %#ok<AGROW>
        end
        return;
    end
    dims=typecast(uint64(size(x)),'uint8');
    if ischar(x)
        tag=uint8('C');payload=uint8(unicode2native(x,'UTF-8'));className=uint8('char');
    elseif islogical(x)
        tag=uint8('L');payload=uint8(x(:));className=uint8('logical');
    else
        tag=uint8('N');payload=typecast(x(:),'uint8');className=uint8(class(x));
    end
    bytes=[tag;pack_length(numel(className));className(:);pack_length(numel(dims));dims(:); ...
        pack_length(numel(payload));payload(:)];
end
function bytes=pack_length(n)
    bytes=typecast(uint64(n),'uint8');bytes=bytes(:);
end
function yes=is_none(c)
    yes=exact(c,{'op'})&&text_scalar(c.op)&&strcmp(c.op,'none');
end
function status=domain_status(S,base)
    if strcmp(S.authority.mode,'fixture_only'),status=['FIXTURE_ONLY_' base];else,status=base;end
end
function yes=slot_in_transition(t,k),yes=t.pending&&(t.old_slot==k||t.new_slot==k);end
function check_context(S)
    probe=behavior_frozen_setup(S.cfg,ones(684,1));
    assert(isequal(probe.plan,S.plan)&&strcmp(probe.public_cfg_sha256,S.public_cfg_sha256)&& ...
        strcmp(sar20_bank_sha256(S.plan(:)),S.plan_sha256)&& ...
        strcmp(sar20_bank_sha256(unicode2native(jsonencode(orderfields(S.profile)),'UTF-8')),S.profile_sha256)&& ...
        strcmp(sar20_bank_sha256(unicode2native(jsonencode(orderfields(S.authority)),'UTF-8')),S.authority_sha256), ...
        'bankOwner:stateIntegrity','Immutable public config/plan/profile/authority state changed.');
end
function yes=binary(x),yes=(isnumeric(x)||islogical(x))&&isreal(x)&&isscalar(x)&&isfinite(double(x))&&any(double(x)==[0 1]);end
function yes=valid_slot(x,allowNominal)
    if allowNominal,yes=integer_range(x,0,2);else,yes=integer_range(x,1,2);end
end
function yes=valid_version(x),yes=integer_range(x,1,2^32-1);end
function yes=integer_range(x,a,b),yes=isnumeric(x)&&isreal(x)&&isscalar(x)&&isfinite(x)&&x==floor(x)&&x>=a&&x<=b;end
function yes=exact(x,fields),yes=isstruct(x)&&isscalar(x)&&isequal(sort(fieldnames(x)),sort(fields(:)));end
function yes=command_safe(x)
% Restrict low-rate command payloads to ordinary public MATLAB values before
% hashing. Malformed objects are rejected as commands, not allowed to throw
% from the serializer or introduce hidden state/input types.
    if ischar(x),yes=isrow(x)||isempty(x);return;end
    if isnumeric(x)||islogical(x),yes=isreal(x)&&~issparse(x)&&ndims(x)<=2;return;end
    if isstruct(x)&&isscalar(x)
        yes=true;names=fieldnames(x);
        for k=1:numel(names)
            if ~command_safe(x.(names{k})),yes=false;return;end
        end
        return;
    end
    yes=false;
end
function yes=text_scalar(x),yes=ischar(x)&&isrow(x)&&~isempty(x);end
function yes=hex64(x),yes=text_scalar(x)&&~isempty(regexp(x,'^[0-9a-f]{64}$','once'))&&~all(x=='0');end
