function R = sar20_plot_regress(runPath, id, workDir)
%SAR20_PLOT_REGRESS Capture the deterministic outputs of behavior_sample_plot.
%
% The function renders PNG/FIG figures (not reproducible byte-for-byte across
% runs) and writes several CSV tables (fully deterministic). This digest keeps
% the CSV content plus the returned struct's non-path fields, which is what a
% pure code reshape could plausibly break.
    assert(isfolder(runPath),'plotReg:path','Missing run %s.',runPath);
    if ~isfolder(workDir), mkdir(workDir); end
    res = behavior_sample_plot(runPath, id);

    R = struct();
    R.status='ok';
    csvNames = {'record_csv','aperture_csv','csv','event_csv'};
    for k=1:numel(csvNames)
        f = csvNames{k};
        if isfield(res,f) && isfile(res.(f))
            t = fileread(res.(f));
            R.([f '_sha'])  = sha_char(t);
            R.([f '_len'])  = numel(t);
            copyfile(res.(f), fullfile(workDir, [f '.csv']));
        else
            R.([f '_sha']) = 'absent';
            R.([f '_len']) = -1;
        end
    end
    % Returned scalar/char fields, excluding paths that embed runPath.
    skip = {'png','fig','tracking_png','tracking_fig','timing_png','timing_fig', ...
            'record_csv','aperture_csv','csv','event_csv'};
    fn = fieldnames(res);
    for k=1:numel(fn)
        n = fn{k};
        if any(strcmp(n,skip)), continue; end
        v = res.(n);
        if (isnumeric(v)&&isscalar(v)),      R.(n)=digest_scalar(v);
        elseif islogical(v)&&isscalar(v),    R.(n)=num2str(double(v));
        elseif ischar(v),                    R.(n)=v;
        end
    end
end

function v = digest_scalar(x)
    if isnan(x), v='NaN'; else, v=num2str(double(x),'%.17g'); end
end

function h = sha_char(t)
    md=java.security.MessageDigest.getInstance('SHA-256');
    md.update(unicode2native(t,'UTF-8'));
    h=lower(reshape(dec2hex(typecast(md.digest(),'uint8'),2).',1,[]));
end
