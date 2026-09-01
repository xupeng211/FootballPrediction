'use strict';

// 离线 replay 只消费已有 immutable RAW、receipt、FotMob allocation；不发起
// provider 请求，也不再向旧 identity/observation JSONL 写入 authoritative state。
const fs = require('node:fs');
const path = require('node:path');
const { loadOfflineEvidence, publishOfflineMarketEvidence } = require('../../src/infrastructure/market_evidence/offlinePipeline');

function main() {
    const outputRoot = process.argv[2];
    if (!outputRoot) throw new Error('usage: stage_c_fixture_identity_replay.js <evidence-output-dir>');
    const allocationPath = process.env.IDENTITY_ALLOCATION_PATH;
    if (!allocationPath) throw new Error('IDENTITY_ALLOCATION_PATH is required for REPLAY');
    if (process.env.PROJECTION_AVAILABLE_AT) throw new Error('PROJECTION_AVAILABLE_AT is publisher-owned and cannot be supplied for REPLAY');
    const evidence = loadOfflineEvidence({
        fotmobRawPath: process.env.FOTMOB_RAW_PATH,
        oddsRawPath: process.env.ODDS_RAW_PATH,
        receiptPath: process.env.ODDS_RECEIPT_PATH,
        allocationPath,
    });
    const root = path.resolve(outputRoot);
    fs.mkdirSync(root, { recursive: true });
    const result = publishOfflineMarketEvidence({
        ...evidence,
        allocationArtifactPath: path.join(root, 'allocation.authority.json'),
        storeRoot: path.join(root, 'transactions'),
        projectionVersion: 'fixture-universe/v1',
        supportedMarketKeys: ['h2h', 'h2h_lay'],
    });
    const summary = {
        mode: 'REPLAY',
        fixture_count: evidence.allocationSnapshot.fixtures.length,
        odds_event_count: JSON.parse(evidence.oddsRawText).length,
        matched_decision_count: result.matched_decision_count,
        quarantined_decision_count: result.quarantined_decision_count,
        observation_count: result.observation_count,
        transaction_id: result.published.transaction_id,
        authority_head: result.freshAuthoritySnapshot.head_transaction_id,
        publisher_knowledge_time: result.knowledge_time,
    };
    process.stdout.write(`${JSON.stringify(summary)}\n`);
}

main();
