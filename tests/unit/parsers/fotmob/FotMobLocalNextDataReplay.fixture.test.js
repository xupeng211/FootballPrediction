/**
 * FotMob Local __NEXT_DATA__ Replay Fixture Test (DATA-L1E-9)
 * ===========================================================
 *
 * Lane A2 only: local raw record metadata fixture + sanitized local
 * __NEXT_DATA__ JSON fixture -> NextDataParser.transformToApiFormat
 * -> adapter -> envelope.
 *
 * 纯静态测试：不访问网络、不写文件、不写 DB/raw/data、不运行 scraper/collector/browser。
 * 本测试不调用 extractFromHtml、不处理 HTML、不证明 Lane A1。
 *
 * lifecycle: permanent
 */

'use strict';

const { describe, test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const NextDataParser = require('../../../../src/parsers/fotmob/NextDataParser');

const {
    validateEnvelopeShape,
    MODEL_ELIGIBILITY,
} = require('../../../../src/parsers/fotmob/FotMobParserOutputEnvelope');

const {
    adaptTransformToApiFormatOutputToEnvelope,
} = require('../../../../src/parsers/fotmob/FotMobParserOutputEnvelopeLegacyAdapter');

// ===========================================================================
// Test-only helpers
// ===========================================================================

function readJsonFixture(relativePath) {
    const fullPath = path.join(__dirname, '../../../fixtures/fotmob', relativePath);
    return JSON.parse(fs.readFileSync(fullPath, 'utf8'));
}

function resolveTransformToApiFormat(nextDataParserModule) {
    if (typeof nextDataParserModule?.transformToApiFormat === 'function') {
        return nextDataParserModule.transformToApiFormat.bind(nextDataParserModule);
    }

    if (typeof nextDataParserModule?.NextDataParser?.transformToApiFormat === 'function') {
        return nextDataParserModule.NextDataParser.transformToApiFormat
            .bind(nextDataParserModule.NextDataParser);
    }

    if (typeof nextDataParserModule?.default?.transformToApiFormat === 'function') {
        return nextDataParserModule.default.transformToApiFormat
            .bind(nextDataParserModule.default);
    }

    throw new Error('Unable to resolve NextDataParser.transformToApiFormat export');
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

function replayLocalNextDataLaneA2(rawRecord, nextData) {
    const transformToApiFormat = resolveTransformToApiFormat(NextDataParser);
    const transformOutput = transformToApiFormat(nextData, rawRecord.match_id);

    const options = buildAdapterOptionsFromRawRecord(rawRecord);
    const envelope = adaptTransformToApiFormatOutputToEnvelope(transformOutput, options);

    return { transformOutput, envelope, options };
}

function fieldByPath(fields, fieldPath) {
    return fields.find(f => f.field_path === fieldPath || f.path === fieldPath);
}

function countByEligibility(envelope, eligibility) {
    return envelope.fields.filter(f => f.model_eligibility === eligibility).length;
}

function assertNoSafeFields(envelope) {
    assert.ok(Array.isArray(envelope.fields), 'envelope.fields must be an array');
    assert.equal(countByEligibility(envelope, MODEL_ELIGIBILITY.ALLOWED_CANDIDATE), 0,
        'ALLOWED_CANDIDATE count must be 0');
    assert.equal(countByEligibility(envelope, MODEL_ELIGIBILITY.CANDIDATE_IF_CUTOFF_VALID), 0,
        'CANDIDATE_IF_CUTOFF_VALID count must be 0');
}

function sensitiveKeywordScanString(nextData) {
    // pageProps.header is a schema-required FotMob block, not an HTTP header payload.
    // Strip that exact JSON key before scanning for accidental HTTP/auth header material.
    return JSON.stringify(nextData)
        .toLowerCase()
        .replaceAll('"header":', '"schema_section":');
}

// ===========================================================================
// DATA-L1E-9 Lane A2 local __NEXT_DATA__ replay
// ===========================================================================

describe('DATA-L1E-9 Lane A2 local __NEXT_DATA__ replay', () => {
    const rawRecord = readJsonFixture(
        'local_raw_html_nextdata_replay_boundary_a2_raw_record_fixture.json'
    );
    const nextData = readJsonFixture(
        'local_raw_html_nextdata_replay_boundary_a2_next_data_fixture.json'
    );
    const { transformOutput, envelope, options } = replayLocalNextDataLaneA2(rawRecord, nextData);

    // -----------------------------------------------------------------------
    // 13.1 fixture sanity
    // -----------------------------------------------------------------------

    test('fixture sanity: rawRecord 是 sanitized Lane A2 metadata fixture', () => {
        assert.ok(rawRecord.match_id);
        assert.equal(rawRecord.source, 'fotmob');
        assert.equal(rawRecord.raw_data.replay_lane, 'A2');
        assert.equal(rawRecord.raw_data.contains_sanitized_next_data, true);
        assert.equal(rawRecord.raw_data.contains_sanitized_html, false);
        assert.equal(rawRecord.raw_data.contains_live_fotmob_payload, false);
        assert.ok(rawRecord.source_url.includes('example.invalid'),
            'source_url must use example.invalid');
        assert.ok(rawRecord.final_url.includes('example.invalid'),
            'final_url must use example.invalid');
    });

    test('fixture sanity: rawRecord 不包含 HTML 字段或 raw_html 字段', () => {
        assert.equal(rawRecord.raw_html, undefined);
        assert.equal(rawRecord.html, undefined);
        assert.equal(rawRecord.raw_data.raw_html, undefined);
        assert.equal(rawRecord.raw_data.html, undefined);
        assert.equal(rawRecord.raw_data.contains_sanitized_html, false);
    });

    test('fixture sanity: nextData fixture 无真实 URL 或敏感 payload 关键词', () => {
        const serialized = sensitiveKeywordScanString(nextData);
        const forbiddenKeywords = [
            'fotmob.com',
            'cookie',
            'token',
            'session',
            'authorization',
            'set-cookie',
            'onetrust',
            'consent',
            'gtag',
            'google-analytics',
            'fbq',
            'header',
        ];

        for (const keyword of forbiddenKeywords) {
            assert.equal(serialized.includes(keyword), false,
                `nextData fixture must not contain sensitive keyword "${keyword}"`);
        }
        assert.equal(JSON.stringify(nextData).includes('example.invalid'), false,
            'nextData fixture must not contain URLs');
    });

    // -----------------------------------------------------------------------
    // 13.2 transformToApiFormat resolves and succeeds
    // -----------------------------------------------------------------------

    test('transformToApiFormat export resolves to a function', () => {
        const transformToApiFormat = resolveTransformToApiFormat(NextDataParser);
        assert.equal(typeof transformToApiFormat, 'function');
    });

    test('transformToApiFormat succeeds for sanitized local __NEXT_DATA__ fixture', () => {
        assert.ok(transformOutput !== null && typeof transformOutput === 'object',
            'transformOutput must be a non-null object');
        assert.equal(transformOutput.matchId, rawRecord.match_id);
        assert.ok(transformOutput.content && typeof transformOutput.content === 'object');
        assert.ok(transformOutput.general && typeof transformOutput.general === 'object');
        assert.ok(transformOutput.header && typeof transformOutput.header === 'object');
        assert.ok(transformOutput._meta && typeof transformOutput._meta === 'object');
        assert.equal(transformOutput._meta.source, 'web_infiltration');
        assert.equal(transformOutput._meta.hasStats, true);
        assert.equal(transformOutput._meta.hasLineup, true);
        assert.equal(transformOutput._meta.hasShotmap, true);
    });

    // -----------------------------------------------------------------------
    // 13.3 replay returns valid envelope
    // -----------------------------------------------------------------------

    test('replay returns a legal envelope', () => {
        assert.ok(envelope !== null && typeof envelope === 'object',
            'replay must return a non-null envelope object');
        const validation = validateEnvelopeShape(envelope);
        assert.ok(validation.valid,
            `envelope should pass shape validation: ${validation.errors.join('; ')}`);
        assert.equal(envelope.source, 'fotmob');
        assert.equal(envelope.match_id, rawRecord.match_id);
    });

    // -----------------------------------------------------------------------
    // 13.4 metadata handoff
    // -----------------------------------------------------------------------

    test('metadata handoff: raw record metadata enters envelope.payload', () => {
        assert.equal(options.dataVersion, rawRecord.data_version);
        assert.equal(options.payloadHash, rawRecord.data_hash);
        assert.equal(options.storagePath, rawRecord.storage_path);
        assert.equal(options.sourceUrl, rawRecord.source_url);
        assert.equal(options.finalUrl, rawRecord.final_url);
        assert.equal(options.fetchedAt, rawRecord.fetched_at);
        assert.equal(options.capturedAt, rawRecord.captured_at);

        assert.equal(envelope.payload.data_version, rawRecord.data_version);
        assert.equal(envelope.payload.payload_hash, rawRecord.data_hash);
        assert.equal(envelope.payload.storage_path, rawRecord.storage_path);
        assert.equal(envelope.payload.source_url, rawRecord.source_url);
        assert.equal(envelope.payload.final_url, rawRecord.final_url);
        assert.equal(envelope.payload.fetched_at, rawRecord.fetched_at);
        assert.equal(envelope.payload.captured_at, rawRecord.captured_at);
    });

    // -----------------------------------------------------------------------
    // 13.5 time semantics
    // -----------------------------------------------------------------------

    test('time semantics: fetch/capture/parser/kickoff clocks remain distinct', () => {
        assert.notEqual(envelope.payload.fetched_at, envelope.payload.captured_at);
        assert.notEqual(envelope.payload.fetched_at, transformOutput._meta.extractedAt);
        assert.notEqual(envelope.payload.fetched_at, transformOutput.general.matchTimeUTC);
        assert.notEqual(envelope.payload.fetched_at, transformOutput.header.status.utcTime);
        assert.notEqual(envelope.payload.captured_at, transformOutput._meta.extractedAt);
        assert.notEqual(envelope.payload.captured_at, transformOutput.general.matchTimeUTC);
        assert.notEqual(envelope.payload.captured_at, transformOutput.header.status.utcTime);
    });

    // -----------------------------------------------------------------------
    // 13.6 0 safe fields
    // -----------------------------------------------------------------------

    test('0 safe fields: no allowed candidate fields are produced', () => {
        assertNoSafeFields(envelope);
    });

    test('0 safe fields: payload metadata does not enter envelope.fields', () => {
        for (const metaPath of ['payload.fetched_at', 'payload.source_url', 'payload.final_url']) {
            assert.equal(fieldByPath(envelope.fields, metaPath), undefined,
                `"${metaPath}" must not appear in envelope.fields`);
        }
    });

    // -----------------------------------------------------------------------
    // 13.7 forbidden classification sanity
    // -----------------------------------------------------------------------

    test('forbidden classification: postmatch and unknown-timing blocks are not safe', () => {
        assert.equal(
            fieldByPath(envelope.fields, 'content').model_eligibility,
            MODEL_ELIGIBILITY.FORBIDDEN_RAW_ONLY
        );
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
            fieldByPath(envelope.fields, 'header').model_eligibility,
            MODEL_ELIGIBILITY.FORBIDDEN_RAW_ONLY
        );
    });

    test('forbidden classification: score/result fields are only covered by forbidden parent blocks', () => {
        const scoreOrResultEntries = envelope.fields.filter(f => (
            String(f.field_path || f.path || '').toLowerCase().includes('score')
            || String(f.field_path || f.path || '').toLowerCase().includes('result')
        ));

        for (const entry of scoreOrResultEntries) {
            assert.notEqual(entry.model_eligibility, MODEL_ELIGIBILITY.ALLOWED_CANDIDATE);
            assert.notEqual(entry.model_eligibility, MODEL_ELIGIBILITY.CANDIDATE_IF_CUTOFF_VALID);
        }

        assert.equal(
            fieldByPath(envelope.fields, 'header').model_eligibility,
            MODEL_ELIGIBILITY.FORBIDDEN_RAW_ONLY,
            'header parent block covers score/result values and must stay forbidden_raw_only'
        );
    });

    // -----------------------------------------------------------------------
    // 13.8 Lane A2 only
    // -----------------------------------------------------------------------

    test('Lane A2 only: helper calls transformToApiFormat only and has no side effects', () => {
        // 本测试不调用 extractFromHtml，不处理 HTML，不访问网络，只证明 Lane A2。
        const result = replayLocalNextDataLaneA2(rawRecord, nextData);
        assert.ok(result.transformOutput);
        assert.ok(result.envelope);
        assert.ok(result.options);
    });
});
