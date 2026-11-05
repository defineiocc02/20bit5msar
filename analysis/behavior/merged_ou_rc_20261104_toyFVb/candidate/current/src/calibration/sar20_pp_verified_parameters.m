function q=sar20_pp_verified_parameters(P)
%SAR20_PP_VERIFIED_PARAMETERS Trusted apply/compile controller; never a signal.
% First bind public P and fixed reviewed artifact; then independently check
% the v3 LOAD/QUALIFY adapter. Only the resulting
% public q enters BankOwner. Same-chip origin is controlled externally; this is not tamper-proof. OFF is transparent.
    [q,Q]=sar20_pp_parameters(P);
    if ~q.enabled,return;end
    sar20_pp_verify_v3_qualification(q,Q);
    q.scope='SOURCE_CONTROLLED_BEHAVIOR_TEST_ONLY';
end
