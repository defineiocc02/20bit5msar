function [before,after]=sb256_diff_values(P0,P,paths)
% Preserve every differing value in MAT format, including class/shape/NaN bits.
    before=cell(size(paths));after=cell(size(paths));
    for k=1:numel(paths)
        parts=strsplit(paths{k},'.');
        assert(numel(parts)>=2&&strcmp(parts{1},'P'),'sb256:diffPath','Invalid P field path.');
        a=P0;b=P;
        for j=2:numel(parts)
            name=parts{j};assert(isstruct(a)&&isscalar(a)&&isfield(a,name)&& ...
                isstruct(b)&&isscalar(b)&&isfield(b,name), ...
                'sb256:diffPath','Missing or non-scalar P field path %s.',paths{k});
            a=a.(name);b=b.(name);
        end
        before{k}=a;after{k}=b;
    end
end
