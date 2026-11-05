function R = sar20_explain_regress(runPath, id)
%SAR20_EXPLAIN_REGRESS Capture behavior_sample_explain output for comparison.
%
% The function writes a Chinese markdown explanation and returns a struct. Both
% are captured: the markdown text is the real deliverable, and the struct holds
% the numeric verdict. A refactor that only reshapes code must leave both byte
% identical.
    assert(isfolder(runPath),'exp:path','Missing run dir %s.',runPath);
    res = behavior_sample_explain(runPath, id);
    txt = fileread(res.markdown);
    % Drop the run path so the digest does not depend on where it ran.
    txt = strrep(txt, runPath, '<RUN>');

    R = struct();
    R.status = 'ok';
    R.markdown = txt;
    R.markdown_len = numel(txt);
    R.markdown_sha = sha_char(txt);

    numeric = {'sample_id','raw_id','epoch','raw_valid','tags_match', ...
               'actual_code20','formula_code20','contribution_identity_matches', ...
               'AZ_log_present','route_log_present'};
    for k = 1:numel(numeric)
        R.(numeric{k}) = digest_scalar(res.(numeric{k}));
    end
    R.adc_raw_ready_time_s = digest_scalar(res.adc_raw_ready_time_s);
    R.actual_record_ready_time_s = digest_scalar(res.actual_record_ready_time_s);
end

function v = digest_scalar(x)
    if isnumeric(x) && isscalar(x)
        if isnan(x), v='NaN'; else, v=num2str(double(x),'%.17g'); end
    elseif islogical(x) && isscalar(x)
        v = num2str(double(x));
    else
        v = 'NaN';
    end
end

function h = sha_char(t)
    md = java.security.MessageDigest.getInstance('SHA-256');
    md.update(unicode2native(t,'UTF-8'));
    h = lower(reshape(dec2hex(typecast(md.digest(),'uint8'),2).',1,[]));
end
