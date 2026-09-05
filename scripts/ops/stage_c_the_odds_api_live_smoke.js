'use strict';

require('dotenv').config();

// The Odds API live entrypoint shares the exact transaction-v1 publication
// path with offline replay.  Network capture is opt-in; normal execution
// consumes the already captured evidence bundle and makes no provider call.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { createTheOddsApiClient } = require('../../src/infrastructure/market_evidence/theOddsApiClient');
const {
    loadOfflineEvidence,
    publishOfflineMarketEvidence,
} = require('../../src/infrastructure/market_evidence/offlinePipeline');
const {
    preparePreflight,
    executePreparedPreflight,
} = require('../../src/infrastructure/market_evidence/preflightRunner');

const evidenceRoot = path.resolve(process.env.STAGE_C_EVIDENCE_ROOT || 'data/market_evidence/live');
const defaultPaths = {
    fotmobRawPath: path.join(evidenceRoot, 'fotmob/raw/fotmob-fixtures-47-2026_2027-e8cfe0500b1b.html'),
    oddsRawPath: path.join(evidenceRoot, 'raw/251ee69904f1b74fd23dd49b5b331826c7ed22232167125ec2e460a3734f15c4.json'),
    receiptPath: path.join(evidenceRoot, 'receipts/live-251ee69904f1b74f.json'),
    allocationPath: path.join(evidenceRoot, 'fixture_identity/2026-08-27/allocation_snapshot.json'),
};

function summarizeBookmakers(rawText) {
    const payload = JSON.parse(rawText);
    const names = new Set();
    for (const event of payload) {
        for (const bookmaker of event.bookmakers || []) {
            names.add(String(bookmaker.title || bookmaker.key || '').trim());
        }
    }
    return [...names].filter(Boolean).sort();
}

function offlineInputPaths() {
    const values = {
        fotmobRawPath: process.env.STAGE_C_FOTMOB_RAW_PATH || defaultPaths.fotmobRawPath,
        oddsRawPath: process.env.STAGE_C_ODDS_RAW_PATH || defaultPaths.oddsRawPath,
        receiptPath: process.env.STAGE_C_ODDS_RECEIPT_PATH || defaultPaths.receiptPath,
        allocationPath: process.env.STAGE_C_IDENTITY_ALLOCATION_PATH || defaultPaths.allocationPath,
    };
    return Object.values(values).every(filePath => fs.existsSync(filePath)) ? values : null;
}

async function acquireOptInLiveEvidence() {
    if (process.env.STAGE_C_ALLOW_NETWORK !== 'yes') {
        throw new Error(
            'live network acquisition is disabled; provide existing offline evidence or set STAGE_C_ALLOW_NETWORK=yes'
        );
    }
    if (!process.env.THE_ODDS_API_KEY) {
        throw new Error('THE_ODDS_API_KEY is required for explicitly authorized live capture');
    }
    const request = { regions: 'uk', markets: 'h2h', oddsFormat: 'decimal' };
    const prepared = preparePreflight({
        rootDir: evidenceRoot,
        requestMetadata: request,
        credentialPresent: true,
        downstreamAvailable: true,
    });
    const client = createTheOddsApiClient();
    const captureId = `live-${crypto.randomUUID()}`;
    const persisted = await executePreparedPreflight({
        prepared,
        captureId,
        transport: async () => {
            const live = await client.capture(request);
            return {
                status: live.http_status,
                headers: live.provider_quota,
                body: live.rawText,
                receivedAt: live.response_received_at,
            };
        },
    });
    const paths = offlineInputPaths() || {};
    return {
        client,
        live: persisted,
        paths: { ...paths, oddsRawPath: persisted.persisted.rawPath, receiptPath: persisted.receiptPath },
    };
}

async function main() {
    const existing = offlineInputPaths();
    const capture = existing ? { paths: existing, client: null, live: null } : await acquireOptInLiveEvidence();
    const transactionRoot = path.resolve(
        process.env.STAGE_C_TRANSACTION_ROOT || path.join(evidenceRoot, 'transactions')
    );
    const allocationArtifactPath = path.resolve(
        process.env.STAGE_C_ALLOCATION_ARTIFACT_PATH || path.join(transactionRoot, 'allocation.authority.json')
    );
    const evidence = loadOfflineEvidence(capture.paths);
    const result = publishOfflineMarketEvidence({
        ...evidence,
        allocationArtifactPath,
        storeRoot: transactionRoot,
        projectionVersion: '1',
        supportedMarketKeys: ['h2h', 'h2h_lay'],
    });
    const summary = {
        acquisition_mode: evidence.receiptEvidence.receipt.acquisition_mode,
        network_acquisition_performed: capture.live !== null,
        live_api_request_count: capture.client?.request_count || 0,
        epl_events_returned: JSON.parse(evidence.oddsRawText).length,
        bookmakers_returned: summarizeBookmakers(evidence.oddsRawText),
        matched_decision_count: result.matched_decision_count,
        quarantined_decision_count: result.quarantined_decision_count,
        canonical_observation_count: result.observation_count,
        transaction_id: result.published.transaction_id,
        authority_head: result.freshAuthoritySnapshot.head_transaction_id,
        publisher_knowledge_time: result.knowledge_time,
    };
    process.stdout.write(`${JSON.stringify(summary)}\n`);
}

main().catch(error => {
    process.stderr.write(`STAGE_C_LIVE_SMOKE_FAILED=${error.message.replace(/https?:\/\/\S+/g, '[redacted-url]')}\n`);
    process.exitCode = 1;
});
