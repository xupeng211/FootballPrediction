'use strict';

require('dotenv').config();

const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { API_HOST, createTheOddsApiClient, createTransportRequestFn } = require('../../src/infrastructure/market_evidence/theOddsApiClient');
const { loadIdentityRegistry } = require('../../src/infrastructure/market_evidence/identityRegistry');
const { adaptTheOddsApiCapture, buildCoverageEvidence } = require('../../src/infrastructure/market_evidence/theOddsApiAdapter');
const { sha256Text, stableStringify } = require('../../src/infrastructure/market_evidence/contracts');
const {
    writeImmutableRaw,
    readImmutableRaw,
    createCaptureReceipt,
    writeReceipt,
    writeCoverageEvidence,
    appendProjection,
} = require('../../src/infrastructure/market_evidence/evidenceStore');
const { replayRaw } = require('../../src/infrastructure/market_evidence/replay');

const evidenceRoot = path.resolve(process.env.STAGE_C_EVIDENCE_ROOT || 'data/market_evidence/live');
const registryPath = path.resolve('tests/fixtures/market_evidence/identity_registry.stage_c.v1.json');

function directConnectivity() {
    const requestFn = createTransportRequestFn();
    return new Promise((resolve, reject) => {
        const request = requestFn(`https://${API_HOST}/`, { headers: { 'User-Agent': 'FootballPrediction-stage-c-pilot/1.0' } }, response => {
            response.resume();
            response.on('end', () => resolve(response.statusCode || null));
            response.on('error', reject);
        });
        request.on('error', reject);
        request.end();
    });
}

function summarizeBookmakers(rawText) {
    const payload = JSON.parse(rawText);
    const names = new Set();
    for (const event of payload) {
        for (const bookmaker of event.bookmakers || []) names.add(String(bookmaker.title || bookmaker.key || '').trim());
    }
    return [...names].filter(Boolean).sort();
}

async function main() {
    if (!process.env.THE_ODDS_API_KEY) throw new Error('THE_ODDS_API_KEY is required');
    const connectivityStatus = await directConnectivity();
    const client = createTheOddsApiClient();
    const live = await client.capture({ regions: 'uk', markets: 'h2h', oddsFormat: 'decimal' });
    const captureId = `live-${crypto.randomUUID()}`;
    const raw = writeImmutableRaw({ rootDir: evidenceRoot, rawText: live.rawText });
    const receipt = createCaptureReceipt({
        capture_id: captureId,
        acquisition_mode: 'LIVE_CAPTURE',
        request_started_at: live.request_started_at,
        response_received_at: live.response_received_at,
        ingested_at: live.ingested_at,
        http_status: live.http_status,
        sanitized_request_parameters: { regions: 'uk', markets: 'h2h', oddsFormat: 'decimal' },
        response_size_bytes: live.response_size_bytes,
        raw_sha256: raw.raw_sha256,
        raw_evidence_reference: raw.raw_evidence_reference,
        provider_quota: live.provider_quota,
    });
    writeReceipt({ rootDir: evidenceRoot, receipt });
    const registry = loadIdentityRegistry(registryPath);
    let observations = [];
    let identityError = null;
    let processingError = null;
    let coverage;
    try {
        const projectionAvailableAt = new Date(Math.max(Date.now(), Date.parse(receipt.response_received_at) + 1)).toISOString();
        const adapted = adaptTheOddsApiCapture({ rawText: live.rawText, capture: receipt, registry, projectionVersion: '1', projectionAvailableAt });
        observations = adapted.observations;
        coverage = adapted.coverage_evidence;
    } catch (error) {
        if (/identity mapping|provider event identity conflicts|MATCHED identity decision/.test(error.message)) identityError = error.message;
        else processingError = error.message;
        coverage = error.coverage_evidence || buildCoverageEvidence({
            rawText: live.rawText,
            expectedProviderBookmakerIds: registry.list('bookmaker', 'the-odds-api').map(entry => entry.provider_id),
        });
    }
    writeCoverageEvidence({ rootDir: evidenceRoot, captureId, evidence: coverage });
    const ledgerPath = path.join(evidenceRoot, 'projections', `${captureId}.jsonl`);
    observations.forEach(projection => appendProjection({ ledgerPath, projection, registry }));
    const replay = observations.length
        ? [
            replayRaw({ rawPath: path.join(evidenceRoot, raw.raw_evidence_reference), capture: receipt, registry, projectionAvailableAt: receipt.ingested_at }),
            replayRaw({ rawPath: path.join(evidenceRoot, raw.raw_evidence_reference), capture: receipt, registry, projectionAvailableAt: receipt.ingested_at }),
        ]
        : [];
    const summary = {
        THE_ODDS_API_KEY_PRESENT: 'YES',
        THE_ODDS_API_DIRECT_CONNECTIVITY: 'PASS',
        connectivity_http_status: connectivityStatus,
        http_status: live.http_status,
        live_api_request_count: client.request_count,
        real_epl_events_returned: JSON.parse(live.rawText).length,
        live_bookmakers_returned: summarizeBookmakers(live.rawText),
        capture_id: captureId,
        raw_sha256: raw.raw_sha256,
        raw_sha256_reverify: sha256Text(readImmutableRaw({ rootDir: evidenceRoot, ...raw, expectedSha256: raw.raw_sha256 })) === raw.raw_sha256,
        real_canonical_observations: observations.length,
        real_quarantined_observations: identityError ? JSON.parse(live.rawText).length : 0,
        identity_fail_closed: identityError !== null,
        processing_fail_closed: processingError !== null,
        live_replay_1_sha256: replay[0] ? sha256Text(stableStringify(replay[0])) : null,
        live_replay_2_sha256: replay[1] ? sha256Text(stableStringify(replay[1])) : null,
    };
    process.stdout.write(`${JSON.stringify(summary)}\n`);
}

main().catch(error => {
    process.stderr.write(`STAGE_C_LIVE_SMOKE_FAILED=${error.message.replace(/https?:\/\/\S+/g, '[redacted-url]')}\n`);
    process.exitCode = 1;
});
