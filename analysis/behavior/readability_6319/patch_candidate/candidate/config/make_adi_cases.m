function suite=make_adi_cases(P,N,sigma_unit,chip_seed)
%MAKE_ADI_CASES Same-chip DEM/dither 2x2 comparisons, v1 2026-10-27.
% Caller: root MATLAB experiment runner, then SAR20('apply',case.P).
% Defaults: N8, unit sigma0.1%, local chip seed20261028. Sigma is an explicit
% IID-unit design stress, not a paper/PDK/identified mismatch value.
% No SLX/file write, global RNG advance, output-code replacement or calibration.
    if nargin<2,N=8;end
    if nargin<3,sigma_unit=0.001;end
    if nargin<4,chip_seed=20261028;end
    assert(isscalar(N)&&isfinite(N)&&N>=1&&N==floor(N),'adiCases:N','N must be a positive integer.');
    assert(isscalar(sigma_unit)&&isreal(sigma_unit)&&isfinite(sigma_unit)&& ...
        sigma_unit>=0&&sigma_unit<0.1,'adiCases:sigma','Use unit relative sigma in [0,0.1).');
    assert(isscalar(chip_seed)&&isfinite(chip_seed)&&chip_seed>=0&& ...
        chip_seed<=2^32-1&&chip_seed==floor(chip_seed), ...
        'adiCases:seed','Local chip seed must be a uint32-valued integer.');
    assert(strcmp(P.digital.calibration_mode,'off'),'adiCases:calibration', ...
        'This uncalibrated comparison must not consume actual C as calibration truth.');
    assert(isscalar(P.front.dither_input_amplitude_v)&& ...
        isreal(P.front.dither_input_amplitude_v)&& ...
        isfinite(P.front.dither_input_amplitude_v)&&P.front.dither_input_amplitude_v>0, ...
        'adiCases:ditherAmplitude', ...
        'The dither-on cases require a strictly positive finite physical amplitude [V].');
    before=rng;
    P.N=double(N);
    derived={'groups','calendar','schedule','n_cycles','stop_time_s','xFE0','xBK0','xSC0'};
    for k=1:numel(derived)
        if isfield(P,derived{k}),P=rmfield(P,derived{k});end
    end
    % Extend only the same public calendar prefix when a larger record needs it.
    oldPlan=P.front.plan;
    required=max(32,N+P.first_id+4);
    if P.front.plan_rows<required
        f=P.front;if isfield(f,'group_C_f'),f=rmfield(f,'group_C_f');end
        f.plan_rows=required;f.plan=[];
        [~,P.front]=behavior_frontend_init(f);
        assert(isequal(P.front.plan(1:size(oldPlan,1),:),oldPlan), ...
            'adiCases:planPrefix','Longer experiment changed the original public plan prefix.');
    end
    weights=[16,32*ones(1,31),16,8,4,2,1,17];
    Cu=P.front.unit_cap_f;
    nominal=Cu*repmat(weights,18,1);
    % Sum of N independent Gaussian unit errors has relative sigma/sqrt(N).
    % One branch-normal draw gives exactly this aggregate distribution. DEM
    % swaps whole32-Cu groups; this does not create per-cell dynamic DEM modes.
    stream=RandStream('mt19937ar','Seed',double(chip_seed));
    z=randn(stream,18,38);
    branchSigma=sigma_unit./sqrt(weights);
    actual=nominal.*(1+z.*repmat(branchSigma,18,1));
    assert(all(isfinite(actual(:)))&&all(actual(:)>0), ...
        'adiCases:negativeC','Mismatch stress produced nonpositive C; do not clip or redraw it.');
    prototype=struct('name','','chip','','dem_enabled',false,'dither_enabled',false, ...
        'P',struct(),'physical_assumptions',struct());
    cases=repmat(prototype,8,1);at=0;
    for chip=1:2
        if chip==1,C=nominal;chipName='nominal';else,C=actual;chipName='unit_mismatch';end
        for dem=0:1
            for dither=0:1
                at=at+1;q=P;
                q.front.C_f=C;
                q.front.group_C_f=[sum(C(:,1:33),2),sum(C(:,34:37),2),C(:,38)];
                q.front.mismatch_enabled=(chip==2&&sigma_unit>0);
                q.front.dem_enabled=logical(dem);q.front.dither_enabled=logical(dither);
                q.digital.dither_enabled=logical(dither);
                q.digital.dither_seed=q.front.dither_seed;
                q.digital.dither_amplitude_v=q.front.dither_input_amplitude_v;
                if isfield(q,'ni'),q.ni.cap_mismatch=q.front.mismatch_enabled||q.backend.ni.cap_mismatch;end
                % Only public dither setup enters the nominal digital decoder.
                digital=q.digital;baseline=P.digital;
                publicFields={'dither_enabled','dither_seed','dither_amplitude_v'};
                digital=rmfield(digital,publicFields);baseline=rmfield(baseline,publicFields);
                assert(isequaln(digital,baseline),'adiCases:truthLeak', ...
                    'The nominal digital codebook changed outside public dither configuration.');
                Cs=sum(q.front.group_C_f,1);
                % Per-sample selected-slice kappa is reported from actual analog C for
                % auditing only. It is never written into digital parameters.
                plan=q.front.plan;
                kappa=zeros(P.first_id+N,1);
                signal=zeros(size(kappa));top=zeros(size(kappa));
                for id=0:numel(kappa)-1
                    ids=plan(id+1,:);
                    signal(id+1)=sum(q.front.group_C_f(ids,1));
                    top(id+1)=sum(q.front.group_C_f(ids,:),'all')+sum(q.front.Cp_f(ids));
                    kappa(id+1)=(1024/15)*sum(q.front.group_C_f(ids,2))/signal(id+1);
                end
                assumptions=struct('source','explicit_IID_unit_design_stress_not_PDK_or_paper', ...
                    'sigma_unit_fraction',double(sigma_unit)*(chip==2), ...
                    'chip_seed',double(chip_seed),'weights_Cu',weights, ...
                    'offset17Cu_also_IID',true,'independent_PN_mismatch',false, ...
                    'gradient_or_correlation',false,'sample_signal_total_f',signal, ...
                    'top_total_f',top,'analog_dither_kappa',kappa, ...
                    'all18_signal_tail_bias_C_f',Cs);
                cases(at)=struct('name',sprintf('%s_dem%d_dither%d',chipName,dem,dither), ...
                    'chip',chipName,'dem_enabled',logical(dem),'dither_enabled',logical(dither), ...
                    'P',q,'physical_assumptions',assumptions);
            end
        end
    end
    assert(isequaln(before,rng),'adiCases:globalRng','Case construction changed the global MATLAB RNG.');
    suite=struct('schema','behavior-ADI-cases/v1','cases',cases, ...
        'chip',struct('unit_cap_f',Cu,'unit_sigma_fraction',sigma_unit, ...
            'local_seed',chip_seed,'branch_weights',weights, ...
            'branch_relative_sigma',branchSigma,'C_nominal_f',nominal, ...
            'C_actual_f',actual,'generator','local_mt19937ar_Gaussian_branch_sums'), ...
        'global_rng_unchanged',true, ...
        'preserved','Input/timing/AZ/kTC/backend/Cf/nominal digital codebook/feature seeds', ...
        'scope','Actual charge-path feature comparisons; no prescribed codes, FFT or benefit claim.');
end
