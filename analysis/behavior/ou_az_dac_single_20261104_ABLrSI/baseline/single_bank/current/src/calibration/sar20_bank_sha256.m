function hex=sar20_bank_sha256(bytes)
%SAR20_BANK_SHA256 Deterministic SHA-256 for explicit uint8 bytes.
% Pure calculation: no file, persistent state, random source or network.
    assert(isa(bytes,'uint8')&&isreal(bytes),'bankOwner:hashBytes','Require explicit uint8 bytes.');
    md=java.security.MessageDigest.getInstance('SHA-256');
    md.update(bytes(:));
    hex=lower(reshape(dec2hex(typecast(md.digest(),'uint8'),2).',1,[]));
end
