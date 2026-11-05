job='D:/Temp/SAR20NORMAL_20261104_NX';phase=getenv('SAR20_NORMAL_PHASE');
names={'test_single_rc_ktc','test_joint_ou_az_dac','test_joint_ou_rc_return','test_comparator_single','test_normal_10v','profile'};
ix=find(strcmp(phase,names));assert(isscalar(ix),'normalEntry:phase','Unknown phase.');
receipt=fullfile(job,[phase '_wrapper.json']);assert(~isfile(receipt),'normalEntry:exists','Receipt exists.');
r=struct('status','started','phase',phase,'pid',feature('getpid'));
try
    assert(r.pid~=27628&&~usejava('desktop')&&~bdIsLoaded('SarAdc'),'normalEntry:session','Fresh headless process required.');
    restoredefaultpath;rehash;cd(job);addpath(fullfile(job,'scripts'),'-begin');
    sha='73867eabe50b70920cd3373190832e2d78426c59b0116d6062ff94c4c903f14c';
    if strcmp(phase,'profile')
        report=normal_profile(job,sha,names(1:5));expected='prepared';
    else
        report=normal_gate(job,phase,sha);expected='passed';
        if strcmp(phase,'test_normal_10v'),expected='FUNCTION_ASSERTIONS_PASSED';end
    end
    assert(strcmp(report.status,expected)&&~bdIsLoaded('SarAdc'),'normalEntry:status','Phase status/model gate failed.');
    if strcmp(phase,'test_normal_10v'),r.v2_cached_sources=check_v2_cache(job);end
    r.status='passed';r.actual_status=report.status;write_receipt(receipt,r);
catch ex
    r.status='failed';r.error_id=ex.identifier;r.error=getReport(ex,'extended','hyperlinks','off');
    try,write_receipt(receipt,r);catch nested,fprintf(2,'%s\n',getReport(nested,'extended','hyperlinks','off'));end
    rethrow(ex)
end
function count=check_v2_cache(job)
    baseline=fullfile(job,'baseline','single_bank');mf=fullfile(baseline,'MANIFEST.json');
    meta=jsondecode(fileread(mf));loaded=inmem('-completenames');checked=struct('name',{},'path',{});
    for k=1:numel(meta.items)
        rel=char(meta.items(k).path);[~,name,ext]=fileparts(rel);
        if ~strcmpi(ext,'.m')||~(strcmp(rel,'SAR20.m')||startsWith(rel,'config/')||startsWith(rel,'current/src/')),continue;end
        for j=1:numel(loaded)
            [~,actualName]=fileparts(loaded{j});if ~strcmpi(actualName,name),continue;end
            expected=fullfile(baseline,strrep(rel,'/',filesep));
            assert(strcmpi(char(java.io.File(loaded{j}).getCanonicalPath()), ...
                char(java.io.File(expected).getCanonicalPath())), ...
                'normalEntry:cache','Cached baseline function resolved elsewhere: %s',loaded{j});
            checked(end+1)=struct('name',name,'path',loaded{j}); %#ok<AGROW>
        end
    end
    count=numel(checked);assert(count>0,'normalEntry:cache','No baseline functions recorded after range test.');
    save(fullfile(job,'gates','test_normal_10v','inmem_after.mat'),'checked','-v7.3');
end
function write_receipt(file,r)
    assert(~isfile(file)&&~isfolder(file),'normalEntry:exists','Receipt exists.');
    f=fopen(file,'w','n','UTF-8');assert(f>=0,'normalEntry:write','Cannot write receipt.');c=onCleanup(@()fclose(f)); %#ok<NASGU>
    fwrite(f,[jsonencode(r) newline],'char');
end
