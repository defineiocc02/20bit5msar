function report=validate_behavior_adi_case(out,P,baseline)
%VALIDATE_BEHAVIOR_ADI_CASE v1, candidate actual-SLX posterior checks.
% Inputs completed SimulationOutput out, its saved P, completed baseline out.
% Baseline supplies ACTUAL event/time axes; analog/code equality is descriptive
% across ADI cases, never a pass criterion. No sim/build/config/RNG mutation.
% Existing logs do not observe DEM shift/selected physical slices/Btail or
% backend D2/TA signs. Optional adi_wire_log58 supplies these actual wires.
    assert(isa(out,'Simulink.SimulationOutput')&&isempty(out.ErrorMessage)&& ...
        isa(baseline,'Simulink.SimulationOutput')&&isempty(baseline.ErrorMessage), ...
        'adi:actualOutput','Require completed actual and baseline SimulationOutputs.');
    before=rng;
    names={'raw_log','ready_log','code_log','front_log','back_log','control_log', ...
        'event_log','d1_log','d2_log','dt_log','az_route_log','az_commit_log'};
    widths=[6 1 1 7 8 13 2 1 1 1 6 8];D=struct;B=struct;axes=struct;baselineEqual=struct;
    for k=1:numel(names)
        name=names{k};[t,x]=series(out.get(name),widths(k),name);
        [bt,bx]=series(baseline.get(name),widths(k),['baseline ' name]);
        D.(name)=x;B.(name)=bx;axes.(name)=t;
        baselineEqual.(name)=bits(x,bx)&&bits(t,bt);
    end
    t=axes.event_log;e=D.event_log;c=D.control_log;r=D.raw_log;
    G=numel(P.groups);cycles=P.schedule.n_cycles;
    checks=struct;checks.groups48=G==48;
    checks.actual_inventory=isequal(e,[repelem((0:cycles-1).',G) repmat((1:G).',cycles,1)]);
    checks.baseline_event_identity=bits(e,B.event_log);
    checks.baseline_actual_time=bits(t,series_time(baseline.get('event_log')));
    checks.logger_axes=true;
    for k=1:numel(names),checks.logger_axes=checks.logger_axes&&bits(t,axes.(names{k}));end
    assert(checks.actual_inventory,'adi:eventInventory','Actual cycle/group inventory differs; stop before indexed validation.');
    expected=zeros(size(t));tokenCounts=zeros(G,5);isRelease=false(size(t));isCnv=false(size(t));
    types={'d2_decide','d2_feedback','ta_compare','ta_feedback','raw_latch'};
    for g=1:G
        tokens={P.groups(g).events.type};
        for j=1:5,tokenCounts(g,j)=sum(strcmp(tokens,types{j}));end
        rr=e(:,2)==g;expected(rr)=e(rr,1)*P.Ts_s+P.groups(g).time_s;
        isRelease(rr)=any(strcmp(tokens,'release'));isCnv(rr)=any(strcmp(tokens,'cnv'));
    end
    checks.saved_calendar_time=bits(t,expected);
    checks.scheduled_12D2_8TA7=isequal(sum(tokenCounts,1),[12 12 8 7 1]);
    checks.raw_ready_iff_latch=isequal(D.ready_log,repmat(tokenCounts(:,5),cycles,1));
    checks.control_tags=isequal(c(:,9:10),[e(:,1) repmat(P.epoch,size(e,1),1)]);
    rows=find(D.ready_log==1);rr=r(rows,:);ids=e(rows,1);
    checks.raw_tags=isequal(rr(:,4:5),[ids repmat(P.epoch,numel(ids),1)]);
    checks.raw_valid=all(rr(:,6)==1)&&all(c(rows,8)==1);
    checks.raw_control_words=isequal(rr(:,1:3),c(rows,5:7));
    checks.dither_public_join=P.front.dither_enabled==P.digital.dither_enabled;
    if P.front.dither_enabled
        checks.dither_public_join=checks.dither_public_join&& ...
            P.front.dither_seed==P.digital.dither_seed&& ...
            P.front.dither_input_amplitude_v==P.digital.dither_amplitude_v&& ...
            P.digital.dither_amplitude_v>0;
    end
    checks.raw_ranges=all(isfinite(rr(:)))&&all(rr(:)==floor(rr(:)))&& ...
        all(rr(:,1)>=0&rr(:,1)<2048)&&all(rr(:,2)>=0&rr(:,2)<4096)&&all(rr(:,3)>=0&rr(:,3)<256);
    selected=rows(ids>=P.first_id&ids<P.first_id+P.N);
    checks.record_ids=isequal(r(selected,4),(P.first_id:P.first_id+P.N-1).');
    decoded=zeros(numel(rows),4);publicDither=zeros(numel(rows),1);
    for j=1:numel(rows)
        q=r(rows(j),:);raw=struct('raw_D1',q(1),'raw_D2',q(2),'raw_DT',q(3), ...
            'sample_id',q(4),'epoch',q(5),'valid',q(6));
        z=behavior_decode(raw,P.digital);
        decoded(j,:)=[z.code20 z.d1_v z.d2_v z.dt_v];publicDither(j)=z.dither_v;
    end
    logged=[D.code_log(rows,:) D.d1_log(rows,:) D.d2_log(rows,:) D.dt_log(rows,:)];
    checks.public_raw_decode=bits(decoded,logged);
    route=D.az_route_log;pol=route(:,1);expectedPol=zeros(size(pol));
    for j=1:numel(pol),expectedPol(j)=behavior_public_pol(e(j,1),P.epoch,P.digital.az_mode);end
    checks.actual_pol_public_identity=bits(pol,expectedPol);
    qexpected=route(:,2);qexpected(pol<0)=-qexpected(pol<0);
    checks.full_qres_pol=bits(route(:,3),qexpected);
    expectedRa=c(:,2);expectedRa(isRelease)=1; % RaCommand is before release/decide.
    checks.routed_ra_flag=isequal(route(:,4),expectedRa);
    checks.az_ra_disjoint=~any(route(:,4)~=0&route(:,5)~=0);
    returned=D.back_log(:,3);returned(pol<0)=-returned(pol<0);
    checks.return_context_coordinates=bits(route(isRelease,6),returned(isRelease));
    % A group contains each decide and any preceding due feedback in fixed order.
    % Public word changes prove digital registration only, NOT physical signs.
    checks.d2_word_change_only_decide=word_events(c(:,6),e,P,{'cnv','d2_decide'});
    checks.dt_word_change_only_compare=word_events(c(:,7),e,P,{'cnv','ta_compare'});
    coverage=struct('event_schedule','actual event/time log plus saved group token inventory', ...
        'raw_decode','actual RAW and FPGA component/code wires; public decoder recomputation', ...
        'qres','actual pre/post full Qres and actual POL wire', ...
        'return','actual ReturnContext Vtop at release, compared with pre-reset backend observation', ...
        'selected_slices','not_observed','dem_physical_shift','not_observed', ...
        'physical_dither_charge','not_observed','physical_12D2_7TA_updates','not_observed', ...
        'q_initial_retention','not_observed_by_this_tap','actual_B_commit','not_observed_by_this_tap', ...
        'release_charge_commit','not_observed_by_this_tap', ...
        'limits','Schedule tokens are saved P metadata; they alone do not prove internal event execution or physical feedback. ReturnContext proves coordinate routing, not every retained FE bottom-charge commit.');
    tap=struct('present',false);
    hasTap=ismember('adi_wire_log',out.who);
    checks.observer_logger_present=hasTap;
    if isfield(P,'debug')&&P.debug.adi_enabled
        assert(hasTap,'adi:tapMissing','Enabled physical observation has no actual logger.');
    end
    if hasTap&&isfield(P,'debug')&&~P.debug.adi_enabled
        [disabledTime,disabledData]=series(out.get('adi_wire_log'),58,'disabled adi_wire_log');
        checks.disabled_tap_not_collecting=numel(disabledTime)<=1&&all(isnan(disabledData(:)));
        tap=struct('present',false,'disabled',true,'retained_rows',numel(disabledTime));
    end
    if hasTap&&isfield(P,'debug')&&P.debug.adi_enabled
        [tt,w]=series(out.get('adi_wire_log'),58,'adi_wire_log');
        assert(bits(tt,t),'adi:tapAxis','Actual tap axis differs.');
        [tap,tapChecks]=validate_tap(w,e,c,P,tokenCounts);
        f=fieldnames(tapChecks);for j=1:numel(f),checks.(f{j})=tapChecks.(f{j});end
        coverage.selected_slices='actual phase==2 IDs, compared with public plan';
        coverage.dem_physical_shift='actual retained DEM shift and DAC signal target charge';
        coverage.physical_dither_charge='actual captured tail B per selected slice at CNV';
        coverage.physical_12D2_7TA_updates='actual command signs and controller counters at event boundaries';
    end
    report=struct('schema','sar20-adi-actual-posterior/v1','checks',checks, ...
        'all_observed_checks_pass',all(structfun(@(x)logical(x),checks)), ...
        'coverage',coverage,'tap',tap,'baseline_bit_equal',baselineEqual, ...
        'actual_selected_rows',selected,'decoded_at_raw',decoded,'public_dither_v',publicDither, ...
        'validator_global_rng_unchanged',isequaln(before,rng),'tolerance_used',[], ...
        'status','observed_checks_fail');
    if report.all_observed_checks_pass,report.status='observed_checks_pass_missing_wire_coverage';end
    if report.all_observed_checks_pass&&tap.present,report.status='observed_checks_and_actual_tap_pass';end
    if isfield(P,'debug'),report.debug=P.debug;else,report.debug=struct('adi_enabled',false);end
end
function [tap,q]=validate_tap(w,e,c,P,tc)
% Tap58 schema documented in behavior_adi_tap_sfun; all entries actual wires.
    q=struct('tap_selected_ids',true,'tap_dem_shift',true,'tap_dac_signal_target',true, ...
        'tap_capture_tail_charge',true,'tap_counts_12D2_8TA7',true,'tap_feedback_commands',true,'tap_phase_validity',true,'tap_actual_command_tags',true);
    N=size(e,1);actualDacRows=0;captureRows=0;signs=zeros(1,19);counts=zeros(1,3);
    for row=1:N
        id=e(row,1);g=P.groups(e(row,2));types={g.events.type};ids=w(row,1:8).';
        q.tap_selected_ids=q.tap_selected_ids&&isequal(ids,sort(P.front.plan(id+1,:).'));
        assert(all(ids>=1&ids<=18&ids==floor(ids)),'adi:tapIDs','Invalid actual selected IDs.');
        for tokenIndex=1:numel(g.events)
            token=g.events(tokenIndex);
            switch token.type
                case 'cnv',signs(:)=0;counts(:)=0;
                case 'd2_feedback'
                    signs(token.index+1)=2*double(bitget(uint32(c(row-1,6)),12-token.index))-1;
                case 'ta_feedback'
                    signs(13+token.index)=2*double(bitget(uint32(c(row-1,7)),8-token.index))-1;
                    counts(3)=counts(3)+1;
            end
        end
        q.tap_feedback_commands=q.tap_feedback_commands&&isequal(w(row,33:51),signs);
        counts(1)=counts(1)+tc(e(row,2),1);counts(2)=counts(2)+tc(e(row,2),3);
        q.tap_counts_12D2_8TA7=q.tap_counts_12D2_8TA7&&isequal(w(row,52:54),counts);
        q.tap_actual_command_tags=q.tap_actual_command_tags&&isequal(w(row,57:58),[id P.epoch]);
        % Test retained command after actual fine DAC prepare/feedback endpoints.
        if any(ismember(types,{'coarse_latch','fine_prepare','fine_feedback'}))
            actualDacRows=actualDacRows+1;
            shift=zeros(8,1);if P.front.dem_enabled,shift=mod(17*id+7*P.epoch+11*(ids-1)+P.front.dem_seed,31);end
            q.tap_dem_shift=q.tap_dem_shift&&isequal(w(row,9:16).',shift);
            assert(w(row,56)==1,'adi:tapActualDAC','DAC endpoint lacks actual physical command-valid flag.');
            trial=w(row,55);
            assert(isfinite(trial)&&trial>=0&&trial<=2047&&trial==floor(trial),'adi:tapD1','Invalid actual physical D1 command.');
            coarse=floor(trial/32);fine=mod(trial,32);
            bank=floor(coarse/32);therm=mod(coarse,32);levels=zeros(1,31);
            if bank==0,levels(1:31-therm)=-1;else,levels(1:therm)=1;end
            fineSigns=2*double(bitget(uint32(fine),5:-1:1))-1;target=zeros(8,1);
            for slice=1:8
                map=mod((0:30)+w(row,8+slice),31)+1;physical=zeros(1,31);physical(map)=levels;
                command=[2*bank-1 physical fineSigns 0];
                target(slice)=P.front.vref_v*sum(P.front.C_f(ids(slice),1:33).*command(1:33));
            end
            q.tap_dac_signal_target=q.tap_dac_signal_target&&bits(w(row,17:24).',target);
        end
        if ~any(strcmp(types,'cnv')),q.tap_phase_validity=q.tap_phase_validity&&all(isnan(w(row,25:32)));end
        if any(strcmp(types,'cnv'))
            q.tap_phase_validity=q.tap_phase_validity&&all(isnan(w(row,9:24)))&&w(row,56)==0;
            captureRows=captureRows+1;dn=behavior_public_dither(id,P.digital);
            expected=-P.front.group_C_f(ids,2)*(dn*(1024/15));
            % Valid only for settled precharge; no tolerance/silent finite-tau oracle.
            assert(all(P.front.tau_precharge_s(ids)==0),'adi:finitePrecharge','Physical tail exact gate requires settled precharge.');
            q.tap_capture_tail_charge=q.tap_capture_tail_charge&&bits(w(row,25:32).',expected);
        end
        if tc(e(row,2),5)==1,q.tap_counts_12D2_8TA7=q.tap_counts_12D2_8TA7&&isequal(w(row,52:54),[12 8 7]);end
    end

    tap=struct('present',true,'schema','adi-wire58/v1','dac_rows',actualDacRows, ...
        'capture_rows',captureRows,'untested_columns',[], ...
        'limits','Observed backend command signs do not separately prove each internal analog impulse; retained target charges do not expose every physical capacitor mask bit.');
end
function ok=word_events(word,e,P,allowed)
    ok=true;for row=2:numel(word)
        if word(row)~=word(row-1),ok=ok&&any(ismember({P.groups(e(row,2)).events.type},allowed));end
    end
end
function [t,x]=series(s,width,name)
    assert(isa(s,'timeseries')&&isnumeric(s.Data)&&isreal(s.Data),'adi:logger','Need actual timeseries %s.',name);
    t=s.Time(:);x=squeeze(s.Data);
    if width==1,x=x(:);elseif size(x,1)~=numel(t),x=x.';end
    assert(isequal(size(x),[numel(t) width])&&all(isfinite(t))&&all(diff(t)>0), ...
        'adi:loggerShape','Unexpected actual shape/time axis %s.',name);
end
function t=series_time(s),t=s.Time(:);end
function same=bits(a,b)
    same=isequal(size(a),size(b))&&strcmp(class(a),class(b));
    if ~same,return;end
    same=isequal(typecast(a(:),'uint64'),typecast(b(:),'uint64'));
end
