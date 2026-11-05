function out=sb256_diff_paths(a,b,prefix)
% Scalar-struct field differences; actual values are retained in P MAT files.
    if sb256_same_bits(a,b),out={};return;end
    if isstruct(a)&&isscalar(a)&&isstruct(b)&&isscalar(b)
        ak=fieldnames(a);bk=fieldnames(b);
        if isequal(sort(ak),sort(bk))&&~isequal(ak,bk),out={prefix};return;end
        keys=union(ak,bk);out={};
        for k=1:numel(keys)
            key=keys{k};where=[prefix '.' key];
            if ~isfield(a,key)||~isfield(b,key),out{end+1}=where; %#ok<AGROW>
            else,out=[out sb256_diff_paths(a.(key),b.(key),where)];end %#ok<AGROW>
        end
    else,out={prefix};end
end
