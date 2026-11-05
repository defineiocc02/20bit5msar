function x=sar20_pp_initial_state(q)
%SAR20_PP_INITIAL_STATE One explicit digital UnitDelay owner, 64 doubles.
% No ADC/train/Ref/holdout data. Startup expects first real RX raw_ready ID0.
    assert(isstruct(q)&&isscalar(q)&&isfield(q,'enabled'),'pp:context','Use applied P context.');
    x=zeros(64,1);x(1)=20261028;x(6)=-1;x(8)=-1;x(10)=-1;x(11)=-1;
    if q.enabled,x(2)=q.initial_slot;end
end
