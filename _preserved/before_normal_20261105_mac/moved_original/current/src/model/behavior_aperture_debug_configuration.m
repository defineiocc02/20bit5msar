function P=behavior_aperture_debug_configuration(P)
%BEHAVIOR_APERTURE_DEBUG_CONFIGURATION Explicit bounded log storage controls.
% Default false/MAX1; true restricted to N8/MAXInf. No graph/file/state writes.
% Caller sets ToWorkspace variable aperture_log and MaxDataPoints expression
% 'P.debug.aperture_max_points'; observer itself never limits or counts rows.
    if ~isfield(P,'debug'),P.debug=struct();end
    assert(isstruct(P.debug)&&isscalar(P.debug),'aperture:debug','P.debug must be a scalar struct.');
    if ~isfield(P.debug,'aperture_enabled'),P.debug.aperture_enabled=false;end
    v=P.debug.aperture_enabled;
    assert(isscalar(v)&&isreal(v)&&ismember(v,[0 1]), ...
        'aperture:debug','aperture_enabled must be one logical flag.');
    P.debug.aperture_enabled=logical(v);
    assert(~v||P.N==8,'aperture:debugN8','Enable actual aperture log only for N8.');
    P.debug.aperture_max_points=1;
    if v,P.debug.aperture_max_points=Inf;end
end
