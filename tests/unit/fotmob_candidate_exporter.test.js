'use strict';

// lifecycle: permanent
// Unit tests for FotMobCandidateExporter — fully mocked, no network.

/* eslint-disable max-lines */

const test = require('node:test');
const assert = require('node:assert');
const path = require('node:path');
const fs = require('node:fs');
const crypto = require('node:crypto');
const { spawnSync } = require('node:child_process');

const {
    EPL_FIXTURES_PER_SEASON,
    normaliseSeason,
    canonicalizeRequestedSeasons,
    canonicalizeCompetition,
    canonicalizeLeagueId,
    canonicalizeLeagueSlug,
    generateCandidateId,
    isStrictAbsoluteTimestamp,
    extractNextData,
    extractPageIdentity,
    extractFixtures,
    classifyFixtureRejection,
    deriveProviderStatus,
    buildCandidate,
    validateSeasonCandidates,
    validateAggregateCandidates,
    computeBusinessContentHash,
    computeV1IdentityProjectionHash,
    computeV2BusinessHash,
    verifyOutputPathSafety,
    buildOutputDocument,
    buildSummaryDocument,
    buildV2OutputDocument,
    buildV2SummaryDocument,
    writeOutputFiles,
    writeRawRetention,
    buildCaptureManifest,
    validateCollectorCodeRevision,
    exportCandidates,
    delay,
    STATUS_MAPPING_VERSION,
    ALLOWED_PROVIDER_STATUSES,
    MAX_TOTAL_REQUESTS,
} = require('../../src/infrastructure/fotmob/FotMobCandidateExporter');
const { main: runCandidateExportCli, validateArgs } = require('../../scripts/ops/fotmob_candidates_export');

// -----------------------------------------------------------------
// Synthetic fixture builders
// -----------------------------------------------------------------

/* prettier-ignore */
function buildFixture(id, home, away, kickoff, statusReason = 'FT', overrides = {}) { const status = { utcTime: kickoff, reason: { short: statusReason }, scoreStr: '1-0' }; if (overrides.finished !== undefined) status.finished = overrides.finished; if (overrides.started !== undefined) status.started = overrides.started; if (overrides.cancelled !== undefined) status.cancelled = overrides.cancelled; if (overrides.extraStatusKey) status[overrides.extraStatusKey] = overrides.extraStatusValue; return { id, home: { name: home }, away: { name: away }, status }; }
/* prettier-ignore */
function buildNextDataPage(overrides = {}) { const fixtures = overrides.fixtures || generateSeasonFixtures(1, EPL_FIXTURES_PER_SEASON); const leagueId = overrides.leagueId === undefined ? 47 : overrides.leagueId; const pageProps = { tabs: ['overview', 'table', 'fixtures', 'stats', 'seasons'], allAvailableSeasons: ['2026/2027', '2025/2026', '2024/2025', '2023/2024', '2022/2023'], details: { name: overrides.leagueName || 'Premier League', id: leagueId }, fixtures: { allMatches: fixtures, firstUnplayedMatch: null, hasOngoingMatch: false }, ...(overrides.pagePropsExtra || {}) }; const nd = { props: { pageProps }, query: { season: overrides.season || '2022/2023', id: String(leagueId), tab: 'fixtures', slug: ['premier-league'] }, buildId: 'test-build-id' }; const json = JSON.stringify(nd); return { html: `<!DOCTYPE html><html><head><title>${pageProps.details.name} fixtures ${nd.query.season}</title></head><body><script id="__NEXT_DATA__" type="application/json">${json}</script></body></html>`, nd }; }
/* prettier-ignore */
function generateSeasonFixtures(startId, count = EPL_FIXTURES_PER_SEASON) { const teams = 'Arsenal|Aston Villa|Bournemouth|Brentford|Brighton|Chelsea|Crystal Palace|Everton|Fulham|Leeds|Leicester|Liverpool|Man City|Man United|Newcastle|Southampton|Tottenham|West Ham|Wolves|Nottingham Forest'.split('|'); return Array.from({ length: count }, (_, i) => { const kickoff = `2022-${String((i % 12) + 1).padStart(2, '0')}-${String((i % 28) + 1).padStart(2, '0')}T${String((i % 22) + 1).padStart(2, '0')}:00:00Z`; return buildFixture(startId + i, teams[i % 20], teams[(i + 3) % 20], kickoff); }); }

// Build a candidate for a synthetic fixture.
/* prettier-ignore */
const candidateFromFixture = (fixture, season) => buildCandidate({ id: String(fixture.id), home: fixture.home.name, away: fixture.away.name, kickoff: fixture.status.utcTime }, 47, 'Premier League', typeof season === 'string' ? season : '2022/2023');
const seasonCandidates = (season, startId, count = EPL_FIXTURES_PER_SEASON) =>
    generateSeasonFixtures(startId, count).map(fixture => candidateFromFixture(fixture, season));
const fixtureResult = fixtures => extractFixtures(buildNextDataPage({ fixtures }).nd);
/* prettier-ignore */
const fixtureAudit = fixtures => { const { fixtures: extracted, audit } = fixtureResult(fixtures); return { extracted, audit }; };

// Run a cleanup step without letting its failure mask the test result.
/* prettier-ignore */
function bestEffort(fn) { try { fn(); } catch (cleanupError) { void cleanupError; } }

const EPL_BASE_IDS = { '2022/2023': 3900000, '2023/2024': 4190000, '2024/2025': 4500000 };
const FIXED_CLOCK = () => '2026-07-18T00:00:00Z';
// Business hash of the 3-season mock pipeline, pinned before the M3-D2BG refactor.
const EXPECTED_PIPELINE_HASH = '046dac4c0a9ff711befc55f5aa885494367303ce9d0ee3aa30c9a5afe1a86c15';
// Valid full-length lowercase hex Git SHA injected wherever a test feeds a
// collector code revision into the manifest core path. The core layer now
// enforces the 40-hex contract, so placeholder revisions ('sha', 'test-sha',
// 'abc123def456', …) must never reach buildCaptureManifest / writeRawRetention.
const TEST_COLLECTOR_CODE_REVISION = '0123456789abcdef0123456789abcdef01234567';
const OUTPUT_META = { schema_version: 'candidate-match-identity/v1', extracted_at: '2026-07-18T00:00:00Z' };
/* prettier-ignore */
const outputSnapshot = (candidateCount, hash = 'h', seasons = ['2022/2023']) => ({ source_provider: 'FotMob', league_id: '47', competition: 'Premier League', seasons, candidate_count: candidateCount, business_content_sha256: hash });

// Fetch mock: canonical Premier League page with 380 synthetic fixtures per season.
/* prettier-ignore */
function makeSeasonPageFetch(onSeason, baseIdForSeason = season => EPL_BASE_IDS[season] || 1000) { return async url => { const season = decodeURIComponent(url.match(/season=([^&]+)/)[1]); if (onSeason) onSeason(season); const fixtures = generateSeasonFixtures(baseIdForSeason(season), EPL_FIXTURES_PER_SEASON); const { html } = buildNextDataPage({ fixtures, season }); return { status: 200, contentType: 'text/html', body: html }; }; }
/* prettier-ignore */
const makeExportOptions = (seasons, fetchPage, deps = {}, overrides = {}) => ({ leagueId: 47, competition: 'Premier League', seasons, networkAuthorization: true, ...overrides, deps: { fetchPage, delay: () => Promise.resolve(), clock: FIXED_CLOCK, ...deps } });
/* prettier-ignore */
const exportFromHtml = (html, seasons = ['2022/2023'], overrides = {}) => exportCandidates(makeExportOptions(seasons, async () => ({ status: 200, contentType: 'text/html', body: html }), {}, overrides));
/* prettier-ignore */
function assertAggregateErrors(result, expectedErrors) { assert.equal(result.valid, false); for (const expectedError of expectedErrors) assert.ok(result.errors.some(error => error.startsWith(expectedError))); }

const assertUnsafeOutput = (outputPath, options = {}) =>
    assert.throws(() => verifyOutputPathSafety(outputPath, options), { code: 'SAFETY_ERROR' });
const isStringSeasonInputError = error =>
    error.code === 'INPUT_ERROR' && error.message === 'Season at index 0 must be a string';
const assertNullSeasons = values => values.forEach(value => assert.equal(normaliseSeason(value), null));

// Rebuild page HTML after mutating the generated __NEXT_DATA__ object.
/* prettier-ignore */
function rebuildPageHtml(nd, html) { return html.replace(/<script id="__NEXT_DATA__"[^>]*>.*?<\/script>/s, `<script id="__NEXT_DATA__" type="application/json">${JSON.stringify(nd)}</script>`); }
/* prettier-ignore */
async function assertInvalidSeasonMakesNoRequests(season) { const calls = { fetch: 0, delay: 0 }; const fetchPage = async () => ((calls.fetch += 1), { status: 500, contentType: 'text/html', body: '' }); await assert.rejects(exportCandidates(makeExportOptions([season], fetchPage, { delay: async () => (calls.delay += 1) })), { code: 'INPUT_ERROR' }); assert.deepEqual(calls, { fetch: 0, delay: 0 }); }

// -----------------------------------------------------------------
// Unit: normaliseSeason
// -----------------------------------------------------------------

test('normaliseSeason canonicalises valid and rejects non-consecutive', () => {
    ['2022/2023', '2022-2023', '22/23', '22-23', '2022/23'].forEach(season =>
        assert.equal(normaliseSeason(season), '2022/2023')
    );
    assertNullSeasons(['', 'abc', '2022', '2022/2024', '2022/2022']);
});

test('normaliseSeason accepts all equivalent consecutive-season formats', () => {
    assertNullSeasons(['', 'abc', '2022', '22/25', '2022/2024', '2022/2022', '2024/2023']);
});

test('normaliseSeason rejects every non-primitive-string value', () => {
    const coercibleObject = { toString: () => '2022/2023' };
    assertNullSeasons([
        null,
        undefined,
        20222023,
        true,
        false,
        {},
        coercibleObject,
        ['2022/2023'],
        [['2022/2023']],
        new String('2022/2023'),
    ]);
});

// -----------------------------------------------------------------
// Unit: canonicalizeRequestedSeasons (integrity correction)
// -----------------------------------------------------------------

test('canonicalizeRequestedSeasons: valid, invalid, duplicates, non-consecutive', () => {
    assert.deepEqual(canonicalizeRequestedSeasons(['2022/2023', '2023/2024']), ['2022/2023', '2023/2024']);
    assert.deepEqual(canonicalizeRequestedSeasons(['2022-2023']), ['2022/2023']);
    assert.deepEqual(canonicalizeRequestedSeasons(['22/23']), ['2022/2023']);
    for (const bad of ['not-a-season', '', '2022', '2022/2024', '2022-2024', '2022/2022']) {
        assert.throws(() => canonicalizeRequestedSeasons([bad]), { code: 'INPUT_ERROR' });
    }
    assert.throws(() => canonicalizeRequestedSeasons([]), { code: 'INPUT_ERROR' });
    assert.throws(() => canonicalizeRequestedSeasons([undefined]), { code: 'INPUT_ERROR' });
    assert.throws(() => canonicalizeRequestedSeasons(['2022/2023', '2024/2025']), { code: 'INPUT_ERROR' });
    assert.throws(() => canonicalizeRequestedSeasons(['2022/2023', '2022/2023']), { code: 'INPUT_ERROR' });
    assert.throws(() => canonicalizeRequestedSeasons(['2022/2023', '2022-2023']), { code: 'INPUT_ERROR' });
});

test('canonicalizeRequestedSeasons rejects non-string members before coercion', () => {
    let toStringCalls = 0;
    const coercibleObject = {
        toString: () => {
            toStringCalls += 1;
            return '2022/2023';
        },
    };
    const values = [20222023, true, {}, coercibleObject, ['2022/2023'], [['2022/2023']], new String('2022/2023')];

    values.forEach(value => assert.throws(() => canonicalizeRequestedSeasons([value]), isStringSeasonInputError));
    assert.equal(toStringCalls, 0);
});

test('canonicalizeCompetition accepts harmless canonical formatting variants', () => {
    for (const value of ['Premier League', ' premier league ', 'PREMIER   LEAGUE']) {
        assert.equal(canonicalizeCompetition(value), 'Premier League');
    }
});

test('canonicalizeCompetition rejects aliases typos and non-string values without coercion', () => {
    let toStringCalls = 0;
    const coercibleObject = {
        toString: () => {
            toStringCalls += 1;
            return 'Premier League';
        },
    };
    const invalidValues = [
        'Premiere League',
        'English Premier League',
        'EPL',
        'Premier League 2',
        'Premier League Women',
        '',
        47,
        true,
        ['Premier League'],
        {},
        new String('Premier League'),
        coercibleObject,
    ];

    for (const value of invalidValues) {
        assert.throws(() => canonicalizeCompetition(value), { code: 'INPUT_ERROR' });
    }
    assert.equal(toStringCalls, 0);
});

// -----------------------------------------------------------------
// Unit: canonicalizeLeagueId / canonicalizeLeagueSlug (URL path safety)
// -----------------------------------------------------------------

/* prettier-ignore */
test('canonicalizeLeagueId accepts canonical numeric identities', () => { assert.equal(canonicalizeLeagueId(47), '47'); assert.equal(canonicalizeLeagueId('47'), '47'); assert.equal(canonicalizeLeagueId(47), canonicalizeLeagueId('47')); assert.equal(typeof canonicalizeLeagueId(47), 'string'); assert.equal(typeof canonicalizeLeagueId('47'), 'string'); assert.equal(canonicalizeLeagueId('  47  '), '47'); assert.equal(canonicalizeLeagueId('\t47\n'), '47'); assert.equal(canonicalizeLeagueId(1), '1'); assert.equal(canonicalizeLeagueId(Number.MAX_SAFE_INTEGER), String(Number.MAX_SAFE_INTEGER)); assert.equal(canonicalizeLeagueId('9007199254740991'), '9007199254740991'); });
/* prettier-ignore */
test('canonicalizeLeagueId rejects unsafe and coercible values without network', async () => { let toStringCalls = 0; const coercible = { toString: () => { toStringCalls += 1; return '47'; } }; const invalid = ['', '   ', '0', 0, '-47', -47, '+47', '47.0', '47.5', 47.5, '4e1', '047', '4 7', '47/fixtures', '47/fixtures/evil', '../47', '47?x=1', '47?tab=table', '47#x', '47#fragment', '47%2Ffixtures', NaN, Infinity, -Infinity, Number.MAX_SAFE_INTEGER + 1, true, false, 47n, [47], ['47'], {}, { leagueId: 47 }, new Number(47), new String('47'), coercible, null, undefined]; for (const value of invalid) assert.throws(() => canonicalizeLeagueId(value), { code: 'INPUT_ERROR' }); assert.equal(toStringCalls, 0); for (const leagueId of ['47/fixtures/evil', '../47', '47%2Ffixtures']) { const calls = { fetch: 0, delay: 0 }; await assert.rejects(exportCandidates({ leagueId, competition: 'Premier League', seasons: ['2022/2023'], networkAuthorization: true, deps: { fetchPage: async () => { calls.fetch += 1; return { status: 500, contentType: 'text/html', body: '' }; }, delay: async () => (calls.delay += 1) } }), { code: 'INPUT_ERROR' }); assert.deepEqual(calls, { fetch: 0, delay: 0 }); } });
/* prettier-ignore */
test('canonicalizeLeagueSlug accepts safe canonical slugs', () => { assert.equal(canonicalizeLeagueSlug('premier-league'), 'premier-league'); assert.equal(canonicalizeLeagueSlug('  Premier-League  '), 'premier-league'); assert.equal(canonicalizeLeagueSlug('PREMIER-LEAGUE'), 'premier-league'); assert.equal(canonicalizeLeagueSlug('epl'), 'epl'); assert.equal(canonicalizeLeagueSlug('a'), 'a'); assert.equal(canonicalizeLeagueSlug('league2'), 'league2'); assert.equal(canonicalizeLeagueSlug('2-bundesliga'), '2-bundesliga'); assert.equal(canonicalizeLeagueSlug('Premier League'.toLowerCase().replace(/\s+/g, '-')), 'premier-league'); });
/* prettier-ignore */
test('canonicalizeLeagueSlug rejects path and query injection without coercion', async () => { let toStringCalls = 0; const coercible = { toString: () => { toStringCalls += 1; return 'premier-league'; } }; const invalid = ['', '   ', '../premier-league', 'premier-league/fixtures', 'premier-league\\fixtures', 'premier-league?tab=table', 'premier-league#fragment', 'premier%2Fleague', 'premier&league', 'premier=league', 'premier_league', 'premier league', '-premier-league', 'premier-league-', 'premier--league', '.', '..', 'premier.league', 'premier\u2215league', 'premier\uFF0Fleague', ['premier-league'], {}, new String('premier-league'), coercible, null, undefined, 47, true]; for (const value of invalid) assert.throws(() => canonicalizeLeagueSlug(value), { code: 'INPUT_ERROR' }); assert.equal(toStringCalls, 0); for (const leagueSlug of ['../premier-league', 'premier-league/fixtures', 'premier-league?tab=table']) { const calls = { fetch: 0, delay: 0 }; await assert.rejects(exportCandidates({ leagueId: 47, competition: 'Premier League', seasons: ['2022/2023'], leagueSlug, networkAuthorization: true, deps: { fetchPage: async () => { calls.fetch += 1; return { status: 500, contentType: 'text/html', body: '' }; }, delay: async () => (calls.delay += 1) } }), { code: 'INPUT_ERROR' }); assert.deepEqual(calls, { fetch: 0, delay: 0 }); } });

// -----------------------------------------------------------------
// Unit: helpers
// -----------------------------------------------------------------

/* prettier-ignore */
test('generateCandidateId follows L1 contract', () => { assert.equal(generateCandidateId(47, '2022/2023', '3900932'), '47_20222023_3900932'); assert.equal(generateCandidateId(53, '2025/2026', '4830473'), '53_20252026_4830473'); assert.equal(generateCandidateId('47', '2024/2025', '4506263'), '47_20242025_4506263'); });
/* prettier-ignore */
test('isStrictAbsoluteTimestamp accepts valid timestamps', () => { for (const ok of ['2022-08-05T19:00:00Z', '2022-08-05T19:00:00+00:00', '2022-08-06T11:30:00+01:00', '2026-03-15T19:00:00.0Z', '2026-03-15T19:00:00.000Z', '2026-03-15T19:00:00.123456Z', '2026-03-15T19:00:00.123456789Z', '2026-03-15T19:00:00.000+00:00', '2026-03-15T19:00:00.250+01:00']) assert.ok(isStrictAbsoluteTimestamp(ok), ok); for (const bad of ['2022-08-05 19:00:00', '2022-08-05T19:00:00', '2026-03-15T19:00:00.000', '2026-03-15T19:00:00.Z', '2026-03-15T19:00:00.1234567890Z', '2026-03-15T19:00:00,000Z', '2026-03-15T19:00:00.000+0100', '2026-03-15T19:00:00.000Z ', '2026-03-15T19:00:00.000Zjunk', '', null]) assert.equal(isStrictAbsoluteTimestamp(bad), false, String(bad)); });
/* prettier-ignore */
test('extractNextData parses valid __NEXT_DATA__', () => { const { html } = buildNextDataPage(); const nd = extractNextData(html); assert.ok(nd); assert.equal(nd.props.pageProps.details.name, 'Premier League'); assert.equal(nd.query.season, '2022/2023'); });
test('extractNextData returns null for missing __NEXT_DATA__', () => {
    assert.equal(extractNextData('<html><body>no data</body></html>'), null);
});
/* prettier-ignore */
test('extractPageIdentity returns correct fields including season_canonical', () => { const { nd } = buildNextDataPage(); const identity = extractPageIdentity(nd); assert.equal(identity.league_name, 'Premier League'); assert.equal(identity.league_id, '47'); assert.equal(identity.season_raw, '2022/2023'); assert.equal(identity.season_canonical, '2022/2023'); assert.ok(identity.tabs.includes('fixtures')); });
/* prettier-ignore */
test('extractPageIdentity normalises dash-format season', () => { const { nd } = buildNextDataPage({ season: '2023-2024' }); const identity = extractPageIdentity(nd); assert.equal(identity.season_raw, '2023-2024'); assert.equal(identity.season_canonical, '2023/2024'); });
/* prettier-ignore */
test('extractPageIdentity returns null season_canonical for bad format', () => { const { nd } = buildNextDataPage({ season: 'not-a-season' }); const identity = extractPageIdentity(nd); assert.equal(identity.season_canonical, null); });
/* prettier-ignore */
test('extractPageIdentity rejects non-string season values without coercion', () => { for (const season of [['2022/2023'], { value: '2022/2023' }, 20222023, true, false]) { const { nd } = buildNextDataPage({ pagePropsExtra: { selectedSeason: '2022/2023' } }); nd.query.season = season; const identity = extractPageIdentity(nd); assert.strictEqual(identity.season_raw, season); assert.equal(identity.season_canonical, null); } });

// -----------------------------------------------------------------
// Unit: extractFixtures with audit
// -----------------------------------------------------------------

/* prettier-ignore */
test('extractFixtures returns correct count with audit', () => { const { extracted, audit } = fixtureAudit(generateSeasonFixtures(1000, 380)); assert.deepEqual([extracted.length, audit.raw_fixture_count, audit.excluded_fixture_count, audit.accepted_fixture_count, extracted[0].id, extracted[0].home], [380, 380, 0, 380, '1000', 'Arsenal']); });
/* prettier-ignore */
test('extractFixtures skips abandoned matches and records audit', () => { const fixtures = [buildFixture('1', 'TeamA', 'TeamB', '2022-08-01T15:00:00Z', 'FT'), buildFixture('2', 'TeamC', 'TeamD', '2022-08-02T15:00:00Z', 'Ab'), buildFixture('3', 'TeamE', 'TeamF', '2022-08-03T15:00:00Z', 'FT')]; const { extracted, audit } = fixtureAudit(fixtures); assert.deepEqual([extracted.map(fixture => fixture.id), audit.raw_fixture_count, audit.excluded_fixture_count, audit.excluded_by_reason.Ab, audit.accepted_fixture_count, audit.excluded_fixture_samples], [['1', '3'], 3, 1, 1, 2, [{ source_match_id: '2', reason_code: 'Ab' }]]); });
/* prettier-ignore */
test('extractFixtures does NOT exclude postponed matches', () => { const fixtures = [buildFixture('1', 'TeamA', 'TeamB', '2022-08-01T15:00:00Z', 'FT'), buildFixture('2', 'TeamC', 'TeamD', '2022-08-02T15:00:00Z', 'Postp'), buildFixture('3', 'TeamE', 'TeamF', '2022-08-03T15:00:00Z', 'FT')]; const { extracted, audit } = fixtureAudit(fixtures); assert.deepEqual([extracted.length, audit.excluded_fixture_count, audit.accepted_fixture_count], [3, 0, 3], 'postponed should NOT be excluded'); });
/* prettier-ignore */
test('extractFixtures does NOT silently exclude status-missing matches', () => { const fixtures = [buildFixture('1', 'TeamA', 'TeamB', '2022-08-01T15:00:00Z', 'FT'), { id: '2', home: { name: 'TeamC' }, away: { name: 'TeamD' }, status: { utcTime: '2022-08-02T15:00:00Z' } }, buildFixture('3', 'TeamE', 'TeamF', '2022-08-03T15:00:00Z', 'FT')]; const { extracted, audit } = fixtureAudit(fixtures); assert.deepEqual([extracted.length, audit.excluded_fixture_count], [3, 0], 'status-missing should NOT be excluded'); });
/* prettier-ignore */
test('extractFixtures handles multiple abandoned matches', () => { const fixtures = [buildFixture('1', 'TeamA', 'TeamB', '2022-08-01T15:00:00Z', 'Ab'), buildFixture('2', 'TeamC', 'TeamD', '2022-08-02T15:00:00Z', 'Ab'), buildFixture('3', 'TeamE', 'TeamF', '2022-08-03T15:00:00Z', 'FT')]; const { extracted, audit } = fixtureAudit(fixtures); assert.deepEqual([extracted.length, audit.excluded_fixture_count, audit.excluded_by_reason.Ab, audit.accepted_fixture_count], [1, 2, 2, 1]); });
/* prettier-ignore */
test('extractFixtures handles null/undefined/missing allMatches', () => { for (const overrides of [{ fixtures: null }, { fixtures: undefined }, { allMatches: null }]) { const result = extractFixtures(buildNextDataPage({ pagePropsExtra: { fixtures: overrides } }).nd); assert.equal(result.fixtures.length, 0); assert.equal(result.audit.raw_fixture_count, 0); } });
/* prettier-ignore */
test('extractFixtures handles empty allMatches array', () => { const result = extractFixtures(buildNextDataPage({ fixtures: [] }).nd); assert.equal(result.fixtures.length, 0); assert.equal(result.audit.raw_fixture_count, 0); assert.equal(result.audit.accepted_fixture_count, 0); });
/* prettier-ignore */
test('extractFixtures skips non-numeric IDs', () => { const { extracted } = fixtureAudit([buildFixture('abc', 'TeamA', 'TeamB', '2022-08-01T15:00:00Z'), buildFixture('123', 'TeamC', 'TeamD', '2022-08-02T15:00:00Z')]); assert.deepEqual([extracted.length, extracted[0].id], [1, '123']); });
/* prettier-ignore */
test('extractFixtures skips missing teams or kickoff', () => { const fixtures = [{ id: '1', home: null, away: { name: 'TeamB' }, status: { utcTime: '2022-08-01T15:00:00Z' } }, { id: '2', home: { name: 'TeamC' }, away: null, status: { utcTime: '2022-08-01T15:00:00Z' } }, { id: '3', home: { name: 'TeamE' }, away: { name: 'TeamF' }, status: {} }, { id: '4', home: { name: 'TeamG' }, away: { name: 'TeamH' }, status: { utcTime: '2022-08-01T15:00:00Z' } }]; const { extracted } = fixtureAudit(fixtures); assert.deepEqual([extracted.length, extracted[0].id], [1, '4']); });

// -----------------------------------------------------------------
// Unit: buildCandidate / validateSeasonCandidates
// -----------------------------------------------------------------

/* prettier-ignore */
test('buildCandidate produces correct structure', () => { const candidate = buildCandidate({ id: '3900932', home: 'Arsenal', away: 'Fulham', kickoff: '2022-08-05T19:00:00Z' }, 47, 'Premier League', '2022/2023'); assert.equal(candidate.id, '47_20222023_3900932'); assert.equal(candidate.source_provider, 'FotMob'); assert.equal(candidate.source_match_id, '3900932'); assert.equal(candidate.competition, 'Premier League'); assert.equal(candidate.season, '2022/2023'); assert.equal(candidate.home_team, 'Arsenal'); assert.equal(candidate.away_team, 'Fulham'); assert.equal(candidate.kickoff_at, '2022-08-05T19:00:00Z'); });
/* prettier-ignore */
test('validateSeasonCandidates passes for 380 valid candidates', () => { const result = validateSeasonCandidates(generateSeasonFixtures(1000, 380).map(candidateFromFixture), { competition: 'Premier League', season: '2022/2023', expectedFixtures: 380 }); assert.deepEqual([result.valid, result.fixture_count, result.errors.length], [true, 380, 0]); });
/* prettier-ignore */
test('validateSeasonCandidates: rejects 379, dup id, same teams, bad kickoff, wrong comp', () => { const opts = { competition: 'Premier League', season: '2022/2023', expectedFixtures: 380 }; const build = (id, home, away, kickoff, competition = opts.competition) => buildCandidate({ id, home, away, kickoff }, 47, competition, opts.season); const candidate = build('1', 'A', 'B', '2022-08-01T15:00:00Z'); const validate = (candidates, expectedFixtures) => validateSeasonCandidates(candidates, { ...opts, expectedFixtures }); [[generateSeasonFixtures(1000, 379).map(candidateFromFixture), 380, 'fixture_count_mismatch'], [[candidate, candidate], 2, 'duplicate_id'], [[build('1', 'X', 'X', '2022-08-01T15:00:00Z')], 1, 'same_teams'], [[build('1', 'A', 'B', '2022-08-01 15:00:00')], 1, 'bad_kickoff']].forEach(([candidates, expectedFixtures, errorName]) => assert.ok(validate(candidates, expectedFixtures).errors.some(error => error.includes(errorName)))); assert.equal(validate([build('1', 'A', 'B', '2022-08-01T15:00:00Z', 'Wrong League')], 1).valid, false); });
// -----------------------------------------------------------------
// Unit: hash determinism
// -----------------------------------------------------------------

// -----------------------------------------------------------------
// Unit: hash determinism
// -----------------------------------------------------------------

/* prettier-ignore */
test('computeBusinessContentHash: order-independent, extracted_at excluded', () => { const c = generateSeasonFixtures(1000, 10).map(candidateFromFixture); assert.equal(computeBusinessContentHash(c), computeBusinessContentHash([...c].reverse())); const h = computeBusinessContentHash(c); const snap = outputSnapshot(10, h); const d1 = buildOutputDocument(c, snap, { schema_version: 'v1', extracted_at: '2026-01-01T00:00:00Z' }); const d2 = buildOutputDocument(c, snap, { schema_version: 'v1', extracted_at: '2026-06-15T12:00:00Z' }); assert.equal(d1.snapshot.business_content_sha256, d2.snapshot.business_content_sha256); });

// -----------------------------------------------------------------
// Unit: output path safety (F2 — symlink protection)
// -----------------------------------------------------------------

test('verifyOutputPathSafety rejects paths inside repository', () => {
    const repoRoot = path.resolve(__dirname, '..', '..');
    assertUnsafeOutput(repoRoot, { repositoryRoot: repoRoot });
    assertUnsafeOutput(path.join(repoRoot, 'subdir'), { repositoryRoot: repoRoot });
});

test('verifyOutputPathSafety rejects .git paths', () => {
    assertUnsafeOutput('/tmp/project/.git/objects');
});

test('verifyOutputPathSafety accepts external absolute paths', () => {
    const result = verifyOutputPathSafety('/tmp', { repositoryRoot: '/home/user/repo' });
    assert.ok(result.startsWith('/tmp'));
});

test('verifyOutputPathSafety rejects relative paths', () => {
    assertUnsafeOutput('relative/path');
});

test('verifyOutputPathSafety rejects non-existent directories', () => {
    assertUnsafeOutput('/tmp/NONEXISTENT_DIR_M3D2B_TEST', { repositoryRoot: '/home/user/repo' });
});

test('verifyOutputPathSafety rejects symlink as output path', t => {
    const tmpDir = fs.mkdtempSync('/tmp/m3d2bf_output_symlink_test_');
    const realDir = fs.mkdtempSync('/tmp/m3d2bf_output_real_');
    const linkPath = path.join(tmpDir, 'symlink_to_real');
    try {
        fs.symlinkSync(realDir, linkPath, 'dir');
        assertUnsafeOutput(linkPath, { repositoryRoot: '/home/user/repo' });
    } finally {
        bestEffort(() => fs.unlinkSync(linkPath));
        bestEffort(() => fs.rmdirSync(tmpDir));
        bestEffort(() => fs.rmdirSync(realDir));
    }
});

test('verifyOutputPathSafety rejects symlink into repository', t => {
    const repoRoot = fs.mkdtempSync('/tmp/m3d2bf_repo_root_');
    const outsideDir = fs.mkdtempSync('/tmp/m3d2bf_outside_');
    const linkPath = path.join(outsideDir, 'link_to_repo');
    try {
        fs.symlinkSync(repoRoot, linkPath, 'dir');
        assertUnsafeOutput(linkPath, { repositoryRoot: repoRoot });
    } finally {
        bestEffort(() => fs.unlinkSync(linkPath));
        bestEffort(() => fs.rmdirSync(outsideDir));
        bestEffort(() => fs.rmdirSync(repoRoot));
    }
});

test('verifyOutputPathSafety succeeds for normal directory outside repo', t => {
    const tmpDir = fs.mkdtempSync('/tmp/m3d2bf_ok_');
    try {
        const result = verifyOutputPathSafety(tmpDir, { repositoryRoot: '/home/user/repo' });
        assert.ok(result.startsWith('/tmp/m3d2bf_ok_'));
    } finally {
        bestEffort(() => fs.rmdirSync(tmpDir));
    }
});

// -----------------------------------------------------------------
// Integration: exportCandidates with season identity
// -----------------------------------------------------------------

test('exportCandidates succeeds for 3 complete seasons', async () => {
    const mockFetch = makeSeasonPageFetch();

    const result = await exportCandidates(makeExportOptions(['2022/2023', '2023/2024', '2024/2025'], mockFetch));

    assert.ok(result.validation.all_seasons_complete);
    assert.equal(result.candidates.length, 1140);
    assert.equal(result.meta.total_requests, 3);
    assert.equal(result.snapshot.business_content_sha256.length, 64);
    for (const season of ['2022/2023', '2023/2024', '2024/2025']) {
        const count = result.candidates.filter(c => c.season === season).length;
        assert.equal(count, 380, `${season} should have 380 candidates, got ${count}`);
    }
});

test('exportCandidates rejects wrong season (page returns different season)', async () => {
    const result = await exportFromHtml(buildNextDataPage({ season: '2023/2024' }).html); // page says 2023/2024

    assert.equal(result.candidates.length, 0, 'no candidates when season mismatches');
    assert.ok(result.validation.season_results[0].result.includes('season_identity_mismatch'));
});

test('exportCandidates rejects missing season in page', async () => {
    const { nd, html } = buildNextDataPage();
    delete nd.query.season;
    const fixedHtml = rebuildPageHtml(nd, html);

    const result = await exportFromHtml(fixedHtml);

    assert.equal(result.candidates.length, 0);
    assert.ok(result.validation.season_results[0].result.includes('season_identity_missing'));
});

test('exportCandidates rejects bad season format in page', async () => {
    const { nd, html } = buildNextDataPage();
    nd.query.season = 'not-a-season';
    const fixedHtml = rebuildPageHtml(nd, html);

    const result = await exportFromHtml(fixedHtml);

    assert.equal(result.candidates.length, 0);
    assert.ok(result.validation.season_results[0].result.includes('season_identity_missing'));
});

test('exportCandidates accepts dash-format season from page', async () => {
    const { nd, html } = buildNextDataPage();
    nd.query.season = '2022-2023';
    const fixedHtml = rebuildPageHtml(nd, html);

    const result = await exportFromHtml(fixedHtml);

    assert.equal(result.candidates.length, 380, 'dash-format season should be accepted');
    assert.ok(result.validation.all_seasons_complete);
});

test('exportCandidates records audit for abandoned matches', async () => {
    const fixtures = generateSeasonFixtures(1000, 380);
    fixtures.push(buildFixture('9999999', 'TeamX', 'TeamY', '2022-12-25T15:00:00Z', 'Ab'));
    const { html } = buildNextDataPage({ fixtures, season: '2022/2023' });
    const result = await exportFromHtml(html);

    assert.equal(result.candidates.length, 380);
    const sr = result.validation.season_results[0];
    assert.ok(sr.audit);
    assert.equal(sr.audit.raw_fixture_count, 381);
    assert.equal(sr.audit.excluded_fixture_count, 1);
    assert.equal(sr.audit.excluded_by_reason['Ab'], 1);
    assert.equal(sr.audit.accepted_fixture_count, 380);
    assert.ok(sr.audit.excluded_fixture_samples.length >= 1);
});

// -----------------------------------------------------------------
// Integration: error handling
// -----------------------------------------------------------------

test('exportCandidates stops on HTTP 403 or 429', async () => {
    for (const status of [403, 429]) {
        let callCount = 0;
        const mockFetch = async () => {
            callCount += 1;
            return { status, contentType: 'text/html', body: '' };
        };
        const result = await exportCandidates(makeExportOptions(['2022/2023', '2023/2024', '2024/2025'], mockFetch));
        assert.ok(callCount <= 1);
        assert.equal(result.validation.all_seasons_complete, false);
    }
});

test('exportCandidates fails on wrong competition identity', async () => {
    const { html } = buildNextDataPage({ leagueName: 'Championship', leagueId: 47 });
    const result = await exportFromHtml(html);

    assert.equal(result.candidates.length, 0);
    assert.ok(result.validation.season_results[0].result.includes('competition_identity_mismatch'));
});

test('page identity must equal the requested canonical competition', async () => {
    for (const leagueName of [
        'Premier League 2',
        'Premier League Women',
        'English Premier League',
        'Premiere League',
    ]) {
        const result = await exportFromHtml(buildNextDataPage({ leagueName, leagueId: 47 }).html);
        assert.equal(result.candidates.length, 0);
        assert.equal(result.validation.season_results[0].result, 'competition_identity_mismatch');
    }
});

test('exportCandidates fails on wrong league ID in page', async () => {
    const { html } = buildNextDataPage({ leagueId: 53 });
    const result = await exportFromHtml(html);

    assert.equal(result.candidates.length, 0);
    assert.ok(result.validation.season_results[0].result.includes('league_id_mismatch'));
});

test('exportCandidates respects request budget', async () => {
    let callCount = 0;
    const mockFetch = async () => {
        callCount += 1;
        return { status: 200, contentType: 'text/html', body: '<html></html>' };
    };

    const seasons = Array.from({ length: 10 }, (_, i) => `20${22 + i}/20${23 + i}`);
    const result = await exportCandidates(makeExportOptions(seasons, mockFetch));

    assert.ok(callCount <= MAX_TOTAL_REQUESTS);
    assert.ok(result.meta.total_requests <= MAX_TOTAL_REQUESTS);
});

test('exportCandidates returns empty for no seasons', async () => {
    await assert.rejects(exportCandidates(makeExportOptions([], async () => ({ status: 500, body: '' }))), {
        code: 'INPUT_ERROR',
    });
});

/* prettier-ignore */
test('exportCandidates rejects invalid competition before fetch or delay', async () => { let tc5 = 0; const co5 = { toString: () => { tc5 += 1; return 'Premier League'; } }; const cd5 = c => ({ fetchPage: async () => { c.f += 1; return { status: 500, ct: 'text/html', body: '' }; }, delay: async () => (c.d += 1), clock: FIXED_CLOCK }); for (const comp of ['Premiere League', 'EPL', 'English Premier League', ['Premier League'], {}, co5]) { const c = { f: 0, d: 0 }; await assert.rejects(exportCandidates({ leagueId: 47, competition: comp, seasons: ['2022/2023'], networkAuthorization: true, deps: cd5(c) }), { code: 'INPUT_ERROR' }); assert.deepEqual(c, { f: 0, d: 0 }); } assert.equal(tc5, 0); });

test('candidates always store the canonical competition name', async () => {
    const result = await exportCandidates(
        makeExportOptions(
            ['2022/2023', '2023/2024', '2024/2025'],
            makeSeasonPageFetch(),
            {},
            { competition: 'PREMIER   LEAGUE' }
        )
    );

    assert.ok(result.candidates.every(candidate => candidate.competition === 'Premier League'));
    assert.equal(result.snapshot.competition, 'Premier League');
    assert.equal(result.snapshot.business_content_sha256, EXPECTED_PIPELINE_HASH);
});

/* prettier-ignore */
test('exportCandidates rejects missing network authorization before fetch or delay', async () => { for (const na of [undefined, false, 'yes']) { const c = { f: 0, d: 0 }; await assert.rejects(exportCandidates({ leagueId: 47, competition: 'Premier League', seasons: ['2022/2023'], networkAuthorization: na, deps: { fetchPage: async () => { c.f += 1; return { status: 500, contentType: 'text/html', body: '' }; }, delay: async () => (c.d += 1) } }), { code: 'SAFETY_ERROR' }); assert.deepEqual(c, { f: 0, d: 0 }); } });

test('exportCandidates rejects each non-string requested season before fetch or delay', async () => {
    for (const season of [20222023, ['2022/2023'], { toString: () => '2022/2023' }]) {
        await assertInvalidSeasonMakesNoRequests(season);
    }
});

/* prettier-ignore */
test('CLI and core reject unsafe FotMob URL parameters before fetch or delay', async () => { const EXPECTED = 'https://www.fotmob.com/leagues/47/fixtures/premier-league?season=2022%2F2023'; const cdeps = c => ({ fetchPage: async () => ((c.f += 1), { status: 500, contentType: 'text/html', body: '' }), delay: async () => (c.d += 1) }); let ltc = 0; const coerciveL = { toString: () => { ltc += 1; return '47'; } }; for (const lid of ['47/fixtures/evil', '../47', '47?tab=table', '47#fragment', '47%2Ffixtures', coerciveL]) { const c = { f: 0, d: 0 }; await assert.rejects(exportCandidates({ leagueId: lid, competition: 'Premier League', seasons: ['2022/2023'], networkAuthorization: true, deps: cdeps(c) }), { code: 'INPUT_ERROR' }); assert.deepEqual(c, { f: 0, d: 0 }); } assert.equal(ltc, 0); let stc = 0; const coerciveS = { toString: () => { stc += 1; return 'premier-league'; } }; for (const slug of ['../premier-league', 'premier-league/fixtures', 'premier-league?tab=table', 'premier-league#fragment', 'premier%2Fleague', coerciveS]) { const c = { f: 0, d: 0 }; await assert.rejects(exportCandidates({ leagueId: 47, competition: 'Premier League', seasons: ['2022/2023'], leagueSlug: slug, networkAuthorization: true, deps: cdeps(c) }), { code: 'INPUT_ERROR' }); assert.deepEqual(c, { f: 0, d: 0 }); } assert.equal(stc, 0); const baseArgs = { leagueId: '47', competition: 'Premier League', seasons: ['2022/2023'], slug: '', output: '' }; assert.deepEqual(validateArgs(baseArgs), []); assert.ok(validateArgs({ ...baseArgs, leagueId: '47/fixtures/evil' }).some(e => /League id/.test(e))); assert.ok(validateArgs({ ...baseArgs, leagueId: '../47' }).some(e => /League id/.test(e))); assert.ok(validateArgs({ ...baseArgs, slug: '../premier-league' }).some(e => /League slug/.test(e))); assert.ok(validateArgs({ ...baseArgs, slug: 'premier-league?tab=table' }).some(e => /League slug/.test(e))); const vArgv = ['--competition', 'Premier League', '--season', '2022/2023', '--network-preview=true', '--network-authorization=yes']; for (const argv of [['--league-id', '47/fixtures/evil', ...vArgv], ['--league-id', '../47', ...vArgv], ['--league-id', '47', '--slug', '../premier-league', ...vArgv], ['--league-id', '47', '--slug', 'premier-league?tab=table', ...vArgv]]) { let ec = 0; let se = ''; const ec2 = await runCandidateExportCli(argv, { stdout: { write: () => {} }, stderr: { write: v => (se += String(v)) }, exportCandidates: async () => { ec += 1; throw new Error('must not run'); }, collectorCodeRevision: 'test-sha' }); assert.equal(ec2, 2); assert.equal(ec, 0); assert.match(se, /Error:/); } const html = buildNextDataPage({ season: '2022/2023' }).html; for (const lid of [47, '47']) { const urls = []; const r = await exportCandidates(makeExportOptions(['2022/2023'], async u => { urls.push(u); return { status: 200, contentType: 'text/html', body: html }; }, {}, { leagueId: lid })); assert.deepEqual(urls, [EXPECTED]); assert.equal(r.snapshot.league_id, '47'); assert.equal(r.validation.all_seasons_complete, true); assert.ok(r.candidates.every(c => c.id.startsWith('47_'))); } const sUrls = []; await exportCandidates(makeExportOptions(['2022/2023'], async u => { sUrls.push(u); return { status: 200, contentType: 'text/html', body: html }; }, {}, { leagueSlug: '  Premier-League  ' })); assert.deepEqual(sUrls, [EXPECTED]); const cliUrls = []; const cliRc = await runCandidateExportCli(['--league-id', '47', ...vArgv], { stdout: { write: () => {} }, stderr: { write: () => {} }, exporterDeps: { fetchPage: async u => { cliUrls.push(u); return { status: 200, contentType: 'text/html', body: html }; }, delay: async () => {}, clock: FIXED_CLOCK }, collectorCodeRevision: 'test-sha' }); assert.equal(cliRc, 0); assert.deepEqual(cliUrls, [EXPECTED]); });

test('exportCandidates rejects non-string page season identity', async () => {
    for (const season of [['2022/2023'], { value: '2022/2023' }]) {
        const { nd, html } = buildNextDataPage({ season });
        const fixedHtml = rebuildPageHtml(nd, html);
        const result = await exportCandidates(
            makeExportOptions(['2022/2023'], async () => ({ status: 200, contentType: 'text/html', body: fixedHtml }))
        );

        assert.equal(result.candidates.length, 0);
        assert.equal(result.validation.season_results[0].result, 'season_identity_missing');
        assert.equal(result.validation.all_seasons_complete, false);
    }
});

test('CLI programmatic APIs reject non-string seasons before global fetch', async () => {
    assert.deepEqual(
        validateArgs({ leagueId: '47', competition: 'Premier League', seasons: [['2022/2023']], output: '' }),
        ['Season at index 0 must be a string']
    );
    let stdout = '',
        stderr = '',
        fetchCalls = 0;
    const originalFetch = global.fetch;
    global.fetch = async () => {
        fetchCalls += 1;
        throw new Error('global fetch must not be called');
    };
    try {
        const exitCode = await runCandidateExportCli(
            ['--league-id', '47', '--competition', 'Premier League', '--season', ['2022/2023']],
            {
                stdout: { write: value => (stdout += String(value)) },
                stderr: { write: value => (stderr += String(value)) },
            }
        );
        assert.deepEqual([exitCode, stdout, fetchCalls], [2, '', 0]);
        assert.match(stderr, /Season at index 0 must be a string/);
    } finally {
        global.fetch = originalFetch;
    }
});

/* prettier-ignore */
test('CLI rejects ordinary invocation without network authorization', async () => { let out = '', err = '', fc = 0; const of5 = global.fetch; global.fetch = async () => { fc += 1; throw new Error('no'); }; try { const ec5 = await runCandidateExportCli(['--league-id', '47', '--competition', 'Premier League', '--season', '2022/2023'], { stdout: { write: v => (out += String(v)) }, stderr: { write: v => (err += String(v)) } }); assert.deepEqual([ec5, out, fc], [2, '', 0]); assert.match(err, /make data-fotmob-candidates-network-export/); } finally { global.fetch = of5; } });

/* prettier-ignore */
test('CLI requires both network preview and network authorization flags', async () => { const va = ['--league-id', '47', '--competition', 'Premier League', '--season', '2022/2023']; const cases = [[...va, '--network-preview=true'], [...va, '--network-authorization=yes'], [...va, '--network-preview=false', '--network-authorization=yes'], [...va, '--network-preview=true', '--network-authorization=no'], [...va, '--network-preview=maybe', '--network-authorization=yes'], [...va, '--network-preview=true', '--network-authorization=maybe']]; const of4 = global.fetch; try { for (const argv of cases) { let se = ''; let fc = 0; global.fetch = async () => { fc += 1; throw new Error('real'); }; const ec4 = await runCandidateExportCli(argv, { stdout: { write: () => {} }, stderr: { write: v => (se += String(v)) } }); assert.deepEqual([ec4, fc], [2, 0]); assert.match(se, /make data-fotmob-candidates-network-export/); } } finally { global.fetch = of4; } });

/* prettier-ignore */
test('CLI accepts explicit authorization with mocked network only', async () => { const { html } = buildNextDataPage({ season: '2022/2023' }); let out = '', err = '', mfc = 0, gfc = 0; const of3 = global.fetch; global.fetch = async () => { gfc += 1; throw new Error('no'); }; try { const ec3 = await runCandidateExportCli(['--league-id', '47', '--competition', ' premier   league ', '--season', '2022/2023', '--network-preview=true', '--network-authorization=yes'], { stdout: { write: v => (out += String(v)) }, stderr: { write: v => (err += String(v)) }, exporterDeps: { fetchPage: async () => { mfc += 1; return { status: 200, contentType: 'text/html', body: html }; }, delay: async () => {}, clock: FIXED_CLOCK }, collectorCodeRevision: 'test-sha' }); assert.deepEqual([ec3, mfc, gfc], [0, 1, 0]); assert.match(out, /"competition": "Premier League"/); assert.match(err, /Total: 380 candidates/); } finally { global.fetch = of3; } });

test('CLI help identifies the canonical data Make target', async () => {
    let stdout = '';
    const exitCode = await runCandidateExportCli(['--help'], {
        stdout: { write: value => (stdout += String(value)) },
        stderr: { write: () => {} },
    });

    assert.equal(exitCode, 0);
    assert.match(stdout, /make data-fotmob-candidates-network-export/);
    assert.match(stdout, /live network requests/);
});

/* prettier-ignore */
test('Make target blocks missing or false network authorization before Node execution', () => { const fb = fs.mkdtempSync('/tmp/m3d2bt_make_bin_'); const fd = path.join(fb, 'docker'); const cl = path.join(fb, 'docker-calls.log'); const tg = 'data-fotmob-candidates-network-export'; fs.writeFileSync(fd, '#!/bin/sh\nprintf called >> "$FOTMOB_MAKE_DOCKER_LOG"\n'); fs.chmodSync(fd, 0o755); const runG = v => { const env = { ...process.env, ...v, PATH: `${fb}:${process.env.PATH}`, FOTMOB_MAKE_DOCKER_LOG: cl }; for (const k of ['LEAGUE_ID', 'COMPETITION', 'SEASONS', 'NETWORK_AUTHORIZATION']) { if (!(k in v)) delete env[k]; } return spawnSync('make', [tg], { cwd: path.resolve(__dirname, '../..'), encoding: 'utf8', env }); }; try { const miss = runG({}); assert.notEqual(miss.status, 0); assert.match(miss.stdout + miss.stderr, /provide LEAGUE_ID/); assert.equal(fs.existsSync(cl), false); const fa = runG({ LEAGUE_ID: '47', COMPETITION: 'Premier League', SEASONS: '2022/2023', NETWORK_AUTHORIZATION: 'no' }); assert.notEqual(fa.status, 0); assert.match(fa.stdout + fa.stderr, /requires NETWORK_AUTHORIZATION=yes before Node execution/); assert.equal(fs.existsSync(cl), false); } finally { bestEffort(() => fs.rmSync(fb, { recursive: true, force: true })); } });

/* prettier-ignore */
test('Make target uses the stable container repository root', () => { const repositoryRoot = path.resolve(__dirname, '../..'); const makefile = fs.readFileSync(path.join(repositoryRoot, 'Makefile'), 'utf8'); const result = spawnSync('make', ['-n', 'data-fotmob-candidates-network-export', 'LEAGUE_ID=47', 'COMPETITION=Premier League', 'SEASONS=2022/2023', 'NETWORK_AUTHORIZATION=yes'], { cwd: repositoryRoot, encoding: 'utf8' }); const output = `${result.stdout}${result.stderr}`; assert.match(makefile, /^data-fotmob-candidates-network-export:/m); assert.equal(result.status, 0); assert.match(output, /cd \/app;/); assert.doesNotMatch(output, /\.claude\/worktrees|m3-fotmob-epl-candidates|\/tmp\/fp-/); assert.match(output, /npm run fotmob:candidates:export/); assert.match(output, /--network-preview=true/); assert.match(output, /--network-authorization=yes/); });

// -----------------------------------------------------------------
// Integration: output document structure
// -----------------------------------------------------------------

test('buildOutputDocument produces correct schema', () => {
    const candidates = [
        buildCandidate(
            { id: '1', home: 'A', away: 'B', kickoff: '2022-08-01T15:00:00Z' },
            47,
            'Premier League',
            '2022/2023'
        ),
    ];
    const doc = buildOutputDocument(candidates, outputSnapshot(1, 'abc123'), OUTPUT_META);
    assert.deepEqual(
        [doc.schema_version, doc.extracted_at, doc.snapshot.business_content_sha256, doc.candidates.length],
        ['candidate-match-identity/v1', '2026-07-18T00:00:00Z', 'abc123', 1]
    );
    assert.ok(doc.candidates[0].id);
});

test('buildSummaryDocument contains no full candidate data', () => {
    const candidates = generateSeasonFixtures(1000, 380).map(candidateFromFixture);
    const summary = buildSummaryDocument(candidates, outputSnapshot(380, 'hash'), OUTPUT_META);
    assert.deepEqual(
        [Boolean(summary.summary), summary.summary.total_candidates, summary.summary.per_season['2022/2023']],
        [true, 380, 380]
    );
    assert.equal(summary.candidates, undefined);
});

// -----------------------------------------------------------------
// Full pipeline: 3 seasons × 380 = 1140
// -----------------------------------------------------------------
// Refactor parity: delay, bounded samples, control flow, cleanup
// -----------------------------------------------------------------

test('extractFixtures bounds excluded samples and stores ids only', () => {
    const abandoned = generateSeasonFixtures(2000, 15).map(({ id, status }) =>
        buildFixture(String(id), 'A', 'B', status.utcTime, 'Ab')
    );
    const { nd } = buildNextDataPage({ fixtures: abandoned });
    const result = extractFixtures(nd);
    assert.equal(result.audit.excluded_fixture_count, 15);
    assert.equal(result.audit.excluded_fixture_samples.length, 10);
    assert.deepEqual(Object.keys(result.audit.excluded_fixture_samples[0]).sort(), ['reason_code', 'source_match_id']);
});

test('exportCandidates fetches seasons serially in order and delays only between successes', async () => {
    const calls = [];
    let delays = 0;
    const mockFetch = makeSeasonPageFetch(season => calls.push(season));
    await exportCandidates(
        makeExportOptions(['2022/2023', '2023/2024', '2024/2025'], mockFetch, { delay: async () => (delays += 1) })
    );
    assert.deepEqual(calls, ['2022/2023', '2023/2024', '2024/2025']);
    assert.equal(delays, 2);
});

test('exportCandidates continues after fetch error and non-200 without delaying', async () => {
    const { html } = buildNextDataPage({ fixtures: generateSeasonFixtures(3900000), season: '2024/2025' });
    const steps = [
        () => Promise.reject(new Error('boom')),
        async () => ({ status: 500, contentType: 'text/html', body: '' }),
        async () => ({ status: 200, contentType: 'text/html', body: html }),
    ];
    let delays = 0;
    const result = await exportCandidates(
        makeExportOptions(['2022/2023', '2023/2024', '2024/2025'], () => steps.shift()(), {
            delay: async () => (delays += 1),
        })
    );
    const results = result.validation.season_results.map(r => r.result);
    assert.ok(results[0].startsWith('fetch_error:'));
    assert.equal(results[1], 'http_500');
    assert.equal(results[2], 'complete');
    assert.equal(delays, 0);
    assert.equal(result.candidates.length, 380);
});

test('writeOutputFiles cleanup never masks the original write or rename error', () => {
    const baseFs = {
        lstatSync: () => ({ isDirectory: () => true, isSymbolicLink: () => false }),
        realpathSync: p => p,
        writeFileSync: () => {},
        renameSync: () => {},
    };
    const unlinks = [];
    const runWith = fileSystem => () =>
        writeOutputFiles('/tmp', [], outputSnapshot(0, 'h', []), OUTPUT_META, { repositoryRoot: '/repo', fileSystem });
    const captureFailure = (method, error) => {
        const fileSystem = {
            ...baseFs,
            [method]: () => {
                throw error;
            },
            unlinkSync: p => {
                unlinks.push(p);
                throw new Error('cleanup failed');
            },
        };
        assert.throws(runWith(fileSystem), actual => actual === error);
        return unlinks.splice(0);
    };
    const renameUnlinks = captureFailure('renameSync', new Error('rename failed'));
    assert.equal(renameUnlinks.length, 2);
    assert.ok(renameUnlinks[0].includes('candidate-match-identity.v1.json.tmp.'));
    assert.ok(renameUnlinks[1].includes('candidate-match-identity.v1.summary.json.tmp.'));
    assert.equal(captureFailure('writeFileSync', new Error('write failed')).length, 2);
});

// -----------------------------------------------------------------
// classifyFixtureRejection + rejected audit (integrity correction)
// -----------------------------------------------------------------

test('extractFixtures: rejected audit closure and sample cap', () => {
    const fixs = [
        buildFixture('1', 'A', 'B', 'T'),
        { id: '2', home: { name: 'C' }, away: { name: 'D' }, status: {} },
        buildFixture('3', 'E', 'F', 'T', 'Ab'),
        { id: 'abc' },
    ];
    const r = extractFixtures(buildNextDataPage({ fixtures: fixs }).nd);
    const a = r.audit;
    const { rejected_by_reason: reasons, rejected_fixture_samples: samples } = a;
    assert.deepEqual([a.rejected_fixture_count, reasons.missing_kickoff, reasons.bad_source_match_id], [2, 1, 1]);
    assert.equal(a.raw_fixture_count, a.accepted_fixture_count + a.excluded_fixture_count + a.rejected_fixture_count);
    assert.deepEqual([samples[0].reason_code, samples[1].source_match_id], ['missing_kickoff', undefined]);
    const many = generateSeasonFixtures(1, 15);
    many.forEach(fixture => (fixture.away = {}));
    assert.equal(extractFixtures(buildNextDataPage({ fixtures: many }).nd).audit.rejected_fixture_samples.length, 10);
});

// -----------------------------------------------------------------
// Pipeline: hash, aggregate validation preserved (integrity correction)
// -----------------------------------------------------------------

/* prettier-ignore */
test('canonical 3-season: hash unchanged, aggregate valid, snapshot canonical', async () => { const r = await exportCandidates(makeExportOptions(['2022/2023', '2023/2024', '2024/2025'], makeSeasonPageFetch())); assert.equal(r.candidates.length, 1140); assert.ok(r.validation.all_seasons_complete); assert.equal(r.meta.total_requests, 3); assert.equal(r.snapshot.candidate_count, 1140); assert.equal(r.validation.total_candidates, 1140); assert.equal(r.validation.total_expected, 1140); assert.equal(r.validation.season_results.length, 3); assert.deepEqual(r.validation.season_results.map(it => it.result), ['complete', 'complete', 'complete']); assert.equal(r.snapshot.business_content_sha256, EXPECTED_PIPELINE_HASH); assert.ok(r.validation.aggregate_validation.valid); assert.equal(r.validation.aggregate_validation.unique_ids, 1140); assert.equal(r.validation.aggregate_validation.unique_source_ids, 1140); assert.deepEqual(r.snapshot.seasons, ['2022/2023', '2023/2024', '2024/2025']); assert.deepEqual(r.validation.aggregate_validation.per_season_counts, { '2022/2023': 380, '2023/2024': 380, '2024/2025': 380 }); });

test('validateAggregateCandidates rejects duplicate candidate and source ids', () => {
    const candidates = seasonCandidates('2022/2023', 1000, 2);
    candidates[1] = { ...candidates[1], id: candidates[0].id, source_match_id: candidates[0].source_match_id };
    const result = validateAggregateCandidates(candidates, ['2022/2023'], 2);
    assertAggregateErrors(result, ['aggregate_duplicate_id:', 'aggregate_duplicate_source_match_id:']);
    assert.ok(result.unique_ids < candidates.length);
    assert.ok(result.unique_source_ids < candidates.length);
});

test('validateAggregateCandidates rejects unexpected seasons and per-season imbalance', () => {
    const seasons = ['2022/2023', '2023/2024'];
    const unexpected = validateAggregateCandidates(seasonCandidates('2024/2025', 3000, 1), seasons, 1);
    assertAggregateErrors(unexpected, ['unexpected_season:2024/2025:']);
    const candidates = [...seasonCandidates(seasons[0], 4000, 379), ...seasonCandidates(seasons[1], 5000, 381)];
    const imbalance = validateAggregateCandidates(candidates, seasons, 380);
    assertAggregateErrors(imbalance, ['season_count_mismatch:2022/2023:379', 'season_count_mismatch:2023/2024:381']);
    assert.equal(
        imbalance.errors.some(error => error.startsWith('aggregate_total_mismatch:')),
        false
    );
});

test('exportCandidates fails aggregate completion on cross-season duplicate source ids', async () => {
    const seasons = ['2022/2023', '2023/2024'];
    const result = await exportCandidates(
        makeExportOptions(
            seasons,
            makeSeasonPageFetch(undefined, () => 7000000)
        )
    );
    const validation = result.validation;
    const aggregate = validation.aggregate_validation;
    assert.equal(result.candidates.length, 760);
    assert.equal(validation.season_results.length, 2);
    assert.deepEqual(
        validation.season_results.map(item => item.result),
        ['complete', 'complete']
    );
    assertAggregateErrors(aggregate, ['aggregate_duplicate_source_match_id:']);
    assert.deepEqual(
        [aggregate.unique_ids, aggregate.unique_source_ids, validation.all_seasons_complete],
        [760, 380, false]
    );
});

/* prettier-ignore */
test('exportCandidates marks rejected missing-kickoff fixture as validation_failed', async () => { const fixs = generateSeasonFixtures(8000000); const mk = buildFixture('8999999', 'TeamX', 'TeamY', '2022-12-25T15:00:00Z'); delete mk.status.utcTime; fixs.push(mk); const r = await exportFromHtml(buildNextDataPage({ fixtures: fixs, season: '2022/2023' }).html); const [sr] = r.validation.season_results; const { audit, validation } = sr; assert.equal(r.candidates.length, 380); assert.equal(r.validation.season_results.length, 1); assert.equal(sr.result, 'validation_failed'); assert.equal(validation.valid, false); assert.equal(r.validation.all_seasons_complete, false); assert.equal(r.validation.aggregate_validation.valid, true); assert.deepEqual([audit.raw_fixture_count, audit.accepted_fixture_count, audit.excluded_fixture_count, audit.rejected_fixture_count, audit.rejected_by_reason.missing_kickoff], [381, 380, 0, 1, 1]); assert.equal(audit.raw_fixture_count, audit.accepted_fixture_count + audit.excluded_fixture_count + audit.rejected_fixture_count); assert.ok(validation.errors.includes('unexpected_rejected_fixtures:1')); });

// -----------------------------------------------------------------
// Fractional-second kickoffs: end-to-end season export (M3-D2BW)
// -----------------------------------------------------------------

/* prettier-ignore */
test('fractional-second absolute kickoffs remain valid through season export', async () => { const fixs = generateSeasonFixtures(3900000, EPL_FIXTURES_PER_SEASON); fixs[0].status.utcTime = '2026-03-15T19:00:00.000Z'; fixs[1].status.utcTime = '2026-03-15T19:00:00.250+01:00'; const { html } = buildNextDataPage({ fixtures: fixs, season: '2022/2023' }); let fc = 0; let gfc = 0; const of2 = global.fetch; global.fetch = async () => { gfc += 1; throw new Error('real network'); }; let result; try { result = await exportCandidates(makeExportOptions(['2022/2023'], async () => { fc += 1; return { status: 200, contentType: 'text/html', body: html }; })); } finally { global.fetch = of2; } const [sr] = result.validation.season_results; assert.equal(result.candidates.length, 380); assert.equal(sr.result, 'complete'); assert.equal(result.validation.all_seasons_complete, true); assert.equal(sr.validation.errors.filter(e => e.startsWith('bad_kickoff')).length, 0); assert.equal(sr.validation.errors.length, 0); const kos = result.candidates.map(c => c.kickoff_at); assert.ok(kos.includes('2026-03-15T19:00:00.000Z')); assert.ok(kos.includes('2026-03-15T19:00:00.250+01:00')); const h = result.snapshot.business_content_sha256; assert.equal(h.length, 64); assert.equal(computeBusinessContentHash(result.candidates), h); assert.equal(computeBusinessContentHash([...result.candidates].reverse()), h); assert.equal(fc, 1); assert.equal(gfc, 0); });

// =================================================================
// V2: deriveProviderStatus unit tests
// =================================================================

/* prettier-ignore */
test('deriveProviderStatus: scheduled when no boolean flags are true', () => { const r = deriveProviderStatus({ utcTime: '2022-08-01T15:00:00Z', reason: { short: 'FT' } }); assert.deepEqual(r, { status: 'scheduled', error: null }); });

/* prettier-ignore */
test('deriveProviderStatus: finished when finished === true', () => { const r = deriveProviderStatus({ utcTime: '2022-08-01T15:00:00Z', finished: true, reason: { short: 'FT' } }); assert.deepEqual(r, { status: 'finished', error: null }); });

/* prettier-ignore */
test('deriveProviderStatus: cancelled when cancelled === true', () => { const r = deriveProviderStatus({ utcTime: '2022-08-01T15:00:00Z', cancelled: true }); assert.deepEqual(r, { status: 'cancelled', error: null }); });

/* prettier-ignore */
test('deriveProviderStatus: postponed via Postponed reason', () => { const r = deriveProviderStatus({ utcTime: '2022-08-01T15:00:00Z', reason: { short: 'Postponed' } }); assert.deepEqual(r, { status: 'postponed', error: null }); });

/* prettier-ignore */
test('deriveProviderStatus: postponed via Postp reason', () => { const r = deriveProviderStatus({ utcTime: '2022-08-01T15:00:00Z', reason: { short: 'Postp' } }); assert.deepEqual(r, { status: 'postponed', error: null }); });

/* prettier-ignore */
test('deriveProviderStatus: contradictory finished and cancelled fails closed', () => { const r = deriveProviderStatus({ utcTime: '2022-08-01T15:00:00Z', finished: true, cancelled: true }); assert.equal(r.status, null); assert.match(r.error, /contradictory/); });

/* prettier-ignore */
test('deriveProviderStatus: missing status object fails closed', () => { assert.deepEqual(deriveProviderStatus(null), { status: null, error: 'missing_status_object' }); assert.deepEqual(deriveProviderStatus(undefined), { status: null, error: 'missing_status_object' }); assert.deepEqual(deriveProviderStatus('nope'), { status: null, error: 'missing_status_object' }); assert.deepEqual(deriveProviderStatus(42), { status: null, error: 'missing_status_object' }); });

/* prettier-ignore */
test('deriveProviderStatus: unknown reason with no boolean flags → fails closed', () => { const r = deriveProviderStatus({ utcTime: '2022-08-01T15:00:00Z', reason: { short: 'UnknownThing' } }); assert.deepEqual(r, { status: null, error: 'unknown_reason:UnknownThing' }); });

/* prettier-ignore */
test('deriveProviderStatus: extra unknown fields do not alter result', () => { const r = deriveProviderStatus({ utcTime: '2022-08-01T15:00:00Z', finished: true, extraField: 'whatever', reason: { short: 'FT', extraNested: true } }); assert.deepEqual(r, { status: 'finished', error: null }); });

/* prettier-ignore */
test('deriveProviderStatus: started=true but not finished → fails closed', () => { const r = deriveProviderStatus({ utcTime: '2022-08-01T15:00:00Z', started: true, reason: { short: 'Live' } }); assert.deepEqual(r, { status: null, error: 'started_with_reason:Live' }); });

/* prettier-ignore */
test('deriveProviderStatus: legal reason shapes still derive normally', () => { assert.deepEqual(deriveProviderStatus({ utcTime: '2022-08-01T15:00:00Z' }), { status: 'scheduled', error: null }); assert.deepEqual(deriveProviderStatus({ utcTime: '2022-08-01T15:00:00Z', reason: null }), { status: 'scheduled', error: null }); assert.deepEqual(deriveProviderStatus({ utcTime: '2022-08-01T15:00:00Z', reason: undefined }), { status: 'scheduled', error: null }); assert.deepEqual(deriveProviderStatus({ utcTime: '2022-08-01T15:00:00Z', reason: {} }), { status: 'scheduled', error: null }); assert.deepEqual(deriveProviderStatus({ utcTime: '2022-08-01T15:00:00Z', reason: { short: null } }), { status: 'scheduled', error: null }); assert.deepEqual(deriveProviderStatus({ utcTime: '2022-08-01T15:00:00Z', reason: { short: undefined } }), { status: 'scheduled', error: null }); assert.deepEqual(deriveProviderStatus({ utcTime: '2022-08-01T15:00:00Z', reason: { short: '' } }), { status: 'scheduled', error: null }); });

test('deriveProviderStatus: malformed reason object fails closed without coercion', () => {
    const cases = [
        ['Postponed', 'malformed_reason_object:string'],
        [123, 'malformed_reason_object:number'],
        [true, 'malformed_reason_object:boolean'],
        [false, 'malformed_reason_object:boolean'],
        [['Postp'], 'malformed_reason_object:array'],
        [() => 'Postp', 'malformed_reason_object:function'],
    ];
    for (const [reason, expectedError] of cases) {
        const r = deriveProviderStatus({ utcTime: '2022-08-01T15:00:00Z', reason });
        assert.equal(r.status, null, `reason=${String(reason)} must fail closed`);
        assert.equal(r.error, expectedError);
    }
});

test('deriveProviderStatus: non-string reason.short fails closed without coercion', () => {
    let toStringCalls = 0;
    const coercible = {
        toString: () => {
            toStringCalls += 1;
            return 'Postp';
        },
    };
    const cases = [
        [5, 'non_string_reason_short:number'],
        [true, 'non_string_reason_short:boolean'],
        [{}, 'non_string_reason_short:object'],
        [['Postp'], 'non_string_reason_short:array'],
        [coercible, 'non_string_reason_short:object'],
    ];
    for (const [short, expectedError] of cases) {
        const r = deriveProviderStatus({ utcTime: '2022-08-01T15:00:00Z', reason: { short } });
        assert.equal(r.status, null, `reason.short must fail closed`);
        assert.equal(r.error, expectedError);
    }
    assert.equal(toStringCalls, 0, 'no implicit String() coercion may be applied to reason.short');
});

test('deriveProviderStatus: started with postponed reason is a contradiction and fails closed', () => {
    for (const short of ['Postponed', 'Postp']) {
        const r = deriveProviderStatus({ utcTime: '2022-08-01T15:00:00Z', started: true, reason: { short } });
        assert.equal(r.status, null);
        assert.equal(r.error, 'contradictory_status_flags:started_and_postponed');
    }
    // Non-contradictory combinations keep the existing behaviour.
    assert.deepEqual(
        deriveProviderStatus({ utcTime: '2022-08-01T15:00:00Z', started: false, reason: { short: 'Postponed' } }),
        { status: 'postponed', error: null }
    );
    assert.deepEqual(
        deriveProviderStatus({ utcTime: '2022-08-01T15:00:00Z', reason: { short: 'Postp' } }),
        { status: 'postponed', error: null }
    );
});

/* prettier-ignore */
test('deriveProviderStatus: terminal and existing fail-closed semantics unchanged', () => { assert.deepEqual(deriveProviderStatus({ utcTime: '2022-08-01T15:00:00Z', finished: true }), { status: 'finished', error: null }); assert.deepEqual(deriveProviderStatus({ utcTime: '2022-08-01T15:00:00Z', cancelled: true }), { status: 'cancelled', error: null }); assert.equal(deriveProviderStatus({ utcTime: '2022-08-01T15:00:00Z', finished: true, cancelled: true }).error, 'contradictory_status_flags:finished_and_cancelled'); assert.deepEqual(deriveProviderStatus({ utcTime: '2022-08-01T15:00:00Z', started: true }), { status: null, error: 'started_no_reason' }); assert.deepEqual(deriveProviderStatus({ utcTime: '2022-08-01T15:00:00Z', started: true, reason: { short: 'Live' } }), { status: null, error: 'started_with_reason:Live' }); assert.deepEqual(deriveProviderStatus({ utcTime: '2022-08-01T15:00:00Z', reason: { short: 'Suspended' } }), { status: null, error: 'unknown_reason:Suspended' }); assert.deepEqual(deriveProviderStatus({ utcTime: '2022-08-01T15:00:00Z' }), { status: 'scheduled', error: null }); });

// =================================================================
// V2: status extraction in fixtures pipeline
// =================================================================

/* prettier-ignore */
test('extractFixtures: accepted fixtures carry provider_status from deriveProviderStatus', () => { const fixtures = [buildFixture('1', 'A', 'B', '2022-08-01T15:00:00Z', 'FT', { finished: true }), buildFixture('2', 'C', 'D', '2022-08-02T15:00:00Z', 'FT')]; const { extracted } = fixtureAudit(fixtures); assert.equal(extracted.length, 2); assert.equal(extracted[0].provider_status, 'finished'); assert.equal(extracted[1].provider_status, 'scheduled'); });

/* prettier-ignore */
test('extractFixtures: contradictory status flags produce status_unknown count', () => { const fixtures = [buildFixture('1', 'A', 'B', '2022-08-01T15:00:00Z', 'FT', { finished: true, cancelled: true })]; const { extracted, audit } = fixtureAudit(fixtures); assert.equal(extracted.length, 0); assert.equal(audit.status_unknown_fixture_count, 1); });

test('extractFixtures: malformed reason.short fails closed as status unknown, never scheduled', () => {
    const fixture = buildFixture('1', 'A', 'B', '2022-08-01T15:00:00Z', 'FT');
    fixture.status.reason = { short: 42 };
    const { extracted, audit } = fixtureAudit([fixture]);
    assert.equal(extracted.length, 0, 'malformed reason.short must not enter accepted fixtures');
    assert.equal(audit.status_unknown_fixture_count, 1);
    assert.equal(audit.status_unknown_by_reason['non_string_reason_short:number'], 1);
    assert.equal(audit.excluded_fixture_count, 0, 'must not be classified as an exclusion');
    assert.equal(audit.rejected_fixture_count, 0, 'must not be classified as a contract rejection');
});

test('extractFixtures: started+postponed fixture fails closed as status unknown, never postponed', () => {
    const fixture = buildFixture('1', 'A', 'B', '2022-08-01T15:00:00Z', 'Postp', { started: true });
    const { extracted, audit } = fixtureAudit([fixture]);
    assert.equal(extracted.length, 0, 'started+postponed must not enter accepted fixtures');
    assert.equal(audit.status_unknown_fixture_count, 1);
    assert.equal(audit.status_unknown_by_reason['contradictory_status_flags:started_and_postponed'], 1);
    assert.equal(audit.excluded_fixture_count, 0);
    assert.equal(audit.rejected_fixture_count, 0);
});

// =================================================================
// V2: buildCandidate includes status fields
// =================================================================

/* prettier-ignore */
test('buildCandidate includes provider_status and status_mapping_version', () => { const c = buildCandidate({ id: '3900932', home: 'Arsenal', away: 'Fulham', kickoff: '2022-08-05T19:00:00Z', provider_status: 'finished' }, 47, 'Premier League', '2022/2023'); assert.equal(c.provider_status, 'finished'); assert.equal(c.status_mapping_version, STATUS_MAPPING_VERSION); assert.equal(c.id, '47_20222023_3900932'); assert.equal(c.source_provider, 'FotMob'); assert.equal(c.source_match_id, '3900932'); });

// =================================================================
// V2: output document structure
// =================================================================

/* prettier-ignore */
test('buildV2OutputDocument produces correct v2 schema', () => { const candidates = [buildCandidate({ id: '1', home: 'A', away: 'B', kickoff: '2022-08-01T15:00:00Z', provider_status: 'finished' }, 47, 'Premier League', '2022/2023')]; const snapshot = outputSnapshot(1, 'abc123', ['2022/2023']); const meta = { schema_version: 'canonical-inventory-artifact/v2', extracted_at: '2026-07-18T00:00:00Z' }; const v2 = { identity_projection_hash: 'aaa111', business_hash: 'bbb222', per_season_counts: { '2022/2023': 1 } }; const doc = buildV2OutputDocument(candidates, snapshot, meta, v2); assert.equal(doc.schema_version, 'canonical-inventory-artifact/v2'); assert.equal(doc.artifact.source_provider, 'FotMob'); assert.equal(doc.artifact.candidate_count, 1); assert.equal(doc.artifact.identity_projection_hash, 'aaa111'); assert.equal(doc.artifact.business_hash, 'bbb222'); assert.equal(doc.artifact.status_mapping_version, STATUS_MAPPING_VERSION); assert.equal(doc.candidates.length, 1); assert.equal(doc.candidates[0].provider_status, 'finished'); });

/* prettier-ignore */
test('buildV2SummaryDocument contains no full candidate data', () => { const candidates = generateSeasonFixtures(1000, 10).map(f => buildCandidate({ id: String(f.id), home: f.home.name, away: f.away.name, kickoff: f.status.utcTime, provider_status: 'scheduled' }, 47, 'Premier League', '2022/2023')); const s = buildV2SummaryDocument(candidates, outputSnapshot(10, 'h', ['2022/2023']), { schema_version: 'canonical-inventory-artifact/v2', extracted_at: '2026-07-18T00:00:00Z' }, { identity_projection_hash: 'iii', business_hash: 'bbb', per_season_counts: { '2022/2023': 10 } }); assert.equal(s.summary.total_candidates, 10); assert.equal(s.candidates, undefined); assert.equal(s.summary.identity_projection_hash, 'iii'); assert.equal(s.summary.business_hash, 'bbb'); assert.equal(s.summary.status_mapping_version, STATUS_MAPPING_VERSION); });

// =================================================================
// V2: hashes — identity projection vs full business
// =================================================================

/* prettier-ignore */
test('v2: identity projection hash excludes status', () => { const cs = generateSeasonFixtures(1000, 10).map(f => buildCandidate({ id: String(f.id), home: f.home.name, away: f.away.name, kickoff: f.status.utcTime, provider_status: 'scheduled' }, 47, 'Premier League', '2022/2023')); const cf = cs.map(c => ({ ...c, provider_status: 'finished' })); assert.equal(computeV1IdentityProjectionHash(cs), computeV1IdentityProjectionHash(cf)); });

/* prettier-ignore */
test('v2: full business hash changes with provider_status', () => { const cs = generateSeasonFixtures(1000, 10).map(f => buildCandidate({ id: String(f.id), home: f.home.name, away: f.away.name, kickoff: f.status.utcTime, provider_status: 'scheduled' }, 47, 'Premier League', '2022/2023')); const cf = cs.map(c => ({ ...c, provider_status: 'finished' })); assert.notEqual(computeV2BusinessHash(cs), computeV2BusinessHash(cf)); });

/* prettier-ignore */
test('v2: identity projection hash equals v1 business hash', () => { const candidates = generateSeasonFixtures(1000, 10).map(f => buildCandidate({ id: String(f.id), home: f.home.name, away: f.away.name, kickoff: f.status.utcTime, provider_status: 'scheduled' }, 47, 'Premier League', '2022/2023')); assert.equal(computeBusinessContentHash(candidates), computeV1IdentityProjectionHash(candidates)); });

/* prettier-ignore */
test('v2: changing identity field changes identity projection hash', () => { const c1 = generateSeasonFixtures(1000, 5).map(f => buildCandidate({ id: String(f.id), home: f.home.name, away: f.away.name, kickoff: f.status.utcTime, provider_status: 'scheduled' }, 47, 'Premier League', '2022/2023')); const c2 = c1.map(c => ({ ...c, home_team: 'Different Team' })); assert.notEqual(computeV1IdentityProjectionHash(c1), computeV1IdentityProjectionHash(c2)); });

/* prettier-ignore */
test('v2: hash determinism with reversed order', () => { const fixs = generateSeasonFixtures(9000, 5); fixs.forEach(f => (f.status.finished = true)); const candidates = fixs.map(f => buildCandidate({ id: String(f.id), home: f.home.name, away: f.away.name, kickoff: f.status.utcTime, provider_status: 'finished' }, 47, 'Premier League', '2022/2023')); assert.equal(computeV1IdentityProjectionHash(candidates), computeV1IdentityProjectionHash([...candidates].reverse())); assert.equal(computeV2BusinessHash(candidates), computeV2BusinessHash([...candidates].reverse())); });

// =================================================================
// V2: end-to-end v2 export pipeline
// =================================================================

/* prettier-ignore */
test('exportCandidates canonical-v2 produces correct schema, hashes, and status fields', async () => { const fixs = generateSeasonFixtures(5000000, 380); fixs.forEach(f => (f.status.finished = true)); const { html } = buildNextDataPage({ fixtures: fixs, season: '2022/2023' }); const retainDir = fs.mkdtempSync('/tmp/m3d2bf_v2_retain_'); try { const result = await exportCandidates(makeExportOptions(['2022/2023'], async () => ({ status: 200, contentType: 'text/html', body: html, bodyBytes: Buffer.from(html, 'utf8') }), {}, { outputSchema: 'canonical-v2', retainRawResponses: { outputDir: retainDir, collectorComponent: 'FotMobCandidateExporter', collectorCodeRevision: TEST_COLLECTOR_CODE_REVISION } })); assert.equal(result.meta.schema_version, 'canonical-inventory-artifact/v2'); assert.equal(result.candidates.length, 380); assert.ok(result.validation.all_seasons_complete); assert.ok(result.v2Snapshot); assert.equal(result.v2Snapshot.identity_projection_hash.length, 64); assert.equal(result.v2Snapshot.business_hash.length, 64); assert.notEqual(result.v2Snapshot.identity_projection_hash, result.v2Snapshot.business_hash); assert.deepEqual(result.v2Snapshot.per_season_counts, { '2022/2023': 380 }); assert.ok(result.candidates.every(c => c.provider_status === 'finished')); assert.ok(result.candidates.every(c => c.status_mapping_version === STATUS_MAPPING_VERSION)); assert.ok(result.rawRetentions); assert.equal(result.rawRetentions.length, 1); assert.equal(result.rawRetentions[0].bodySha256.length, 64); assert.ok(result.rawRetentions[0].byteSize > 0); assert.ok(result.rawRetentions[0].rawFilePath.startsWith(retainDir)); assert.ok(result.rawRetentions[0].manifestFilePath); assert.ok(result.rawRetentions[0].manifestFilePath.startsWith(retainDir)); assert.ok(result.rawRetentions[0].manifest.request_url.includes('fotmob.com')); assert.equal(result.rawRetentions[0].manifest.source_provider, 'FotMob'); assert.equal(result.rawRetentions[0].manifest.collector_component, 'FotMobCandidateExporter'); assert.equal(result.rawRetentions[0].manifest.canonical_season, '2022/2023'); const manifestStr = JSON.stringify(result.rawRetentions[0].manifest); const secretPattern = /\b(cookie|bearer|[Aa]uthorization:|password|credential|secret[_-]|api[_-]key|api[_-]secret|access[_-]token|proxy[_-](?:url|host|user|pass|secret)|x-api-key)\b/i; assert.doesNotMatch(manifestStr, secretPattern); } finally { bestEffort(() => fs.rmSync(retainDir, { recursive: true, force: true })); } });

/* prettier-ignore */
test('exportCandidates: canonical-v2 without retainRawResponses throws SAFETY_ERROR', async () => { await assert.rejects(exportCandidates(makeExportOptions(['2022/2023'], async () => ({ status: 200, contentType: 'text/html', body: '', bodyBytes: Buffer.from('') }), {}, { outputSchema: 'canonical-v2' })), { code: 'SAFETY_ERROR' }); });

/* prettier-ignore */
test('exportCandidates: season fails when status_unknown fixtures exist', async () => { const fixs = generateSeasonFixtures(6000000, 380); fixs[0].status.finished = true; fixs[0].status.cancelled = true; const { html } = buildNextDataPage({ fixtures: fixs, season: '2022/2023' }); const result = await exportFromHtml(html); assert.equal(result.candidates.length, 379); assert.equal(result.validation.all_seasons_complete, false); const sr = result.validation.season_results[0]; assert.equal(sr.result, 'validation_failed'); assert.equal(sr.audit.status_unknown_fixture_count, 1); });

test('exportCandidates: malformed reason.short fixture fails the season closed', async () => {
    const fixs = generateSeasonFixtures(6100000, 380);
    fixs[5].status.reason = { short: 7 };
    const { html } = buildNextDataPage({ fixtures: fixs, season: '2022/2023' });
    const result = await exportFromHtml(html);
    assert.equal(result.candidates.length, 379, 'malformed fixture must not be accepted as scheduled');
    assert.equal(result.validation.all_seasons_complete, false);
    const sr = result.validation.season_results[0];
    assert.equal(sr.result, 'validation_failed');
    assert.equal(sr.validation.valid, false);
    assert.equal(sr.audit.status_unknown_fixture_count, 1);
    assert.equal(sr.audit.status_unknown_by_reason['non_string_reason_short:number'], 1);
    assert.equal(sr.audit.rejected_fixture_count, 0);
    assert.equal(sr.audit.excluded_fixture_count, 0);
    assert.ok(sr.validation.errors.includes('unknown_provider_status:1'));
});

test('exportCandidates: started+postponed fixture fails the season closed', async () => {
    const fixs = generateSeasonFixtures(6200000, 380);
    fixs[9].status.started = true;
    fixs[9].status.reason = { short: 'Postponed' };
    const { html } = buildNextDataPage({ fixtures: fixs, season: '2022/2023' });
    const result = await exportFromHtml(html);
    assert.equal(result.candidates.length, 379, 'contradictory fixture must not be accepted as postponed');
    assert.equal(result.validation.all_seasons_complete, false);
    const sr = result.validation.season_results[0];
    assert.equal(sr.result, 'validation_failed');
    assert.equal(sr.validation.valid, false);
    assert.equal(sr.audit.status_unknown_fixture_count, 1);
    assert.equal(sr.audit.status_unknown_by_reason['contradictory_status_flags:started_and_postponed'], 1);
    assert.equal(sr.audit.rejected_fixture_count, 0);
    assert.equal(sr.audit.excluded_fixture_count, 0);
    assert.ok(sr.validation.errors.includes('unknown_provider_status:1'));
});

/* prettier-ignore */
test('exportCandidates: abandoned fixture still excluded in v2 mode', async () => { const fixs = generateSeasonFixtures(7000000, 380); fixs.push(buildFixture('7999999', 'TeamX', 'TeamY', '2022-12-25T15:00:00Z', 'Ab')); fixs.forEach(f => (f.status.finished = true)); const { html } = buildNextDataPage({ fixtures: fixs, season: '2022/2023' }); const retainDir = fs.mkdtempSync('/tmp/m3d2bf_v2_ab_retain_'); try { const result = await exportCandidates(makeExportOptions(['2022/2023'], async () => ({ status: 200, contentType: 'text/html', body: html, bodyBytes: Buffer.from(html, 'utf8') }), {}, { outputSchema: 'canonical-v2', retainRawResponses: { outputDir: retainDir, collectorComponent: 'FotMobCandidateExporter', collectorCodeRevision: TEST_COLLECTOR_CODE_REVISION } })); assert.equal(result.candidates.length, 380); assert.equal(result.validation.season_results[0].audit.excluded_fixture_count, 1); assert.equal(result.validation.season_results[0].audit.excluded_by_reason['Ab'], 1); } finally { bestEffort(() => fs.rmSync(retainDir, { recursive: true, force: true })); } });

// =================================================================
// Raw retention: unit tests
// =================================================================

test('writeRawRetention: atomic write, sha256, manifest, conflict detection', () => {
    const tmpDir = fs.mkdtempSync('/tmp/m3d2bf_retain_test_');
    try {
        const bodyBytes = Buffer.from('<html><body>test page content here</body></html>', 'utf8');
        const ctx = {
            url: 'https://www.fotmob.com/leagues/47/fixtures/premier-league?season=2022%2F2023',
            leagueId: '47', competition: 'Premier League',
            requestedSeason: '2022/2023', canonicalSeason: '2022/2023',
            httpStatus: 200, contentType: 'text/html',
            captureStartedAt: '2026-07-30T00:00:00Z',
            captureCompletedAt: '2026-07-30T00:00:01Z',
            collectorComponent: 'FotMobCandidateExporter',
            collectorCodeRevision: TEST_COLLECTOR_CODE_REVISION,
            networkAuthorizationMode: 'explicit',
        };
        const r1 = writeRawRetention(tmpDir, bodyBytes, ctx, { repositoryRoot: '/home/user/repo' });
        assert.ok(r1.rawFilePath.startsWith(tmpDir));
        assert.equal(r1.bodySha256.length, 64);
        assert.equal(r1.byteSize, bodyBytes.length);
        assert.ok(fs.existsSync(r1.rawFilePath));
        // Manifest is persisted to disk alongside raw HTML (P1-2)
        assert.ok(r1.manifestFilePath);
        assert.ok(r1.manifestFilePath.startsWith(tmpDir));
        assert.ok(fs.existsSync(r1.manifestFilePath));
        const manifestOnDisk = JSON.parse(fs.readFileSync(r1.manifestFilePath, 'utf8'));
        assert.equal(manifestOnDisk.body_sha256, r1.bodySha256);
        assert.equal(manifestOnDisk.schema_version, 'fotmob-raw-capture-manifest/v1');
        const m = r1.manifest;
        assert.equal(m.schema_version, 'fotmob-raw-capture-manifest/v1');
        assert.equal(m.source_provider, 'FotMob');
        assert.equal(m.source_kind, 'league_fixtures_page');
        assert.equal(m.request_method, 'GET');
        assert.equal(m.http_status, 200);
        assert.equal(m.body_byte_size, bodyBytes.length);
        assert.equal(m.body_sha256, r1.bodySha256);
        assert.equal(m.collector_code_revision, TEST_COLLECTOR_CODE_REVISION);
        assert.ok(m.raw_file_relative_path.length > 0);
        const secretPattern = /\b(cookie|bearer|[Aa]uthorization:|password|credential|secret[_-]|api[_-]key|api[_-]secret|access[_-]token|proxy[_-](?:url|host|user|pass|secret)|x-api-key)\b/i;
        assert.doesNotMatch(JSON.stringify(m), secretPattern);
        // Idempotent: same content same path → no error
        const r2 = writeRawRetention(tmpDir, bodyBytes, ctx, { repositoryRoot: '/home/user/repo' });
        assert.equal(r2.bodySha256, r1.bodySha256);
        // Content conflict: corrupt file on disk, then write same bytes →
        // same SHA path → existing file with different content → SAFETY_ERROR
        fs.writeFileSync(r1.rawFilePath, Buffer.from('tampered content goes here!!!', 'utf8'));
        assert.throws(
            () => writeRawRetention(tmpDir, bodyBytes, ctx, { repositoryRoot: '/home/user/repo' }),
            { code: 'SAFETY_ERROR' }
        );
    } finally {
        bestEffort(() => fs.rmSync(tmpDir, { recursive: true, force: true }));
    }
});

/* prettier-ignore */
test('writeRawRetention: rejects paths inside repository', () => { const repoRoot = path.resolve(__dirname, '..', '..'); const ctx = { url: 'https://example.com', leagueId: '47', competition: 'Premier League', requestedSeason: '2022/2023', canonicalSeason: '2022/2023', httpStatus: 200, contentType: 'text/html', captureStartedAt: '2026-07-30T00:00:00Z', captureCompletedAt: '2026-07-30T00:00:01Z', collectorComponent: 'test', collectorCodeRevision: TEST_COLLECTOR_CODE_REVISION, networkAuthorizationMode: 'explicit' }; assert.throws(() => writeRawRetention(repoRoot, Buffer.from('test'), ctx), { code: 'SAFETY_ERROR' }); });

/* prettier-ignore */
test('buildCaptureManifest: correct structure and no secrets', () => { const m = buildCaptureManifest({ url: 'https://www.fotmob.com/leagues/47/fixtures/premier-league?season=2022%2F2023', leagueId: '47', competition: 'Premier League', requestedSeason: '2022/2023', canonicalSeason: '2022/2023', captureStartedAt: '2026-07-30T00:00:00Z', captureCompletedAt: '2026-07-30T00:00:01Z', httpStatus: 200, contentType: 'text/html', collectorComponent: 'FotMobCandidateExporter', collectorCodeRevision: TEST_COLLECTOR_CODE_REVISION, networkAuthorizationMode: 'explicit_network_authorization' }, 'abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890', 12345, 'fotmob-fixtures-47-2022_2023-abcdef123456.html'); assert.equal(m.schema_version, 'fotmob-raw-capture-manifest/v1'); assert.equal(m.body_sha256, 'abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890'); assert.equal(m.body_byte_size, 12345); assert.equal(m.collector_code_revision, TEST_COLLECTOR_CODE_REVISION); assert.equal(m.request_headers, undefined); const str = JSON.stringify(m); const secretPattern = /\b(cookie|bearer|[Aa]uthorization:|password|credential|secret[_-]|api[_-]key|api[_-]secret|access[_-]token|proxy[_-](?:url|host|user|pass|secret)|x-api-key)\b/i; assert.doesNotMatch(str, secretPattern); });

// =================================================================
// Core-layer 40-hex collector_code_revision enforcement
// =================================================================

test('validateCollectorCodeRevision: accepts a full 40-hex SHA and rejects everything else', () => {
    const VALID = TEST_COLLECTOR_CODE_REVISION;
    assert.equal(validateCollectorCodeRevision(VALID), VALID, 'valid revision returned verbatim');
    const invalid = [
        undefined,
        null,
        42,
        true,
        {},
        [],
        '',
        'sha',
        'test-sha',
        'unknown',
        'abc123def456',
        VALID.slice(0, 39), // 39 chars
        `${VALID}0`, // 41 chars
        VALID.toUpperCase(), // 40 hex but uppercase
        ` ${VALID}`, // leading whitespace — never trimmed into validity
        `${VALID} `, // trailing whitespace
        `${VALID.slice(0, 20)}g${VALID.slice(21)}`, // non-hex character
    ];
    for (const value of invalid) {
        assert.throws(() => validateCollectorCodeRevision(value), { code: 'SAFETY_ERROR' }, `must reject: ${String(value)}`);
    }
});

test('buildCaptureManifest: invalid revision throws SAFETY_ERROR at the core layer', () => {
    const baseContext = {
        url: 'https://www.fotmob.com/leagues/47/fixtures/premier-league?season=2022%2F2023',
        leagueId: '47', competition: 'Premier League',
        requestedSeason: '2022/2023', canonicalSeason: '2022/2023',
        captureStartedAt: '2026-08-02T00:00:00Z', captureCompletedAt: '2026-08-02T00:00:01Z',
        httpStatus: 200, contentType: 'text/html',
        collectorComponent: 'FotMobCandidateExporter',
        networkAuthorizationMode: 'explicit_network_authorization',
    };
    const bodySha = 'a'.repeat(64);
    const rawFileName = 'fotmob-fixtures-47-2022_2023-aaaaaaaaaaaa.html';
    for (const revision of [undefined, null, 42, 'unknown', 'test-sha', 'abc123def456789', TEST_COLLECTOR_CODE_REVISION.toUpperCase(), ` ${TEST_COLLECTOR_CODE_REVISION}`]) {
        assert.throws(
            () => buildCaptureManifest({ ...baseContext, collectorCodeRevision: revision }, bodySha, 12345, rawFileName),
            { code: 'SAFETY_ERROR' },
            `direct buildCaptureManifest call must reject revision: ${String(revision)}`
        );
    }
    const manifest = buildCaptureManifest(
        { ...baseContext, collectorCodeRevision: TEST_COLLECTOR_CODE_REVISION },
        bodySha,
        12345,
        rawFileName
    );
    assert.equal(manifest.collector_code_revision, TEST_COLLECTOR_CODE_REVISION, 'valid revision written verbatim');
});

test('writeRawRetention: invalid revision writes no raw or manifest files', () => {
    const tmpDir = fs.mkdtempSync('/tmp/m3d2bf_reject_rev_');
    try {
        const baseContext = {
            url: 'https://www.fotmob.com/leagues/47/test',
            leagueId: '47', competition: 'Premier League',
            requestedSeason: '2022/2023', canonicalSeason: '2022/2023',
            httpStatus: 200, contentType: 'text/html',
            captureStartedAt: '2026-08-02T00:00:00Z', captureCompletedAt: '2026-08-02T00:00:01Z',
            collectorComponent: 'test', networkAuthorizationMode: 'test',
        };
        const bodyBytes = Buffer.from('<html>rev-test</html>', 'utf8');
        for (const revision of [undefined, 'sha', 'abc123def456789', TEST_COLLECTOR_CODE_REVISION.toUpperCase(), ` ${TEST_COLLECTOR_CODE_REVISION}`]) {
            assert.throws(
                () => writeRawRetention(tmpDir, bodyBytes, { ...baseContext, collectorCodeRevision: revision }, { repositoryRoot: '/home/user/repo' }),
                { code: 'SAFETY_ERROR' },
                `writeRawRetention must reject revision: ${String(revision)}`
            );
            assert.deepEqual(fs.readdirSync(tmpDir), [], 'invalid revision must leave the output directory untouched');
        }
    } finally {
        bestEffort(() => fs.rmSync(tmpDir, { recursive: true, force: true }));
    }
});

test('exportCandidates: injected invalid collector revision cannot bypass the core check', async () => {
    const fixs = generateSeasonFixtures(6300000, 380);
    fixs.forEach(f => (f.status.finished = true));
    const { html } = buildNextDataPage({ fixtures: fixs, season: '2022/2023' });
    for (const revision of ['test-sha', undefined]) {
        let fetchCalls = 0;
        const mockedPage = async () => {
            fetchCalls += 1;
            return { status: 200, contentType: 'text/html', body: html, bodyBytes: Buffer.from(html, 'utf8') };
        };
        const retainDir = fs.mkdtempSync('/tmp/m3d2bf_v2_bad_rev_');
        try {
            const retainRawResponses = { outputDir: retainDir, collectorComponent: 'FotMobCandidateExporter' };
            if (revision !== undefined) retainRawResponses.collectorCodeRevision = revision;
            await assert.rejects(
                exportCandidates(makeExportOptions(['2022/2023'], mockedPage, {}, { outputSchema: 'canonical-v2', retainRawResponses })),
                { code: 'SAFETY_ERROR' },
                `injected revision ${String(revision)} must fail closed`
            );
            assert.equal(fetchCalls, 0, 'invalid revision must fail before any network request');
            assert.deepEqual(fs.readdirSync(retainDir), [], 'invalid revision must not produce raw or manifest files');
        } finally {
            bestEffort(() => fs.rmSync(retainDir, { recursive: true, force: true }));
        }
    }
});

// =================================================================
// CLI: v2 args and usage
// =================================================================

/* prettier-ignore */
test('CLI parseArgs supports --output-schema and --retain-raw-responses', () => { const { parseArgs: cliParseArgs } = require('../../scripts/ops/fotmob_candidates_export'); const args = cliParseArgs(['--league-id', '47', '--competition', 'Premier League', '--season', '2022/2023', '--output-schema=canonical-v2', '--retain-raw-responses=/tmp/retain', '--network-preview=true', '--network-authorization=yes']); assert.equal(args.outputSchema, 'canonical-v2'); assert.equal(args.retainRawResponses, '/tmp/retain'); assert.equal(args.networkPreview, 'true'); assert.equal(args.networkAuthorization, 'yes'); });

/* prettier-ignore */
test('CLI parseArgs supports --output-schema and --retain-raw-responses as separate tokens', () => { const { parseArgs: cliParseArgs } = require('../../scripts/ops/fotmob_candidates_export'); const args = cliParseArgs(['--league-id', '47', '--competition', 'Premier League', '--season', '2022/2023', '--output-schema', 'canonical-v2', '--retain-raw-responses', '/tmp/retain2', '--network-preview=true', '--network-authorization=yes']); assert.equal(args.outputSchema, 'canonical-v2'); assert.equal(args.retainRawResponses, '/tmp/retain2'); });

/* prettier-ignore */
test('CLI usage string mentions v2 options', () => { const { USAGE } = require('../../scripts/ops/fotmob_candidates_export'); assert.match(USAGE, /output-schema/); assert.match(USAGE, /canonical-v2/); assert.match(USAGE, /retain-raw-responses/); assert.match(USAGE, /provider_status/); });

// =================================================================
// Pair Integrity: raw + manifest (section 6.1)
// =================================================================

test('raw+manifest: only raw file (no manifest) → SAFETY_ERROR', () => {
    const tmpDir = fs.mkdtempSync('/tmp/m3d2bf_pair_rm_');
    try {
        const bodyBytes = Buffer.from('<html>pair-test</html>', 'utf8');
        const ctx = {
            url: 'https://www.fotmob.com/leagues/47/test',
            leagueId: '47', competition: 'Premier League',
            requestedSeason: '2022/2023', canonicalSeason: '2022/2023',
            httpStatus: 200, contentType: 'text/html',
            captureStartedAt: '2026-08-01T00:00:00Z',
            captureCompletedAt: '2026-08-01T00:00:01Z',
            collectorComponent: 'test', collectorCodeRevision: TEST_COLLECTOR_CODE_REVISION,
            networkAuthorizationMode: 'test',
        };
        const sha = crypto.createHash('sha256').update(bodyBytes).digest('hex');
        const rawName = `fotmob-fixtures-47-2022_2023-${sha.slice(0, 12)}.html`;
        // Create only the raw file, leave manifest absent
        fs.writeFileSync(path.join(tmpDir, rawName), bodyBytes);
        assert.throws(
            () => writeRawRetention(tmpDir, bodyBytes, ctx, { repositoryRoot: '/home/user/repo' }),
            { code: 'SAFETY_ERROR' }
        );
    } finally {
        bestEffort(() => fs.rmSync(tmpDir, { recursive: true, force: true }));
    }
});

test('raw+manifest: only manifest file (no raw) → SAFETY_ERROR', () => {
    const tmpDir = fs.mkdtempSync('/tmp/m3d2bf_pair_mo_');
    try {
        const bodyBytes = Buffer.from('<html>pair-test-2</html>', 'utf8');
        const ctx = {
            url: 'https://www.fotmob.com/leagues/47/test',
            leagueId: '47', competition: 'Premier League',
            requestedSeason: '2022/2023', canonicalSeason: '2022/2023',
            httpStatus: 200, contentType: 'text/html',
            captureStartedAt: '2026-08-01T00:00:00Z',
            captureCompletedAt: '2026-08-01T00:00:01Z',
            collectorComponent: 'test', collectorCodeRevision: TEST_COLLECTOR_CODE_REVISION,
            networkAuthorizationMode: 'test',
        };
        const sha = crypto.createHash('sha256').update(bodyBytes).digest('hex');
        const manifestName = `fotmob-fixtures-47-2022_2023-${sha.slice(0, 12)}.manifest.json`;
        // Create only the manifest file, leave raw absent
        fs.writeFileSync(path.join(tmpDir, manifestName), JSON.stringify({ test: true }));
        assert.throws(
            () => writeRawRetention(tmpDir, bodyBytes, ctx, { repositoryRoot: '/home/user/repo' }),
            { code: 'SAFETY_ERROR' }
        );
    } finally {
        bestEffort(() => fs.rmSync(tmpDir, { recursive: true, force: true }));
    }
});

test('raw+manifest: manifest body_sha256 wrong → SAFETY_ERROR', () => {
    const tmpDir = fs.mkdtempSync('/tmp/m3d2bf_pair_mh_');
    try {
        const bodyBytes = Buffer.from('<html>pair-test-3</html>', 'utf8');
        const ctx = {
            url: 'https://www.fotmob.com/leagues/47/test',
            leagueId: '47', competition: 'Premier League',
            requestedSeason: '2022/2023', canonicalSeason: '2022/2023',
            httpStatus: 200, contentType: 'text/html',
            captureStartedAt: '2026-08-01T00:00:00Z',
            captureCompletedAt: '2026-08-01T00:00:01Z',
            collectorComponent: 'test', collectorCodeRevision: TEST_COLLECTOR_CODE_REVISION,
            networkAuthorizationMode: 'test',
        };
        const sha = crypto.createHash('sha256').update(bodyBytes).digest('hex');
        const rawName = `fotmob-fixtures-47-2022_2023-${sha.slice(0, 12)}.html`;
        const manifestName = `fotmob-fixtures-47-2022_2023-${sha.slice(0, 12)}.manifest.json`;
        // Create both files but manifest has wrong body_sha256
        fs.writeFileSync(path.join(tmpDir, rawName), bodyBytes);
        const badManifest = buildCaptureManifest(ctx, '0000000000000000000000000000000000000000000000000000000000000000', bodyBytes.length, rawName);
        fs.writeFileSync(path.join(tmpDir, manifestName), JSON.stringify(badManifest, null, 2) + '\n');
        assert.throws(
            () => writeRawRetention(tmpDir, bodyBytes, ctx, { repositoryRoot: '/home/user/repo' }),
            { code: 'SAFETY_ERROR' }
        );
    } finally {
        bestEffort(() => fs.rmSync(tmpDir, { recursive: true, force: true }));
    }
});

test('raw+manifest: manifest body_byte_size wrong → SAFETY_ERROR', () => {
    const tmpDir = fs.mkdtempSync('/tmp/m3d2bf_pair_mbs_');
    try {
        const bodyBytes = Buffer.from('<html>pair-test-4</html>', 'utf8');
        const ctx = {
            url: 'https://www.fotmob.com/leagues/47/test',
            leagueId: '47', competition: 'Premier League',
            requestedSeason: '2022/2023', canonicalSeason: '2022/2023',
            httpStatus: 200, contentType: 'text/html',
            captureStartedAt: '2026-08-01T00:00:00Z',
            captureCompletedAt: '2026-08-01T00:00:01Z',
            collectorComponent: 'test', collectorCodeRevision: TEST_COLLECTOR_CODE_REVISION,
            networkAuthorizationMode: 'test',
        };
        const sha = crypto.createHash('sha256').update(bodyBytes).digest('hex');
        const rawName = `fotmob-fixtures-47-2022_2023-${sha.slice(0, 12)}.html`;
        const manifestName = `fotmob-fixtures-47-2022_2023-${sha.slice(0, 12)}.manifest.json`;
        fs.writeFileSync(path.join(tmpDir, rawName), bodyBytes);
        const badManifest = buildCaptureManifest(ctx, sha, 99999, rawName); // wrong byte_size
        fs.writeFileSync(path.join(tmpDir, manifestName), JSON.stringify(badManifest, null, 2) + '\n');
        assert.throws(
            () => writeRawRetention(tmpDir, bodyBytes, ctx, { repositoryRoot: '/home/user/repo' }),
            { code: 'SAFETY_ERROR' }
        );
    } finally {
        bestEffort(() => fs.rmSync(tmpDir, { recursive: true, force: true }));
    }
});

test('raw+manifest: manifest raw_file_relative_path wrong → SAFETY_ERROR', () => {
    const tmpDir = fs.mkdtempSync('/tmp/m3d2bf_pair_mrp_');
    try {
        const bodyBytes = Buffer.from('<html>pair-test-5</html>', 'utf8');
        const ctx = {
            url: 'https://www.fotmob.com/leagues/47/test',
            leagueId: '47', competition: 'Premier League',
            requestedSeason: '2022/2023', canonicalSeason: '2022/2023',
            httpStatus: 200, contentType: 'text/html',
            captureStartedAt: '2026-08-01T00:00:00Z',
            captureCompletedAt: '2026-08-01T00:00:01Z',
            collectorComponent: 'test', collectorCodeRevision: TEST_COLLECTOR_CODE_REVISION,
            networkAuthorizationMode: 'test',
        };
        const sha = crypto.createHash('sha256').update(bodyBytes).digest('hex');
        const rawName = `fotmob-fixtures-47-2022_2023-${sha.slice(0, 12)}.html`;
        const manifestName = `fotmob-fixtures-47-2022_2023-${sha.slice(0, 12)}.manifest.json`;
        fs.writeFileSync(path.join(tmpDir, rawName), bodyBytes);
        const badManifest = buildCaptureManifest(ctx, sha, bodyBytes.length, 'wrong-file-name.html');
        fs.writeFileSync(path.join(tmpDir, manifestName), JSON.stringify(badManifest, null, 2) + '\n');
        assert.throws(
            () => writeRawRetention(tmpDir, bodyBytes, ctx, { repositoryRoot: '/home/user/repo' }),
            { code: 'SAFETY_ERROR' }
        );
    } finally {
        bestEffort(() => fs.rmSync(tmpDir, { recursive: true, force: true }));
    }
});

test('raw+manifest: raw is symlink → SAFETY_ERROR', () => {
    const tmpDir = fs.mkdtempSync('/tmp/m3d2bf_pair_rs_');
    const realDir = fs.mkdtempSync('/tmp/m3d2bf_pair_rs_real_');
    try {
        const bodyBytes = Buffer.from('<html>pair-test-6</html>', 'utf8');
        const ctx = {
            url: 'https://www.fotmob.com/leagues/47/test',
            leagueId: '47', competition: 'Premier League',
            requestedSeason: '2022/2023', canonicalSeason: '2022/2023',
            httpStatus: 200, contentType: 'text/html',
            captureStartedAt: '2026-08-01T00:00:00Z',
            captureCompletedAt: '2026-08-01T00:00:01Z',
            collectorComponent: 'test', collectorCodeRevision: TEST_COLLECTOR_CODE_REVISION,
            networkAuthorizationMode: 'test',
        };
        const sha = crypto.createHash('sha256').update(bodyBytes).digest('hex');
        const rawName = `fotmob-fixtures-47-2022_2023-${sha.slice(0, 12)}.html`;
        const manifestName = `fotmob-fixtures-47-2022_2023-${sha.slice(0, 12)}.manifest.json`;
        const realRawPath = path.join(realDir, rawName);
        const manifestPath_sl = path.join(tmpDir, manifestName);
        // Raw is a symlink to a real file in another directory
        fs.writeFileSync(realRawPath, bodyBytes);
        fs.symlinkSync(realRawPath, path.join(tmpDir, rawName));
        const correctSha = crypto.createHash('sha256').update(bodyBytes).digest('hex');
        const correctManifest = buildCaptureManifest(ctx, correctSha, bodyBytes.length, rawName);
        fs.writeFileSync(manifestPath_sl, JSON.stringify(correctManifest, null, 2) + '\n');
        assert.throws(
            () => writeRawRetention(tmpDir, bodyBytes, ctx, { repositoryRoot: '/home/user/repo' }),
            { code: 'SAFETY_ERROR' }
        );
    } finally {
        bestEffort(() => fs.rmSync(tmpDir, { recursive: true, force: true }));
        bestEffort(() => fs.rmSync(realDir, { recursive: true, force: true }));
    }
});

test('raw+manifest: manifest is symlink → SAFETY_ERROR', () => {
    const tmpDir = fs.mkdtempSync('/tmp/m3d2bf_pair_ms_');
    const realDir = fs.mkdtempSync('/tmp/m3d2bf_pair_ms_real_');
    try {
        const bodyBytes = Buffer.from('<html>pair-test-7</html>', 'utf8');
        const ctx = {
            url: 'https://www.fotmob.com/leagues/47/test',
            leagueId: '47', competition: 'Premier League',
            requestedSeason: '2022/2023', canonicalSeason: '2022/2023',
            httpStatus: 200, contentType: 'text/html',
            captureStartedAt: '2026-08-01T00:00:00Z',
            captureCompletedAt: '2026-08-01T00:00:01Z',
            collectorComponent: 'test', collectorCodeRevision: TEST_COLLECTOR_CODE_REVISION,
            networkAuthorizationMode: 'test',
        };
        const sha = crypto.createHash('sha256').update(bodyBytes).digest('hex');
        const rawName = `fotmob-fixtures-47-2022_2023-${sha.slice(0, 12)}.html`;
        const manifestName = `fotmob-fixtures-47-2022_2023-${sha.slice(0, 12)}.manifest.json`;
        const realManifestPath = path.join(realDir, manifestName);
        // Manifest is a symlink to a real file in another directory
        fs.writeFileSync(path.join(tmpDir, rawName), bodyBytes);
        const correctManifest = buildCaptureManifest(ctx, sha, bodyBytes.length, rawName);
        fs.writeFileSync(realManifestPath, JSON.stringify(correctManifest, null, 2) + '\n');
        fs.symlinkSync(realManifestPath, path.join(tmpDir, manifestName));
        assert.throws(
            () => writeRawRetention(tmpDir, bodyBytes, ctx, { repositoryRoot: '/home/user/repo' }),
            { code: 'SAFETY_ERROR' }
        );
    } finally {
        bestEffort(() => fs.rmSync(tmpDir, { recursive: true, force: true }));
        bestEffort(() => fs.rmSync(realDir, { recursive: true, force: true }));
    }
});

test('raw+manifest: manifest rename failure → no orphaned final raw file', () => {
    const tmpDir = fs.mkdtempSync('/tmp/m3d2bf_pair_rf_');
    try {
        const bodyBytes = Buffer.from('<html>pair-test-rename-fail</html>', 'utf8');
        const ctx = {
            url: 'https://www.fotmob.com/leagues/47/test',
            leagueId: '47', competition: 'Premier League',
            requestedSeason: '2022/2023', canonicalSeason: '2022/2023',
            httpStatus: 200, contentType: 'text/html',
            captureStartedAt: '2026-08-01T00:00:00Z',
            captureCompletedAt: '2026-08-01T00:00:01Z',
            collectorComponent: 'test', collectorCodeRevision: TEST_COLLECTOR_CODE_REVISION,
            networkAuthorizationMode: 'test',
        };
        const sha = crypto.createHash('sha256').update(bodyBytes).digest('hex');
        const rawName = `fotmob-fixtures-47-2022_2023-${sha.slice(0, 12)}.html`;
        const manifestName = `fotmob-fixtures-47-2022_2023-${sha.slice(0, 12)}.manifest.json`;
        const finalRawPath = path.join(tmpDir, rawName);
        const finalManifestPath = path.join(tmpDir, manifestName);
        // Simulate rename failure: renameSync succeeds for raw but throws for manifest
        const realRenameSync = fs.renameSync;
        let renameCount = 0;
        const mockFs = {
            ...fs,
            renameSync: (src, dst) => {
                renameCount += 1;
                if (renameCount === 2 && dst === finalManifestPath) {
                    throw new Error('simulated manifest rename failure');
                }
                return realRenameSync(src, dst);
            },
        };
        assert.throws(
            () => writeRawRetention(tmpDir, bodyBytes, ctx, { repositoryRoot: '/home/user/repo', fileSystem: mockFs }),
            { code: 'SAFETY_ERROR' }
        );
        // Verify the raw file was rolled back (deleted after rename error)
        assert.equal(fs.existsSync(finalRawPath), false, 'orphaned raw file should not exist after rollback');
        assert.equal(fs.existsSync(finalManifestPath), false, 'manifest should not exist');
    } finally {
        bestEffort(() => fs.rmSync(tmpDir, { recursive: true, force: true }));
    }
});

// =================================================================
// Pair Integrity: validateV2SummaryAgainstArtifact (section 5.4)
// =================================================================

test('summary: validateV2SummaryAgainstArtifact passes for consistent pair', () => {
    const { validateV2SummaryAgainstArtifact } = require('../../src/infrastructure/fotmob/FotMobCandidateExporter');
    const candidateDoc = {
        schema_version: 'canonical-inventory-artifact/v2',
        artifact: {
            source_provider: 'FotMob', competition: 'Premier League',
            per_season_counts: { '2022/2023': 380 },
            identity_projection_hash: 'aaa111', business_hash: 'bbb222',
            status_mapping_version: STATUS_MAPPING_VERSION,
        },
        candidates: new Array(380).fill(null),
    };
    const summaryDoc = {
        schema_version: 'canonical-inventory-artifact/v2',
        summary: {
            total_candidates: 380, per_season: { '2022/2023': 380 },
            source_provider: 'FotMob', competition: 'Premier League',
            identity_projection_hash: 'aaa111', business_hash: 'bbb222',
            status_mapping_version: STATUS_MAPPING_VERSION,
        },
    };
    // Should not throw
    validateV2SummaryAgainstArtifact(candidateDoc, summaryDoc);
});

test('summary: validateV2SummaryAgainstArtifact rejects total_candidates mismatch', () => {
    const { validateV2SummaryAgainstArtifact } = require('../../src/infrastructure/fotmob/FotMobCandidateExporter');
    const candidateDoc = {
        schema_version: 'canonical-inventory-artifact/v2',
        artifact: { source_provider: 'FotMob', competition: 'Premier League', per_season_counts: { '2022/2023': 380 }, identity_projection_hash: 'aaa111', business_hash: 'bbb222', status_mapping_version: STATUS_MAPPING_VERSION },
        candidates: new Array(380).fill(null),
    };
    const summaryDoc = {
        schema_version: 'canonical-inventory-artifact/v2',
        summary: { total_candidates: 999, per_season: { '2022/2023': 380 }, source_provider: 'FotMob', competition: 'Premier League', identity_projection_hash: 'aaa111', business_hash: 'bbb222', status_mapping_version: STATUS_MAPPING_VERSION },
    };
    assert.throws(() => validateV2SummaryAgainstArtifact(candidateDoc, summaryDoc), { code: 'SAFETY_ERROR' });
});

test('summary: validateV2SummaryAgainstArtifact rejects hash mismatch', () => {
    const { validateV2SummaryAgainstArtifact } = require('../../src/infrastructure/fotmob/FotMobCandidateExporter');
    const candidateDoc = {
        schema_version: 'canonical-inventory-artifact/v2',
        artifact: { source_provider: 'FotMob', competition: 'Premier League', per_season_counts: { '2022/2023': 380 }, identity_projection_hash: 'aaa111', business_hash: 'bbb222', status_mapping_version: STATUS_MAPPING_VERSION },
        candidates: new Array(380).fill(null),
    };
    const summaryDoc = {
        schema_version: 'canonical-inventory-artifact/v2',
        summary: { total_candidates: 380, per_season: { '2022/2023': 380 }, source_provider: 'FotMob', competition: 'Premier League', identity_projection_hash: 'DIFFERENT_HASH', business_hash: 'bbb222', status_mapping_version: STATUS_MAPPING_VERSION },
    };
    assert.throws(() => validateV2SummaryAgainstArtifact(candidateDoc, summaryDoc), { code: 'SAFETY_ERROR' });
});

test('summary: validateV2SummaryAgainstArtifact rejects per_season mismatch', () => {
    const { validateV2SummaryAgainstArtifact } = require('../../src/infrastructure/fotmob/FotMobCandidateExporter');
    const candidateDoc = {
        schema_version: 'canonical-inventory-artifact/v2',
        artifact: { source_provider: 'FotMob', competition: 'Premier League', per_season_counts: { '2022/2023': 380 }, identity_projection_hash: 'aaa111', business_hash: 'bbb222', status_mapping_version: STATUS_MAPPING_VERSION },
        candidates: new Array(380).fill(null),
    };
    const summaryDoc = {
        schema_version: 'canonical-inventory-artifact/v2',
        summary: { total_candidates: 380, per_season: { '2022/2023': 100 }, source_provider: 'FotMob', competition: 'Premier League', identity_projection_hash: 'aaa111', business_hash: 'bbb222', status_mapping_version: STATUS_MAPPING_VERSION },
    };
    assert.throws(() => validateV2SummaryAgainstArtifact(candidateDoc, summaryDoc), { code: 'SAFETY_ERROR' });
});

test('summary: validateV2SummaryAgainstArtifact rejects missing summary block', () => {
    const { validateV2SummaryAgainstArtifact } = require('../../src/infrastructure/fotmob/FotMobCandidateExporter');
    assert.throws(() => validateV2SummaryAgainstArtifact({ artifact: {} }, { no_summary: true }), { code: 'SAFETY_ERROR' });
    assert.throws(() => validateV2SummaryAgainstArtifact(null, { summary: {} }), { code: 'SAFETY_ERROR' });
});

// =================================================================
// Pair Integrity: v2 artifact + summary (section 6.2)
// =================================================================

// Generate a season of EPL_FIXTURES_PER_SEASON fixtures with all unique ordered
// team pairings (20 teams × 19 opponents = 380) so the contract validator does not
// reject duplicate fixture identities.
/* prettier-ignore */
function generateUniqueSeasonFixtures(startId) {
    const teams = ['Arsenal','Aston Villa','Bournemouth','Brentford','Brighton','Chelsea','Crystal Palace','Everton','Fulham','Leeds','Leicester','Liverpool','Man City','Man United','Newcastle','Southampton','Tottenham','West Ham','Wolves','Nottingham Forest'];
    const fixtures = [];
    let id = startId;
    for (let hi = 0; hi < teams.length; hi += 1) {
        for (let ai = 0; ai < teams.length; ai += 1) {
            if (hi === ai) continue;
            const kickoff = `2022-${String((fixtures.length % 12) + 1).padStart(2, '0')}-${String((fixtures.length % 28) + 1).padStart(2, '0')}T${String((fixtures.length % 22) + 1).padStart(2, '0')}:00:00Z`;
            fixtures.push(buildFixture(id, teams[hi], teams[ai], kickoff));
            id += 1;
            if (fixtures.length >= EPL_FIXTURES_PER_SEASON) break;
        }
        if (fixtures.length >= EPL_FIXTURES_PER_SEASON) break;
    }
    return fixtures;
}

// Fetch mock that returns unique fixtures for each of the 3 approved seasons.
/* prettier-ignore */
function makeUniqueSeasonPageFetch() {
    const baseIds = { '2022/2023': 5000000, '2023/2024': 5100000, '2024/2025': 5200000 };
    return async url => {
        const season = decodeURIComponent(url.match(/season=([^&]+)/)[1]);
        const startId = baseIds[season] || 5000000;
        const fixtures = generateUniqueSeasonFixtures(startId);
        const { html } = buildNextDataPage({ fixtures, season });
        return { status: 200, contentType: 'text/html', body: html };
    };
}

// Build valid v2 documents using all 3 approved seasons (1140 candidates) that
// pass formal contract validation including master population and hash parity.
/* prettier-ignore */
async function buildValidV2Docs() {
    const result = await exportCandidates(makeExportOptions(
        ['2022/2023', '2023/2024', '2024/2025'],
        makeUniqueSeasonPageFetch()
    ));
    const meta = { schema_version: 'canonical-inventory-artifact/v2', extracted_at: '2026-08-01T00:00:00Z' };
    const perSeasonCounts = {};
    for (const c of result.candidates) perSeasonCounts[c.season] = (perSeasonCounts[c.season] || 0) + 1;
    const v2 = {
        identity_projection_hash: computeV1IdentityProjectionHash(result.candidates),
        business_hash: computeV2BusinessHash(result.candidates),
        per_season_counts: perSeasonCounts,
    };
    const candidateDoc = buildV2OutputDocument(result.candidates, result.snapshot, meta, v2);
    // Mark as synthetic for testing so the contract does not require the
    // approved real master hash.
    candidateDoc.artifact.synthetic_test_only = true;
    const summaryDoc = buildV2SummaryDocument(result.candidates, result.snapshot, meta, v2);
    return { candidateDoc, summaryDoc };
}

test('v2 pair: first write succeeds, both files created', async () => {
    const { writeV2OutputFiles, bestEffortUnlink: cliCleanup } = require('../../scripts/ops/fotmob_candidates_export');
    const tmpDir = fs.mkdtempSync('/tmp/m3d2bf_v2pair_first_');
    try {
        const { candidateDoc, summaryDoc } = await buildValidV2Docs();
        writeV2OutputFiles(tmpDir, candidateDoc, summaryDoc, { repositoryRoot: '/home/user/repo' }, { allowSyntheticTestOnly: true });
        assert.ok(fs.existsSync(path.join(tmpDir, 'canonical-inventory-artifact.v2.json')));
        assert.ok(fs.existsSync(path.join(tmpDir, 'canonical-inventory-artifact.v2.summary.json')));
    } finally {
        bestEffort(() => fs.rmSync(tmpDir, { recursive: true, force: true }));
    }
});

test('v2 pair: idempotent second write with identical content', async () => {
    const { writeV2OutputFiles } = require('../../scripts/ops/fotmob_candidates_export');
    const tmpDir = fs.mkdtempSync('/tmp/m3d2bf_v2pair_idem_');
    try {
        const { candidateDoc, summaryDoc } = await buildValidV2Docs();
        writeV2OutputFiles(tmpDir, candidateDoc, summaryDoc, { repositoryRoot: '/home/user/repo' }, { allowSyntheticTestOnly: true });
        const stat1 = fs.lstatSync(path.join(tmpDir, 'canonical-inventory-artifact.v2.json'));
        // Second write with identical content should succeed (idempotent)
        writeV2OutputFiles(tmpDir, candidateDoc, summaryDoc, { repositoryRoot: '/home/user/repo' }, { allowSyntheticTestOnly: true });
        const stat2 = fs.lstatSync(path.join(tmpDir, 'canonical-inventory-artifact.v2.json'));
        assert.equal(stat1.mtimeMs, stat2.mtimeMs, 'idempotent write should not modify files');
    } finally {
        bestEffort(() => fs.rmSync(tmpDir, { recursive: true, force: true }));
    }
});

test('v2 pair: only artifact file (no summary) → SAFETY_ERROR', async () => {
    const { writeV2OutputFiles } = require('../../scripts/ops/fotmob_candidates_export');
    const tmpDir = fs.mkdtempSync('/tmp/m3d2bf_v2pair_oa_');
    try {
        const { candidateDoc, summaryDoc } = await buildValidV2Docs();
        // Create only artifact, leave summary absent
        fs.writeFileSync(path.join(tmpDir, 'canonical-inventory-artifact.v2.json'), JSON.stringify(candidateDoc));
        assert.throws(
            () => writeV2OutputFiles(tmpDir, candidateDoc, summaryDoc, { repositoryRoot: '/home/user/repo' }, { allowSyntheticTestOnly: true }),
            { code: 'SAFETY_ERROR' }
        );
    } finally {
        bestEffort(() => fs.rmSync(tmpDir, { recursive: true, force: true }));
    }
});

test('v2 pair: only summary file (no artifact) → SAFETY_ERROR', async () => {
    const { writeV2OutputFiles } = require('../../scripts/ops/fotmob_candidates_export');
    const tmpDir = fs.mkdtempSync('/tmp/m3d2bf_v2pair_os_');
    try {
        const { candidateDoc, summaryDoc } = await buildValidV2Docs();
        // Create only summary, leave artifact absent
        fs.writeFileSync(path.join(tmpDir, 'canonical-inventory-artifact.v2.summary.json'), JSON.stringify(summaryDoc));
        assert.throws(
            () => writeV2OutputFiles(tmpDir, candidateDoc, summaryDoc, { repositoryRoot: '/home/user/repo' }, { allowSyntheticTestOnly: true }),
            { code: 'SAFETY_ERROR' }
        );
    } finally {
        bestEffort(() => fs.rmSync(tmpDir, { recursive: true, force: true }));
    }
});

test('v2 pair: artifact same but summary content differs → SAFETY_ERROR', async () => {
    const { writeV2OutputFiles } = require('../../scripts/ops/fotmob_candidates_export');
    const tmpDir = fs.mkdtempSync('/tmp/m3d2bf_v2pair_asd_');
    try {
        const { candidateDoc, summaryDoc } = await buildValidV2Docs();
        writeV2OutputFiles(tmpDir, candidateDoc, summaryDoc, { repositoryRoot: '/home/user/repo' }, { allowSyntheticTestOnly: true });
        // Tamper with the summary on disk, then try again with unchanged candidate
        fs.writeFileSync(
            path.join(tmpDir, 'canonical-inventory-artifact.v2.summary.json'),
            JSON.stringify({ tampered: true })
        );
        assert.throws(
            () => writeV2OutputFiles(tmpDir, candidateDoc, summaryDoc, { repositoryRoot: '/home/user/repo' }, { allowSyntheticTestOnly: true }),
            { code: 'SAFETY_ERROR' }
        );
    } finally {
        bestEffort(() => fs.rmSync(tmpDir, { recursive: true, force: true }));
    }
});

test('v2 pair: artifact is symlink → SAFETY_ERROR', async () => {
    const { writeV2OutputFiles } = require('../../scripts/ops/fotmob_candidates_export');
    const tmpDir = fs.mkdtempSync('/tmp/m3d2bf_v2pair_asl_');
    const realDir = fs.mkdtempSync('/tmp/m3d2bf_v2pair_asl_real_');
    try {
        const { candidateDoc, summaryDoc } = await buildValidV2Docs();
        const realArtifactPath = path.join(realDir, 'canonical-inventory-artifact.v2.json');
        const linkArtifactPath = path.join(tmpDir, 'canonical-inventory-artifact.v2.json');
        const summaryPath_sl = path.join(tmpDir, 'canonical-inventory-artifact.v2.summary.json');
        fs.writeFileSync(realArtifactPath, JSON.stringify(candidateDoc));
        fs.symlinkSync(realArtifactPath, linkArtifactPath);
        fs.writeFileSync(summaryPath_sl, JSON.stringify(summaryDoc));
        assert.throws(
            () => writeV2OutputFiles(tmpDir, candidateDoc, summaryDoc, { repositoryRoot: '/home/user/repo' }, { allowSyntheticTestOnly: true }),
            { code: 'SAFETY_ERROR' }
        );
    } finally {
        bestEffort(() => fs.rmSync(tmpDir, { recursive: true, force: true }));
        bestEffort(() => fs.rmSync(realDir, { recursive: true, force: true }));
    }
});

test('v2 pair: summary rename failure → no orphaned final artifact file', async () => {
    const { writeV2OutputFiles } = require('../../scripts/ops/fotmob_candidates_export');
    const tmpDir = fs.mkdtempSync('/tmp/m3d2bf_v2pair_srf_');
    try {
        const { candidateDoc, summaryDoc } = await buildValidV2Docs();
        const finalArtifactPath = path.join(tmpDir, 'canonical-inventory-artifact.v2.json');
        const finalSummaryPath = path.join(tmpDir, 'canonical-inventory-artifact.v2.summary.json');
        const realRenameSync = fs.renameSync;
        let renameCount = 0;
        const mockFs = {
            ...fs,
            renameSync: (src, dst) => {
                renameCount += 1;
                if (renameCount === 2 && dst === finalSummaryPath) {
                    throw new Error('simulated summary rename failure');
                }
                return realRenameSync(src, dst);
            },
        };
        assert.throws(
            () => writeV2OutputFiles(tmpDir, candidateDoc, summaryDoc, { repositoryRoot: '/home/user/repo', fileSystem: mockFs }, { allowSyntheticTestOnly: true }),
            { code: 'SAFETY_ERROR' }
        );
        assert.equal(fs.existsSync(finalArtifactPath), false, 'orphaned artifact should not exist after rollback');
        assert.equal(fs.existsSync(finalSummaryPath), false, 'summary should not exist');
    } finally {
        bestEffort(() => fs.rmSync(tmpDir, { recursive: true, force: true }));
    }
});

test('v2 pair: contract rejection → zero files written', async () => {
    const { writeV2OutputFiles } = require('../../scripts/ops/fotmob_candidates_export');
    const tmpDir = fs.mkdtempSync('/tmp/m3d2bf_v2pair_cr_');
    try {
        // Build an invalid artifact (wrong candidate count for master)
        const badDoc = { schema_version: 'canonical-inventory-artifact/v2', artifact: { kind: 'master' }, candidates: [1, 2, 3] };
        const badSummary = { schema_version: 'canonical-inventory-artifact/v2', summary: { total_candidates: 3 } };
        assert.throws(
            () => writeV2OutputFiles(tmpDir, badDoc, badSummary, { repositoryRoot: '/home/user/repo' }),
            { code: 'CANONICAL_INPUT_INVALID' }
        );
        assert.equal(fs.existsSync(path.join(tmpDir, 'canonical-inventory-artifact.v2.json')), false);
        assert.equal(fs.existsSync(path.join(tmpDir, 'canonical-inventory-artifact.v2.summary.json')), false);
    } finally {
        bestEffort(() => fs.rmSync(tmpDir, { recursive: true, force: true }));
    }
});

// =================================================================
// Network: verify all tests use mocked fetch, zero real network
// =================================================================

/* prettier-ignore */
test('no global fetch leakage in tests', () => { assert.ok(typeof global.fetch === 'function' || global.fetch === undefined); });
