function p=behavior_reference_queue_parameters(p)
%BEHAVIOR_REFERENCE_QUEUE_PARAMETERS Public instrument-reference routing only.
% enabled=false bypasses original Ref4; groups index the actual merged calendar.
    q=struct('enabled',false,'cnv_group',1,'close_group',49);
    if nargin==0,p=q;return;end
    assert(isstruct(p)&&isscalar(p)&&all(ismember(fieldnames(p),fieldnames(q))), ...
        'referenceQueue:config','Unknown reference queue parameter.');
    % Copy every incoming field into a normalized struct, so unknown extras are
    % preserved rather than silently dropped.
    names=fieldnames(p);
    for k=1:numel(names)
        q.(names{k})=p.(names{k});
    end
    p=q;
    assert(isscalar(p.enabled)&&isreal(p.enabled)&&ismember(p.enabled,[0 1]), ...
        'referenceQueue:enabled','enabled must be one logical flag.');p.enabled=logical(p.enabled);
    for name={'cnv_group','close_group'}
        v=p.(name{1});assert(isnumeric(v)&&isreal(v)&&isscalar(v)&&isfinite(v)&&v>=1&&v==floor(v), ...
            'referenceQueue:group','Group indices must be positive integers.');
    end
end
