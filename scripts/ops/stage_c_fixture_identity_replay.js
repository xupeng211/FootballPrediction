'use strict';
// Offline-only Stage C projection: its inputs are immutable RAW already retained
// by the canonical collectors. It never makes a provider request.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { seedFotMobFixtureUniverse, resolveOddsEvents, semanticReplayHash } = require('../../src/infrastructure/fixture_universe/FixtureUniverse');
const { adaptTheOddsApiRaw } = require('../../src/infrastructure/market_evidence/theOddsApiAdapter');
const { createIdentityDecisionLedger } = require('../../src/infrastructure/fixture_universe/IdentityDecisionLedger');
const { appendProjection, readProjectionLedger } = require('../../src/infrastructure/market_evidence/evidenceStore');
function sha(file) { return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex'); }
function main() {
    const root = process.argv[2]; if (!root) throw new Error('usage: stage_c_fixture_identity_replay.js <evidence-output-dir>');
    const fotmob = process.env.FOTMOB_RAW_PATH; const odds = process.env.ODDS_RAW_PATH; const receipt = process.env.ODDS_RECEIPT_PATH;
    if (!fotmob || !odds || !receipt) throw new Error('offline raw and receipt paths are required');
    const fotmobRaw = fs.readFileSync(fotmob, 'utf8'); const oddsRaw = fs.readFileSync(odds, 'utf8'); const capture = JSON.parse(fs.readFileSync(receipt, 'utf8'));
    if (!process.env.IDENTITY_ALLOCATION_PATH) throw new Error('IDENTITY_ALLOCATION_PATH is required for REPLAY');
    const allocation = JSON.parse(fs.readFileSync(process.env.IDENTITY_ALLOCATION_PATH, 'utf8'));
    const universe = seedFotMobFixtureUniverse({ rawHtml: fotmobRaw, rawSha256: sha(fotmob), manifest: { raw_file_relative_path: path.basename(fotmob) }, allocation, mode: 'REPLAY' });
    fs.mkdirSync(root, { recursive: true });
    const decisionLedger = createIdentityDecisionLedger({ ledgerPath: path.join(root, 'identity_decisions.jsonl') });
    const resolution = resolveOddsEvents({ oddsRawText: oddsRaw, oddsRawSha256: sha(odds), universe, decidedAt: capture.response_received_at, decisionLedger });
    if (!process.env.PROJECTION_AVAILABLE_AT) throw new Error('PROJECTION_AVAILABLE_AT is required for REPLAY');
    const observations = adaptTheOddsApiRaw({ rawText: oddsRaw, capture, registry: resolution.registry, projectionVersion: 'fixture-universe/v1', projectionAvailableAt: process.env.PROJECTION_AVAILABLE_AT, allowedProviderEventIds: new Set(resolution.aliases.map(alias => alias.provider_event_id)), supportedMarketKeys: ['h2h', 'h2h_lay'] });
    const observationLedgerPath = path.join(root, 'market_observations.jsonl');
    observations.forEach(projection => appendProjection({ ledgerPath: observationLedgerPath, projection, registry: resolution.registry }));
    const ledgerObservations = readProjectionLedger({ ledgerPath: observationLedgerPath });
    const payload = { allocation_snapshot: universe.allocationSnapshot, competition_registry: universe.competitionRegistry, team_registry: universe.teamRegistry, fixture_universe: universe.snapshot, provider_event_aliases: resolution.aliases, identity_decisions: resolution.decisions, identity_quarantines: resolution.quarantines, identity_decision_semantic_sha256: resolution.semantic_sha256, market_observations: observations, market_projection_sha256: semanticReplayHash(observations.map(({ ingested_at, ...row }) => row)) };
    for (const [name, value] of Object.entries(payload)) fs.writeFileSync(path.join(root, `${name}.json`), `${JSON.stringify(value, null, 2)}\n`, { mode: 0o444 });
    const report = { fixture_count: universe.snapshot.fixtures.length, event_count: universe.snapshot.fixtures.length, odds_event_count: JSON.parse(oddsRaw).length, matched: resolution.aliases.length, quarantined: resolution.quarantines.length, observation_count: observations.length, identity_decision_ledger_count: decisionLedger.read().length, market_observation_ledger_count: ledgerObservations.length, hashes: Object.fromEntries(Object.keys(payload).filter(k => k.endsWith('_snapshot') || k.endsWith('_registry') || k === 'fixture_universe').map(k => [k, semanticReplayHash(payload[k])])), identity_replay_sha256: resolution.semantic_sha256, market_replay_sha256: payload.market_projection_sha256 };
    fs.writeFileSync(path.join(root, 'report.json'), `${JSON.stringify(report, null, 2)}\n`, { mode: 0o444 });
    process.stdout.write(`${JSON.stringify(report)}\n`);
}
main();
