function r = sar20_cdac2_network(net, vx, sar_sign, track_sign, vref, reset_noise_v, floating_qb_c)
    % 文档版本：1.0
    % 功能：差分CDAC节点电荷守恒。
    % 当前调用方：behavior_backend_step 的观察、开关电荷与输出负载计算。
    % 输入参数：net, vx, sar_sign, track_sign, vref, reset_noise_v, floating_qb_c.
    % 输出参数：r.
    % 单位：模拟量单位SI制，码/逻辑量无量纲。
    % 状态/复位/RNG：无跨调用状态或RNG；reset_noise_v为显式输入电压，不传seed。
    % 假设与边界：符号0表示VCM保持；floating_qb_c显式传电荷。
    % 本函数不执行验证；当前验收以实际运行的源码快照、输入配置及回执为准。
    % SAR20_CDAC2_NETWORK Charge conservation of both differential split networks.
    % Voltages are departures from VCM at reset release. SAR/track signs are
    % -1,0,+1; 0 means both bottom plates remain at VCM, not an undecided zero bit.
    % Inputs are VX differential, 12 SAR states and 7 tracking states. A sign +1
    % drives P bottom to VCM-Vref/2 and N bottom to VCM+Vref/2.
    % [CT-01/v1] 差分CDAC节点电荷守恒。
    sar_sign = double(sar_sign(:));
    track_sign = double(track_sign(:));
    if nargin < 6
        reset_noise_v = zeros(2, 1);
    end
    if nargin < 7
        floating_qb_c = zeros(2, 1);
    end
    if ~isstruct(net) || ~isfield(net, 'main_f') || ~isfield(net, 'sub_f') || ...
            ~isfield(net, 'track_f') || size(net.main_f, 1) ~= 2 || ...
            size(net.sub_f, 1) ~= 2 || size(net.track_f, 1) ~= 2 || ...
            size(net.main_f, 2) + size(net.sub_f, 2) ~= 12 || ...
            size(net.track_f, 2) ~= 7
        error('sar20:cdac2Layout', ...
              'CDAC2 network must have two differential halves, 12 D2 caps total and 7 tracking caps.');
    end
    n_main = size(net.main_f, 2);
    n_sub = size(net.sub_f, 2);
    if numel(sar_sign) ~= n_main + n_sub || numel(track_sign) ~= size(net.track_f, 2)
        error('sar20:cdac2Shape', ...
              'D2 sign vector must match main+sub matrix columns; tracking signs must match tracking columns.');
    end
    v = zeros(2, 2);
    input_gain = zeros(2, 1);
    dv = zeros(2, 1);
    tv = zeros(2, 1);
    equivalent_load = zeros(2, 1);
    for side = 1:2
        cs = net.cinc_f(side);
        cb = net.bridge_f(side);
        cm = net.main_f(side, :);
        cl = net.sub_f(side, :);
        ct = net.track_f(side, :);
        a = cs + sum(cm) + cb + net.parasitic_main_f(side);
        b = sum(cl) + sum(ct) + net.dummy_f(side) + cb + net.parasitic_sub_f(side);
        matrix = [a -cb; -cb b];
        polarity = 3 - 2 * side;
        qin = [cs * polarity * vx / 2; 0];
        % D2 raw width is fixed at 12, while the physical split may be 6+6
        % (engineering candidate) or 10+2 (paper Fig. 3 candidate).
        qdac = -polarity * vref / 2 * ...
            [cm * sar_sign(1:n_main); cl * sar_sign(n_main + (1:n_sub))];
        qtrack = -polarity * vref / 2 * [0; ct * track_sign];
        % B has no conductive reset. Preserve its initial floating charge;
        % A-only reset leaves a rank-one voltage/noise initial condition.
        effective_a = a - cb^2 / b;
        qmemory = [-cb * floating_qb_c(side) / b + effective_a * reset_noise_v(side); ...
                 floating_qb_c(side)];
        node = matrix \ (qin + qdac + qtrack + qmemory);
        v(side, :) = node';
        gi = matrix \ [cs; 0];
        gd = matrix \ qdac;
        gt = matrix \ qtrack;
        input_gain(side) = gi(1);
        dv(side) = gd(1);
        tv(side) = gt(1);
        equivalent_load(side) = cs * (1 - gi(1));
    end
    r.vy = v(1, 1) - v(2, 1);
    r.vz = v(1, 2) - v(2, 2);
    r.vy_common_delta = (v(1, 1) + v(2, 1)) / 2;
    r.nodes_delta_v = v;
    r.switch_node_delta_v = dv + tv;
    r.cinc_injected_charge_c = net.cinc_f .* (dv + tv);
    r.node_effective_cap_f = net.cinc_f ./ input_gain;
    alpha = mean(input_gain);
    r.alpha = alpha;
    r.dac_ra_v = -(dv(1) - dv(2)) / alpha;
    r.track_ra_v = -(tv(1) - tv(2)) / alpha;
    r.ra_load_per_output_f = equivalent_load;
end
