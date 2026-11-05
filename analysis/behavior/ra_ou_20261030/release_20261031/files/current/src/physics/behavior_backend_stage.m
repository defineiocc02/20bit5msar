function [stateNext,obs] = behavior_backend_stage(kind,state,eventTime,command,p,oldFrontend)
%BEHAVIOR_BACKEND_STAGE Pure backend Advance/Commit adapter, v1 2026-10-27.
% Caller: behavior_backend_sfun or direct event runner. No retained memory/RNG.
% Inputs: kind='advance'/'commit'; state48 per behavior_backend_pack; absolute
% eventTime [s]; command26=[Qres C; Ctop F; D2(12); TA(7); RAon; AZon; reset; sample_id; epoch].
% Output stateNext48 and obs8=[VX V; VY V; Vtop V; target V; NG 1; tau s;
% AZ input-differential V; CT reset-baseline VX V]. All voltage obs differential.
% Advance ignores NEW command and advances only the command in the incoming
% state. Commit requires eventTime==state.time_s and applies NEW command at dt0.
% Both blocks represent successive transforms of ONE state, not two memories.
% Candidate optional oldFrontend353 is read ONLY in finite-DAC active advance;
% off/all-zero tau retains the original backend_step call/operations.
    assert((ischar(kind)&&isrow(kind))||(isstring(kind)&&isscalar(kind)), ...
        'behavior:stageKind','Stage kind must be advance or commit.');
    kind=char(kind);
    assert(isnumeric(eventTime)&&isreal(eventTime)&&isscalar(eventTime)&&isfinite(eventTime), ...
        'behavior:stageTime','Event time must be finite scalar seconds.');
    s=behavior_backend_unpack(state);
    switch kind
        case 'advance'
            dt=double(eventTime)-s.time_s;
            assert(dt>=0,'behavior:stageTimeOrder','Advance time precedes retained state time.');
            finiteCoupling=isfield(p,'dac_coupling')&&p.dac_coupling.enabled&& ...
                any(p.dac_coupling.tau_dac_s>0);
            % The original caller and arithmetic remain exact for noise OFF.
            % ON receives the ORIGINAL eventTime word, never s.time_s+dt.
            noiseInterval=isfield(p,'ni')&&isstruct(p.ni)&& ...
                isfield(p.ni,'ra_noise')&&isscalar(p.ni.ra_noise)&& ...
                isreal(p.ni.ra_noise)&&isequal(double(p.ni.ra_noise),1)&& ...
                s.command.ra_on&&~s.command.reset&&dt>0;
            if finiteCoupling&&s.command.ra_on&&~s.command.reset
                assert(nargin==6,'behaviorDAC:oldFrontRequired','Finite coupling requires the actual OLD FE state input.');
                forcing=behavior_dac_forcing_from_frontend(oldFrontend,s,eventTime,p);
                % ON is rejected by the backend finite-DAC guard.
                [s,y]=behavior_backend_step(s,s.command,dt,p,forcing);
            else
                if noiseInterval
                    [s,y]=behavior_backend_step(s,s.command,dt,p,[],double(eventTime));
                else
                    [s,y]=behavior_backend_step(s,s.command,dt,p);
                end
            end
        case 'commit'
            assert(double(eventTime)==s.time_s,'behavior:stageCommitTime', ...
                'Commit requires the state already advanced to the exact event time.');
            c=unpack_command(command);
            [s,y]=behavior_backend_step(s,c,0,p);
        otherwise
            error('behavior:stageKind','Unknown backend stage %s.',kind);
    end
    % Align to the exact event-time word rather than trusting (t0+(t-t0))
    % to reproduce it for all positive/negative simulator start-time values.
    s.time_s=double(eventTime);
    stateNext=behavior_backend_pack(s);
    obs=[y.vx_v;y.vy_v;y.vtop_v;y.target_v;y.noise_gain;y.tau_ra_s; ...
        s.az_input_half_v(1)-s.az_input_half_v(2);s.ct_reset_vx_v];
    assert(isequal(size(obs),[8 1])&&all(isfinite(obs)), ...
        'behavior:stageObservation','Backend observation must contain eight finite doubles.');
end

function c=unpack_command(v)
    assert(isa(v,'double')&&isreal(v)&&isvector(v)&&numel(v)==26&&all(isfinite(v(:))), ...
        'behavior:stageCommand','Backend command must contain 26 finite doubles.');
    v=v(:);
    assert(all(ismember(v(3:21),[-1 0 1]))&&all(ismember(v(22:24),[0 1])), ...
        'behavior:stageCommandSigns','Invalid D2/TA signs or command booleans.');
    assert(v(25)>=-1&&v(25)==floor(v(25))&&v(26)>=0&&v(26)==floor(v(26)), ...
        'behavior:stageCommandTags','Require integer sample_id>=-1 and epoch>=0.');
    c=struct('qres_c',v(1),'ctop_f',v(2),'d2_signs',v(3:14), ...
        'ta_signs',v(15:21),'ra_on',logical(v(22)), ...
        'az_on',logical(v(23)),'reset',logical(v(24)), ...
        'sample_id',v(25),'epoch',v(26));
end
