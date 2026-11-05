function report=compare_captures(referenceDir,candidateDir,allowPhysicsExtras)
% COMPARE_CAPTURES Version 2 (2026-10-26): exact actual-Simulink capture gate.
% Inputs are closed direct_run directories. No model/config/RNG changes.
% Default comparison requires the same complete logger inventory, dimensions,
% IEEE data/time/tout bits and the entire selected output tree. No tolerance.
% allowPhysicsExtras=true is ONLY the observer compact/physics equivalence
% check: the five declared heavy logs may be added. It is not a full-state
% acceptance gate. Optimization comparisons must use false and both physics.
    assert(nargin==3 && islogical(allowPhysicsExtras) && isscalar(allowPhysicsExtras), ...
        'SAR20Compare:arguments','Supply two closed capture directories and an explicit logical scope.');
    a=load(fullfile(referenceDir,'raw.mat'),'simOut');
    b=load(fullfile(candidateDir,'raw.mat'),'simOut');
    na=log_names(a.simOut.who);nb=log_names(b.simOut.who);
    na=setdiff(na,{'tout','yout'});nb=setdiff(nb,{'tout','yout'});
    heavy={'pool_analog_voltage','pool_analog_old_state','pool_analog_pred_state', ...
        'pool_analog_ledger','pool_analog_roundoff_ledger'};
    onlyA=setdiff(na,nb);onlyB=setdiff(nb,na);
    if allowPhysicsExtras
        assert(numel(na)==54&&numel(nb)==59&&isempty(intersect(na,heavy))&& ...
            isempty(onlyA)&&isequal(onlyB,sort(heavy(:))), ...
            'SAR20Compare:inventory','Require compact 54 -> physics 59, adding exactly the five heavy observers.');
    else
        assert(isequal(na,nb)&&((numel(na)==54&&isempty(intersect(na,heavy)))|| ...
            (numel(na)==59&&all(ismember(heavy,na)))), ...
            'SAR20Compare:inventory','Require identical compact 54 or complete physics 59 logger inventories.');
    end
    validate_heavy(a.simOut,na,heavy);validate_heavy(b.simOut,nb,heavy);
    names=intersect(na,nb);
    rows=repmat(struct('name','','data_bits_equal',false,'time_bits_equal',false),numel(names),1);
    stateRows=struct('name',{},'rng_word_5179_bits_equal',{}, ...
        'charge_words_5180_5181_bits_equal',{});
    for k=1:numel(names)
        sa=a.simOut.get(names{k});sb=b.simOut.get(names{k});
        assert(isa(sa,'timeseries')&&isa(sb,'timeseries'), ...
            'SAR20Compare:series','Expected real saved timeseries for %s.',names{k});
        rows(k).name=names{k};
        rows(k).data_bits_equal=exact(sa.Data,sb.Data);
        rows(k).time_bits_equal=exact(sa.Time,sb.Time);
        if any(strcmp(names{k},{'pool_analog_old_state','pool_analog_pred_state'}))
            da=heavy_matrix(sa,5181,names{k});db=heavy_matrix(sb,5181,names{k});
            stateRows(end+1)=struct('name',names{k}, ...
                'rng_word_5179_bits_equal',exact(da(:,5179),db(:,5179)), ...
                'charge_words_5180_5181_bits_equal',exact(da(:,5180:5181),db(:,5180:5181))); %#ok<AGROW>
        end
    end
    toutEqual=exact(a.simOut.get('tout'),b.simOut.get('tout'));
    clear a b
    a=load(fullfile(referenceDir,'selected.mat'),'selected');
    b=load(fullfile(candidateDir,'selected.mat'),'selected');
    selectedEqual=exact(a.selected,b.selected);
    report=struct('status','bitwise_capture_fail','reference_dir',referenceDir, ...
        'candidate_dir',candidateDir,'allow_physics_extras',allowPhysicsExtras, ...
        'excluded_reference_loggers',{onlyA},'excluded_candidate_loggers',{onlyB}, ...
        'full_analog_state_in_comparison',~allowPhysicsExtras&&all(ismember(heavy,names)), ...
        'native_tout_bits_equal',toutEqual,'entire_selected_tree_bits_equal',selectedEqual, ...
        'state_word_comparisons',stateRows, ...
        'logger_count',numel(names),'loggers',rows,'tolerance_used',[]);
    if toutEqual&&selectedEqual&&all([rows.data_bits_equal])&&all([rows.time_bits_equal])
        report.status='bitwise_capture_pass';
    end
end

function names=log_names(value)
    if isstring(value)||ischar(value),value=cellstr(value);end
    assert(iscell(value), ...
        'SAR20Compare:names','SimulationOutput.who must return reviewed text names.');
    for k=1:numel(value)
        if isstring(value{k})&&isscalar(value{k}),value{k}=char(value{k});end
        assert(ischar(value{k})&&isrow(value{k})&&~isempty(value{k}), ...
            'SAR20Compare:names','Logger names must be nonempty text scalars.');
    end
    names=sort(value(:));
    assert(numel(unique(names))==numel(names),'SAR20Compare:names','Duplicate logger names.');
end

function validate_heavy(simOut,names,heavy)
    widths=[1540 5181 5181 4621 6160];
    for k=1:numel(heavy)
        if ismember(heavy{k},names),heavy_matrix(simOut.get(heavy{k}),widths(k),heavy{k});end
    end
end

function data=heavy_matrix(series,width,name)
% Only derive an indexing view; exact() still checks original Data class/shape/bits.
    assert(isa(series,'timeseries')&&isa(series.Data,'double')&& ...
        isreal(series.Data)&&~issparse(series.Data)&&~isempty(series.Time), ...
        'SAR20Compare:heavyStorage','Malformed heavy timeseries %s.',name);
    data=squeeze(series.Data);
    if size(data,1)~=numel(series.Time),data=data.';end
    assert(ismatrix(data)&&size(data,1)==numel(series.Time)&&size(data,2)==width, ...
        'SAR20Compare:heavyWidth','Heavy logger %s must contain %d words per time sample.',name,width);
end

function yes=exact(a,b)
% Compare values as stored. NaNs, signed zero and every low word stay visible.
    yes=strcmp(class(a),class(b))&&isequal(size(a),size(b));
    if ~yes,return;end
    if isstruct(a)
        fields=fieldnames(a);
        yes=isequal(fields,fieldnames(b));if ~yes,return;end
        for i=1:numel(a)
            for k=1:numel(fields)
                if ~exact(a(i).(fields{k}),b(i).(fields{k})),yes=false;return;end
            end
        end
    elseif iscell(a)
        for k=1:numel(a)
            if ~exact(a{k},b{k}),yes=false;return;end
        end
    elseif isnumeric(a)
        assert(~issparse(a)&&~issparse(b)&&isreal(a)&&isreal(b), ...
            'SAR20Compare:storage','Saved logger/selected payload must be full real numeric data.');
        yes=isequal(typecast(a(:),'uint8'),typecast(b(:),'uint8'));
    elseif islogical(a)||ischar(a)||isstring(a)
        yes=isequal(a,b);
    else
        error('SAR20Compare:type','Unreviewed selected payload class: %s.',class(a));
    end
end
