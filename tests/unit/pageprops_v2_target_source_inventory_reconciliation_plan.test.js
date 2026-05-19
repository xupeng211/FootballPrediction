'use strict';
/* eslint-disable max-lines -- safety-contract coverage stays in one file for auditability. */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const pg = require('pg');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/pageprops_v2_target_source_inventory_reconciliation_plan.js');
const RAW_WRITE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/renewed_pageprops_v2_raw_write_execute.js');

function loadFreshModule() {
    delete require.cache[require.resolve(MODULE_PATH)];
    return require(MODULE_PATH);
}

const mod = loadFreshModule();
const rawWrite = require(RAW_WRITE_PATH);

const MISMATCH_IDS = Object.freeze([
    '4830466',
    '4830461',
    '4830481',
    '4830496',
    '4830511',
    '4830463',
    '4830465',
    '4830508',
]);

const OBSERVED = Object.freeze({
    4830466: [
        '4830759',
        'Marseille',
        'Rennes',
        '2026-05-17T19:00:00.000Z',
        '34',
        '/matches/marseille-vs-rennes/2t9n7h',
    ],
    4830461: ['4830758', 'Lyon', 'Lens', '2026-05-17T19:00:00.000Z', '34', '/matches/lens-vs-lyon/2s3gtg'],
    4830481: [
        '4830763',
        'Strasbourg',
        'Monaco',
        '2026-05-17T19:00:00.000Z',
        '34',
        '/matches/monaco-vs-strasbourg/379ruz',
    ],
    4830496: [
        '4830757',
        'Lorient',
        'Le Havre',
        '2026-05-17T19:00:00.000Z',
        '34',
        '/matches/lorient-vs-le-havre/2t6haw',
    ],
    4830511: ['4830760', 'Nantes', 'Toulouse', '2026-05-17T19:00:00.000Z', '34', '/matches/nantes-vs-toulouse/38dikf'],
    4830463: ['4830622', 'Le Havre', 'Monaco', '2026-01-24T18:00:00.000Z', '19', '/matches/le-havre-vs-monaco/362v61'],
    4830465: ['4830619', 'Toulouse', 'Nice', '2026-01-17T18:00:00.000Z', '18', '/matches/nice-vs-toulouse/38dxtn'],
    4830508: [
        '4830620',
        'Auxerre',
        'Paris Saint-Germain',
        '2026-01-23T19:00:00.000Z',
        '19',
        '/matches/auxerre-vs-paris-saint-germain/2t4i9k',
    ],
});

function targetFields(externalId) {
    const base = {
        4830466: ['Rennes', 'Marseille', '2025-08-15T18:45:00.000Z'],
        4830461: ['Lens', 'Lyon', '2025-08-16T15:00:00.000Z'],
        4830481: ['Monaco', 'Strasbourg', '2025-08-31T15:15:00.000Z'],
        4830496: ['Le Havre', 'Lorient', '2025-09-21T15:15:00.000Z'],
        4830511: ['Toulouse', 'Nantes', '2025-09-27T17:00:00.000Z'],
        4830463: ['Monaco', 'Le Havre', '2025-08-16T17:00:00.000Z'],
        4830465: ['Nice', 'Toulouse', '2025-08-16T19:05:00.000Z'],
        4830508: ['Paris Saint-Germain', 'Auxerre', '2025-09-27T19:05:00.000Z'],
    };
    return base[externalId];
}

function candidate(externalId, overrides = {}) {
    const [home, away, matchDate] = targetFields(externalId) || [
        `Home ${externalId}`,
        `Away ${externalId}`,
        '2025-08-15T18:45:00.000Z',
    ];
    return {
        target_id: `${mod.BATCH_ID}:53_20252026_${externalId}`,
        batch_id: mod.BATCH_ID,
        source: 'fotmob',
        route: 'html_hydration',
        raw_data_version: 'fotmob_pageprops_v2',
        hash_strategy: 'stable_pageprops_payload_v1',
        match_id: `53_20252026_${externalId}`,
        external_id: externalId,
        league_id: 53,
        league_name: 'Ligue 1',
        season: '2025/2026',
        home_team: home,
        away_team: away,
        kickoff_time: matchDate,
        match_date: matchDate,
        status: 'finished',
        preflight_status: 'hash_baseline_ready',
        baseline_hash: 'a'.repeat(64),
        matches_seed_status: 'inserted_matches_identity',
        source_inventory_route: 'source_inventory',
        ...overrides,
    };
}

function candidates50() {
    const filler = Array.from({ length: 42 }, (_, index) => String(4900000 + index));
    return [...MISMATCH_IDS, ...filler].map(externalId => candidate(externalId));
}

function knownCompleted() {
    return ['4830746', '4830747', '4830748', '4830750', '4830751', '4830752', '4830753', '4830754'].map(externalId => ({
        target_id: `${mod.BATCH_ID}:53_20252026_${externalId}`,
        external_id: externalId,
        match_id: `53_20252026_${externalId}`,
    }));
}

function manifest(overrides = {}) {
    return {
        batch_id: mod.BATCH_ID,
        source: 'fotmob',
        route: 'html_hydration',
        raw_data_version: 'fotmob_pageprops_v2',
        hash_strategy: 'stable_pageprops_payload_v1',
        league: { league_id: 53, league_name: 'Ligue 1', season: '2025/2026' },
        known_completed_targets: knownCompleted(),
        candidate_targets: candidates50(),
        phase_5_21_l2v3c_planning_status: 'completed_no_write',
        phase_5_21_l2v3c_metadata_target_mismatch_count: 8,
        renewed_baseline_requires_separate_baseline_acceptance: true,
        renewed_baseline_requires_separate_final_db_write_authorization: true,
        raw_write_ready_for_execution: false,
        next_required_step: 'target_identity_source_inventory_reconciliation_planning',
        phase_5_21_l2v3d_planning_status: 'completed_no_write',
        phase_5_21_l2v3d_identity_mismatch_count: 8,
        phase_5_21_l2v3d_manifest_target_metadata_mismatch_indicated: true,
        target_identity_mismatch_blocks_baseline_acceptance: true,
        raw_write_retry_authorization_status: 'blocked_pending_target_identity_reconciliation',
        ...overrides,
    };
}

function proposalTarget(externalId, overrides = {}) {
    const observed = OBSERVED[externalId];
    return {
        target_id: `${mod.BATCH_ID}:53_20252026_${externalId}`,
        match_id: `53_20252026_${externalId}`,
        external_id: externalId,
        hash_status: 'metadata_target_mismatch',
        metadata_identity_status: 'metadata_target_mismatch',
        attempts: [
            {
                metadata_identity_observed: {
                    external_id: observed?.[0] || externalId,
                    home_team: observed?.[1] || `Home ${externalId}`,
                    away_team: observed?.[2] || `Away ${externalId}`,
                    match_time_utc: observed?.[3] || '2025-08-15T18:45:00.000Z',
                },
            },
        ],
        ...overrides,
    };
}

function renewedProposal(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3C',
        no_write: true,
        db_write_performed: false,
        raw_insert_performed: false,
        summary: {
            metadata_target_mismatch_count: 8,
            next_required_step: 'target_identity_reconciliation_planning',
        },
        recommendation: {
            raw_write_ready_for_execution: false,
            requires_separate_baseline_acceptance: true,
            requires_separate_final_db_write_authorization: true,
        },
        checked_targets: MISMATCH_IDS.map(externalId => proposalTarget(externalId)),
        ...overrides,
    };
}

function sourceInventoryJson() {
    const requested = MISMATCH_IDS.map((externalId, index) => {
        const [home, away, matchDate] = targetFields(externalId);
        return {
            id: externalId,
            home: { name: home },
            away: { name: away },
            status: { utcTime: matchDate, finished: true },
            round: String(index + 1),
            roundName: String(index + 1),
            pageUrl: `${OBSERVED[externalId][5]}#${externalId}`,
        };
    });
    const observed = MISMATCH_IDS.map(externalId => ({
        id: OBSERVED[externalId][0],
        home: { name: OBSERVED[externalId][1] },
        away: { name: OBSERVED[externalId][2] },
        status: { utcTime: OBSERVED[externalId][3], finished: true },
        round: OBSERVED[externalId][4],
        roundName: OBSERVED[externalId][4],
        pageUrl: `${OBSERVED[externalId][5]}#${OBSERVED[externalId][0]}`,
    }));
    return {
        overview: {
            matches: {
                allMatches: [...requested, ...observed],
            },
        },
    };
}

function dbSnapshot(overrides = {}) {
    return {
        row_counts: {
            matches: 60,
            raw_match_data: 18,
            bookmaker_odds_history: 2,
            l3_features: 2,
            match_features_training: 2,
            predictions: 2,
        },
        target_rows: MISMATCH_IDS.map(externalId => {
            const [home, away, matchDate] = targetFields(externalId);
            return {
                match_id: `53_20252026_${externalId}`,
                external_id: externalId,
                league_name: 'Ligue 1',
                season: '2025/2026',
                home_team: home,
                away_team: away,
                match_date: matchDate,
                status: 'finished',
                data_source: 'fotmob',
                pipeline_status: 'pending',
            };
        }),
        candidate_v2_rows_count: 0,
        ...overrides,
    };
}

function validInput(overrides = {}) {
    return {
        manifest: mod.MANIFEST_PATH,
        renewedProposal: mod.RENEWED_PROPOSAL_PATH,
        reportOutput: mod.REPORT_PATH,
        source: 'fotmob',
        leagueId: 53,
        leagueName: 'Ligue 1',
        season: '2025/2026',
        rawVersion: 'fotmob_pageprops_v2',
        hashStrategy: 'stable_pageprops_payload_v1',
        batchId: mod.BATCH_ID,
        targetCount: 50,
        planningAuthorization: true,
        sourceInventoryReconciliationAuthorization: true,
        networkAuthorization: true,
        allowDbWrite: false,
        allowRawMatchDataWrite: false,
        allowControlledWrite: false,
        allowMatchesWrite: false,
        allowBookmakerOddsWrite: false,
        allowFeatureWrite: false,
        allowSchemaMigration: false,
        allowParserImplementation: false,
        allowFeatureExtraction: false,
        allowTraining: false,
        allowPrediction: false,
        allowBrowserRuntime: false,
        allowProxyRuntime: false,
        printFullBody: false,
        saveFullBody: false,
        printFullJson: false,
        saveFullJson: false,
        printFullPageprops: false,
        saveFullPageprops: false,
        retry: 0,
        requestDelayMs: 0,
        generatedAt: '2026-05-18T00:00:00.000Z',
        branch: 'data/pageprops-v2-source-inventory-reconciliation-phase521l2v3e',
        baseHead: 'd2db9e9f9276a130de52bad724be3a7bc6566481',
        mainHead: 'd2db9e9f9276a130de52bad724be3a7bc6566481',
        mainCiStatus: 'success',
        pr1278State: 'MERGED',
        pr1278MergeCommit: 'd2db9e9f9276a130de52bad724be3a7bc6566481',
        ...overrides,
    };
}

test('valid L2V3E run stays no-write and identifies schedule/detail identity mismatch with high confidence', async () => {
    const writes = [];
    const result = await mod.runPlanning(validInput(), {
        manifest: manifest(),
        renewedProposal: renewedProposal(),
        sourceInventoryJson: sourceInventoryJson(),
        dbSnapshot: dbSnapshot(),
        writeJsonFile: (filePath, data) => writes.push({ filePath, data }),
        writeReportFile: (filePath, data) => writes.push({ filePath, data }),
    });

    assert.equal(result.ok, true);
    assert.equal(result.summary.no_write, true);
    assert.equal(result.summary.db_write_performed, false);
    assert.equal(result.summary.raw_insert_performed, false);
    assert.equal(result.summary.checked_target_count, 8);
    assert.equal(result.summary.identity_mismatch_count, 8);
    assert.equal(result.summary.source_inventory_vs_manifest_mismatch_count, 0);
    assert.equal(result.summary.manifest_vs_db_mismatch_count, 0);
    assert.equal(result.summary.db_vs_live_observed_mismatch_count, 8);
    assert.equal(result.summary.requested_vs_observed_external_id_mismatch_count, 8);
    assert.equal(result.summary.shared_page_url_base_pair_count, 8);
    assert.equal(result.summary.all_pairs_share_page_url_base, true);
    assert.equal(
        result.summary.source_inventory_request_url,
        'https://www.fotmob.com/api/data/leagues?id=53&season=20252026'
    );
    assert.equal(result.summary.suspected_root_cause, 'schedule_vs_detail_external_id_mismatch');
    assert.equal(result.summary.root_cause_confidence, 'high');
    assert.equal(result.summary.recommended_next_step, 'schedule_detail_identity_normalization_fix_planning');
    assert.equal(result.updated_manifest.raw_write_ready_for_execution, false);
    assert.equal(result.updated_manifest.target_identity_mismatch_blocks_baseline_acceptance, true);
    assert.equal(result.updated_manifest.requires_separate_baseline_acceptance, true);
    assert.equal(result.updated_manifest.requires_separate_final_db_write_authorization, true);
    assert.equal(writes.length, 2);
});

test('write, baseline acceptance and raw retry flags are blocked', () => {
    for (const [key, value] of [
        ['allowDbWrite', true],
        ['allowRawMatchDataWrite', true],
        ['allowControlledWrite', true],
        ['allowMatchesWrite', true],
        ['allowBookmakerOddsWrite', true],
        ['allowFeatureWrite', true],
        ['allowSchemaMigration', true],
        ['allowParserImplementation', true],
        ['allowFeatureExtraction', true],
        ['allowTraining', true],
        ['allowPrediction', true],
        ['allowBrowserRuntime', true],
        ['allowProxyRuntime', true],
        ['acceptBaseline', true],
        ['acceptedBaseline', true],
        ['baselineAcceptanceAuthorization', true],
        ['rawWriteReadyForExecution', true],
        ['rawWriteRetryAuthorization', true],
    ]) {
        const result = mod.validatePlanningInput(validInput({ [key]: value }));
        assert.equal(result.ok, false, `${key} should be blocked`);
    }
});

test('argument parsing, help mode and helper branches stay safe', async () => {
    const parsed = mod.parseArgs([
        '--manifest',
        mod.MANIFEST_PATH,
        '--source=fotmob',
        '--planning-authorization=maybe',
        '--target-external-ids=4830466,4830466,4830461',
        '--unknown-flag=yes',
        'loose',
    ]);
    assert.equal(parsed.manifest, mod.MANIFEST_PATH);
    assert.equal(parsed.source, 'fotmob');
    assert.equal(parsed.planningAuthorization, true);
    assert.equal(parsed.targetExternalIds, '4830466,4830466,4830461');
    assert.deepEqual(parsed.unknown, ['unknown-flag', 'loose']);
    assert.equal(mod.normalizeBooleanFlag(true, false), true);
    assert.equal(mod.normalizeBooleanFlag(false, true), false);
    assert.equal(mod.normalizeBooleanFlag('yes', false), true);
    assert.equal(mod.normalizeBooleanFlag('0', true), false);
    assert.equal(mod.normalizeBooleanFlag('bogus', false), false);

    const underscoreAndBareBoolean = mod.parseArgs([
        '--base_head',
        'abc123',
        '--main-ci-status=success',
        '--final_db_write_confirmation',
        '--request-delay-ms',
        '5',
    ]);
    assert.equal(underscoreAndBareBoolean.baseHead, 'abc123');
    assert.equal(underscoreAndBareBoolean.mainCiStatus, 'success');
    assert.equal(underscoreAndBareBoolean.finalDbWriteConfirmation, true);
    assert.equal(underscoreAndBareBoolean.requestDelayMs, '5');

    const stdout = [];
    const originalWrite = process.stdout.write;
    process.stdout.write = chunk => {
        stdout.push(String(chunk));
        return true;
    };
    try {
        const result = await mod.runCli(['--help']);
        assert.equal(result.status, 0);
        assert.match(stdout.join(''), /Usage:/);
    } finally {
        process.stdout.write = originalWrite;
    }
});

test('validation and manifest gate expose exact missing and follow-up outcome branches', () => {
    const invalid = mod.validatePlanningInput(
        validInput({
            manifest: '',
            renewedProposal: '',
            reportOutput: '',
            source: 'other',
            leagueId: 54,
            leagueName: '',
            season: '',
            rawVersion: '',
            hashStrategy: '',
            batchId: '',
            targetCount: 49,
            planningAuthorization: false,
            sourceInventoryReconciliationAuthorization: false,
            networkAuthorization: false,
            allowDbWrite: true,
            retry: 1,
            requestDelayMs: -1,
        })
    );
    assert.equal(invalid.ok, false);
    assert.match(invalid.errors.join('\n'), /missing manifest=/);
    assert.match(invalid.errors.join('\n'), /league-id must be 53/);
    assert.match(invalid.errors.join('\n'), /retry must be 0/);
    assert.match(invalid.errors.join('\n'), /request-delay-ms must be a non-negative integer/);

    const allowedFollowUp = mod.buildManifestGate(
        manifest({
            next_required_step: 'source_inventory_manifest_regeneration_review',
            raw_write_retry_authorization_status: 'blocked_pending_target_identity_source_inventory_reconciliation',
        })
    );
    assert.equal(allowedFollowUp.ok, true);

    const invalidGate = mod.buildManifestGate(
        manifest({
            next_required_step: 'wrong_step',
            phase_5_21_l2v3d_planning_status: 'missing',
            phase_5_21_l2v3d_identity_mismatch_count: 7,
            raw_write_ready_for_execution: true,
            raw_write_retry_authorization_status: 'wrong',
            phase_5_21_l2v3d_manifest_target_metadata_mismatch_indicated: false,
        })
    );
    assert.equal(invalidGate.ok, false);
    assert.match(invalidGate.errors.join('\n'), /allowed L2V3E follow-up outcome/);
    assert.match(invalidGate.errors.join('\n'), /phase_5_21_l2v3d_planning_status/);
    assert.match(invalidGate.errors.join('\n'), /phase_5_21_l2v3d_identity_mismatch_count/);
    assert.match(invalidGate.errors.join('\n'), /raw_write_retry_authorization_status/);
});

test('manifest gate and source inventory fetch fail closed', async () => {
    const invalidManifest = await mod.runPlanning(validInput(), {
        manifest: manifest({ target_identity_mismatch_blocks_baseline_acceptance: false }),
        renewedProposal: renewedProposal(),
        sourceInventoryJson: sourceInventoryJson(),
        dbSnapshot: dbSnapshot(),
        writeManifest: false,
        writeReport: false,
    });
    assert.equal(invalidManifest.ok, false);
    assert.equal(invalidManifest.status, 3);

    const invalidSourceFetch = await mod.runPlanning(validInput(), {
        manifest: manifest(),
        renewedProposal: renewedProposal(),
        fetchFn: async () => ({
            status: 403,
            url: 'https://www.fotmob.com/api/data/leagues?id=53&season=20252026',
            async text() {
                return 'forbidden';
            },
        }),
        writeManifest: false,
        writeReport: false,
        dbSnapshot: dbSnapshot(),
    });
    assert.equal(invalidSourceFetch.ok, false);
    assert.equal(invalidSourceFetch.status, 6);
});

test('fetch helpers and reconciliation item helpers cover direct fallback branches', async () => {
    const fetchError = await mod.fetchSourceInventoryPayload(validInput(), {
        fetchFn: async () => {
            throw new Error('network-down');
        },
    });
    assert.equal(fetchError.ok, false);
    assert.equal(fetchError.parse_status, 'fetch_error');

    const non200Json = await mod.fetchSourceInventoryPayload(validInput(), {
        fetchFn: async () => ({
            status: 503,
            url: 'https://www.fotmob.com/api/data/leagues?id=53&season=20252026',
            async text() {
                return JSON.stringify({ overview: { matches: { allMatches: [] } } });
            },
        }),
    });
    assert.equal(non200Json.ok, false);
    assert.equal(non200Json.parse_status, 'parsed_json');

    const sourceByExternalId = new Map([
        [
            '4830466',
            {
                external_id: '4830466',
                source_path: 'overview.matches.allMatches',
                source_inventory_record_key: 'overview.matches.allMatches#4830466',
                home_team: 'Rennes',
                away_team: 'Marseille',
                match_date: '2025-08-15T18:45:00.000Z',
                status: 'finished',
                page_url: '/matches/marseille-vs-rennes/2t9n7h#4830466',
                page_url_base: '/matches/marseille-vs-rennes/2t9n7h',
                page_url_anchor: '4830466',
                id_like_fields: {},
                top_level_keys: [],
            },
        ],
    ]);
    const matched = mod.buildTargetReconciliationItem(
        candidate('4830466'),
        proposalTarget('4830466', {
            attempts: [
                {
                    metadata_identity_observed: {
                        external_id: '4830466',
                        home_team: 'Rennes',
                        away_team: 'Marseille',
                        match_time_utc: '2025-08-15T18:45:00.000Z',
                        status: 'finished',
                    },
                },
            ],
        }),
        sourceByExternalId,
        dbSnapshot().target_rows
    );
    assert.equal(matched.requested_vs_observed_identity_status, 'match');
    assert.equal(matched.suspected_mismatch_stage, 'matched');
});

test('source inventory fetch and root-cause branches fail closed across fallback paths', async () => {
    const missingFetchDependency = await mod.runPlanning(validInput(), {
        manifest: manifest(),
        renewedProposal: renewedProposal(),
        fetchFn: 'missing',
        writeManifest: false,
        writeReport: false,
        dbSnapshot: dbSnapshot(),
    });
    assert.equal(missingFetchDependency.ok, false);
    assert.equal(missingFetchDependency.status, 6);
    assert.match(missingFetchDependency.errors.join('\n'), /FETCH_DEPENDENCY_MISSING/);

    const bodyReadFailure = await mod.runPlanning(validInput(), {
        manifest: manifest(),
        renewedProposal: renewedProposal(),
        fetchFn: async () => ({
            status: 200,
            url: 'https://www.fotmob.com/api/data/leagues?id=53&season=20252026',
            async text() {
                throw new Error('broken-body');
            },
        }),
        writeManifest: false,
        writeReport: false,
        dbSnapshot: dbSnapshot(),
    });
    assert.equal(bodyReadFailure.ok, false);
    assert.equal(bodyReadFailure.status, 6);
    assert.match(bodyReadFailure.errors.join('\n'), /BODY_READ_ERROR/);

    const blockedResponse = await mod.runPlanning(validInput(), {
        manifest: manifest(),
        renewedProposal: renewedProposal(),
        fetchFn: async () => ({
            status: 200,
            url: 'https://www.fotmob.com/api/data/leagues?id=53&season=20252026',
            async text() {
                return '<html><title>Just a moment</title><body>captcha</body></html>';
            },
        }),
        writeManifest: false,
        writeReport: false,
        dbSnapshot: dbSnapshot(),
    });
    assert.equal(blockedResponse.ok, false);
    assert.equal(blockedResponse.status, 6);
    assert.match(blockedResponse.errors.join('\n'), /BLOCKED/);

    const malformedJson = await mod.runPlanning(validInput(), {
        manifest: manifest(),
        renewedProposal: renewedProposal(),
        fetchFn: async () => ({
            status: 200,
            url: 'https://www.fotmob.com/api/data/leagues?id=53&season=20252026',
            async text() {
                return '{';
            },
        }),
        writeManifest: false,
        writeReport: false,
        dbSnapshot: dbSnapshot(),
    });
    assert.equal(malformedJson.ok, false);
    assert.equal(malformedJson.status, 6);
    assert.match(malformedJson.errors.join('\n'), /JSON_PARSE_ERROR/);
});

test('source inventory mismatch keeps raw write blocked', async () => {
    const mismatched = sourceInventoryJson();
    mismatched.overview.matches.allMatches[0].home.name = 'Wrong Home';
    const result = await mod.runPlanning(validInput({ targetExternalIds: ['4830466'] }), {
        manifest: manifest(),
        renewedProposal: renewedProposal(),
        sourceInventoryJson: mismatched,
        dbSnapshot: dbSnapshot(),
        writeManifest: false,
        writeReport: false,
    });
    assert.equal(result.ok, true);
    assert.equal(result.summary.source_inventory_vs_manifest_mismatch_count, 1);
    assert.equal(result.summary.raw_write_ready_for_execution, false);
    assert.equal(result.updated_manifest.raw_write_ready_for_execution, false);
});

test('manifest-vs-db and live-mapping alternatives remain blocked with lower confidence', async () => {
    const missingDbRow = await mod.runPlanning(validInput({ targetExternalIds: ['4830466'] }), {
        manifest: manifest(),
        renewedProposal: renewedProposal(),
        sourceInventoryJson: sourceInventoryJson(),
        dbSnapshot: dbSnapshot({ target_rows: [] }),
        writeManifest: false,
        writeReport: false,
    });
    assert.equal(missingDbRow.ok, true);
    assert.equal(missingDbRow.summary.manifest_vs_db_mismatch_count, 1);
    assert.equal(missingDbRow.summary.suspected_root_cause, 'DB_seed_identity_wrong');
    assert.equal(missingDbRow.summary.root_cause_confidence, 'medium');
    assert.equal(missingDbRow.summary.raw_write_ready_for_execution, false);

    const differentPageBase = sourceInventoryJson();
    differentPageBase.overview.matches.allMatches = differentPageBase.overview.matches.allMatches.map(item =>
        item.id === OBSERVED['4830466'][0]
            ? { ...item, pageUrl: `/matches/other-fixture/zzz#${OBSERVED['4830466'][0]}` }
            : item
    );
    const liveMapping = await mod.runPlanning(validInput({ targetExternalIds: ['4830466'] }), {
        manifest: manifest(),
        renewedProposal: renewedProposal(),
        sourceInventoryJson: differentPageBase,
        dbSnapshot: dbSnapshot(),
        writeManifest: false,
        writeReport: false,
    });
    assert.equal(liveMapping.ok, true);
    assert.equal(liveMapping.summary.db_vs_live_observed_mismatch_count, 1);
    assert.equal(liveMapping.summary.suspected_root_cause, 'FotMob_live_detail_mapping_changed');
    assert.equal(liveMapping.summary.root_cause_confidence, 'low');
    assert.equal(liveMapping.updated_manifest.raw_write_ready_for_execution, false);
});

test('rerun remains idempotent after L2V3E manifest metadata is already written', async () => {
    const firstRun = await mod.runPlanning(validInput({ targetExternalIds: ['4830466'] }), {
        manifest: manifest(),
        renewedProposal: renewedProposal(),
        sourceInventoryJson: sourceInventoryJson(),
        dbSnapshot: dbSnapshot(),
        writeManifest: false,
        writeReport: false,
    });
    assert.equal(firstRun.ok, true);

    const secondRun = await mod.runPlanning(validInput({ targetExternalIds: ['4830466'] }), {
        manifest: firstRun.updated_manifest,
        renewedProposal: renewedProposal(),
        sourceInventoryJson: sourceInventoryJson(),
        dbSnapshot: dbSnapshot(),
        writeManifest: false,
        writeReport: false,
    });
    assert.equal(secondRun.ok, true);
    assert.equal(secondRun.summary.suspected_root_cause, 'schedule_vs_detail_external_id_mismatch');
    assert.equal(secondRun.updated_manifest.next_required_step, 'schedule_detail_identity_normalization_fix_planning');
});

test('source inventory selection, DB snapshot helpers and comparison helpers cover fallback branches', async () => {
    const selected = mod.buildSourceInventorySelection(
        {
            request_url: 'https://www.fotmob.com/api/data/leagues?id=53&season=20252026',
            final_url: 'https://www.fotmob.com/api/data/leagues?id=53&season=20252026',
            http_status: 200,
            body_bytes: 10,
            parse_status: 'parsed_json',
            blocked_markers: [],
            json: {
                overview: { matches: { allMatches: sourceInventoryJson().overview.matches.allMatches } },
                fixtures: {
                    allMatches: [
                        {
                            id: '4830466',
                            home: { shortName: 'Ren' },
                            away: { longName: 'Marseille' },
                            time: { utc: '2025-08-15T18:45:00Z' },
                            scheduled: true,
                            pageUrl: '/matches/marseille-vs-rennes/2t9n7h#4830466',
                            slug: 'rennes-marseille',
                        },
                    ],
                },
            },
        },
        ['4830466'],
        ['4830759']
    );
    assert.equal(selected.selected_count, 2);
    assert.equal(selected.duplicate_selection_events >= 1, true);

    const chosen = selected.selected_by_external_id.get('4830466');
    assert.equal(chosen.source_path, 'overview.matches.allMatches');
    assert.equal(chosen.page_url_anchor, '4830466');
    assert.equal(chosen.id_like_fields.pageUrl.includes('#4830466'), true);

    const fakePool = {
        ended: false,
        async query(sql) {
            if (/FROM matches\\s*UNION ALL/i.test(sql) || /SELECT 'matches' AS table_name/i.test(sql)) {
                return { rows: [{ table_name: 'matches', rows: 60 }] };
            }
            if (/FROM matches\\s*WHERE/i.test(sql)) {
                return { rows: [] };
            }
            return { rows: [{ rows: 0 }] };
        },
        async end() {
            this.ended = true;
        },
    };
    const snapshot = await mod.queryReadOnlyDbSnapshot(['53_20252026_4830466'], ['4830759'], { pool: fakePool });
    assert.equal(snapshot.row_counts.matches, 60);
    assert.equal(snapshot.row_counts.raw_match_data, 0);
    assert.equal(snapshot.candidate_v2_rows_count, 0);
    assert.equal(fakePool.ended, false);

    const emptySelection = mod.buildSourceInventorySelection({ json: {} }, ['missing'], ['observed-missing']);
    assert.equal(emptySelection.selected_count, 0);

    const baseTarget = candidate('4830466');
    const missingSourceItem = mod.buildTargetReconciliationItem(baseTarget, proposalTarget('4830466'), new Map(), []);
    assert.equal(missingSourceItem.source_inventory_vs_manifest_status, 'missing_source_inventory_record');
    assert.equal(missingSourceItem.manifest_vs_db_status, 'missing_db_row');
    assert.equal(missingSourceItem.db_vs_live_observed_status, 'missing_db_row');
    assert.equal(missingSourceItem.suspected_mismatch_stage, 'source_inventory_generation');

    const requestedRecord = {
        external_id: '4830466',
        home_team: 'Rennes',
        away_team: 'Marseille',
        match_date: '2025-08-15T18:45:00.000Z',
        status: 'finished',
        page_url_base: '/matches/marseille-vs-rennes/2t9n7h',
    };
    const dbSeedMismatch = mod.buildTargetReconciliationItem(
        baseTarget,
        proposalTarget('4830466'),
        new Map([['4830466', requestedRecord]]),
        [
            {
                match_id: '53_20252026_4830466',
                external_id: 'wrong',
                home_team: 'Rennes',
                away_team: 'Marseille',
                match_date: '2025-08-15T18:45:00.000Z',
                status: 'finished',
            },
        ]
    );
    assert.equal(dbSeedMismatch.source_inventory_vs_manifest_status, 'match');
    assert.equal(dbSeedMismatch.manifest_vs_db_status, 'mismatch');
    assert.equal(dbSeedMismatch.suspected_mismatch_stage, 'DB_seed');
});

test('source inventory normalization covers alternate id, team, status, url, and duplicate priority branches', () => {
    const selected = mod.buildSourceInventorySelection(
        {
            request_url: '/api/data/leagues?id=53&season=20252026',
            final_url: '/api/data/leagues?id=53&season=20252026',
            http_status: 200,
            body_bytes: 123,
            parse_status: 'parsed_json',
            blocked_markers: [],
            json: {
                fixtures: {
                    allMatches: [
                        {
                            matchId: '7001',
                            homeTeam: 'Home String',
                            awayTeam: { shortName: 'Away Short' },
                            matchTime: '2026-02-01T10:00:00.000Z',
                            status: 'Live',
                            matchUrl: '/matches/home-string-vs-away-short/a#7001',
                        },
                        {
                            id: '7003',
                            home: { name: 'Lower Priority Home' },
                            away: { name: 'Lower Priority Away' },
                            date: '2026-02-03T10:00:00.000Z',
                            scheduled: true,
                            pageUrl: '/matches/lower-priority/low#7003',
                        },
                    ],
                },
                matches: {
                    allMatches: [
                        {
                            match_id: '7002',
                            home_team: { longName: 'Home Snake' },
                            away: 'Away Direct',
                            time: { utc: '2026-02-02T10:00:00.000Z' },
                            status: { live: true },
                            url: '/matches/home-snake-vs-away-direct/b#7002',
                        },
                    ],
                },
                overview: {
                    matches: {
                        allMatches: [
                            {
                                id: '7003',
                                home: { name: 'Preferred Home' },
                                away: { name: 'Preferred Away' },
                                kickoff: { datetime: '2026-02-03T10:00:00.000Z' },
                                status: { cancelled: true },
                                pageURL: '/matches/preferred/c#7003',
                                slug: 'preferred-home-preferred-away',
                            },
                        ],
                    },
                    leagueOverviewMatches: [
                        {
                            id: '7004',
                            home: { longName: 'Home Event' },
                            away: { shortName: 'Away Event' },
                            date: '2026-02-04T10:00:00.000Z',
                            status: { started: true },
                            pageUrl: '/matches/home-event-vs-away-event/d#7004',
                        },
                    ],
                },
            },
        },
        ['7001', '7002', '7003', '7004'],
        []
    );

    assert.equal(selected.selected_count, 4);
    assert.equal(selected.duplicate_selection_events >= 1, true);
    assert.equal(selected.selected_by_external_id.get('7001').home_team, 'Home String');
    assert.equal(selected.selected_by_external_id.get('7001').away_team, 'Away Short');
    assert.equal(selected.selected_by_external_id.get('7001').status, 'live');
    assert.equal(selected.selected_by_external_id.get('7002').home_team, 'Home Snake');
    assert.equal(selected.selected_by_external_id.get('7002').away_team, 'Away Direct');
    assert.equal(selected.selected_by_external_id.get('7002').status, 'live');
    assert.equal(selected.selected_by_external_id.get('7003').source_path, 'overview.matches.allMatches');
    assert.equal(selected.selected_by_external_id.get('7003').status, 'cancelled');
    assert.equal(selected.selected_by_external_id.get('7003').id_like_fields.slug, 'preferred-home-preferred-away');
    assert.equal(selected.selected_by_external_id.get('7004').status, 'live');
});

test('target reconciliation covers malformed URL summary and missing observed identity branches', () => {
    const malformedSource = {
        external_id: '4830466',
        source_path: 'fixtures.allMatches',
        source_inventory_record_key: 'fixtures.allMatches#4830466',
        home_team: 'Rennes',
        away_team: 'Marseille',
        match_date: '2025-08-15T18:45:00.000Z',
        status: 'finished',
        page_url: 'http://[::1',
        page_url_base: 'http://[::1',
        page_url_anchor: null,
        id_like_fields: { pageUrl: 'http://[::1' },
        top_level_keys: ['id', 'pageUrl'],
    };
    const item = mod.buildTargetReconciliationItem(
        candidate('4830466'),
        { attempts: [{ metadata_identity_observed: {} }] },
        new Map([['4830466', malformedSource]]),
        dbSnapshot().target_rows
    );

    assert.equal(item.source_inventory_page_url_summary, 'http://[::1');
    assert.equal(item.live_observed_external_id, null);
    assert.equal(item.db_vs_live_observed_status, 'missing_live_observed');
    assert.equal(item.suspected_mismatch_stage, 'unknown');
});

test('summary and planning gates cover unresolved-unknown, proposal failure and selection failure branches', async () => {
    const summary = mod.buildSummary({
        items: [
            {
                requested_vs_observed_identity_status: 'mismatch',
                source_inventory_vs_manifest_status: 'match',
                manifest_vs_db_status: 'match',
                db_vs_live_observed_status: 'missing_live_observed',
                observed_source_inventory_found: false,
                shared_page_url_base_with_observed: false,
                suspected_mismatch_stage: 'unknown',
            },
        ],
        input: validInput(),
        manifestGate: { candidate_targets_count: 50 },
        proposalGate: { checkedTargets: [proposalTarget('4830466')] },
        sourceInventorySelection: {},
        dbSnapshot: dbSnapshot(),
        generatedAt: '2026-05-18T00:00:00.000Z',
    });
    assert.equal(summary.suspected_root_cause, 'unresolved_unknown');
    assert.equal(summary.root_cause_confidence, 'unknown');

    const invalidProposal = await mod.runPlanning(validInput(), {
        manifest: manifest(),
        renewedProposal: renewedProposal({
            proposal_phase: 'wrong',
            recommendation: {
                raw_write_ready_for_execution: true,
                requires_separate_baseline_acceptance: false,
                requires_separate_final_db_write_authorization: false,
            },
        }),
        sourceInventoryJson: sourceInventoryJson(),
        dbSnapshot: dbSnapshot(),
        writeManifest: false,
        writeReport: false,
    });
    assert.equal(invalidProposal.ok, false);
    assert.equal(invalidProposal.status, 4);

    const invalidSelection = await mod.runPlanning(validInput({ targetExternalIds: ['9999999'], requestDelayMs: 1 }), {
        manifest: manifest(),
        renewedProposal: renewedProposal(),
        sourceInventoryJson: sourceInventoryJson(),
        dbSnapshot: dbSnapshot(),
        writeManifest: false,
        writeReport: false,
    });
    assert.equal(invalidSelection.ok, false);
    assert.equal(invalidSelection.status, 5);

    const manifestGenerationSummary = mod.buildSummary({
        items: [
            {
                requested_vs_observed_identity_status: 'mismatch',
                source_inventory_vs_manifest_status: 'mismatch',
                manifest_vs_db_status: 'match',
                db_vs_live_observed_status: 'mismatch',
                observed_source_inventory_found: true,
                shared_page_url_base_with_observed: false,
                suspected_mismatch_stage: 'source_inventory_generation',
            },
        ],
        input: validInput(),
        manifestGate: { candidate_targets_count: 50 },
        proposalGate: { checkedTargets: [proposalTarget('4830466')] },
        sourceInventorySelection: {},
        dbSnapshot: dbSnapshot(),
        generatedAt: '2026-05-18T00:00:00.000Z',
    });
    assert.equal(manifestGenerationSummary.suspected_root_cause, 'manifest_generation_mapping_wrong');
    assert.equal(manifestGenerationSummary.recommended_next_step, 'source_inventory_manifest_regeneration_review');

    const dbSeedSummary = mod.buildSummary({
        items: [
            {
                requested_vs_observed_identity_status: 'mismatch',
                source_inventory_vs_manifest_status: 'match',
                manifest_vs_db_status: 'mismatch',
                db_vs_live_observed_status: 'mismatch',
                observed_source_inventory_found: true,
                shared_page_url_base_with_observed: false,
                suspected_mismatch_stage: 'DB_seed',
            },
        ],
        input: validInput(),
        manifestGate: { candidate_targets_count: 50 },
        proposalGate: { checkedTargets: [proposalTarget('4830466')] },
        sourceInventorySelection: {},
        dbSnapshot: dbSnapshot(),
        generatedAt: '2026-05-18T00:00:00.000Z',
    });
    assert.equal(dbSeedSummary.suspected_root_cause, 'DB_seed_identity_wrong');
    assert.equal(dbSeedSummary.recommended_next_step, 'matches_identity_seed_reconciliation_review');

    const liveMappingSummary = mod.buildSummary({
        items: [
            {
                requested_vs_observed_identity_status: 'mismatch',
                source_inventory_vs_manifest_status: 'match',
                manifest_vs_db_status: 'match',
                db_vs_live_observed_status: 'mismatch',
                observed_source_inventory_found: true,
                shared_page_url_base_with_observed: false,
                suspected_mismatch_stage: 'FotMob_live_mapping',
            },
        ],
        input: validInput(),
        manifestGate: { candidate_targets_count: 50 },
        proposalGate: { checkedTargets: [proposalTarget('4830466')] },
        sourceInventorySelection: {},
        dbSnapshot: dbSnapshot(),
        generatedAt: '2026-05-18T00:00:00.000Z',
    });
    assert.equal(liveMappingSummary.suspected_root_cause, 'FotMob_live_detail_mapping_changed');
});

test('source inventory fetch helper fail-closed branches stay no-write and body-safe', async () => {
    const baseInput = validInput();
    const originalFetch = globalThis.fetch;
    try {
        globalThis.fetch = undefined;
        const missingFetch = await mod.fetchSourceInventoryPayload(baseInput, {
            sourceInventoryUrl: 'https://example.test/source.json',
        });
        assert.equal(missingFetch.ok, false);
        assert.equal(missingFetch.parse_status, 'fetch_dependency_missing');
    } finally {
        globalThis.fetch = originalFetch;
    }

    const fetchError = await mod.fetchSourceInventoryPayload(baseInput, {
        sourceInventoryUrl: 'https://example.test/source.json',
        fetchFn: async () => {
            throw new Error('network down');
        },
    });
    assert.equal(fetchError.parse_status, 'fetch_error');
    assert.match(fetchError.error, /^FETCH_ERROR:/);

    const bodyReadError = await mod.fetchSourceInventoryPayload(baseInput, {
        sourceInventoryUrl: 'https://example.test/source.json',
        fetchFn: async () => ({
            status: 200,
            url: 'https://example.test/source.json',
            text: async () => {
                throw new Error('body failed');
            },
        }),
    });
    assert.equal(bodyReadError.parse_status, 'body_read_error');

    const blocked = await mod.fetchSourceInventoryPayload(baseInput, {
        sourceInventoryUrl: 'https://example.test/source.json',
        fetchFn: async () => ({
            status: 403,
            url: 'https://example.test/source.json',
            text: async () => '<html>cloudflare access denied</html>',
        }),
    });
    assert.equal(blocked.ok, false);
    assert.equal(blocked.parse_status, 'blocked_markers_detected');
    assert.equal(blocked.error.includes('<html>'), false);

    const invalidJson = await mod.fetchSourceInventoryPayload(baseInput, {
        sourceInventoryUrl: 'https://example.test/source.json',
        fetchFn: async () => ({
            status: 200,
            url: 'https://example.test/source.json',
            text: async () => '{bad',
        }),
    });
    assert.equal(invalidJson.parse_status, 'json_parse_failed');

    const non200Json = await mod.fetchSourceInventoryPayload(baseInput, {
        sourceInventoryUrl: 'https://example.test/source.json',
        fetchFn: async () => ({
            status: 204,
            url: 'https://example.test/source.json',
            text: async () => '{}',
        }),
    });
    assert.equal(non200Json.ok, false);
    assert.equal(non200Json.parse_status, 'parsed_json');
});

test('file helpers and sleep cover local IO branches safely', async () => {
    const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'l2v3e-'));
    const jsonPath = path.join(tempDir, 'nested', 'sample.json');
    const reportPath = path.join(tempDir, 'nested', 'report.md');

    mod.writeJsonFile(jsonPath, { ok: true });
    mod.writeReportFile(reportPath, '# ok\n');

    assert.deepEqual(mod.readJsonFile(jsonPath), { ok: true });
    assert.equal(fs.readFileSync(reportPath, 'utf8'), '# ok\n');

    await mod.sleep(1);
});

test('queryReadOnlyDbSnapshot covers default Pool creation and pool.end cleanup', async () => {
    const originalPool = pg.Pool;
    let ended = false;
    pg.Pool = class FakePool {
        async query(sql) {
            if (/SELECT 'matches' AS table_name/i.test(sql)) {
                return { rows: [{ table_name: 'matches', rows: 60 }] };
            }
            if (/FROM matches/i.test(sql)) {
                return { rows: [] };
            }
            return { rows: [{ rows: 0 }] };
        }
        async end() {
            ended = true;
        }
    };

    try {
        const fresh = loadFreshModule();
        const snapshot = await fresh.queryReadOnlyDbSnapshot(['53_20252026_4830466'], ['4830759']);
        assert.equal(snapshot.row_counts.matches, 60);
        assert.equal(snapshot.candidate_v2_rows_count, 0);
        assert.equal(ended, true);
    } finally {
        pg.Pool = originalPool;
        delete require.cache[require.resolve(MODULE_PATH)];
    }
});

test('report and manifest do not contain full payload markers', async () => {
    const result = await mod.runPlanning(validInput({ targetExternalIds: ['4830466'] }), {
        manifest: manifest(),
        renewedProposal: renewedProposal(),
        sourceInventoryJson: sourceInventoryJson(),
        dbSnapshot: dbSnapshot(),
        writeManifest: false,
        writeReport: false,
    });
    const manifestText = JSON.stringify(result.updated_manifest);
    const reportText = result.report;

    assert.equal(manifestText.includes('<html>'), false);
    assert.equal(manifestText.includes('__NEXT_DATA__'), false);
    assert.equal(reportText.includes('<html>'), false);
    assert.equal(reportText.includes('__NEXT_DATA__'), false);
    assert.equal(reportText.includes('/matches/marseille-vs-rennes/2t9n7h'), true);
});

test('unresolved source inventory reconciliation is not executable by raw write runner', async () => {
    const result = await mod.runPlanning(validInput(), {
        manifest: manifest(),
        renewedProposal: renewedProposal(),
        sourceInventoryJson: sourceInventoryJson(),
        dbSnapshot: dbSnapshot(),
        writeManifest: false,
        writeReport: false,
    });
    const gate = rawWrite.validateManifestGate(result.updated_manifest);

    assert.equal(result.updated_manifest.raw_write_ready_for_execution, false);
    assert.equal(result.updated_manifest.next_required_step, 'schedule_detail_identity_normalization_fix_planning');
    assert.equal(gate.ok, false);
    assert.match(gate.errors.join('\n'), /required_next_step/);
});

test('runCli prints only safe JSON summary', async () => {
    const stdout = [];
    const originalWrite = process.stdout.write;
    process.stdout.write = chunk => {
        stdout.push(String(chunk));
        return true;
    };
    try {
        const result = await mod.runCli(
            [
                `--manifest=${mod.MANIFEST_PATH}`,
                `--renewed-proposal=${mod.RENEWED_PROPOSAL_PATH}`,
                `--report-output=${mod.REPORT_PATH}`,
                '--source=fotmob',
                '--league-id=53',
                '--league-name=Ligue 1',
                '--season=2025/2026',
                '--raw-version=fotmob_pageprops_v2',
                '--hash-strategy=stable_pageprops_payload_v1',
                `--batch-id=${mod.BATCH_ID}`,
                '--target-count=50',
                '--planning-authorization=yes',
                '--source-inventory-reconciliation-authorization=yes',
                '--network-authorization=yes',
                '--allow-db-write=no',
                '--allow-raw-match-data-write=no',
                '--allow-controlled-write=no',
                '--allow-matches-write=no',
                '--allow-bookmaker-odds-write=no',
                '--allow-feature-write=no',
                '--allow-schema-migration=no',
                '--allow-parser-implementation=no',
                '--allow-feature-extraction=no',
                '--allow-training=no',
                '--allow-prediction=no',
                '--allow-browser-runtime=no',
                '--allow-proxy-runtime=no',
                '--print-full-body=no',
                '--save-full-body=no',
                '--print-full-json=no',
                '--save-full-json=no',
                '--print-full-pageprops=no',
                '--save-full-pageprops=no',
                '--target-external-ids=4830466',
                '--retry=0',
            ],
            {
                manifest: manifest(),
                renewedProposal: renewedProposal(),
                sourceInventoryJson: sourceInventoryJson(),
                dbSnapshot: dbSnapshot(),
                writeManifest: false,
                writeReport: false,
            }
        );
        assert.equal(result.status, 0);
        assert.match(stdout.join(''), /"ok": true/);
        assert.equal(stdout.join('').includes('<html>'), false);
        assert.equal(stdout.join('').includes('__NEXT_DATA__'), false);
    } finally {
        process.stdout.write = originalWrite;
    }
});
