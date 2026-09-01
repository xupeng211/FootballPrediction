'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { seedFotMobFixtureUniverse, resolveOddsEvents } = require('../../src/infrastructure/fixture_universe/FixtureUniverse');
const { createIdentityDecisionLedger } = require('../../src/infrastructure/fixture_universe/IdentityDecisionLedger');
const { sha256Text } = require('../../src/infrastructure/market_evidence/contracts');
const { createCaptureReceipt, writeReceipt, loadVerifiedCaptureReceipt } = require('../../src/infrastructure/market_evidence/evidenceStore');

function fixtureUniverseHtml() {
    const allMatches = Array.from({ length: 380 }, (_, index) => ({
        id: String(800000 + index),
        home: { name: index === 0 ? 'Arsenal' : `Home ${index}` },
        away: { name: index === 0 ? 'Chelsea' : `Away ${index}` },
        status: { utcTime: index === 0 ? '2026-09-12T15:00:00Z' : `2026-10-${String((index % 28) + 1).padStart(2, '0')}T15:00:00Z` },
    }));
    return `<script id="__NEXT_DATA__" type="application/json">${JSON.stringify({ query: { season: '2026/2027' }, props: { pageProps: { details: { id: 47 }, fixtures: { allMatches } } } })}</script>`;
}

function createGovernedFixtureTestContext({ rawText, decidedAt = '2026-08-27T13:31:49Z' }) {
    const rawHtml = fixtureUniverseHtml();
    const universe = seedFotMobFixtureUniverse({ rawHtml, rawSha256: sha256Text(rawHtml), mode: 'INITIAL_SEED' });
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'market-evidence-governed-'));
    const decisionLedger = createIdentityDecisionLedger({ ledgerPath: path.join(root, 'identity-decisions.jsonl'), allocationAuthority: universe.allocationAuthority });
    const resolution = resolveOddsEvents({ oddsRawText: rawText, oddsRawSha256: sha256Text(rawText), universe, decidedAt, decisionLedger });
    return Object.freeze({ root, universe, decisionLedger, resolution, registry: resolution.registry, canonicalEventId: resolution.aliases[0]?.canonical_event_id ?? null, cleanup: () => fs.rmSync(root, { recursive: true, force: true }) });
}

function createVerifiedTestReceipt({ root, rawText, overrides = {} }) {
    const receipt = createCaptureReceipt({
        provider: 'the-odds-api',
        capture_id: 'test-capture',
        acquisition_mode: 'HISTORICAL_FILE',
        request_started_at: '2026-08-27T13:31:20Z',
        response_received_at: '2026-08-27T13:31:49Z',
        ingested_at: '2026-08-27T13:31:49Z',
        http_status: 200,
        sanitized_request_parameters: { regions: 'uk', markets: 'h2h', oddsFormat: 'decimal' },
        response_size_bytes: Buffer.byteLength(rawText, 'utf8'),
        raw_sha256: sha256Text(rawText),
        raw_evidence_reference: `raw/${sha256Text(rawText)}.json`,
        ...overrides,
    });
    const receiptPath = writeReceipt({ rootDir: root, receipt });
    return loadVerifiedCaptureReceipt({ receiptPath });
}

module.exports = { createGovernedFixtureTestContext, createVerifiedTestReceipt };
