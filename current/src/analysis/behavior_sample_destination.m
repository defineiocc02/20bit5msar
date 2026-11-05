function outputDir=behavior_sample_destination(runPath,outputDir)
%BEHAVIOR_SAMPLE_DESTINATION Keep generated reports outside their source run.
    assert(isfolder(runPath)&&isfolder(outputDir),'sample:directory', ...
        'Source run and output directory must exist.');
    source=char(java.io.File(char(runPath)).getCanonicalPath());
    outputDir=char(java.io.File(char(outputDir)).getCanonicalPath());
    prefix=source;
    if prefix(end)~=filesep,prefix=[prefix filesep];end
    assert(~strcmpi(outputDir,source)&&~startsWith(lower(outputDir),lower(prefix)), ...
        'sample:sourceWrite','Sample outputs must not be written into the source run.');
end
