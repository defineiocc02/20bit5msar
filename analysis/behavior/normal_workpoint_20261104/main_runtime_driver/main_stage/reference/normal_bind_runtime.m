function bound=normal_bind_runtime(runtime,entries,requireFresh)
% Resolve all actual .m files to this runtime in a fresh process.
    loaded=inmem('-completenames');mfiles={};
    for k=1:numel(entries)
        [~,name,ext]=fileparts(entries(k).path);
        if strcmpi(ext,'.m'),mfiles{end+1}=name;end %#ok<AGROW>
    end
    for k=1:numel(loaded)
        [~,name]=fileparts(loaded{k});index=find(strcmpi(name,mfiles),1);
        if isempty(index),continue;end
        assert(~requireFresh,'sbN8:cached','Source cached before binding: %s',loaded{k});
        expected=which(name);assert(~isempty(expected)&&strcmpi(canon(expected),canon(loaded{k})), ...
            'sbN8:cached','Source cached from another path: %s',loaded{k});
    end
    addpath(genpath(fullfile(runtime,'current','src')),fullfile(runtime,'config'),runtime,'-begin');rehash;
    bound=struct('name',{},'path',{});
    for k=1:numel(entries)
        [~,name,ext]=fileparts(entries(k).path);if ~strcmpi(ext,'.m'),continue;end
        expected=fullfile(runtime,strrep(entries(k).path,'/',filesep));actual=which(name);
        assert(~isempty(actual)&&strcmpi(canon(actual),canon(expected)), ...
            'sbN8:sourcePath','Source resolves outside runtime: %s',name);
        bound(end+1)=struct('name',name,'path',actual); %#ok<AGROW>
    end
    assert(numel(bound)==numel(mfiles),'normalCase:sourceCount','Incomplete project function bindings.');
end
function s=canon(p),s=strrep(char(java.io.File(p).getCanonicalPath()),'\','/');end
