function report=normal_compare_outputs(a,b,skip)
% Compare actual non-debug outputs bitwise; no physics or state reconstruction.
    assert(isa(a,'Simulink.SimulationOutput')&&isa(b,'Simulink.SimulationOutput')&& ...
        isempty(a.ErrorMessage)&&isempty(b.ErrorMessage),'sbN8:output','Need two completed outputs.');
    na=sort(a.who);nb=sort(b.who);assert(isequal(na,nb),'sbN8:outputs','Output variable sets differ.');
    if nargin<3,skip={};end
    permitted={'adi_wire_log','aperture_log','dac_ra_pre_log'};
    assert(iscell(skip)&&all(ismember(skip,permitted)),'normalCompare:skip','Only explicit observer logs may be excluded.');
    required={'raw_log','ready_log','record_log', ...
        'record_ready_log','front_log','back_log','control_log','event_log','code_log','yout','tout'};
    assert(all(ismember(required,na)), ...
        'sbN8:outputs','Required actual or debug output is missing.');
    for k=1:numel(na)
        if any(strcmp(na{k},skip)),continue;end
        same_value(a.get(na{k}),b.get(na{k}),na{k});
    end
    y=a.get('yout');assert(isa(y,'Simulink.SimulationData.Dataset')&&y.numElements==3, ...
        'sbN8:rootPorts','Require three actual root outputs.');
    scope='bit equality of all actual output variables and root Time/Data';
    if ~isempty(skip),scope='bit equality of non-observer variables and root Time/Data; named observer logs excluded';end
    report=struct('status','PASS','compared_variables',{setdiff(na,skip,'stable')}, ...
        'excluded_observer_variables',{skip},'root_outputs',3,'scope',scope);
end
function same_value(a,b,where)
    assert(strcmp(class(a),class(b))&&isequal(size(a),size(b)), ...
        'sbN8:type','Class or shape differs: %s.',where);
    if isa(a,'timeseries')
        assert(a.IsTimeFirst==b.IsTimeFirst,'sbN8:timeFirst','Time orientation differs: %s.',where);
        same_value(a.Time,b.Time,[where '.Time']);same_value(a.Data,b.Data,[where '.Data']);
    elseif isa(a,'Simulink.SimulationData.Dataset')
        assert(a.numElements==b.numElements,'sbN8:dataset','Dataset count differs: %s.',where);
        for j=1:a.numElements
            x=a.getElement(j);y=b.getElement(j);
            assert(strcmp(class(x),class(y))&&isprop(x,'Name')&&isprop(x,'Values')&& ...
                isequal(x.Name,y.Name),'sbN8:signal','Dataset signal differs: %s.',where);
            same_value(x.Values,y.Values,sprintf('%s[%d]',where,j));
        end
    elseif isnumeric(a)
        assert(isreal(a)==isreal(b),'sbN8:complex','Complexity differs: %s.',where);
        assert(isequal(typecast(real(a(:)),'uint8'),typecast(real(b(:)),'uint8')), ...
            'sbN8:bits','Real bits differ: %s.',where);
        if ~isreal(a)
            assert(isequal(typecast(imag(a(:)),'uint8'),typecast(imag(b(:)),'uint8')), ...
                'sbN8:bits','Imaginary bits differ: %s.',where);
        end
    elseif islogical(a)||ischar(a)||isstring(a)
        assert(isequaln(a,b),'sbN8:value','Value differs: %s.',where);
    else,error('sbN8:unhandled','Cannot skip output class %s at %s.',class(a),where);
    end
end
