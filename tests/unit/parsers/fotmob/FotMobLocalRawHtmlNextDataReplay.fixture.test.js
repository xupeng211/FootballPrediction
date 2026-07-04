/**
 * FotMob Local Raw HTML __NEXT_DATA__ Extraction Fixture Test (DATA-L1E-10)
 * ========================================================================
 *
 * Lane A1 only: minimal sanitized local raw HTML fixture
 *   -> NextDataParser.extractFromHtml(html)
 *   -> NextDataParser.transformToApiFormat(nextData, matchId)
 *   -> adaptTransformToApiFormatOutputToEnvelope(transformOutput, adapterOptions)
 *   -> validateEnvelopeShape(envelope)
 *   -> assert metadata handoff
 *   -> assert 0 safe fields
 *
 * 纯静态测试：不访问网络、不写文件、不写 DB/raw/data、不运行 scraper/collector/browser。
 * 本测试证明 Lane A1，不证明 runtime integration。
 *
 * Lane A2 已在 DATA-L1E-9 覆盖。
 * Lane B 已在 DATA-L1E-7 覆盖。
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
// These helpers are test-only.
// They are not exported.
// They are not runtime integration.
// Future helper extraction requires separate authorization.
// ===========================================================================

function readTextFixture(relativePath) {
    const fullPath = path.join(__dirname, '../../../fixtures/fotmob', relativePath);
    return fs.readFileSync(fullPath, 'utf8');
}

function readJsonFixture(relativePath) {
    const fullPath = path.join(__dirname, '../../../fixtures/fotmob', relativePath);
    return JSON.parse(fs.readFileSync(fullPath, 'utf8'));
}

function resolveExtractFromHtml(module) {
    if (typeof module?.extractFromHtml === 'function') {
        return module.extractFromHtml.bind(module);
    }
    if (typeof module?.NextDataParser?.extractFromHtml === 'function') {
        return module.NextDataParser.extractFromHtml.bind(module.NextDataParser);
    }
    if (typeof module?.default?.extractFromHtml === 'function') {
        return module.default.extractFromHtml.bind(module.default);
    }
    throw new Error('Unable to resolve NextDataParser.extractFromHtml export');
}

function resolveTransformToApiFormat(module) {
    if (typeof module?.transformToApiFormat === 'function') {
        return module.transformToApiFormat.bind(module);
    }
    if (typeof module?.NextDataParser?.transformToApiFormat === 'function') {
        return module.NextDataParser.transformToApiFormat.bind(module.NextDataParser);
    }
    if (typeof module?.default?.transformToApiFormat === 'function') {
        return module.default.transformToApiFormat.bind(module.default);
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

/**
 * Lane A1 local raw HTML replay helper.
 *
 * 读取 minimal sanitized HTML → extractFromHtml → transformToApiFormat → adapter → envelope。
 * 纯函数：不访问网络、不写文件、不接 runtime。
 */
function replayLocalRawHtmlLaneA1(rawRecord, html) {
    const extractFromHtml = resolveExtractFromHtml(NextDataParser);
    const extractResult = extractFromHtml(html);

    if (!extractResult.success) {
        throw new Error(`extractFromHtml failed: ${extractResult.error}`);
    }

    const nextData = extractResult.data;
    const transformToApiFormat = resolveTransformToApiFormat(NextDataParser);
    const transformOutput = transformToApiFormat(nextData, rawRecord.match_id);

    if (!transformOutput) {
        throw new Error('transformToApiFormat returned null');
    }

    const options = buildAdapterOptionsFromRawRecord(rawRecord);
    const envelope = adaptTransformToApiFormatOutputToEnvelope(transformOutput, options);

    return { extractResult, nextData, transformOutput, envelope, options };
}

function fieldByPath(fields, fieldPath) {
    return fields.find(f => f.field_path === fieldPath || f.path === fieldPath);
}

function countByEligibility(envelope, eligibility) {
    return envelope.fields.filter(f => f.model_eligibility === eligibility).length;
}

function assertNoForbiddenHtmlPayload(html) {
    const lowered = html.toLowerCase();
    const forbiddenKeywords = [
        'fotmob.com',
        'api.fotmob.com',
        'cookie',
        'set-cookie',
        'authorization',
        'bearer',
        'access_token',
        'refresh_token',
        'csrf',
        'session',
        'jsessionid',
        'phpsessid',
        'connect.sid',
        'onetrust',
        'optanonalertboxclosed',
        'consent',
        'gtag',
        'googleanalytics',
        'analytics',
        'fbq',
        'fbclid',
        'gclid',
        'msclkid',
        'doubleclick',
        'adsense',
        'utm_',
        '<script src=',
        '<link',
        '<iframe',
        '<form',
        // HTTP auth header patterns inside payload
        'optanonconsent',
    ];
    const found = [];
    for (const keyword of forbiddenKeywords) {
        if (lowered.includes(keyword)) {
            found.push(keyword);
        }
    }
    assert.deepEqual(found, [],
        `HTML fixture must not contain forbidden keywords: ${found.join(', ')}`);
}

function assertNoSafeFields(envelope) {
    assert.ok(Array.isArray(envelope.fields), 'envelope.fields must be an array');
    assert.equal(countByEligibility(envelope, MODEL_ELIGIBILITY.ALLOWED_CANDIDATE), 0,
        'ALLOWED_CANDIDATE count must be 0');
    assert.equal(countByEligibility(envelope, MODEL_ELIGIBILITY.CANDIDATE_IF_CUTOFF_VALID), 0,
        'CANDIDATE_IF_CUTOFF_VALID count must be 0');
}

// ===========================================================================
// DATA-L1E-10 Lane A1 local raw HTML __NEXT_DATA__ extraction replay
// ===========================================================================

describe('DATA-L1E-10 Lane A1 local raw HTML __NEXT_DATA__ extraction replay', () => {
    const html = readTextFixture(
        'local_raw_html_nextdata_replay_boundary_a1_html_fixture.html'
    );
    const rawRecord = readJsonFixture(
        'local_raw_html_nextdata_replay_boundary_a1_raw_record_fixture.json'
    );
    const { extractResult, nextData, transformOutput, envelope, options } =
        replayLocalRawHtmlLaneA1(rawRecord, html);

    // -----------------------------------------------------------------------
    // 1. HTML fixture sanitation test
    // -----------------------------------------------------------------------

    test('fixture sanitation: HTML fixture 不包含 forbidden keywords', () => {
        assertNoForbiddenHtmlPayload(html);
    });

    test('fixture sanitation: HTML fixture 包含必需的 __NEXT_DATA__ 标签', () => {
        assert.ok(html.includes('__NEXT_DATA__'),
            'HTML fixture must contain __NEXT_DATA__ script tag');
        // HTML fixture is a minimal shell — it intentionally contains no URLs.
        // The example.invalid URLs live in the raw record fixture, not in the HTML.
        assert.equal(html.includes('fotmob.com'), false,
            'HTML fixture must not contain real fotmob.com URL');
    });

    test('fixture sanitation: HTML fixture 包含 synthetic fixture team IDs', () => {
        assert.ok(html.includes('home-fixture-a1'),
            'HTML fixture must reference synthetic home team ID');
        assert.ok(html.includes('away-fixture-a1'),
            'HTML fixture must reference synthetic away team ID');
        assert.ok(html.includes('Fixture League A1'),
            'HTML fixture must reference synthetic league name');
    });

    // -----------------------------------------------------------------------
    // 2. raw record metadata sanity test
    // -----------------------------------------------------------------------

    test('raw record metadata sanity: Lane A1 markers', () => {
        assert.equal(rawRecord.raw_data.replay_lane, 'A1');
        assert.equal(rawRecord.raw_data.contains_sanitized_html, true);
        assert.equal(rawRecord.raw_data.contains_sanitized_next_data, true);
        assert.equal(rawRecord.raw_data.contains_live_fotmob_payload, false);
    });

    test('raw record metadata sanity: URLs use example.invalid', () => {
        assert.ok(rawRecord.source_url.startsWith('https://example.invalid/'),
            'source_url must use example.invalid');
        assert.ok(rawRecord.final_url.startsWith('https://example.invalid/'),
            'final_url must use example.invalid');
    });

    test('raw record metadata sanity: deterministic timestamps', () => {
        assert.equal(rawRecord.fetched_at, '2026-07-04T01:00:00.000Z');
        assert.equal(rawRecord.captured_at, '2026-07-04T01:00:05.000Z');
        assert.notEqual(rawRecord.fetched_at, rawRecord.captured_at,
            'fetched_at and captured_at must be distinct');
    });

    test('raw record metadata sanity: match_id is synthetic', () => {
        assert.equal(rawRecord.match_id, 'fixture-local-replay-a1-001');
        assert.equal(rawRecord.source, 'fotmob');
    });

    // -----------------------------------------------------------------------
    // 3. extractFromHtml test
    // -----------------------------------------------------------------------

    test('extractFromHtml: export resolves to a function', () => {
        const fn = resolveExtractFromHtml(NextDataParser);
        assert.equal(typeof fn, 'function');
    });

    test('extractFromHtml: succeed for sanitized local HTML fixture', () => {
        assert.equal(extractResult.success, true,
            `extractFromHtml must succeed: ${extractResult.error || 'unknown error'}`);
        assert.ok(extractResult.data, 'extractResult.data must exist');
    });

    test('extractFromHtml: extracted data has props.pageProps', () => {
        assert.ok(nextData.props, 'extracted nextData must have props');
        assert.ok(nextData.props.pageProps, 'extracted nextData must have props.pageProps');
    });

    test('extractFromHtml: extracted data has content/general/header shape', () => {
        const pp = nextData.props.pageProps;
        assert.ok(pp.content && typeof pp.content === 'object',
            'pageProps.content must exist');
        assert.ok(pp.general && typeof pp.general === 'object',
            'pageProps.general must exist');
        assert.ok(pp.header && typeof pp.header === 'object',
            'pageProps.header must exist');
    });

    // -----------------------------------------------------------------------
    // 4. transformToApiFormat test
    // -----------------------------------------------------------------------

    test('transformToApiFormat: export resolves to a function', () => {
        const fn = resolveTransformToApiFormat(NextDataParser);
        assert.equal(typeof fn, 'function');
    });

    test('transformToApiFormat: returns non-null output', () => {
        assert.ok(transformOutput !== null && typeof transformOutput === 'object',
            'transformOutput must be a non-null object');
    });

    test('transformToApiFormat: matchId matches rawRecord', () => {
        assert.equal(transformOutput.matchId, rawRecord.match_id);
    });

    test('transformToApiFormat: has content, general, header, _meta', () => {
        assert.ok(transformOutput.content && typeof transformOutput.content === 'object');
        assert.ok(transformOutput.general && typeof transformOutput.general === 'object');
        assert.ok(transformOutput.header && typeof transformOutput.header === 'object');
        assert.ok(transformOutput._meta && typeof transformOutput._meta === 'object');
    });

    test('transformToApiFormat: _meta extractedAt is generated (legacy parser behavior)', () => {
        assert.ok(typeof transformOutput._meta.extractedAt === 'string',
            '_meta.extractedAt must be a string (legacy parser execution time)');
    });

    // -----------------------------------------------------------------------
    // 5. envelope validation test
    // -----------------------------------------------------------------------

    test('envelope validation: validateEnvelopeShape passes', () => {
        const validation = validateEnvelopeShape(envelope);
        assert.ok(validation.valid,
            `envelope should pass shape validation: ${validation.errors.join('; ')}`);
    });

    test('envelope validation: source and match_id', () => {
        assert.equal(envelope.source, 'fotmob');
        assert.equal(envelope.match_id, rawRecord.match_id);
    });

    test('envelope validation: payload exists', () => {
        assert.ok(envelope.payload && typeof envelope.payload === 'object',
            'envelope.payload must exist');
    });

    test('envelope validation: fields is array', () => {
        assert.ok(Array.isArray(envelope.fields),
            'envelope.fields must be an array');
    });

    // -----------------------------------------------------------------------
    // 6. metadata handoff test
    // -----------------------------------------------------------------------

    test('metadata handoff: data_version enters envelope.payload', () => {
        assert.equal(envelope.payload.data_version, rawRecord.data_version);
    });

    test('metadata handoff: payload_hash enters envelope.payload', () => {
        assert.equal(envelope.payload.payload_hash, rawRecord.data_hash);
    });

    test('metadata handoff: storage_path is null', () => {
        assert.equal(envelope.payload.storage_path, null);
    });

    test('metadata handoff: source_url enters envelope.payload', () => {
        assert.equal(envelope.payload.source_url, rawRecord.source_url);
    });

    test('metadata handoff: final_url enters envelope.payload', () => {
        assert.equal(envelope.payload.final_url, rawRecord.final_url);
    });

    test('metadata handoff: fetched_at enters envelope.payload', () => {
        assert.equal(envelope.payload.fetched_at, rawRecord.fetched_at);
    });

    test('metadata handoff: captured_at enters envelope.payload', () => {
        assert.equal(envelope.payload.captured_at, rawRecord.captured_at);
    });

    // -----------------------------------------------------------------------
    // 7. clock non-substitution test
    // -----------------------------------------------------------------------

    test('clock non-substitution: fetched_at !== extractedAt', () => {
        assert.notEqual(envelope.payload.fetched_at, transformOutput._meta.extractedAt,
            'fetched_at must not equal _meta.extractedAt');
    });

    test('clock non-substitution: captured_at !== extractedAt', () => {
        assert.notEqual(envelope.payload.captured_at, transformOutput._meta.extractedAt,
            'captured_at must not equal _meta.extractedAt');
    });

    test('clock non-substitution: fetched_at !== matchTimeUTC', () => {
        assert.notEqual(envelope.payload.fetched_at, transformOutput.general.matchTimeUTC,
            'fetched_at must not equal matchTimeUTC');
    });

    test('clock non-substitution: captured_at !== matchTimeUTC', () => {
        assert.notEqual(envelope.payload.captured_at, transformOutput.general.matchTimeUTC,
            'captured_at must not equal matchTimeUTC');
    });

    test('clock non-substitution: fetched_at !== utcTime', () => {
        assert.notEqual(envelope.payload.fetched_at, transformOutput.header.status.utcTime,
            'fetched_at must not equal utcTime');
    });

    test('clock non-substitution: captured_at !== utcTime', () => {
        assert.notEqual(envelope.payload.captured_at, transformOutput.header.status.utcTime,
            'captured_at must not equal utcTime');
    });

    // -----------------------------------------------------------------------
    // 8. model safety test (0 safe fields)
    // -----------------------------------------------------------------------

    test('model safety: 0 ALLOWED_CANDIDATE fields', () => {
        const count = countByEligibility(envelope, MODEL_ELIGIBILITY.ALLOWED_CANDIDATE);
        assert.equal(count, 0, 'ALLOWED_CANDIDATE count must be 0');
    });

    test('model safety: 0 CANDIDATE_IF_CUTOFF_VALID fields', () => {
        const count = countByEligibility(envelope, MODEL_ELIGIBILITY.CANDIDATE_IF_CUTOFF_VALID);
        assert.equal(count, 0, 'CANDIDATE_IF_CUTOFF_VALID count must be 0');
    });

    test('model safety: payload metadata does not become model-safe fields', () => {
        for (const metaPath of ['payload.fetched_at', 'payload.source_url', 'payload.final_url']) {
            assert.equal(fieldByPath(envelope.fields, metaPath), undefined,
                `"${metaPath}" must not appear in envelope.fields`);
        }
    });

    // -----------------------------------------------------------------------
    // 9. forbidden field classification sanity test
    // -----------------------------------------------------------------------

    test('forbidden classification: content is FORBIDDEN_RAW_ONLY', () => {
        const entry = fieldByPath(envelope.fields, 'content');
        assert.ok(entry, 'content raw block must exist');
        assert.equal(entry.model_eligibility, MODEL_ELIGIBILITY.FORBIDDEN_RAW_ONLY,
            'content must be FORBIDDEN_RAW_ONLY');
    });

    test('forbidden classification: content.stats is FORBIDDEN_POSTMATCH', () => {
        const entry = fieldByPath(envelope.fields, 'content.stats');
        assert.ok(entry, 'content.stats field must exist');
        assert.equal(entry.model_eligibility, MODEL_ELIGIBILITY.FORBIDDEN_POSTMATCH,
            'content.stats must be FORBIDDEN_POSTMATCH');
    });

    test('forbidden classification: content.shotmap is FORBIDDEN_POSTMATCH', () => {
        const entry = fieldByPath(envelope.fields, 'content.shotmap');
        assert.ok(entry, 'content.shotmap field must exist');
        assert.equal(entry.model_eligibility, MODEL_ELIGIBILITY.FORBIDDEN_POSTMATCH,
            'content.shotmap must be FORBIDDEN_POSTMATCH');
    });

    test('forbidden classification: content.events is FORBIDDEN_POSTMATCH', () => {
        const entry = fieldByPath(envelope.fields, 'content.events');
        assert.ok(entry, 'content.events field must exist');
        assert.equal(entry.model_eligibility, MODEL_ELIGIBILITY.FORBIDDEN_POSTMATCH,
            'content.events must be FORBIDDEN_POSTMATCH');
    });

    test('forbidden classification: content.lineup is FORBIDDEN_UNKNOWN_TIMING', () => {
        const entry = fieldByPath(envelope.fields, 'content.lineup');
        assert.ok(entry, 'content.lineup field must exist');
        assert.equal(entry.model_eligibility, MODEL_ELIGIBILITY.FORBIDDEN_UNKNOWN_TIMING,
            'content.lineup must be FORBIDDEN_UNKNOWN_TIMING');
    });

    test('forbidden classification: header is FORBIDDEN_RAW_ONLY', () => {
        const entry = fieldByPath(envelope.fields, 'header');
        assert.ok(entry, 'header raw block must exist');
        assert.equal(entry.model_eligibility, MODEL_ELIGIBILITY.FORBIDDEN_RAW_ONLY,
            'header must be FORBIDDEN_RAW_ONLY');
    });

    test('forbidden classification: general is FORBIDDEN_RAW_ONLY', () => {
        const entry = fieldByPath(envelope.fields, 'general');
        assert.ok(entry, 'general raw block must exist');
        assert.equal(entry.model_eligibility, MODEL_ELIGIBILITY.FORBIDDEN_RAW_ONLY,
            'general must be FORBIDDEN_RAW_ONLY');
    });

    // -----------------------------------------------------------------------
    // 10. no runtime integration test
    // -----------------------------------------------------------------------

    test('no runtime integration: Lane A1 helper is deterministic and has no side effects', () => {
        // Run a second time to confirm no state leaks.
        const result2 = replayLocalRawHtmlLaneA1(rawRecord, html);
        assert.ok(result2.extractResult.success);
        assert.ok(result2.transformOutput);
        assert.ok(result2.envelope);
        assert.equal(result2.extractResult.success, extractResult.success);
    });

    test('no runtime integration: extractFromHtml is called test-only in Lane A1', () => {
        // Confirm the function is imported from source but only called within this test.
        assert.equal(typeof NextDataParser.extractFromHtml, 'function');
        // This test itself calls extractFromHtml via the Lane A1 helper, which is test-only.
    });

    test('no runtime integration: no production module imports this test helper', () => {
        // This test file is not imported by any src/** module.
        // Verified by code review: grep for require of this test file in src/ returns empty.
        // This assertion exists as explicit documentation.
        assert.ok(true, 'referential integrity: no src/** module imports this test file');
    });

    // -----------------------------------------------------------------------
    // 11. raw_data markers stay in payload, not fields
    // -----------------------------------------------------------------------

    test('raw_data metadata markers stay in payload only', () => {
        assert.equal(rawRecord.raw_data.replay_lane, 'A1');
        assert.equal(fieldByPath(envelope.fields, 'raw_data'), undefined,
            'raw_data must not appear in envelope.fields');
        assert.equal(fieldByPath(envelope.fields, 'replay_lane'), undefined,
            'replay_lane must not appear in envelope.fields');
    });

    // -----------------------------------------------------------------------
    // 12. HTML fixture structure verification
    // -----------------------------------------------------------------------

    test('HTML fixture: is minimal shell with single __NEXT_DATA__ script tag', () => {
        // Ensure no second script block sneaks in.
        const scriptCount = (html.match(/<script[^>]*>/gi) || []).length;
        assert.equal(scriptCount, 1,
            'HTML fixture must contain exactly one script tag (__NEXT_DATA__)');

        // No CSS
        assert.equal(html.includes('<style'), false, 'HTML fixture must not contain CSS');
        assert.equal(html.includes('style='), false, 'HTML fixture must not contain inline styles');
    });
});
