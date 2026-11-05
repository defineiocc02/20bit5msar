job='D:/Temp/SAR20NORMAL_20261104_NX';phase=getenv('SAR20_NORMAL_CASE');
allowed={'ideal_v2_n8','ideal_merged_n8','normal_merged_n8','normal_merged_n8_tap','ideal_merged_n256','normal_merged_n256'};
assert(any(strcmp(phase,allowed)),'normalMain:phase','Unknown case.');
receipt=fullfile(job,[phase '_wrapper.json']);assert(~isfile(receipt),'normalMain:exists','Receipt exists.');
r=struct('status','started','phase',phase,'pid',feature('getpid'));
try
    assert(r.pid~=27628&&~usejava('desktop')&&~bdIsLoaded('SarAdc'),'normalMain:session','Fresh headless process required.');
    restoredefaultpath;rehash;cd(job);addpath(fullfile(job,'scripts'),'-begin');
    report=normal_case(job,phase);assert(strcmp(report.status,'passed'),'normalMain:case','Case did not pass.');
    r.status='passed';r.result=report.status;write_receipt(receipt,r);
catch ex
    r.status='failed';r.error_id=ex.identifier;r.error=getReport(ex,'extended','hyperlinks','off');
    try,write_receipt(receipt,r);catch nested,fprintf(2,'%s\n',getReport(nested,'extended','hyperlinks','off'));end
    rethrow(ex)
end
function write_receipt(file,r)
    assert(~isfile(file)&&~isfolder(file),'normalMain:exists','Receipt exists.');
    f=fopen(file,'w','n','UTF-8');assert(f>=0,'normalMain:write','Cannot write receipt.');c=onCleanup(@()fclose(f)); %#ok<NASGU>
    fwrite(f,[jsonencode(r) newline],'char');
end
