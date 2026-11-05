function report=normal_validate_tap(out,P)
% Existing wire taps only. Actual stage-next wires are not committed-state probes.
    assert(P.debug.adi_enabled&&P.debug.aperture_enabled&&P.front.single_bank&& ...
        ~P.front.dem_enabled&&~P.front.dither_enabled&&~P.front.jitter.enabled, ...
        'sbN8:debug','Use single-bank with only existing read-only taps enabled.');
    assert(isfield(P.control,'comparator')&&P.control.comparator.enabled&& ...
        P.control.comparator.sar2_noise_rms_v>0,'normalTap:comparator','Expected active SAR2/TA comparator noise.');
    plain=sb_validate_plain(out,P);
    [te,e]=sb_series(out,'event_log',2);[tc,c]=sb_series(out,'control_log',13);
    [tb,back]=sb_series(out,'back_log',8);[tw,w]=sb_series(out,'adi_wire_log',58);
    [ta,ap]=sb_series(out,'aperture_log',28);
    assert(sb_same_bits(te,tc)&&sb_same_bits(te,tb)&&sb_same_bits(te,tw)&&sb_same_bits(te,ta), ...
        'sbN8:axis','Actual observer axes differ.');
    cycles=P.schedule.n_cycles;G=numel(P.groups);cnv=false(size(te));raw=false(size(te));
    releaseToken=P.calendar(strcmp({P.calendar.type},'release'));
    assert(isscalar(releaseToken),'sbN8:release','One release token required.');
    rel=releaseToken.time_s;
    for g=1:G
        types={P.groups(g).events.type};rows=e(:,2)==g;
        cnv(rows)=any(strcmp(types,'cnv'));raw(rows)=any(strcmp(types,'raw_latch'));
    end
    assert(nnz(cnv)==cycles&&nnz(raw)==cycles&&all(isnan(ap(~cnv,:)),'all'), ...
        'sbN8:aperturePhase','Unexpected aperture log phase.');
    ids=1:8;windows=zeros(cycles,4);zeroD2=0;zeroTA=0;signDiffD2=0;signDiffTA=0;
    cmpTrace=zeros(cycles*20,10);cmpCount=0;
    noisy=isfield(P.control,'comparator')&&P.control.comparator.enabled&& ...
        (P.control.comparator.sar2_noise_rms_v~=0||P.control.comparator.sar2_offset_v~=0);
    for id=0:cycles-1
        rows=find(e(:,1)==id);cr=rows(cnv(rows));rr=rows(raw(rows));
        assert(isscalar(cr)&&isscalar(rr),'sbN8:cycle','Missing/duplicate CNV or raw.');
        assert(all(w(rows,1:8)==repmat(ids,numel(rows),1),'all')&& ...
            all(w(rows,57)==id)&&all(w(rows,58)==P.epoch), ...
            'sbN8:segments','Actual stage-next IDs/tags differ from sole numerical group.');
        expectedOpen=(id-1)*P.Ts_s+rel+P.front.single_guard_s;
        assert(isequal(ap(cr,1:3),[id P.epoch 1])&&isequal(ap(cr,5:12),ids)&& ...
            sb_same_bits(ap(cr,4),te(cr))&&sb_same_bits(ap(cr,13:20),repmat(te(cr),1,8))&& ...
            sb_same_bits(ap(cr,21:28),repmat(expectedOpen,1,8)), ...
            'sbN8:aperture','Recorded acquisition/aperture metadata mismatch.');
        windows(id+1,:)=[id expectedOpen te(cr) te(cr)-expectedOpen];
        signs=zeros(1,19);counts=zeros(1,3);
        for j=1:numel(rows)
            row=rows(j);events=P.groups(e(row,2)).events;
            for k=1:numel(events)
                event=events(k);
                switch event.type
                    case 'd2_decide'
                        counts(1)=counts(1)+1;v=back(row,2);
                        observed=double(bitget(uint32(c(row,6)),event.bit+1));
                        if v==0,zeroD2=zeroD2+1;else
                            differs=observed~=double(v>0);signDiffD2=signDiffD2+double(differs);
                            if ~noisy,assert(~differs,'sbN8:d2Sign','D2 bit differs from VY sign with comparator noise/offset off.');end
                        end
                        [derived,checked]=predict_cmp(event,id,P.epoch,te(row),v,observed,P.control.comparator);
                        cmpCount=cmpCount+1;cmpTrace(cmpCount,:)=derived;
                        assert(checked,'normalTap:cmpD2','D2 RAW differs from keyed comparator re-evaluation.');
                    case 'd2_feedback'
                        assert(row>1,'sbN8:feedback','No previous observed control row.');
                        signs(event.index+1)=2*double(bitget(uint32(c(row-1,6)),12-event.index))-1;
                    case 'ta_compare'
                        counts(2)=counts(2)+1;v=back(row,2);
                        observed=double(bitget(uint32(c(row,7)),event.bit+1));
                        if v==0,zeroTA=zeroTA+1;else
                            differs=observed~=double(v>0);signDiffTA=signDiffTA+double(differs);
                            if ~noisy,assert(~differs,'sbN8:taSign','TA bit differs from VY sign with comparator noise/offset off.');end
                        end
                        [derived,checked]=predict_cmp(event,id,P.epoch,te(row),v,observed,P.control.comparator);
                        cmpCount=cmpCount+1;cmpTrace(cmpCount,:)=derived;
                        assert(checked,'normalTap:cmpTA','TA RAW differs from keyed comparator re-evaluation.');
                    case 'ta_feedback'
                        assert(row>1,'sbN8:feedback','No previous observed control row.');
                        signs(13+event.index)=2*double(bitget(uint32(c(row-1,7)),8-event.index))-1;
                        counts(3)=counts(3)+1;
                end
            end
            assert(isequal(w(row,33:51),signs)&&isequal(w(row,52:54),counts), ...
                'sbN8:wire','Observed RA command signs or next-controller counters differ.');
        end
        assert(isequal(w(rr,52:54),[12 8 7]),'sbN8:counts','Actual next-controller counts differ at RAW.');
    end
    assert(cmpCount==cycles*20,'normalTap:cmpCount','Missing comparator events.');
    plain.actual_feedback_counts='UNOBSERVED_BY_PLAIN_VALIDATOR';
    report=struct('status','tap_wire_checks_pass','plain',plain, ...
        'recorded_open_aperture_windows_s',windows,'actual_stage_next_counts_per_cycle',[12 8 7], ...
        'zero_VY_D2_unadjudicated',zeroD2,'zero_VY_TA_unadjudicated',zeroTA, ...
        'raw_vs_vy_sign_diff_D2',signDiffD2,'raw_vs_vy_sign_diff_TA',signDiffTA, ...
        'derived_comparator_trace',cmpTrace, ...
        'derived_comparator_columns',{{'sample_id','time_s','event_code','event_index','actual_VY_v','derived_noise_v','derived_effective_v','derived_bit','observed_RAW_bit','perturbation_applied'}}, ...
        'sign_scope','Noise/offset can change decisions; input noise and comparator state are not directly probed.', ...
        'segment_ids','OBSERVED_SAMPLE_STAGE_NEXT_NUMERICAL_SEGMENTS_1_TO_8', ...
        'phase_and_counts_scope','Observed stage-next/control and command wires; not independent committed-state history.', ...
        'opening_scope','Stored opening-time metadata; no sampled switch waveform at the opening instant.', ...
        'release_charge','UNOBSERVED_NO_DIRECT_FE_STATE_PROBE', ...
        'adi_scope','adi_enabled activates read-only existing tap only; pool/DEM/dither remain OFF.');
end

function [row,checked]=predict_cmp(event,id,epoch,time,vy,observed,cfg)
% Re-evaluate the public stateless key from logged VY and calendar metadata.
% Noise/effective voltage are derived, not a direct comparator probe.
    event.sample_id=id;event.epoch=epoch;
    c=struct('vy_v',double(vy),'decision2',double(vy>0));
    [~,d]=behavior_comparator_sample(event,c,cfg);
    checked=(d.applied||vy~=0)&&double(d.decision)==double(observed);
    row=[id,time,d.event_code,event.index,vy,d.noise_v,d.effective_v,d.decision,observed,double(d.applied)];
end
