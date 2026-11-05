function [P,assumptions,ideal] = normal_parameters(Pbase)
%NORMAL_PARAMETERS Expected operating-point estimate for the single-array ADC.
% Version 1, 2026-11-04. Caller: isolated MATLAB qualification/run driver.
% Usage: [P,A,ideal]=normal_parameters(Pbase), with the complete verified N8 P.
% Requires the qualified OU/RC/comparator merge and normal_10v_configuration.
% Outputs: P is the prepared normal estimate; A records its derivation and
% omissions; ideal is the same 10 V range with the original baseline physics.
% This does not write files, change paths, draw global RNG, fit a spectrum,
% enable ADI, or read a calibration/holdout answer. SI units throughout.

    beforeRng=rng;
    [ideal,range] = normal_10v_configuration(Pbase);
    assert(ideal.N==8 && ideal.front.single_bank && ideal.Ts_s==200e-9, ...
        'normal:baseline','Require the verified single-bank N8, 5 MS/s baseline.');
    P=ideal;
    assert(iscell(P.assumptions)&&numel(P.assumptions)>=2&& ...
        strcmp(P.assumptions{2},'Sampling/DAC initially fully settled; their finite-settling tests pending'), ...
        'normal:assumptions','Review inherited settling assumptions before using this profile.');
    P.assumptions{2}=['Finite sampling RC+kTC and finite DAC are enabled; ' ...
        'values are design estimates and require joint graph validation'];

    % One fixed chip: the eight identical rows are numerical subdivisions,
    % never eight independent arrays. Ac_pair and density are planning
    % assumptions, not foundry matching data. The single-unit sigma formula
    % supplies independent capacitor-group errors scaled by sqrt(N); one
    % symmetric effective array is used, with no separate P/N mismatch draw.
    branch=[16 32*ones(1,31) 16 8 4 2 1];
    density_f_per_um2=1e-15;
    Ac_pair=0.005;                       % relative * um, assumed
    unitArea_um2=27e-15/density_f_per_um2;
    sigmaUnit=Ac_pair/sqrt(2*unitArea_um2);
    chipSeed=20261104;
    chipStream=RandStream('mt19937ar','Seed',chipSeed);
    z=randn(chipStream,1,37);
    relative=sigmaUnit*z./sqrt(branch);
    row=P.front.unit_cap_f*branch.*(1+relative);
    assert(all(row>0)&&all(isfinite(row)),'normal:cap','Invalid chip capacitance; no clipping or redraw.');
    P.front.C_f=repmat([row 0],18,1);
    P.front.mismatch_enabled=true;
    P.front.Cp_f=repmat(100e-15/8,18,1);  % total 100 fF per half, assumed

    % Sampling load uses total top C for the RC estimate. Its thermal noise
    % uses signal C per half inside the physical kernel. Two half-circuit
    % Johnson sources are independent; no driver excess noise is included.
    ctop=sum(P.front.C_f(1:8,:),'all')+sum(P.front.Cp_f(1:8));
    Ron_eq=20;                           % driver + switch, ohm, assumed
    P.front.single_guard_s=2e-9;         % release-to-acquire nonoverlap
    P.front.tau_sample_s(:)=Ron_eq*ctop;
    P.front.tau_precharge_s(:)=0;         % ideal tail precharge; not coverage
    P.front.ktc_enabled=true;
    P.front.temperature_K=298.15;
    P.front.ktc_seed=20261027;
    P.front.tau_dac_s(:)=0.5e-9;         % linear single-pole DAC estimate
    P.backend.dac_coupling.enabled=true;

    % Ordinary AZ suppresses a fixed 1 mV RA input offset through finite
    % write/hold dynamics. Residual offset must be measured from actual codes.
    % The existing write window and event calendar are kept.
    % The 10 ms hold constant is an explicit low-leakage design assumption.
    P.backend.ra.vos_input_v=1e-3;
    P.backend.az.mode='ordinary';
    P.backend.ni.az=true;
    P.digital.az_mode='ordinary';
    P.ni.az=true;
    P.backend.az.write_tau_s=[1e-9;1e-9];
    P.backend.az.leak_tau_s=[10e-3;10e-3];
    P.backend.az.sense_injection_half_v=zeros(2,1);

    % Keep the nominal 900 fF CT design and its public decode weights. Only
    % the physical main/replica CINC pair receives the declared 1-sigma pair
    % difference: 0.5%*um / sqrt(900 um^2). Other DAC2 caps stay nominal.
    nominal=P.backend.ct.net_nominal;
    pairSigma=Ac_pair/sqrt(900e-15/density_f_per_um2);
    P.backend.ct.net_actual=nominal;
    P.backend.ct.net_replica=nominal;
    P.backend.ct.net_actual.cinc_f=nominal.cinc_f*(1+pairSigma/2);
    P.backend.ct.net_replica.cinc_f=nominal.cinc_f*(1-pairSigma/2);
    P.backend.ni.cap_mismatch=true;

    % A1 channel thermal-noise estimate only: 350 uA total pair current,
    % 175 uA per branch, gm/Id=15 V^-1 for both complementary input devices.
    % en^2=8*k*T*gamma/(gm_n+gm_p), one-sided V^2/Hz. The OU model uses
    % the same linear closed-loop pole as the signal: ENBW=1/(4*tau).
    % This excludes other stages, tail/load excess noise, 1/f and AZ noise.
    kB=1.380649e-23; gamma=2/3; gmId=15;
    branchCurrent_A=175e-6;
    gmTotal_S=2*branchCurrent_A*gmId;
    en=sqrt(8*kB*P.front.temperature_K*gamma/gmTotal_S);
    NG=1+ctop/P.backend.ra.Cf_f;
    gainFactor=P.backend.ra.A0/(P.backend.ra.A0+NG);
    tauRA=NG/(2*pi*P.backend.ra.UGB_hz);
    sigmaVX=en*gainFactor*NG*sqrt(1/(4*tauRA));
    P.backend.ni.ra_noise=true;
    P.backend.ra_noise=struct('schema','sar20-ra-ou/v1', ...
        'sigma_vx_rms',sigmaVX,'seed_u64',uint64(20261104));

    % SAR2 and tracking: independent decision input noise at physical VY.
    % Ceff=100 fF is an unverified equivalent-noise-capacitance assumption,
    % not a disclosed latch capacitor. No regeneration/delay/timeout model.
    % SAR1 fine/Flash noise and all comparator offsets remain unestimated.
    Ceff_f=100e-15;
    sigmaCmp=sqrt(2*kB*P.front.temperature_K/Ceff_f);
    P.control.comparator=struct('enabled',true,'sar1_offset_v',0, ...
        'sar1_noise_rms_v',0,'sar2_offset_v',0, ...
        'sar2_noise_rms_v',sigmaCmp,'seed_u64',uint64(20261105), ...
        'tie_decision',true);
    P=behavior_prepare_configuration(P);

    % Public reconstruction is nominal. Actual C above is consumed only by
    % the analog charge/noise model; it cannot alter the digital weights.
    d=P.digital; d.az_mode=ideal.digital.az_mode;
    assert(isequaln(d,ideal.digital),'normal:decode','Actual chip data leaked into digital reconstruction.');
    assert(strcmp(P.backend.az.mode,'ordinary')&&strcmp(P.digital.az_mode,'ordinary'), ...
        'normal:AZ','Physical AZ and digital polarity mode must both be ordinary.');
    for id=0:3
        route=behavior_az_schedule(id,P.epoch,struct('offset_s',0,'ra_on',false),P);
        assert(route.polarity==1&&route.qres_sign==1&& ...
            behavior_public_pol(id,P.epoch,P.digital.az_mode)==1, ...
            'normal:polarity','Ordinary AZ must retain positive public polarity.');
    end
    assert(isequaln(beforeRng,rng),'normal:rng','Profile creation changed global RNG.');
    assert(~P.front.dem_enabled&&~P.front.dither_enabled&&~P.front.jitter.enabled&& ...
        ~P.transport.enabled&&~P.training.enabled&&~P.cal_cfg.enabled&& ...
        ~P.frozen.enabled&&~P.bank.enabled&&strcmp(P.digital.calibration_mode,'off'), ...
        'normal:boundary','ADI, transport, legacy calibration or unsupported jitter enabled.');
    assert(P.ni.sample_ktc&&P.ni.sample_settling&&P.ni.dac_settling&& ...
        P.ni.ra_noise&&P.ni.comparator_noise&&P.ni.az&&P.ni.cap_mismatch, ...
        'normal:coverage','Physical implementation and enabled summary disagree.');

    release=P.calendar(strcmp({P.calendar.type},'release'));
    acquisitionWindow=P.Ts_s-release.time_s-P.front.single_guard_s;
    signalC=sum(P.front.group_C_f(1:8,1));
    assumptions=struct('status','EXPECTED_OPERATING_ESTIMATE_NOT_PDK_TYPICAL', ...
        'information_boundary','PRIVATE_ANALOG_DIAGNOSTIC_NOT_CALIBRATION_INPUT', ...
        'range',range,'chip_seed',chipSeed,'cap_density_f_per_um2',density_f_per_um2, ...
        'Ac_pair_relative_um',Ac_pair,'unit_relative_sigma',sigmaUnit, ...
        'chip_normal_z',z,'branch_relative_error',relative, ...
        'front_pn_capacitance','one symmetric effective array; P/N mismatch not separately represented', ...
        'ct_other_caps','nominal; only main/replica CINC difference is applied', ...
        'CINC_pair_relative_sigma',pairSigma, ...
        'CINC_mismatch_scope','explicit deterministic 1-sigma pair example; inherited generator sigma is unused', ...
        'sample_ktc_seed',P.front.ktc_seed,'ra_noise_seed_u64',P.backend.ra_noise.seed_u64, ...
        'cmp_noise_seed_u64',P.control.comparator.seed_u64,'Ron_eq_ohm',Ron_eq, ...
        'Csignal_half_f',signalC,'equilibrium_ktc_diff_rms_v',sqrt(2*kB*P.front.temperature_K/signalC), ...
        'Ctop_half_f',ctop,'acquisition_window_s',acquisitionWindow, ...
        'guard_s',P.front.single_guard_s,'sample_tau_s',P.front.tau_sample_s(1), ...
        'dac_tau_s',P.front.tau_dac_s(1),'ra_vos_input_v',P.backend.ra.vos_input_v, ...
        'az_write_tau_s',P.backend.az.write_tau_s,'az_leak_tau_s',P.backend.az.leak_tau_s, ...
        'A0',P.backend.ra.A0,'UGB_hz',P.backend.ra.UGB_hz, ...
        'A1_branch_current_A',branchCurrent_A,'gmId_per_v',gmId,'gamma',gamma, ...
        'ra_noise_scope','350 uA total pair current; N/P both effective; A1 channel thermal only; OU pole equals signal pole', ...
        'A1_en_v_per_sqrt_hz',en,'noise_gain',NG,'ra_tau_s',tauRA, ...
        'ra_sigma_vx_rms',sigmaVX,'cmp_Ceff_f',Ceff_f,'cmp_sigma_vy_rms',sigmaCmp, ...
        'calibration','OFF; no fitted/corrected output is fed back', ...
        'jitter','OFF: finite-RC joint qualification absent; 0.5 ps is a separate design budget', ...
        'uncovered','driver/reference noise and recovery; other RA stages and 1/f/AZ noise; finite slew; full CT parasitics; SAR1/Flash noise; comparator regeneration/timeout; PDK and power');
end
