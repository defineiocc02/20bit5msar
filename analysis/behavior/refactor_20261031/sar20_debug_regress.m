function R = sar20_debug_regress(runDir, id)
%SAR20_DEBUG_REGRESS Capture behavior_sample_debug output as a comparable digest.
%
% The function under test turns a saved simout into a structured diagnostic.
% Rather than comparing the whole nested struct (which contains timestamps and
% NaNs), this digest keeps the parts a refactor could plausibly break: the
% record selection, the branch values, the bank verdict and every reason string.
%
%   runDir  directory containing simout.mat and parameters.mat
%   id      sample id to inspect
%
% Returns a struct of scalars/strings only, safe to JSON-encode and diff.
    assert(isfolder(runDir),'dbg:path','Missing run directory %s.',runDir);
    S=load(fullfile(runDir,'simout.mat'));
    P=load(fullfile(runDir,'parameters.mat'));
    if isfield(S,'simout'), out=S.simout; else, fn=fieldnames(S); out=S.(fn{1}); end
    if isfield(P,'P'), P=P.P; end
    D=behavior_sample_debug(out,P,id);

    R=struct();
    R.status='ok';
    R.adc_latch_time_s = digest_scalar(D.adc_ready_time_s);
    R.adc_raw          = digest_vec(D.adc_raw);
    R.groups           = digest_any(D.groups);
    R.groups_type      = class(D.groups);
    if isstruct(D.groups)
        R.groups_fields = strjoin(fieldnames(D.groups).',',');
        R.groups_size   = sprintf('%dx%d',size(D.groups,1),size(D.groups,2));
    end
    R.transport        = double(D.transport_enabled);
    R.raw              = digest_vec(D.raw);
    R.ready            = digest_vec(D.ready);
    R.back             = digest_vec(D.back);

    r=D.record;
    R.record_available   = double(r.available);
    R.record_valid       = double(r.valid);
    R.record_code20      = digest_scalar(r.code20);
    R.record_raw         = digest_vec(r.raw);
    R.record_raw_eq_adc  = double(r.raw_equals_adc);
    R.record_reason      = char(r.reason);
    R.d1_v               = digest_scalar(r.d1_v);
    R.d2_v               = digest_scalar(r.d2_v);
    R.dt_v               = digest_scalar(r.dt_v);
    R.branch_reasons     = strjoin(cellfun(@char,r.branch_reasons,'UniformOutput',false),'|');

    f=D.frozen;
    R.frozen_enabled = double(f.enabled);
    R.frozen_used    = double(f.used);
    R.frozen_reason  = char(f.reason);

    b=D.bank;
    R.bank_enabled       = double(b.enabled);
    R.bank_available     = double(b.available);
    R.bank_valid         = digest_scalar(b.code_valid);
    R.bank_fault         = digest_scalar(b.fault);
    R.bank_slot          = digest_scalar(b.slot);
    R.bank_version       = digest_scalar(b.version);
    R.bank_tags_match    = double(b.tags_match);
    R.bank_version_match = double(b.version_match);
    R.bank_reason        = char(b.reason);
end

function v = digest_scalar(x)
% NaN-safe scalar: NaN becomes the literal string 'NaN' so JSON keeps it.
    if isnumeric(x) && isscalar(x)
        if isnan(x), v='NaN';
        else, v=num2str(double(x),'%.17g'); end
    else
        v='NaN';
    end
end

function v = digest_any(x)
% Structural digest that works for numeric, logical, char and struct input.
    if isnumeric(x) || islogical(x)
        v = digest_vec(x);
    elseif ischar(x)
        v = x;
    elseif isstruct(x)
        v = sprintf('struct[%dx%d]{%s}', size(x,1), size(x,2), strjoin(fieldnames(x).',','));
    elseif iscell(x)
        v = sprintf('cell[%dx%d]', size(x,1), size(x,2));
    else
        v = class(x);
    end
end

function v = digest_vec(x)
% Row vector of numbers with NaN folded to a fixed token.
    x=double(x(:)).';
    parts=cell(1,numel(x));
    for k=1:numel(x)
        if isnan(x(k)), parts{k}='N';
        else, parts{k}=num2str(x(k),'%.17g'); end
    end
    v=strjoin(parts,',');
end
