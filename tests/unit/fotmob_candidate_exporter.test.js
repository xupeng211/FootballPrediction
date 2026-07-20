'use strict';

// lifecycle: permanent
// Unit tests for FotMobCandidateExporter — fully mocked, no network.

const test = require('node:test');
const assert = require('node:assert');
const path = require('node:path');
const fs = require('node:fs');
const { spawnSync } = require('node:child_process');

const {
    EPL_FIXTURES_PER_SEASON,
    normaliseSeason,
    canonicalizeRequestedSeasons,
    canonicalizeCompetition,
    generateCandidateId,
    isStrictAbsoluteTimestamp,
    extractNextData,
    extractPageIdentity,
    extractFixtures,
    classifyFixtureRejection,
    buildCandidate,
    validateSeasonCandidates,
    validateAggregateCandidates,
    computeBusinessContentHash,
    verifyOutputPathSafety,
    buildOutputDocument,
    buildSummaryDocument,
    writeOutputFiles,
    exportCandidates,
    delay,
    MAX_TOTAL_REQUESTS,
} = require('../../src/infrastructure/fotmob/FotMobCandidateExporter');
const { main: runCandidateExportCli, validateArgs } = require('../../scripts/ops/fotmob_candidates_export');

// -----------------------------------------------------------------
// Synthetic fixture builders
// -----------------------------------------------------------------

/* prettier-ignore */
function buildFixture(id, home, away, kickoff, statusReason = 'FT') { return { id, home: { name: home }, away: { name: away }, status: { utcTime: kickoff, reason: { short: statusReason }, scoreStr: '1-0' } }; }
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
// Unit: helpers
// -----------------------------------------------------------------

/* prettier-ignore */
test('generateCandidateId follows L1 contract', () => { assert.equal(generateCandidateId(47, '2022/2023', '3900932'), '47_20222023_3900932'); assert.equal(generateCandidateId(53, '2025/2026', '4830473'), '53_20252026_4830473'); assert.equal(generateCandidateId('47', '2024/2025', '4506263'), '47_20242025_4506263'); });
/* prettier-ignore */
test('isStrictAbsoluteTimestamp accepts valid timestamps', () => { assert.ok(isStrictAbsoluteTimestamp('2022-08-05T19:00:00Z')); assert.ok(isStrictAbsoluteTimestamp('2022-08-05T19:00:00+00:00')); assert.ok(isStrictAbsoluteTimestamp('2022-08-06T11:30:00+01:00')); assert.equal(isStrictAbsoluteTimestamp('2022-08-05 19:00:00'), false); assert.equal(isStrictAbsoluteTimestamp('2022-08-05T19:00:00'), false); assert.equal(isStrictAbsoluteTimestamp(''), false); assert.equal(isStrictAbsoluteTimestamp(null), false); });
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

test('exportCandidates rejects invalid competition before fetch or delay', async () => {
    let toStringCalls = 0;
    const coercibleObject = {
        toString: () => {
            toStringCalls += 1;
            return 'Premier League';
        },
    };
    for (const competition of [
        'Premiere League',
        'EPL',
        'English Premier League',
        ['Premier League'],
        {},
        coercibleObject,
    ]) {
        const calls = { fetch: 0, delay: 0 };
        await assert.rejects(
            exportCandidates(
                makeExportOptions(
                    ['2022/2023'],
                    async () => {
                        calls.fetch += 1;
                        return { status: 500, contentType: 'text/html', body: '' };
                    },
                    { delay: async () => (calls.delay += 1) },
                    { competition }
                )
            ),
            { code: 'INPUT_ERROR' }
        );
        assert.deepEqual(calls, { fetch: 0, delay: 0 });
    }
    assert.equal(toStringCalls, 0);
});

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

test('exportCandidates rejects missing network authorization before fetch or delay', async () => {
    for (const networkAuthorization of [undefined, false, 'yes']) {
        const calls = { fetch: 0, delay: 0 };
        await assert.rejects(
            exportCandidates({
                leagueId: 47,
                competition: 'Premier League',
                seasons: ['2022/2023'],
                networkAuthorization,
                deps: {
                    fetchPage: async () => {
                        calls.fetch += 1;
                        return { status: 500, contentType: 'text/html', body: '' };
                    },
                    delay: async () => (calls.delay += 1),
                },
            }),
            { code: 'SAFETY_ERROR' }
        );
        assert.deepEqual(calls, { fetch: 0, delay: 0 });
    }
});

test('exportCandidates rejects each non-string requested season before fetch or delay', async () => {
    for (const season of [20222023, ['2022/2023'], { toString: () => '2022/2023' }]) {
        await assertInvalidSeasonMakesNoRequests(season);
    }
});

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

test('CLI rejects ordinary invocation without network authorization', async () => {
    let stdout = '';
    let stderr = '';
    let fetchCalls = 0;
    const originalFetch = global.fetch;
    global.fetch = async () => {
        fetchCalls += 1;
        throw new Error('global fetch must not be called');
    };
    try {
        const exitCode = await runCandidateExportCli(
            ['--league-id', '47', '--competition', 'Premier League', '--season', '2022/2023'],
            {
                stdout: { write: value => (stdout += String(value)) },
                stderr: { write: value => (stderr += String(value)) },
            }
        );
        assert.deepEqual([exitCode, stdout, fetchCalls], [2, '', 0]);
        assert.match(stderr, /make data-fotmob-candidates-network-export/);
    } finally {
        global.fetch = originalFetch;
    }
});

test('CLI requires both network preview and network authorization flags', async () => {
    const validArgs = ['--league-id', '47', '--competition', 'Premier League', '--season', '2022/2023'];
    const cases = [
        [...validArgs, '--network-preview=true'],
        [...validArgs, '--network-authorization=yes'],
        [...validArgs, '--network-preview=false', '--network-authorization=yes'],
        [...validArgs, '--network-preview=true', '--network-authorization=no'],
        [...validArgs, '--network-preview=maybe', '--network-authorization=yes'],
        [...validArgs, '--network-preview=true', '--network-authorization=maybe'],
    ];
    const originalFetch = global.fetch;
    try {
        for (const argv of cases) {
            let stderr = '';
            let fetchCalls = 0;
            global.fetch = async () => {
                fetchCalls += 1;
                throw new Error('global fetch must not be called');
            };
            const exitCode = await runCandidateExportCli(argv, {
                stdout: { write: () => {} },
                stderr: { write: value => (stderr += String(value)) },
            });
            assert.deepEqual([exitCode, fetchCalls], [2, 0]);
            assert.match(stderr, /make data-fotmob-candidates-network-export/);
        }
    } finally {
        global.fetch = originalFetch;
    }
});

test('CLI accepts explicit authorization with mocked network only', async () => {
    const { html } = buildNextDataPage({ season: '2022/2023' });
    let stdout = '';
    let stderr = '';
    let mockFetchCalls = 0;
    let globalFetchCalls = 0;
    const originalFetch = global.fetch;
    global.fetch = async () => {
        globalFetchCalls += 1;
        throw new Error('global fetch must not be called');
    };
    try {
        const exitCode = await runCandidateExportCli(
            [
                '--league-id',
                '47',
                '--competition',
                ' premier   league ',
                '--season',
                '2022/2023',
                '--network-preview=true',
                '--network-authorization=yes',
            ],
            {
                stdout: { write: value => (stdout += String(value)) },
                stderr: { write: value => (stderr += String(value)) },
                exporterDeps: {
                    fetchPage: async () => {
                        mockFetchCalls += 1;
                        return { status: 200, contentType: 'text/html', body: html };
                    },
                    delay: async () => {},
                    clock: FIXED_CLOCK,
                },
            }
        );
        assert.deepEqual([exitCode, mockFetchCalls, globalFetchCalls], [0, 1, 0]);
        assert.match(stdout, /"competition": "Premier League"/);
        assert.match(stderr, /Total: 380 candidates/);
    } finally {
        global.fetch = originalFetch;
    }
});

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

test('Make target blocks missing or false network authorization before Node execution', () => {
    const fakeBin = fs.mkdtempSync('/tmp/m3d2bt_make_bin_');
    const fakeDocker = path.join(fakeBin, 'docker');
    const callLog = path.join(fakeBin, 'docker-calls.log');
    const target = 'data-fotmob-candidates-network-export';
    fs.writeFileSync(fakeDocker, '#!/bin/sh\nprintf called >> "$FOTMOB_MAKE_DOCKER_LOG"\n');
    fs.chmodSync(fakeDocker, 0o755);

    const runGate = variables => {
        const env = {
            ...process.env,
            ...variables,
            PATH: `${fakeBin}:${process.env.PATH}`,
            FOTMOB_MAKE_DOCKER_LOG: callLog,
        };
        for (const key of ['LEAGUE_ID', 'COMPETITION', 'SEASONS', 'NETWORK_AUTHORIZATION']) {
            if (!(key in variables)) delete env[key];
        }
        return spawnSync('make', [target], { cwd: path.resolve(__dirname, '../..'), encoding: 'utf8', env });
    };

    try {
        const missing = runGate({});
        assert.notEqual(missing.status, 0);
        assert.match(missing.stdout + missing.stderr, /provide LEAGUE_ID/);
        assert.equal(fs.existsSync(callLog), false);

        const falseAuthorization = runGate({
            LEAGUE_ID: '47',
            COMPETITION: 'Premier League',
            SEASONS: '2022/2023',
            NETWORK_AUTHORIZATION: 'no',
        });
        assert.notEqual(falseAuthorization.status, 0);
        assert.match(
            falseAuthorization.stdout + falseAuthorization.stderr,
            /requires NETWORK_AUTHORIZATION=yes before Node execution/
        );
        assert.equal(fs.existsSync(callLog), false);
    } finally {
        bestEffort(() => fs.rmSync(fakeBin, { recursive: true, force: true }));
    }
});

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

test('canonical 3-season: hash unchanged, aggregate valid, snapshot canonical', async () => {
    const r = await exportCandidates(makeExportOptions(['2022/2023', '2023/2024', '2024/2025'], makeSeasonPageFetch()));
    assert.equal(r.candidates.length, 1140);
    assert.ok(r.validation.all_seasons_complete);
    assert.equal(r.meta.total_requests, 3);
    assert.equal(r.snapshot.candidate_count, 1140);
    assert.equal(r.validation.total_candidates, 1140);
    assert.equal(r.validation.total_expected, 1140);
    assert.equal(r.validation.season_results.length, 3);
    assert.deepEqual(
        r.validation.season_results.map(item => item.result),
        ['complete', 'complete', 'complete']
    );
    assert.equal(r.snapshot.business_content_sha256, EXPECTED_PIPELINE_HASH);
    assert.ok(r.validation.aggregate_validation.valid);
    assert.equal(r.validation.aggregate_validation.unique_ids, 1140);
    assert.equal(r.validation.aggregate_validation.unique_source_ids, 1140);
    assert.deepEqual(r.snapshot.seasons, ['2022/2023', '2023/2024', '2024/2025']);
    assert.deepEqual(r.validation.aggregate_validation.per_season_counts, {
        '2022/2023': 380,
        '2023/2024': 380,
        '2024/2025': 380,
    });
});

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

test('exportCandidates marks rejected missing-kickoff fixture as validation_failed', async () => {
    const fixtures = generateSeasonFixtures(8000000);
    const missingKickoff = buildFixture('8999999', 'TeamX', 'TeamY', '2022-12-25T15:00:00Z');
    delete missingKickoff.status.utcTime;
    fixtures.push(missingKickoff);
    const result = await exportFromHtml(buildNextDataPage({ fixtures, season: '2022/2023' }).html);
    const [seasonResult] = result.validation.season_results;
    const { audit, validation } = seasonResult;
    assert.equal(result.candidates.length, 380);
    assert.equal(result.validation.season_results.length, 1);
    assert.equal(seasonResult.result, 'validation_failed');
    assert.equal(validation.valid, false);
    assert.equal(result.validation.all_seasons_complete, false);
    assert.equal(result.validation.aggregate_validation.valid, true);
    assert.deepEqual(
        [
            audit.raw_fixture_count,
            audit.accepted_fixture_count,
            audit.excluded_fixture_count,
            audit.rejected_fixture_count,
            audit.rejected_by_reason.missing_kickoff,
        ],
        [381, 380, 0, 1, 1]
    );
    assert.equal(
        audit.raw_fixture_count,
        audit.accepted_fixture_count + audit.excluded_fixture_count + audit.rejected_fixture_count
    );
    assert.ok(validation.errors.includes('unexpected_rejected_fixtures:1'));
});
