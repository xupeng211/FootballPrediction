/**
 * FotMobParserOutputEnvelope Metadata Handoff Fixture Test
 * =======================================================
 *
 * 使用静态 raw-record fixture + transformToApiFormat output fixture 验证
 * DATA-L1E-4 metadata handoff contract。
 *
 * 纯静态测试：不访问网络、不写文件、不写 DB/raw/data、不运行 FotMob parser runtime。
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

function buildAdapterOptionsFromRawRecord(rawRecord) {
    return {
        source: 'fotmob',
        dataVersion:
            rawRecord.data_version
            ?? rawRecord.dataVersion
            ?? rawRecord.raw_data?._meta?.data_version
            ?? 'unknown',
        payloadHash:
            rawRecord.data_hash
            ?? rawRecord.payload_hash
            ?? rawRecord.raw_data_hash
            ?? rawRecord.stable_raw_payload_hash
            ?? rawRecord.raw_data?._meta?.data_hash
            ?? null,
        storagePath:
            rawRecord.storage_path
            ?? rawRecord.storagePath
            ?? null,
        capturedAt:
            rawRecord.captured_at
            ?? rawRecord.capturedAt
            ?? null,
        fetchedAt:
            rawRecord.fetched_at
            ?? rawRecord.fetchedAt
            ?? rawRecord.raw_data?._meta?.fetched_at
            ?? null,
        parsedAt: null,
        parserName: 'NextDataParser.transformToApiFormat',
        parserVersion: 'legacy-static',
    };
}

function fieldByPath(fields, fieldPath) {
    return fields.find(f => f.field_path === fieldPath);
}

function assertNoSafeFields(envelope) {
    for (const field of envelope.fields) {
        assert.notEqual(
            field.model_eligibility,
            MODEL_ELIGIBILITY.ALLOWED_CANDIDATE,
            `field "${field.field_path}" must not be ALLOWED_CANDIDATE`
        );
        assert.notEqual(
            field.model_eligibility,
            MODEL_ELIGIBILITY.CANDIDATE_IF_CUTOFF_VALID,
            `field "${field.field_path}" must not be CANDIDATE_IF_CUTOFF_VALID`
        );
    }
}

// ===========================================================================
// Fixture metadata handoff
// ===========================================================================

describe('DATA-L1E-5 metadata handoff fixture', () => {
    const rawRecord = loadFixture('metadata_handoff_raw_record_boundary_a_fixture.json');
    const transformOutput = loadFixture('metadata_handoff_transform_output_boundary_a_fixture.json');
    const options = buildAdapterOptionsFromRawRecord(rawRecord);
    const envelope = adaptTransformToApiFormatOutputToEnvelope(transformOutput, options);

    test('raw record metadata 能进入 adapter options', () => {
        assert.equal(options.source, 'fotmob');
        assert.equal(options.dataVersion, 'fotmob_html_hyd_v1');
        assert.equal(options.payloadHash, 'sha256:fixture-data-hash-001');
        assert.equal(options.storagePath, null);
        assert.equal(options.capturedAt, '2026-07-04T01:00:05.000Z');
        assert.equal(options.fetchedAt, '2026-07-04T01:00:00.000Z');
        assert.equal(options.parsedAt, null);
        assert.equal(options.parserName, 'NextDataParser.transformToApiFormat');
        assert.equal(options.parserVersion, 'legacy-static');
    });

    test('payloadHash 优先使用 rawRecord.data_hash', () => {
        assert.equal(rawRecord.raw_data_hash, 'sha256:fixture-raw-data-hash-001');
        assert.equal(rawRecord.stable_raw_payload_hash, 'sha256:fixture-stable-raw-payload-hash-001');
        assert.equal(rawRecord.payload_hash, null);
        assert.equal(rawRecord.raw_data._meta.data_hash, 'sha256:fixture-meta-data-hash-001');
        assert.equal(options.payloadHash, rawRecord.data_hash);
    });

    test('metadata 进入 envelope 正确位置', () => {
        const validation = validateEnvelopeShape(envelope);
        assert.ok(validation.valid, `envelope should pass shape validation: ${validation.errors.join('; ')}`);
        assert.equal(envelope.source, 'fotmob');
        assert.equal(envelope.match_id, 'fixture-metadata-001');
        assert.equal(envelope.payload.data_version, 'fotmob_html_hyd_v1');
        assert.equal(envelope.payload.payload_hash, 'sha256:fixture-data-hash-001');
        assert.equal(envelope.payload.storage_path, null);
        assert.equal(envelope.payload.captured_at, '2026-07-04T01:00:05.000Z');
        assert.equal(envelope.parser.parser_name, 'NextDataParser.transformToApiFormat');
        assert.equal(envelope.parser.parser_version, 'legacy-static');
        assert.equal(envelope.parser.parsed_at, null);
    });

    test('fetchedAt 不冒充 capturedAt', () => {
        assert.equal(envelope.payload.captured_at, rawRecord.captured_at);
        assert.notEqual(envelope.payload.captured_at, rawRecord.fetched_at);
        assert.equal(Object.prototype.hasOwnProperty.call(envelope.payload, 'fetched_at'), false);
    });

    test('_meta.extractedAt 保留为 audit-only 且不覆盖 captured_at', () => {
        const extractedAtEntry = fieldByPath(envelope.fields, '_meta.extractedAt');
        assert.ok(extractedAtEntry, '_meta.extractedAt entry should exist');
        assert.equal(extractedAtEntry.value, transformOutput._meta.extractedAt);
        assert.equal(extractedAtEntry.model_eligibility, MODEL_ELIGIBILITY.AUDIT_ONLY);
        assert.notEqual(extractedAtEntry.value, envelope.payload.captured_at);
        assert.ok(
            extractedAtEntry.warnings.some(w => w.includes('supplementary audit evidence only')),
            '_meta.extractedAt should be retained as audit-only context'
        );
    });

    test('matchTimeUTC / utcTime 不当作 captured_at', () => {
        assert.notEqual(envelope.payload.captured_at, transformOutput.general.matchTimeUTC);
        assert.notEqual(envelope.payload.captured_at, transformOutput.header.status.utcTime);
    });

    test('source_url / final_url 当前保持 null', () => {
        assert.ok(rawRecord.source_url);
        assert.ok(rawRecord.final_url);
        assert.ok(rawRecord.raw_data._meta.request_url);
        assert.ok(rawRecord.raw_data._meta.final_url);
        // Current adapter has no sourceUrl/finalUrl options. Future adapter extension required.
        assert.equal(envelope.payload.source_url, null);
        assert.equal(envelope.payload.final_url, null);
    });

    test('不产生任何 safe field', () => {
        assertNoSafeFields(envelope);
    });

    test('postmatch / unknown timing / raw blocks 保持 forbidden', () => {
        assert.equal(
            fieldByPath(envelope.fields, 'content.stats').model_eligibility,
            MODEL_ELIGIBILITY.FORBIDDEN_POSTMATCH
        );
        assert.equal(
            fieldByPath(envelope.fields, 'content.shotmap').model_eligibility,
            MODEL_ELIGIBILITY.FORBIDDEN_POSTMATCH
        );
        assert.equal(
            fieldByPath(envelope.fields, 'content.events').model_eligibility,
            MODEL_ELIGIBILITY.FORBIDDEN_POSTMATCH
        );
        assert.equal(
            fieldByPath(envelope.fields, 'content.lineup').model_eligibility,
            MODEL_ELIGIBILITY.FORBIDDEN_UNKNOWN_TIMING
        );
        assert.equal(
            fieldByPath(envelope.fields, 'content').model_eligibility,
            MODEL_ELIGIBILITY.FORBIDDEN_RAW_ONLY
        );
        assert.equal(
            fieldByPath(envelope.fields, 'general').model_eligibility,
            MODEL_ELIGIBILITY.FORBIDDEN_RAW_ONLY
        );
        assert.equal(
            fieldByPath(envelope.fields, 'header').model_eligibility,
            MODEL_ELIGIBILITY.FORBIDDEN_RAW_ONLY
        );
    });
});

// ===========================================================================
// Missing metadata remains null / unknown
// ===========================================================================

describe('DATA-L1E-5 missing metadata fixture behavior', () => {
    const minimalRawRecord = {
        match_id: 'fixture-metadata-minimal-001',
        raw_data: {},
    };

    const minimalTransformOutput = {
        matchId: 'fixture-metadata-minimal-001',
        content: {},
        general: {
            homeTeam: { name: 'A' },
            awayTeam: { name: 'B' },
            matchTimeUTC: '2026-07-04T12:00:00Z',
        },
        header: {
            status: { utcTime: '2026-07-04T12:00:00Z' },
        },
        _meta: {
            source: 'web_infiltration',
        },
    };

    const options = buildAdapterOptionsFromRawRecord(minimalRawRecord);
    const envelope = adaptTransformToApiFormatOutputToEnvelope(minimalTransformOutput, options);

    test('缺失 metadata 时 adapter options 保持 null / unknown', () => {
        assert.equal(options.dataVersion, 'unknown');
        assert.equal(options.payloadHash, null);
        assert.equal(options.storagePath, null);
        assert.equal(options.capturedAt, null);
        assert.equal(options.fetchedAt, null);
    });

    test('缺失 metadata 时 envelope payload 保持 null / unknown', () => {
        const validation = validateEnvelopeShape(envelope);
        assert.ok(validation.valid, `minimal envelope should pass: ${validation.errors.join('; ')}`);
        assert.equal(envelope.payload.data_version, 'unknown');
        assert.equal(envelope.payload.payload_hash, null);
        assert.equal(envelope.payload.storage_path, null);
        assert.equal(envelope.payload.captured_at, null);
    });

    test('minimal matchTimeUTC / utcTime 不会被当作 captured_at', () => {
        assert.notEqual(envelope.payload.captured_at, minimalTransformOutput.general.matchTimeUTC);
        assert.notEqual(envelope.payload.captured_at, minimalTransformOutput.header.status.utcTime);
        assert.equal(envelope.payload.captured_at, null);
    });

    test('minimal fixture 不产生任何 safe field', () => {
        assertNoSafeFields(envelope);
    });
});
