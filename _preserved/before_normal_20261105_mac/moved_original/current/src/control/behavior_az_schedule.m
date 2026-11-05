function a = behavior_az_schedule(id,epoch,phase,P)
%BEHAVIOR_AZ_SCHEDULE v1 (2026-10-27): pure event-level AZ/chop routing.
% Inputs: id zero-based sample ID, epoch integer tag; phase struct with
% offset_s [s] relative to CNV, ra_on [0/1], optional release [0/1].
% P.backend.az.mode: off/ordinary/chop/hold/hold_chop. Legacy missing mode is
% accepted only when P.backend.ni.az is false. No RNG, state, or event creation.
% WRITE WINDOW
% Current engineering candidate is [0, RA-start=31.25 ns) and requires RA off.
% This is a behavioral phase allocation, NOT a measured circuit write time.
% write_end_s may be declared explicitly, or read from the existing RA event.
%
% HOLD MODES
% Write even IDs and retain the paired odd frame; pair_id = floor(id/2).
%
% CHOPPING
% POL cycles [+1,-1,-1,+1] by ID. The returned polarity multiplies the complete
% physical Qres. CT D2/TA signs are NOT touched: they stay in the backend
% comparator's negative-feedback coordinate. Return Vtop uses POL.
%
% WHAT THIS FUNCTION DOES NOT DO
% No RNG, no state, no event creation. It only decides, for a given sample and
% phase offset, whether AZ is on, what polarity applies, and which window was
% used. Any overlap between an active AZ window and RA is a hard error.
    assert(isnumeric(id)&&isreal(id)&&isscalar(id)&&isfinite(id)&&id>=0&&id==floor(id), ...
        'behavior:azRoute:id','Sample ID must be a nonnegative integer.');
    assert(isnumeric(epoch)&&isreal(epoch)&&isscalar(epoch)&&isfinite(epoch)&&epoch>=0&&epoch==floor(epoch), ...
        'behavior:azRoute:epoch','Epoch must be a nonnegative integer tag.');
    assert(isstruct(phase)&&isscalar(phase)&&all(isfield(phase,{'offset_s','ra_on'}))&& ...
        isnumeric(phase.offset_s)&&isreal(phase.offset_s)&&isscalar(phase.offset_s)&&isfinite(phase.offset_s), ...
        'behavior:azRoute:phase','phase requires finite offset_s and binary ra_on.');
    ra=flag(phase.ra_on,'ra_on');
    release=false;
    if isfield(phase,'release')
        release=flag(phase.release,'release');
    end
    assert(isstruct(P)&&isfield(P,'backend')&&isfield(P.backend,'az')&&isfield(P.backend,'ni')&& ...
        isfield(P.backend.ni,'az'),'behavior:azRoute:parameters','Require explicit P.backend AZ configuration.');
    enabled=flag(P.backend.ni.az,'P.backend.ni.az');
    if isfield(P.backend.az,'mode')
        mode=char(P.backend.az.mode);
    else
        % Legacy configs may omit the mode, but only while AZ is disabled.
        assert(~enabled,'behavior:azRoute:missingMode','Enabled AZ needs an explicit mode.');
        mode='off';
    end
    assert(any(strcmp(mode,{'off','ordinary','chop','hold','hold_chop'})), ...
        'behavior:azRoute:mode','Unsupported AZ mode.');
    assert(enabled==~strcmp(mode,'off'),'behavior:azRoute:modeFlag', ...
        'P.backend.ni.az must agree with mode off/on.');
    chopped=any(strcmp(mode,{'chop','hold_chop'}));
    held=any(strcmp(mode,{'hold','hold_chop'}));
    % Chopping polarity repeats every four samples: +1,-1,-1,+1.
    % The returned polarity multiplies the complete physical Qres; CT D2/TA
    % signs stay in the backend comparator negative-feedback coordinate.
    pol=1;
    if chopped
        sequence=[1 -1 -1 1];
        pol=sequence(mod(id,4)+1);
    end
    writeEligible=enabled&&(~held||mod(id,2)==0);
    if isfield(P.backend.az,'write_end_s')
        stop=double(P.backend.az.write_end_s);
        windowSource='explicit_engineering_candidate';
    else
        assert(isfield(P,'groups'),'behavior:azRoute:writeWindow', ...
            'Supply write_end_s or the existing grouped calendar.');
        found=[];
        for k=1:numel(P.groups)
            if any(strcmp({P.groups(k).events.type},'ra_start'))
                found(end+1)=P.groups(k).time_s; %#ok<AGROW>
            end
        end
        assert(isscalar(found),'behavior:azRoute:raCalendar','Need exactly one RA-start event.');
        stop=found;
        windowSource='existing_ra_start_engineering_candidate';
    end
    assert(isscalar(stop)&&isreal(stop)&&isfinite(stop)&& ...
        stop==31.25*1e-9, ...
        'behavior:azRoute:writeWindow','Current unchanged calendar requires write_end=31.25 ns.');
    if isfield(P.backend.az,'write_start_s')
        assert(isscalar(P.backend.az.write_start_s)&&P.backend.az.write_start_s==0, ...
            'behavior:azRoute:writeStart','Current unchanged calendar starts AZ at CNV=0.');
    end
    inWindow=phase.offset_s>=0&&phase.offset_s<stop;
    azOn=writeEligible&&inWindow&&~ra&&~release;
    assert(~(enabled&&inWindow&&ra),'behavior:azRoute:overlap', ...
        'RA cannot be enabled inside the declared AZ write interval.');
    a=struct('mode',mode,'sample_id',double(id),'epoch',double(epoch), ...
        'pair_id',floor(double(id)/2),'polarity',double(pol),'qres_sign',double(pol), ...
        'chop_enabled',chopped,'hold_enabled',held,'write_eligible',writeEligible, ...
        'write_window',inWindow,'az_on',azOn,'ra_on',ra, ...
        'reset_signal',~ra,'az_end',writeEligible&&phase.offset_s==stop, ...
        'write_start_s',0,'write_end_s',stop,'write_window_source',windowSource);
end
function b=flag(v,name)
    assert((islogical(v)||isnumeric(v))&&isreal(v)&&isscalar(v)&&isfinite(v)&&any(v==[0 1]), ...
        'behavior:azRoute:flag','%s must be binary scalar.',name);b=logical(v);
end
