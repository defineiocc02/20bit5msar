function [xnext,o]=behavior_transport_step(x,context2,chipRaw6,chipRawReady,en,cfg)
%BEHAVIOR_TRANSPORT_STEP Pure incremental compressed transport, external x97 UD.
% context2=[actual_t_s,kind], kind0 NOOP/1 CNV/2 actualRAW/3 CLOSE(+138ns).
% ChipRaw6 tags ONLY enter TX pending/cache. RX is called ONLY with public pins.
% o.raw6 retains negative startup target -2/-1 with valid0, never relabels ID0.
% o.ready3=[frame_ready;raw_ready;sample_ready]. Gate FPGA on raw_ready; startup
% negative tags must NOT enter its unconditional nominal/public-POL arithmetic.
% o.trace69x8=[t,CNV,CLK,EN,D+,D-,DCO+,DCO-], only first nRows meaningful;
% unused rows NaN. This is a compressed historical trace, not scalar pin timing.
% Outputs may recompute this function; ONLY caller's UnitDelay commits xnext.
    assert(isa(x,'double')&&isreal(x)&&isequal(size(x),[97 1])&&all(isfinite(x)), ...
        'transport97:state','Finite explicit double97 owner state required.');
    assert(isnumeric(context2)&&isreal(context2)&&numel(context2)==2&&all(isfinite(context2(:))), ...
        'transport97:context','Use actual time_s and explicit event kind.');
    t=context2(1);kind=context2(2);assert(any(kind==0:3),'transport97:kind','Unknown event kind.');
    xnext=x;o=struct('raw6',x(92:97),'ready3',zeros(3,1),'frame12',nan(12,1), ...
        'trace',nan(69,8),'nRows',0);
    assert(isscalar(en)&&isfinite(en)&&any(en==[10 4]), ...
        'transport97:EN','Only predeclared normal/test EN; run-time shutdown/reset needs a separate system-reset contract.');
    % Fixed x97 ABI: x4=TX.prev_en; x66=RX.prev_en. Read on EVERY event,
    % including NOOP: an unsupported EN pulse cannot disappear between stages.
    assert(en==x(4)&&en==x(66),'transport97:ENChange','Run-time EN mode changes are not implemented.');
    if kind==0,return;end % EN checked, no pack/unpack or protocol advance
    s=behavior_transport_unpack(x,cfg);
    if kind==1
        assert(~s.pending_valid,'transport97:pending','Unconsumed source at next CNV.');
        if s.tx.cnv_id<0
            assert(t==0,'transport97:firstCNV','First public CNV must match declared sample calendar t=0.');
        else
            assert(abs(t-s.tx.slot_time_s-200e-9)<=1e-15&&s.tx.prev_cnv==0&&s.tx.prev_clk==0&&~s.tx.tx_active, ...
                'transport97:cnvOrder','Expected next200ns CNV after completed close.');
        end
        [pin,s.tx]=sar20_lvds_tx_step(t,struct('cnv',1,'clk',0,'en',en,'record',[]),s.tx,cfg.tx);
        row=[t,1,0,en,pin.d_p,pin.d_n,pin.dco_p,pin.dco_n];
        [s.rx,s.held_raw6,o]=receive_row(s.rx,s.held_raw6,o,row,cfg.rx);o.trace(1,:)=row;o.nRows=1;
    elseif kind==2
        assert(isscalar(chipRawReady)&&any(chipRawReady==[0 1]),'transport97:rawReady','Actual chip RawReady must be binary.');
        if ~chipRawReady,return;end
        assert(~s.pending_valid&&s.tx.cnv_id>=0&&isfinite(s.tx.slot_time_s)&& ...
            t>=s.tx.slot_time_s&&t<s.tx.slot_time_s+138e-9, ...
            'transport97:sourceWindow','At most one actual source commit before close in this slot.');
        r=double(chipRaw6(:));lim=[2047;4095;255;2^32-1;2^32-1;1];
        assert(isnumeric(chipRaw6)&&isreal(chipRaw6)&&numel(r)==6&& ...
            all(isfinite(r))&&all(r==floor(r))&&all(r>=0)&&all(r<=lim), ...
            'transport97:source','Malformed actual chip RAW6.');
        s.pending_valid=true;s.pending_record=[t;r]; % ACTUAL event time, no id*Ts+86.25 fixture expression
    else
        assert(s.tx.cnv_id>=0&&isfinite(s.tx.slot_time_s)&& ...
            abs(t-s.tx.slot_time_s-138e-9)<=1e-15&&s.tx.tx_active, ...
            'transport97:closeOrder','Close must occur once at actual CNV+138ns.');
        base=s.tx.slot_time_s;edges=base+(8:2:138).'*1e-9;
        times=[edges;base+cfg.cnv_pulse_s];
        if s.pending_valid,times(end+1,1)=s.pending_record(1);end
        times=unique(times);assert(numel(times)<=69,'transport97:traceSize','Trace exceeds declared fixed bound.');
        levels=repmat([1;0],33,1);
        for k=1:numel(times)
            now=times(k);j=find(edges<=now,1,'last');clk=0;if ~isempty(j),clk=levels(j);end
            cnv=double(now<base+cfg.cnv_pulse_s);record=[];
            if s.pending_valid&&now>=s.pending_record(1)
                v=s.pending_record;record=struct('raw_D1',v(2),'raw_D2',v(3),'raw_DT',v(4), ...
                    'sample_id',v(5),'epoch',v(6),'valid',v(7),'commit_time_s',v(1));
            end
            prior=s.tx;
            [pin,s.tx]=sar20_lvds_tx_step(now,struct('cnv',cnv,'clk',clk,'en',en,'record',record),s.tx,cfg.tx);
            d=pin.debug;
            if s.pending_valid&&now==s.pending_record(1)
                assert(d.record_cached==1,'transport97:sourceRejected','Actual new commit rejected by unchanged TX core.');
            end
            if d.cache_overwrite
                [~,old]=min([prior.cache.commit_time_s]);entry=prior.cache(old);
                assert(entry.sample_id+2<prior.cnv_id,'transport97:unretiredOverwrite','Unretired source cache overwrite.');
            end
            assert(~d.slot_clock_error&&~d.resync_required,'transport97:txFault','TX clock/resync fault in declared compressed calendar.');
            row=[now,cnv,clk,en,pin.d_p,pin.d_n,pin.dco_p,pin.dco_n];
            [s.rx,s.held_raw6,o]=receive_row(s.rx,s.held_raw6,o,row,cfg.rx);o.trace(k,:)=row;
        end
        o.nRows=numel(times);s.pending_valid=false;s.pending_record=zeros(7,1);
    end
    xnext=behavior_transport_pack(s,cfg);o.raw6=s.held_raw6;
end
function [rx,held,o]=receive_row(rx,held,o,row,rx_cfg)
% This receiver call ONLY sees time and seven public pins; no TX payload/tag.
    p=struct('cnv',row(2),'clk',row(3),'en',row(4), ...
        'd_p',row(5),'d_n',row(6),'dco_p',row(7),'dco_n',row(8));
    [y,rx]=sar20_lvds_rx_step(row(1),p,rx,rx_cfg);
    if y.ready
        assert(o.ready3(1)==0,'transport97:multipleFrames','More than one receive event per parent event.');
        held=[y.d1;y.d2;y.dt;y.sample_id;y.epoch;y.adc_sample_valid];
        rawReady=y.sample_id>=0&&~y.is_test&&~y.resync_required;
        o.ready3=[1;double(rawReady);double(rawReady&&y.adc_sample_valid)];
        o.frame12=[row(1);y.frame_word;y.d1;y.d2;y.dt;y.sample_id;y.epoch; ...
            y.valid;y.adc_sample_valid;y.is_test;y.test_pattern_ok;y.resync_required];
    end
end
