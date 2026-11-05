function [t,x]=sb_series(out,name,width)
% Preserve original Time/Data classes; reshape only for explicit I1 trace checks.
    listed=out.who;if isstring(listed),listed=cellstr(listed);end
    assert(any(strcmp(listed,name)),'i1N8:missingLog','Missing %s.',name);
    s=out.get(name);assert(isa(s,'timeseries'),'i1N8:logType','%s is not timeseries.',name);
    t=s.Time(:);d=s.Data;assert(isnumeric(t)&&isnumeric(d)&&isreal(t)&&isreal(d), ...
        'i1N8:logValue','%s must have real numeric Time/Data.',name);
    if s.IsTimeFirst,x=reshape(d,numel(t),[]);
    else,x=reshape(permute(d,[ndims(d) 1:ndims(d)-1]),numel(t),[]);end
    assert(isequal(size(x),[numel(t),width])&&all(isfinite(t)), ...
        'i1N8:logShape','Unexpected %s dimensions.',name);
end
