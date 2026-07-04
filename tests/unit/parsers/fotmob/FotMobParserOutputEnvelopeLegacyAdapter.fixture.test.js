/**
 * FotMobParserOutputEnvelopeLegacyAdapter Fixture Test
 * ===================================================
 *
 * 使用静态 fixture 验证 DATA-L1E-2 adapter 对真实结构 transformToApiFormat output 的兼容性。
 * 纯静态测试：不访问网络、文件只读 fixture、不写 DB/raw/data。
 *
 * lifecycle: permanent
 */

'use strict';

const { describe, test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const {
    adaptTransformToApiFormatOutputToEnvelope,
} = require('../../../../src/parsers/fotmob/FotMobParserOutputEnvelopeLegacyAdapter');

const {
    MODEL_ELIGIBILITY,
    validateEnvelopeShape,
} = require('../../../../src/parsers/fotmob/FotMobParserOutputEnvelope');

// ===========================================================================
// Helpers
// ===========================================================================

function loadFixture(name) {
    const filePath = path.join(__dirname, '../../../fixtures/fotmob', name);
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function fieldByPath(fields, p) {
    return fields.find(f => f.field_path === p);
}

// ===========================================================================
// Rich fixture tests
// ===========================================================================

describe('Rich fixture', () => {
    const richFixture = loadFixture('nextdata_transform_output_boundary_a_rich_fixture.json');
    const envelope = adaptTransformToApiFormatOutputToEnvelope(richFixture);

    test('应生成合法 envelope shape', () => {
        const validation = validateEnvelopeShape(envelope);
        assert.ok(validation.valid, `envelope should pass shape validation: ${validation.errors.join('; ')}`);
        assert.equal(envelope.match_id, 'fixture-rich-001');
        assert.ok(Array.isArray(envelope.fields));
        assert.ok(envelope.fields.length > 0);
        assert.ok(Array.isArray(envelope.warnings));
    });

    test('payload metadata 默认值', () => {
        assert.equal(envelope.payload.data_version, 'unknown');
        assert.equal(envelope.payload.payload_hash, null);
        assert.equal(envelope.payload.storage_path, null);
        assert.equal(envelope.payload.captured_at, null);
    });

    test('parser metadata 默认值', () => {
        assert.equal(envelope.parser.parser_name, 'NextDataParser.transformToApiFormat');
        assert.equal(envelope.parser.parser_version, 'legacy-static');
        assert.equal(envelope.parser.parsed_at, null);
    });

    test('matchId 字段存在', () => {
        const entry = fieldByPath(envelope.fields, 'matchId');
        assert.ok(entry, 'matchId entry should exist');
        assert.equal(entry.value, 'fixture-rich-001');
    });

    test('content 整块标记为 forbidden_raw_only', () => {
        const entry = fieldByPath(envelope.fields, 'content');
        assert.ok(entry, 'content entry should exist');
        assert.equal(entry.model_eligibility, MODEL_ELIGIBILITY.FORBIDDEN_RAW_ONLY);
    });

    test('general 整块标记为 forbidden_raw_only', () => {
        const entry = fieldByPath(envelope.fields, 'general');
        assert.ok(entry, 'general entry should exist');
        assert.equal(entry.model_eligibility, MODEL_ELIGIBILITY.FORBIDDEN_RAW_ONLY);
    });

    test('header 整块标记为 forbidden_raw_only', () => {
        const entry = fieldByPath(envelope.fields, 'header');
        assert.ok(entry, 'header entry should exist');
        assert.equal(entry.model_eligibility, MODEL_ELIGIBILITY.FORBIDDEN_RAW_ONLY);
    });

    test('content.stats 标记为 forbidden_postmatch', () => {
        const entry = fieldByPath(envelope.fields, 'content.stats');
        assert.ok(entry, 'content.stats entry should exist');
        assert.equal(entry.model_eligibility, MODEL_ELIGIBILITY.FORBIDDEN_POSTMATCH);
        assert.ok(typeof entry.value === 'object', 'stats value should be object');
    });

    test('content.shotmap 标记为 forbidden_postmatch', () => {
        const entry = fieldByPath(envelope.fields, 'content.shotmap');
        assert.ok(entry, 'content.shotmap entry should exist');
        assert.equal(entry.model_eligibility, MODEL_ELIGIBILITY.FORBIDDEN_POSTMATCH);
        assert.ok(Array.isArray(entry.value));
    });

    test('content.events 标记为 forbidden_postmatch', () => {
        const entry = fieldByPath(envelope.fields, 'content.events');
        assert.ok(entry, 'content.events entry should exist');
        assert.equal(entry.model_eligibility, MODEL_ELIGIBILITY.FORBIDDEN_POSTMATCH);
    });

    test('content.lineup 标记为 forbidden_unknown_timing', () => {
        const entry = fieldByPath(envelope.fields, 'content.lineup');
        assert.ok(entry, 'content.lineup entry should exist');
        assert.equal(entry.model_eligibility, MODEL_ELIGIBILITY.FORBIDDEN_UNKNOWN_TIMING);
    });

    test('不产生任何 ALLOWED_CANDIDATE 字段', () => {
        for (const f of envelope.fields) {
            assert.notEqual(f.model_eligibility, MODEL_ELIGIBILITY.ALLOWED_CANDIDATE,
                `field "${f.field_path}" must not be ALLOWED_CANDIDATE`);
            assert.notEqual(f.model_eligibility, MODEL_ELIGIBILITY.CANDIDATE_IF_CUTOFF_VALID,
                `field "${f.field_path}" must not be CANDIDATE_IF_CUTOFF_VALID`);
        }
    });

    test('_meta 子字段存在且标记为 audit_only', () => {
        const sourceEntry = fieldByPath(envelope.fields, '_meta.source');
        assert.ok(sourceEntry, '_meta.source should exist');
        assert.equal(sourceEntry.value, 'web_infiltration');
        assert.equal(sourceEntry.model_eligibility, MODEL_ELIGIBILITY.AUDIT_ONLY);

        const hasStatsEntry = fieldByPath(envelope.fields, '_meta.hasStats');
        assert.ok(hasStatsEntry, '_meta.hasStats should exist');
        assert.equal(hasStatsEntry.value, true);

        const hasLineupEntry = fieldByPath(envelope.fields, '_meta.hasLineup');
        assert.ok(hasLineupEntry, '_meta.hasLineup should exist');
        assert.equal(hasLineupEntry.value, true);

        const hasShotmapEntry = fieldByPath(envelope.fields, '_meta.hasShotmap');
        assert.ok(hasShotmapEntry, '_meta.hasShotmap should exist');
        assert.equal(hasShotmapEntry.value, true);
    });

    test('_meta.extractedAt 作为 audit-only 存在', () => {
        const entry = fieldByPath(envelope.fields, '_meta.extractedAt');
        assert.ok(entry, '_meta.extractedAt should exist');
        assert.equal(entry.model_eligibility, MODEL_ELIGIBILITY.AUDIT_ONLY);
        assert.ok(entry.warnings.some(w => w.includes('parser execution time')),
            'should warn about extractedAt being parser time');
    });
});

// ===========================================================================
// Rich fixture with options metadata
// ===========================================================================

describe('Rich fixture with options metadata', () => {
    const richFixture = loadFixture('nextdata_transform_output_boundary_a_rich_fixture.json');
    const envelope = adaptTransformToApiFormatOutputToEnvelope(richFixture, {
        dataVersion: 'fotmob_html_hyd_v1',
        payloadHash: 'fixture-hash-001',
        storagePath: null,
        capturedAt: '2026-07-04T01:00:00.000Z',
        parsedAt: null,
    });

    test('data_version 被保留', () => {
        assert.equal(envelope.payload.data_version, 'fotmob_html_hyd_v1');
    });

    test('payload_hash 被保留', () => {
        assert.equal(envelope.payload.payload_hash, 'fixture-hash-001');
    });

    test('storage_path null 被保留', () => {
        assert.equal(envelope.payload.storage_path, null);
    });

    test('captured_at 被保留', () => {
        assert.equal(envelope.payload.captured_at, '2026-07-04T01:00:00.000Z');
    });

    test('parsed_at null 被保留', () => {
        assert.equal(envelope.parser.parsed_at, null);
    });

    test('_meta.extractedAt audit field 仍存在且不覆盖 captured_at', () => {
        const entry = fieldByPath(envelope.fields, '_meta.extractedAt');
        assert.ok(entry, '_meta.extractedAt should still exist');
        assert.equal(entry.model_eligibility, MODEL_ELIGIBILITY.AUDIT_ONLY);
        // captured_at 是 '2026-07-04T01:00:00.000Z'，extractedAt 是 '2026-07-04T00:00:00.000Z'
        assert.ok(
            entry.warnings.some(w => w.includes('captured_at or fetched_at is present')),
            'should warn extractedAt is supplementary'
        );
        assert.notEqual(envelope.payload.captured_at, entry.value,
            'extractedAt value must not equal captured_at');
    });
});

// ===========================================================================
// Minimal fixture tests
// ===========================================================================

describe('Minimal fixture', () => {
    const minimalFixture = loadFixture('nextdata_transform_output_boundary_a_minimal_fixture.json');
    const envelope = adaptTransformToApiFormatOutputToEnvelope(minimalFixture);

    test('应生成合法 envelope shape', () => {
        const validation = validateEnvelopeShape(envelope);
        assert.ok(validation.valid, `minimal envelope should pass: ${validation.errors.join('; ')}`);
        assert.equal(envelope.match_id, 'fixture-minimal-001');
    });

    test('payload metadata 均为 default/null', () => {
        assert.equal(envelope.payload.data_version, 'unknown');
        assert.equal(envelope.payload.payload_hash, null);
        assert.equal(envelope.payload.storage_path, null);
        assert.equal(envelope.payload.captured_at, null);
    });

    test('不产生任何 ALLOWED_CANDIDATE 字段', () => {
        for (const f of envelope.fields) {
            assert.notEqual(f.model_eligibility, MODEL_ELIGIBILITY.ALLOWED_CANDIDATE,
                `field "${f.field_path}" must not be ALLOWED_CANDIDATE`);
            assert.notEqual(f.model_eligibility, MODEL_ELIGIBILITY.CANDIDATE_IF_CUTOFF_VALID,
                `field "${f.field_path}" must not be CANDIDATE_IF_CUTOFF_VALID`);
        }
    });

    test('content empty 但不崩溃', () => {
        const entry = fieldByPath(envelope.fields, 'content');
        if (entry) {
            assert.equal(entry.model_eligibility, MODEL_ELIGIBILITY.FORBIDDEN_RAW_ONLY);
        }
        // content 可能为 undefined（empty object edge case）或 explicit null
    });

    test('不包含 content.stats 等子字段（fixture 没有这些数据）', () => {
        const statsEntry = fieldByPath(envelope.fields, 'content.stats');
        assert.equal(statsEntry, undefined, 'minimal fixture has no stats — should not create entry');
        const shotmapEntry = fieldByPath(envelope.fields, 'content.shotmap');
        assert.equal(shotmapEntry, undefined);
        const lineupEntry = fieldByPath(envelope.fields, 'content.lineup');
        assert.equal(lineupEntry, undefined);
    });

    test('_meta.source 存在且 audit_only', () => {
        const entry = fieldByPath(envelope.fields, '_meta.source');
        assert.ok(entry, '_meta.source should exist');
        assert.equal(entry.value, 'web_infiltration');
        assert.equal(entry.model_eligibility, MODEL_ELIGIBILITY.AUDIT_ONLY);
    });

    test('extractedAt 不存在（fixture 未提供）', () => {
        const entry = fieldByPath(envelope.fields, '_meta.extractedAt');
        assert.equal(entry, undefined, 'extractedAt should not be created when fixture lacks it');
    });
});
