/**
 * FotMobParserOutputEnvelopeLegacyAdapter 单元测试
 * ===============================================
 *
 * 测试 dry-run adapter 的 field 分类、metadata 映射、invalid input 处理和 envelope shape。
 * 纯静态测试：不访问网络、文件、DB、FotMob parser runtime。
 *
 * lifecycle: permanent
 */

'use strict';

const { describe, test } = require('node:test');
const assert = require('node:assert/strict');

const {
    adaptTransformToApiFormatOutputToEnvelope,
    classifyField,
    flattenTransformOutputFields,
} = require('../../../../src/parsers/fotmob/FotMobParserOutputEnvelopeLegacyAdapter');

const {
    MODEL_ELIGIBILITY,
    TIMING_CLASSES,
    FIELD_CONTRACT_CLASSES,
    validateEnvelopeShape,
    isForbidden,
} = require('../../../../src/parsers/fotmob/FotMobParserOutputEnvelope');

// ===========================================================================
// Fixtures
// ===========================================================================

/**
 * 标准 happy-path transformToApiFormat 输出。
 */
const HAPPY_PATH_TRANSFORM_OUTPUT = Object.freeze({
    matchId: '4193673',
    content: {
        stats: {
            expectedGoals: { home: 1.2, away: 0.8 },
            shots: { home: 10, away: 8 },
            Periods: { All: { stats: [] } },
        },
        lineup: {
            home: { starters: [{ id: 1, name: 'Player A' }], bench: [] },
            away: { starters: [{ id: 2, name: 'Player B' }], bench: [] },
        },
        shotmap: [{ id: 1, xG: 0.2 }, { id: 2, xG: 0.1 }],
        events: [{ id: 1, type: 'Goal', minute: 23 }],
    },
    general: {
        homeTeam: { id: 1, name: 'Home FC' },
        awayTeam: { id: 2, name: 'Away FC' },
        matchTimeUTC: '2026-07-04T12:00:00Z',
    },
    header: {
        status: { utcTime: '2026-07-04T12:00:00Z', scoreStr: '2-1' },
        teams: [
            { name: 'Home FC', score: 2 },
            { name: 'Away FC', score: 1 },
        ],
    },
    _meta: {
        source: 'web_infiltration',
        extractedAt: '2026-07-04T00:00:00.000Z',
        hasStats: true,
        hasLineup: true,
        hasShotmap: true,
    },
});

/**
 * 精简 transformToApiFormat 输出（无 content 数据）。
 */
const MINIMAL_TRANSFORM_OUTPUT = Object.freeze({
    matchId: '1',
    general: { homeTeam: { name: 'A' }, awayTeam: { name: 'B' } },
    header: { status: { utcTime: '2026-07-04T12:00:00Z' } },
    content: {},
    _meta: { source: 'web_infiltration' },
});

// ===========================================================================
// classifyField 测试
// ===========================================================================

describe('classifyField', () => {
    test('content.stats 应标记为 forbidden_postmatch', () => {
        const result = classifyField('content.stats', { some: 'data' });
        assert.equal(result.timingClass, TIMING_CLASSES.POSTMATCH);
        assert.equal(result.modelEligibility, MODEL_ELIGIBILITY.FORBIDDEN_POSTMATCH);
        assert.equal(result.contractClass, FIELD_CONTRACT_CLASSES.UNSAFE_POSTMATCH);
    });

    test('content.stats.expectedGoals 应标记为 forbidden_postmatch（前缀匹配）', () => {
        const result = classifyField('content.stats.expectedGoals', { home: 1.2 });
        assert.equal(result.timingClass, TIMING_CLASSES.POSTMATCH);
        assert.equal(result.modelEligibility, MODEL_ELIGIBILITY.FORBIDDEN_POSTMATCH);
    });

    test('content.shotmap 应标记为 forbidden_postmatch', () => {
        const result = classifyField('content.shotmap', []);
        assert.equal(result.modelEligibility, MODEL_ELIGIBILITY.FORBIDDEN_POSTMATCH);
    });

    test('content.shotmap[0].xG 应标记为 forbidden_postmatch（前缀匹配）', () => {
        const result = classifyField('content.shotmap[0].xG', 0.2);
        assert.equal(result.modelEligibility, MODEL_ELIGIBILITY.FORBIDDEN_POSTMATCH);
    });

    test('content.events 应标记为 forbidden_postmatch', () => {
        const result = classifyField('content.events', []);
        assert.equal(result.modelEligibility, MODEL_ELIGIBILITY.FORBIDDEN_POSTMATCH);
    });

    test('content.playerStats 应标记为 forbidden_postmatch', () => {
        const result = classifyField('content.playerStats', {});
        assert.equal(result.modelEligibility, MODEL_ELIGIBILITY.FORBIDDEN_POSTMATCH);
    });

    test('content.lineup 应标记为 forbidden_unknown_timing', () => {
        const result = classifyField('content.lineup', { home: [] });
        assert.equal(result.timingClass, TIMING_CLASSES.UNKNOWN_TIMING);
        assert.equal(result.modelEligibility, MODEL_ELIGIBILITY.FORBIDDEN_UNKNOWN_TIMING);
        assert.equal(result.contractClass, FIELD_CONTRACT_CLASSES.UNKNOWN_TIMING);
    });

    test('content.injury 应标记为 forbidden_unknown_timing', () => {
        const result = classifyField('content.injury', []);
        assert.equal(result.modelEligibility, MODEL_ELIGIBILITY.FORBIDDEN_UNKNOWN_TIMING);
    });

    test('content.odds 应标记为 forbidden_unknown_timing', () => {
        const result = classifyField('content.odds', {});
        assert.equal(result.modelEligibility, MODEL_ELIGIBILITY.FORBIDDEN_UNKNOWN_TIMING);
    });

    test('content.form 应标记为 forbidden_unknown_timing', () => {
        const result = classifyField('content.form', []);
        assert.equal(result.modelEligibility, MODEL_ELIGIBILITY.FORBIDDEN_UNKNOWN_TIMING);
    });

    test('content.table 应标记为 forbidden_unknown_timing', () => {
        const result = classifyField('content.table', []);
        assert.equal(result.modelEligibility, MODEL_ELIGIBILITY.FORBIDDEN_UNKNOWN_TIMING);
    });

    test('general 应标记为 forbidden_raw_only', () => {
        const result = classifyField('general', {});
        assert.equal(result.timingClass, TIMING_CLASSES.RAW_ONLY);
        assert.equal(result.modelEligibility, MODEL_ELIGIBILITY.FORBIDDEN_RAW_ONLY);
    });

    test('header 应标记为 forbidden_raw_only', () => {
        const result = classifyField('header', {});
        assert.equal(result.timingClass, TIMING_CLASSES.RAW_ONLY);
    });

    test('content 应标记为 forbidden_raw_only', () => {
        const result = classifyField('content', {});
        assert.equal(result.modelEligibility, MODEL_ELIGIBILITY.FORBIDDEN_RAW_ONLY);
    });

    test('_meta.source 应标记为 forbidden_raw_only（前缀匹配）', () => {
        const result = classifyField('_meta.source', 'web_infiltration');
        assert.equal(result.modelEligibility, MODEL_ELIGIBILITY.FORBIDDEN_RAW_ONLY);
    });

    test('未见已知前缀的路径应默认为 forbidden_unknown_timing', () => {
        const result = classifyField('unknown.custom.field', 'value');
        assert.equal(result.timingClass, TIMING_CLASSES.UNKNOWN_TIMING);
        assert.equal(result.modelEligibility, MODEL_ELIGIBILITY.FORBIDDEN_UNKNOWN_TIMING);
    });

    test('postmatch 前缀优先级高于 raw_only（content.stats 匹配 postmatch 而非 raw content）', () => {
        const result = classifyField('content.stats.shots', { home: 10 });
        assert.equal(result.modelEligibility, MODEL_ELIGIBILITY.FORBIDDEN_POSTMATCH);
    });

    test('unknown_timing 前缀优先级高于 raw_only（content.lineup 匹配 unknown_timing 而非 raw content）', () => {
        const result = classifyField('content.lineup.home', []);
        assert.equal(result.modelEligibility, MODEL_ELIGIBILITY.FORBIDDEN_UNKNOWN_TIMING);
    });
});

// ===========================================================================
// flattenTransformOutputFields 测试
// ===========================================================================

describe('flattenTransformOutputFields', () => {
    test('happy path: 应产生 field entries 数组', () => {
        const fields = flattenTransformOutputFields(HAPPY_PATH_TRANSFORM_OUTPUT);
        assert.ok(Array.isArray(fields));
        assert.ok(fields.length > 0, `expected non-empty fields array, got ${fields.length}`);
    });

    test('happy path: matchId 字段应存在且标记为 audit_only', () => {
        const fields = flattenTransformOutputFields(HAPPY_PATH_TRANSFORM_OUTPUT);
        const matchIdEntry = fields.find(f => f.field_path === 'matchId');
        assert.ok(matchIdEntry, 'matchId entry not found');
        assert.equal(matchIdEntry.value, '4193673');
        assert.equal(matchIdEntry.model_eligibility, MODEL_ELIGIBILITY.AUDIT_ONLY);
    });

    test('happy path: content.stats 应存在且标记为 forbidden_postmatch', () => {
        const fields = flattenTransformOutputFields(HAPPY_PATH_TRANSFORM_OUTPUT);
        const statsEntry = fields.find(f => f.field_path === 'content.stats');
        assert.ok(statsEntry, 'content.stats entry not found');
        assert.equal(statsEntry.model_eligibility, MODEL_ELIGIBILITY.FORBIDDEN_POSTMATCH);
    });

    test('happy path: content.shotmap 应存在且标记为 forbidden_postmatch', () => {
        const fields = flattenTransformOutputFields(HAPPY_PATH_TRANSFORM_OUTPUT);
        const shotmapEntry = fields.find(f => f.field_path === 'content.shotmap');
        assert.ok(shotmapEntry, 'content.shotmap entry not found');
        assert.equal(shotmapEntry.model_eligibility, MODEL_ELIGIBILITY.FORBIDDEN_POSTMATCH);
    });

    test('happy path: content.lineup 应存在且标记为 forbidden_unknown_timing', () => {
        const fields = flattenTransformOutputFields(HAPPY_PATH_TRANSFORM_OUTPUT);
        const lineupEntry = fields.find(f => f.field_path === 'content.lineup');
        assert.ok(lineupEntry, 'content.lineup entry not found');
        assert.equal(lineupEntry.model_eligibility, MODEL_ELIGIBILITY.FORBIDDEN_UNKNOWN_TIMING);
    });

    test('happy path: content.events 应存在且标记为 forbidden_postmatch', () => {
        const fields = flattenTransformOutputFields(HAPPY_PATH_TRANSFORM_OUTPUT);
        const eventsEntry = fields.find(f => f.field_path === 'content.events');
        assert.ok(eventsEntry, 'content.events entry not found');
        assert.equal(eventsEntry.model_eligibility, MODEL_ELIGIBILITY.FORBIDDEN_POSTMATCH);
    });

    test('happy path: content 整块应标记为 forbidden_raw_only', () => {
        const fields = flattenTransformOutputFields(HAPPY_PATH_TRANSFORM_OUTPUT);
        const contentEntry = fields.find(f => f.field_path === 'content');
        assert.ok(contentEntry, 'content entry not found');
        assert.equal(contentEntry.model_eligibility, MODEL_ELIGIBILITY.FORBIDDEN_RAW_ONLY);
    });

    test('happy path: general 整块应标记为 forbidden_raw_only', () => {
        const fields = flattenTransformOutputFields(HAPPY_PATH_TRANSFORM_OUTPUT);
        const generalEntry = fields.find(f => f.field_path === 'general');
        assert.ok(generalEntry, 'general entry not found');
        assert.equal(generalEntry.model_eligibility, MODEL_ELIGIBILITY.FORBIDDEN_RAW_ONLY);
    });

    test('happy path: header 整块应标记为 forbidden_raw_only', () => {
        const fields = flattenTransformOutputFields(HAPPY_PATH_TRANSFORM_OUTPUT);
        const headerEntry = fields.find(f => f.field_path === 'header');
        assert.ok(headerEntry, 'header entry not found');
        assert.equal(headerEntry.model_eligibility, MODEL_ELIGIBILITY.FORBIDDEN_RAW_ONLY);
    });

    test('happy path: _meta 子字段应逐个展平且标记为 audit_only', () => {
        const fields = flattenTransformOutputFields(HAPPY_PATH_TRANSFORM_OUTPUT);
        const metaSource = fields.find(f => f.field_path === '_meta.source');
        assert.ok(metaSource, '_meta.source entry not found');
        assert.equal(metaSource.value, 'web_infiltration');
        assert.equal(metaSource.model_eligibility, MODEL_ELIGIBILITY.AUDIT_ONLY);

        const metaHasStats = fields.find(f => f.field_path === '_meta.hasStats');
        assert.ok(metaHasStats, '_meta.hasStats entry not found');
        assert.equal(metaHasStats.value, true);

        const metaHasLineup = fields.find(f => f.field_path === '_meta.hasLineup');
        assert.ok(metaHasLineup, '_meta.hasLineup entry not found');
        assert.equal(metaHasLineup.value, true);

        const metaHasShotmap = fields.find(f => f.field_path === '_meta.hasShotmap');
        assert.ok(metaHasShotmap, '_meta.hasShotmap entry not found');
        assert.equal(metaHasShotmap.value, true);
    });

    test('minimal: 精简输入不产生 safe_prematch field', () => {
        const fields = flattenTransformOutputFields(MINIMAL_TRANSFORM_OUTPUT);
        for (const f of fields) {
            assert.notEqual(
                f.model_eligibility,
                MODEL_ELIGIBILITY.ALLOWED_CANDIDATE,
                `field ${f.field_path} should not be ALLOWED_CANDIDATE in minimal input`
            );
            assert.notEqual(
                f.model_eligibility,
                MODEL_ELIGIBILITY.CANDIDATE_IF_CUTOFF_VALID,
                `field ${f.field_path} should not be CANDIDATE_IF_CUTOFF_VALID in minimal input`
            );
        }
    });

    test('minimal: 所有非 metadata/audit field 应被 isForbidden 判定为 forbidden', () => {
        const fields = flattenTransformOutputFields(MINIMAL_TRANSFORM_OUTPUT);
        for (const f of fields) {
            // audit_only fields (matchId, _meta.*) 不是 forbidden——它们是审计追踪字段
            if (f.model_eligibility === MODEL_ELIGIBILITY.AUDIT_ONLY) {
                continue;
            }
            assert.ok(isForbidden(f), `field ${f.field_path} with eligibility "${f.model_eligibility}" should be forbidden in minimal input`);
        }
    });
});

// ===========================================================================
// adaptTransformToApiFormatOutputToEnvelope 测试
// ===========================================================================

describe('adaptTransformToApiFormatOutputToEnvelope', () => {
    // --- happy path ---

    test('happy path: 应返回 envelope-compatible 对象', () => {
        const envelope = adaptTransformToApiFormatOutputToEnvelope(HAPPY_PATH_TRANSFORM_OUTPUT);

        // 必须通过 schema validation
        const validation = validateEnvelopeShape(envelope);
        assert.ok(validation.valid, `envelope should pass shape validation: ${validation.errors.join('; ')}`);

        // 核心字段检查
        assert.equal(envelope.match_id, '4193673');
        assert.equal(envelope.source, 'fotmob');
        assert.ok(Array.isArray(envelope.fields));
        assert.ok(envelope.fields.length > 0);
    });

    test('happy path: payload metadata 默认值', () => {
        const envelope = adaptTransformToApiFormatOutputToEnvelope(HAPPY_PATH_TRANSFORM_OUTPUT);

        assert.equal(envelope.payload.payload_type, 'parser_input');
        assert.equal(envelope.payload.data_version, 'unknown');
        assert.equal(envelope.payload.payload_hash, null);
        assert.equal(envelope.payload.storage_path, null);
        assert.equal(envelope.payload.captured_at, null);
        assert.equal(envelope.payload.source_url, null);
        assert.equal(envelope.payload.final_url, null);
        assert.equal(envelope.payload.fetched_at, null);
    });

    test('happy path: parser metadata 默认值', () => {
        const envelope = adaptTransformToApiFormatOutputToEnvelope(HAPPY_PATH_TRANSFORM_OUTPUT);

        assert.equal(envelope.parser.parser_name, 'NextDataParser.transformToApiFormat');
        assert.equal(envelope.parser.parser_version, 'legacy-static');
        assert.equal(envelope.parser.parsed_at, null);
    });

    test('happy path: warnings 应反映 metadata 缺失', () => {
        const envelope = adaptTransformToApiFormatOutputToEnvelope(HAPPY_PATH_TRANSFORM_OUTPUT);

        assert.ok(Array.isArray(envelope.warnings));
        const hasVersionWarning = envelope.warnings.some(w => w.includes('data_version is unknown'));
        assert.ok(hasVersionWarning, 'should warn about unknown data_version');

        const hasHashWarning = envelope.warnings.some(w => w.includes('payload_hash is null'));
        assert.ok(hasHashWarning, 'should warn about null payload_hash');
    });

    test('happy path: matchId 被正确保留', () => {
        const envelope = adaptTransformToApiFormatOutputToEnvelope(HAPPY_PATH_TRANSFORM_OUTPUT);
        assert.equal(envelope.match_id, '4193673');
    });

    test('happy path: 不应产生任何 ALLOWED_CANDIDATE field（保守策略）', () => {
        const envelope = adaptTransformToApiFormatOutputToEnvelope(HAPPY_PATH_TRANSFORM_OUTPUT);
        for (const f of envelope.fields) {
            assert.notEqual(
                f.model_eligibility,
                MODEL_ELIGIBILITY.ALLOWED_CANDIDATE,
                `field ${f.field_path} should not be ALLOWED_CANDIDATE — dry-run is conservative`
            );
        }
    });

    test('happy path: content.stats / content.shotmap / content.events 均标记 forbidden_postmatch', () => {
        const envelope = adaptTransformToApiFormatOutputToEnvelope(HAPPY_PATH_TRANSFORM_OUTPUT);
        const riskyFields = ['content.stats', 'content.shotmap', 'content.events'];
        for (const path of riskyFields) {
            const entry = envelope.fields.find(f => f.field_path === path);
            assert.ok(entry, `${path} entry should exist`);
            assert.equal(
                entry.model_eligibility,
                MODEL_ELIGIBILITY.FORBIDDEN_POSTMATCH,
                `${path} should be FORBIDDEN_POSTMATCH`
            );
        }
    });

    test('happy path: content.lineup 标记 forbidden_unknown_timing', () => {
        const envelope = adaptTransformToApiFormatOutputToEnvelope(HAPPY_PATH_TRANSFORM_OUTPUT);
        const lineupEntry = envelope.fields.find(f => f.field_path === 'content.lineup');
        assert.ok(lineupEntry);
        assert.equal(lineupEntry.model_eligibility, MODEL_ELIGIBILITY.FORBIDDEN_UNKNOWN_TIMING);
    });

    // --- metadata preservation ---

    test('metadata: options 传入的 dataVersion / payloadHash / capturedAt / fetchedAt 应被正确保留', () => {
        const envelope = adaptTransformToApiFormatOutputToEnvelope(HAPPY_PATH_TRANSFORM_OUTPUT, {
            dataVersion: 'fotmob_html_hyd_v1',
            payloadHash: 'abc123',
            storagePath: null,
            capturedAt: '2026-07-04T01:00:05.000Z',
            fetchedAt: '2026-07-04T01:00:00.000Z',
        });

        assert.equal(envelope.payload.data_version, 'fotmob_html_hyd_v1');
        assert.equal(envelope.payload.payload_hash, 'abc123');
        assert.equal(envelope.payload.storage_path, null);
        assert.equal(envelope.payload.captured_at, '2026-07-04T01:00:05.000Z');
        assert.equal(envelope.payload.fetched_at, '2026-07-04T01:00:00.000Z');
        // fetchedAt 和 capturedAt 是独立字段，fetchedAt 不覆盖 capturedAt
        assert.notEqual(envelope.payload.fetched_at, envelope.payload.captured_at);
    });

    test('metadata: transformOutput._meta.extractedAt 不覆盖 captured_at', () => {
        const envelope = adaptTransformToApiFormatOutputToEnvelope(HAPPY_PATH_TRANSFORM_OUTPUT, {
            capturedAt: '2026-07-04T02:00:00.000Z',
        });

        assert.equal(envelope.payload.captured_at, '2026-07-04T02:00:00.000Z');

        // _meta.extractedAt 应作为 audit-only field 存在
        const extractedEntry = envelope.fields.find(f => f.field_path === '_meta.extractedAt');
        assert.ok(extractedEntry, '_meta.extractedAt audit field should exist');
        assert.equal(extractedEntry.model_eligibility, MODEL_ELIGIBILITY.AUDIT_ONLY);
    });

    test('metadata: 当 captured_at 存在时，_meta.extractedAt 仍需存在作为补充审计证据', () => {
        const envelope = adaptTransformToApiFormatOutputToEnvelope(HAPPY_PATH_TRANSFORM_OUTPUT, {
            capturedAt: '2026-07-04T02:00:00.000Z',
        });
        // extractedAt 应该作为 audit_only field 保留（不是冒充 captured_at，而是补充证据）
        const extractedEntry = envelope.fields.find(f => f.field_path === '_meta.extractedAt');
        assert.ok(extractedEntry, '_meta.extractedAt audit field should exist alongside captured_at');
        assert.equal(extractedEntry.model_eligibility, MODEL_ELIGIBILITY.AUDIT_ONLY);
        assert.ok(
            extractedEntry.warnings.some(w => w.includes('captured_at or fetched_at is present')),
            'should warn that extractedAt is supplementary when captured_at exists'
        );
    });

    // --- options 覆盖 ---

    test('options: parserName / parserVersion / source 可被覆盖', () => {
        const envelope = adaptTransformToApiFormatOutputToEnvelope(HAPPY_PATH_TRANSFORM_OUTPUT, {
            parserName: 'CustomParser',
            parserVersion: 'v2.0',
            source: 'fotmob_test',
        });

        assert.equal(envelope.parser.parser_name, 'CustomParser');
        assert.equal(envelope.parser.parser_version, 'v2.0');
        assert.equal(envelope.source, 'fotmob_test');
    });

    test('options: parsedAt 不应该被伪造——明确传 null 时应为 null', () => {
        const envelope = adaptTransformToApiFormatOutputToEnvelope(HAPPY_PATH_TRANSFORM_OUTPUT, {
            parsedAt: null,
        });
        assert.equal(envelope.parser.parsed_at, null);
    });

    // --- invalid input ---

    test('invalid: null 输入应抛出明确的 validation error', () => {
        assert.throws(
            () => adaptTransformToApiFormatOutputToEnvelope(null),
            /transformOutput must be a non-null object/
        );
    });

    test('invalid: undefined 输入应抛出明确的 validation error', () => {
        assert.throws(
            () => adaptTransformToApiFormatOutputToEnvelope(undefined),
            /transformOutput must be a non-null object/
        );
    });

    test('invalid: 空对象（无 matchId）应抛出明确的 validation error', () => {
        assert.throws(
            () => adaptTransformToApiFormatOutputToEnvelope({}),
            /matchId is required/
        );
    });

    test('invalid: { matchId: "1" } 但无其他字段应能成功（最少合法输入）', () => {
        const envelope = adaptTransformToApiFormatOutputToEnvelope({ matchId: '1' });
        const validation = validateEnvelopeShape(envelope);
        assert.ok(validation.valid, `minimal envelope should pass: ${validation.errors.join('; ')}`);
        assert.equal(envelope.match_id, '1');
        // fields 数组可能只包含 matchId entry
        assert.ok(Array.isArray(envelope.fields));
    });

    test('invalid: 字符串输入应抛出 error（非对象）', () => {
        assert.throws(
            () => adaptTransformToApiFormatOutputToEnvelope('not_an_object'),
            /transformOutput must be a non-null object/
        );
    });

    test('invalid: 数字输入应抛出 error（非对象）', () => {
        assert.throws(
            () => adaptTransformToApiFormatOutputToEnvelope(42),
            /transformOutput must be a non-null object/
        );
    });

    // --- conservative unknown timing ---

    test('conservative: 精简输入不产生任何 safe_prematch 标记', () => {
        const envelope = adaptTransformToApiFormatOutputToEnvelope(MINIMAL_TRANSFORM_OUTPUT);

        for (const f of envelope.fields) {
            const allowed = f.model_eligibility === MODEL_ELIGIBILITY.ALLOWED_CANDIDATE;
            assert.ok(!allowed, `field "${f.field_path}" must not be ALLOWED_CANDIDATE in dry-run`);
        }
    });

    test('conservative: 所有非 audit 的 field 应被 isForbidden 判定为 forbidden', () => {
        const envelope = adaptTransformToApiFormatOutputToEnvelope(MINIMAL_TRANSFORM_OUTPUT);

        for (const f of envelope.fields) {
            // audit_only fields (matchId, _meta.*) 是审计追踪字段，不是 forbidden
            if (f.model_eligibility === MODEL_ELIGIBILITY.AUDIT_ONLY) {
                continue;
            }
            assert.ok(
                isForbidden(f),
                `field "${f.field_path}" with eligibility "${f.model_eligibility}" should be forbidden`
            );
        }
    });

    // --- schema validation ---

    test('schema: happy path envelope 通过 validateEnvelopeShape', () => {
        const envelope = adaptTransformToApiFormatOutputToEnvelope(HAPPY_PATH_TRANSFORM_OUTPUT);
        const validation = validateEnvelopeShape(envelope);
        assert.ok(validation.valid, `validation errors: ${validation.errors.join('; ')}`);
        assert.deepEqual(validation.errors, []);
    });

    test('schema: minimal envelope 通过 validateEnvelopeShape', () => {
        const envelope = adaptTransformToApiFormatOutputToEnvelope({ matchId: '1' });
        const validation = validateEnvelopeShape(envelope);
        assert.ok(validation.valid, `validation errors: ${validation.errors.join('; ')}`);
    });

    test('schema: options full metadata envelope 通过 validateEnvelopeShape', () => {
        const envelope = adaptTransformToApiFormatOutputToEnvelope(HAPPY_PATH_TRANSFORM_OUTPUT, {
            dataVersion: 'fotmob_html_hyd_v1',
            payloadHash: 'abc123def456',
            storagePath: '/tmp/test',
            capturedAt: '2026-07-04T01:00:00.000Z',
            fetchedAt: '2026-07-04T01:00:00.000Z',
            parserName: 'NextDataParser.transformToApiFormat',
            parserVersion: 'legacy-static',
            parsedAt: '2026-07-04T01:05:00.000Z',
        });
        const validation = validateEnvelopeShape(envelope);
        assert.ok(validation.valid, `validation errors: ${validation.errors.join('; ')}`);
    });

    // --- data_version handling ---

    test('data_version: 未传 options 时应为 "unknown"', () => {
        const envelope = adaptTransformToApiFormatOutputToEnvelope(HAPPY_PATH_TRANSFORM_OUTPUT);
        assert.equal(envelope.payload.data_version, 'unknown');
    });

    test('data_version: 空字符串应保留为字面值（不自动转为 unknown）', () => {
        const envelope = adaptTransformToApiFormatOutputToEnvelope(HAPPY_PATH_TRANSFORM_OUTPUT, {
            dataVersion: '',
        });
        assert.equal(envelope.payload.data_version, '');
    });

    test('data_version: null 应保持 null（调用方显式表达缺失）', () => {
        const envelope = adaptTransformToApiFormatOutputToEnvelope(HAPPY_PATH_TRANSFORM_OUTPUT, {
            dataVersion: null,
        });
        assert.equal(envelope.payload.data_version, null);
    });

    // --- metadata extension: sourceUrl / finalUrl / fetchedAt ---

    test('metadata extension: sourceUrl 写入 envelope.payload.source_url', () => {
        const envelope = adaptTransformToApiFormatOutputToEnvelope(HAPPY_PATH_TRANSFORM_OUTPUT, {
            sourceUrl: 'https://example.invalid/fotmob/match/4193673',
        });
        assert.equal(envelope.payload.source_url, 'https://example.invalid/fotmob/match/4193673');
    });

    test('metadata extension: finalUrl 写入 envelope.payload.final_url', () => {
        const envelope = adaptTransformToApiFormatOutputToEnvelope(HAPPY_PATH_TRANSFORM_OUTPUT, {
            finalUrl: 'https://example.invalid/fotmob/match/4193673#final',
        });
        assert.equal(envelope.payload.final_url, 'https://example.invalid/fotmob/match/4193673#final');
    });

    test('metadata extension: fetchedAt 写入 envelope.payload.fetched_at', () => {
        const envelope = adaptTransformToApiFormatOutputToEnvelope(HAPPY_PATH_TRANSFORM_OUTPUT, {
            fetchedAt: '2026-07-04T01:00:00.000Z',
        });
        assert.equal(envelope.payload.fetched_at, '2026-07-04T01:00:00.000Z');
    });

    test('metadata extension: sourceUrl 缺失时 payload.source_url 为 null', () => {
        const envelope = adaptTransformToApiFormatOutputToEnvelope(HAPPY_PATH_TRANSFORM_OUTPUT, {});
        assert.equal(envelope.payload.source_url, null);
    });

    test('metadata extension: finalUrl 缺失时 payload.final_url 为 null', () => {
        const envelope = adaptTransformToApiFormatOutputToEnvelope(HAPPY_PATH_TRANSFORM_OUTPUT, {});
        assert.equal(envelope.payload.final_url, null);
    });

    test('metadata extension: fetchedAt 缺失时 payload.fetched_at 为 null', () => {
        const envelope = adaptTransformToApiFormatOutputToEnvelope(HAPPY_PATH_TRANSFORM_OUTPUT, {});
        assert.equal(envelope.payload.fetched_at, null);
    });

    test('metadata extension: fetchedAt 不覆盖 captured_at（两个独立字段）', () => {
        const envelope = adaptTransformToApiFormatOutputToEnvelope(HAPPY_PATH_TRANSFORM_OUTPUT, {
            capturedAt: '2026-07-04T01:00:05.000Z',
            fetchedAt: '2026-07-04T01:00:00.000Z',
        });
        assert.equal(envelope.payload.captured_at, '2026-07-04T01:00:05.000Z');
        assert.equal(envelope.payload.fetched_at, '2026-07-04T01:00:00.000Z');
        assert.notEqual(envelope.payload.fetched_at, envelope.payload.captured_at);
    });

    test('metadata extension: _meta.extractedAt 不覆盖 fetched_at', () => {
        const envelope = adaptTransformToApiFormatOutputToEnvelope(HAPPY_PATH_TRANSFORM_OUTPUT, {
            fetchedAt: '2026-07-04T01:00:00.000Z',
        });
        assert.equal(envelope.payload.fetched_at, '2026-07-04T01:00:00.000Z');
        const extractedEntry = envelope.fields.find(f => f.field_path === '_meta.extractedAt');
        assert.ok(extractedEntry, '_meta.extractedAt audit field should exist');
        assert.notEqual(envelope.payload.fetched_at, extractedEntry.value,
            'fetched_at must not equal _meta.extractedAt');
    });

    test('metadata extension: matchTimeUTC / utcTime 不覆盖 fetched_at', () => {
        const envelope = adaptTransformToApiFormatOutputToEnvelope(HAPPY_PATH_TRANSFORM_OUTPUT, {
            fetchedAt: '2026-07-04T01:00:00.000Z',
        });
        assert.notEqual(envelope.payload.fetched_at, HAPPY_PATH_TRANSFORM_OUTPUT.general.matchTimeUTC,
            'fetched_at must not equal matchTimeUTC');
        assert.notEqual(envelope.payload.fetched_at, HAPPY_PATH_TRANSFORM_OUTPUT.header.status.utcTime,
            'fetched_at must not equal utcTime');
    });

    test('metadata extension: 所有 metadata 字段不产生 ALLOWED_CANDIDATE', () => {
        const envelope = adaptTransformToApiFormatOutputToEnvelope(HAPPY_PATH_TRANSFORM_OUTPUT, {
            sourceUrl: 'https://example.invalid/fotmob/match/4193673',
            finalUrl: 'https://example.invalid/fotmob/match/4193673#final',
            fetchedAt: '2026-07-04T01:00:00.000Z',
            capturedAt: '2026-07-04T01:00:05.000Z',
        });
        for (const f of envelope.fields) {
            assert.notEqual(
                f.model_eligibility,
                MODEL_ELIGIBILITY.ALLOWED_CANDIDATE,
                `field "${f.field_path}" must not be ALLOWED_CANDIDATE`
            );
            assert.notEqual(
                f.model_eligibility,
                MODEL_ELIGIBILITY.CANDIDATE_IF_CUTOFF_VALID,
                `field "${f.field_path}" must not be CANDIDATE_IF_CUTOFF_VALID`
            );
        }
    });

    test('metadata extension: fetched_at/source_url/final_url 不存在于 envelope.fields 中', () => {
        const envelope = adaptTransformToApiFormatOutputToEnvelope(HAPPY_PATH_TRANSFORM_OUTPUT, {
            sourceUrl: 'https://example.invalid/fotmob/match/4193673',
            finalUrl: 'https://example.invalid/fotmob/match/4193673#final',
            fetchedAt: '2026-07-04T01:00:00.000Z',
        });
        // payload metadata 应该只在 envelope.payload 中，不出现在 envelope.fields
        const payloadMetaPaths = ['payload.fetched_at', 'payload.source_url', 'payload.final_url'];
        for (const metaPath of payloadMetaPaths) {
            const entry = envelope.fields.find(f => f.field_path === metaPath);
            assert.equal(entry, undefined,
                `"${metaPath}" should not appear in envelope.fields — payload metadata only`);
        }
    });
});
