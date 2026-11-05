function yes=sb_same_bits(a,b)
% Class, shape, and exact numeric bits; compare cells/structs recursively.
    yes=strcmp(class(a),class(b))&&isequal(size(a),size(b));
    if ~yes,return;end
    if isstruct(a)
        names=fieldnames(a);yes=isequal(names,fieldnames(b));
        if ~yes,return;end
        for i=1:numel(a)
            for k=1:numel(names)
                if ~sb_same_bits(a(i).(names{k}),b(i).(names{k})),yes=false;return;end
            end
        end
    elseif iscell(a)
        for i=1:numel(a)
            if ~sb_same_bits(a{i},b{i}),yes=false;return;end
        end
    elseif isa(a,'double')||isa(a,'single')
        if ~isreal(a)||~isreal(b)
            yes=sb_same_bits(real(a),real(b))&&sb_same_bits(imag(a),imag(b));return;
        end
        kind='uint64';if isa(a,'single'),kind='uint32';end
        yes=isequal(typecast(a(:),kind),typecast(b(:),kind));
    elseif isnumeric(a)||islogical(a)||ischar(a)||isstring(a)
        yes=isequaln(a,b);
    else
        error('i1N8:unsupportedType','Unsupported comparison type %s.',class(a));
    end
end
