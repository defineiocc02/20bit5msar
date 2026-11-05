function status=behavior_spectrum_eligibility(N,fs,fin,amplitude)
%BEHAVIOR_SPECTRUM_ELIGIBILITY Decide whether the existing coherent FFT applies.
% Pure preflight on saved sampling/input settings; never retunes the stimulus.
% Harmonic collisions remain eligible and are reported by behavior_spectrum.
    assert(isnumeric(N)&&isreal(N)&&isscalar(N)&&isfinite(N)&&N>=1&&N==floor(N), ...
        'spectrumEligibility:length','Record length must be a positive integer.');
    if N<256,status='not_run_short_capture';return;end
    if N~=2^round(log2(N)),status='not_run_non_power_of_two';return;end
    if ~(isnumeric(fs)&&isreal(fs)&&isscalar(fs)&&isfinite(fs)&&fs>0&& ...
            isnumeric(fin)&&isreal(fin)&&isscalar(fin)&&isfinite(fin)&& ...
            isnumeric(amplitude)&&isreal(amplitude)&&isscalar(amplitude)&&isfinite(amplitude)&&amplitude>=0)
        status='not_run_invalid_input';return;
    end
    if amplitude==0,status='not_run_zero_input_amplitude';return;end
    if fin<=0||fin>=fs/2,status='not_run_frequency_out_of_band';return;end
    exactBin=fin*N/fs;bin=round(exactBin);
    if bin<=0||bin>=N/2,status='not_run_frequency_out_of_band';return;end
    if abs(exactBin-bin)>=1e-9,status='not_run_noncoherent';return;end
    status='eligible';
end
