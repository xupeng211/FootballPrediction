'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/pageprops_v2_schedule_detail_identity_normalization_plan.js');
const RAW_WRITE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/renewed_pageprops_v2_raw_write_execute.js');
const L2V3E_PATH = path.join(PROJECT_ROOT, 'scripts/ops/pageprops_v2_target_source_inventory_reconciliation_plan.js');

function loadFreshModule() {
    delete require.cache[require.resolve(MODULE_PATH)];
    return require(MODULE_PATH);
}

const mod = loadFreshModule();
const rawWrite = require(RAW_WRITE_PATH);
const l2v3e = require(L2V3E_PATH);

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
        write_plan_status: 'eligible_for_insert',
        write_status: 'blocked_missing_matches_fk_prerequisite',
        write_execution_status: 'blocked_missing_matches_fk_prerequisite',
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
        next_required_step: 'schedule_detail_identity_normalization_fix_planning',
        phase_5_21_l2v3d_planning_status: 'completed_no_write',
        phase_5_21_l2v3d_identity_mismatch_count: 8,
        phase_5_21_l2v3d_manifest_target_metadata_mismatch_indicated: true,
        target_identity_mismatch_blocks_baseline_acceptance: true,
        raw_write_retry_authorization_status: 'blocked_pending_target_identity_source_inventory_reconciliation',
        phase_5_21_l2v3e_planning_status: 'completed_no_write',
        target_identity_source_inventory_reconciliation_status: 'blocked_schedule_detail_identity_mismatch_identified',
        phase_5_21_l2v3e_checked_target_count: 8,
        phase_5_21_l2v3e_identity_match_count: 0,
        phase_5_21_l2v3e_identity_mismatch_count: 8,
        phase_5_21_l2v3e_source_inventory_vs_manifest_mismatch_count: 0,
        phase_5_21_l2v3e_manifest_vs_db_mismatch_count: 0,
        phase_5_21_l2v3e_db_vs_live_observed_mismatch_count: 8,
        phase_5_21_l2v3e_requested_vs_observed_external_id_mismatch_count: 8,
        phase_5_21_l2v3e_shared_page_url_base_pair_count: 8,
        phase_5_21_l2v3e_all_pairs_share_page_url_base: true,
        phase_5_21_l2v3e_suspected_root_cause: 'schedule_vs_detail_external_id_mismatch',
        phase_5_21_l2v3e_root_cause_confidence: 'high',
        phase_5_21_l2v3e_recommended_next_step: 'schedule_detail_identity_normalization_fix_planning',
        requires_separate_baseline_acceptance: true,
        requires_separate_final_db_write_authorization: true,
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
                    status: 'finished',
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
        normalizationProposalOutput: mod.NORMALIZATION_PROPOSAL_PATH,
        sourceInventoryReconciliationReport: mod.SOURCE_RECONCILIATION_REPORT_PATH,
        source: 'fotmob',
        leagueId: 53,
        leagueName: 'Ligue 1',
        season: '2025/2026',
        rawVersion: 'fotmob_pageprops_v2',
        hashStrategy: 'stable_pageprops_payload_v1',
        batchId: mod.BATCH_ID,
        targetCount: 50,
        planningAuthorization: true,
        scheduleDetailNormalizationAuthorization: true,
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
        requestDelayMs: 0,
        retry: 0,
        branch: 'data/pageprops-v2-schedule-detail-normalization-phase521l2v3f',
        baseHead: '3a769e5892b7e983d8e7a765b5f8c7b09fd79704',
        mainHead: '3a769e5892b7e983d8e7a765b5f8c7b09fd79704',
        mainCiStatus: 'success',
        pr1279State: 'MERGED',
        pr1279MergeCommit: '3a769e5892b7e983d8e7a765b5f8c7b09fd79704',
        ...overrides,
    };
}

test('valid L2V3F run stays no-write and keeps normalization proposal blocked pending route fix planning', async () => {
    const writes = [];
    const result = await mod.runPlanning(validInput(), {
        manifest: manifest(),
        renewedProposal: renewedProposal(),
        sourceInventoryJson: sourceInventoryJson(),
        dbSnapshot: dbSnapshot(),
        writeJsonFile: (filePath, data) => writes.push({ filePath, data }),
        writeReportFile: (filePath, data) => writes.push({ filePath, data }),
        generatedAt: '2026-05-19T00:00:00.000Z',
    });

    assert.equal(result.ok, true);
    assert.equal(result.summary.no_write, true);
    assert.equal(result.summary.db_write_performed, false);
    assert.equal(result.summary.raw_insert_performed, false);
    assert.equal(result.summary.identity_mapping_acceptance_performed, false);
    assert.equal(result.summary.checked_target_count, 8);
    assert.equal(result.summary.proposed_mapping_count, 8);
    assert.equal(result.summary.high_confidence_mapping_count, 0);
    assert.equal(result.summary.medium_confidence_mapping_count, 8);
    assert.equal(result.summary.low_confidence_mapping_count, 0);
    assert.equal(result.summary.unresolved_mapping_count, 8);
    assert.equal(result.summary.page_url_base_match_count, 8);
    assert.equal(result.summary.team_pair_match_count, 8);
    assert.equal(result.summary.exact_date_match_count, 0);
    assert.equal(result.summary.team_date_status_compatible_count, 0);
    assert.equal(result.summary.team_date_status_mismatch_count, 8);
    assert.equal(result.summary.route_fix_planning_required, true);
    assert.equal(
        result.summary.recommended_next_step,
        'schedule_detail_route_normalization_fix_implementation_planning'
    );
    assert.equal(result.updated_manifest.raw_write_ready_for_execution, false);
    assert.equal(result.updated_manifest.schedule_detail_normalization_required, true);
    assert.equal(result.updated_manifest.requires_separate_identity_mapping_acceptance, true);
    assert.equal(result.updated_manifest.requires_separate_baseline_acceptance, true);
    assert.equal(result.updated_manifest.requires_separate_final_db_write_authorization, true);
    assert.equal(
        result.updated_manifest.next_required_step,
        'schedule_detail_route_normalization_fix_implementation_planning'
    );
    assert.equal(result.proposal.checked_targets.length, 8);
    assert.equal(result.proposal.unchecked_targets.length, 42);
    assert.equal(result.proposal.targets_not_checked.length, 42);
    assert.equal(result.proposal.proposed_mapping_count, 8);
    assert.equal(result.proposal.high_confidence_mapping_count, 0);
    assert.equal(result.proposal.medium_confidence_mapping_count, 8);
    assert.equal(result.proposal.low_confidence_mapping_count, 0);
    assert.equal(result.proposal.unresolved_mapping_count, 8);
    assert.equal(
        result.proposal.checked_targets[0].requested_schedule_external_id !==
            result.proposal.checked_targets[0].observed_detail_external_id,
        true
    );
    assert.equal(writes.length, 3);
});

test('write, baseline, identity acceptance and raw retry flags are blocked', () => {
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
        ['acceptIdentityMapping', true],
        ['identityMappingAcceptance', true],
        ['baselineAcceptanceAuthorization', true],
        ['rawWriteReadyForExecution', true],
        ['rawWriteRetryAuthorization', true],
    ]) {
        const result = mod.validatePlanningInput(validInput({ [key]: value }));
        assert.equal(result.ok, false, `${key} should be blocked`);
    }
});

test('manifest gate fails when L2V3E prerequisites drift', () => {
    const gate = mod.buildManifestGate(
        manifest({
            phase_5_21_l2v3e_planning_status: 'pending',
            target_identity_source_inventory_reconciliation_status: 'wrong',
            phase_5_21_l2v3e_identity_match_count: 1,
            phase_5_21_l2v3e_identity_mismatch_count: 7,
            phase_5_21_l2v3e_source_inventory_vs_manifest_mismatch_count: 1,
            phase_5_21_l2v3e_manifest_vs_db_mismatch_count: 1,
            phase_5_21_l2v3e_db_vs_live_observed_mismatch_count: 7,
            phase_5_21_l2v3e_requested_vs_observed_external_id_mismatch_count: 7,
            phase_5_21_l2v3e_all_pairs_share_page_url_base: false,
            phase_5_21_l2v3e_suspected_root_cause: 'unknown',
            phase_5_21_l2v3e_root_cause_confidence: 'medium',
            phase_5_21_l2v3e_checked_target_count: 7,
            raw_write_ready_for_execution: true,
            target_identity_mismatch_blocks_baseline_acceptance: false,
            requires_separate_baseline_acceptance: false,
            requires_separate_final_db_write_authorization: false,
            next_required_step: 'wrong',
        })
    );
    assert.equal(gate.ok, false);
    assert.match(gate.errors.join('\n'), /phase_5_21_l2v3e_planning_status/);
    assert.match(gate.errors.join('\n'), /target_identity_source_inventory_reconciliation_status/);
    assert.match(gate.errors.join('\n'), /identity_match_count/);
    assert.match(gate.errors.join('\n'), /identity_mismatch_count/);
    assert.match(gate.errors.join('\n'), /source_inventory_vs_manifest_mismatch_count/);
    assert.match(gate.errors.join('\n'), /manifest_vs_db_mismatch_count/);
    assert.match(gate.errors.join('\n'), /db_vs_live_observed_mismatch_count/);
    assert.match(gate.errors.join('\n'), /requested_vs_observed_external_id_mismatch_count/);
    assert.match(gate.errors.join('\n'), /all_pairs_share_page_url_base/);
    assert.match(gate.errors.join('\n'), /suspected_root_cause/);
    assert.match(gate.errors.join('\n'), /root_cause_confidence/);
    assert.match(gate.errors.join('\n'), /checked_target_count/);
    assert.match(gate.errors.join('\n'), /requires_separate_baseline_acceptance/);
    assert.match(gate.errors.join('\n'), /requires_separate_final_db_write_authorization/);
    assert.match(gate.errors.join('\n'), /raw_write_ready_for_execution/);
    assert.match(gate.errors.join('\n'), /next_required_step/);
});

test('pageUrl base match plus exact team, date and status yields high-confidence proposal', () => {
    const item = mod.buildNormalizationItem(
        {
            requested_match_id: '53_20252026_100',
            requested_external_id: '100',
            requested_league: 'Ligue 1',
            requested_season: '2025/2026',
            requested_home_team: 'Marseille',
            requested_away_team: 'Rennes',
            requested_match_date: '2026-05-17T19:00:00.000Z',
            requested_status: 'finished',
            source_inventory_record_key: 'overview.matches.allMatches#100',
            source_inventory_page_url_base: '/matches/marseille-vs-rennes/2t9n7h',
            observed_source_inventory_page_url_base: '/matches/marseille-vs-rennes/2t9n7h',
            shared_page_url_base_with_observed: true,
            live_observed_external_id: '200',
            live_observed_home_team: 'Marseille',
            live_observed_away_team: 'Rennes',
            live_observed_match_date: '2026-05-17T19:00:00.000Z',
            live_observed_status: 'finished',
        },
        mod.buildMappingConflicts([]),
        { status: 'finished' },
        '2026-05-19T00:00:00.000Z'
    );
    assert.equal(item.page_url_base_match_status, 'match');
    assert.equal(item.team_date_status_match_status, 'compatible');
    assert.equal(item.mapping_confidence, 'high');
    assert.deepEqual(item.safety_blockers, []);
});

test('pageUrl base mismatch or team/date/status mismatch blocks proposal acceptance', () => {
    const mismatch = mod.buildNormalizationItem(
        {
            requested_match_id: '53_20252026_100',
            requested_external_id: '100',
            requested_league: 'Ligue 1',
            requested_season: '2025/2026',
            requested_home_team: 'Rennes',
            requested_away_team: 'Marseille',
            requested_match_date: '2025-08-15T18:45:00.000Z',
            requested_status: 'finished',
            source_inventory_record_key: 'overview.matches.allMatches#100',
            source_inventory_page_url_base: '/matches/marseille-vs-rennes/2t9n7h',
            observed_source_inventory_page_url_base: '/matches/other/zzz',
            shared_page_url_base_with_observed: false,
            live_observed_external_id: '200',
            live_observed_home_team: 'Marseille',
            live_observed_away_team: 'Rennes',
            live_observed_match_date: '2026-05-17T19:00:00.000Z',
            live_observed_status: 'finished',
        },
        mod.buildMappingConflicts([]),
        { status: 'finished' },
        '2026-05-19T00:00:00.000Z'
    );
    assert.equal(mismatch.page_url_base_match_status, 'mismatch');
    assert.equal(mismatch.team_date_status_match_status, 'date_mismatch');
    assert.equal(mismatch.mapping_confidence, 'low');
    assert.equal(mismatch.safety_blockers.includes('page_url_base_mismatch'), true);
    assert.equal(mismatch.safety_blockers.includes('team_date_status_mismatch'), true);
});

test('multiple detail ids and multiple schedule ids are detected as blockers', () => {
    const conflicts = mod.buildMappingConflicts([
        { requested_external_id: '100', live_observed_external_id: '200' },
        { requested_external_id: '100', live_observed_external_id: '201' },
        { requested_external_id: '101', live_observed_external_id: '200' },
    ]);
    assert.equal(conflicts.multiple_detail_ids_for_same_schedule_id_count, 1);
    assert.equal(conflicts.multiple_schedule_ids_for_same_detail_id_count, 1);

    const item = mod.buildNormalizationItem(
        {
            requested_match_id: '53_20252026_100',
            requested_external_id: '100',
            requested_league: 'Ligue 1',
            requested_season: '2025/2026',
            requested_home_team: 'Marseille',
            requested_away_team: 'Rennes',
            requested_match_date: '2026-05-17T19:00:00.000Z',
            requested_status: 'finished',
            source_inventory_record_key: 'overview.matches.allMatches#100',
            source_inventory_page_url_base: '/matches/marseille-vs-rennes/2t9n7h',
            observed_source_inventory_page_url_base: '/matches/marseille-vs-rennes/2t9n7h',
            shared_page_url_base_with_observed: true,
            live_observed_external_id: '200',
            live_observed_home_team: 'Marseille',
            live_observed_away_team: 'Rennes',
            live_observed_match_date: '2026-05-17T19:00:00.000Z',
            live_observed_status: 'finished',
        },
        conflicts,
        { status: 'finished' },
        '2026-05-19T00:00:00.000Z'
    );
    assert.equal(item.safety_blockers.includes('multiple_detail_ids_for_same_schedule_id'), true);
    assert.equal(item.safety_blockers.includes('multiple_schedule_ids_for_same_detail_id'), true);
});

test('report, manifest and proposal do not contain full raw_data, pageProps or source body markers', async () => {
    const result = await mod.runPlanning(validInput(), {
        manifest: manifest(),
        renewedProposal: renewedProposal(),
        sourceInventoryJson: sourceInventoryJson(),
        dbSnapshot: dbSnapshot(),
        writeManifest: false,
        writeProposal: false,
        writeReport: false,
        generatedAt: '2026-05-19T00:00:00.000Z',
    });
    const manifestText = JSON.stringify(result.updated_manifest);
    const proposalText = JSON.stringify(result.proposal);
    assert.equal(manifestText.includes('__NEXT_DATA__'), false);
    assert.equal(proposalText.includes('__NEXT_DATA__'), false);
    assert.equal(manifestText.includes('"pageProps":'), false);
    assert.equal(proposalText.includes('"pageProps":'), false);
    assert.equal(result.report.includes('__NEXT_DATA__'), false);
    assert.equal(result.report.includes('SECRET_PAGEPROPS_SHOULD_NOT_PRINT'), false);
});

test('checked-in L2V3F candidate scope clarification does not treat pre-existing v2 rows as write success', () => {
    const manifestText = fs.readFileSync(path.join(PROJECT_ROOT, mod.MANIFEST_PATH), 'utf8');
    const proposalText = fs.readFileSync(path.join(PROJECT_ROOT, mod.NORMALIZATION_PROPOSAL_PATH), 'utf8');
    const reportText = fs.readFileSync(path.join(PROJECT_ROOT, mod.REPORT_PATH), 'utf8');
    const manifestJson = JSON.parse(manifestText);
    const proposalJson = JSON.parse(proposalText);

    assert.equal(manifestJson.phase_5_21_l2v3f_candidate_scope_explained, true);
    assert.equal(manifestJson.phase_5_21_l2v3f_candidate_matches_scope_count, 58);
    assert.equal(manifestJson.phase_5_21_l2v3f_manifest_schedule_targets_count, 50);
    assert.equal(manifestJson.phase_5_21_l2v3f_preexisting_seeded_pageprops_v2_match_count, 8);
    assert.equal(manifestJson.phase_5_21_l2v3f_candidate_count_is_schedule_targets_plus_observed_detail_ids, false);
    assert.equal(manifestJson.phase_5_21_l2v3f_observed_detail_external_ids_in_matches_count, 0);
    assert.equal(manifestJson.phase_5_21_l2v3f_candidate_fotmob_pageprops_v2_raw_rows, 8);
    assert.equal(manifestJson.phase_5_21_l2v3f_candidate_v2_rows_preexisting, true);
    assert.equal(manifestJson.phase_5_21_l2v3f_candidate_v2_rows_are_l2v3f_writes, false);
    assert.equal(manifestJson.phase_5_21_l2v3f_raw_write_succeeded, false);
    assert.equal(manifestJson.raw_write_ready_for_execution, false);
    assert.equal(manifestJson.requires_separate_identity_mapping_acceptance, true);
    assert.equal(manifestJson.requires_separate_baseline_acceptance, true);
    assert.equal(manifestJson.requires_separate_final_db_write_authorization, true);

    assert.equal(proposalJson.candidate_scope_review.candidate_scope_explained, true);
    assert.equal(proposalJson.candidate_scope_review.candidate_matches_count, 58);
    assert.equal(
        proposalJson.candidate_scope_review.candidate_count_is_schedule_targets_plus_observed_detail_ids,
        false
    );
    assert.equal(proposalJson.candidate_scope_review.observed_detail_external_ids_in_matches_count, 0);
    assert.equal(proposalJson.candidate_scope_review.candidate_v2_rows_preexisting, true);
    assert.equal(proposalJson.candidate_scope_review.l2v3f_db_write_performed, false);
    assert.equal(proposalJson.candidate_scope_review.l2v3f_raw_write_succeeded, false);
    assert.equal(proposalJson.candidate_scope_review.candidate_v2_safe_rows.length, 8);
    for (const row of proposalJson.candidate_scope_review.candidate_v2_safe_rows) {
        assert.equal(row.data_version, 'fotmob_pageprops_v2');
        assert.equal(Object.hasOwn(row, 'raw_data'), false);
        assert.equal(Object.hasOwn(row, 'pageProps'), false);
    }

    assert.match(reportText, /candidate_count_is_schedule_targets_plus_observed_detail_ids=false/);
    assert.match(reportText, /candidate_v2_rows_are_l2v3f_writes=false/);
    assert.match(reportText, /l2v3f_raw_write_succeeded=false/);
    assert.equal(reportText.includes('"raw_data":'), false);
    assert.equal(reportText.includes('"pageProps":'), false);
});

test('unresolved normalization proposal is not executable by raw write runner', async () => {
    const result = await mod.runPlanning(validInput(), {
        manifest: manifest(),
        renewedProposal: renewedProposal(),
        sourceInventoryJson: sourceInventoryJson(),
        dbSnapshot: dbSnapshot(),
        writeManifest: false,
        writeProposal: false,
        writeReport: false,
        generatedAt: '2026-05-19T00:00:00.000Z',
    });
    const gate = rawWrite.validateManifestGate(result.updated_manifest);
    assert.equal(gate.ok, false);
    assert.match(gate.errors.join('\n'), /required_next_step/);
});

test('rerun remains idempotent after L2V3F manifest metadata is already written', async () => {
    const first = await mod.runPlanning(validInput(), {
        manifest: manifest(),
        renewedProposal: renewedProposal(),
        sourceInventoryJson: sourceInventoryJson(),
        dbSnapshot: dbSnapshot(),
        writeManifest: false,
        writeProposal: false,
        writeReport: false,
        generatedAt: '2026-05-19T00:00:00.000Z',
    });
    const second = await mod.runPlanning(validInput(), {
        manifest: first.updated_manifest,
        renewedProposal: renewedProposal(),
        sourceInventoryJson: sourceInventoryJson(),
        dbSnapshot: dbSnapshot(),
        writeManifest: false,
        writeProposal: false,
        writeReport: false,
        generatedAt: '2026-05-19T00:00:00.000Z',
    });
    assert.equal(second.ok, true);
    assert.equal(
        second.summary.recommended_next_step,
        'schedule_detail_route_normalization_fix_implementation_planning'
    );
    assert.equal(second.updated_manifest.phase_5_21_l2v3f_planning_status, 'completed_no_write');
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
                '--manifest=' + mod.MANIFEST_PATH,
                '--renewed-proposal=' + mod.RENEWED_PROPOSAL_PATH,
                '--report-output=' + mod.REPORT_PATH,
                '--normalization-proposal-output=' + mod.NORMALIZATION_PROPOSAL_PATH,
                '--source-inventory-reconciliation-report=' + mod.SOURCE_RECONCILIATION_REPORT_PATH,
                '--source=fotmob',
                '--league-id=53',
                '--league-name=Ligue 1',
                '--season=2025/2026',
                '--raw-version=fotmob_pageprops_v2',
                '--hash-strategy=stable_pageprops_payload_v1',
                '--batch-id=' + mod.BATCH_ID,
                '--target-count=50',
                '--planning-authorization=yes',
                '--schedule-detail-normalization-authorization=yes',
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
                '--request-delay-ms=0',
                '--retry=0',
            ],
            {
                manifest: manifest(),
                renewedProposal: renewedProposal(),
                sourceInventoryJson: sourceInventoryJson(),
                dbSnapshot: dbSnapshot(),
                writeManifest: false,
                writeProposal: false,
                writeReport: false,
                generatedAt: '2026-05-19T00:00:00.000Z',
            }
        );
        assert.equal(result.status, 0);
        assert.match(stdout.join(''), /"ok": true/);
        assert.equal(stdout.join('').includes('__NEXT_DATA__'), false);
        assert.equal(stdout.join('').includes('"pageProps":'), false);
    } finally {
        process.stdout.write = originalWrite;
    }
});

test('file helpers and sleep cover local IO branches safely', async () => {
    const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'l2v3f-'));
    const jsonPath = path.join(tempDir, 'data.json');
    const mdPath = path.join(tempDir, 'report.md');
    mod.writeJsonFile(jsonPath, { ok: true });
    mod.writeReportFile(mdPath, '# ok\n');
    assert.deepEqual(mod.readJsonFile(jsonPath), { ok: true });
    assert.equal(fs.readFileSync(mdPath, 'utf8'), '# ok\n');
    await mod.sleep(0);
    await mod.sleep(1);
});

test('parseArgs records positional args, unknown keys, bare booleans and next-arg values', () => {
    const parsed = mod.parseArgs([
        'positional',
        '--planning-authorization',
        '--network-authorization',
        'yes',
        '--unknown-flag=1',
        '--retry',
        '0',
    ]);
    assert.equal(parsed.planningAuthorization, true);
    assert.equal(parsed.networkAuthorization, true);
    assert.equal(parsed.retry, '0');
    assert.deepEqual(parsed.unknown, ['positional', 'unknown-flag']);
    assert.equal(mod.normalizeBooleanFlag('maybe', false), false);
    assert.equal(mod.normalizeBooleanFlag('', true), true);
});

test('validatePlanningInput reports missing and mismatched exact values and numeric guards', () => {
    const missingManifest = mod.validatePlanningInput(validInput({ manifest: '', leagueId: 'abc', retry: 1 }));
    assert.equal(missingManifest.ok, false);
    assert.match(missingManifest.errors.join('\n'), /missing manifest=/);
    assert.match(missingManifest.errors.join('\n'), /league-id must be 53/);
    assert.match(missingManifest.errors.join('\n'), /retry must be 0/);

    const wrongManifest = mod.validatePlanningInput(validInput({ manifest: 'wrong', requestDelayMs: -1 }));
    assert.equal(wrongManifest.ok, false);
    assert.match(wrongManifest.errors.join('\n'), /manifest must be/);
    assert.match(wrongManifest.errors.join('\n'), /request-delay-ms must be a non-negative integer/);
});

test('helper branches cover missing pageUrl, source-record fallback, null mapping and non-route summary outcomes', () => {
    assert.equal(
        mod.pageUrlBaseMatchStatus({
            source_inventory_page_url_base: '',
            observed_source_inventory_page_url_base: '/matches/foo',
        }),
        'missing_page_url_base'
    );

    const fallback = mod.buildNormalizationItem(
        {
            requested_match_id: '53_20252026_300',
            requested_external_id: '300',
            requested_league: 'Ligue 1',
            requested_season: '2025/2026',
            requested_home_team: 'Paris Saint-Germain',
            requested_away_team: 'Auxerre',
            requested_match_date: '2026-01-23T19:00:00.000Z',
            requested_status: '',
            source_inventory_record_key: '',
            source_inventory_page_url_base: '',
            observed_source_inventory_page_url_base: '',
            shared_page_url_base_with_observed: false,
            live_observed_external_id: '',
            live_observed_home_team: '',
            live_observed_away_team: '',
            live_observed_match_date: '',
            live_observed_status: '',
        },
        mod.buildMappingConflicts([]),
        {
            home_team: 'Paris Saint-Germain',
            away_team: 'Auxerre',
            match_date: '2026-01-23T19:00:00.000Z',
            status: '',
        },
        '2026-05-19T00:00:00.000Z'
    );
    assert.equal(fallback.observed_home_team, 'Paris Saint-Germain');
    assert.equal(fallback.page_url_base_match_status, 'missing_page_url_base');
    assert.equal(fallback.team_date_status_match_status, 'status_unknown');
    assert.equal(fallback.proposed_normalization_key, 'unknown');
    assert.equal(fallback.proposed_mapping, null);
    assert.equal(fallback.mapping_confidence, 'unknown');
    assert.equal(fallback.mapping_status, 'unresolved_unknown');
    assert.equal(fallback.safety_blockers.includes('missing_page_url_base'), true);
    assert.equal(fallback.safety_blockers.includes('unknown'), true);

    const summary = mod.buildSummary({
        input: validInput(),
        manifestGate: { candidate_targets_count: 8 },
        items: [
            {
                proposed_mapping: null,
                mapping_confidence: 'unknown',
                safety_blockers: ['unknown'],
                page_url_base_match_status: 'missing_page_url_base',
                team_date_status_match_status: 'status_unknown',
                requested_home_team: 'Paris Saint-Germain',
                requested_away_team: 'Auxerre',
                observed_home_team: 'Paris Saint-Germain',
                observed_away_team: 'Auxerre',
                requested_match_date: '2026-01-23T19:00:00.000Z',
                observed_match_date: '2026-01-23T19:00:00.000Z',
                mapping_status: 'unresolved_unknown',
            },
        ],
        conflicts: {},
        generatedAt: '2026-05-19T00:00:00.000Z',
    });
    assert.equal(summary.recommended_next_step, 'continued target identity investigation');

    const expandedManifest = mod.buildUpdatedManifest(
        {},
        { recommended_next_step: 'expanded no-write schedule detail normalization proposal' }
    );
    assert.equal(
        expandedManifest.schedule_detail_identity_normalization_status,
        'blocked_pending_expanded_normalization_proposal'
    );

    const acceptanceManifest = mod.buildUpdatedManifest(
        {},
        { recommended_next_step: 'schedule_detail_identity_mapping_acceptance_review' }
    );
    assert.equal(
        acceptanceManifest.schedule_detail_identity_normalization_status,
        'proposal_only_ready_for_identity_mapping_acceptance_review'
    );

    const continuedManifest = mod.buildUpdatedManifest(
        {},
        { recommended_next_step: 'continued target identity investigation' }
    );
    assert.equal(
        continuedManifest.schedule_detail_identity_normalization_status,
        'blocked_pending_schedule_detail_investigation'
    );

    const expandedSummary = mod.buildSummary({
        input: validInput(),
        manifestGate: { candidate_targets_count: 50 },
        items: [
            {
                proposed_mapping: { schedule_external_id: '100', detail_external_id: '200' },
                mapping_confidence: 'medium',
                safety_blockers: ['team_date_status_mismatch'],
                page_url_base_match_status: 'match',
                team_date_status_match_status: 'date_mismatch',
                requested_home_team: 'Marseille',
                requested_away_team: 'Rennes',
                observed_home_team: 'Lens',
                observed_away_team: 'Lyon',
                requested_match_date: '2025-08-15T18:45:00.000Z',
                observed_match_date: '2026-05-17T19:00:00.000Z',
                mapping_status: 'proposal_only_unaccepted',
            },
        ],
        conflicts: {},
        generatedAt: '2026-05-19T00:00:00.000Z',
    });
    assert.equal(expandedSummary.recommended_next_step, 'expanded no-write schedule detail normalization proposal');

    const acceptanceSummary = mod.buildSummary({
        input: validInput(),
        manifestGate: { candidate_targets_count: 1 },
        items: [
            {
                proposed_mapping: { schedule_external_id: '100', detail_external_id: '200' },
                mapping_confidence: 'high',
                safety_blockers: [],
                page_url_base_match_status: 'match',
                team_date_status_match_status: 'compatible',
                requested_home_team: 'Marseille',
                requested_away_team: 'Rennes',
                observed_home_team: 'Rennes',
                observed_away_team: 'Marseille',
                requested_match_date: '2026-05-17T19:00:00.000Z',
                observed_match_date: '2026-05-17T19:00:00.000Z',
                mapping_status: 'proposal_only_high_confidence_unaccepted',
            },
        ],
        conflicts: {},
        generatedAt: '2026-05-19T00:00:00.000Z',
    });
    assert.equal(acceptanceSummary.recommended_next_step, 'schedule_detail_identity_mapping_acceptance_review');
});

test('team/date/status helper covers mismatch branches and compatibility fallback', () => {
    assert.equal(
        mod.teamDateStatusMatchStatus({
            requested_home_team: '',
            requested_away_team: '',
            observed_home_team: '',
            observed_away_team: '',
            requested_match_date: '',
            observed_match_date: '',
            requested_status: '',
            observed_status: '',
        }),
        'team_mismatch'
    );
    assert.equal(
        mod.teamDateStatusMatchStatus({
            requested_home_team: 'Marseille',
            requested_away_team: 'Rennes',
            observed_home_team: 'Marseille',
            observed_away_team: 'Rennes',
            requested_match_date: '2026-05-17T19:00:00.000Z',
            observed_match_date: '2026-05-17T19:00:00.000Z',
            requested_status: 'finished',
            observed_status: 'scheduled',
        }),
        'status_mismatch'
    );
    assert.equal(
        mod.teamDateStatusMatchStatus({
            requested_home_team: 'Marseille',
            requested_away_team: 'Rennes',
            observed_home_team: 'Lens',
            observed_away_team: 'Lyon',
            requested_match_date: '2026-05-17T19:00:00.000Z',
            observed_match_date: '2026-05-18T19:00:00.000Z',
            requested_status: 'finished',
            observed_status: 'finished',
        }),
        'team_and_date_mismatch'
    );
    assert.equal(
        mod.teamDateStatusMatchStatus({
            requested_home_team: 'Marseille',
            requested_away_team: 'Rennes',
            observed_home_team: 'Lens',
            observed_away_team: 'Lyon',
            requested_match_date: '2026-05-17T19:00:00.000Z',
            observed_match_date: '2026-05-17T19:00:00.000Z',
            requested_status: 'finished',
            observed_status: 'scheduled',
        }),
        'team_and_status_mismatch'
    );
    assert.equal(
        mod.teamDateStatusMatchStatus({
            requested_home_team: 'PSG',
            requested_away_team: 'Auxerre',
            observed_home_team: 'Paris Saint-Germain',
            observed_away_team: 'Auxerre',
            requested_match_date: '2026-01-23T19:00:00.000Z',
            observed_match_date: '2026-01-24T19:00:00.000Z',
            requested_status: 'finished',
            observed_status: 'scheduled',
        }),
        'date_and_status_mismatch'
    );
});

test('runPlanning fails closed when L2V3E prerequisite replay fails and runCli help/invalid branches stay safe', async () => {
    const originalRunPlanning = l2v3e.runPlanning;
    l2v3e.runPlanning = async () => ({ ok: false, errors: ['PREREQ_FAILED'] });
    try {
        const blocked = await mod.runPlanning(validInput(), {
            manifest: manifest(),
            renewedProposal: renewedProposal(),
            sourceInventoryJson: sourceInventoryJson(),
            dbSnapshot: dbSnapshot(),
            writeManifest: false,
            writeProposal: false,
            writeReport: false,
            generatedAt: '2026-05-19T00:00:00.000Z',
        });
        assert.equal(blocked.ok, false);
        assert.equal(blocked.status, 4);
        assert.match(blocked.errors.join('\n'), /PREREQ_FAILED/);
    } finally {
        l2v3e.runPlanning = originalRunPlanning;
    }

    const stdout = [];
    const originalWrite = process.stdout.write;
    process.stdout.write = chunk => {
        stdout.push(String(chunk));
        return true;
    };
    try {
        const help = await mod.runCli(['--help']);
        assert.equal(help.status, 0);
        assert.match(
            stdout.join(''),
            /Usage: node scripts\/ops\/pageprops_v2_schedule_detail_identity_normalization_plan\.js/
        );
        stdout.length = 0;

        const invalid = await mod.runCli(['--manifest=wrong']);
        assert.equal(invalid.status, 2);
        assert.match(stdout.join(''), /"ok": false/);
        assert.match(stdout.join(''), /manifest must be/);
        assert.equal(stdout.join('').includes('__NEXT_DATA__'), false);
    } finally {
        process.stdout.write = originalWrite;
    }
});

test('CLI main module catch branch reports safe error without payload output', () => {
    const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'l2v3f-cli-'));
    const helpResult = require('node:child_process').spawnSync(process.execPath, [MODULE_PATH, '--help'], {
        cwd: tempDir,
        encoding: 'utf8',
    });
    assert.equal(helpResult.status, 0);
    assert.match(
        helpResult.stdout,
        /Usage: node scripts\/ops\/pageprops_v2_schedule_detail_identity_normalization_plan\.js/
    );
    assert.equal(helpResult.stdout.includes('__NEXT_DATA__'), false);

    const result = require('node:child_process').spawnSync(
        process.execPath,
        [
            MODULE_PATH,
            `--manifest=${mod.MANIFEST_PATH}`,
            `--renewed-proposal=${mod.RENEWED_PROPOSAL_PATH}`,
            `--report-output=${mod.REPORT_PATH}`,
            `--normalization-proposal-output=${mod.NORMALIZATION_PROPOSAL_PATH}`,
            `--source-inventory-reconciliation-report=${mod.SOURCE_RECONCILIATION_REPORT_PATH}`,
            '--source=fotmob',
            '--league-id=53',
            '--league-name=Ligue 1',
            '--season=2025/2026',
            '--raw-version=fotmob_pageprops_v2',
            '--hash-strategy=stable_pageprops_payload_v1',
            `--batch-id=${mod.BATCH_ID}`,
            '--target-count=50',
            '--planning-authorization=yes',
            '--schedule-detail-normalization-authorization=yes',
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
            '--request-delay-ms=0',
            '--retry=0',
        ],
        {
            cwd: tempDir,
            encoding: 'utf8',
        }
    );

    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /ENOENT/);
    assert.equal(result.stderr.includes('__NEXT_DATA__'), false);
    assert.equal(result.stderr.includes('"pageProps":'), false);
});
