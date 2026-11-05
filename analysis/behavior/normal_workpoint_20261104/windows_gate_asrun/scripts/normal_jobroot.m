function root=normal_jobroot(jobRoot)
% Scratch task root must be a real direct child of D:/Temp; external controller rejects nested reparse points.
    assert(ispc&&ischar(jobRoot)&&isfolder(jobRoot),'normalJob:root','Use an existing Windows scratch directory.');
    p=java.io.File(jobRoot).toPath();absolute=char(p.toAbsolutePath().normalize().toString());
    opts=javaArray('java.nio.file.LinkOption',0);actual=char(p.toRealPath(opts).toString());
    a=lower(strrep(absolute,'\','/'));b=lower(strrep(actual,'\','/'));
    assert(strcmp(a,b)&&~isempty(regexp(b,'^d:/temp/sar20normal_[a-z0-9_-]+$','once')), ...
        'normalJob:root','Require real direct D:/Temp/SAR20NORMAL_<id>.');
    root=actual;
end
