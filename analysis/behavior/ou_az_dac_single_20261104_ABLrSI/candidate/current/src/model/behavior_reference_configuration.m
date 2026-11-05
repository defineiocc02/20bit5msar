function P=behavior_reference_configuration(P)
%BEHAVIOR_REFERENCE_CONFIGURATION Public reference queue config/IC only.
% Caller: prepare after the REAL parent event groups/transport enable are final.
% Reads only P.transport.enabled and P.groups event names. Writes only
% P.ref_queue/P.xREF0, reusing the native-tested queue parameters/init/pack.
% No ADC C, held, residual, source formula, model/graph or file/RNG access.
    assert(isstruct(P)&&isscalar(P)&&isfield(P,'transport')&& ...
        isstruct(P.transport)&&isscalar(P.transport)&&isfield(P.transport,'enabled'), ...
        'referenceConfig:transport','Explicit P.transport.enabled required.');
    enabled=P.transport.enabled;
    assert(isscalar(enabled)&&isreal(enabled)&&ismember(enabled,[0 1]), ...
        'referenceConfig:enabled','Transport enable must be a logical scalar.');
    assert(isfield(P,'groups')&&isstruct(P.groups)&&~isempty(P.groups), ...
        'referenceConfig:groups','Actual final parent groups are required.');
    cnv=[];
    close=[];
    for g=1:numel(P.groups)
        types={P.groups(g).events.type};
        assert(sum(strcmp(types,'cnv'))<=1&&sum(strcmp(types,'frame_ready'))<=1, ...
            'referenceConfig:duplicateEvent','Duplicate CNV/frame_ready token in one group.');
        if any(strcmp(types,'cnv')),cnv(end+1)=g;end %#ok<AGROW>
        if any(strcmp(types,'frame_ready')),close(end+1)=g;end %#ok<AGROW>
    end
    assert(isscalar(cnv),'referenceConfig:cnvGroup','Need exactly one actual parent CNV group.');
    if enabled
        assert(isscalar(close),'referenceConfig:closeGroup', ...
            'Transport on requires exactly one actual frame_ready parent group before queue configuration.');
        closeGroup=close;
    else
        assert(isempty(close)||isscalar(close),'referenceConfig:closeGroup','Ambiguous frame_ready groups.');
        % The off calendar has no inserted close token. This unused positive
        % placeholder is the REAL CNV index; off core returns before reading it.
        % Never fabricate or append a 49th event merely to initialize bypass.
        closeGroup=cnv;if ~isempty(close),closeGroup=close;end
    end
    P.ref_queue=behavior_reference_queue_parameters(struct('enabled',logical(enabled), ...
        'cnv_group',cnv,'close_group',closeGroup));
    P.xREF0=behavior_reference_queue_pack(behavior_reference_queue_init());
end
