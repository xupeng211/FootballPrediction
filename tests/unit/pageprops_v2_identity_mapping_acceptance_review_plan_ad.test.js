'use strict';
/* eslint-disable max-lines -- L2V3AD safety contract is audited together. */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const Module = require('node:module');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/pageprops_v2_identity_mapping_acceptance_review_plan.js');

function loadFreshModule() {
    delete require.cache[require.resolve(MODULE_PATH)];
    return require(MODULE_PATH);
}

const mod = loadFreshModule();

function readJson(repoPath) {
    return JSON.parse(fs.readFileSync(path.join(PROJECT_ROOT, repoPath), 'utf8'));
}

function readText(repoPath) {
    return fs.readFileSync(path.join(PROJECT_ROOT, repoPath), 'utf8');
}

function enrichedTarget(index, overrides = {}) {
    const externalId = String(9000001 + index);
    return {
        target_id: `fotmob-pageprops-v2-ligue1-2025-2026-profile-001:53_20252026_${externalId}`,
        match_id: `53_20252026_${externalId}`,
        external_id: externalId,
        schedule_external_id: externalId,
        source_page_url: `/matches/home-${index}-away-${index}/route-${index}#${externalId}`,
        source_page_url_base: `/matches/home-${index}-away-${index}/route-${index}`,
        source_url_fragment_external_id: externalId,
        source_slug: `home-${index}-away-${index}`,
        source_route_code: `route-${index}`,
        schedule_date: '2025-08-15T18:45:00.000Z',
        schedule_home_team: `Home ${index}`,
        schedule_away_team: `Away ${index}`,
        source_inventory_record_key: `l1_api_data_leagues:overview.leagueOverviewMatches.${index}:${externalId}`,
        source_inventory_generated_at: '2026-05-21T14:20:00Z',
        identity_evidence_status: 'complete',
        enrichment_source_artifact:
            'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.controlled_source_inventory_acquisition_result.phase521l2v3y.json',
        regeneration_status: 'regenerated_no_write',
        regeneration_blockers: [],
        raw_write_ready_for_execution: false,
        ...overrides,
    };
}

function sourceRecord(index, overrides = {}) {
    const target = enrichedTarget(index);
    return {
        target_id: target.target_id,
        match_id: target.match_id,
        external_id: target.external_id,
        acquired_source_inventory_record: true,
        source_page_url: target.source_page_url,
        source_page_url_base: target.source_page_url_base,
        source_url_fragment_external_id: target.source_url_fragment_external_id,
        schedule_external_id: target.schedule_external_id,
        schedule_date: target.schedule_date,
        schedule_home_team: target.schedule_home_team,
        schedule_away_team: target.schedule_away_team,
        source_inventory_record_key: target.source_inventory_record_key,
        identity_evidence_status: 'complete',
        ...overrides,
    };
}

function verificationResult(index, overrides = {}) {
    const target = enrichedTarget(index);
    return {
        target_id: target.target_id,
        match_id: target.match_id,
        schedule_external_id: target.schedule_external_id,
        source_url_fragment_external_id: target.source_url_fragment_external_id,
        verification_status: 'verified',
        failure_reasons: [],
        ...overrides,
    };
}

function manifest(overrides = {}) {
    return {
        next_required_step: 'identity_mapping_acceptance_review_planning',
        recommended_next_step: 'Phase 5.21L2V3AD: identity mapping acceptance review planning',
        raw_write_ready_for_execution: false,
        accepted_mapping_count: 0,
        identity_mapping_acceptance_performed: false,
        baseline_acceptance_performed: false,
        raw_write_retry_performed: false,
        requires_separate_identity_mapping_acceptance: true,
        requires_separate_baseline_acceptance: true,
        requires_separate_final_db_write_authorization: true,
        ...overrides,
    };
}

function l2v3acArtifact(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3AC',
        verification_execution_performed: true,
        live_fetch_performed: false,
        detail_fetch_performed: false,
        db_write_performed: false,
        verification_status: 'passed_no_write_source_controlled',
        verified_target_count: 50,
        failed_target_count: 0,
        blocked_target_count: 0,
        source_url_evidence_complete_count: 50,
        fragment_schedule_id_match_count: 50,
        duplicate_target_id_count: 0,
        duplicate_match_id_count: 0,
        duplicate_source_inventory_record_key_count: 0,
        duplicate_fragment_external_id_count: 0,
        missing_required_metadata_count: 0,
        regeneration_status_valid_count: 50,
        regeneration_blockers_count: 0,
        raw_write_ready_target_count: 0,
        raw_write_runner_blocked: true,
        accepted_mapping_count: 0,
        raw_write_ready_for_execution: false,
        verification_analysis: {
            target_results: Array.from({ length: 50 }, (_, index) => verificationResult(index)),
        },
        ...overrides,
    };
}

function l2v3aaArtifact(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3AA',
        regenerated_target_count: 50,
        accepted_mapping_count: 0,
        raw_write_ready_for_execution: false,
        enriched_targets: Array.from({ length: 50 }, (_, index) => enrichedTarget(index)),
        ...overrides,
    };
}

function l2v3yArtifact(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3Y',
        candidate_scope_count: 50,
        accepted_mapping_count: 0,
        raw_write_ready_for_execution: false,
        source_inventory_metadata_records: Array.from({ length: 50 }, (_, index) => sourceRecord(index)),
        ...overrides,
    };
}

function l2v3mArtifact(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3M',
        integrated_with_raw_write_guard: true,
        accepted_mapping_count: 0,
        raw_write_ready_for_execution: false,
        blocking_statuses: ['reverse_fixture_detected', 'cross_season_slug_reuse', 'unresolved_large_gap', 'unknown'],
        review_only_statuses: ['timezone_only_mismatch', 'postponed_or_rescheduled_explained'],
        positive_evidence_statuses: ['date_match', 'same_utc_day'],
        ...overrides,
    };
}

function priorArtifacts(overrides = {}) {
    return {
        l2v3iArtifact: { accepted_mapping_count: 0, raw_write_ready_for_execution: false },
        l2v3jArtifact: { accepted_mapping_count: 0, raw_write_ready_for_execution: false },
        l2v3kArtifact: { accepted_mapping_count: 0, raw_write_ready_for_execution: false },
        ...overrides,
    };
}

function runSynthetic(overrides = {}) {
    return mod.runIdentityMappingAcceptanceReviewPlan({
        manifest: manifest(overrides.manifest || {}),
        l2v3acArtifact: l2v3acArtifact(overrides.l2v3acArtifact || {}),
        l2v3aaArtifact: l2v3aaArtifact(overrides.l2v3aaArtifact || {}),
        l2v3yArtifact: l2v3yArtifact(overrides.l2v3yArtifact || {}),
        l2v3mArtifact: l2v3mArtifact(overrides.l2v3mArtifact || {}),
        priorArtifacts: priorArtifacts(overrides.priorArtifacts || {}),
        sourceTextByPath: {},
        writeFiles: false,
    });
}

function installImportGuard(t) {
    const originalLoad = Module._load;
    Module._load = function patchedLoad(request, parent, isMain) {
        if (
            /pg|http|https|playwright|puppeteer|ProductionHarvester|odds_harvest_pipeline|child_process/i.test(request)
        ) {
            throw new Error(`blocked import: ${request}`);
        }
        return originalLoad.call(this, request, parent, isMain);
    };
    t.after(() => {
        Module._load = originalLoad;
    });
}

test('L2V3AD is identity mapping acceptance review planning-only', () => {
    const result = runSynthetic();
    const artifact = result.artifact;
    const updatedManifest = result.updated_manifest;

    assert.equal(result.ok, true);
    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3AD');
    assert.equal(artifact.phase_name, 'identity_mapping_acceptance_review_planning');
    assert.equal(artifact.planning_only, true);
    assert.equal(artifact.source_controlled_artifacts_only, true);
    assert.equal(artifact.live_fetch_performed, false);
    assert.equal(artifact.detail_fetch_performed, false);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_match_data_insert_performed, false);
    assert.equal(artifact.matches_write_performed, false);
    assert.equal(artifact.matches_external_id_modified, false);
    assert.equal(artifact.acceptance_execution_performed, false);
    assert.equal(artifact.identity_mapping_acceptance_performed, false);
    assert.equal(artifact.baseline_acceptance_performed, false);
    assert.equal(artifact.raw_write_retry_performed, false);
    assert.equal(artifact.accepted_mapping_count, 0);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(artifact.human_review_required, true);
    assert.equal(updatedManifest.identity_mapping_acceptance_performed, false);
    assert.equal(updatedManifest.raw_write_ready_for_execution, false);
});

test('50 verified targets become review-ready candidates but are not accepted mappings', () => {
    const artifact = runSynthetic().artifact;

    assert.equal(artifact.verification_passed_target_count, 50);
    assert.equal(artifact.acceptance_review_candidate_count, 50);
    assert.equal(artifact.review_ready_count, 50);
    assert.equal(artifact.review_blocked_count, 0);
    assert.equal(artifact.planned_acceptance_rule_count, 12);
    assert.equal(artifact.planned_blocking_rule_count, 12);
    for (const entry of artifact.review_plan_entries) {
        assert.equal(entry.review_status, 'review_ready');
        assert.equal(entry.acceptance_status, 'not_accepted_planning_only');
        assert.equal(entry.reviewer_required, true);
        assert.equal(entry.accepted_by, null);
        assert.equal(entry.accepted_at, null);
        assert.deepEqual(entry.acceptance_blockers, []);
        assert.equal(entry.raw_write_eligible_after_acceptance, false);
    }
});

test('review-ready and complete identity evidence do not imply acceptance or raw-write readiness', () => {
    const artifact = runSynthetic().artifact;

    assert.equal(artifact.safety_contract.review_ready_is_not_accepted, true);
    assert.equal(artifact.safety_contract.verification_passed_is_not_accepted_mapping, true);
    assert.equal(artifact.safety_contract.source_url_fragment_external_id_match_is_not_accepted_mapping, true);
    assert.equal(
        artifact.safety_contract.identity_evidence_complete_does_not_imply_raw_write_ready_for_execution,
        true
    );
    assert.equal(artifact.accepted_mapping_count, 0);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(artifact.baseline_acceptance_performed, false);
    assert.equal(artifact.raw_write_retry_performed, false);
});

test('missing source URL evidence blocks target review without accepting mapping', () => {
    const targets = Array.from({ length: 50 }, (_, index) =>
        enrichedTarget(index, index === 0 ? { source_page_url: null } : {})
    );
    const artifact = runSynthetic({ l2v3aaArtifact: { enriched_targets: targets } }).artifact;

    assert.equal(artifact.review_ready_count, 49);
    assert.equal(artifact.review_blocked_count, 1);
    assert.equal(artifact.review_plan_entries[0].review_status, 'review_blocked');
    assert.equal(artifact.review_plan_entries[0].acceptance_blockers.includes('missing_source_url_evidence'), true);
    assert.equal(artifact.accepted_mapping_count, 0);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(artifact.recommended_next_step, 'Phase 5.21L2V3AE: identity mapping acceptance blocker investigation');
});

test('fragment mismatch, duplicate keys, and raw write runner readiness block review planning', () => {
    const duplicate = enrichedTarget(0);
    const targets = Array.from({ length: 50 }, (_, index) =>
        enrichedTarget(
            index,
            index === 0
                ? { source_url_fragment_external_id: 'mismatch' }
                : index === 1
                  ? { target_id: duplicate.target_id }
                  : index === 2
                    ? { source_inventory_record_key: duplicate.source_inventory_record_key }
                    : index === 3
                      ? { raw_write_ready_for_execution: true }
                      : {}
        )
    );
    const artifact = runSynthetic({
        l2v3aaArtifact: { enriched_targets: targets },
        l2v3acArtifact: { raw_write_runner_blocked: true },
    }).artifact;

    const blockers = artifact.review_plan_entries.flatMap(entry => entry.acceptance_blockers);
    assert.equal(blockers.includes('fragment_schedule_mismatch'), true);
    assert.equal(blockers.includes('duplicate_target_or_match_id'), true);
    assert.equal(blockers.includes('duplicate_source_key'), true);
    assert.equal(blockers.includes('raw_write_target_unexpectedly_ready'), true);
    assert.equal(artifact.accepted_mapping_count, 0);
    assert.equal(artifact.raw_write_ready_for_execution, false);
});

test('additional blocker branches stay visible without accepting identity mapping', () => {
    const targets = Array.from({ length: 50 }, (_, index) =>
        enrichedTarget(
            index,
            index === 4
                ? { source_url_fragment_external_id: enrichedTarget(5).source_url_fragment_external_id }
                : index === 5
                  ? { schedule_date: '', regeneration_status: 'blocked', regeneration_blockers: ['date_rule'] }
                  : {}
        )
    );
    const sourceRecords = Array.from({ length: 49 }, (_, index) => sourceRecord(index));
    const candidateAnalysis = mod.analyzeAcceptanceReviewCandidates(
        l2v3acArtifact({ raw_write_runner_blocked: false }),
        l2v3aaArtifact({ enriched_targets: targets }),
        l2v3yArtifact({ source_inventory_metadata_records: sourceRecords })
    );

    const blockers = candidateAnalysis.review_plan_entries.flatMap(entry => entry.acceptance_blockers);
    assert.equal(blockers.includes('duplicate_fragment_external_id'), true);
    assert.equal(blockers.includes('schedule_team_date_mismatch'), true);
    assert.equal(blockers.includes('regeneration_status_not_clean'), true);
    assert.equal(blockers.includes('regeneration_blockers_present'), true);
    assert.equal(blockers.includes('source_inventory_record_missing'), true);
    assert.equal(blockers.includes('raw_write_runner_unexpectedly_ready'), true);
    assert.equal(candidateAnalysis.review_blocked_count > 0, true);
});

test('candidate count drift keeps the plan in continued planning without acceptance', () => {
    const result = runSynthetic({
        l2v3aaArtifact: {
            enriched_targets: Array.from({ length: 49 }, (_, index) => enrichedTarget(index)),
        },
    });

    assert.equal(result.ok, true);
    assert.equal(result.artifact.acceptance_review_candidate_count, 49);
    assert.equal(
        result.artifact.recommended_next_step,
        'Phase 5.21L2V3AE: continued identity mapping acceptance review planning'
    );
    assert.equal(result.artifact.next_required_step, 'continued_identity_mapping_acceptance_review_planning');
    assert.equal(result.artifact.accepted_mapping_count, 0);
});

test('argument parser handles explicit safe false values and reports positional arguments', () => {
    const parsed = mod.parseArgs([
        'positional',
        '--write-files=no',
        '--allow-db-write=no',
        '--allow-live-fetch=off',
        '--allow-detail-fetch',
        'false',
    ]);
    const validation = mod.validateCliOptions(parsed);

    assert.equal(parsed.writeFiles, false);
    assert.equal(parsed.allowDbWrite, false);
    assert.equal(parsed.allowLiveFetch, false);
    assert.equal(parsed.allowDetailFetch, false);
    assert.deepEqual(parsed.unknown, ['positional']);
    assert.equal(validation.ok, false);
    assert.match(validation.errors.join('\n'), /unknown arguments: positional/);
});

test('validateInputs fails closed on unsafe execution, acceptance, baseline, or raw-write state', () => {
    const invalid = mod.validateInputs(
        manifest({
            next_required_step: 'raw_write_retry',
            raw_write_ready_for_execution: true,
            accepted_mapping_count: 1,
            identity_mapping_acceptance_performed: true,
            baseline_acceptance_performed: true,
            raw_write_retry_performed: true,
        }),
        l2v3acArtifact({
            verification_execution_performed: false,
            verification_status: 'blocked',
            verified_target_count: 49,
            failed_target_count: 1,
            raw_write_runner_blocked: false,
        }),
        l2v3aaArtifact({ regenerated_target_count: 49, accepted_mapping_count: 1 }),
        l2v3yArtifact({ candidate_scope_count: 49, raw_write_ready_for_execution: true }),
        l2v3mArtifact({ integrated_with_raw_write_guard: false, accepted_mapping_count: 1 }),
        priorArtifacts({ l2v3kArtifact: { accepted_mapping_count: 1 } })
    );

    assert.equal(invalid.ok, false);
    assert.match(invalid.errors.join('\n'), /manifest next_required_step/);
    assert.match(invalid.errors.join('\n'), /L2V3AC verification_execution_performed/);
    assert.match(invalid.errors.join('\n'), /L2V3AC verification_status/);
    assert.match(invalid.errors.join('\n'), /L2V3AA regenerated_target_count/);
    assert.match(invalid.errors.join('\n'), /L2V3Y candidate_scope_count/);
    assert.match(invalid.errors.join('\n'), /L2V3M integrated_with_raw_write_guard/);
    assert.match(invalid.errors.join('\n'), /l2v3kArtifact/);
});

test('helper refuses live fetch, detail fetch, DB write, raw write, acceptance, baseline, and payload flags', () => {
    const parsed = mod.parseArgs([
        '--allow-db-write=yes',
        '--allow-network=yes',
        '--allow-live-fetch=yes',
        '--allow-detail-fetch=yes',
        '--allow-raw-match-data-write=yes',
        '--allow-matches-write=yes',
        '--allow-matches-external-id-write=yes',
        '--execute-acceptance=yes',
        '--accept-identity-mapping=yes',
        '--accept-baseline=yes',
        '--allow-raw-write-retry=yes',
        '--execute-raw-write=yes',
        '--print-full-json=yes',
    ]);
    const validation = mod.validateCliOptions(parsed);

    assert.equal(validation.ok, false);
    assert.match(validation.errors.join('\n'), /allow-db-write=yes is blocked/);
    assert.match(validation.errors.join('\n'), /allow-network=yes is blocked/);
    assert.match(validation.errors.join('\n'), /allow-live-fetch=yes is blocked/);
    assert.match(validation.errors.join('\n'), /allow-detail-fetch=yes is blocked/);
    assert.match(validation.errors.join('\n'), /allow-raw-match-data-write=yes is blocked/);
    assert.match(validation.errors.join('\n'), /allow-matches-write=yes is blocked/);
    assert.match(validation.errors.join('\n'), /allow-matches-external-id-write=yes is blocked/);
    assert.match(validation.errors.join('\n'), /execute-acceptance=yes is blocked/);
    assert.match(validation.errors.join('\n'), /accept-identity-mapping=yes is blocked/);
    assert.match(validation.errors.join('\n'), /accept-baseline=yes is blocked/);
    assert.match(validation.errors.join('\n'), /allow-raw-write-retry=yes is blocked/);
    assert.match(validation.errors.join('\n'), /execute-raw-write=yes is blocked/);
    assert.match(validation.errors.join('\n'), /print-full-json=yes is blocked/);
});

test('helper does not import network, DB, browser, proxy, harvest, odds, or child process modules on load', t => {
    installImportGuard(t);
    const loaded = loadFreshModule();
    assert.equal(typeof loaded.runIdentityMappingAcceptanceReviewPlan, 'function');
});

test('outputs avoid full raw data, pageProps, source body, and HTML payloads', () => {
    const result = runSynthetic();
    for (const text of [JSON.stringify(result.artifact), result.report, JSON.stringify(result.updated_manifest)]) {
        assert.equal(text.includes('"raw_data":'), false);
        assert.equal(text.includes('"pageProps":'), false);
        assert.equal(text.includes('__NEXT_DATA__'), false);
        assert.equal(text.includes('<!DOCTYPE'), false);
        assert.equal(text.includes('"source_body":'), false);
        assert.equal(text.includes('"full_json":'), false);
    }
});

test('runIdentityMappingAcceptanceReviewPlan can write planning outputs to explicit temp paths', () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'l2v3ad-acceptance-review-plan-'));
    const artifactPath = path.join(tmpDir, 'artifact.json');
    const reportPath = path.join(tmpDir, 'report.md');
    const manifestPath = path.join(tmpDir, 'manifest.json');

    try {
        const result = mod.runIdentityMappingAcceptanceReviewPlan({
            manifest: manifest(),
            l2v3acArtifact: l2v3acArtifact(),
            l2v3aaArtifact: l2v3aaArtifact(),
            l2v3yArtifact: l2v3yArtifact(),
            l2v3mArtifact: l2v3mArtifact(),
            priorArtifacts: priorArtifacts(),
            writeFiles: true,
            artifactOutputPath: artifactPath,
            reportOutputPath: reportPath,
            manifestOutputPath: manifestPath,
        });

        assert.equal(result.ok, true);
        assert.equal(JSON.parse(fs.readFileSync(artifactPath, 'utf8')).proposal_phase, 'Phase 5.21L2V3AD');
        assert.match(fs.readFileSync(reportPath, 'utf8'), /planning_only=true/i);
        assert.equal(JSON.parse(fs.readFileSync(manifestPath, 'utf8')).raw_write_ready_for_execution, false);
    } finally {
        fs.rmSync(tmpDir, { recursive: true, force: true });
    }
});

test('CLI covers help and invalid options after repository phase may have advanced', () => {
    let helpOutput = '';
    let invalidOutput = '';

    const helpStatus = mod.runCli(['--help'], { stdout: text => (helpOutput += text) });
    const invalidStatus = mod.runCli(['--unknown'], { stdout: text => (invalidOutput += text) });

    assert.equal(helpStatus, 0);
    assert.match(helpOutput, /identity mapping acceptance review planning-only phase/);
    assert.equal(invalidStatus, 2);
    assert.match(invalidOutput, /unknown arguments/);
});

test('repository L2V3AD artifacts preserve planning-only safety when generated', () => {
    const artifactPath =
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.identity_mapping_acceptance_review_plan.phase521l2v3ad.json';
    if (!fs.existsSync(path.join(PROJECT_ROOT, artifactPath))) {
        return;
    }

    const manifestJson = readJson('docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json');
    const artifact = readJson(artifactPath);
    const report = readText('docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AD.md');

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3AD');
    assert.equal(artifact.planning_only, true);
    assert.equal(artifact.acceptance_execution_performed, false);
    assert.equal(artifact.identity_mapping_acceptance_performed, false);
    assert.equal(artifact.accepted_mapping_count, 0);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(artifact.acceptance_review_candidate_count, 50);
    assert.equal(artifact.review_ready_count, 50);
    assert.equal(artifact.review_blocked_count, 0);
    assert.equal(artifact.safety_contract.review_ready_is_not_accepted, true);
    assert.equal(manifestJson.phase_5_21_l2v3ad_planning_status, artifact.planning_status);
    assert.equal(manifestJson.accepted_mapping_count, 0);
    assert.equal(manifestJson.raw_write_ready_for_execution, false);
    assert.equal(
        [
            'identity_mapping_acceptance_review_execution',
            'baseline_acceptance_planning',
            'baseline_acceptance_execution',
            'final_db_write_authorization_planning',
            'final_db_write_authorization_execution',
            'controlled_raw_match_data_write_execution_planning',
            'controlled_raw_match_data_write_execution',
            'controlled_raw_write_execution_blocker_resolution',
            'continued_controlled_raw_write_planning',
            'controlled_payload_source_declaration_planning',
        ].includes(manifestJson.next_required_step),
        true
    );
    assert.match(report, /review_ready is not accepted mapping/i);
});
