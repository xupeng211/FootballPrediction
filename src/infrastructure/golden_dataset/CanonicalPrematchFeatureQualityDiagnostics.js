'use strict';

// lifecycle: permanent；仅诊断来源绑定的 canonical frame，不定义特征或修复数据。
const { sha256Text, stableStringify } = require('../canonical/StableValue');
const { sha256Bytes } = require('./GdA01AssemblyContract');
const { validateFrameAgainstInputs } = require('./CanonicalPrematchFeatureFrameContract');

const INTERPRETATION = '受影响比赛数不等于修复后可新增训练样本数；多问题可重叠，标签或其他特征仍可能阻断。常量、全零及 IQR 离群仅为调查线索，不自动判错、填补或排除。';
const compareText = (a, b) => a < b ? -1 : a > b ? 1 : 0;
const unique = values => [...new Set(values)].sort(compareText);
const copy = value => JSON.parse(JSON.stringify(value));

function quantile(sorted, fraction) {
    if (!sorted.length) return null;
    const index = (sorted.length - 1) * fraction;
    const low = Math.floor(index);
    const weight = index - low;
    return sorted[low] * (1 - weight) + sorted[Math.ceil(index)] * weight;
}

function numericQuality(observations) {
    const values = observations.map(item => item.value).sort((a, b) => a - b);
    const count = values.length;
    const mean = count ? values.reduce((sum, value) => sum + value / count, 0) : null;
    const variance = count ? values.reduce((sum, value) => sum + ((value - mean) ** 2) / count, 0) : null;
    const q1 = quantile(values, 0.25);
    const q3 = quantile(values, 0.75);
    const iqr = count ? q3 - q1 : null;
    const lower = count >= 4 ? q1 - 1.5 * iqr : null;
    const upper = count >= 4 ? q3 + 1.5 * iqr : null;
    const outliers = count >= 4 ? observations.filter(item => item.value < lower || item.value > upper) : [];
    return {
        observation_count: count,
        distinct_value_count: new Set(values).size,
        zero_count: values.filter(value => value === 0).length,
        min: count ? values[0] : null,
        max: count ? values[count - 1] : null,
        mean,
        population_standard_deviation: count ? Math.sqrt(variance) : null,
        q1, median: quantile(values, 0.5), q3,
        constant: count >= 2 && values[0] === values[count - 1],
        all_zero: count >= 2 && values.every(value => value === 0),
        insufficient_observations: count < 2,
        iqr_outliers: {
            method: 'LINEAR_QUANTILES_1.5_IQR_STRICT_FENCES_MIN_N_4',
            lower_fence: lower, upper_fence: upper,
            count: outliers.length, locations: outliers,
        },
    };
}

function summarizeReasons(locations) {
    const groups = new Map();
    for (const location of locations) {
        const key = stableStringify([location.kind, location.reason_code]);
        if (!groups.has(key)) groups.set(key, { kind: location.kind, reason_code: location.reason_code, locations: [] });
        groups.get(key).locations.push(location);
    }
    return [...groups.values()].sort((a, b) => compareText(stableStringify([a.kind, a.reason_code]), stableStringify([b.kind, b.reason_code])))
        .map(group => ({
            ...group,
            reason_hit_count: group.locations.length,
            affected_match_count: unique(group.locations.map(item => item.canonical_match_id)).length,
            match_ids: unique(group.locations.map(item => item.canonical_match_id)),
            feature_names: unique(group.locations.map(item => item.feature_name).filter(Boolean)),
        }));
}

// 完整集合的组合分区（不是所有子集）；每场在一个组合中只出现一次。
function reasonCombinations(rows, locations) {
    const byMatch = new Map(rows.map(row => [row.canonical_match_id, []]));
    for (const item of locations) byMatch.get(item.canonical_match_id).push(stableStringify([item.kind, item.reason_code]));
    const groups = new Map();
    for (const [id, reasons] of byMatch) {
        const keys = unique(reasons);
        if (!keys.length) continue;
        const key = stableStringify(keys);
        if (!groups.has(key)) groups.set(key, { reasons: keys.map(value => JSON.parse(value)), match_ids: [] });
        groups.get(key).match_ids.push(id);
    }
    return [...groups.entries()].sort(([a], [b]) => compareText(a, b)).map(([, group]) => ({
        ...group, affected_match_count: group.match_ids.length,
    }));
}

function featureSummary(name, rows, reasons) {
    const available = rows.filter(row => row.features[name].availability_status === 'AVAILABLE');
    const observations = available.map(row => ({ canonical_match_id: row.canonical_match_id, feature_name: name, value: row.features[name].value }));
    const missing = rows.length - available.length;
    return {
        feature_name: name,
        valid_count: available.length,
        missing_count: missing,
        missing_rate: rows.length ? missing / rows.length : null,
        missing_match_ids: rows.filter(row => row.features[name].availability_status === 'UNAVAILABLE').map(row => row.canonical_match_id),
        unavailable_reasons: summarizeReasons(reasons.filter(item => item.feature_name === name)),
        numeric_quality: numericQuality(observations),
    };
}

function investigationPriorities(features, reasonSummary, rows) {
    const issues = reasonSummary.map(reason => ({
        issue_id: stableStringify([reason.kind, reason.reason_code]),
        type: reason.kind, reason_code: reason.reason_code,
        evidence: { reason_hit_count: reason.reason_hit_count },
        locations: reason.locations,
    }));
    for (const feature of features) {
        const quality = feature.numeric_quality;
        const available = rows.filter(row => row.features[feature.feature_name].availability_status === 'AVAILABLE')
            .map(row => ({ canonical_match_id: row.canonical_match_id, feature_name: feature.feature_name, value: row.features[feature.feature_name].value }));
        for (const [flag, active, locations] of [
            ['CONSTANT', quality.constant, available],
            ['ALL_ZERO', quality.all_zero, available],
            ['IQR_OUTLIER', quality.iqr_outliers.count > 0, quality.iqr_outliers.locations],
        ]) {
            if (active) {
                issues.push({
                    issue_id: stableStringify([flag, feature.feature_name]), type: flag,
                    reason_code: null, feature_name: feature.feature_name,
                    evidence: copy(quality), locations,
                });
            }
        }
    }
    const eligibleIds = new Set(rows.filter(row => row.training_eligibility.status === 'ELIGIBLE').map(row => row.canonical_match_id));
    return issues.map(issue => {
        const ids = unique(issue.locations.map(item => item.canonical_match_id));
        const eligible = ids.filter(id => eligibleIds.has(id)).length;
        return {
            ...issue, affected_match_count: ids.length, match_ids: ids,
            affected_eligible_match_count: eligible, affected_ineligible_match_count: ids.length - eligible,
            feature_names: unique(issue.locations.map(item => item.feature_name).filter(Boolean)),
        };
    }).sort((a, b) => b.affected_match_count - a.affected_match_count || compareText(a.issue_id, b.issue_id))
        .map((issue, index) => ({ rank: index + 1, ...issue }));
}

function buildQualityDiagnostics(inputs) {
    // 不接受仅自洽 hash 的 frame：沿用 frame 的逐字节重投影、registry、provenance 与 leakage 校验。
    const { artifact, receipt } = validateFrameAgainstInputs(inputs);
    const rows = [...artifact.rows].sort((a, b) => compareText(a.canonical_match_id, b.canonical_match_id));
    const order = artifact.feature_contract.training_feature_order;
    const locations = [];
    const eligibilityLocations = [];
    for (const row of rows) {
        for (const name of order) {
            const line = row.features[name];
            if (line.availability_status === 'UNAVAILABLE') {
                for (const reason of unique(line.unavailable_reason_codes)) {
                    locations.push({
                        canonical_match_id: row.canonical_match_id, feature_name: name,
                        kind: 'FEATURE_UNAVAILABLE', reason_code: reason,
                    });
                }
            }
        }
        if (row.target_label.status !== 'AVAILABLE') {
            locations.push({
                canonical_match_id: row.canonical_match_id, feature_name: null,
                kind: 'TARGET_LABEL_UNAVAILABLE', reason_code: 'TARGET_LABEL_UNAVAILABLE',
            });
        }
        for (const reason of unique(row.training_eligibility.reason_codes)) {
            eligibilityLocations.push({
                canonical_match_id: row.canonical_match_id, feature_name: null,
                kind: 'TRAINING_ELIGIBILITY', reason_code: reason,
            });
        }
    }
    const features = order.map(name => featureSummary(name, rows, locations));
    const reasons = summarizeReasons(locations);
    const priorities = investigationPriorities(features, reasons, rows);
    const report = {
        schema_version: 'canonical-prematch-feature-quality-diagnostics/v1',
        code_revision: receipt.code_revision,
        input_binding: {
            frame_artifact_sha256: sha256Bytes(inputs.artifactBytes),
            frame_receipt_sha256: sha256Bytes(inputs.receiptBytes),
            frame_business_sha256: artifact.business_content_sha256,
            source_bindings: copy(artifact.source_bindings),
        },
        feature_contract: copy(artifact.feature_contract),
        temporal_boundary: {
            feature_cutoff_policy: artifact.feature_cutoff_policy,
            feature_as_of_status: artifact.feature_as_of_status,
            model_decision_time_status: artifact.model_decision_time_status,
            real_decision_time_availability: 'NOT_PROVEN',
        },
        interpretation: INTERPRETATION,
        counting_policy: '原因命中按不同比赛/特征/原因计数，标签单列；组合为每场完整去重原因集合；各优先项影响数不可相加。数值统计覆盖全部 accounted 行的 AVAILABLE 有限数值，合法零值计入。',
        population_accounting: copy(artifact.population_accounting),
        eligibility: {
            eligible_match_ids: rows.filter(row => row.training_eligibility.status === 'ELIGIBLE').map(row => row.canonical_match_id),
            ineligible_match_ids: rows.filter(row => row.training_eligibility.status === 'INELIGIBLE').map(row => row.canonical_match_id),
            reason_summary: summarizeReasons(eligibilityLocations),
            reason_combinations: reasonCombinations(rows, eligibilityLocations),
        },
        features,
        non_selected_features: artifact.feature_decisions.filter(item => item.final_decision !== 'ACCEPTED_FOR_TRAINING')
            .map(item => ({ feature_name: item.feature_name, final_decision: item.final_decision, reason_code: item.reason_code })),
        unavailability: {
            reason_hit_count: locations.length,
            affected_match_count: unique(locations.map(item => item.canonical_match_id)).length,
            reason_summary: reasons,
            reason_combinations: reasonCombinations(rows, locations),
        },
        investigation: {
            ranking_policy: '按每项受影响的不同比赛数降序；同数按稳定 issue_id 排序；无恢复样本数估计。',
            affected_match_count: unique(priorities.flatMap(item => item.match_ids)).length,
            priorities,
        },
        match_diagnostics: rows.map(row => ({
            ...copy(row.target_match_identity), target_kickoff_utc: row.target_kickoff_utc,
            training_eligibility: copy(row.training_eligibility),
            unavailable_locations: locations.filter(item => item.canonical_match_id === row.canonical_match_id),
            investigation_issue_ids: priorities.filter(item => item.match_ids.includes(row.canonical_match_id)).map(item => item.issue_id),
        })),
    };
    report.business_content_sha256 = sha256Text(stableStringify(report));
    return { report, jsonBytes: Buffer.from(`${JSON.stringify(report, null, 2)}\n`), markdownBytes: Buffer.from(renderQualityMarkdown(report)) };
}

function cell(value) {
    return String(value ?? '无').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/\|/g, '&#124;').replace(/`/g, '&#96;').replace(/[\r\n]/g, ' ');
}

function renderQualityMarkdown(report) {
    const population = report.population_accounting;
    const lines = [
        '# Canonical 赛前特征质量诊断', '',
        `代码版本：${report.code_revision}；业务摘要：${report.business_content_sha256}`, '',
        `Frame SHA-256：${report.input_binding.frame_artifact_sha256}；receipt SHA-256：${report.input_binding.frame_receipt_sha256}`, '',
        `覆盖 ${population.rows_accounted} 场不同比赛；eligible ${population.training_eligible} 场；ineligible ${population.training_ineligible} 场。`, '',
        `时点边界：${report.temporal_boundary.feature_as_of_status}；${report.temporal_boundary.model_decision_time_status}；真实决策时点可用性未证明。`, '',
        report.interpretation, '', report.counting_policy, '',
        '## 获准特征（全部 accounted 比赛）', '',
        '| 特征 | 有效 | 缺失 | 缺失率 | 零值 | 不同值 | 最小 / 最大 | 均值 / 总体标准差 | Q1 / 中位数 / Q3 | 常量 / 全零 |',
        '|---|---:|---:|---:|---:|---:|---|---|---|---|',
    ];
    for (const feature of report.features) {
        const q = feature.numeric_quality;
        lines.push(`| ${cell(feature.feature_name)} | ${feature.valid_count} | ${feature.missing_count} | ${cell(feature.missing_rate)} | ${q.zero_count} | ${q.distinct_value_count} | ${cell(q.min)} / ${cell(q.max)} | ${cell(q.mean)} / ${cell(q.population_standard_deviation)} | ${cell(q.q1)} / ${cell(q.median)} / ${cell(q.q3)} | ${q.constant} / ${q.all_zero} |`);
    }
    lines.push('', '## Registry 排除或阻断（不做数值诊断）', '', '| 特征 | 决策 | 既有理由 |', '|---|---|---|');
    for (const item of report.non_selected_features) lines.push(`| ${cell(item.feature_name)} | ${cell(item.final_decision)} | ${cell(item.reason_code)} |`);
    lines.push('', '## 不可用原因与共同出现', '', `原因命中 ${report.unavailability.reason_hit_count} 次，影响 ${report.unavailability.affected_match_count} 场不同比赛。`, '', '| 类型 / 原因 | 命中次数 | 不同比赛 | 特征 | 比赛 ID |', '|---|---:|---:|---|---|');
    for (const item of report.unavailability.reason_summary) lines.push(`| ${cell(item.kind)} / ${cell(item.reason_code)} | ${item.reason_hit_count} | ${item.affected_match_count} | ${cell(item.feature_names.join(', '))} | ${cell(item.match_ids.join(', '))} |`);
    for (const [label, combinations] of [
        ['完整不可用原因组合', report.unavailability.reason_combinations],
        ['完整 eligibility 原因组合', report.eligibility.reason_combinations],
    ]) {
        lines.push('', `### ${label}`, '', '| 完整原因集合 | 不同比赛 | 比赛 ID |', '|---|---:|---|');
        for (const group of combinations) lines.push(`| ${cell(group.reasons.map(reason => reason.join(':')).join(' + '))} | ${group.affected_match_count} | ${cell(group.match_ids.join(', '))} |`);
    }
    lines.push('', '## 调查优先级与直接依据', '', report.investigation.ranking_policy, '', `所有调查项合计去重影响 ${report.investigation.affected_match_count} 场。`, '');
    for (const issue of report.investigation.priorities) {
        lines.push(`### ${issue.rank}. ${cell(issue.type)} / ${cell(issue.reason_code || issue.feature_name)}`, '',
            `影响 ${issue.affected_match_count} 场（eligible ${issue.affected_eligible_match_count}；ineligible ${issue.affected_ineligible_match_count}）。`, '',
            `依据：${cell(JSON.stringify(issue.evidence))}`, '',
            '| 比赛 ID | 特征 | 原因或观测值 |', '|---|---|---|');
        for (const location of issue.locations) lines.push(`| ${cell(location.canonical_match_id)} | ${cell(location.feature_name)} | ${cell(location.reason_code ?? location.value)} |`);
        lines.push('');
    }
    lines.push('## 比赛定位', '', '| 比赛 ID | 对阵 | kickoff | eligibility | 原因 | 特征 / 不可用原因 |', '|---|---|---|---|---|---|');
    for (const row of report.match_diagnostics) lines.push(`| ${cell(row.canonical_match_id)} | ${cell(row.home_team)} / ${cell(row.away_team)} | ${cell(row.target_kickoff_utc)} | ${cell(row.training_eligibility.status)} | ${cell(row.training_eligibility.reason_codes.join(', '))} | ${cell(row.unavailable_locations.map(item => `${item.feature_name ?? '标签'}:${item.reason_code}`).join(', '))} |`);
    return `${lines.join('\n')}\n`;
}

module.exports = { buildQualityDiagnostics, renderQualityMarkdown };
