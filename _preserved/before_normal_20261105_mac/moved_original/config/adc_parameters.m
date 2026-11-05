function P=adc_parameters()
%ADC_PARAMETERS User-editable behavior-model parameters, v1 2026-10-27.
% Caller: the public ADC entry. Output: the same named P used by the validated
% event runner/SLX. Only local nominal.mat is read; no old workspace or paths.
% The model is a design-level behavior approximation, not fitted ADC spectrum.
    nominalFile=fullfile(fileparts(mfilename('fullpath')),'nominal.mat');
    assert(isfile(nominalFile),'adc:nominalMissing','Missing config/nominal.mat.');
    loaded=load(nominalFile,'nominal');
    assert(isfield(loaded,'nominal')&&isstruct(loaded.nominal)&&isscalar(loaded.nominal), ...
        'adc:nominal','nominal.mat must contain the small nominal design struct.');
    saved=loaded.nominal;
    % Compatibility names consumed by the existing small backend constructor.
    % All three contain NOMINAL geometry; no old actual chip/state is imported.
    saved.dac2.net_actual=saved.dac2.net_nominal;
    saved.dac2.net_replica=saved.dac2.net_nominal;

    % Record length [samples], integer >=1. N>=256 permits the spectrum gate;
    % changing N extends the genuine event simulation, never replays old codes.
    N=8;
    % Sample period [s], positive; 200 ns means 5 MS/s. Event timings remain
    % explicit in behavior_calendar; changing Fs requires checking that calendar.
    Ts_s=200e-9;
    % Capture starts at sample ID first_id [integer >=0]; prior samples warm up.
    first_id=4;
    % Epoch and master label seed [integers]. Enabled feature seeds are explicit
    % frontend fields; this label does not silently reseed any noise source.
    epoch=1;seed=20261020;
    P=struct('schema','sar20-behavior/v1','Ts_s',Ts_s,'N',N, ...
        'first_id',first_id,'epoch',epoch,'seed',seed);
    % Read-only physical-wire diagnostics. Default off stores at most one NaN
    % row; true requires N8. This does not enable a physical nonideality.
    P.debug=struct('adi_enabled',false,'dac_enabled',false,'dac_max_points',1);
    % dac_enabled only records actual pre-CINC RAadvance obs8; true is N8-only.
    % Public transport defaults: OFF uses ADC RawReady without protocol replay.
    % ON uses32bit/N−2 RX, sample-CNV to RX538ns, two real CNV flush cycles.
    % public_en=10 means binary1010 normal mode; startup EN is derived/checked
    % by prepare, not an RX hidden ID/epoch. Full pin trace is explicit N8 only.
    P.transport=struct('enabled',false,'public_en',10,'trace_enabled',false);

    % Differential source: offset/amplitude [V], f [Hz >=0], phase [rad].
    % Amplitude >=0; choose f<Fs/2. No automatic frequency retuning is performed.
    % 97.65625 kHz is bin 5 for N=256 at 5 MS/s; N8 is a functional record.
    P.input=struct('offset_v',0,'amplitude_v',3.650563842595822, ...
        'frequency_hz',97656.25,'phase_rad',0.731);

    % Total top-connected sampling C per half [F >0], across eight 1056-Cu
    % arrays. 28 pF is a declared design assumption, not a recovered C definition.
    % Signal-only C is 1024/1056 of this total and is used to set nominal gain.
    top_sampling_cap_f=28e-12;
    unit=top_sampling_cap_f/(8*1056);
    % DEM/dither flags enable actual switching/charge actions, not plot labels.
    % Mismatch requires explicit actual C_f in frontend options. Sampling kT/C
    % is injected once into retained capacitor charge at the actual aperture;
    % the current equilibrium-noise model requires tau_sample_s=0.
    options=struct('plan_rows',max(32,N+P.first_id+4),'unit_cap_f',unit, ...
        'input',P.input,'dem_enabled',false,'dither_enabled',false, ...
        'mismatch_enabled',false,'ktc_enabled',false);
    % Frontend DAC reference [V >0]. CT reference/nominal digital scales remain
    % separate nominal design values in nominal.mat; changing Vref is a design change.
    options.vref_v=4.096;
    % Sampling thermal noise: absolute temperature [K >=0] and independent
    % uint32 seed. Differential variance=2*kB*T/Csample_half per physical slice.
    % T=0 produces zero thermal perturbation and is not enabled NI coverage.
    options.temperature_K=298.15;options.ktc_seed=20261027;
    % Endpoint aperture error [s], default off; event/compare calendar unchanged.
    % Enable through explicit P.front.jitter and apply; prepare binds the actual
    % coarse-latch bound. Finite sampling RC with jitter is not implemented.
    options.jitter=behavior_jitter_parameters();
    % Settling time constants [s >=0], zero=fully settled, Inf=hold. Sampling,
    % tail precharge can use positive tau. Finite DAC-to-RA interval coupling
    % needs backend.dac_coupling.enabled=true and linear RA slew=Inf; default0.
    options.tau_sample_s=0;options.tau_precharge_s=0;options.tau_dac_s=0;
    [~,P.front]=behavior_frontend_init(options);
    Csample=8*1024*unit;

    % RA: A0 [1 >0 or Inf], UGB [Hz >0 or Inf]. Inf disables the respective
    % finite-gain/bandwidth effect. These are explicit single-pole assumptions.
    % Cf [F >0]=signal C/32; NG separately uses total top C, including Cp.
    % Reset tau [s >=0] controls analog decay; zero means ideal fast reset.
    A=struct('A0',1e4,'UGB_hz',1.2e9,'Cf_f',Csample/32,'tau_reset_s',1e-9);
    P.backend=behavior_backend_parameters(saved,A);
    % Explicit DAC->RA interval coupling; default OFF requires tau_dac_s=0.
    % Finite tau needs enabled=true; prepare binds exact normalized FE tau/plan.
    P.backend.dac_coupling=struct('enabled',false);
    % Input-referred RA offset [V]; slew [V/s >0], Inf disables the endpoint
    % slew approximation. Factory RA OU remains OFF, preserving legacy P.
    % User enable through the public entry (factory default remains OFF):
    % P=adc_parameters();
    % P.backend.ni.ra_noise=true;
    % P.backend.ra_noise=struct('schema','sar20-ra-ou/v1', ...
    %   'sigma_vx_rms',1e-3,'seed_u64',uint64(20261030));
    % sigma_vx_rms is differential VX stationary RMS in V at fixed RA pole;
    % 1 mV is an example stress assumption, not a fitted circuit parameter.
    % SAR20('apply',P); SAR20('check'); SAR20('run');
    % ON requires infinite slew, finite UGB and zero DAC tau; AZ, comparator
    % noise, reference recovery, training, Frozen and Bank must remain OFF.
    % Other combinations, noise sources and circuit/PDK behavior are unverified.
    % ON checks P.ni labels against actual RA gain/UGB, finite sampling tau,
    % selected physical C mismatch and the narrow front-Cp/RA-load indicator.
    % Zero/Inf sampling tau are not finite settling; Inf holds and is not covered.
    % P.ni.parasitic does NOT describe the complete CT parasitic network.
    % A +Inf sar2.limit_v disables the model overrange test; it is not coverage.
    P.backend.ra.vos_input_v=0;P.backend.ra.slew_v_per_s=Inf;
    % CINC kick=true applies main/replica delta-Q to the same continuous VX.
    % The nominal file has no actual mismatch sample; mismatch remains off.
    P.backend.ni.cap_mismatch=false;P.backend.ni.cinc_kick=true;
    % AZ mode: off | ordinary | chop | hold | hold_chop.
    % ordinary/chop write each service; hold/hold_chop write even ID and hold
    % its odd partner. Chopped modes use public POL=[+1,-1,-1,+1].
    % The 0..31.25 ns write window is an explicit engineering allocation within
    % SAR1, ending at existing RA-start. It does not add any simulator event.
    P.backend.az.mode='off';
    P.backend.ni.az=~strcmp(P.backend.az.mode,'off');
    P.backend.az.write_start_s=0;P.backend.az.write_end_s=31.25*1e-9;
    % Write tau [s >0 finite when enabled], leakage tau [s >=0 or Inf].
    % Stored input-half voltages follow sensed Vos with a finite RC response.
    % Sense table [2 x K V] is deterministic injection, NOT random AZ noise.
    % Signal reset retains storage; epoch changes revoke validity, not charge.
    P.backend.az.write_tau_s=[1e-9;1e-9];
    P.backend.az.leak_tau_s=[Inf;Inf];
    P.backend.az.target_input_half_v=[0;0];
    P.backend.az.initial_input_half_v=[0;0];
    P.backend.az.sense_injection_half_v=zeros(2,1);

    P.control=behavior_control_parameters(saved);
    P.control.sample_period_s=P.Ts_s;
    % Coarse offset/noise [V]. This deterministic baseline has no comparator
    % noise generator; do not enable a coverage label to claim generated noise.
    P.control.sar1.coarse_offset_v=0;P.control.sar1.coarse_noise_rms_v=0;
    P.digital=behavior_decode_parameters(saved,P.front.vref_v,P.backend.az.mode);
    % Digital input-referred dither addback (+dn once) follows the physical
    % frontend flag/seed/amplitude; do not multiply this term by CT polarity.
    P.digital.dither_enabled=P.front.dither_enabled;
    if P.front.dither_enabled
        P.digital.dither_seed=P.front.dither_seed;
        P.digital.dither_amplitude_v=P.front.dither_input_amplitude_v;
    end
    P.fs_hz=1/P.Ts_s;P.fsr_diff_v=P.digital.fsr_diff_v;
    % Derived coverage summary, NOT independent enable knobs. Modify the real
    % parameters/feature flags above; unsupported features are not activated here.
    % Parasitic includes frontend Cp and active fixed RA-output load, not a scan.
    P.ni=struct('ra_finite_gain',isfinite(A.A0),'ra_finite_bandwidth',isfinite(A.UGB_hz), ...
        'sample_ktc',P.front.ktc_enabled&&P.front.temperature_K>0, ...
        'sample_settling',any(isfinite(P.front.tau_sample_s)&P.front.tau_sample_s>0), ...
        'dac_settling',P.backend.dac_coupling.enabled&& ...
        any(isfinite(P.front.tau_dac_s)&P.front.tau_dac_s>0), ...
        'cap_mismatch',P.front.mismatch_enabled||P.backend.ni.cap_mismatch, ...
        'parasitic',any(P.front.Cp_f>0)|| ...
        (P.backend.ni.cinc_kick&&any(P.backend.ct.output_parasitic_half_f>0)), ...
        'jitter',P.front.jitter.enabled&& ...
        (P.front.jitter.common_sigma_s>0||P.front.jitter.local_sigma_s>0||any(P.front.jitter.fixed_slice_skew_s~=0)), ...
        'az',P.backend.ni.az, ...
        'reference_recovery',false,'comparator_noise',false);
    P.assumptions={'RA A0/UGB/closed-loop single pole are design assumptions'; ...
        'Sampling/DAC initially fully settled; their finite-settling tests pending'; ...
        'CINC geometry/scaling inherited from the nominal saved configuration'; ...
        'No calibration and no pin-level LVDS timing claim'};
end
