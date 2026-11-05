function [z,digest_hex]=behavior_comparator_keyed_normal(seed,epoch,id,eventCode,eventIndex)
%BEHAVIOR_COMPARATOR_KEYED_NORMAL Stateless domain-separated event noise.
% SHA-256 payload uses its OWN comparator domain and exact integer words.
% Same tuple produces the same sample, regardless of Outputs call count/order.
% As in the existing RA helper, IEEE log/cos may differ across platforms; this
% is a behavioral Gaussian assumption, not comparator or process qualification.
    assert(isa(seed,'uint64')&&isscalar(seed),'sar20Cmp:seed','Seed must be uint64 scalar.');
    keys={epoch,id,eventCode,eventIndex};
    for k=1:numel(keys)
        v=keys{k};assert(isnumeric(v)&&isreal(v)&&isscalar(v)&&isfinite(v)&& ...
            v>=0&&v<=2^32-1&&v==floor(v),'sar20Cmp:key','Keys must be uint32-valued.');
    end
    payload=[uint8('SAR20-COMPARATOR-v1'),uint8(0),word(seed), ...
        word(uint64(epoch)),word(uint64(id)),word(uint64(eventCode)),word(uint64(eventIndex))];
    assert(usejava('jvm'),'sar20Cmp:jvm','Keyed comparator noise requires the MATLAB JVM.');
    md=java.security.MessageDigest.getInstance('SHA-256');
    md.update(typecast(payload(:),'int8'));
    digest=typecast(md.digest(),'uint8');
    assert(numel(digest)==32,'sar20Cmp:digest','SHA-256 digest must be 32 bytes.');
    a=readword(digest(1:8));b=readword(digest(9:16));
    scale=4503599627370496;
    u1=(double(bitshift(a,-12))+0.5)/scale;
    u2=(double(bitshift(b,-12))+0.5)/scale;
    assert(u1>0&&u1<1&&u2>0&&u2<1,'sar20Cmp:uniform','Invalid open-interval uniforms.');
    z=sqrt(-2*log(u1))*cos(2*pi*u2);
    assert(isfinite(z),'sar20Cmp:normal','Nonfinite comparator sample.');
    if nargout>1
        digest_hex=lower(reshape(dec2hex(digest(:),2).',1,[]));
    end
end
function b=word(v)
    b=zeros(1,8,'uint8');
    for j=1:8,b(j)=uint8(bitand(bitshift(v,-8*(8-j)),uint64(255)));end
end
function v=readword(b)
    v=uint64(0);
    for j=1:8,v=bitor(bitshift(v,8),uint64(b(j)));end
end
