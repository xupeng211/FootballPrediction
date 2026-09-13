'use strict';

// Synthetic governed authority for the Stage D backup tooling tests.
//
// The fixture is built by the repository's real publication pipeline rather
// than by hand.  A hand-built fixture would encode this module's assumptions
// about the authority contract, and a backup tool proved against its own
// assumptions proves nothing.  Running the real bootstrap, the real prospective
// builder and the real atomic publisher means the fixture is an authority the
// canonical reader accepts for the same reasons production is.
//
// Nothing here reads, copies or references production evidence.  Every root is
// a fresh temporary directory and every byte is generated in-process.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const { seedFotMobFixtureUniverse } = require('../../src/infrastructure/fixture_universe/FixtureUniverse');
const { persistVerifiedAllocationAuthority } = require('../../src/infrastructure/fixture_universe/AllocationAuthorityArtifact');
const { sha256Text } = require('../../src/infrastructure/market_evidence/contracts');
const { bootstrapMarketEvidenceTransactionStore } = require('../../src/infrastructure/market_evidence/transactionStore');
const { openMarketEvidenceAuthoritySnapshot } = require('../../src/infrastructure/market_evidence/authorityReader');
const { buildProspectiveMarketEvidenceTransaction } = require('../../src/infrastructure/market_evidence/prospectiveBatch');
const { publishProspectiveMarketEvidenceTransaction } = require('../../src/infrastructure/market_evidence/atomicPublisher');
const { initializeRequestAccountingEpoch, recordRequestIntent, markTransmissionStarted } = require('../../src/infrastructure/market_evidence/stageDOperations');
const { createVerifiedTestReceipt } = require('./market_evidence_authority');

const EPOCH_STARTED_AT = '2026-09-13T00:00:00Z';

// The universe gate accepts exactly the authorized 380-fixture shape, so the
// synthetic page carries 380 entries.  It is generated, not copied: only the
// shape is constrained, never the content.
function fixtureUniverseHtml() {
    const allMatches = Array.from({ length: 380 }, (_, index) => ({
        id: String(850000 + index),
        home: { name: index === 0 ? 'Arsenal' : `Home ${index}` },
        away: { name: index === 0 ? 'Chelsea' : `Away ${index}` },
        status: { utcTime: index === 0 ? '2026-09-12T15:00:00Z' : `2026-10-${String((index % 28) + 1).padStart(2, '0')}T15:00:00Z` },
    }));
    return `<script id="__NEXT_DATA__" type="application/json">${JSON.stringify({ query: { season: '2026/2027' }, props: { pageProps: { details: { id: 47 }, fixtures: { allMatches } } } })}</script>`;
}

function oddsRawText({ eventId, price }) {
    return JSON.stringify([{
        id: eventId,
        sport_key: 'soccer_epl',
        home_team: 'Arsenal',
        away_team: 'Chelsea',
        commence_time: '2026-09-12T15:00:00Z',
        bookmakers: [{ key: 'fixture', title: 'Fixture', markets: [{ key: 'h2h', outcomes: [{ name: 'Arsenal', price }, { name: 'Draw', price: 3 }, { name: 'Chelsea', price: 4 }] }] }],
    }]);
}

// Same key set as the governed quota configuration, with synthetic values.  The
// pre-epoch fields are carried verbatim because those two strings are the
// recorded state of the historical accounting uncertainty, not a tunable.
function syntheticQuotaConfiguration() {
    return Object.freeze({
        schema_version: 'footballprediction-stage-d-quota-budget/v2',
        provider: 'the-odds-api',
        subscription_tier: 'starter_free',
        quota_evidence_class: 'SYNTHETIC_FIXTURE',
        quota_evidence_verified: true,
        quota_evidence_source: 'synthetic offline backup fixture; no provider contact',
        billing_period_id: '2026-09',
        period_start_at: '2026-09-08T05:56:56Z',
        period_end_at: '2026-10-01T00:00:00Z',
        monthly_quota_limit: 500,
        reserved_safety_buffer: 50,
        automated_spend_limit: 450,
        max_requests_per_stage_d_run: 1,
        max_requests_per_day: null,
        stop_before_quota_exhaustion_threshold: 0,
        configured_markets: ['h2h'],
        configured_regions: ['uk'],
        market_count: 1,
        region_count: 1,
        expected_request_cost_credits: 1,
        max_provider_requests_per_cycle: 1,
        quota_reset_rule: 'PROVIDER_RECONCILED__NO_UNVERIFIED_AUTOMATIC_RESET',
        automatic_zero_on_calendar_change: false,
        historical_pre_epoch_request_total: 'AT_LEAST_2_CONFIRMED',
        historical_pre_epoch_exact_total: 'UNKNOWN',
        post_epoch_usage_source: 'read_from_durable_request_ledger',
    });
}

function createAllocationAndStore(root, rawHtml) {
    const initial = seedFotMobFixtureUniverse({ rawHtml, rawSha256: sha256Text(rawHtml), mode: 'INITIAL_SEED' });
    const allocationArtifactPath = path.join(root, 'allocation.authority.json');
    const persisted = persistVerifiedAllocationAuthority({ artifactPath: allocationArtifactPath, allocationAuthority: initial.allocationAuthority });
    const authorityRoot = path.join(root, 'transactions');
    bootstrapMarketEvidenceTransactionStore({ storeRoot: authorityRoot, allocationArtifactPath, bootstrapMetadata: { purpose: 'stage-d-backup-tooling-fixture' } });
    return { initial, allocationArtifactPath, authorityRoot };
}

function publishTransaction({ authorityRoot, allocationArtifactPath, initial, rawHtml, index }) {
    const eventId = `fixture-event-${index}`;
    const raw = oddsRawText({ eventId, price: 2 + index / 10 });
    const universe = seedFotMobFixtureUniverse({
        rawHtml,
        rawSha256: sha256Text(rawHtml),
        allocation: initial.allocationSnapshot,
        allocationAuthority: initial.allocationAuthority,
        mode: 'REPLAY',
    });
    const captureReceipt = createVerifiedTestReceipt({
        root: path.join(path.dirname(authorityRoot), 'receipts', `capture-${index}`),
        rawText: raw,
        overrides: { capture_id: `capture-${index}` },
    });
    const candidate = buildProspectiveMarketEvidenceTransaction({
        authoritySnapshot: openMarketEvidenceAuthoritySnapshot({ storeRoot: authorityRoot, allocationArtifactPath }),
        universe,
        oddsRawText: raw,
        captureReceipt,
    });
    return publishProspectiveMarketEvidenceTransaction({ storeRoot: authorityRoot, allocationArtifactPath, candidate });
}

// Real hash-chained ledger entries, written through the same API the runtime
// uses.  A hand-written entry file would not chain correctly, and a snapshot of
// a broken ledger would prove nothing about snapshotting a working one.
function appendFixtureLedgerEntry({ ledgerRoot, sequence }) {
    const requestId = `fixture-request-${String(sequence).padStart(4, '0')}`;
    const runId = 'fixture-run-0001';
    const at = `2026-09-13T00:${String(sequence).padStart(2, '0')}:00Z`;
    recordRequestIntent({ ledgerRoot, requestId, runId, createdAt: at, recordedAt: at });
    markTransmissionStarted({ ledgerRoot, requestId, transmittedAt: at, recordedAt: at });
    return requestId;
}

function buildBackupFixture({ root = null, transactionCount = 2, includeLedgerEntries = 0, writeQuotaConfigFile = true } = {}) {
    const resolvedRoot = root || fs.mkdtempSync(path.join(os.tmpdir(), 'stage-d-backup-fixture-'));
    const rawHtml = fixtureUniverseHtml();
    const { initial, allocationArtifactPath, authorityRoot } = createAllocationAndStore(resolvedRoot, rawHtml);
    const published = [];
    for (let index = 0; index < transactionCount; index += 1) published.push(publishTransaction({ authorityRoot, allocationArtifactPath, initial, rawHtml, index }));

    const ledgerRoot = path.join(resolvedRoot, 'request-accounting');
    const authority = openMarketEvidenceAuthoritySnapshot({ storeRoot: authorityRoot, allocationArtifactPath });
    initializeRequestAccountingEpoch({ ledgerRoot, authoritySnapshot: authority, startedAt: EPOCH_STARTED_AT, epochId: 'fixture-epoch-2026-09' });

    for (let index = 0; index < includeLedgerEntries; index += 1) appendFixtureLedgerEntry({ ledgerRoot, sequence: index + 1 });

    const quotaConfigPath = path.join(resolvedRoot, 'stage_d_quota_budget.json');
    if (writeQuotaConfigFile) fs.writeFileSync(quotaConfigPath, `${JSON.stringify(syntheticQuotaConfiguration(), null, 2)}\n`, { mode: 0o644 });

    return Object.freeze({
        root: resolvedRoot,
        authorityRoot,
        allocationArtifactPath,
        ledgerRoot,
        quotaConfigPath,
        published,
        head_transaction_id: authority.head_transaction_id,
        state_hash: authority.state_hash,
        observation_count: authority.observations.length,
        decision_count: authority.decisions.length,
        cleanup: () => fs.rmSync(resolvedRoot, { recursive: true, force: true }),
    });
}

module.exports = {
    EPOCH_STARTED_AT,
    buildBackupFixture,
    fixtureUniverseHtml,
    oddsRawText,
    syntheticQuotaConfiguration,
};
