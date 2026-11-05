function hex=sar20_bank_certificate_sha256(certificate)
%SAR20_BANK_CERTIFICATE_SHA256 Hash one flat, versioned certificate struct.
% Canonical bytes are UTF-8 of MATLAB jsonencode(orderfields(certificate)).
% Trust anchors must be provisioned by an external evidence verifier. Hash
% equality alone does not authenticate who issued the certificate.
    assert(isstruct(certificate)&&isscalar(certificate), ...
        'bankOwner:certificateShape','Certificate must be one scalar struct.');
    hex=sar20_bank_sha256(unicode2native(jsonencode(orderfields(certificate)),'UTF-8'));
end
