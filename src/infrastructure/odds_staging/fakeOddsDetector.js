'use strict';

// lifecycle: permanent；离线批次中的异常1X2与跨比赛重复赔率向量检测。

const { appendObservationSignals, stableStringify } = require('./contracts');

const DEFAULT_FAKE_ODDS_CONFIG = Object.freeze({
    implied_probability_min: 0.8,
    implied_probability_max: 1.35,
    repeated_vector_min_distinct_matches: 2,
    quarantine_repeated_vectors: false,
});

// 已知旧限制（本轮如实保留、不修复）：source_match_id=null 时同一 bookmaker 的多行仍会
// 落入同一 group，使单场 1X2 隐含概率检测退化为跳过；当前历史数据全部 quarantine，该
// 限制不影响接受结果，留待显式授权的身份重构轮次处理。
function groupKey(observation) {
    return stableStringify({
        source_provider: observation.source_provider,
        source_match_id: observation.source_match_id,
        bookmaker: observation.bookmaker,
        market: observation.market,
        snapshot_type: observation.snapshot_type,
        source_observed_at: observation.source_observed_at,
        // source-native quote series 是独立报价序列：B365 与 B365C 必须分别检测；
        // 缺失该字段的旧 observation 统一归入 null，分组行为与既有版本一致。
        source_quote_series: observation.source_quote_series ?? null,
    });
}

function completeOneXTwoVector(group) {
    const bySelection = new Map();
    for (const entry of group) {
        if (!['home', 'draw', 'away'].includes(entry.selection)) {
            return null;
        }
        const decimalOdds = Number(entry.decimal_odds);
        if (!Number.isFinite(decimalOdds) || decimalOdds <= 1) {
            return null;
        }
        if (bySelection.has(entry.selection)) {
            // 同一 selection 的完全相同重复（如 uppercase 与 snake_case 同值列）折叠为同一表示，
            // 不得使守卫失效；数值冲突则不可判定：不任选其一，交由下游 semantic conflict fail-closed。
            if (bySelection.get(entry.selection) === decimalOdds) {
                continue;
            }
            return null;
        }
        bySelection.set(entry.selection, decimalOdds);
    }
    if (bySelection.size !== 3) {
        return null;
    }
    return {
        home: bySelection.get('home'),
        draw: bySelection.get('draw'),
        away: bySelection.get('away'),
    };
}

function collectOneXTwoGroups(observations) {
    const groups = new Map();
    observations.forEach((observation, index) => {
        if (observation.market !== '1X2') {
            return;
        }
        const key = groupKey(observation);
        if (!groups.has(key)) {
            groups.set(key, []);
        }
        groups.get(key).push({ observation, index });
    });
    return groups;
}

function addSignal(signalMap, index, signal) {
    if (!signalMap.has(index)) {
        signalMap.set(index, new Set());
    }
    signalMap.get(index).add(signal);
}

function detectFakeOdds(observations = [], options = {}) {
    const config = { ...DEFAULT_FAKE_ODDS_CONFIG, ...options };
    const reasonMap = new Map();
    const flagMap = new Map();
    const completeVectors = [];
    const groups = collectOneXTwoGroups(observations);

    for (const entries of groups.values()) {
        const vector = completeOneXTwoVector(entries.map(entry => entry.observation));
        if (!vector) {
            continue;
        }
        const impliedProbability = 1 / vector.home + 1 / vector.draw + 1 / vector.away;
        if (
            impliedProbability < config.implied_probability_min ||
            impliedProbability > config.implied_probability_max
        ) {
            for (const entry of entries) {
                addSignal(reasonMap, entry.index, 'one_x_two_implied_probability_out_of_bounds');
            }
        }
        completeVectors.push({ entries, vector });
    }

    const repeatedVectors = new Map();
    for (const complete of completeVectors) {
        const first = complete.entries[0].observation;
        if (!first.source_match_id) {
            continue;
        }
        const key = stableStringify({
            source_provider: first.source_provider,
            bookmaker: first.bookmaker,
            market: first.market,
            snapshot_type: first.snapshot_type,
            // 跨比赛重复向量同样按 series 隔离：不同 series 偶合相同向量不得互相制造标记。
            source_quote_series: first.source_quote_series ?? null,
            vector: complete.vector,
        });
        if (!repeatedVectors.has(key)) {
            repeatedVectors.set(key, []);
        }
        repeatedVectors.get(key).push(complete);
    }

    for (const vectors of repeatedVectors.values()) {
        const sourceMatchIds = new Set(vectors.map(vector => vector.entries[0].observation.source_match_id));
        if (sourceMatchIds.size < config.repeated_vector_min_distinct_matches) {
            continue;
        }
        for (const vector of vectors) {
            for (const entry of vector.entries) {
                addSignal(flagMap, entry.index, 'repeated_one_x_two_vector_across_source_matches');
                if (config.quarantine_repeated_vectors === true) {
                    addSignal(reasonMap, entry.index, 'repeated_one_x_two_vector_across_source_matches');
                }
            }
        }
    }

    return observations.map((observation, index) => {
        const reasons = [...(reasonMap.get(index) || [])];
        const flags = [...(flagMap.get(index) || [])];
        return reasons.length === 0 && flags.length === 0
            ? observation
            : appendObservationSignals(observation, reasons, flags);
    });
}

module.exports = {
    DEFAULT_FAKE_ODDS_CONFIG,
    detectFakeOdds,
};
