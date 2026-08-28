'use strict';
/* eslint-disable complexity -- identity resolution is deliberately explicit and fail-closed. */

// File-first Stage C fixture identity authority.  This deliberately does not
// depend on CanonicalInventoryContract: historical inventory and the current
// football world have distinct authorities.
const crypto = require('node:crypto');
const { extractNextData, extractFixtures, extractPageIdentity } = require('../fotmob/FotMobCandidateExporter');
const { sha256Text, stableStringify, compareUtcTimestamps, isUtcTimestamp } = require('../market_evidence/contracts');
const { createIdentityRegistry } = require('../market_evidence/identityRegistry');
const { KICKOFF_TOLERANCE_SECONDS, normalizeIdentityText } = require('./identityRules');

const SCHEMA_VERSION = 'footballprediction-fixture-universe/v1';
const REGISTRY_VERSION = 'fixture-identity-registry/v1';
const RULESET_VERSION = 'fixture-identity-ruleset/v1';
const RESOLVER_VERSION = 'fixture-identity-resolver/v1';
const COMPETITION_ID = 'cmp_epl';
const SEASON = '2026/2027';

function opaque(prefix, allocate) {
    const value = allocate ? allocate(prefix) : crypto.randomUUID().replaceAll('-', '');
    if (typeof value !== 'string' || !value) throw new Error('opaque ID allocator returned an invalid value');
    return `${prefix}_${value.replace(new RegExp(`^${prefix}_`), '')}`;
}
const normalize = normalizeIdentityText;
function semanticHash(value) { return sha256Text(stableStringify(value)); }
function secondsBetween(a, b) { return Math.abs(Date.parse(a) - Date.parse(b)) / 1000; }
function by(value, field) { return [...value].sort((a, b) => String(a[field]).localeCompare(String(b[field]))); }

function validateAllocationSnapshot(allocation, rawSha256) {
    if (!allocation || typeof allocation !== 'object' || Array.isArray(allocation)) throw new Error('REPLAY requires immutable allocation snapshot');
    const topLevel = ['schema_version', 'authority', 'fixtures', 'teams', 'provenance_raw_sha256', 'identity_ruleset_version', 'resolver_version', 'content_sha256'];
    if (Object.keys(allocation).some(key => !topLevel.includes(key))) throw new Error('allocation snapshot contains unknown field');
    if (allocation.schema_version !== 'fixture-identity-allocation/v1' || allocation.authority !== 'FootballPrediction') throw new Error('allocation snapshot schema is invalid');
    if (!/^[a-f0-9]{64}$/.test(allocation.content_sha256 || '') || allocation.identity_ruleset_version !== RULESET_VERSION || allocation.resolver_version !== RESOLVER_VERSION || allocation.content_sha256 !== semanticHash({ schema_version: allocation.schema_version, authority: allocation.authority, fixtures: allocation.fixtures, teams: allocation.teams, provenance_raw_sha256: allocation.provenance_raw_sha256, identity_ruleset_version: allocation.identity_ruleset_version, resolver_version: allocation.resolver_version })) throw new Error('allocation snapshot content hash is invalid');
    if (allocation.provenance_raw_sha256 !== rawSha256 || !Array.isArray(allocation.fixtures) || !Array.isArray(allocation.teams)) throw new Error('allocation snapshot provenance is invalid');
    for (const [rows, key] of [[allocation.fixtures, 'fotmob_event_id'], [allocation.teams, 'fotmob_name']]) {
        const values = rows.map(row => row?.[key]);
        if (values.some(value => typeof value !== 'string' || !value) || new Set(values).size !== values.length) throw new Error(`allocation snapshot ${key} is not unique`);
    }
    for (const key of ['canonical_fixture_id', 'canonical_event_id']) {
        const values = allocation.fixtures.map(row => row?.[key]);
        if (values.some(value => typeof value !== 'string' || !value) || new Set(values).size !== values.length) throw new Error(`allocation snapshot ${key} is not unique`);
    }
    const teamIds = allocation.teams.map(row => row?.canonical_team_id);
    if (teamIds.some(value => typeof value !== 'string' || !value) || new Set(teamIds).size !== teamIds.length) throw new Error('allocation snapshot canonical_team_id is not unique');
    if (allocation.fixtures.some(row => Object.keys(row || {}).some(key => !['fotmob_event_id', 'canonical_fixture_id', 'canonical_event_id'].includes(key)))) throw new Error('allocation fixture contains unknown field');
    if (allocation.teams.some(row => Object.keys(row || {}).some(key => !['fotmob_name', 'canonical_team_id', 'canonical_name'].includes(key)))) throw new Error('allocation team contains unknown field');
    if (allocation.fixtures.some(row => !/^fx_[A-Za-z0-9]+$/.test(row.canonical_fixture_id) || !/^evt_[A-Za-z0-9]+$/.test(row.canonical_event_id))) throw new Error('allocation snapshot canonical fixture IDs are invalid');
    if (allocation.teams.some(row => !/^team_[A-Za-z0-9]+$/.test(row.canonical_team_id) || typeof row.canonical_name !== 'string' || !row.canonical_name.trim())) throw new Error('allocation snapshot canonical team IDs are invalid');
    const normalizedTeams = allocation.teams.map(row => normalize(row.fotmob_name));
    if (normalizedTeams.some(value => !value) || new Set(normalizedTeams).size !== normalizedTeams.length) throw new Error('allocation snapshot normalized fotmob_name is not unique');
    return allocation;
}
function seedFotMobFixtureUniverse({ rawHtml, rawSha256, manifest, allocation = null, allocate = null, mode = 'INITIAL_SEED' }) {
    if (!/^[a-f0-9]{64}$/.test(rawSha256 || '')) throw new Error('FotMob raw SHA-256 is required');
    if (sha256Text(rawHtml) !== rawSha256) throw new Error('FotMob raw SHA-256 does not match content');
    const page = extractPageIdentity(extractNextData(rawHtml));
    const extracted = extractFixtures(extractNextData(rawHtml));
    if (page?.league_id !== '47' || page?.season_canonical !== SEASON || extracted.fixtures.length !== 380) {
        throw new Error('FotMob fixture evidence is not the authorized EPL 2026/2027 universe');
    }
    if (!['INITIAL_SEED', 'REPLAY'].includes(mode)) throw new Error('fixture seed mode is invalid');
    if (mode === 'INITIAL_SEED' && allocation !== null) throw new Error('INITIAL_SEED must not accept a replay allocation');
    if (mode === 'REPLAY' && allocate !== null) throw new Error('REPLAY must not accept an allocator');
    const validatedAllocation = mode === 'REPLAY' ? validateAllocationSnapshot(allocation, rawSha256) : allocation;
    if (mode === 'REPLAY') {
        const fixtureIds = new Set(extracted.fixtures.map(source => source.id));
        const teamNames = new Set(extracted.fixtures.flatMap(source => [normalize(source.home), normalize(source.away)]));
        if (validatedAllocation.fixtures.length !== fixtureIds.size || validatedAllocation.fixtures.some(row => !fixtureIds.has(row.fotmob_event_id))) throw new Error('REPLAY allocation fixture coverage is invalid');
        if (validatedAllocation.teams.length !== teamNames.size || validatedAllocation.teams.some(row => !teamNames.has(normalize(row.fotmob_name)))) throw new Error('REPLAY allocation team coverage is invalid');
    }
    const prior = new Map((validatedAllocation?.fixtures || []).map(row => [row.fotmob_event_id, row]));
    const priorTeams = new Map((validatedAllocation?.teams || []).map(row => [normalize(row.fotmob_name), row]));
    const teams = new Map();
    const fixtures = extracted.fixtures.map(source => {
        let row = prior.get(source.id);
        if (!row && mode === 'REPLAY') throw new Error(`REPLAY allocation missing fixture: ${source.id}`);
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
                if (!existingTeam && mode === 'REPLAY') throw new Error(`REPLAY allocation missing team: ${name}`);
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
    const allocationUnsigned = { schema_version: 'fixture-identity-allocation/v1', authority: 'FootballPrediction', fixtures: by(allocations, 'fotmob_event_id'), teams: by([...teams.values()].map(team => ({ fotmob_name: team.fotmob_name, canonical_team_id: team.canonical_team_id, canonical_name: team.canonical_name })), 'fotmob_name'), provenance_raw_sha256: rawSha256, identity_ruleset_version: RULESET_VERSION, resolver_version: RESOLVER_VERSION };
    const allocationSnapshot = { ...allocationUnsigned, content_sha256: semanticHash(allocationUnsigned) };
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

function resolveOddsEvents({ oddsRawText, oddsRawSha256, universe, decidedAt, decisionLedger = null, authorizedSupersessions = new Set() }) {
    if (sha256Text(oddsRawText) !== oddsRawSha256) throw new Error('Odds raw SHA-256 does not match content');
    const odds = JSON.parse(oddsRawText);
    if (!Array.isArray(odds) || semanticHash(oddsRawText) === '') throw new Error('Odds raw must be an array');
    const snapshot = universe.snapshot;
    const teamByName = new Map(universe.teamRegistry.teams.map(t => [normalize(t.canonical_name), t]));
    const fixtures = snapshot.fixtures;
    if (!isUtcTimestamp(decidedAt)) throw new Error('identity decision time must be UTC');
    if (!(authorizedSupersessions instanceof Set)) throw new Error('authorizedSupersessions must be a Set');
    const providerIds = odds.map(event => event?.id);
    if (providerIds.some(id => typeof id !== 'string' || !id) || new Set(providerIds).size !== providerIds.length) throw new Error('duplicate or invalid provider event identity in identity batch');
    const priorActive = decisionLedger ? decisionLedger.activeMappings() : new Map();
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
        if (!reason && !isUtcTimestamp(event.commence_time)) reason = 'INVALID_KICKOFF_UTC';
        const candidate = candidates[0]; const delta = candidate && !reason ? secondsBetween(candidate.scheduled_kickoff_utc, event.commence_time) : null;
        if (!reason && delta > KICKOFF_TOLERANCE_SECONDS) reason = 'KICKOFF_CONFLICT';
        const prior = priorActive.get(`the-odds-api\u0000${event.id}`) || null;
        if (reason) {
            const decision = { ...base, canonical_event_id: null, decision: 'QUARANTINED', method: 'LEVEL_2_FAIL_CLOSED', competition_match: event.sport_key === 'soccer_epl', season_evidence_status: 'NOT_PROVIDED', season_resolution_method: 'FIXTURE_UNIVERSE_CONTEXT', home_team_match: Boolean(home), away_team_match: Boolean(away), kickoff_delta_seconds: delta, candidate_count: candidates.length, quarantine_reason: reason };
            if (prior) decision.supersedes_decision_id = prior.decision_id || prior.identity_decision_id;
            decisions.push(decision); quarantines.push({ provider: 'the-odds-api', provider_event_id: event.id, reason_code: reason, candidate_count: candidates.length, evidence_refs: base.evidence_refs, ruleset_version: RULESET_VERSION, resolver_version: RESOLVER_VERSION, raw_sha256: oddsRawSha256, created_at: decidedAt });
        } else {
            if (prior && prior.canonical_event_id !== candidate.canonical_event_id && !authorizedSupersessions.has(event.id)) throw new Error(`identity mapping conflict requires authorized supersession: ${event.id}`);
            if (prior && prior.canonical_event_id === candidate.canonical_event_id) {
                decisions.push(prior);
                aliases.push({ provider: 'the-odds-api', provider_event_id: event.id, canonical_event_id: candidate.canonical_event_id, mapping_status: 'ACTIVE', mapping_method: 'IDENTITY_DECISION', evidence_raw_sha256: prior.raw_sha256 });
                continue;
            }
            const decision = { ...base, decision_id: base.identity_decision_id, canonical_event_id: candidate.canonical_event_id, decision: 'MATCHED', method: 'LEVEL_2_STRICT_FIXTURE', competition_match: true, season_evidence_status: 'NOT_PROVIDED', season_resolution_method: 'FIXTURE_UNIVERSE_CONTEXT', home_team_match: true, away_team_match: true, kickoff_delta_seconds: delta, candidate_count: 1, supersedes_decision_id: prior && prior.canonical_event_id !== candidate.canonical_event_id ? (prior.decision_id || prior.identity_decision_id) : null };
            decisions.push(decision);
            aliases.push({ provider: 'the-odds-api', provider_event_id: event.id, canonical_event_id: candidate.canonical_event_id, mapping_status: 'ACTIVE', mapping_method: 'IDENTITY_DECISION', evidence_raw_sha256: oddsRawSha256 });
        }
    }
    const registry = buildMarketIdentityRegistry({ universe, aliases, decisions, odds });
    if (decisionLedger) for (const decision of decisions) decisionLedger.append(decision);
    return Object.freeze({ decisions: by(decisions, 'candidate_provider_event_id'), quarantines: by(quarantines, 'provider_event_id'), aliases: by(aliases, 'provider_event_id'), registry, semantic_sha256: semanticHash(by(decisions.map(({ decided_at, ...row }) => row), 'candidate_provider_event_id')) });
}

function buildMarketIdentityRegistry({ universe, aliases, decisions, odds = [] }) {
    const fixtureByEvent = new Map(universe.snapshot.fixtures.map(f => [f.canonical_event_id, f]));
    const teamById = new Map(universe.teamRegistry.teams.map(t => [t.canonical_team_id, t]));
    const decisionByEvent = new Map(decisions.filter(d => d.decision === 'MATCHED').map(d => [d.candidate_provider_event_id, d]));
    const events = aliases.map(alias => { const f = fixtureByEvent.get(alias.canonical_event_id); const d = decisionByEvent.get(alias.provider_event_id); const source = odds.find(event => event.id === alias.provider_event_id); return { kind: 'event', provider: 'the-odds-api', provider_id: alias.provider_event_id, canonical_id: alias.canonical_event_id, season: f.season, home_team: teamById.get(f.canonical_home_team_id).canonical_name, away_team: teamById.get(f.canonical_away_team_id).canonical_name, kickoff_utc: f.scheduled_kickoff_utc, provider_observed_kickoff_utc: source.commence_time, identity_decision_id: d.identity_decision_id, identity_decision_status: 'MATCHED', identity_ruleset_version: RULESET_VERSION, provenance: 'fixture-universe/v1' }; });
    const bookmakerIds = [...new Set(odds.flatMap(event => (event.bookmakers || []).map(bookmaker => bookmaker.key)))].sort();
    // Team outcome labels are event-contextual (a club is HOME one week and
    // AWAY another); only Draw is a global provider selection alias.
    return createIdentityRegistry({ version: 'fixture-universe-market-registry/v1', allocation_snapshot: { authority: 'FootballPrediction', fixtures: universe.snapshot.fixtures, allocation_snapshot_sha256: universe.snapshot.allocation_snapshot_sha256 }, events, bookmakers: bookmakerIds.map(id => ({ kind: 'bookmaker', provider: 'the-odds-api', provider_id: id, canonical_id: `bookmaker:${id}`, price_side: 'BOOKMAKER', provenance: 'provider-evidence' })), markets: [{ kind: 'market', provider: 'the-odds-api', provider_id: 'h2h', canonical_id: 'MATCH/1X2/NULL', period: 'MATCH', market_type: '1X2', line: null, provenance: 'stage-c' }, { kind: 'market', provider: 'the-odds-api', provider_id: 'h2h_lay', canonical_id: 'MATCH/1X2/NULL', period: 'MATCH', market_type: '1X2', line: null, provenance: 'stage-c' }], selections: [{ kind: 'selection', provider: 'the-odds-api', provider_id: 'Draw', canonical_id: 'DRAW', selection: 'DRAW', provenance: 'stage-c' }] });
}

function semanticReplayHash(value) { return semanticHash(value); }
module.exports = { SCHEMA_VERSION, REGISTRY_VERSION, RULESET_VERSION, RESOLVER_VERSION, KICKOFF_TOLERANCE_SECONDS, normalize, seedFotMobFixtureUniverse, resolveOddsEvents, buildMarketIdentityRegistry, semanticReplayHash };
