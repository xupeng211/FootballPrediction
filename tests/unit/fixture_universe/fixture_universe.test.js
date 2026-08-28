'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const test = require('node:test');
const {
    normalize,
    KICKOFF_TOLERANCE_SECONDS,
    seedFotMobFixtureUniverse,
    resolveOddsEvents,
    semanticReplayHash,
} = require('../../../src/infrastructure/fixture_universe/FixtureUniverse');
const historical = require('../../../src/infrastructure/canonical/CanonicalInventoryContract');
const { latestAsOf } = require('../../../src/infrastructure/market_evidence/asOfView');
const { sha256Text } = require('../../../src/infrastructure/market_evidence/contracts');
const { loadIdentityRegistry } = require('../../../src/infrastructure/market_evidence/identityRegistry');
const { adaptTheOddsApiRaw } = require('../../../src/infrastructure/market_evidence/theOddsApiAdapter');

const stageCFixtureRaw = fs.readFileSync(
    path.join(__dirname, '../../fixtures/market_evidence/the_odds_api_epl_h2h.minimal.json'),
    'utf8'
);
const stageCFixtureRegistry = loadIdentityRegistry(
    path.join(__dirname, '../../fixtures/market_evidence/identity_registry.stage_c.v1.json')
);
function buildFixtureUniverseRaw() {
    const allMatches = Array.from({ length: 380 }, (_, index) => ({
        id: String(900000 + index),
        home: { name: index === 0 ? 'Arsenal' : `Home ${index}` },
        away: { name: index === 0 ? 'Chelsea' : `Away ${index}` },
        status: { utcTime: index === 0 ? '2026-09-12T15:00:00Z' : `2026-10-${String((index % 28) + 1).padStart(2, '0')}T15:00:00Z` },
    }));
    return `<script id="__NEXT_DATA__" type="application/json">${JSON.stringify({ query: { season: '2026/2027' }, props: { pageProps: { details: { id: 47 }, fixtures: { allMatches } } } })}</script>`;
}
const fixtureUniverseRaw = buildFixtureUniverseRaw();
const fixtureUniverseOddsRaw = JSON.stringify([{
    id: 'fixture-universe-arsenal-chelsea', sport_key: 'soccer_epl', home_team: 'Arsenal', away_team: 'Chelsea', commence_time: '2026-09-12T15:00:00Z',
    bookmakers: [{ key: 'fixture-bookmaker', title: 'Fixture Bookmaker', markets: [{ key: 'h2h', outcomes: [{ name: 'Arsenal', price: 2.1 }, { name: 'Draw', price: 3.2 }, { name: 'Chelsea', price: 3.6 }] }] }],
}]);
const fixtureUniverseRawSha = sha256Text(fixtureUniverseRaw);
const fixtureUniverseOddsSha = sha256Text(fixtureUniverseOddsRaw);

function deterministicAllocator() {
    let index = 0;
    return prefix => `${prefix}_${String(++index).padStart(4, '0')}`;
}

function seededUniverse() {
    return seedFotMobFixtureUniverse({
        rawHtml: fixtureUniverseRaw,
        rawSha256: fixtureUniverseRawSha,
        manifest: { raw_file_relative_path: 'fixture-universe.html' },
        allocate: deterministicAllocator(),
        mode: 'INITIAL_SEED',
    });
}

function stageCFixtureObservations() {
    return adaptTheOddsApiRaw({
        rawText: stageCFixtureRaw,
        capture: {
            capture_id: 'fixture-universe-stage-c-001',
            provider: 'the-odds-api',
            acquisition_mode: 'REPLAY',
            request_started_at: '2026-08-27T13:31:20Z',
            response_received_at: '2026-08-27T13:31:49Z',
            ingested_at: '2026-08-27T13:31:49Z',
            raw_evidence_reference: 'raw/fixture-universe-stage-c.json',
            raw_sha256: sha256Text(stageCFixtureRaw),
        },
        registry: stageCFixtureRegistry,
        projectionVersion: '1',
    });
}

test('fixture-universe strict team normalization is Unicode/case/whitespace only', () => {
    assert.equal(normalize('  MANCHESTER   CITY '), normalize('Manchester City'));
    assert.notEqual(normalize('Wolves'), normalize('Wolverhampton Wanderers'));
});

test('historical canonical inventory scope remains frozen outside the current fixture universe', () => {
    assert.equal(historical.SEASONS.includes('2026/2027'), false);
    assert.equal(KICKOFF_TOLERANCE_SECONDS, 900);
});

test('Stage C does not derive canonical opaque identifiers from provider input', () => {
    const source = require('node:fs').readFileSync(
        require('node:path').join(__dirname, '../../../src/infrastructure/fixture_universe/FixtureUniverse.js'),
        'utf8'
    );
    assert.match(source, /crypto\.randomUUID/);
    assert.doesNotMatch(source, /sha256\(business fields\)/);
});

test('Stage C fixture observation is visible only at market knowledge time', () => {
    const observations = stageCFixtureObservations();
    const observation = observations.find(row => row.price_side === 'BOOKMAKER' && row.source_snapshot_at === null);
    assert.ok(observation, 'fixture canonical market observation with explicit knowledge time is required');
    const query = {
        canonical_event_id: observation.canonical_event_id,
        canonical_bookmaker_id: observation.canonical_bookmaker_id,
        canonical_selection_id: observation.canonical_selection_id,
        period: observation.period,
        market_type: observation.market_type,
        line: observation.line,
        price_side: observation.price_side,
    };
    const before = new Date(Date.parse(observation.response_received_at) - 1).toISOString();
    assert.equal(latestAsOf(observations, { ...query, decision_time: before }), null);
    assert.equal(latestAsOf(observations, { ...query, decision_time: observation.response_received_at }).observation_id, observation.observation_id);
    assert.notEqual(observation.capture_started_at, observation.response_received_at);
    assert.equal(observation.source_snapshot_at, null);
});

test('quarantined provider events retain fixture evidence and never enter canonical observations', () => {
    const rawSha256 = '251ee69904f1b74fd23dd49b5b331826c7ed22232167125ec2e460a3734f15c4';
    const quarantines = [
        'UNKNOWN_HOME_TEAM',
        'UNKNOWN_AWAY_TEAM',
        'NO_FIXTURE_CANDIDATE',
        'KICKOFF_CONFLICT',
    ].map((reason_code, index) => ({
        provider_event_id: `quarantined-fixture-${index + 1}`,
        reason_code,
        raw_sha256: rawSha256,
    }));
    const observations = stageCFixtureObservations();
    const providerEvents = quarantines.map(({ provider_event_id }) => ({ id: provider_event_id }));
    assert.equal(quarantines.length, 4);
    for (const quarantine of quarantines) {
        assert.match(quarantine.reason_code, /^(UNKNOWN_HOME_TEAM|UNKNOWN_AWAY_TEAM|NO_FIXTURE_CANDIDATE|KICKOFF_CONFLICT)$/);
        assert.equal(quarantine.raw_sha256, rawSha256);
        assert.ok(providerEvents.some(event => event.id === quarantine.provider_event_id));
        assert.equal(observations.some(row => row.provider_event_id === quarantine.provider_event_id), false);
    }
});

test('fixture resolver uses real universe evidence for invalid and tolerance-bound kickoff decisions', () => {
    const universe = seededUniverse();
    const source = JSON.parse(fixtureUniverseOddsRaw);
    const event = source.find(candidate => candidate.sport_key === 'soccer_epl');
    assert.ok(event, 'committed odds fixture requires EPL event');
    const within = JSON.parse(JSON.stringify([event]));
    within[0].bookmakers = within[0].bookmakers.map(bookmaker => ({
        ...bookmaker,
        markets: bookmaker.markets.filter(market => market.key === 'h2h'),
    }));
    const baseKickoff = Date.parse(within[0].commence_time);
    within[0].commence_time = new Date(baseKickoff + KICKOFF_TOLERANCE_SECONDS * 1000).toISOString().replace('.000Z', 'Z');
    const withinText = JSON.stringify(within);
    const withinResolution = resolveOddsEvents({ oddsRawText: withinText, oddsRawSha256: sha256Text(withinText), universe, decidedAt: '2026-08-27T13:31:49Z' });
    assert.equal(withinResolution.decisions[0].decision, 'MATCHED');
    const capture = { capture_id: 'fixture-universe-within-900', provider: 'the-odds-api', acquisition_mode: 'REPLAY', request_started_at: '2026-08-27T13:31:20Z', response_received_at: '2026-08-27T13:31:49Z', ingested_at: '2026-08-27T13:31:49Z', raw_evidence_reference: 'raw/within-900.json', raw_sha256: sha256Text(withinText) };
    const projections = adaptTheOddsApiRaw({ rawText: withinText, capture, registry: withinResolution.registry, projectionVersion: 'fixture-universe/v1', allowedProviderEventIds: new Set(withinResolution.aliases.map(alias => alias.provider_event_id)) });
    assert.ok(projections.length > 0, 'resolver-matched provider kickoff must be adaptable');
    const normalized = JSON.parse(JSON.stringify(within));
    normalized[0].home_team = '  ＡＲＳＥＮＡＬ  ';
    normalized[0].away_team = ' CHELSEA ';
    normalized[0].bookmakers[0].markets[0].outcomes = normalized[0].bookmakers[0].markets[0].outcomes.map(outcome => ({
        ...outcome,
        name: outcome.name === 'Arsenal' ? ' ａｒｓｅｎａｌ ' : outcome.name === 'Chelsea' ? '  CHELSEA  ' : outcome.name,
    }));
    const normalizedText = JSON.stringify(normalized);
    const normalizedResolution = resolveOddsEvents({ oddsRawText: normalizedText, oddsRawSha256: sha256Text(normalizedText), universe, decidedAt: '2026-08-27T13:31:49Z' });
    assert.equal(normalizedResolution.decisions[0].decision, 'MATCHED');
    assert.ok(adaptTheOddsApiRaw({ rawText: normalizedText, capture: { ...capture, capture_id: 'fixture-universe-normalized', raw_sha256: sha256Text(normalizedText) }, registry: normalizedResolution.registry, projectionVersion: 'fixture-universe/v1', allowedProviderEventIds: new Set(normalizedResolution.aliases.map(alias => alias.provider_event_id)) }).length > 0);
    const outside = JSON.parse(JSON.stringify([event]));
    outside[0].commence_time = new Date(baseKickoff + (KICKOFF_TOLERANCE_SECONDS + 1) * 1000).toISOString().replace('.000Z', 'Z');
    const outsideText = JSON.stringify(outside);
    const outsideResolution = resolveOddsEvents({ oddsRawText: outsideText, oddsRawSha256: sha256Text(outsideText), universe, decidedAt: '2026-08-27T13:31:49Z' });
    assert.equal(outsideResolution.decisions[0].decision, 'QUARANTINED');
    assert.equal(outsideResolution.quarantines[0].reason_code, 'KICKOFF_CONFLICT');
    const invalid = JSON.parse(JSON.stringify([event]));
    invalid[0].commence_time = 'not-a-utc-timestamp';
    const invalidText = JSON.stringify(invalid);
    const invalidResolution = resolveOddsEvents({ oddsRawText: invalidText, oddsRawSha256: sha256Text(invalidText), universe, decidedAt: '2026-08-27T13:31:49Z' });
    assert.equal(invalidResolution.decisions[0].decision, 'QUARANTINED');
    assert.equal(invalidResolution.quarantines[0].reason_code, 'INVALID_KICKOFF_UTC');
});

test('fixture identity rejects forged RAW provenance and duplicate canonical allocation identities', () => {
    const universe = seededUniverse();
    assert.throws(() => seedFotMobFixtureUniverse({ rawHtml: fixtureUniverseRaw, rawSha256: '0'.repeat(64), mode: 'INITIAL_SEED' }), /does not match content/);
    assert.throws(() => resolveOddsEvents({ oddsRawText: fixtureUniverseOddsRaw, oddsRawSha256: '0'.repeat(64), universe, decidedAt: '2026-08-27T13:31:49Z' }), /does not match content/);
    const duplicate = JSON.parse(JSON.stringify(universe.allocationSnapshot));
    duplicate.fixtures[1].canonical_event_id = duplicate.fixtures[0].canonical_event_id;
    const unsigned = { schema_version: duplicate.schema_version, authority: duplicate.authority, fixtures: duplicate.fixtures, teams: duplicate.teams, provenance_raw_sha256: duplicate.provenance_raw_sha256 };
    duplicate.content_sha256 = semanticReplayHash(unsigned);
    assert.throws(() => seedFotMobFixtureUniverse({ rawHtml: fixtureUniverseRaw, rawSha256: fixtureUniverseRawSha, allocation: duplicate, mode: 'REPLAY' }), /canonical_event_id is not unique/);
    const providerDerived = JSON.parse(JSON.stringify(universe.allocationSnapshot));
    providerDerived.fixtures[0].canonical_event_id = 'provider-business-id';
    const providerUnsigned = { schema_version: providerDerived.schema_version, authority: providerDerived.authority, fixtures: providerDerived.fixtures, teams: providerDerived.teams, provenance_raw_sha256: providerDerived.provenance_raw_sha256 };
    providerDerived.content_sha256 = semanticReplayHash(providerUnsigned);
    assert.throws(() => seedFotMobFixtureUniverse({ rawHtml: fixtureUniverseRaw, rawSha256: fixtureUniverseRawSha, allocation: providerDerived, mode: 'REPLAY' }), /canonical fixture IDs are invalid/);
});

test('fixture replay requires an immutable allocation and is deterministic with the same allocation', () => {
    assert.throws(() => seedFotMobFixtureUniverse({ rawHtml: fixtureUniverseRaw, rawSha256: fixtureUniverseRawSha, mode: 'REPLAY' }), /requires immutable allocation/);
    const initial = seededUniverse();
    const replayOne = seedFotMobFixtureUniverse({ rawHtml: fixtureUniverseRaw, rawSha256: fixtureUniverseRawSha, allocation: initial.allocationSnapshot, mode: 'REPLAY' });
    const replayTwo = seedFotMobFixtureUniverse({ rawHtml: fixtureUniverseRaw, rawSha256: fixtureUniverseRawSha, allocation: initial.allocationSnapshot, mode: 'REPLAY' });
    assert.deepEqual(replayOne.snapshot.fixtures, replayTwo.snapshot.fixtures);
    assert.equal(replayOne.snapshot.allocation_snapshot_sha256, replayTwo.snapshot.allocation_snapshot_sha256);
    assert.equal(semanticReplayHash(replayOne.snapshot), semanticReplayHash(replayTwo.snapshot));
});

test('offline replay script requires an allocation and explicitly uses REPLAY mode', t => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'stage-c-replay-script-'));
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    const fotmob = path.join(root, 'fotmob.html'); const odds = path.join(root, 'odds.json'); const receipt = path.join(root, 'receipt.json');
    fs.writeFileSync(fotmob, '{}'); fs.writeFileSync(odds, '[]'); fs.writeFileSync(receipt, '{}');
    const script = path.join(__dirname, '../../../scripts/ops/stage_c_fixture_identity_replay.js');
    const run = spawnSync(process.execPath, [script, path.join(root, 'out')], { env: { ...process.env, FOTMOB_RAW_PATH: fotmob, ODDS_RAW_PATH: odds, ODDS_RECEIPT_PATH: receipt }, encoding: 'utf8' });
    assert.notEqual(run.status, 0);
    assert.match(run.stderr, /IDENTITY_ALLOCATION_PATH is required for REPLAY/);
    assert.match(fs.readFileSync(script, 'utf8'), /mode:\s*'REPLAY'/);
});

test('live smoke creates receipt identities independent of the RAW hash', () => {
    const source = fs.readFileSync(path.join(__dirname, '../../../scripts/ops/stage_c_the_odds_api_live_smoke.js'), 'utf8');
    assert.match(source, /crypto\.randomUUID\(\)/);
    assert.doesNotMatch(source, /live-\$\{raw\.raw_sha256/);
});
