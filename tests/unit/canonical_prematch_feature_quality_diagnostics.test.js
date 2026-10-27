'use strict';

// lifecycle: test-fixture；诊断的直接行为、来源防篡改与文件边界回归；无业务采集。
const assert = require('node:assert/strict');
const test = require('node:test');
const path = require('node:path');
const fs = require('node:fs');
const os = require('node:os');
const { loadFeatureContract } = require('../../scripts/ops/gd_a03_assembler');
const { admittedIdSetHash, sha256Bytes } = require('../../src/infrastructure/golden_dataset/GdA01AssemblyContract');
const { FEATURE_SEMANTICS } = require('../../src/infrastructure/golden_dataset/GdA03PriorStateContract');
const {
    buildFrameOutput, computeFrameBusinessHash, computeFrameReceiptHash, sourceLineBindingDigest,
} = require('../../src/infrastructure/golden_dataset/CanonicalPrematchFeatureFrameContract');
const { buildQualityDiagnostics, renderQualityMarkdown } = require('../../src/infrastructure/golden_dataset/CanonicalPrematchFeatureQualityDiagnostics');
const { parseArgs, main } = require('../../scripts/ops/canonical_prematch_feature_frame');

const ROOT = path.resolve(__dirname, '../..');
const LOADED = loadFeatureContract(ROOT);
const ORDER = LOADED.vNextContract.feature_statuses.filter(item => item.training_decision === 'ACCEPTED_FOR_TRAINING').map(item => item.feature_name);

function fixture(count = 6, mutate = () => {}) {
    const rows = Array.from({ length: count }, (_, index) => {
        const id = `match-${index + 1}`;
        const kickoff = '2024-02-01T12:00:00Z';
        return {
            canonical_match_id: id, home_team: '主队', away_team: '客队', target_kickoff: kickoff,
            features: Object.fromEntries(LOADED.contract.ordered_features.map(name => [name, {
                availability_status: 'AVAILABLE', value: name === 'home_points' ? 0 : name === 'points_diff' ? [-5, -2, 0, 2, 4, 100][index % 6] : index,
                unavailable_reason_codes: [],
                source_match_ids: ['prior-1'],
                source_identities: [{ canonical_match_id: 'prior-1', kickoff_at: '2024-01-01T12:00:00Z' }],
                source_fields: ['fixture.value'], provenance_digest: 'a'.repeat(64),
                cutoff_proof: { passed: true, relation: 'source_match_kickoff < target_match_kickoff', target_cutoff: kickoff },
            }])),
            target_label: {
                canonical_match_id: id, role: 'TRAINING_LABEL_POSTMATCH', timing_class: 'POSTMATCH_ONLY',
                status: 'AVAILABLE', outcome: 'home', provenance_digest: 'b'.repeat(64), source_fact_binding: {},
            },
        };
    });
    if (count === 6) {
        const unavailable = (index, name, reasons) => Object.assign(rows[index].features[name], { availability_status: 'UNAVAILABLE', value: null, unavailable_reason_codes: reasons });
        unavailable(0, ORDER[0], ['A', 'B']);
        unavailable(0, ORDER[1], ['A']);
        unavailable(1, ORDER[0], ['A']);
        for (const index of [1, 2]) Object.assign(rows[index].target_label, { status: 'UNAVAILABLE', outcome: null });
    }
    mutate(rows);
    const priorStateArtifact = {
        schema_version: 'test-source/v1', business_content_sha256: 'c'.repeat(64),
        feature_contract: LOADED.contract, feature_semantics: FEATURE_SEMANTICS,
        population_authority: { target_population_count: count, target_id_set_sha256: admittedIdSetHash(rows.map(row => row.canonical_match_id)) }, rows,
    };
    const priorStateReceipt = { schema_version: 'test-receipt/v1' };
    const inputs = {
        priorStateArtifact, priorStateReceipt,
        priorStateArtifactBytes: Buffer.from(JSON.stringify(priorStateArtifact)),
        priorStateReceiptBytes: Buffer.from(JSON.stringify(priorStateReceipt)),
        featureContractBinding: { sha256: LOADED.sha256, registrySchemaVersion: LOADED.registrySchemaVersion },
        vNextContract: LOADED.vNextContract,
        runtimeSemanticEngineBinding: { sha256: 'e'.repeat(64), adapterSha256: 'f'.repeat(64) },
        codeRevision: '1'.repeat(40),
    };
    const output = buildFrameOutput(inputs);
    return { ...inputs, artifactBytes: output.artifactBytes, receiptBytes: output.receiptBytes };
}

function rehash(inputs, mutate) {
    const artifact = JSON.parse(inputs.artifactBytes);
    const receipt = JSON.parse(inputs.receiptBytes);
    mutate(artifact);
    artifact.business_content_sha256 = computeFrameBusinessHash(artifact);
    const artifactBytes = Buffer.from(`${JSON.stringify(artifact, null, 2)}\n`);
    receipt.artifact_sha256 = sha256Bytes(artifactBytes);
    receipt.output_business_sha256 = artifact.business_content_sha256;
    receipt.receipt_content_sha256 = computeFrameReceiptHash(receipt);
    return { ...inputs, artifactBytes, receiptBytes: Buffer.from(`${JSON.stringify(receipt, null, 2)}\n`) };
}

const result = () => buildQualityDiagnostics(fixture());

test('九项有效数量、缺失率和合法零值；八项只复用 registry 理由', () => {
    const { report } = result();
    assert.equal(report.features.length, 9);
    assert.deepEqual(report.features.map(item => item.feature_name), ORDER);
    const home = report.features[0];
    assert.equal(home.valid_count, 4);
    assert.equal(home.missing_count, 2);
    assert.equal(home.missing_rate, 2 / 6);
    assert.equal(home.numeric_quality.zero_count, 0);
    const zero = report.features.find(item => item.feature_name === 'home_points');
    assert.equal(zero.valid_count, 6);
    assert.equal(zero.missing_count, 0);
    assert.equal(zero.numeric_quality.zero_count, 6);
    assert.equal(zero.numeric_quality.constant, true);
    assert.equal(zero.numeric_quality.all_zero, true);
    assert.deepEqual(report.non_selected_features, LOADED.vNextContract.feature_statuses.filter(item => item.training_decision !== 'ACCEPTED_FOR_TRAINING').map(item => ({ feature_name: item.feature_name, final_decision: item.training_decision, reason_code: item.reason_code })));
    assert.equal(report.non_selected_features.length, 8);
});

test('多原因命中不重复计算不同比赛，并区分特征和标签', () => {
    const { report } = result();
    assert.equal(report.population_accounting.training_eligible, 3);
    assert.equal(report.population_accounting.training_ineligible, 3);
    assert.equal(report.unavailability.reason_hit_count, 6);
    assert.equal(report.unavailability.affected_match_count, 3);
    const a = report.unavailability.reason_summary.find(item => item.reason_code === 'A');
    assert.equal(a.reason_hit_count, 3);
    assert.equal(a.affected_match_count, 2);
    assert.deepEqual(a.match_ids, ['match-1', 'match-2']);
    assert.deepEqual(a.feature_names, ORDER.slice(0, 2).sort());
    const label = report.unavailability.reason_summary.find(item => item.kind === 'TARGET_LABEL_UNAVAILABLE');
    assert.equal(label.reason_hit_count, 2);
    assert.equal(label.affected_match_count, 2);
    assert.deepEqual(label.feature_names, []);
    assert.equal(report.features[0].unavailable_reasons.find(item => item.reason_code === 'A').reason_hit_count, 2);
    assert.equal(report.eligibility.reason_summary.reduce((sum, item) => sum + item.reason_hit_count, 0), 5);
});

test('完整原因组合是去重分区；定位保留比赛和特征', () => {
    const { report } = result();
    const combinations = report.unavailability.reason_combinations;
    assert.equal(combinations.length, 3);
    assert.equal(combinations.reduce((sum, item) => sum + item.affected_match_count, 0), 3);
    const group = combinations.find(item => item.match_ids.includes('match-1'));
    assert.deepEqual(group.reasons, [['FEATURE_UNAVAILABLE', 'A'], ['FEATURE_UNAVAILABLE', 'B']]);
    assert.equal(report.match_diagnostics[0].unavailable_locations.length, 3);
    assert.equal(report.match_diagnostics[0].unavailable_locations[1].feature_name, ORDER[0]);
    assert.deepEqual(report.eligibility.ineligible_match_ids, ['match-1', 'match-2', 'match-3']);
    assert.equal(report.eligibility.reason_combinations.reduce((sum, item) => sum + item.affected_match_count, 0), 3);
});

test('数值分布与 IQR 离群依据可以从观测值直接核验', () => {
    const { report } = result();
    const q = report.features.find(item => item.feature_name === 'points_diff').numeric_quality;
    assert.equal(q.distinct_value_count, 6);
    assert.equal(q.min, -5);
    assert.equal(q.max, 100);
    assert.equal(q.mean, 16.5);
    assert.equal(q.q1, -1.5);
    assert.equal(q.median, 1);
    assert.equal(q.q3, 3.5);
    assert.ok(Math.abs(q.population_standard_deviation - Math.sqrt([-5, -2, 0, 2, 4, 100].reduce((sum, v) => sum + (v - 16.5) ** 2, 0) / 6)) < 1e-12);
    assert.equal(q.iqr_outliers.lower_fence, -9);
    assert.equal(q.iqr_outliers.upper_fence, 11);
    assert.deepEqual(q.iqr_outliers.locations, [{ canonical_match_id: 'match-6', feature_name: 'points_diff', value: 100 }]);
});

test('调查按不同比赛影响量排序，常量全零证据不推断修复收益', () => {
    const { report } = result();
    const issues = report.investigation.priorities;
    assert.equal(issues[0].affected_match_count, 6);
    for (let i = 1; i < issues.length; i++) assert.ok(issues[i - 1].affected_match_count >= issues[i].affected_match_count);
    const zero = issues.find(item => item.type === 'ALL_ZERO');
    assert.equal(zero.locations.length, 6);
    assert.ok(zero.locations.every(item => item.value === 0));
    assert.equal(zero.affected_eligible_match_count, 3);
    assert.equal(zero.affected_ineligible_match_count, 3);
    assert.equal(report.investigation.affected_match_count, 6);
    assert.match(report.interpretation, /不等于修复后可新增训练样本数/);
    assert.match(report.interpretation, /不自动判错/);
});

test('空总体、无可用观测和单个观测不虚构统计证据', () => {
    const empty = buildQualityDiagnostics(fixture(0)).report;
    assert.equal(empty.features[0].missing_rate, null);
    assert.equal(empty.features[0].numeric_quality.mean, null);
    assert.equal(empty.investigation.priorities.length, 0);
    const single = buildQualityDiagnostics(fixture(1)).report;
    assert.equal(single.features[0].numeric_quality.constant, false);
    assert.equal(single.features[0].numeric_quality.all_zero, false);
    assert.equal(single.features[0].numeric_quality.insufficient_observations, true);
    const missing = buildQualityDiagnostics(fixture(2, rows => rows.forEach(row => Object.assign(row.features[ORDER[0]], { availability_status: 'UNAVAILABLE', value: null, unavailable_reason_codes: ['NO_HISTORY'] })))).report.features[0];
    assert.equal(missing.valid_count, 0);
    assert.equal(missing.missing_rate, 1);
    assert.equal(missing.numeric_quality.distinct_value_count, 0);
    assert.equal(missing.numeric_quality.constant, false);
});

test('合法零值和负差值不自动判异常；重复原因按同一特征一次计数', () => {
    const report = buildQualityDiagnostics(fixture(2, rows => {
        rows[0].features.points_diff.value = -1;
        rows[1].features.points_diff.value = 0;
        Object.assign(rows[0].features[ORDER[0]], { availability_status: 'UNAVAILABLE', value: null, unavailable_reason_codes: ['A', 'A'] });
    })).report;
    assert.equal(report.unavailability.reason_hit_count, 1);
    assert.equal(report.features.find(item => item.feature_name === 'points_diff').missing_count, 0);
    assert.equal(report.features.find(item => item.feature_name === 'points_diff').numeric_quality.iqr_outliers.count, 0);
});

test('同输入同版本 JSON 与中文 Markdown 字节确定、无改写输入', () => {
    const inputs = fixture();
    const before = JSON.stringify(inputs);
    const first = buildQualityDiagnostics(inputs);
    const second = buildQualityDiagnostics(inputs);
    assert.equal(JSON.stringify(inputs), before);
    assert.deepEqual(first.jsonBytes, second.jsonBytes);
    assert.deepEqual(first.markdownBytes, second.markdownBytes);
    assert.deepEqual(JSON.parse(first.jsonBytes), first.report);
    assert.equal(first.markdownBytes.toString(), renderQualityMarkdown(first.report));
    assert.match(first.markdownBytes.toString(), /覆盖 6 场不同比赛；eligible 3 场；ineligible 3 场/);
    assert.match(first.markdownBytes.toString(), /原因命中 6 次，影响 3 场不同比赛/);
    assert.match(first.markdownBytes.toString(), /KICKOFF_REFERENCE_ONLY/);
    assert.match(first.markdownBytes.toString(), /真实决策时点可用性未证明/);
    assert.match(first.markdownBytes.toString(), /match-6.*points_diff.*100/);
    assert.equal(first.report.input_binding.frame_artifact_sha256, sha256Bytes(inputs.artifactBytes));
    const { business_content_sha256: hash, ...business } = first.report;
    assert.equal(hash, require('../../src/infrastructure/canonical/StableValue').sha256Text(require('../../src/infrastructure/canonical/StableValue').stableStringify(business)));
});

test('拒绝未重 hash 的值篡改、receipt 篡改和错误来源 bytes', () => {
    const inputs = fixture();
    const changed = JSON.parse(inputs.artifactBytes);
    changed.rows[0].features.home_points.value = 5;
    assert.throws(() => buildQualityDiagnostics({ ...inputs, artifactBytes: Buffer.from(JSON.stringify(changed)) }), /binding/);
    assert.throws(() => buildQualityDiagnostics({ ...inputs, receiptBytes: Buffer.from('{}') }), /receipt/);
    assert.throws(() => buildQualityDiagnostics({ ...inputs, priorStateArtifactBytes: Buffer.from('{}') }), /bound/);
    assert.throws(() => buildQualityDiagnostics({ ...inputs, priorStateReceiptBytes: Buffer.from('{}') }), /bound/);
});

test('即使协调重 hash，来源投影、registry、eligibility 和标签篡改仍失败', () => {
    const inputs = fixture();
    const label = rehash(inputs, artifact => { artifact.rows[3].target_label.outcome = 'away'; });
    assert.throws(() => buildQualityDiagnostics(label), /bound/);
    const reasons = rehash(inputs, artifact => { artifact.rows[0].training_eligibility.reason_codes = ['FAKE']; });
    assert.throws(() => buildQualityDiagnostics(reasons), /bound/);
    const decision = rehash(inputs, artifact => { artifact.feature_decisions[0].reason_code = 'FAKE'; });
    assert.throws(() => buildQualityDiagnostics(decision), /bound/);
    assert.throws(() => buildQualityDiagnostics({ ...inputs, featureContractBinding: { ...inputs.featureContractBinding, sha256: '9'.repeat(64) } }), /bound/);
    assert.throws(() => buildQualityDiagnostics({ ...inputs, codeRevision: '2'.repeat(40) }), /bound/);
});

test('重 hash 的来源时点泄漏和非法 AVAILABLE 值 fail closed', () => {
    const inputs = fixture();
    for (const mutate of [
        line => { line.source_identities[0].kickoff_at = '2024-02-01T12:00:00Z'; },
        line => { line.value = null; },
    ]) {
        const changed = rehash(inputs, artifact => {
            const row = artifact.rows[0];
            mutate(row.features.home_points);
            row.features.home_points.source_line_sha256 = sourceLineBindingDigest(row.canonical_match_id, 'home_points', row.features.home_points);
        });
        assert.throws(() => buildQualityDiagnostics(changed), /future source identity|available value is invalid/);
    }
});

test('中文 Markdown 安全展示动态文本，不产生伪造表格或 HTML', () => {
    const { report } = buildQualityDiagnostics(fixture(1, rows => { rows[0].home_team = '<script>|`注入\n标题'; }));
    const markdown = renderQualityMarkdown(report);
    assert.doesNotMatch(markdown, /<script>/);
    assert.match(markdown, /&lt;script&gt;&#124;&#96;注入 标题/);
});

test('diagnose CLI 必填输入、显式双输出与结构化错误', () => {
    const args = ['diagnose', '--artifact', '/tmp/frame.json', '--receipt', '/tmp/receipt.json', '--gd-a03-artifact', '/tmp/source.json', '--gd-a03-receipt', '/tmp/source-receipt.json', '--output', '/tmp/quality.json', '--markdown-output', '/tmp/quality.md', '--expected-targets', '888'];
    assert.equal(parseArgs(args).expectedTargets, 888);
    assert.equal(parseArgs(args).markdownOutputPath, '/tmp/quality.md');
    assert.throws(() => parseArgs(args.slice(0, -4)), /required/);
    assert.throws(() => parseArgs([...args, '--unknown', 'x']), /unknown/);
    const writes = [];
    const original = process.stderr.write;
    try {
        process.stderr.write = value => { writes.push(value); return true; };
        assert.equal(main(['diagnose']), 2);
    } finally { process.stderr.write = original; }
    assert.equal(JSON.parse(writes.join('')).code, 'INPUT_INVALID');
});

// 端到端使用真正 GD-A03 assembler/validator；仅 Git 身份探针为测试替身。
// 真实 888 输入、真实 clean HEAD 与产物生成仍由独立的仓库外验收执行。
function assembledSource() {
    const contract = require('../../src/infrastructure/golden_dataset/GdA03PriorStateContract');
    const { buildPriorStateFeatureView } = require('../../src/infrastructure/golden_dataset/GdA03PriorStateAssembler');
    const teams = Array.from({ length: 20 }, (_, index) => `Team ${index}`);
    const schedule = [];
    const counts = {};
    for (const home of teams) {
        counts[home] = { total: 38, home: 19, away: 19 };
        for (const away of teams) {
            if (home === away) continue;
            const n = schedule.length + 1;
            schedule.push({
                id: `47_20242025_${String(n).padStart(7, '0')}`, source_provider: 'FotMob', source_match_id: String(n),
                competition: 'Premier League', season: '2024/2025', home_team: home, away_team: away,
                kickoff_at: new Date(Date.parse('2024-07-01T12:00:00Z') + n * 86400000).toISOString(),
            });
        }
    }
    const targets = schedule.slice(0, 2).map(row => ({ ...row, canonical_match_id: row.id }));
    const facts = targets.map(row => ({
        canonical_match_id: row.id, competition: row.competition, season: row.season, kickoff_at: row.kickoff_at,
        home_team: row.home_team, away_team: row.away_team,
        facts: {
            match_result: { status: 'AVAILABLE', home_score: 0, away_score: 0, outcome: 'draw', source_path: 'fixture.score' },
            xg: {
                status: 'VALID', source_path: 'fixture.xg', aggregation: 'sum_known_expectedGoals_by_team_id',
                total_shots: 2, shots_with_xg: 2, shots_without_xg: 0, non_own_goal_shots: 2, non_own_goal_shots_with_xg: 2,
                home: { value: 0, status: 'COMPLETE', known_shots: 1, missing_shots: 0 },
                away: { value: 0, status: 'COMPLETE', known_shots: 1, missing_shots: 0 },
            },
            shots_on_target: {
                status: 'UNAVAILABLE', source_path: 'fixture.sot', aggregation: 'count_true_isOnTarget_by_team_id',
                total_shots: null, shots_with_on_target: null, shots_without_on_target: null,
                home: { value: null, status: 'UNAVAILABLE', known_shots: 0, missing_shots: 0 },
                away: { value: null, status: 'UNAVAILABLE', known_shots: 0, missing_shots: 0 },
            }, sections: {},
        },
        provenance: { staging: { artifact_integrity_sha256: 'a'.repeat(64), business_hash: 'b'.repeat(64), stable_payload_sha256: 'c'.repeat(64) } },
        source_linkage: { status: 'matched', matched_id: row.id, candidate_ids: [row.id] },
    }));
    const binding = { sha256: 'a'.repeat(64), business_hash: 'b'.repeat(64), schema_version: 'fixture/v1' };
    const resultBindings = facts.map(row => ({ canonical_match_id: row.canonical_match_id, fact_result_binding: contract.computeFactResultBinding({ canonicalMatchId: row.canonical_match_id, result: row.facts.match_result, sourceProvenance: row.provenance }) }));
    return buildPriorStateFeatureView({
        targetRows: targets, factRows: facts, factRejections: [], scheduleCandidates: schedule,
        scheduleClosure: {
            schema_version: 'canonical-schedule-history/v1', status: 'PROVEN', authority: 'unit-test complete schedule',
            per_season_expected_counts: { '2024/2025': 380 },
            team_closure: { schema_version: contract.SCHEDULE_TEAM_CLOSURE_SCHEMA_VERSION, status: 'PROVEN', teams_per_season: 20, fixtures_per_team: 38, home_fixtures_per_team: 19, away_fixtures_per_team: 19, per_team_counts: { '2024/2025': counts } },
        },
        featureContract: LOADED.contract, codeRevision: '1'.repeat(40),
        sourceBindings: {
            gd_a01_artifact: binding, gd_a01_receipt: { ...binding, admitted_id_set_sha256: admittedIdSetHash(targets.map(row => row.id)), admitted_row_count: 2 },
            gd_a02_artifact: {
                ...binding, fact_result_bindings_sha256: contract.computeFactResultBindingsHash(resultBindings), fact_result_binding_count: 2,
                fact_rejection_bindings_sha256: contract.computeFactRejectionBindingsHash([]), fact_rejection_binding_count: 0,
                fact_admitted_id_set_sha256: admittedIdSetHash(targets.map(row => row.id)), fact_admitted_row_count: 2,
                fact_rejected_id_set_sha256: admittedIdSetHash([]), fact_rejected_row_count: 0,
                fact_accounted_id_set_sha256: admittedIdSetHash(targets.map(row => row.id)), fact_accounted_row_count: 2,
            },
            gd_a02_receipt: binding, canonical_schedule: binding,
            feature_contract: { sha256: binding.sha256, schema_version: 'model-feature-contract-registry/v1' },
            runtime_feature_adapter: { sha256: binding.sha256, schema_version: 'V26_6_PreMatchAdapter.V26_6_FEATURES', ordered_features: LOADED.contract.ordered_features },
        },
    });
}

test('正式 CLI build → validate → diagnose 写出确定的双报告，拒绝篡改、旧版本和不安全输出', context => {
    const cli = require('../../scripts/ops/canonical_prematch_feature_frame');
    const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'canonical-quality-'));
    context.after(() => fs.rmSync(directory, { recursive: true, force: true }));
    context.mock.method(require('node:child_process'), 'execSync', command => {
        if (command === 'git status --porcelain') return '';
        if (command === 'git rev-parse HEAD') return '1'.repeat(40);
        throw new Error(`unexpected Git identity probe: ${command}`);
    });
    const source = assembledSource();
    const sourcePath = path.join(directory, 'source.json');
    const sourceReceipt = path.join(directory, 'source-receipt.json');
    fs.writeFileSync(sourcePath, source.artifactBytes);
    fs.writeFileSync(sourceReceipt, source.receiptBytes);
    const artifactPath = path.join(directory, 'frame.json');
    const receiptPath = path.join(directory, 'frame-receipt.json');
    const args = { gdA03ArtifactPath: sourcePath, gdA03ReceiptPath: sourceReceipt, artifactPath, receiptPath, expectedTargets: 2 };
    assert.equal(cli.build({ ...args, outputPath: artifactPath, codeRevision: '1'.repeat(40) }, ROOT).validation, 'PASS');
    assert.equal(cli.validate(args, ROOT).validation, 'PASS');
    const diagnose = (prefix, overrides = {}) => cli.diagnose({ ...args, outputPath: path.join(directory, `${prefix}.json`), markdownOutputPath: path.join(directory, `${prefix}.md`), ...overrides }, ROOT);
    const first = diagnose('first');
    const second = diagnose('second');
    assert.deepEqual(fs.readFileSync(first.output.json), fs.readFileSync(second.output.json));
    assert.deepEqual(fs.readFileSync(first.output.markdown), fs.readFileSync(second.output.markdown));
    assert.equal(JSON.parse(fs.readFileSync(first.output.json)).population_accounting.rows_accounted, 2);
    assert.match(fs.readFileSync(first.output.markdown, 'utf8'), /KICKOFF_REFERENCE_ONLY/);
    assert.throws(() => diagnose('first'), error => error.code === 'OUTPUT_EXISTS');
    assert.throws(() => diagnose('same', { markdownOutputPath: path.join(directory, 'same.json') }), error => error.code === 'PATH_INVALID');
    assert.throws(() => diagnose('wrong-population', { expectedTargets: 3 }), error => error.code === 'POPULATION_MISMATCH');
    assert.throws(() => diagnose('internal', { outputPath: path.join(ROOT, 'quality-must-not-exist.json') }), error => error.code === 'SAFETY_BOUNDARY');
    assert.throws(() => diagnose('relative', { outputPath: 'quality.json' }), error => error.code === 'PATH_INVALID');
    fs.symlinkSync(directory, path.join(directory, 'link'));
    assert.throws(() => diagnose('symlink', { outputPath: path.join(directory, 'link/report.json') }), error => error.code === 'PATH_INVALID');
    assert.throws(() => diagnose('input-symlink', { artifactPath: path.join(directory, 'link/frame.json') }), error => error.code === 'PATH_INVALID');
    const receipt = JSON.parse(fs.readFileSync(receiptPath));
    receipt.code_revision = '2'.repeat(40);
    receipt.receipt_content_sha256 = computeFrameReceiptHash(receipt);
    fs.writeFileSync(receiptPath, JSON.stringify(receipt));
    assert.throws(() => diagnose('old'), error => error.code === 'CODE_REVISION_MISMATCH');
    fs.writeFileSync(receiptPath, JSON.stringify({ ...receipt, code_revision: '1'.repeat(40) }));
    // 重新通过 build 生成正确 receipt 到新路径，保留已生成的所有输出。
    const rebuilt = path.join(directory, 'frame2.json');
    const rebuiltReceipt = path.join(directory, 'frame2-receipt.json');
    cli.build({ ...args, outputPath: rebuilt, receiptPath: rebuiltReceipt, codeRevision: '1'.repeat(40) }, ROOT);
    const original = fs.readFileSync(sourcePath);
    fs.writeFileSync(sourcePath, '{}');
    assert.throws(() => diagnose('source-tamper', { artifactPath: rebuilt, receiptPath: rebuiltReceipt }));
    fs.writeFileSync(sourcePath, original);
    const frame = JSON.parse(fs.readFileSync(rebuilt));
    frame.rows[0].features.home_points.value = 777;
    fs.writeFileSync(rebuilt, JSON.stringify(frame));
    assert.throws(() => diagnose('frame-tamper', { artifactPath: rebuilt, receiptPath: rebuiltReceipt }), /binding/);
    for (const prefix of ['same', 'wrong-population', 'symlink', 'old', 'source-tamper', 'frame-tamper']) {
        assert.equal(fs.existsSync(path.join(directory, `${prefix}.json`)), false);
        assert.equal(fs.existsSync(path.join(directory, `${prefix}.md`)), false);
    }
});
