function report=normal_gate(jobRoot,testName,candidateManifestSha)
% UNFROZEN SCRATCH. One function gate per new headless process.
% The outer controller must verify the frozen package, file paths and hashes.
    jobRoot=normal_jobroot(jobRoot);
    allowed={'test_single_rc_ktc','test_joint_ou_az_dac','test_joint_ou_rc_return', ...
        'test_comparator_single','test_normal_10v'};
    assert(ischar(testName)&&any(strcmp(testName,allowed)), ...
        'normalGate:name','A reviewed function gate is required.');
    assert(ischar(candidateManifestSha)&&~isempty(regexp(candidateManifestSha,'^[0-9a-f]{64}$','once')), ...
        'normalGate:sha','Frozen candidate manifest SHA required.');
    assert(feature('getpid')~=27628&&~usejava('desktop')&&~bdIsLoaded('SarAdc'), ...
        'normalGate:session','Use a fresh headless process without a loaded model.');
    candidate=fullfile(jobRoot,'candidate');tests=fullfile(candidate,'tests');
    assert(strcmp(normal_sha(fullfile(candidate,'MANIFEST.json')),candidateManifestSha), ...
        'normalGate:manifest','Candidate manifest identity differs.');
    folder=fullfile(jobRoot,'gates',testName);
    assert(~isfolder(folder)&&~isfile(folder),'normalGate:exists','Never overwrite a gate.');
    [ok,msg,id]=mkdir(folder);assert(ok&&isempty(id),'normalGate:mkdir','%s',msg);
    result=struct('status','started','test',testName,'pid',feature('getpid'), ...
        'candidate_manifest_sha256',candidateManifestSha,'model_loaded',false);
    try
        restoredefaultpath;rehash;cd(jobRoot);
        isRange=strcmp(testName,'test_normal_10v');before=rng;started=tic;
        if isRange
            range=fullfile(jobRoot,'range_helpers');baseline=fullfile(jobRoot,'baseline','single_bank');
            assert(strcmp(normal_sha(fullfile(baseline,'MANIFEST.json')), ...
                '2cbdffe537b694cef6107ce893ea8bca7f8ef5d95f6ff7d993f020150c6dd514'), ...
                'normalGate:baseline','Original v2 manifest differs.');
            addpath(range,'-begin');actual=which(testName);
            assert(same_path(actual,fullfile(range,[testName '.m'])),'normalGate:path','Unexpected range-test path: %s',actual);
            [report,P,normalNominal]=test_normal_10v(baseline);
            assert(isstruct(report)&&strcmp(report.status,'FUNCTION_ASSERTIONS_PASSED'), ...
                'normalGate:test','10V function assertions failed.');
        else
            addpath(tests,'-begin');actual=which(testName);
            assert(same_path(actual,fullfile(tests,[testName '.m'])),'normalGate:path','Test resolves outside candidate: %s',actual);
            report=feval(testName);
            assert(isstruct(report)&&isfield(report,'status')&&strcmp(report.status,'passed'), ...
                'normalGate:test','Actual merged test did not pass.');
        end
        result.elapsed_s=toc(started);assert(isequaln(before,rng),'normalGate:rng','Global RNG changed.');
        reportFile=fullfile(folder,'report.mat');
        if isRange,save(reportFile,'report','P','normalNominal','-v7.3');else,save(reportFile,'report','-v7.3');end
        result.report_sha256=normal_sha(reportFile);result.status=report.status;
        write_new(fullfile(folder,'complete.json'),result);
    catch ex
        result.status='failed';result.error_id=ex.identifier;
        result.error=getReport(ex,'extended','hyperlinks','off');
        try,write_new(fullfile(folder,'failed.json'),result);catch secondary,fprintf(2,'%s\n',getReport(secondary,'extended','hyperlinks','off'));end
        rethrow(ex)
    end
end
function yes=same_path(a,b)
    yes=~isempty(a)&&strcmpi(char(java.io.File(a).getCanonicalPath()),char(java.io.File(b).getCanonicalPath()));
end
function h=normal_sha(file)
    d=dir(file);assert(isscalar(d)&&~d.isdir&&d.bytes<=300000000,'normalGate:size','Missing or oversized: %s',file);
    f=fopen(file,'rb');assert(f>=0,'normalGate:read','Cannot read: %s',file);c=onCleanup(@()fclose(f)); %#ok<NASGU>
    x=fread(f,Inf,'*uint8');md=java.security.MessageDigest.getInstance('SHA-256');md.update(typecast(x(:),'int8'));
    h=lower(reshape(dec2hex(typecast(md.digest(),'uint8'),2).',1,[]));
end
function write_new(file,x)
    assert(~isfile(file)&&~isfolder(file),'normalGate:exists','Receipt already exists.');
    f=fopen(file,'w','n','UTF-8');assert(f>=0,'normalGate:write','Cannot write receipt.');c=onCleanup(@()fclose(f)); %#ok<NASGU>
    fwrite(f,[jsonencode(x) newline],'char');
end
