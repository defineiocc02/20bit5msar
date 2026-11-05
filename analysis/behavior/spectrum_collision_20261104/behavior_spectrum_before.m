function result=behavior_spectrum(code20,p)
%BEHAVIOR_SPECTRUM Characterize actual reconstructed 20-bit codes without generation.
%Version: v1 (2026-10-27). Caller: capture validation/postprocessing.
%Inputs code20 integer vector [0,2^20), saved p.fs_hz [Hz], fsr_diff_v [V] and
%stimulus frequency [Hz]/amplitude [V]/phase [rad]; output result metrics [dB,bits]
%and frequency [Hz]/power [V^2]. N<256 returns not_run without performance metrics.
%Stateless; does not reset a model, generate samples or consume RNG.
%Model: coherent rectangular single-sided spectrum, DC excluded; H2..H10 only
%for THD/SNR harmonic separation, ENOB without full-scale amplitude correction.
%No static-linearity, transistor or PDK acceptance is implied.
%
% KEY DEFINITIONS
%   bin       round(fin*N/fs); an exact-coherence gate rejects anything else
%   signal    power at the fundamental bin only
%   nd        total power outside DC and the fundamental (noise + distortion)
%   harmonics H2..H10 folded back into band, since they may alias above Nyquist
%   noise     nd minus the harmonic bins  -> SNR
%   SNDR      signal / nd                 -> includes harmonics
%   THD       harmonic power / signal power
%   ENOB      (SNDR - 1.76)/6.02, with no full-scale amplitude correction
    assert(isnumeric(code20)&&isreal(code20)&&isvector(code20)&& ...
        all(isfinite(code20(:)))&&all(code20(:)==floor(code20(:)))&& ...
        all(code20(:)>=0&code20(:)<2^20), ...
        'BehaviorSpectrum:codes','Require actual integer code20 in [0,2^20).');
    code20=double(code20(:));
    N=numel(code20);
    result=struct('schema','sar20-behavior-spectrum/v1','status','not_run_short_capture', ...
        'record_length',N,'scope','Actual behavior-model reconstructed codes; not transistor/PDK/static-linearity evidence', ...
        'inl_dnl','not_measured');
    if N<256,return;end
    assert(N==2^round(log2(N)),'BehaviorSpectrum:length','N must be a power of two.');
    fs=p.fs_hz;
    fin=p.stimulus.frequency_hz;
    fsr=p.fsr_diff_v;
    assert(isscalar(fs)&&isfinite(fs)&&fs>0&&isscalar(fin)&&isfinite(fin)&& ...
        isscalar(fsr)&&isfinite(fsr)&&fsr>0,'BehaviorSpectrum:parameters','Invalid saved Fs/Fin/FSR.');
    bin=round(fin*N/fs);
    % Same coherence gate as existing native cicc_spectrum; no input retuning.
    assert(bin>0&&bin<N/2&&abs(fin*N/fs-bin)<1e-9, ...
        'BehaviorSpectrum:coherence','Actual input is not coherent with N/Fs.');
    % Code-centre reconstruction: an LSB is centred on its code value.
    v=((code20+0.5)/2^20-0.5)*fsr;
    dc=mean(v);
    transform=fft(v-dc)/N;
    power=abs(transform(1:N/2+1)).^2;
    % Double every non-DC, non-Nyquist bin to get single-sided power.
    power(2:end-1)=2*power(2:end-1);
    signal=power(bin+1);
    other=power;
    other([1 bin+1])=0;
    nd=sum(other);
    % Harmonics may alias above Nyquist, so fold them back before removing them
    % from the noise bin set. Without this fold H2..H10 would be double counted.
    harmonics=mod((2:10)*bin,N);
    harmonics=setdiff(unique(min(harmonics,N-harmonics)),[0 bin]);
    hp=sum(power(harmonics+1));
    noise=nd-hp;
    assert(signal>0&&nd>0&&noise>0,'BehaviorSpectrum:power','Degenerate signal/noise power.');
    result.status='actual_codes_characterized';
    result.sample_rate_hz=fs;result.input_frequency_hz=fin;
    result.full_scale_diff_v=fsr;result.stimulus=p.stimulus;
    result.fundamental_bin=bin;result.harmonic_bins=harmonics;
    result.snr_db=10*log10(signal/noise);result.sndr_db=10*log10(signal/nd);
    result.sfdr_db=10*log10(signal/max(other));result.thd_db=10*log10(hp/signal);
    result.enob=(result.sndr_db-1.76)/6.02;
    result.dc_voltage_v=dc;result.residual_rms_v=sqrt(nd);
    result.frequency_hz=(0:N/2).'*fs/N;result.power_v2=power;
    result.convention=['Coherent rectangular single-sided power through Nyquist, DC excluded; ' ...
        'SNR excludes H2..H10 only, THD includes H2..H10 only; ENOB has no full-scale amplitude correction.'];
end
