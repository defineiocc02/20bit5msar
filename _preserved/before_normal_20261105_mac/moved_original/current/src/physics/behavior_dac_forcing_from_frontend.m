function f=behavior_dac_forcing_from_frontend(xFE,bk,eventTime,p)
%BEHAVIOR_DAC_FORCING_FROM_FRONTEND Read-only OLD FE state -> one interval drive.
% This is a pure prediction from the one real FE owner, not another stored B.
% q0/delta/end [C differential RA coordinates], tau/dt [s]. No capacitance,
% ideal input, calibration truth, RNG or new FE command is read or generated.
    c=p.dac_coupling;
    assert(c.enabled&&any(c.tau_dac_s>0),'behaviorDAC:inactive','Do not read old FE port in off/all-zero path.');
    assert(bk.command.ra_on&&~bk.command.reset, ...
        'behaviorDAC:phase','Forcing is meaningful only for the retained active RA interval.');
    fe=behavior_frontend_unpack(xFE,struct('schema',c.frontend_schema));
    id=bk.command.sample_id;epoch=bk.command.epoch;h=double(eventTime)-bk.time_s;
    assert(fe.has_time&&fe.time_s==bk.time_s&&h>=0, ...
        'behaviorDAC:time','OLD FE and backend must start at the same exact interval time.');
    assert(id>=0&&id==floor(id)&&id<size(c.public_plan,1)&& ...
        fe.active_id==id&&fe.active_epoch==epoch, ...
        'behaviorDAC:activeTags','Old FE/backend conversion ID/epoch differ.');
    ids=c.public_plan(id+1,:).';actual=find(fe.phase==2);
    assert(numel(unique(ids))==8&&isequal(sort(ids),actual)&& ...
        all(fe.capture_valid(ids))&&all(fe.capture_id(ids)==id)&&all(fe.capture_epoch(ids)==epoch), ...
        'behaviorDAC:ownership','Actual active capture tags must prove the public plan is exactly the current eight slices.');
    b=fe.B_c(ids,:);target=fe.B_target_c(ids,:);tau=c.tau_dac_s(ids);
    q0=sum(fe.q_initial_c(ids)-sum(b,2));delta=sum(b-target,2);bend=b;
    if h>0
        % Preserve frontend.advance's componentwise relax operations and plan
        % reduction order for the observable endpoint, not an algebraic Q sum.
        for k=1:8
            if tau(k)==0,bend(k,:)=target(k,:);
            elseif isinf(tau(k)),continue;
            else,bend(k,:)=target(k,:)+(b(k,:)-target(k,:))*exp(-h/tau(k));end
        end
    end
    qend=sum(fe.q_initial_c(ids)-sum(bend,2));
    assert(all(delta(tau==0)==0),'behaviorDAC:zeroTauState', ...
        'Zero-tau slices must already have applied their DAC target at commit.');
    pol=behavior_public_pol(id,epoch,p.az.mode);
    if pol<0,q0=-q0;delta=-delta;qend=-qend;end
    assert(isequal(typecast(q0,'uint64'),typecast(bk.command.qres_c,'uint64')), ...
        'behaviorDAC:qresStart','Old command Qres does not match the actual OLD FE point in the same coordinates.');
    assert(all(isfinite([q0;delta;qend])),'behaviorDAC:finite','Nonfinite real FE driving charge.');
    f=struct('q0_c',q0,'delta_q_c',delta,'tau_dac_s',tau, ...
        'q_endpoint_c',qend,'dt_s',h,'source_time_s',fe.time_s, ...
        'physical_ids',ids,'sample_id',id,'epoch',epoch,'polarity',pol);
end
