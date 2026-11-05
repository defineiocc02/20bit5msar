function [P,protocol]=make_training_case(base,kind,provenance)
%MAKE_TRAINING_CASE Predeclared physical bench and independent reference setup.
% Caller persists protocol BEFORE run. kind short/train/holdout; short is an
% eight-record interface/rank-rejection gate, never a fit or performance claim.
% This bench constructor may set the known chip; the train callback only gets
% public CalCfg and actual Ref4, never this analog P. No ADC samples generated.
    assert(any(strcmp(kind,{'short','train','holdout'}))&&ischar(provenance)&&~isempty(provenance));
    % v1 2026-10-27: this registered static experiment excludes aperture jitter.
    % Check the caller's P before case construction can normalize any fields.
    assert(~isfield(base.front,'jitter')||~base.front.jitter.enabled, ...
        'calBench:jitterRegistered','Registered static training/holdout requires jitter disabled.');
    % Reject before a case constructor can normalize any caller configuration.
    % Keep the complete post-construction physical gate below as well.
    assert(isfield(base.front,'tau_dac_s')&&all(base.front.tau_dac_s(:)==0), ...
        'calBench:dacRegistered','Registered static training/holdout requires tau_dac_s=0; finite settling needs a separately registered protocol.');
    protocol=make_training_protocol();N=protocol.train.records;
    suite=make_adi_cases(base,N,protocol.sigma_unit_fraction,protocol.chip_seed);P=suite.cases(8).P;
    trial=protocol.train;
    if strcmp(kind,'short'),trial.records=8;end
    if strcmp(kind,'holdout'),trial=protocol.holdout;end
    P.N=trial.records;P.first_id=trial.first_id;P.epoch=trial.epoch;P.input=trial.source;
    assert(P.front.plan_rows==protocol.public_plan_rows,'calBench:plan','Require the predeclared complete public plan.');
    % The independent reference source is declared here, not fitted/read from
    % ADC output or its current saved P.input. Both consume this bench contract.
    u=trial.source;
    ref=struct('enabled',true,'source','declared_external_reference','provenance',provenance, ...
        'sample_period_s',protocol.sample_period_s,'epoch',trial.epoch, ...
        'first_id',trial.first_id,'records',trial.records, ...
        'offset_v',u.offset_v,'amplitude_v',u.amplitude_v, ...
        'frequency_hz',u.frequency_hz,'phase_rad',u.phase_rad);
    P.training=struct('enabled',~strcmp(kind,'holdout'),'reference',ref);
    P.debug.adi_enabled=false;
    % Fixed known static model for this first identification experiment.
    assert(~P.front.ktc_enabled&&all(P.front.tau_sample_s==0)&&all(P.front.tau_precharge_s==0)&& ...
        all(P.front.tau_dac_s==0)&&strcmp(P.backend.az.mode,'off')&&P.backend.ra.vos_input_v==0&& ...
        P.backend.ra.A0==1e4&&P.backend.ra.UGB_hz==1.2e9, ...
        'calBench:physical','Starting conditions differ from the predeclared static identification experiment.');
end
