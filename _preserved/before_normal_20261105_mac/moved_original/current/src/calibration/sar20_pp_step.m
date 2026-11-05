function [N,out]=sar20_pp_step(x,event2,time_s,raw6,ready,nominal,rxFault,en,cmd,ack,q)
%SAR20_PP_STEP M8 public RX A/B switch, pure Outputs prediction.
% One external UnitDelay is the only owner; this function has no DWork, Ref,
% held, actual C, stimulus or mutable closure. ON uses prequalified h slots;
% OFF copies old Fpga code exactly. E=(Event2,actual seconds,public RX Raw6,
% RX raw_ready,old nominal code,public RX fault,public EN,command5,drainAck7).
% cmd=[op,id,slot,version,arg]: 0 none,1 PUBLISH,2 RETIRE; ack is an
% independent consumer report [valid,oldslot,oldversion,newslot,newversion,
% epoch,activation_id], never inferred from a command or elapsed time alone.
% output meta9=[hit,time,id,epoch,input_valid,slot,version,fault,command_status].
% Any output on bank ON is valid only for qualified real RX valid1, never a
% fixture. valid0 advances the public ID/transition and produces valid0.
    assert(isa(x,'double')&&isreal(x)&&isequal(size(x),[64 1])&&x(1)==20261028&& ...
        isa(event2,'double')&&isreal(event2)&&numel(event2)==2&& ...
        isa(time_s,'double')&&isreal(time_s)&&isscalar(time_s)&&isfinite(time_s)&& ...
        isa(raw6,'double')&&isreal(raw6)&&numel(raw6)==6&& ...
        isa(ready,'double')&&isreal(ready)&&isscalar(ready)&& ...
        isa(nominal,'double')&&isreal(nominal)&&isscalar(nominal)&& ...
        isa(rxFault,'double')&&isreal(rxFault)&&isscalar(rxFault)&& ...
        isa(en,'double')&&isreal(en)&&isscalar(en)&& ...
        isa(cmd,'double')&&isreal(cmd)&&numel(cmd)==5&& ...
        isa(ack,'double')&&isreal(ack)&&numel(ack)==7&& ...
        isstruct(q)&&isscalar(q)&&isfield(q,'enabled'), ...
        'pp:portABI','Fixed scalar/double port ABI and owner state required.');
    N=x;out=struct('code20',nominal,'code_valid',false,'diagnostic_code20',NaN,'diagnostic_valid',false, ...
        'meta9',[NaN;time_s;NaN;NaN;NaN;0;0;0;0]);
    if ~q.enabled,return;end % exact legacy code bits, no state or validation change
    assert(isfield(q,'scope')&&any(strcmp(q.scope,{'SOURCE_CONTROLLED_BEHAVIOR_TEST_ONLY','FIXTURE_ONLY'})), ...
        'pp:scope','Only actual qualified context or an isolated fixture is permitted.');
    e=event2(:);r=raw6(:);cmd=cmd(:);ack=ack(:);
    assert(all(isfinite(e))&&all(e==floor(e))&&e(1)>=0&&e(2)>=1&&e(2)<=q.n_groups&& ...
        any(ready==[0 1])&&any(rxFault==[0 1]),'pp:eventABI','Public event/flags malformed.');
    hit=e(1)*q.n_groups+e(2)-1;assert(hit<=2^53-1,'pp:eventABI','Event ordinal exceeds exact double range.');
    sig=signature(ready,rxFault,en,time_s,r,nominal,cmd,ack);
    if x(12)~=0
        out=unpack_cached(x);out.code_valid=false;out.diagnostic_code20=NaN;out.diagnostic_valid=false;out.meta9(1:2)=[hit;time_s];
        out.meta9(8)=1;out.meta9(9)=-7;return;
    end
    if hit==x(11)
        if isequaln(sig,x(20:42)),out=unpack_cached(x);return;end
        [N,out]=fault(x,hit,time_s,4);N=remember(N,hit,sig,out);return;
    end
    if (x(11)<0&&hit~=0)||hit<x(11)||(x(11)>=0&&hit~=x(11)+1)
        [N,out]=fault(x,hit,time_s,5);N=remember(N,hit,sig,out);return;
    end
    out.code20=x(43);out.code_valid=false;
    out.meta9=[hit;time_s;NaN;NaN;NaN;x(2);q.versions(x(2));0;0];
    if rxFault~=0||en~=10,[N,out]=fault(x,hit,time_s,1);N=remember(N,hit,sig,out);return;end
    if ready==1
        if cmd(1)~=0,out.meta9(9)=4;end % RAW has priority over all commands
        tag=r(4:6);
        if any(~isfinite(tag))||any(tag~=floor(tag))||tag(1)<0||tag(1)>size(q.slot{1}.plan,1)-2|| ...
                tag(2)~=q.epoch||~any(tag(3)==[0 1])
            [N,out]=fault(x,hit,time_s,2);N=remember(N,hit,sig,out);return;
        end
        id=tag(1);valid=tag(3);
        if (~x(9)&&id~=q.first_ready_id)||(x(9)&&id~=x(10)+1)
            [N,out]=fault(x,hit,time_s,3);N=remember(N,hit,sig,out);return;
        end
        selected=x(2);
        if x(3)
            if id<x(6),selected=x(4);else,selected=x(5);N(2)=selected;N(7)=1;
                if valid==1&&x(8)<0,N(8)=id;end
            end
        end
        N(9)=1;N(10)=id;out.meta9(3:7)=[id;tag(2);valid;selected;q.versions(selected)];
        if valid==1
            if any(~isfinite(r(1:3)))||any(r(1:3)~=floor(r(1:3)))|| ...
                    any(r(1:3)<0)||any(r(1:3)>[2047;4095;255])|| ...
                    ~isfinite(nominal)||nominal~=floor(nominal)||nominal<0||nominal>=2^20
                [N,out]=fault(x,hit,time_s,2);N=remember(N,hit,sig,out);return;
            end
            try
                [code,~]=behavior_frozen_step(r,1,nominal,true,q.slot{selected});
            catch cause
                if any(strcmp(cause.identifier,{'frozenCal:finiteDot','frozenCal:finiteVoltage'}))
                    [N,out]=fault(x,hit,time_s,6);N=remember(N,hit,sig,out);return;
                end
                rethrow(cause);
            end
            out.diagnostic_code20=code;out.diagnostic_valid=true;
            if strcmp(q.scope,'SOURCE_CONTROLLED_BEHAVIOR_TEST_ONLY')
                out.code20=code;out.code_valid=true;N(43)=code;
            else
                out.code20=0;out.code_valid=false;N(43)=0;
            end
        end
        N=remember(N,hit,sig,out);return;
    end
    % Control applies only on an existing no-ready hit.
    if cmd(1)~=0
        [N,status,accepted]=command(x,cmd,ack,q);out.meta9(9)=status;
        if accepted,N(14)=cmd(2);N(15:19)=cmd;end
    end
    N=remember(N,hit,sig,out);
end
function [N,status,accepted]=command(x,c,ack,q)
    N=x;status=-1;accepted=false;
    if any(~isfinite(c))||any(c~=floor(c))||c(2)<1||c(2)>2^32-1|| ...
        ~any(c(1)==[1 2])||~any(c(3)==[1 2])||c(4)<1||c(4)>2^32-1,return;end
    if c(2)==x(14)
        if isequal(c,x(15:19)),status=3;else,status=-3;end;return;
    elseif c(2)<x(14),status=-2;return;end
    if c(1)==1
        if x(3)||~x(9)||c(3)==x(2)||q.versions(c(3))~=c(4),status=-4;return;end
        a=c(5);
        if a~=floor(a)||a<0||a>size(q.slot{1}.plan,1)-2||a<=x(10)+q.lead_samples,status=-5;return;end
        N(3)=1;N(4)=x(2);N(5)=c(3);N(6)=a;N(7)=0;N(8)=-1;
        status=1;accepted=true;return;
    end
    if ~x(3)||~x(7)||x(8)<0||c(3)~=x(4)||c(4)~=q.versions(x(4)),status=-4;return;end
    expected=[1;x(4);q.versions(x(4));x(5);q.versions(x(5));q.epoch;x(6)];
    if ~isequal(ack,expected),status=-6;return;end
    % A separate actual consumer acknowledgment is mandatory; no elapsed-time
    % rule or command-carried assertion can manufacture drain evidence.
    N(3:8)=[0;0;0;-1;0;-1];status=2;accepted=true;
end
function s=signature(ready,fault,en,time,r,nominal,cmd,ack)
    if ready==0||fault~=0||en~=10,r=zeros(6,1);nominal=0;
    elseif ~isfinite(r(6))||r(6)~=1,r(1:3)=0;nominal=0;end
    if cmd(1)==0,cmd=zeros(5,1);end
    if ready~=0||fault~=0||en~=10||cmd(1)~=2,ack=zeros(7,1);end
    if fault~=0||en~=10,cmd=zeros(5,1);end
    s=[ready;fault;en;time;r;nominal;cmd;ack];
end
function [N,out]=fault(x,hit,time,reason)
    N=x;N(12)=1;N(13)=reason;N(3:8)=[0;0;0;-1;0;-1];
    out=struct('code20',x(43),'code_valid',false,'diagnostic_code20',NaN,'diagnostic_valid',false, ...
        'meta9',[hit;time;NaN;NaN;NaN;0;0;1;-7]);
end
function N=remember(N,hit,sig,out)
    N(11)=hit;N(20:42)=sig;N(44:56)=[out.code20;double(out.code_valid);out.meta9;out.diagnostic_code20;double(out.diagnostic_valid)];N(57)=1;
end
function out=unpack_cached(x)
    if x(57),out=struct('code20',x(44),'code_valid',logical(x(45)),'meta9',x(46:54), ...
            'diagnostic_code20',x(55),'diagnostic_valid',logical(x(56)));
    else,out=struct('code20',x(43),'code_valid',false,'meta9',[NaN;NaN;NaN;NaN;NaN;0;0;1;-7], ...
            'diagnostic_code20',NaN,'diagnostic_valid',false);end
end
