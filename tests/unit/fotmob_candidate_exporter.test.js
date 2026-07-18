'use strict';

// lifecycle: permanent
// Unit tests for FotMobCandidateExporter — fully mocked, no network.

const test = require('node:test');
const assert = require('node:assert');
const path = require('node:path');
const fs = require('node:fs');
const crypto = require('node:crypto');

const {
    EPL_FIXTURES_PER_SEASON,
    normaliseSeason,
    generateCandidateId,
    isStrictAbsoluteTimestamp,
    extractNextData,
    extractPageIdentity,
    extractFixtures,
    buildCandidate,
    validateSeasonCandidates,
    computeBusinessContentHash,
    verifyOutputPathSafety,
    buildOutputDocument,
    buildSummaryDocument,
    writeOutputFiles,
    exportCandidates,
    delay,
    MAX_TOTAL_REQUESTS,
} = require('../../src/infrastructure/fotmob/FotMobCandidateExporter');

// -----------------------------------------------------------------
// Synthetic fixture builders
// -----------------------------------------------------------------

function buildFixture(id, home, away, kickoff, statusReason = 'FT') {
    return {
        id,
        home: { name: home },
        away: { name: away },
        status: { utcTime: kickoff, reason: { short: statusReason }, scoreStr: '1-0' },
    };
}

function buildNextDataPage(overrides = {}) {
    const fixtures = overrides.fixtures || generateSeasonFixtures(1, EPL_FIXTURES_PER_SEASON);
    const nd = {
        props: {
            pageProps: {
                tabs: ['overview', 'table', 'fixtures', 'stats', 'seasons'],
                allAvailableSeasons: ['2026/2027', '2025/2026', '2024/2025', '2023/2024', '2022/2023'],
                details: {
                    name: overrides.leagueName || 'Premier League',
                    id: overrides.leagueId !== undefined ? overrides.leagueId : 47,
                },
                fixtures: {
                    allMatches: fixtures,
                    firstUnplayedMatch: null,
                    hasOngoingMatch: false,
                },
                ...(overrides.pagePropsExtra || {}),
            },
        },
        query: {
            season: overrides.season || '2022/2023',
            id: String(overrides.leagueId !== undefined ? overrides.leagueId : 47),
            tab: 'fixtures',
            slug: ['premier-league'],
        },
        buildId: 'test-build-id',
    };

    const json = JSON.stringify(nd);
    const html = `<!DOCTYPE html><html><head><title>${nd.props.pageProps.details.name} fixtures ${nd.query.season}</title></head><body><script id="__NEXT_DATA__" type="application/json">${json}</script></body></html>`;

    return { html, nd, json };
}

function generateSeasonFixtures(startId, count = EPL_FIXTURES_PER_SEASON) {
    const teams = [
        'Arsenal',
        'Aston Villa',
        'Bournemouth',
        'Brentford',
        'Brighton',
        'Chelsea',
        'Crystal Palace',
        'Everton',
        'Fulham',
        'Leeds',
        'Leicester',
        'Liverpool',
        'Man City',
        'Man United',
        'Newcastle',
        'Southampton',
        'Tottenham',
        'West Ham',
        'Wolves',
        'Nottingham Forest',
    ];
    const fixtures = [];
    for (let i = 0; i < count; i += 1) {
        const h = teams[i % 20];
        const a = teams[(i + 3) % 20];
        const kickoff = `2022-${String((i % 12) + 1).padStart(2, '0')}-${String((i % 28) + 1).padStart(2, '0')}T${String((i % 22) + 1).padStart(2, '0')}:00:00Z`;
        fixtures.push(buildFixture(startId + i, h, a, kickoff));
    }
    return fixtures;
}

// Build the canonical 2022/2023 candidate for a synthetic fixture.
function candidateFromFixture(f) {
    return buildCandidate(
        { id: f.id.toString(), home: f.home.name, away: f.away.name, kickoff: f.status.utcTime },
        47,
        'Premier League',
        '2022/2023'
    );
}

// Run a cleanup step without letting its failure mask the test result.
function bestEffort(fn) {
    try {
        fn();
    } catch (cleanupError) {
        // Test cleanup is best-effort.
        void cleanupError;
    }
}

const EPL_BASE_IDS = { '2022/2023': 3900000, '2023/2024': 4190000, '2024/2025': 4500000 };
const FIXED_CLOCK = () => '2026-07-18T00:00:00Z';
// Business hash of the 3-season mock pipeline, pinned before the M3-D2BG refactor.
const EXPECTED_PIPELINE_HASH = '046dac4c0a9ff711befc55f5aa885494367303ce9d0ee3aa30c9a5afe1a86c15';

// Fetch mock: canonical Premier League page with 380 synthetic fixtures per season.
function makeSeasonPageFetch(onSeason) {
    return async url => {
        const season = decodeURIComponent(url.match(/season=([^&]+)/)[1]);
        if (onSeason) {
            onSeason(season);
        }
        const fixtures = generateSeasonFixtures(EPL_BASE_IDS[season] || 1000, EPL_FIXTURES_PER_SEASON);
        const { html } = buildNextDataPage({ fixtures, season });
        return { status: 200, contentType: 'text/html', body: html };
    };
}

// Rebuild page HTML after mutating the generated __NEXT_DATA__ object.
function rebuildPageHtml(nd, html) {
    const json = JSON.stringify(nd);
    return html.replace(
        /<script id="__NEXT_DATA__"[^>]*>.*?<\/script>/s,
        `<script id="__NEXT_DATA__" type="application/json">${json}</script>`
    );
}

// -----------------------------------------------------------------
// Unit: normaliseSeason
// -----------------------------------------------------------------

test('normaliseSeason canonicalises valid formats', () => {
    assert.equal(normaliseSeason('2022/2023'), '2022/2023');
    assert.equal(normaliseSeason('2023/2024'), '2023/2024');
    assert.equal(normaliseSeason('2022-2023'), '2022/2023');
    assert.equal(normaliseSeason('22/23'), '2022/2023');
    assert.equal(normaliseSeason('23/24'), '2023/2024');
});

test('normaliseSeason rejects invalid formats', () => {
    assert.equal(normaliseSeason(''), null);
    assert.equal(normaliseSeason('abc'), null);
    assert.equal(normaliseSeason('2022'), null);
    assert.equal(normaliseSeason('22/25'), null); // gap > 1 after expansion
    assert.equal(normaliseSeason('2022/23'), null); // mixed format
});

test('normaliseSeason passes through canonical format even for illogical ranges', () => {
    // The normaliser canonicalises FORMAT, not logic. Season validation
    // (right competition, right league, right year) happens at identity check.
    assert.equal(normaliseSeason('2022/2024'), '2022/2024');
});

// -----------------------------------------------------------------
// Unit: helpers
// -----------------------------------------------------------------

test('generateCandidateId follows L1 contract', () => {
    assert.equal(generateCandidateId(47, '2022/2023', '3900932'), '47_20222023_3900932');
    assert.equal(generateCandidateId(53, '2025/2026', '4830473'), '53_20252026_4830473');
    assert.equal(generateCandidateId('47', '2024/2025', '4506263'), '47_20242025_4506263');
});

test('isStrictAbsoluteTimestamp accepts valid timestamps', () => {
    assert.ok(isStrictAbsoluteTimestamp('2022-08-05T19:00:00Z'));
    assert.ok(isStrictAbsoluteTimestamp('2022-08-05T19:00:00+00:00'));
    assert.ok(isStrictAbsoluteTimestamp('2022-08-06T11:30:00+01:00'));
    assert.equal(isStrictAbsoluteTimestamp('2022-08-05 19:00:00'), false);
    assert.equal(isStrictAbsoluteTimestamp('2022-08-05T19:00:00'), false);
    assert.equal(isStrictAbsoluteTimestamp(''), false);
    assert.equal(isStrictAbsoluteTimestamp(null), false);
});

test('extractNextData parses valid __NEXT_DATA__', () => {
    const { html } = buildNextDataPage();
    const nd = extractNextData(html);
    assert.ok(nd);
    assert.equal(nd.props.pageProps.details.name, 'Premier League');
    assert.equal(nd.query.season, '2022/2023');
});

test('extractNextData returns null for missing __NEXT_DATA__', () => {
    assert.equal(extractNextData('<html><body>no data</body></html>'), null);
});

test('extractPageIdentity returns correct fields including season_canonical', () => {
    const { nd } = buildNextDataPage();
    const identity = extractPageIdentity(nd);
    assert.equal(identity.league_name, 'Premier League');
    assert.equal(identity.league_id, '47');
    assert.equal(identity.season_raw, '2022/2023');
    assert.equal(identity.season_canonical, '2022/2023');
    assert.ok(identity.tabs.includes('fixtures'));
});

test('extractPageIdentity normalises dash-format season', () => {
    const { nd } = buildNextDataPage({ season: '2023-2024' });
    const identity = extractPageIdentity(nd);
    assert.equal(identity.season_raw, '2023-2024');
    assert.equal(identity.season_canonical, '2023/2024');
});

test('extractPageIdentity returns null season_canonical for bad format', () => {
    const { nd } = buildNextDataPage({ season: 'not-a-season' });
    const identity = extractPageIdentity(nd);
    assert.equal(identity.season_canonical, null);
});

// -----------------------------------------------------------------
// Unit: extractFixtures with audit
// -----------------------------------------------------------------

test('extractFixtures returns correct count with audit', () => {
    const fixtures = generateSeasonFixtures(1000, 380);
    const { nd } = buildNextDataPage({ fixtures });
    const result = extractFixtures(nd);
    assert.equal(result.fixtures.length, 380);
    assert.equal(result.audit.raw_fixture_count, 380);
    assert.equal(result.audit.excluded_fixture_count, 0);
    assert.equal(result.audit.accepted_fixture_count, 380);
    assert.equal(result.fixtures[0].id, '1000');
    assert.equal(result.fixtures[0].home, 'Arsenal');
});

test('extractFixtures skips abandoned matches and records audit', () => {
    const fixtures = [
        buildFixture('1', 'TeamA', 'TeamB', '2022-08-01T15:00:00Z', 'FT'),
        buildFixture('2', 'TeamC', 'TeamD', '2022-08-02T15:00:00Z', 'Ab'),
        buildFixture('3', 'TeamE', 'TeamF', '2022-08-03T15:00:00Z', 'FT'),
    ];
    const { nd } = buildNextDataPage({ fixtures });
    const result = extractFixtures(nd);
    assert.equal(result.fixtures.length, 2);
    assert.equal(result.fixtures[0].id, '1');
    assert.equal(result.fixtures[1].id, '3');
    assert.equal(result.audit.raw_fixture_count, 3);
    assert.equal(result.audit.excluded_fixture_count, 1);
    assert.equal(result.audit.excluded_by_reason['Ab'], 1);
    assert.equal(result.audit.accepted_fixture_count, 2);
    assert.equal(result.audit.excluded_fixture_samples.length, 1);
    assert.equal(result.audit.excluded_fixture_samples[0].source_match_id, '2');
    assert.equal(result.audit.excluded_fixture_samples[0].reason_code, 'Ab');
});

test('extractFixtures does NOT exclude postponed matches', () => {
    const fixtures = [
        buildFixture('1', 'TeamA', 'TeamB', '2022-08-01T15:00:00Z', 'FT'),
        buildFixture('2', 'TeamC', 'TeamD', '2022-08-02T15:00:00Z', 'Postp'),
        buildFixture('3', 'TeamE', 'TeamF', '2022-08-03T15:00:00Z', 'FT'),
    ];
    const { nd } = buildNextDataPage({ fixtures });
    const result = extractFixtures(nd);
    assert.equal(result.fixtures.length, 3, 'postponed should NOT be excluded');
    assert.equal(result.audit.excluded_fixture_count, 0);
    assert.equal(result.audit.accepted_fixture_count, 3);
});

test('extractFixtures does NOT silently exclude status-missing matches', () => {
    const fixtures = [
        buildFixture('1', 'TeamA', 'TeamB', '2022-08-01T15:00:00Z', 'FT'),
        { id: '2', home: { name: 'TeamC' }, away: { name: 'TeamD' }, status: { utcTime: '2022-08-02T15:00:00Z' } }, // no reason.short
        buildFixture('3', 'TeamE', 'TeamF', '2022-08-03T15:00:00Z', 'FT'),
    ];
    const { nd } = buildNextDataPage({ fixtures });
    const result = extractFixtures(nd);
    assert.equal(result.fixtures.length, 3, 'status-missing should NOT be excluded');
    assert.equal(result.audit.excluded_fixture_count, 0);
});

test('extractFixtures handles multiple abandoned matches', () => {
    const fixtures = [
        buildFixture('1', 'TeamA', 'TeamB', '2022-08-01T15:00:00Z', 'Ab'),
        buildFixture('2', 'TeamC', 'TeamD', '2022-08-02T15:00:00Z', 'Ab'),
        buildFixture('3', 'TeamE', 'TeamF', '2022-08-03T15:00:00Z', 'FT'),
    ];
    const { nd } = buildNextDataPage({ fixtures });
    const result = extractFixtures(nd);
    assert.equal(result.fixtures.length, 1);
    assert.equal(result.audit.excluded_fixture_count, 2);
    assert.equal(result.audit.excluded_by_reason['Ab'], 2);
    assert.equal(result.audit.accepted_fixture_count, 1);
});

test('extractFixtures handles null/undefined/missing allMatches', () => {
    const emptyCases = [{ fixtures: null }, { fixtures: undefined }, { allMatches: null }];
    for (const overrides of emptyCases) {
        const { nd } = buildNextDataPage({ pagePropsExtra: { fixtures: overrides } });
        const result = extractFixtures(nd);
        assert.equal(result.fixtures.length, 0);
        assert.equal(result.audit.raw_fixture_count, 0);
    }
});

test('extractFixtures handles empty allMatches array', () => {
    const { nd } = buildNextDataPage({ fixtures: [] });
    const result = extractFixtures(nd);
    assert.equal(result.fixtures.length, 0);
    assert.equal(result.audit.raw_fixture_count, 0);
    assert.equal(result.audit.accepted_fixture_count, 0);
});

test('extractFixtures skips non-numeric IDs', () => {
    const fixtures = [
        buildFixture('abc', 'TeamA', 'TeamB', '2022-08-01T15:00:00Z'),
        buildFixture('123', 'TeamC', 'TeamD', '2022-08-02T15:00:00Z'),
    ];
    const { nd } = buildNextDataPage({ fixtures });
    const result = extractFixtures(nd);
    assert.equal(result.fixtures.length, 1);
    assert.equal(result.fixtures[0].id, '123');
});

test('extractFixtures skips missing teams or kickoff', () => {
    const fixtures = [
        { id: '1', home: null, away: { name: 'TeamB' }, status: { utcTime: '2022-08-01T15:00:00Z' } },
        { id: '2', home: { name: 'TeamC' }, away: null, status: { utcTime: '2022-08-01T15:00:00Z' } },
        { id: '3', home: { name: 'TeamE' }, away: { name: 'TeamF' }, status: {} },
        { id: '4', home: { name: 'TeamG' }, away: { name: 'TeamH' }, status: { utcTime: '2022-08-01T15:00:00Z' } },
    ];
    const { nd } = buildNextDataPage({ fixtures });
    const result = extractFixtures(nd);
    assert.equal(result.fixtures.length, 1);
    assert.equal(result.fixtures[0].id, '4');
});

// -----------------------------------------------------------------
// Unit: buildCandidate / validateSeasonCandidates
// -----------------------------------------------------------------

test('buildCandidate produces correct structure', () => {
    const fixture = { id: '3900932', home: 'Arsenal', away: 'Fulham', kickoff: '2022-08-05T19:00:00Z' };
    const candidate = buildCandidate(fixture, 47, 'Premier League', '2022/2023');
    assert.equal(candidate.id, '47_20222023_3900932');
    assert.equal(candidate.source_provider, 'FotMob');
    assert.equal(candidate.source_match_id, '3900932');
    assert.equal(candidate.competition, 'Premier League');
    assert.equal(candidate.season, '2022/2023');
    assert.equal(candidate.home_team, 'Arsenal');
    assert.equal(candidate.away_team, 'Fulham');
    assert.equal(candidate.kickoff_at, '2022-08-05T19:00:00Z');
});

test('validateSeasonCandidates passes for 380 valid candidates', () => {
    const candidates = generateSeasonFixtures(1000, 380).map(candidateFromFixture);
    const result = validateSeasonCandidates(candidates, {
        competition: 'Premier League',
        season: '2022/2023',
        expectedFixtures: 380,
    });
    assert.ok(result.valid);
    assert.equal(result.fixture_count, 380);
    assert.equal(result.errors.length, 0);
});

test('validateSeasonCandidates rejects 379 fixtures', () => {
    const candidates = generateSeasonFixtures(1000, 379).map(candidateFromFixture);
    const result = validateSeasonCandidates(candidates, {
        competition: 'Premier League',
        season: '2022/2023',
        expectedFixtures: 380,
    });
    assert.equal(result.valid, false);
    assert.ok(result.errors.some(e => e.includes('fixture_count_mismatch')));
});

test('validateSeasonCandidates rejects duplicate IDs', () => {
    const single = buildCandidate(
        { id: '1', home: 'A', away: 'B', kickoff: '2022-08-01T15:00:00Z' },
        47,
        'Premier League',
        '2022/2023'
    );
    const result = validateSeasonCandidates([single, single], {
        competition: 'Premier League',
        season: '2022/2023',
        expectedFixtures: 2,
    });
    assert.equal(result.valid, false);
    assert.ok(result.errors.some(e => e.includes('duplicate_id')));
});

test('validateSeasonCandidates rejects same teams', () => {
    const candidate = buildCandidate(
        { id: '1', home: 'TeamA', away: 'TeamA', kickoff: '2022-08-01T15:00:00Z' },
        47,
        'Premier League',
        '2022/2023'
    );
    const result = validateSeasonCandidates([candidate], {
        competition: 'Premier League',
        season: '2022/2023',
        expectedFixtures: 1,
    });
    assert.equal(result.valid, false);
    assert.ok(result.errors.some(e => e.includes('same_teams')));
});

test('validateSeasonCandidates rejects bad kickoff format', () => {
    const candidate = buildCandidate(
        { id: '1', home: 'TeamA', away: 'TeamB', kickoff: '2022-08-01 15:00:00' },
        47,
        'Premier League',
        '2022/2023'
    );
    const result = validateSeasonCandidates([candidate], {
        competition: 'Premier League',
        season: '2022/2023',
        expectedFixtures: 1,
    });
    assert.equal(result.valid, false);
    assert.ok(result.errors.some(e => e.includes('bad_kickoff')));
});

test('validateSeasonCandidates rejects wrong competition', () => {
    const candidate = buildCandidate(
        { id: '1', home: 'A', away: 'B', kickoff: '2022-08-01T15:00:00Z' },
        47,
        'Wrong League',
        '2022/2023'
    );
    const result = validateSeasonCandidates([candidate], {
        competition: 'Premier League',
        season: '2022/2023',
        expectedFixtures: 1,
    });
    assert.equal(result.valid, false);
});

// -----------------------------------------------------------------
// Unit: hash determinism
// -----------------------------------------------------------------

test('computeBusinessContentHash is stable regardless of input order', () => {
    const candidates1 = generateSeasonFixtures(1000, 10).map(candidateFromFixture);
    const candidates2 = [...candidates1].reverse();
    const hash1 = computeBusinessContentHash(candidates1);
    const hash2 = computeBusinessContentHash(candidates2);
    assert.equal(hash1, hash2);
});

test('extracted_at does not affect business content hash', () => {
    const candidates = generateSeasonFixtures(1000, 10).map(candidateFromFixture);
    const hash1 = computeBusinessContentHash(candidates);
    const doc1 = buildOutputDocument(
        candidates,
        {
            source_provider: 'FotMob',
            league_id: '47',
            competition: 'Premier League',
            seasons: ['2022/2023'],
            candidate_count: 10,
            business_content_sha256: hash1,
        },
        { schema_version: 'candidate-match-identity/v1', extracted_at: '2026-01-01T00:00:00Z' }
    );
    const doc2 = buildOutputDocument(
        candidates,
        {
            source_provider: 'FotMob',
            league_id: '47',
            competition: 'Premier League',
            seasons: ['2022/2023'],
            candidate_count: 10,
            business_content_sha256: hash1,
        },
        { schema_version: 'candidate-match-identity/v1', extracted_at: '2026-06-15T12:00:00Z' }
    );
    assert.equal(doc1.snapshot.business_content_sha256, doc2.snapshot.business_content_sha256);
    assert.notEqual(doc1.extracted_at, doc2.extracted_at);
});

// -----------------------------------------------------------------
// Unit: output path safety (F2 — symlink protection)
// -----------------------------------------------------------------

test('verifyOutputPathSafety rejects paths inside repository', () => {
    const repoRoot = path.resolve(__dirname, '..', '..');
    assert.throws(() => verifyOutputPathSafety(repoRoot, { repositoryRoot: repoRoot }), { code: 'SAFETY_ERROR' });
    assert.throws(() => verifyOutputPathSafety(path.join(repoRoot, 'subdir'), { repositoryRoot: repoRoot }), {
        code: 'SAFETY_ERROR',
    });
});

test('verifyOutputPathSafety rejects .git paths', () => {
    assert.throws(() => verifyOutputPathSafety('/tmp/project/.git/objects', {}), { code: 'SAFETY_ERROR' });
});

test('verifyOutputPathSafety accepts external absolute paths', () => {
    const result = verifyOutputPathSafety('/tmp', { repositoryRoot: '/home/user/repo' });
    assert.ok(result.startsWith('/tmp'));
});

test('verifyOutputPathSafety rejects relative paths', () => {
    assert.throws(() => verifyOutputPathSafety('relative/path', {}), { code: 'SAFETY_ERROR' });
});

test('verifyOutputPathSafety rejects non-existent directories', () => {
    assert.throws(
        () => verifyOutputPathSafety('/tmp/NONEXISTENT_DIR_M3D2B_TEST', { repositoryRoot: '/home/user/repo' }),
        { code: 'SAFETY_ERROR' }
    );
});

test('verifyOutputPathSafety rejects symlink as output path', t => {
    const tmpDir = fs.mkdtempSync('/tmp/m3d2bf_output_symlink_test_');
    const realDir = fs.mkdtempSync('/tmp/m3d2bf_output_real_');
    const linkPath = path.join(tmpDir, 'symlink_to_real');
    try {
        fs.symlinkSync(realDir, linkPath, 'dir');
        assert.throws(() => verifyOutputPathSafety(linkPath, { repositoryRoot: '/home/user/repo' }), {
            code: 'SAFETY_ERROR',
        });
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
        assert.throws(() => verifyOutputPathSafety(linkPath, { repositoryRoot: repoRoot }), { code: 'SAFETY_ERROR' });
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

    const result = await exportCandidates({
        leagueId: 47,
        competition: 'Premier League',
        seasons: ['2022/2023', '2023/2024', '2024/2025'],
        deps: { fetchPage: mockFetch, delay: () => Promise.resolve(), clock: () => '2026-07-18T00:00:00Z' },
    });

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
    const { html } = buildNextDataPage({ season: '2023/2024' }); // page says 2023/2024
    const mockFetch = async () => ({ status: 200, contentType: 'text/html', body: html });

    const result = await exportCandidates({
        leagueId: 47,
        competition: 'Premier League',
        seasons: ['2022/2023'], // request says 2022/2023
        deps: { fetchPage: mockFetch, delay: () => Promise.resolve(), clock: () => '2026-07-18T00:00:00Z' },
    });

    assert.equal(result.candidates.length, 0, 'no candidates when season mismatches');
    assert.ok(result.validation.season_results[0].result.includes('season_identity_mismatch'));
});

test('exportCandidates rejects missing season in page', async () => {
    const { nd, html } = buildNextDataPage();
    delete nd.query.season;
    const fixedHtml = rebuildPageHtml(nd, html);

    const mockFetch = async () => ({ status: 200, contentType: 'text/html', body: fixedHtml });
    const result = await exportCandidates({
        leagueId: 47,
        competition: 'Premier League',
        seasons: ['2022/2023'],
        deps: { fetchPage: mockFetch, delay: () => Promise.resolve(), clock: () => '2026-07-18T00:00:00Z' },
    });

    assert.equal(result.candidates.length, 0);
    assert.ok(result.validation.season_results[0].result.includes('season_identity_missing'));
});

test('exportCandidates rejects bad season format in page', async () => {
    const { nd, html } = buildNextDataPage();
    nd.query.season = 'not-a-season';
    const fixedHtml = rebuildPageHtml(nd, html);

    const mockFetch = async () => ({ status: 200, contentType: 'text/html', body: fixedHtml });
    const result = await exportCandidates({
        leagueId: 47,
        competition: 'Premier League',
        seasons: ['2022/2023'],
        deps: { fetchPage: mockFetch, delay: () => Promise.resolve(), clock: () => '2026-07-18T00:00:00Z' },
    });

    assert.equal(result.candidates.length, 0);
    assert.ok(result.validation.season_results[0].result.includes('season_identity_missing'));
});

test('exportCandidates accepts dash-format season from page', async () => {
    const { nd, html } = buildNextDataPage();
    nd.query.season = '2022-2023';
    const fixedHtml = rebuildPageHtml(nd, html);

    const mockFetch = async () => ({ status: 200, contentType: 'text/html', body: fixedHtml });
    const result = await exportCandidates({
        leagueId: 47,
        competition: 'Premier League',
        seasons: ['2022/2023'],
        deps: { fetchPage: mockFetch, delay: () => Promise.resolve(), clock: () => '2026-07-18T00:00:00Z' },
    });

    assert.equal(result.candidates.length, 380, 'dash-format season should be accepted');
    assert.ok(result.validation.all_seasons_complete);
});

test('exportCandidates records audit for abandoned matches', async () => {
    const fixtures = generateSeasonFixtures(1000, 380);
    fixtures.push(buildFixture('9999999', 'TeamX', 'TeamY', '2022-12-25T15:00:00Z', 'Ab'));
    const { html } = buildNextDataPage({ fixtures, season: '2022/2023' });
    const mockFetch = async () => ({ status: 200, contentType: 'text/html', body: html });

    const result = await exportCandidates({
        leagueId: 47,
        competition: 'Premier League',
        seasons: ['2022/2023'],
        deps: { fetchPage: mockFetch, delay: () => Promise.resolve(), clock: () => '2026-07-18T00:00:00Z' },
    });

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

test('exportCandidates stops on HTTP 403', async () => {
    let callCount = 0;
    const mockFetch = async () => {
        callCount += 1;
        return { status: 403, contentType: 'text/html', body: '' };
    };

    const result = await exportCandidates({
        leagueId: 47,
        competition: 'Premier League',
        seasons: ['2022/2023', '2023/2024', '2024/2025'],
        deps: { fetchPage: mockFetch, delay: () => Promise.resolve(), clock: () => '2026-07-18T00:00:00Z' },
    });

    assert.ok(callCount <= 1);
    assert.equal(result.validation.all_seasons_complete, false);
});

test('exportCandidates stops on HTTP 429', async () => {
    let callCount = 0;
    const mockFetch = async () => {
        callCount += 1;
        return { status: 429, contentType: 'text/html', body: '' };
    };

    const result = await exportCandidates({
        leagueId: 47,
        competition: 'Premier League',
        seasons: ['2022/2023', '2023/2024'],
        deps: { fetchPage: mockFetch, delay: () => Promise.resolve(), clock: () => '2026-07-18T00:00:00Z' },
    });

    assert.ok(callCount <= 1);
    assert.ok(result.validation.season_results[0].result.includes('blocked'));
});

test('exportCandidates fails on wrong competition identity', async () => {
    const { html } = buildNextDataPage({ leagueName: 'Championship', leagueId: 47 });
    const mockFetch = async () => ({ status: 200, contentType: 'text/html', body: html });

    const result = await exportCandidates({
        leagueId: 47,
        competition: 'Premier League',
        seasons: ['2022/2023'],
        deps: { fetchPage: mockFetch, delay: () => Promise.resolve(), clock: () => '2026-07-18T00:00:00Z' },
    });

    assert.equal(result.candidates.length, 0);
    assert.ok(result.validation.season_results[0].result.includes('competition_identity_mismatch'));
});

test('exportCandidates fails on wrong league ID in page', async () => {
    const { html } = buildNextDataPage({ leagueId: 53 });
    const mockFetch = async () => ({ status: 200, contentType: 'text/html', body: html });

    const result = await exportCandidates({
        leagueId: 47,
        competition: 'Premier League',
        seasons: ['2022/2023'],
        deps: { fetchPage: mockFetch, delay: () => Promise.resolve(), clock: () => '2026-07-18T00:00:00Z' },
    });

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
    const result = await exportCandidates({
        leagueId: 47,
        competition: 'Premier League',
        seasons,
        deps: { fetchPage: mockFetch, delay: () => Promise.resolve(), clock: () => '2026-07-18T00:00:00Z' },
    });

    assert.ok(callCount <= MAX_TOTAL_REQUESTS);
    assert.ok(result.meta.total_requests <= MAX_TOTAL_REQUESTS);
});

test('exportCandidates returns empty for no seasons', async () => {
    await assert.rejects(exportCandidates({ leagueId: 47, competition: 'Premier League', seasons: [] }), {
        code: 'INPUT_ERROR',
    });
});

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
    const snapshot = {
        source_provider: 'FotMob',
        league_id: '47',
        competition: 'Premier League',
        seasons: ['2022/2023'],
        candidate_count: 1,
        business_content_sha256: 'abc123',
    };
    const meta = { schema_version: 'candidate-match-identity/v1', extracted_at: '2026-07-18T00:00:00Z' };

    const doc = buildOutputDocument(candidates, snapshot, meta);
    assert.equal(doc.schema_version, 'candidate-match-identity/v1');
    assert.equal(doc.extracted_at, '2026-07-18T00:00:00Z');
    assert.equal(doc.snapshot.business_content_sha256, 'abc123');
    assert.equal(doc.candidates.length, 1);
    assert.ok(doc.candidates[0].id);
});

test('buildSummaryDocument contains no full candidate data', () => {
    const candidates = generateSeasonFixtures(1000, 380).map(candidateFromFixture);
    const snapshot = {
        source_provider: 'FotMob',
        league_id: '47',
        competition: 'Premier League',
        seasons: ['2022/2023'],
        candidate_count: 380,
        business_content_sha256: 'hash',
    };
    const meta = { schema_version: 'candidate-match-identity/v1', extracted_at: '2026-07-18T00:00:00Z' };

    const summary = buildSummaryDocument(candidates, snapshot, meta);
    assert.ok(summary.summary);
    assert.equal(summary.summary.total_candidates, 380);
    assert.equal(summary.summary.per_season['2022/2023'], 380);
    assert.equal(summary.candidates, undefined);
});

// -----------------------------------------------------------------
// Full pipeline: 3 seasons × 380 = 1140
// -----------------------------------------------------------------

test('full pipeline: 3 seasons produce exactly 1140 candidates', async () => {
    const mockFetch = makeSeasonPageFetch();

    const result = await exportCandidates({
        leagueId: 47,
        competition: 'Premier League',
        seasons: ['2022/2023', '2023/2024', '2024/2025'],
        deps: { fetchPage: mockFetch, delay: () => Promise.resolve(), clock: () => '2026-07-18T00:00:00Z' },
    });

    assert.equal(result.candidates.length, 1140);
    assert.ok(result.validation.all_seasons_complete);
    assert.equal(result.meta.total_requests, 3);
    assert.equal(result.snapshot.candidate_count, 1140);
    assert.ok(result.snapshot.business_content_sha256);
    // Hash contract pinned pre-refactor (M3-D2BG): identical mock data must keep this value.
    assert.equal(result.snapshot.business_content_sha256, EXPECTED_PIPELINE_HASH);
});

// -----------------------------------------------------------------
// Refactor parity: delay, bounded samples, control flow, cleanup
// -----------------------------------------------------------------

test('delay resolves via mocked timer without network', async t => {
    t.mock.timers.enable({ apis: ['setTimeout'] });
    const pending = delay(1000);
    t.mock.timers.tick(1000);
    assert.equal(await pending, undefined);
});

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
    await exportCandidates({
        leagueId: 47,
        competition: 'Premier League',
        seasons: ['2022/2023', '2023/2024', '2024/2025'],
        deps: { fetchPage: mockFetch, delay: async () => (delays += 1), clock: FIXED_CLOCK },
    });
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
    const result = await exportCandidates({
        leagueId: 47,
        competition: 'Premier League',
        seasons: ['2022/2023', '2023/2024', '2024/2025'],
        deps: { fetchPage: () => steps.shift()(), delay: async () => (delays += 1), clock: FIXED_CLOCK },
    });
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
    const throwingUnlink = p => {
        unlinks.push(p);
        throw new Error('cleanup failed');
    };
    const raise = err => () => {
        throw err;
    };
    const snapshot = {
        source_provider: 'FotMob',
        league_id: '47',
        competition: 'Premier League',
        seasons: [],
        candidate_count: 0,
        business_content_sha256: 'h',
    };
    const meta = { schema_version: 'candidate-match-identity/v1', extracted_at: '2026-07-18T00:00:00Z' };
    const runWith = fileSystem => () =>
        writeOutputFiles('/tmp', [], snapshot, meta, { repositoryRoot: '/repo', fileSystem });
    const renameError = new Error('rename failed');
    const renameFailFs = { ...baseFs, renameSync: raise(renameError), unlinkSync: throwingUnlink };
    assert.throws(runWith(renameFailFs), err => err === renameError);
    assert.equal(unlinks.length, 2);
    assert.ok(unlinks[0].includes('candidate-match-identity.v1.json.tmp.'));
    assert.ok(unlinks[1].includes('candidate-match-identity.v1.summary.json.tmp.'));
    unlinks.length = 0;
    const writeError = new Error('write failed');
    const writeFailFs = { ...baseFs, writeFileSync: raise(writeError), unlinkSync: throwingUnlink };
    assert.throws(runWith(writeFailFs), err => err === writeError);
    assert.equal(unlinks.length, 2);
});
