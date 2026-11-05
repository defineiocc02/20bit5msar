function [xnext,obs,out] = behavior_frontend_stage(kind,x,context,p,input4)
%BEHAVIOR_FRONTEND_STAGE Pure named advance/commit adapter for one UnitDelay.
% Context6=[t_s,id,epoch,event,d1_code,vtop_v], all double.
% Optional input4=[offset V,amplitude V,frequency Hz,phase rad] changes source
% after advancing the old source to t; omitted input4 preserves runner behavior.
% advance: 0 observe, 1 CNV(capture/join; pool opens next here), 2 startup open, 3 reset.
% commit: 0 observe, 1 registered DAC command, 2 return/release (single opens next), 3 reset.
% Obs7=[coarse_input_v,vres_v,qres_c,cs_f,ctop_f,vtop_equiv_v,dither_input_v].
% All state resides in external x[353]; no scheduler/SAR/backend is embedded.
    kind=char(kind);
    assert(any(strcmp(kind,{'advance','commit'})),'behaviorFE:stageKind','Use advance or commit.');
    assert(isnumeric(context)&&isreal(context)&&numel(context)==6, ...
        'behaviorFE:contextWidth','Expected [time,id,epoch,event,D1,vtop].');
    c=double(context(:));
    assert(all(isfinite(c(1:4)))&&c(4)==floor(c(4))&&c(4)>=0&&c(4)<=3, ...
        'behaviorFE:contextEvent','Context time/tags/event must be finite; event integer 0..3.');
    s=behavior_frontend_unpack(x,p);
    cmd=struct('event','observe','t_s',c(1),'id',c(2),'epoch',c(3));
    % Always analytically advance the old phase before any topology/command event.
    [s,out]=behavior_frontend_step(s,cmd,p);
    % Optional external Driver is an actual analog source input. Integrate the
    % old source first, then change it at t before capture/topology/command.
    if nargin>=5
        assert(isnumeric(input4)&&isreal(input4)&&numel(input4)==4&&all(isfinite(input4(:))), ...
            'behaviorFE:driverWidth','Driver must be [offset V,amplitude V,frequency Hz,phase rad].');
        d=double(input4(:));
        assert(d(2)>=0&&d(3)>=0,'behaviorFE:driverRange','Driver amplitude/frequency cannot be negative.');
        u=struct('offset_v',d(1),'amplitude_v',d(2),'frequency_hz',d(3),'phase_rad',d(4));
        if ~isequaln(u,s.input)
            cmd.event='input_change';cmd.input=u;
            [s,out]=behavior_frontend_step(s,cmd,p);
            cmd=rmfield(cmd,'input');cmd.event='observe';
        end
    end
    if strcmp(kind,'advance')
        switch c(4)
            case 1
                cmd.event='capture';[s,~]=behavior_frontend_step(s,cmd,p);
                cmd.event='convert_join';[s,~]=behavior_frontend_step(s,cmd,p);
                if ~isfield(p,'single_bank')||~p.single_bank
                    cmd.event='acquire_open';cmd.id=c(2)+1;
                    [s,~]=behavior_frontend_step(s,cmd,p);
                end
                cmd.event='observe';cmd.id=c(2);[s,out]=behavior_frontend_step(s,cmd,p);
            case 2
                cmd.event='acquire_open';[s,out]=behavior_frontend_step(s,cmd,p);
            case 3
                cmd.event='reset';[s,out]=behavior_frontend_step(s,cmd,p);
        end
    else
        switch c(4)
            case 1
                cmd.event='dac_commit';cmd.d1_code=c(5);
                [s,out]=behavior_frontend_step(s,cmd,p);
            case 2
                cmd.event='release';cmd.vtop_v=c(6);
                [s,out]=behavior_frontend_step(s,cmd,p);
                if isfield(p,'single_bank')&&p.single_bank
                    % Same FE owner: release first, then reserve next acquisition.
                    cmd=rmfield(cmd,'vtop_v');cmd.event='acquire_open';cmd.id=c(2)+1;
                    [s,~]=behavior_frontend_step(s,cmd,p);
                end
            case 3
                cmd.event='reset';[s,out]=behavior_frontend_step(s,cmd,p);
        end
    end
    xnext=behavior_frontend_pack(s);
    obs=[out.coarse_input_v;out.vres_v;out.qres_c;out.cs_f;out.ctop_f; ...
        out.vtop_equiv_v;out.dither_input_v];
end
