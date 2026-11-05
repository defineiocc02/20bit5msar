function [y, state] = sar20_lvds_rx_step(t_s, u, state, cfg)
    % 文档版本：1.0
    % 功能：差分边沿、前导、echo和数据帧解析。
    % 真实调用方：matlab/sar20_pin_fpga_step.m、matlab/sar20_lvds_rx_numeric_step.m
    % 输入参数：t_s, u, state, cfg.
    % 输出参数：y, state.
    % 单位：模拟量单位SI制，码/逻辑量无量纲。
    % 状态/复位/RNG：显式state保存边沿、shift register和帧校验。
    % 假设与边界：逻辑pin解析，不含CDC/亚稳概率。
    % 证据位置：tests/test_sar20_lvds.m
    % SAR20_LVDS_RX_STEP Pin-only receiver for the Rev0.3 custom 32-bit frame.
    %   u fields are only cnv, clk, en, d_p, d_n, dco_p, and dco_n.  The
    %   function never accepts an internal raw record, hidden debug tag, sample
    %   ID, bank, epoch, or analog-model signal.  Sample ID is reconstructed from
    %   CNV count minus the fixed two-slot latency; bank/pair/polarity are derived
    %   locally from that ID and cfg.polarity_sequence.
    %
    %   DCO rising +8 ns is the ignored preamble.  The 32 captures are expected at
    %   +12,+16,...,+136 ns; +138 ns final falling edge closes the word.  A slot
    %   without a complete word emits one VALID=0 event when the next CNV arrives.
    %
    %   This is a numeric protocol candidate; it does not verify LVDS electrical,
    %   setup/hold, CDC/RDC, package, or FPGA timing.

    % [IO-01/v1] 核心阶段：差分边沿、前导、echo和数据帧解析。
    if nargin < 4 || isempty(cfg)
        cfg = rx_defaults();
    else
        cfg = rx_defaults(cfg);
    end
    if ~isnumeric(t_s) || ~isreal(t_s) || ~isscalar(t_s) || ~isfinite(t_s)
        error('sar20:lvdsRx:time', 't_s must be a finite scalar in seconds.');
    end
    check_input(u);
    if isempty(state)
        state = initial_state();
    else
        check_state(state);
    end

    cnv = double(u.cnv ~= 0);
    clk = double(u.clk ~= 0);
    dco = double(u.dco_p ~= 0);
    dco_n = double(u.dco_n ~= 0);
    en = double(u.en);
    mode = en_mode(en);
    y = output_template();
    debug = y.debug;
    debug.mode = mode;
    debug.epoch = state.epoch;

    % EN=0000 is the only epoch reset.  Invalid EN merely disables/cancels this
    % receive slot; test-mode transitions keep the same CNV calendar.
    if en == 0
        if ~state.in_shutdown
            state.epoch = state.epoch + 1;
        end
        state.in_shutdown = true;
        state.cnv_id = -1;
        state.cnv_count = 0;
        state.last_complete_ordinal = 0;
        state.resync_required = false;
        state.slot_active = false;
        state.slot_closed = true;
        state.slot_done = false;
        state.slot_corrupt = false;
        state.slot_target_id = -2;
        state.slot_time_s = NaN;
        state.frame_word = 0;
        state.capture_count = 0;
        state.prev_cnv = cnv;
        state.prev_clk = clk;
        state.prev_dco = dco;
        state.prev_dco_n = dco_n;
        state.prev_en = en;
        y.debug = debug;
        y.debug.mode = 0;
        y.debug.epoch = state.epoch;
        y.debug.reset = 1;
        return
    end

    state.in_shutdown = false;
    cnv_rise = state.prev_cnv == 0 && cnv == 1;
    dco_pair_valid = dco ~= dco_n;
    dco_rise = state.prev_dco == 0 && dco == 1 && state.prev_dco_n == 1 && dco_n == 0;
    dco_fall = state.prev_dco == 1 && dco == 0 && state.prev_dco_n == 0 && dco_n == 1;
    debug.cnv_rise = double(cnv_rise);
    debug.dco_rise = double(dco_rise);
    debug.dco_fall = double(dco_fall);
    debug.echo_mismatch = double((mode == 1 || mode == 2) && ...
                                 dco_pair_valid && (double(u.clk ~= 0) ~= dco));

    % If a previous normal/test slot never closed with a full frame, retire it as
    % invalid before opening the next CNV slot.  This emits no replay and leaves
    % the CNV-derived ID calendar untouched.
    if cnv_rise
        if isfinite(state.slot_time_s) && ...
                t_s - state.slot_time_s < cfg.sample_period_s - cfg.time_tolerance_s
            error('sar20:lvdsRx:cnvInterval', ...
                  'CNV rising edges must be separated by at least sample_period_s.');
        end
        if state.slot_active && ~state.slot_done && ...
                (state.slot_mode == 1 || state.slot_mode == 2)
            y = emit_invalid(y, state, true);
            debug.previous_slot_missing = 1;
        end
        next_id = state.cnv_id + 1;
        if next_id >= cfg.counter_modulus
            next_id = 0;
            debug.counter_wrapped = 1;
        end
        state.cnv_id = next_id;
        state.cnv_count = state.cnv_count + 1;
        if state.cnv_count - state.last_complete_ordinal >= cfg.counter_modulus - 1
            state.resync_required = true;
        end
        state.slot_time_s = t_s;
        state.slot_mode = mode;
        state.slot_active = true;
        state.slot_closed = (mode == 3);
        state.slot_done = false;
        state.slot_corrupt = false;
        state.capture_count = 0;
        state.frame_word = 0;
        state.preamble_seen = false;
        state.slot_target_id = slot_target(state.cnv_id, state.cnv_count, cfg);
        debug.new_slot = 1;
        debug.slot_id = state.cnv_id;
        debug.target_sample_id = state.slot_target_id;
    end

    % A mode disable cancels any partial current-slot frame but does not reset the
    % local slot counter.  Re-enable consumes only the next future CNV slot.
    if mode ~= 1 && mode ~= 2
        % Keep the slot identity so the next CNV can retire it as invalid; only
        % the in-progress capture is cancelled.
        state.slot_closed = true;
    end

    if state.slot_active && ~state.slot_closed
        rel_s = t_s - state.slot_time_s;
        in_burst = rel_s >= cfg.preamble_rise_s - cfg.edge_tolerance_s && ...
            rel_s <= cfg.final_fall_s + cfg.edge_tolerance_s;
        if in_burst && ~dco_pair_valid
            state.slot_corrupt = true;
            debug.dco_differential_error = 1;
        end
        if in_burst && dco_pair_valid && double(u.clk ~= 0) ~= dco
            state.slot_corrupt = true;
            debug.echo_mismatch = 1;
        end
        if dco_rise
            if abs(rel_s - cfg.preamble_rise_s) <= cfg.edge_tolerance_s
                state.preamble_seen = true;
                debug.preamble_ignored = 1;
            elseif rel_s >= cfg.first_capture_s - cfg.edge_tolerance_s && ...
                    rel_s <= cfg.last_capture_s + cfg.edge_tolerance_s
                expected_s = cfg.first_capture_s + state.capture_count * cfg.clk_period_s;
                if abs(rel_s - expected_s) <= cfg.edge_tolerance_s && dco_pair_valid
                    if double(u.d_p ~= 0) == double(u.d_n ~= 0)
                        state.slot_corrupt = true;
                        debug.differential_data_error = 1;
                    else
                        bit_value = double(u.d_p ~= 0);
                        state.frame_word = state.frame_word * 2 + bit_value;
                        state.capture_count = state.capture_count + 1;
                        debug.captured_bit = bit_value;
                        debug.bit_index = state.capture_count - 1;
                    end
                else
                    state.slot_corrupt = true;
                    debug.rise_timing_error = 1;
                end
            elseif rel_s > cfg.last_capture_s && rel_s <= cfg.final_fall_s + cfg.edge_tolerance_s
                state.slot_corrupt = true;
                debug.extra_capture = 1;
            elseif in_burst
                state.slot_corrupt = true;
                debug.rise_timing_error = 1;
            end
        end

        if dco_fall && abs(rel_s - cfg.final_fall_s) <= cfg.edge_tolerance_s
            state.slot_closed = true;
            debug.final_fall = 1;
            if state.capture_count == cfg.frame_bits && ~state.slot_corrupt && ...
                    state.preamble_seen && dco_pair_valid
                y = decode_word(y, state, cfg, true);
                state.slot_done = true;
                state.last_complete_ordinal = state.cnv_count;
            else
                debug.incomplete_frame = 1;
                if ~state.preamble_seen
                    debug.missing_preamble = 1;
                end
            end
        end
    end

    y.debug = debug;
    y.debug.mode = mode;
    y.debug.epoch = state.epoch;
    y.debug.slot_id = state.cnv_id;
    y.debug.target_sample_id = state.slot_target_id;
    y.debug.capture_count = state.capture_count;
    y.debug.slot_corrupt = double(state.slot_corrupt);
    y.debug.resync_required = double(state.resync_required);
    y.resync_required = double(state.resync_required);
    if state.resync_required
        y.ready = 0;
        y.valid = 0;
        y.adc_sample_valid = 0;
        y.d1 = 0;
        y.d2 = 0;
        y.dt = 0;
    end

    state.prev_cnv = cnv;
    state.prev_clk = clk;
    state.prev_dco = dco;
    state.prev_dco_n = dco_n;
    state.prev_en = en;
end

function y = decode_word(y, s, cfg, complete)
    word = s.frame_word;
    y.ready = double(complete);
    y.frame_word = word;
    y.d1 = floor(word / 2^21);
    y.d2 = mod(floor(word / 2^9), 2^12);
    y.dt = mod(floor(word / 2), 2^8);
    y.valid = mod(word, 2);
    if y.valid == 0
        y.d1 = 0;
        y.d2 = 0;
        y.dt = 0;
    end
    y.sample_id = s.slot_target_id;
    y.epoch = s.epoch;
    y.is_test = double(s.slot_mode == 2);
    y.test_pattern_ok = double(s.slot_mode == 2 && word == cfg.test_word);
    y.adc_sample_valid = double(s.slot_mode == 1 && y.valid ~= 0 && ...
                                s.slot_target_id >= 0 && ~s.resync_required);
    if s.resync_required
        y.d1 = 0;
        y.d2 = 0;
        y.dt = 0;
        y.valid = 0;
    end
    if s.slot_target_id >= 0
        % Public sample-ID parity tag; not a coefficient-bank selector.
        y.bank = mod(s.slot_target_id, 2);
        y.pair_id = floor(s.slot_target_id / 2);
        y.polarity = cfg.polarity_sequence(mod(s.slot_target_id, numel(cfg.polarity_sequence)) + 1);
    end
end

function y = emit_invalid(y, s, is_complete_event)
    y.ready = double(is_complete_event);
    y.frame_word = 0;
    y.d1 = 0;
    y.d2 = 0;
    y.dt = 0;
    y.valid = 0;
    y.adc_sample_valid = 0;
    y.sample_id = s.slot_target_id;
    y.epoch = s.epoch;
    y.is_test = double(s.slot_mode == 2);
    y.bank = -1;
    y.pair_id = -1;
    y.polarity = 0;
    y.test_pattern_ok = 0;
end

function id = slot_target(cnv_id, count, cfg)
    if count <= cfg.latency_samples
        id = cnv_id - cfg.latency_samples;
    else
        id = mod(cnv_id - cfg.latency_samples, cfg.counter_modulus);
    end
end

function mode = en_mode(en)
    if ~isscalar(en) || ~isnumeric(en) || ~isreal(en) || ~isfinite(en) || ...
            en ~= floor(en) || en < 0 || en > 15
        error('sar20:lvdsRx:en', 'EN must be a four-bit integer.');
    end
    if en == 10
        mode = 1; % normal
    elseif en == 4
        mode = 2; % test
    elseif en == 0
        mode = 0; % shutdown/reset
    else
        mode = 3; % invalid
    end
end

function check_input(u)
    required = {'cnv', 'clk', 'en', 'd_p', 'd_n', 'dco_p', 'dco_n'};
    if ~isstruct(u) || ~isscalar(u) || ~all(isfield(u, required)) || ...
            numel(fieldnames(u)) ~= numel(required)
        error('sar20:lvdsRx:input', 'u must contain only visible CNV/CLK/EN/D/DCO pins.');
    end
    for name = {'cnv', 'clk', 'd_p', 'd_n', 'dco_p', 'dco_n'}
        v = u.(name{1});
        if ~(isnumeric(v) || islogical(v)) || ~isreal(v) || ~isscalar(v) || ~isfinite(v)
            error('sar20:lvdsRx:inputLevel', '%s must be a finite scalar level.', name{1});
        end
    end
    if ~isnumeric(u.en) || ~isreal(u.en) || ~isscalar(u.en) || ~isfinite(u.en)
        error('sar20:lvdsRx:inputLevel', 'en must be a finite four-bit integer value.');
    end
end

function check_state(s)
    required = {'initialized', 'prev_cnv', 'prev_clk', 'prev_dco', 'prev_dco_n', 'prev_en', ...
                'in_shutdown', 'epoch', 'cnv_id', 'cnv_count', 'slot_time_s', 'slot_mode', ...
                'slot_active', 'slot_closed', 'slot_done', 'slot_corrupt', 'slot_target_id', ...
                'frame_word', 'capture_count', 'preamble_seen', 'last_complete_ordinal', ...
                'resync_required'};
    if ~isstruct(s) || ~all(isfield(s, required)) || s.initialized ~= 1
        error('sar20:lvdsRx:state', 'state must be empty or a state returned by this function.');
    end
end

function s = initial_state()
    s = struct();
    s.initialized = 1;
    s.prev_cnv = 0;
    s.prev_clk = 0;
    s.prev_dco = 0;
    s.prev_dco_n = 1;
    s.prev_en = -1;
    s.in_shutdown = false;
    s.epoch = 0;
    s.cnv_id = -1;
    s.cnv_count = 0;
    s.last_complete_ordinal = 0;
    s.resync_required = false;
    s.slot_time_s = NaN;
    s.slot_mode = 3;
    s.slot_active = false;
    s.slot_closed = true;
    s.slot_done = false;
    s.slot_corrupt = false;
    s.slot_target_id = -2;
    s.frame_word = 0;
    s.capture_count = 0;
    s.preamble_seen = false;
end

function y = output_template()
    y = struct('ready', 0, 'frame_word', 0, 'd1', 0, 'd2', 0, 'dt', 0, ...
               'valid', 0, 'adc_sample_valid', 0, 'resync_required', 0, ...
               'sample_id', -1, 'epoch', 0, ...
               'bank', -1, 'pair_id', -1, 'polarity', 0, 'is_test', 0, ...
               'test_pattern_ok', 0, 'debug', struct('mode', 3, 'epoch', 0, ...
                                              'cnv_rise', 0, 'dco_rise', 0, 'dco_fall', 0, 'new_slot', 0, 'slot_id', -1, ...
                                              'target_sample_id', -2, 'preamble_ignored', 0, 'captured_bit', 0, ...
                                              'bit_index', -1, 'capture_count', 0, 'final_fall', 0, 'incomplete_frame', 0, ...
                                              'previous_slot_missing', 0, 'differential_data_error', 0, ...
                                              'rise_timing_error', 0, 'extra_capture', 0, 'echo_mismatch', 0, ...
                                              'dco_differential_error', 0, 'missing_preamble', 0, 'counter_wrapped', 0, ...
                                              'slot_corrupt', 0, 'resync_required', 0, 'reset', 0));
end

function cfg = rx_defaults(cfg)
    if nargin == 0 || isempty(cfg)
        cfg = struct();
    end
    if ~isstruct(cfg) || ~isscalar(cfg)
        error('sar20:lvdsRx:config', 'cfg must be a scalar struct.');
    end
    defaults = struct('sample_period_s', 200e-9, 'clk_period_s', 4e-9, ...
                      'preamble_rise_s', 8e-9, 'first_capture_s', 12e-9, ...
                      'last_capture_s', 136e-9, 'final_fall_s', 138e-9, ...
                      'frame_bits', 32, 'latency_samples', 2, 'counter_modulus', 2^32, ...
                      'test_word', hex2dec('A55A5AA5'), 'polarity_sequence', [1 -1 -1 1], ...
                      'edge_tolerance_s', 1e-12, 'time_tolerance_s', 1e-15);
    names = fieldnames(defaults);
    for k = 1:numel(names)
        if ~isfield(cfg, names{k})
            cfg.(names{k}) = defaults.(names{k});
        end
    end
    sequence = double(cfg.polarity_sequence(:).');
    if isempty(sequence) || mod(numel(sequence), 2) ~= 0 || any(abs(sequence) ~= 1) || ...
            any(sequence(1:2:end) ~= -sequence(2:2:end))
        error('sar20:lvdsRx:polarity', ...
              'polarity_sequence must be even-length +/-1 pairs with opposite polarities.');
    end
    cfg.polarity_sequence = sequence;
end
