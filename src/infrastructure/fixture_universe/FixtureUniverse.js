'use strict';
/* eslint-disable complexity -- identity resolution is deliberately explicit and fail-closed. */

// File-first Stage C fixture identity authority.  This deliberately does not
// depend on CanonicalInventoryContract: historical inventory and the current
// football world have distinct authorities.
const crypto = require('node:crypto');
const { extractNextData, extractFixtures, extractPageIdentity } = require('../fotmob/FotMobCandidateExporter');
const { sha256Text, stableStringify, compareUtcTimestamps } = require('../market_evidence/contracts');
const { createIdentityRegistry } = require('../market_evidence/identityRegistry');

const SCHEMA_VERSION = 'footballprediction-fixture-universe/v1';
const REGISTRY_VERSION = 'fixture-identity-registry/v1';
const RULESET_VERSION = 'fixture-identity-ruleset/v1';
const RESOLVER_VERSION = 'fixture-identity-resolver/v1';
const KICKOFF_TOLERANCE_SECONDS = 900;
const COMPETITION_ID = 'cmp_epl';
const SEASON = '2026/2027';

function opaque(prefix, allocate) {
    const value = allocate ? allocate(prefix) : crypto.randomUUID().replaceAll('-', '');
    if (typeof value !== 'string' || !value) throw new Error('opaque ID allocator returned an invalid value');
    return `${prefix}_${value.replace(new RegExp(`^${prefix}_`), '')}`;
}
function normalize(value) {
    return String(value || '').normalize('NFKC').trim().replace(/\s+/g, ' ').toLocaleLowerCase('en-US');
}
function semanticHash(value) { return sha256Text(stableStringify(value)); }
function secondsBetween(a, b) { return Math.abs(Date.parse(a) - Date.parse(b)) / 1000; }
function by(value, field) { return [...value].sort((a, b) => String(a[field]).localeCompare(String(b[field]))); }

function seedFotMobFixtureUniverse({ rawHtml, rawSha256, manifest, allocation = null, allocate = null }) {
    if (!/^[a-f0-9]{64}$/.test(rawSha256 || '')) throw new Error('FotMob raw SHA-256 is required');
    const page = extractPageIdentity(extractNextData(rawHtml));
    const extracted = extractFixtures(extractNextData(rawHtml));
    if (page?.league_id !== '47' || page?.season_canonical !== SEASON || extracted.fixtures.length !== 380) {
        throw new Error('FotMob fixture evidence is not the authorized EPL 2026/2027 universe');
    }
    const prior = new Map((allocation?.fixtures || []).map(row => [row.fotmob_event_id, row]));
    const priorTeams = new Map((allocation?.teams || []).map(row => [normalize(row.fotmob_name), row]));
    const teams = new Map();
    const fixtures = extracted.fixtures.map(source => {
        let row = prior.get(source.id);
        if (!row) {
            row = {
                fotmob_event_id: source.id,
                canonical_fixture_id: opaque('fx', allocate),
                canonical_event_id: opaque('evt', allocate),
            };
        }
        for (const name of [source.home, source.away]) {
            const key = normalize(name);
            if (!teams.has(key)) {
                const existingTeam = priorTeams.get(key);
                teams.set(key, existingTeam ? { ...existingTeam } : { canonical_team_id: opaque('team', allocate), canonical_name: name, fotmob_name: name });
            }
        }
        return {
            canonical_fixture_id: row.canonical_fixture_id,
            canonical_event_id: row.canonical_event_id,
            canonical_competition_id: COMPETITION_ID,
            season: SEASON,
            canonical_home_team_id: teams.get(normalize(source.home)).canonical_team_id,
            canonical_away_team_id: teams.get(normalize(source.away)).canonical_team_id,
            scheduled_kickoff_utc: source.kickoff,
            status: source.provider_status,
            provider_alias: { provider: 'fotmob', provider_event_id: source.id },
            capture_reference: manifest?.raw_file_relative_path || 'fotmob/raw',
            raw_sha256: rawSha256,
        };
    });
    const allocations = fixtures.map(fixture => ({
        fotmob_event_id: fixture.provider_alias.provider_event_id,
        canonical_fixture_id: fixture.canonical_fixture_id,
        canonical_event_id: fixture.canonical_event_id,
    }));
    const allocationSnapshot = { schema_version: 'fixture-identity-allocation/v1', authority: 'FootballPrediction', fixtures: by(allocations, 'fotmob_event_id'), teams: by([...teams.values()].map(team => ({ fotmob_name: team.fotmob_name, canonical_team_id: team.canonical_team_id, canonical_name: team.canonical_name })), 'fotmob_name') };
    const competitionRegistry = {
        schema_version: REGISTRY_VERSION, version: 'competition-registry/v1',
        competitions: [{ canonical_competition_id: COMPETITION_ID, name: 'English Premier League' }],
        aliases: [
            { provider: 'fotmob', provider_competition_id: '47', canonical_competition_id: COMPETITION_ID, evidence_raw_sha256: rawSha256 },
            { provider: 'the-odds-api', provider_competition_id: 'soccer_epl', canonical_competition_id: COMPETITION_ID, evidence_raw_sha256: null },
        ],
    };
    const teamRegistry = {
        schema_version: REGISTRY_VERSION, version: 'team-registry/v1',
        teams: by([...teams.values()], 'canonical_team_id'),
        aliases: by([...teams.values()].map(team => ({ provider: 'fotmob', provider_team_identity: team.fotmob_name, canonical_team_id: team.canonical_team_id, mapping_status: 'ACTIVE', mapping_method: 'SEED_EVIDENCE', evidence_raw_sha256: rawSha256 })), 'provider_team_identity'),
    };
    const snapshot = { schema_version: SCHEMA_VERSION, snapshot_id: `fus_${rawSha256.slice(0, 16)}`, authority: 'FootballPrediction Canonical Fixture Registry', initial_seed_source: 'fotmob', competition_seasons: [{ canonical_competition_id: COMPETITION_ID, season: SEASON }], fixtures: by(fixtures, 'canonical_fixture_id'), allocation_snapshot_sha256: semanticHash(allocationSnapshot), competition_registry_version: competitionRegistry.version, team_registry_version: teamRegistry.version, projection_version: '1' };
    return Object.freeze({ snapshot, allocationSnapshot, competitionRegistry, teamRegistry, extractionAudit: extracted.audit });
}

function resolveOddsEvents({ oddsRawText, oddsRawSha256, universe, decidedAt }) {
    const odds = JSON.parse(oddsRawText);
    if (!Array.isArray(odds) || semanticHash(oddsRawText) === '') throw new Error('Odds raw must be an array');
    const snapshot = universe.snapshot;
    const teamByName = new Map(universe.teamRegistry.teams.map(t => [normalize(t.canonical_name), t]));
    const fixtures = snapshot.fixtures;
    const decisions = [], quarantines = [], aliases = [];
    for (const event of odds) {
        const base = { identity_decision_id: opaque('idn', () => crypto.createHash('sha256').update(`decision|${event.id}|${oddsRawSha256}`).digest('hex').slice(0, 24)), candidate_provider: 'the-odds-api', candidate_provider_event_id: event.id, ruleset_version: RULESET_VERSION, resolver_version: RESOLVER_VERSION, decided_at: decidedAt, raw_sha256: oddsRawSha256, evidence_refs: [snapshot.snapshot_id, event.id] };
        let reason = null;
        if (event.sport_key !== 'soccer_epl') reason = 'UNKNOWN_COMPETITION';
        const home = teamByName.get(normalize(event.home_team)); const away = teamByName.get(normalize(event.away_team));
        if (!reason && !home) reason = 'UNKNOWN_HOME_TEAM';
        if (!reason && !away) reason = 'UNKNOWN_AWAY_TEAM';
        const candidates = !reason ? fixtures.filter(f => f.canonical_home_team_id === home.canonical_team_id && f.canonical_away_team_id === away.canonical_team_id && f.canonical_competition_id === COMPETITION_ID && f.season === SEASON) : [];
        if (!reason && candidates.length === 0) reason = 'NO_FIXTURE_CANDIDATE';
        if (!reason && candidates.length > 1) reason = 'MULTIPLE_FIXTURE_CANDIDATES';
        const candidate = candidates[0]; const delta = candidate ? secondsBetween(candidate.scheduled_kickoff_utc, event.commence_time) : null;
        if (!reason && delta > KICKOFF_TOLERANCE_SECONDS) reason = 'KICKOFF_CONFLICT';
        if (reason) {
            const decision = { ...base, canonical_event_id: null, decision: 'QUARANTINED', method: 'LEVEL_2_FAIL_CLOSED', competition_match: event.sport_key === 'soccer_epl', season_evidence_status: 'NOT_PROVIDED', season_resolution_method: 'FIXTURE_UNIVERSE_CONTEXT', home_team_match: Boolean(home), away_team_match: Boolean(away), kickoff_delta_seconds: delta, candidate_count: candidates.length, quarantine_reason: reason };
            decisions.push(decision); quarantines.push({ provider: 'the-odds-api', provider_event_id: event.id, reason_code: reason, candidate_count: candidates.length, evidence_refs: base.evidence_refs, ruleset_version: RULESET_VERSION, resolver_version: RESOLVER_VERSION, raw_sha256: oddsRawSha256, created_at: decidedAt });
        } else {
            decisions.push({ ...base, canonical_event_id: candidate.canonical_event_id, decision: 'MATCHED', method: 'LEVEL_2_STRICT_FIXTURE', competition_match: true, season_evidence_status: 'NOT_PROVIDED', season_resolution_method: 'FIXTURE_UNIVERSE_CONTEXT', home_team_match: true, away_team_match: true, kickoff_delta_seconds: delta, candidate_count: 1 });
            aliases.push({ provider: 'the-odds-api', provider_event_id: event.id, canonical_event_id: candidate.canonical_event_id, mapping_status: 'ACTIVE', mapping_method: 'IDENTITY_DECISION', evidence_raw_sha256: oddsRawSha256 });
        }
    }
    const registry = buildMarketIdentityRegistry({ universe, aliases, decisions, odds });
    return Object.freeze({ decisions: by(decisions, 'candidate_provider_event_id'), quarantines: by(quarantines, 'provider_event_id'), aliases: by(aliases, 'provider_event_id'), registry, semantic_sha256: semanticHash(by(decisions.map(({ decided_at, ...row }) => row), 'candidate_provider_event_id')) });
}

function buildMarketIdentityRegistry({ universe, aliases, decisions, odds = [] }) {
    const fixtureByEvent = new Map(universe.snapshot.fixtures.map(f => [f.canonical_event_id, f]));
    const teamById = new Map(universe.teamRegistry.teams.map(t => [t.canonical_team_id, t]));
    const decisionByEvent = new Map(decisions.filter(d => d.decision === 'MATCHED').map(d => [d.candidate_provider_event_id, d]));
    const events = aliases.map(alias => { const f = fixtureByEvent.get(alias.canonical_event_id); const d = decisionByEvent.get(alias.provider_event_id); return { kind: 'event', provider: 'the-odds-api', provider_id: alias.provider_event_id, canonical_id: alias.canonical_event_id, season: f.season, home_team: teamById.get(f.canonical_home_team_id).canonical_name, away_team: teamById.get(f.canonical_away_team_id).canonical_name, kickoff_utc: f.scheduled_kickoff_utc, identity_decision_id: d.identity_decision_id, identity_ruleset_version: RULESET_VERSION, provenance: 'fixture-universe/v1' }; });
    const bookmakerIds = [...new Set(odds.flatMap(event => (event.bookmakers || []).map(bookmaker => bookmaker.key)))].sort();
    // Team outcome labels are event-contextual (a club is HOME one week and
    // AWAY another); only Draw is a global provider selection alias.
    return createIdentityRegistry({ version: 'fixture-universe-market-registry/v1', events, bookmakers: bookmakerIds.map(id => ({ kind: 'bookmaker', provider: 'the-odds-api', provider_id: id, canonical_id: `bookmaker:${id}`, price_side: 'BOOKMAKER', provenance: 'provider-evidence' })), markets: [{ kind: 'market', provider: 'the-odds-api', provider_id: 'h2h', canonical_id: 'MATCH/1X2/NULL', period: 'MATCH', market_type: '1X2', line: null, provenance: 'stage-c' }, { kind: 'market', provider: 'the-odds-api', provider_id: 'h2h_lay', canonical_id: 'MATCH/1X2/NULL', period: 'MATCH', market_type: '1X2', line: null, provenance: 'stage-c' }], selections: [{ kind: 'selection', provider: 'the-odds-api', provider_id: 'Draw', canonical_id: 'DRAW', selection: 'DRAW', provenance: 'stage-c' }] });
}

function semanticReplayHash(value) { return semanticHash(value); }
module.exports = { SCHEMA_VERSION, REGISTRY_VERSION, RULESET_VERSION, RESOLVER_VERSION, KICKOFF_TOLERANCE_SECONDS, normalize, seedFotMobFixtureUniverse, resolveOddsEvents, buildMarketIdentityRegistry, semanticReplayHash };
