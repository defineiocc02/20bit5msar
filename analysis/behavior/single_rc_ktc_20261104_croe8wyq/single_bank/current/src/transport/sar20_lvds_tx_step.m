function [y, state] = sar20_lvds_tx_step(t_s, u, state, cfg)
    % 文档版本：1.0
    % 功能：CNV/CLK/EN驱动的LVDS serializer。
    % 真实调用方：matlab/sar20_lvds_tx_numeric_step.m
    % 输入参数：t_s, u, state, cfg.
    % 输出参数：y, state.
    % 单位：模拟量单位SI制，码/逻辑量无量纲。
    % 状态/复位/RNG：显式state保存serializer帧和边沿。
    % 假设与边界：离散逻辑边沿，不含pad驱动。
    % 证据位置：tests/test_sar20_lvds.m
    % SAR20_LVDS_TX_STEP Pure event-step model of the Rev0.3 32-bit LVDS TX.
    %   u fields: cnv, clk, en (integer 0..15), record.  record fields are
    %   raw_D1 (11b), raw_D2 (12b), raw_DT (8b), valid, sample_id (uint32-valued
    %   double), epoch, and commit_time_s (seconds).  An absent record uses
    %   sample_id=-1.  This helper has no persistent state and no RNG.
    %
    %   The CNV edge is the atomic N-2 snapshot boundary.  The input bundle must
    %   have committed by CNV-10 ns; equality is accepted.  Output data launches
    %   on CLK falling edges at +10,+14,...,+134 ns.  The +8 ns rising edge is a
    %   preamble, and +138 ns is the final falling edge that parks DATA at logic 0.
    %
    %   This is a numeric protocol candidate, not a pad/CDC/eye/STA model.

    % [IO-01/v1] CNV/CLK/EN驱动的LVDS serializer。
    if nargin < 4 || isempty(cfg)
        cfg = tx_defaults();
    else
        cfg = tx_defaults(cfg);
    end
    if ~isscalar(t_s) || ~isnumeric(t_s) || ~isreal(t_s) || ~isfinite(t_s)
        error('sar20:lvdsTx:time', 't_s must be a finite scalar in seconds.');
    end
    check_input(u);
    if isempty(state)
        state = initial_state(cfg.cache_depth, cfg.history_depth);
    else
        check_state(state);
    end

    % Normalize observable pin inputs to logical levels.
    cnv = double(u.cnv ~= 0);
    clk = double(u.clk ~= 0);
    en = double(u.en);
    record = u.record;
    mode = en_mode(en);

    y = output_template();
    debug = y.debug;
    debug.mode = mode;
    debug.epoch = state.epoch;

    % EN=0000 is the only command that resets the slot calendar.  Repeated low
    % EN levels hold reset without repeatedly incrementing the local epoch.
    if en == 0
        if ~state.in_shutdown
            state.epoch = state.epoch + 1;
            state.reset_time_s = t_s;
        end
        state.in_shutdown = true;
        state.cnv_id = -1;
        state.cnv_count = 0;
        state.slot_time_s = NaN;
        state.slot_target_id = -2;
        state.slot_word = 0;
        state.slot_mode = 0;
        state.tx_active = false;
        state.data_bit_index = -1;
        state.data_bit = 0;
        state.preamble_seen = false;
        state.slot_clock_error = false;
        state.last_complete_ordinal = 0;
        state.resync_required = false;
        state.cache = empty_cache(cfg.cache_depth);
        state.active_source_epoch = state.epoch;
        state.sample_history_id = -ones(1, cfg.history_depth);
        state.sample_history_time_s = NaN(1, cfg.history_depth);
        state.sample_history_next = 1;
        state.prev_cnv = cnv;
        state.prev_clk = clk;
        state.prev_en = en;
        y.debug = debug;
        y.debug.mode = 0;
        y.debug.epoch = state.epoch;
        y.debug.reset = 1;
        return
    end

    state.in_shutdown = false;
    cnv_rise = state.prev_cnv == 0 && cnv == 1;
    clk_rise = state.prev_clk == 0 && clk == 1;
    clk_fall = state.prev_clk == 1 && clk == 0;
    debug.cnv_rise = double(cnv_rise);
    debug.clk_rise = double(clk_rise);
    debug.clk_fall = double(clk_fall);

    % Cache a committed record before a same-tick CNV snapshot so an exactly
    % boundary-aligned input can be considered with its actual commit timestamp.
    [state, debug] = ingest_record(state, record, t_s, cfg, debug);

    if cnv_rise
        if isfinite(state.slot_time_s) && ...
                t_s - state.slot_time_s < cfg.sample_period_s - cfg.time_tolerance_s
            error('sar20:lvdsTx:cnvInterval', ...
                  'CNV rising edges must be separated by at least sample_period_s.');
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
        [state, alias_evicted] = push_sample_time(state, state.cnv_id, t_s, cfg);
        debug.cache_alias_evicted = double(alias_evicted);
        state.slot_mode = mode;
        state.tx_active = false;
        state.data_bit_index = -1;
        state.data_bit = 0;
        state.preamble_seen = false;
        state.slot_clock_error = false;
        state.slot_word = 0;
        if state.cnv_count <= cfg.latency_samples
            state.slot_target_id = state.cnv_id - cfg.latency_samples;
        else
            state.slot_target_id = mod(state.cnv_id - cfg.latency_samples, cfg.counter_modulus);
        end
        debug.new_slot = 1;
        debug.slot_id = state.cnv_id;
        debug.target_sample_id = state.slot_target_id;

        if state.resync_required
            state.slot_word = 0;
            state.tx_active = true;
            debug.guard_invalid = 1;
        elseif mode == 1
            [state, state.slot_word, found, late, stale] = snapshot_record( ...
                                                                           state, state.slot_target_id, t_s, cfg);
            state.tx_active = true;
            debug.record_found = double(found);
            debug.late_snapshot = double(late);
            debug.stale_cache_reject = double(stale);
        elseif mode == 2
            state.slot_word = cfg.test_word;
            state.tx_active = true;
            debug.record_found = 0;
        end
        debug.snapshot_word = state.slot_word;
        debug.frame_active = double(state.tx_active);
        debug.resync_required = double(state.resync_required);
    end

    % Invalid nonzero EN disables the pads and cancels this burst without
    % changing the CNV counter or epoch.  Returning to a valid EN cannot replay a
    % partial frame; a new CNV is needed to establish a new slot word.
    if mode ~= 1 && mode ~= 2
        state.tx_active = false;
        state.data_bit = 0;
    end
    if state.tx_active && mode ~= state.slot_mode
        state.tx_active = false;
        state.data_bit = 0;
    end

    if clk_rise && state.tx_active && isfinite(state.slot_time_s) && ...
            mode == state.slot_mode
        rel_s = t_s - state.slot_time_s;
        if abs(rel_s - cfg.preamble_rise_s) <= cfg.edge_tolerance_s
            state.preamble_seen = true;
            debug.preamble_seen = 1;
        else
            rise_position = (rel_s - (cfg.first_data_fall_s + cfg.clk_period_s / 2)) / cfg.clk_period_s;
            rise_index = round(rise_position);
            is_capture_rise = rise_index >= 0 && rise_index < cfg.frame_bits && ...
                abs(rise_position - rise_index) <= cfg.edge_tolerance_s / cfg.clk_period_s;
            if rel_s >= 0 && rel_s <= cfg.final_fall_s + cfg.edge_tolerance_s && ~is_capture_rise
                state.slot_clock_error = true;
                debug.clock_sequence_error = 1;
            end
        end
    end

    if clk_fall && state.tx_active && isfinite(state.slot_time_s)
        rel_s = t_s - state.slot_time_s;
        tol = cfg.edge_tolerance_s;
        if abs(rel_s - cfg.final_fall_s) <= tol
            if state.data_bit_index == cfg.frame_bits - 1 && state.preamble_seen && ...
                    ~state.slot_clock_error
                state.last_complete_ordinal = state.cnv_count;
                debug.slot_transfer_complete = 1;
            else
                state.slot_clock_error = true;
                debug.clock_sequence_error = 1;
            end
            state.data_bit = 0;
            state.data_bit_index = 32;
            state.tx_active = false;
            debug.final_fall = 1;
        else
            bit_position = (rel_s - cfg.first_data_fall_s) / cfg.clk_period_s;
            bit_index = round(bit_position);
            on_data_fall = bit_index >= 0 && bit_index < cfg.frame_bits && ...
                abs(bit_position - bit_index) <= tol / cfg.clk_period_s;
            if on_data_fall
                if bit_index == 0 && ~state.preamble_seen
                    debug.clock_sequence_error = 1;
                    state.slot_clock_error = true;
                end
                if bit_index ~= state.data_bit_index + 1
                    debug.clock_sequence_error = 1;
                    state.slot_clock_error = true;
                end
                state.data_bit_index = bit_index;
                state.data_bit = bit_at(state.slot_word, bit_index, cfg.frame_bits);
                debug.launched_bit = state.data_bit;
                debug.bit_index = bit_index;
                debug.launch_count = debug.launch_count + 1;
            elseif rel_s >= cfg.preamble_rise_s - tol && rel_s < cfg.first_data_fall_s - tol
                debug.clock_sequence_error = 1;
                state.slot_clock_error = true;
            elseif rel_s >= cfg.first_data_fall_s - tol && rel_s <= cfg.final_fall_s + tol
                debug.clock_sequence_error = 1;
                state.slot_clock_error = true;
            end
        end
    end

    oe = (mode == 1 || mode == 2);
    y.oe = double(oe);
    if oe
        y.dco_p = clk;
        y.dco_n = 1 - clk;
        y.d_p = state.data_bit;
        y.d_n = 1 - state.data_bit;
    end
    y.debug = debug;
    y.debug.mode = mode;
    y.debug.epoch = state.epoch;
    y.debug.slot_id = state.cnv_id;
    y.debug.target_sample_id = state.slot_target_id;
    y.debug.snapshot_word = state.slot_word;
    y.debug.frame_active = double(state.tx_active);
    y.debug.resync_required = double(state.resync_required);
    y.debug.slot_clock_error = double(state.slot_clock_error);

    state.prev_cnv = cnv;
    state.prev_clk = clk;
    state.prev_en = en;
end

function [state, debug] = ingest_record(state, r, t_s, cfg, debug)
    record_fields = {'raw_D1', 'raw_D2', 'raw_DT', 'valid', 'sample_id', 'epoch', 'commit_time_s'};
    if isempty(r)
        return
    end
    if ~isstruct(r) || ~isscalar(r) || ~all(isfield(r, record_fields)) || ...
            numel(fieldnames(r)) ~= numel(record_fields)
        error('sar20:lvdsTx:record', 'record must contain exactly the seven committed-record fields.');
    end
    id = double(r.sample_id);
    epoch = double(r.epoch);
    commit_time_s = double(r.commit_time_s);
    if isscalar(id) && isfinite(id) && id == -1
        return
    end
    if ~isscalar(id) || ~isfinite(id) || id < 0 || id ~= floor(id) || ...
            id >= cfg.counter_modulus || ~isscalar(epoch) || ~isfinite(epoch) || ...
            epoch ~= floor(epoch) || ~isscalar(commit_time_s) || ~isfinite(commit_time_s)
        debug.bad_record = 1;
        return
    end
    word = pack_word(r, cfg);
    valid = double(r.valid ~= 0);
    if state.cnv_id < 0 || isnan(state.slot_time_s)
        debug.record_before_first_cnv = 1;
        return
    end
    if commit_time_s < state.reset_time_s - cfg.time_tolerance_s
        debug.reset_epoch_reject = 1;
        return
    end
    if commit_time_s > t_s + cfg.time_tolerance_s
        debug.future_commit_reject = 1;
        return
    end
    sample_time_s = latest_sample_time(state, id);
    if ~isfinite(sample_time_s)
        debug.unknown_sample_time_reject = 1;
        return
    end
    if commit_time_s < sample_time_s - cfg.time_tolerance_s
        debug.stale_record_reject = 1;
        return
    end

    % Only current/recently converted IDs can be committed.  The setup deadline
    % is checked against the actual CNV edge at the atomic snapshot below; this
    % also handles a stopped/irregular CNV calendar without predicting its phase.
    age = mod(state.cnv_id - id, cfg.counter_modulus);
    if age >= cfg.latency_samples || age >= cfg.counter_modulus / 2
        debug.stale_or_future_reject = 1;
        return
    end

    if epoch ~= state.active_source_epoch
        debug.wrong_epoch_reject = 1;
        return
    end

    same = find([state.cache.sample_id] == id & [state.cache.epoch] == epoch, 1);
    if ~isempty(same)
        prior = state.cache(same);
        if prior.commit_time_s == commit_time_s && prior.word == word && prior.valid == valid
            return  % Same held record level, not a second commit event.
        end
        debug.duplicate_commit_reject = 1;
        return
    end

    empty = find([state.cache.sample_id] < 0, 1);
    if isempty(empty)
        % A bounded cache is enough for the fixed two-sample latency.  If an
        % upstream source violates that contract, evict the oldest item and make
        % the loss visible instead of silently replacing a newer entry.
        [~, empty] = min([state.cache.commit_time_s]);
        debug.cache_overwrite = 1;
    end
    state.cache(empty) = struct('sample_id', id, 'epoch', epoch, ...
                                'commit_time_s', commit_time_s, 'word', word, 'valid', valid);
    debug.record_cached = 1;
end

function [state, word, found, late, stale] = snapshot_record(state, target_id, slot_time_s, cfg)
    word = 0;
    found = false;
    late = false;
    stale = false;
    if target_id < 0
        return
    end
    if state.active_source_epoch < 0
        return
    end
    for k = 1:numel(state.cache)
        r = state.cache(k);
        if r.sample_id == target_id && r.epoch == state.active_source_epoch
            sample_time_s = latest_sample_time(state, target_id);
            if isfinite(sample_time_s) && r.commit_time_s < sample_time_s - cfg.time_tolerance_s
                stale = true;
                state.cache(k) = empty_cache_entry();
            elseif r.commit_time_s <= slot_time_s - cfg.bundle_setup_s + cfg.time_tolerance_s
                found = true;
                if r.valid ~= 0
                    word = r.word;
                end
            else
                late = true;
                state.cache(k) = struct('sample_id', -1, 'epoch', -1, ...
                                        'commit_time_s', Inf, 'word', 0, 'valid', 0);
            end
            return
        end
    end
end

function [state, evicted] = push_sample_time(state, id, time_s, cfg)
    evicted = false;
    % A uint32 ID can recur after wrap.  Drop an ancient same-ID cache entry when
    % the corresponding new source sample is observed, so modulo tags never
    % resurrect a record from a previous 2^32-slot cycle.
    for k = 1:numel(state.cache)
        if state.cache(k).sample_id == id && ...
                state.cache(k).commit_time_s < time_s - cfg.time_tolerance_s
            state.cache(k) = empty_cache_entry();
            evicted = true;
        end
    end
    state.sample_history_id(state.sample_history_next) = id;
    state.sample_history_time_s(state.sample_history_next) = time_s;
    state.sample_history_next = state.sample_history_next + 1;
    if state.sample_history_next > cfg.history_depth
        state.sample_history_next = 1;
    end
end

function time_s = latest_sample_time(state, id)
    matches = state.sample_history_id == id & isfinite(state.sample_history_time_s);
    if any(matches)
        time_s = max(state.sample_history_time_s(matches));
    else
        time_s = NaN;
    end
end

function e = empty_cache_entry()
    e = struct('sample_id', -1, 'epoch', -1, 'commit_time_s', Inf, 'word', 0, 'valid', 0);
end

function word = pack_word(r, cfg)
    d1 = bounded_integer(r.raw_D1, 0, 2^11 - 1, 'raw_D1');
    d2 = bounded_integer(r.raw_D2, 0, 2^12 - 1, 'raw_D2');
    dt = bounded_integer(r.raw_DT, 0, 2^8 - 1, 'raw_DT');
    if ~isscalar(r.valid) || ~isnumeric(r.valid) || ~isreal(r.valid) || ...
            ~isfinite(r.valid) || ~(r.valid == 0 || r.valid == 1)
        error('sar20:lvdsTx:recordField', 'valid must be the binary value 0 or 1.');
    end
    valid = double(r.valid ~= 0);
    word = d1 * 2^21 + d2 * 2^9 + dt * 2 + valid;
    if word < 0 || word >= 2^cfg.frame_bits
        error('sar20:lvdsTx:word', 'Packed frame is outside 32 bits.');
    end
end

function v = bounded_integer(v, lo, hi, name)
    if ~isnumeric(v) || ~isreal(v) || ~isscalar(v) || ~isfinite(v) || ...
            v ~= floor(v) || v < lo || v > hi
        error('sar20:lvdsTx:recordField', '%s must be an integer in [%d,%d].', name, lo, hi);
    end
    v = double(v);
end

function b = bit_at(word, index, width)
    b = mod(floor(word / 2^(width - 1 - index)), 2);
end

function mode = en_mode(en)
    if ~isscalar(en) || ~isnumeric(en) || ~isreal(en) || ~isfinite(en) || ...
            en ~= floor(en) || en < 0 || en > 15
        error('sar20:lvdsTx:en', 'EN must be a four-bit integer.');
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
    required = {'cnv', 'clk', 'en', 'record'};
    if ~isstruct(u) || ~isscalar(u) || ~all(isfield(u, required)) || ...
            numel(fieldnames(u)) ~= numel(required)
        error('sar20:lvdsTx:input', 'u must contain exactly cnv, clk, en, and record.');
    end
    for name = {'cnv', 'clk'}
        v = u.(name{1});
        if ~(isnumeric(v) || islogical(v)) || ~isreal(v) || ~isscalar(v) || ~isfinite(v)
            error('sar20:lvdsTx:inputLevel', '%s must be a finite scalar level.', name{1});
        end
    end
end

function check_state(s)
    required = {'initialized', 'prev_cnv', 'prev_clk', 'prev_en', 'in_shutdown', ...
                'epoch', 'reset_time_s', 'cnv_id', 'cnv_count', 'slot_time_s', 'slot_target_id', ...
                'slot_word', 'slot_mode', 'tx_active', 'data_bit_index', 'data_bit', 'cache', ...
                'active_source_epoch', 'sample_history_id', ...
                'sample_history_time_s', 'sample_history_next', 'preamble_seen', ...
                'slot_clock_error', 'last_complete_ordinal', 'resync_required'};
    if ~isstruct(s) || ~all(isfield(s, required)) || s.initialized ~= 1
        error('sar20:lvdsTx:state', 'state must be empty or a state returned by this function.');
    end
end

function s = initial_state(cache_depth, history_depth)
    s = struct();
    s.initialized = 1;
    s.prev_cnv = 0;
    s.prev_clk = 0;
    s.prev_en = -1;
    s.in_shutdown = false;
    s.epoch = 0;
    s.reset_time_s = -Inf;
    s.cnv_id = -1;
    s.cnv_count = 0;
    s.slot_time_s = NaN;
    s.slot_target_id = -2;
    s.slot_word = 0;
    s.slot_mode = 3;
    s.tx_active = false;
    s.data_bit_index = -1;
    s.data_bit = 0;
    s.preamble_seen = false;
    s.slot_clock_error = false;
    s.last_complete_ordinal = 0;
    s.resync_required = false;
    s.cache = empty_cache(cache_depth);
    s.active_source_epoch = 0;
    s.sample_history_id = -ones(1, history_depth);
    s.sample_history_time_s = NaN(1, history_depth);
    s.sample_history_next = 1;
end

function c = empty_cache(n)
    entry = struct('sample_id', -1, 'epoch', -1, 'commit_time_s', Inf, 'word', 0, 'valid', 0);
    c = repmat(entry, 1, n);
end

function y = output_template()
    y = struct();
    y.d_p = 0;
    y.d_n = 0;
    y.dco_p = 0;
    y.dco_n = 0;
    y.oe = 0;
    y.debug = struct('mode', 3, 'epoch', 0, 'cnv_rise', 0, ...
                     'clk_rise', 0, 'clk_fall', 0, 'new_slot', 0, 'slot_id', -1, ...
                     'target_sample_id', -2, 'snapshot_word', 0, 'record_found', 0, ...
                     'record_cached', 0, 'record_before_first_cnv', 0, 'bad_record', 0, ...
                     'late_commit_reject', 0, 'late_snapshot', 0, 'future_commit_reject', 0, ...
                     'wrong_epoch_reject', 0, 'reset_epoch_reject', 0, ...
                     'stale_or_future_reject', 0, 'duplicate_commit_reject', 0, ...
                     'cache_overwrite', 0, 'unknown_sample_time_reject', 0, ...
                     'stale_record_reject', 0, 'stale_cache_reject', 0, ...
                     'cache_alias_evicted', 0, 'counter_wrapped', 0, ...
                     'frame_active', 0, 'preamble_seen', 0, 'bit_index', -1, ...
                     'launched_bit', 0, 'launch_count', 0, 'final_fall', 0, ...
                     'clock_sequence_error', 0, 'slot_clock_error', 0, ...
                     'slot_transfer_complete', 0, 'guard_invalid', 0, ...
                     'resync_required', 0, 'reset', 0);
end

function cfg = tx_defaults(cfg)
    if nargin == 0 || isempty(cfg)
        cfg = struct();
    end
    if ~isstruct(cfg) || ~isscalar(cfg)
        error('sar20:lvdsTx:config', 'cfg must be a scalar struct.');
    end
    defaults = struct('sample_period_s', 200e-9, 'clk_period_s', 4e-9, ...
                      'bundle_setup_s', 10e-9, 'preamble_rise_s', 8e-9, ...
                      'first_data_fall_s', 10e-9, 'final_fall_s', 138e-9, ...
                      'frame_bits', 32, 'latency_samples', 2, 'counter_modulus', 2^32, ...
                      'test_word', hex2dec('A55A5AA5'), 'cache_depth', 4, ...
                      'time_tolerance_s', 1e-15, 'edge_tolerance_s', 1e-12, 'history_depth', 4);
    names = fieldnames(defaults);
    for k = 1:numel(names)
        if ~isfield(cfg, names{k})
            cfg.(names{k}) = defaults.(names{k});
        end
    end
end
