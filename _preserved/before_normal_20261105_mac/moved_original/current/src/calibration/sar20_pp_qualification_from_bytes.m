function Q=sar20_pp_qualification_from_bytes(bytes)
%SAR20_PP_QUALIFICATION_FROM_BYTES One locked byte image, hash then parse.
% A later path/file replacement cannot change this in-memory parsed object.
    assert(isa(bytes,'uint8')&&isvector(bytes)&&~isempty(bytes), ...
        'pp:qualificationFile','Nonempty qualification bytes required.');
    expected='a9cfaaefed217e5f6d6e7e1a2faa5586e78dbf8f6808523a9c5185c19ab9778f';
    assert(strcmp(sar20_bank_sha256(bytes(:)),expected),'pp:qualificationFile', ...
        'Use the fixed independently reviewed behavior qualification bytes.');
    Q=jsondecode(native2unicode(bytes(:).','UTF-8'));
end
