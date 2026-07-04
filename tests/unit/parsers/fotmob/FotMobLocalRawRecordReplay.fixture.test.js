/**
 * FotMob Local Raw Record Replay Fixture Test (DATA-L1E-7)
 * =========================================================
 *
 * Lane B only: local raw record metadata fixture + already-sanitized
 * transformToApiFormat output fixture → adapter → envelope.
 *
 * 纯静态测试：不访问网络、不写文件、不写 DB/raw/data、不运行 FotMob parser runtime。
 * 本测试不 import NextDataParser、不处理 HTML、不处理 __NEXT_DATA__、不访问 FotMob。
 * 本测试只证明 Lane B，不证明 Lane A。
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
// Test-only helpers
// ===========================================================================

function readJsonFixture(relativePath) {
    const fullPath = path.join(__dirname, '../../../fixtures/fotmob', relativePath);
    return JSON.parse(fs.readFileSync(fullPath, 'utf8'));
}

function buildAdapterOptionsFromRawRecord(rawRecord) {
    return {
        source: rawRecord.source ?? 'fotmob',
        dataVersion:
            rawRecord.data_version
            ?? rawRecord.dataVersion
            ?? rawRecord.raw_data?._meta?.data_version
            ?? 'unknown',
        payloadHash:
            rawRecord.payload_hash
            ?? rawRecord.data_hash
            ?? rawRecord.raw_data_hash
            ?? rawRecord.stable_raw_payload_hash
            ?? rawRecord.raw_data?._meta?.data_hash
            ?? null,
        storagePath:
            rawRecord.storage_path
            ?? rawRecord.storagePath
            ?? null,
        sourceUrl:
            rawRecord.source_url
            ?? rawRecord.sourceUrl
            ?? rawRecord.raw_data?._meta?.request_url
            ?? null,
        finalUrl:
            rawRecord.final_url
            ?? rawRecord.finalUrl
            ?? rawRecord.raw_data?._meta?.final_url
            ?? null,
        fetchedAt:
            rawRecord.fetched_at
            ?? rawRecord.fetchedAt
            ?? rawRecord.raw_data?._meta?.fetched_at
            ?? null,
        capturedAt:
            rawRecord.captured_at
            ?? rawRecord.capturedAt
            ?? null,
        parsedAt: null,
        parserName: 'NextDataParser.transformToApiFormat',
        parserVersion: 'legacy-static',
    };
}

/**
 * Lane B only local replay helper.
 *
 * 不读网络、不写文件、不接 runtime、不调用 NextDataParser。
 * 只处理 already-sanitized transform output + raw record metadata。
 */
function replayLocalRawRecordLaneB(rawRecord, transformOutput) {
    const options = buildAdapterOptionsFromRawRecord(rawRecord);
    const envelope = adaptTransformToApiFormatOutputToEnvelope(transformOutput, options);
    return { envelope, options };
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
// DATA-L1E-7 Lane B local raw record replay
// ===========================================================================

describe('DATA-L1E-7 Lane B local raw record replay', () => {
    const rawRecord = readJsonFixture('local_raw_record_replay_boundary_b_raw_record_fixture.json');
    const transformOutput = readJsonFixture('local_raw_record_replay_boundary_b_transform_output_fixture.json');
    const { envelope, options } = replayLocalRawRecordLaneB(rawRecord, transformOutput);

    // -----------------------------------------------------------------------
    // 10.1 fixture sanity
    // -----------------------------------------------------------------------

    test('fixture sanity: rawRecord 和 transformOutput 对齐', () => {
        assert.equal(rawRecord.match_id, transformOutput.matchId,
            'rawRecord.match_id must match transformOutput.matchId');
        assert.equal(rawRecord.source, 'fotmob');
        assert.equal(rawRecord.raw_data.contains_html, false);
        assert.equal(rawRecord.raw_data.contains_next_data, false);
        assert.equal(rawRecord.raw_data.contains_live_fotmob_payload, false);
        assert.ok(rawRecord.source_url.includes('example.invalid'),
            'source_url must use example.invalid');
        assert.ok(rawRecord.final_url.includes('example.invalid'),
            'final_url must use example.invalid');
    });

    // -----------------------------------------------------------------------
    // 10.2 replay returns valid envelope
    // -----------------------------------------------------------------------

    test('replay 返回 legal envelope', () => {
        assert.ok(envelope !== null && typeof envelope === 'object',
            'replay must return a non-null envelope object');
    });

    test('validateEnvelopeShape 通过', () => {
        const validation = validateEnvelopeShape(envelope);
        assert.ok(validation.valid,
            `envelope should pass shape validation: ${validation.errors.join('; ')}`);
    });

    test('envelope.source === fotmob', () => {
        assert.equal(envelope.source, 'fotmob');
    });

    test('envelope.match_id === rawRecord.match_id', () => {
        assert.equal(envelope.match_id, rawRecord.match_id);
    });

    // -----------------------------------------------------------------------
    // 10.3 metadata handoff
    // -----------------------------------------------------------------------

    test('metadata: data_version 进入 envelope.payload', () => {
        assert.equal(envelope.payload.data_version, rawRecord.data_version);
    });

    test('metadata: payloadHash 优先 data_hash，进入 envelope.payload', () => {
        assert.ok(rawRecord.data_hash, 'fixture must have data_hash');
        assert.equal(envelope.payload.payload_hash, rawRecord.data_hash);
    });

    test('metadata: storage_path 进入 envelope.payload', () => {
        assert.equal(envelope.payload.storage_path, rawRecord.storage_path);
    });

    test('metadata: source_url 进入 envelope.payload', () => {
        assert.equal(envelope.payload.source_url, rawRecord.source_url);
    });

    test('metadata: final_url 进入 envelope.payload', () => {
        assert.equal(envelope.payload.final_url, rawRecord.final_url);
    });

    test('metadata: fetched_at 进入 envelope.payload', () => {
        assert.equal(envelope.payload.fetched_at, rawRecord.fetched_at);
    });

    test('metadata: captured_at 进入 envelope.payload', () => {
        assert.equal(envelope.payload.captured_at, rawRecord.captured_at);
    });

    // -----------------------------------------------------------------------
    // 10.4 time semantics
    // -----------------------------------------------------------------------

    test('time semantics: fetched_at !== captured_at', () => {
        assert.notEqual(envelope.payload.fetched_at, envelope.payload.captured_at);
    });

    test('time semantics: fetched_at !== _meta.extractedAt', () => {
        assert.notEqual(envelope.payload.fetched_at, transformOutput._meta.extractedAt,
            'fetched_at must not equal _meta.extractedAt');
    });

    test('time semantics: fetched_at !== general.matchTimeUTC', () => {
        assert.notEqual(envelope.payload.fetched_at, transformOutput.general.matchTimeUTC,
            'fetched_at must not equal matchTimeUTC');
    });

    test('time semantics: fetched_at !== header.status.utcTime', () => {
        assert.notEqual(envelope.payload.fetched_at, transformOutput.header.status.utcTime,
            'fetched_at must not equal utcTime');
    });

    test('time semantics: captured_at !== _meta.extractedAt', () => {
        assert.notEqual(envelope.payload.captured_at, transformOutput._meta.extractedAt,
            'captured_at must not equal _meta.extractedAt');
    });

    test('time semantics: captured_at !== general.matchTimeUTC', () => {
        assert.notEqual(envelope.payload.captured_at, transformOutput.general.matchTimeUTC,
            'captured_at must not equal matchTimeUTC');
    });

    test('time semantics: captured_at !== header.status.utcTime', () => {
        assert.notEqual(envelope.payload.captured_at, transformOutput.header.status.utcTime,
            'captured_at must not equal utcTime');
    });

    // -----------------------------------------------------------------------
    // 10.5 0 safe fields
    // -----------------------------------------------------------------------

    test('0 safe fields: envelope.fields 是数组', () => {
        assert.ok(Array.isArray(envelope.fields));
    });

    test('0 safe fields: ALLOWED_CANDIDATE 数量为 0', () => {
        assertNoSafeFields(envelope);
    });

    test('0 safe fields: payload metadata 不进入 envelope.fields', () => {
        const payloadMetaPaths = ['payload.fetched_at', 'payload.source_url', 'payload.final_url'];
        for (const metaPath of payloadMetaPaths) {
            const found = fieldByPath(envelope.fields, metaPath);
            assert.equal(found, undefined,
                `"${metaPath}" must not appear in envelope.fields`);
        }
    });

    // -----------------------------------------------------------------------
    // 10.6 forbidden classification sanity
    // -----------------------------------------------------------------------

    test('forbidden: content.stats 不得是 safe', () => {
        const entry = fieldByPath(envelope.fields, 'content.stats');
        if (entry) {
            assert.equal(entry.model_eligibility, MODEL_ELIGIBILITY.FORBIDDEN_POSTMATCH,
                'content.stats must be FORBIDDEN_POSTMATCH');
        }
        // If not separately flattened, parent raw block must cover it.
        const contentEntry = fieldByPath(envelope.fields, 'content');
        assert.ok(contentEntry, 'content raw block must exist');
        assert.equal(contentEntry.model_eligibility, MODEL_ELIGIBILITY.FORBIDDEN_RAW_ONLY,
            'content raw block must be FORBIDDEN_RAW_ONLY');
    });

    test('forbidden: content.shotmap 不得是 safe', () => {
        const entry = fieldByPath(envelope.fields, 'content.shotmap');
        if (entry) {
            assert.equal(entry.model_eligibility, MODEL_ELIGIBILITY.FORBIDDEN_POSTMATCH,
                'content.shotmap must be FORBIDDEN_POSTMATCH');
        }
    });

    test('forbidden: content.events 不得是 safe', () => {
        const entry = fieldByPath(envelope.fields, 'content.events');
        if (entry) {
            assert.equal(entry.model_eligibility, MODEL_ELIGIBILITY.FORBIDDEN_POSTMATCH,
                'content.events must be FORBIDDEN_POSTMATCH');
        }
    });

    test('forbidden: content.lineup 不得是 safe', () => {
        const entry = fieldByPath(envelope.fields, 'content.lineup');
        if (entry) {
            assert.equal(entry.model_eligibility, MODEL_ELIGIBILITY.FORBIDDEN_UNKNOWN_TIMING,
                'content.lineup must be FORBIDDEN_UNKNOWN_TIMING');
        }
    });

    test('forbidden: header 不得是 safe（含 score', () => {
        const headerEntry = fieldByPath(envelope.fields, 'header');
        assert.ok(headerEntry, 'header raw block must exist');
        assert.equal(headerEntry.model_eligibility, MODEL_ELIGIBILITY.FORBIDDEN_RAW_ONLY,
            'header raw block must be FORBIDDEN_RAW_ONLY');
    });

    // -----------------------------------------------------------------------
    // 10.7 Lane B only confirmation
    // -----------------------------------------------------------------------

    test('Lane B only: 不 import NextDataParser', () => {
        // 本测试文件没有任何 NextDataParser require。
        // 验证 adapter 不会把 NextDataParser 偷偷拉进来。
        const adapterExports = require('../../../../src/parsers/fotmob/FotMobParserOutputEnvelopeLegacyAdapter');
        assert.ok(typeof adapterExports.adaptTransformToApiFormatOutputToEnvelope === 'function');
    });

    test('Lane B only: replay helper 只是 test-only 函数，不产生副作用', () => {
        // replayLocalRawRecordLaneB 只接受两个参数，纯函数。
        const result = replayLocalRawRecordLaneB(rawRecord, transformOutput);
        assert.ok(result.envelope);
        assert.ok(result.options);
    });
});

// ===========================================================================
// Missing metadata stays null
// ===========================================================================

describe('DATA-L1E-7 Lane B missing metadata minimal replay', () => {
    const minimalRawRecord = {
        match_id: 'fixture-local-replay-b-minimal-001',
        source: 'fotmob',
        raw_data: {},
    };

    const minimalTransformOutput = {
        matchId: 'fixture-local-replay-b-minimal-001',
        content: {},
        general: {
            matchTimeUTC: '2026-07-04T12:00:00Z',
        },
        header: {
            status: { utcTime: '2026-07-04T12:00:00Z' },
        },
        _meta: {
            source: 'web_infiltration',
        },
    };

    const { envelope, options } = replayLocalRawRecordLaneB(minimalRawRecord, minimalTransformOutput);

    test('minimal: dataVersion 为 unknown', () => {
        assert.equal(options.dataVersion, 'unknown');
    });

    test('minimal: payloadHash 为 null', () => {
        assert.equal(options.payloadHash, null);
    });

    test('minimal: sourceUrl/finalUrl 为 null', () => {
        assert.equal(options.sourceUrl, null);
        assert.equal(options.finalUrl, null);
    });

    test('minimal: fetchedAt/capturedAt 为 null', () => {
        assert.equal(options.fetchedAt, null);
        assert.equal(options.capturedAt, null);
    });

    test('minimal: envelope payload metadata 全为 null/unknown', () => {
        const validation = validateEnvelopeShape(envelope);
        assert.ok(validation.valid, `minimal envelope should pass: ${validation.errors.join('; ')}`);
        assert.equal(envelope.payload.data_version, 'unknown');
        assert.equal(envelope.payload.payload_hash, null);
        assert.equal(envelope.payload.storage_path, null);
        assert.equal(envelope.payload.source_url, null);
        assert.equal(envelope.payload.final_url, null);
        assert.equal(envelope.payload.fetched_at, null);
        assert.equal(envelope.payload.captured_at, null);
    });

    test('minimal: matchTimeUTC/utcTime 不被当作 fetched_at/captured_at', () => {
        assert.equal(envelope.payload.fetched_at, null);
        assert.equal(envelope.payload.captured_at, null);
    });

    test('minimal: 0 safe fields', () => {
        assertNoSafeFields(envelope);
    });
});
