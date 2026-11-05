function out=behavior_decode(raw,p)
%BEHAVIOR_DECODE Reconstruct nominal input voltage from public RAW fields only.
%Version: v1 (2026-10-27). Caller: behavior post-receive decode path.
%Inputs raw scalar: D1 11-bit/D2 12-bit/DT 8-bit unsigned integer words,
%sample_id/epoch integers and valid; p from behavior_decode_parameters.
%Outputs code20 unsigned 20-bit count, voltage/component terms [V] and public tags.
%Stateless; no reset/RNG/actual C/held/residual/truth input and no training update.
%Model: nominal DAC1 geometry; d1_bias_v is zero for single or legacy -17Cu;
%RA-referred D2/DT divide by nominal gain, finite-sinc2 DT uses weights 8..1 /8.
%Digitally ADD public dither once, because sampled tail subtracts it physically.
%d2_ra_v/dt_ra_v are raw RA-domain terms; d2_v/dt_v are public-POL demodulated.
%Validity is propagated; invalid records still have a computed, non-accepted code.
%
% DECODE CHAIN
%   D1 -> c (6-bit unary count) + f (5-bit fine) -> d1Dac, plus d1Bias
%   D2 -> twelve RA-referred weights -> d2RA, divided by ra_gain -> d2V
%   DT -> eight sign bits weighted 8..1, divided by 8 -> dtWeighted -> dtV
%   AZ -> public polarity flips only d2V/dtV, never DAC1 or dither
%   voltage = d1V + d2V + dtV + dither   (dither added once, digitally)
%
% NOTE ON THE /8: the plain average would divide by sum(weights)=36. This chain
% divides by 8 because decision eight has no physical update while its raw LSB
% still carries digital weight one. That is deliberate, not a normalisation bug.
    fields={'raw_D1';'raw_D2';'raw_DT';'sample_id';'epoch';'valid'};
    assert(isstruct(raw)&&isscalar(raw)&&isequal(sort(fieldnames(raw)),sort(fields)), ...
        'behaviorDecode:publicInputs','RAW input must contain exactly D1/D2/DT/sample_id/epoch/valid.');
    limits=[2047 4095 255 2^32-1 2^32-1 1];
    for k=1:numel(fields)
        x=raw.(fields{k});assert((isnumeric(x)||islogical(x))&&isreal(x)&& ...
            isscalar(x)&&isfinite(x)&&x>=0&&x<=limits(k)&&x==floor(x), ...
            'behaviorDecode:rawRange','Invalid public field %s.',fields{k});
    end
    validate_parameters(p);
    % D1 splits into a 6-bit unary count c and a 5-bit fine decision f.
    c=floor(double(raw.raw_D1)/32);
    f=mod(double(raw.raw_D1),32);
    d2=double(bitget(uint32(raw.raw_D2),12:-1:1)).';
    dt=double(bitget(uint32(raw.raw_DT),8:-1:1)).';
    dtSigns=2*dt-1;
    % Same finite two-integrator sum as native_decode dt_weights and
    % sar20_fpga_step finite_sinc2; chronological MSB gets weight eight.
    % Decision eight has NO physical update, but its raw LSB still has digital
    % weight one. This is /8, never normalization by sum(weights)=36.
    weights=(8:-1:1).';
    statistic=sum(weights.*dtSigns);
    dtWeighted=statistic/8;
    d1Dac=(32*c+2*f-1039)*p.vref_v/1024;
    % Separate capture-bias term, kept additive so it stays inspectable.
    d1Bias=-17*p.vref_v/1024; % legacy P without the explicit field
    if isfield(p,'d1_bias_v')
        assert(isnumeric(p.d1_bias_v)&&isreal(p.d1_bias_v)&&isscalar(p.d1_bias_v)&& ...
            isfinite(p.d1_bias_v),'behaviorDecode:d1Bias','d1_bias_v must be a finite V scalar.');
        d1Bias=double(p.d1_bias_v);
    end
    d1V=d1Dac+d1Bias;
    d2RA=p.d2_offset_ra_v+sum(p.d2_weights_ra_v(:).*d2);
    dtRA=p.tracking_step_ra_v*dtWeighted;
    % RA-referred terms divided by the nominal gain to reach the input domain.
    d2V=d2RA/p.ra_gain;
    dtV=dtRA/p.ra_gain;
    mode='off';if isfield(p,'az_mode'),mode=p.az_mode;end
    [pol,pair]=behavior_public_pol(double(raw.sample_id),double(raw.epoch),mode);
    % Keep the old off/+1 arithmetic path exactly; no extra multiply or sum.
    % Flip only already input-referred CT terms, never DAC1 or dither.
    if pol<0
        d2V=-d2V;
        dtV=-dtV;
    end
    dith=behavior_public_dither(double(raw.sample_id),p);
    voltage=((d1V+d2V)+dtV)+dith;
    unsat=voltage*(2^20/p.fsr_diff_v)+2^19;
    rounded=round(unsat);
    code=max(0,min(2^20-1,rounded));
    out=struct('schema','sar20-behavior-decode-output/v1', ...
        'sample_id',double(raw.sample_id),'epoch',double(raw.epoch), ...
        'valid',logical(raw.valid),'code20',code,'voltage_v',voltage, ...
        'public_pol',pol,'pair_id',pair,'az_mode',char(mode), ...
        'd1_v',d1V,'d2_v',d2V,'dt_v',dtV,'dither_v',dith, ...
        'd1_dac_v',d1Dac,'d1_capture_bias_v',d1Bias, ...
        'd2_ra_v',d2RA,'dt_ra_v',dtRA,'dt_statistic',statistic, ...
        'dt_weighted',dtWeighted,'dt_weights',weights,'dt_signs',dtSigns, ...
        'unsat_code',unsat,'rounded_code',rounded,'clip',rounded~=code, ...
        'calibration_mode','off','rounding','nearest_away_from_zero', ...
        'invalid_semantics','code is diagnostic only when valid=false');
end

function validate_parameters(p)
    required={'schema','vref_v','fsr_diff_v','ra_gain','d2_weights_ra_v', ...
        'd2_offset_ra_v','tracking_step_ra_v','dither_enabled','dither_seed', ...
        'dither_amplitude_v','calibration_mode','tracking_mode'};
    assert(isstruct(p)&&isscalar(p)&&all(isfield(p,required))&& ...
        strcmp(p.schema,'sar20-behavior-decode/v1'), ...
        'behaviorDecode:parameters','Use explicit nominal decoder parameters.');
    assert(strcmp(p.calibration_mode,'off'),'behaviorDecode:calibration', ...
        'Calibration/training/frozen coefficients are not implemented.');
    for key={'vref_v','fsr_diff_v','tracking_step_ra_v'}
        x=p.(key{1});assert(isnumeric(x)&&isreal(x)&&isscalar(x)&&isfinite(x)&&x>0, ...
            'behaviorDecode:scale','%s must be finite positive SI value.',key{1});
    end
    assert(isscalar(p.ra_gain)&&p.ra_gain==32,'behaviorDecode:gain','This profile uses nominal RA gain32.');
    assert(isnumeric(p.d2_weights_ra_v)&&isreal(p.d2_weights_ra_v)&& ...
        numel(p.d2_weights_ra_v)==12&&all(isfinite(p.d2_weights_ra_v(:)))&& ...
        all(p.d2_weights_ra_v(:)>0)&&isscalar(p.d2_offset_ra_v)&&isfinite(p.d2_offset_ra_v), ...
        'behaviorDecode:D2','Require twelve positive nominal RA-referred bit weights and offset.');
    assert(strcmp(p.tracking_mode,'finite_sinc2'),'behaviorDecode:tracking', ...
        'Only explicit finite_sinc2 [8..1]/8 profile implemented.');
    assert((islogical(p.dither_enabled)||isnumeric(p.dither_enabled))&& ...
        isscalar(p.dither_enabled)&&ismember(p.dither_enabled,[0 1])&& ...
        isscalar(p.dither_seed)&&isfinite(p.dither_seed)&&p.dither_seed>=0&& ...
        p.dither_seed<=2^32-1&&p.dither_seed==floor(p.dither_seed)&& ...
        isscalar(p.dither_amplitude_v)&&isfinite(p.dither_amplitude_v)&&p.dither_amplitude_v>=0, ...
        'behaviorDecode:dither','Require explicit public dither enable/uint32 seed/amplitude V.');
end

