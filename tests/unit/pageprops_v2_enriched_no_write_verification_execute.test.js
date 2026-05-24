'use strict';
/* eslint-disable max-lines -- L2V3AC safety contract is audited together. */

const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const Module = require('node:module');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/pageprops_v2_enriched_no_write_verification_execute.js');

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

function sourceRecord(index, overrides = {}) {
    const externalId = String(9000001 + index);
    return {
        target_id: `fotmob-pageprops-v2-ligue1-2025-2026-profile-001:53_20252026_${externalId}`,
        match_id: `53_20252026_${externalId}`,
        external_id: externalId,
        acquired_source_inventory_record: true,
        source_page_url: `/matches/home-${index}-away-${index}/route-${index}#${externalId}`,
        source_page_url_base: `/matches/home-${index}-away-${index}/route-${index}`,
        source_url_fragment_external_id: externalId,
        source_slug: `home-${index}-away-${index}`,
        source_route_code: `route-${index}`,
        schedule_external_id: externalId,
        schedule_date: '2025-08-15T18:45:00.000Z',
        schedule_home_team: `Home ${index}`,
        schedule_away_team: `Away ${index}`,
        source_inventory_record_key: `l1_api_data_leagues:overview.leagueOverviewMatches.${index}:${externalId}`,
        source_inventory_generated_at: '2026-05-21T14:20:00Z',
        identity_evidence_status: 'complete',
        acquisition_status: 'acquired',
        safe_error_summary: null,
        ...overrides,
    };
}

function enrichedTarget(index, overrides = {}) {
    const record = sourceRecord(index);
    return {
        target_id: record.target_id,
        match_id: record.match_id,
        external_id: record.external_id,
        schedule_external_id: record.schedule_external_id,
        source_page_url: record.source_page_url,
        source_page_url_base: record.source_page_url_base,
        source_url_fragment_external_id: record.source_url_fragment_external_id,
        source_slug: record.source_slug,
        source_route_code: record.source_route_code,
        schedule_date: record.schedule_date,
        schedule_home_team: record.schedule_home_team,
        schedule_away_team: record.schedule_away_team,
        source_inventory_record_key: record.source_inventory_record_key,
        source_inventory_generated_at: record.source_inventory_generated_at,
        identity_evidence_status: 'complete',
        enrichment_source_artifact:
            'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.controlled_source_inventory_acquisition_result.phase521l2v3y.json',
        regeneration_status: 'regenerated_no_write',
        regeneration_blockers: [],
        raw_write_ready_for_execution: false,
        ...overrides,
    };
}

function syntheticManifest(overrides = {}) {
    return {
        batch_id: 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001',
        next_required_step: 'controlled_enriched_no_write_verification_execution',
        recommended_next_step: 'Phase 5.21L2V3AC: controlled enriched no-write verification execution',
        required_next_step: 'renewed_controlled_pageprops_v2_raw_write_execution_blocked_review',
        write_execution_status: 'RECAPTURE_HASH_GATE_BLOCKED',
        raw_match_data_write_status: 'not_executed',
        raw_write_ready_for_execution: false,
        accepted_mapping_count: 0,
        identity_mapping_acceptance_performed: false,
        baseline_acceptance_performed: false,
        raw_write_retry_performed: false,
        requires_separate_identity_mapping_acceptance: true,
        requires_separate_baseline_acceptance: true,
        requires_separate_final_db_write_authorization: true,
        phase_5_21_l2v3ab_planning_status: 'completed_no_write_enriched_no_write_verification_planning',
        enriched_no_write_verification_planning_status: 'completed_no_write_enriched_no_write_verification_planning',
        ...overrides,
    };
}

function syntheticL2V3ABPlan(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3AB',
        artifact_status: 'completed_no_write_enriched_no_write_verification_planning',
        live_fetch_performed: false,
        db_write_performed: false,
        verification_execution_performed: false,
        enriched_target_count: 50,
        planned_verification_rule_count: 17,
        planned_verification_input_artifact_count: 5,
        accepted_mapping_count: 0,
        raw_write_ready_for_execution: false,
        verification_execution_authorization_required: true,
        next_required_step: 'controlled_enriched_no_write_verification_execution',
        recommended_next_step: 'Phase 5.21L2V3AC: controlled enriched no-write verification execution',
        ...overrides,
    };
}

function syntheticL2V3AAArtifact(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3AA',
        artifact_status: 'completed_controlled_no_write_enriched_target_regeneration_execution',
        regeneration_attempted: true,
        live_fetch_performed: false,
        db_write_performed: false,
        candidate_scope_count: 50,
        acquired_source_record_count: 50,
        regenerated_target_count: 50,
        blocked_target_count: 0,
        one_to_one_mapping_count: 50,
        identity_evidence_complete_count: 50,
        raw_write_ready_target_count: 0,
        accepted_mapping_count: 0,
        raw_write_ready_for_execution: false,
        no_write_verification_required: true,
        enriched_targets: Array.from({ length: 50 }, (_, index) => enrichedTarget(index)),
        ...overrides,
    };
}

function syntheticL2V3YArtifact(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3Y',
        artifact_status: 'completed_metadata_only_source_inventory_acquisition_execution',
        candidate_scope_count: 50,
        identity_evidence_complete_count: 50,
        accepted_mapping_count: 0,
        raw_write_ready_for_execution: false,
        source_inventory_metadata_records: Array.from({ length: 50 }, (_, index) => sourceRecord(index)),
        ...overrides,
    };
}

function syntheticL2V3MArtifact(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3M',
        integrated_with_raw_write_guard: true,
        raw_write_ready_for_execution: false,
        accepted_mapping_count: 0,
        blocking_statuses: ['reverse_fixture_detected', 'cross_season_slug_reuse', 'unresolved_large_gap', 'unknown'],
        review_only_statuses: ['timezone_only_mismatch', 'postponed_or_rescheduled_explained'],
        positive_evidence_statuses: ['date_match', 'same_utc_day'],
        ...overrides,
    };
}

function syntheticL2V3AAReport() {
    return `# Data Entrypoint Governance - Phase 5.21 L2V3AA

- regenerated_target_count=50
- blocked_target_count=0
- no_write_verification_required=true
`;
}

function sourceTextByPath() {
    return {
        'scripts/ops/renewed_pageprops_v2_raw_write_execute.js':
            'function validateManifestGate(manifest = {}) { required_next_step raw_match_data_write_status }',
    };
}

function stubRawWriteGate() {
    return {
        ok: false,
        errors: [
            'required_next_step must be renewed_controlled_pageprops_v2_raw_write_execution',
            'write_execution_status must retain prior blocked_missing_matches_fk_prerequisite before retry',
            'raw_match_data_write_status must be not_executed before retry',
        ],
    };
}

function buildSyntheticRunResult(overrides = {}) {
    return mod.runEnrichedNoWriteVerificationExecution({
        manifest: syntheticManifest(overrides.manifest || {}),
        l2v3abPlan: syntheticL2V3ABPlan(overrides.l2v3abPlan || {}),
        l2v3aaArtifact: syntheticL2V3AAArtifact(overrides.l2v3aaArtifact || {}),
        l2v3aaReport: overrides.l2v3aaReport || syntheticL2V3AAReport(),
        l2v3yArtifact: syntheticL2V3YArtifact(overrides.l2v3yArtifact || {}),
        l2v3mArtifact: syntheticL2V3MArtifact(overrides.l2v3mArtifact || {}),
        sourceTextByPath: overrides.sourceTextByPath || sourceTextByPath(),
        rawWriteGate: overrides.rawWriteGate || stubRawWriteGate,
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

test('L2V3AC records controlled no-write verification execution semantics', () => {
    const result = buildSyntheticRunResult();
    const artifact = result.artifact;
    const manifest = result.updated_manifest;

    assert.equal(result.ok, true);
    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3AC');
    assert.equal(artifact.phase_name, 'controlled_enriched_no_write_verification_execution');
    assert.equal(artifact.no_write, true);
    assert.equal(artifact.source_controlled_artifacts_only, true);
    assert.equal(artifact.verification_execution_performed, true);
    assert.equal(artifact.live_fetch_performed, false);
    assert.equal(artifact.detail_fetch_performed, false);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_match_data_insert_performed, false);
    assert.equal(artifact.matches_write_performed, false);
    assert.equal(artifact.matches_external_id_modified, false);
    assert.equal(artifact.identity_mapping_acceptance_performed, false);
    assert.equal(artifact.baseline_acceptance_performed, false);
    assert.equal(artifact.raw_write_retry_performed, false);
    assert.equal(artifact.accepted_mapping_count, 0);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(artifact.enriched_target_count, 50);
    assert.equal(artifact.verified_target_count, 50);
    assert.equal(artifact.failed_target_count, 0);
    assert.equal(artifact.blocked_target_count, 0);
    assert.equal(artifact.raw_write_ready_target_count, 0);
    assert.equal(artifact.raw_write_runner_blocked, true);
    assert.equal(artifact.validation_caution.broad_node_test_accidental_write_path_attempt_reviewed, true);
    assert.equal(artifact.validation_caution.accidental_write_path_attempt_blocked_by_db_constraints, true);
    assert.equal(artifact.validation_caution.accidental_attempt_was_not_successful_db_write, true);
    assert.equal(artifact.verification_status, 'passed_no_write_source_controlled');
    assert.equal(artifact.recommended_next_step, 'Phase 5.21L2V3AD: identity mapping acceptance review planning');
    assert.equal(manifest.phase_5_21_l2v3ac_execution_status, artifact.artifact_status);
    assert.equal(manifest.enriched_no_write_verification_execution_status, artifact.artifact_status);
    assert.equal(manifest.raw_write_ready_for_execution, false);
    assert.equal(manifest.accepted_mapping_count, 0);
    assert.ok(
        [
            'identity_mapping_acceptance_review_planning',
            'identity_mapping_acceptance_review_execution',
            'baseline_acceptance_planning',
            'baseline_acceptance_execution',
            'final_db_write_authorization_planning',
            'final_db_write_authorization_execution',
            'controlled_raw_match_data_write_execution_planning',
        ].includes(manifest.next_required_step)
    );
});

test('verification rules cover 50 targets, evidence, uniqueness, metadata, regeneration, and raw guard', () => {
    const result = buildSyntheticRunResult();
    const artifact = result.artifact;

    assert.equal(artifact.verification_rule_count, mod.VERIFICATION_RULES.length);
    assert.equal(artifact.verification_rule_results.length, 21);
    assert.equal(
        artifact.verification_rule_results.every(rule => rule.passed === true),
        true
    );
    assert.equal(artifact.source_url_evidence_complete_count, 50);
    assert.equal(artifact.fragment_schedule_id_match_count, 50);
    assert.equal(artifact.duplicate_target_id_count, 0);
    assert.equal(artifact.duplicate_match_id_count, 0);
    assert.equal(artifact.duplicate_source_inventory_record_key_count, 0);
    assert.equal(artifact.duplicate_fragment_external_id_count, 0);
    assert.equal(artifact.missing_required_metadata_count, 0);
    assert.equal(artifact.regeneration_status_valid_count, 50);
    assert.equal(artifact.regeneration_blockers_count, 0);
});

test('missing source URL evidence or schedule metadata blocks verification without acceptance', () => {
    const targets = Array.from({ length: 50 }, (_, index) =>
        enrichedTarget(
            index,
            index === 0
                ? { source_page_url: null }
                : index === 1
                  ? { source_page_url_base: null }
                  : index === 2
                    ? { source_url_fragment_external_id: null }
                    : index === 3
                      ? { source_inventory_record_key: null }
                      : index === 4
                        ? { schedule_date: null }
                        : index === 5
                          ? { schedule_home_team: null }
                          : index === 6
                            ? { schedule_away_team: null }
                            : {}
        )
    );
    const result = buildSyntheticRunResult({ l2v3aaArtifact: { enriched_targets: targets } });
    const artifact = result.artifact;

    assert.equal(artifact.verification_status, 'blocked');
    assert.equal(artifact.verified_target_count, 43);
    assert.equal(artifact.blocked_target_count, 7);
    assert.equal(artifact.missing_source_page_url_count, 1);
    assert.equal(artifact.missing_source_page_url_base_count, 1);
    assert.equal(artifact.missing_source_url_fragment_external_id_count, 1);
    assert.equal(artifact.missing_source_inventory_record_key_count, 1);
    assert.equal(artifact.missing_required_metadata_count, 7);
    assert.equal(artifact.accepted_mapping_count, 0);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(
        artifact.recommended_next_step,
        'Phase 5.21L2V3AD: enriched no-write verification blocker investigation'
    );
});

test('identity mismatch and duplicate keys block verification', () => {
    const targetZero = enrichedTarget(0);
    const targets = Array.from({ length: 50 }, (_, index) =>
        enrichedTarget(
            index,
            index === 0
                ? { source_url_fragment_external_id: 'mismatch' }
                : index === 1
                  ? { target_id: targetZero.target_id }
                  : index === 2
                    ? { match_id: targetZero.match_id }
                    : index === 3
                      ? { source_inventory_record_key: targetZero.source_inventory_record_key }
                      : index === 4
                        ? { source_url_fragment_external_id: enrichedTarget(5).source_url_fragment_external_id }
                        : {}
        )
    );
    const result = buildSyntheticRunResult({ l2v3aaArtifact: { enriched_targets: targets } });
    const artifact = result.artifact;

    assert.equal(artifact.verification_status, 'blocked');
    assert.equal(artifact.duplicate_target_id_count, 1);
    assert.equal(artifact.duplicate_match_id_count, 1);
    assert.equal(artifact.duplicate_source_inventory_record_key_count, 1);
    assert.equal(artifact.duplicate_fragment_external_id_count, 1);
    assert.equal(artifact.fragment_schedule_id_match_count, 48);
    assert.equal(artifact.raw_write_ready_target_count, 0);
    assert.equal(artifact.accepted_mapping_count, 0);
});

test('regeneration status, blockers, and raw-write-ready target block verification', () => {
    const targets = Array.from({ length: 50 }, (_, index) =>
        enrichedTarget(
            index,
            index === 0
                ? { regeneration_status: 'planned_only' }
                : index === 1
                  ? { regeneration_blockers: ['source_url_missing'] }
                  : index === 2
                    ? { raw_write_ready_for_execution: true }
                    : {}
        )
    );
    const result = buildSyntheticRunResult({ l2v3aaArtifact: { enriched_targets: targets } });
    const artifact = result.artifact;

    assert.equal(artifact.verification_status, 'blocked');
    assert.equal(artifact.regeneration_status_valid_count, 49);
    assert.equal(artifact.regeneration_blockers_count, 1);
    assert.equal(artifact.raw_write_ready_target_count, 1);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(artifact.accepted_mapping_count, 0);
});

test('raw write runner must remain blocked and cannot become a raw write authorization', () => {
    const result = buildSyntheticRunResult({
        rawWriteGate: () => ({ ok: true, errors: [] }),
    });
    const artifact = result.artifact;

    assert.equal(artifact.raw_write_runner_blocked, false);
    assert.equal(artifact.verification_status, 'blocked_raw_write_guard_review_required');
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(artifact.accepted_mapping_count, 0);
    assert.equal(artifact.safety_contract.verification_result_is_not_raw_write_authorization, true);
    assert.equal(artifact.recommended_next_step, 'Phase 5.21L2V3AD: raw write guard review planning');
});

test('validateInputs fails closed on missing authorization or unsafe acceptance/write state', () => {
    const invalid = mod.validateInputs(
        syntheticManifest({
            next_required_step: 'wrong-step',
            raw_write_ready_for_execution: true,
            accepted_mapping_count: 1,
            identity_mapping_acceptance_performed: true,
            baseline_acceptance_performed: true,
            raw_write_retry_performed: true,
        }),
        syntheticL2V3ABPlan({
            verification_execution_authorization_required: false,
            verification_execution_performed: true,
            enriched_target_count: 49,
        }),
        syntheticL2V3AAArtifact({
            regenerated_target_count: 49,
            accepted_mapping_count: 1,
            raw_write_ready_for_execution: true,
            enriched_targets: Array.from({ length: 49 }, (_, index) => enrichedTarget(index)),
        }),
        '# broken report',
        syntheticL2V3YArtifact({
            candidate_scope_count: 49,
            accepted_mapping_count: 1,
            raw_write_ready_for_execution: true,
            source_inventory_metadata_records: Array.from({ length: 49 }, (_, index) => sourceRecord(index)),
        }),
        syntheticL2V3MArtifact({
            integrated_with_raw_write_guard: false,
            raw_write_ready_for_execution: true,
            accepted_mapping_count: 1,
        })
    );

    assert.equal(invalid.ok, false);
    assert.match(
        invalid.errors.join('\n'),
        /manifest next_required_step must be controlled_enriched_no_write_verification_execution/
    );
    assert.match(invalid.errors.join('\n'), /L2V3AB verification_execution_authorization_required must remain true/);
    assert.match(invalid.errors.join('\n'), /L2V3AA regenerated_target_count must be 50/);
    assert.match(invalid.errors.join('\n'), /L2V3Y candidate_scope_count must be 50/);
    assert.match(invalid.errors.join('\n'), /L2V3M integrated_with_raw_write_guard must remain true/);
});

test('helper refuses live fetch, detail fetch, DB write, raw write, acceptance, and full payload flags', () => {
    const parsed = mod.parseArgs([
        '--allow-db-write=yes',
        '--allow-network=yes',
        '--allow-live-fetch=yes',
        '--allow-detail-fetch=yes',
        '--allow-raw-match-data-write=yes',
        '--allow-matches-write=yes',
        '--allow-matches-external-id-write=yes',
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
    assert.match(validation.errors.join('\n'), /accept-identity-mapping=yes is blocked/);
    assert.match(validation.errors.join('\n'), /accept-baseline=yes is blocked/);
    assert.match(validation.errors.join('\n'), /allow-raw-write-retry=yes is blocked/);
    assert.match(validation.errors.join('\n'), /execute-raw-write=yes is blocked/);
    assert.match(validation.errors.join('\n'), /print-full-json=yes is blocked/);
});

test('helper does not import network, DB, browser, proxy, odds, harvest, or child process modules on load', t => {
    installImportGuard(t);
    const loaded = loadFreshModule();
    assert.equal(typeof loaded.runEnrichedNoWriteVerificationExecution, 'function');
});

test('outputs avoid full raw data, pageProps, source body, and HTML payloads', () => {
    const result = buildSyntheticRunResult();
    const texts = [JSON.stringify(result.artifact), result.report, JSON.stringify(result.updated_manifest)];

    for (const text of texts) {
        assert.equal(text.includes('"raw_data":'), false);
        assert.equal(text.includes('"pageProps":'), false);
        assert.equal(text.includes('__NEXT_DATA__'), false);
        assert.equal(text.includes('<!DOCTYPE'), false);
        assert.equal(text.includes('"source_body":'), false);
        assert.equal(text.includes('"full_json":'), false);
    }
});

test('runEnrichedNoWriteVerificationExecution can write outputs to explicit temp paths', () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'l2v3ac-verification-execute-'));
    const artifactPath = path.join(tmpDir, 'artifact.json');
    const reportPath = path.join(tmpDir, 'report.md');
    const manifestPath = path.join(tmpDir, 'manifest.json');

    try {
        const result = mod.runEnrichedNoWriteVerificationExecution({
            manifest: syntheticManifest(),
            l2v3abPlan: syntheticL2V3ABPlan(),
            l2v3aaArtifact: syntheticL2V3AAArtifact(),
            l2v3aaReport: syntheticL2V3AAReport(),
            l2v3yArtifact: syntheticL2V3YArtifact(),
            l2v3mArtifact: syntheticL2V3MArtifact(),
            sourceTextByPath: sourceTextByPath(),
            rawWriteGate: stubRawWriteGate,
            writeFiles: true,
            artifactOutputPath: artifactPath,
            reportOutputPath: reportPath,
            manifestOutputPath: manifestPath,
        });

        assert.equal(result.ok, true);
        assert.equal(JSON.parse(fs.readFileSync(artifactPath, 'utf8')).proposal_phase, 'Phase 5.21L2V3AC');
        assert.match(fs.readFileSync(reportPath, 'utf8'), /verification_execution_performed=true/i);
        assert.equal(JSON.parse(fs.readFileSync(manifestPath, 'utf8')).raw_write_ready_for_execution, false);
    } finally {
        fs.rmSync(tmpDir, { recursive: true, force: true });
    }
});

test('CLI covers help, invalid options, and no-write execution output', () => {
    let helpOutput = '';
    let invalidOutput = '';
    let successOutput = '';

    const helpStatus = mod.runCli(['--help'], { stdout: text => (helpOutput += text) });
    const invalidStatus = mod.runCli(['--unknown'], { stdout: text => (invalidOutput += text) });
    const successStatus = mod.runCli(['--write-files=false'], { stdout: text => (successOutput += text) });

    assert.equal(helpStatus, 0);
    assert.match(helpOutput, /L2V3AC is a controlled enriched no-write verification execution phase/);
    assert.equal(invalidStatus, 2);
    assert.match(invalidOutput, /unknown arguments/);
    if (successStatus === 0) {
        assert.match(successOutput, /"verification_execution_performed": true/);
        assert.match(successOutput, /"raw_write_ready_for_execution": false/);
    } else {
        assert.equal(successStatus, 3);
        assert.match(successOutput, /baseline_acceptance_performed must remain false/i);
    }
});

test('main entrypoint prints help and blocked option output', () => {
    const help = spawnSync(process.execPath, [MODULE_PATH, '--help'], {
        cwd: PROJECT_ROOT,
        encoding: 'utf8',
    });
    assert.equal(help.status, 0);
    assert.match(help.stdout, /L2V3AC is a controlled enriched no-write verification execution phase/);

    const blocked = spawnSync(process.execPath, [MODULE_PATH, '--allow-db-write=yes'], {
        cwd: PROJECT_ROOT,
        encoding: 'utf8',
    });
    assert.equal(blocked.status, 2);
    assert.match(blocked.stdout, /allow-db-write=yes is blocked/);
});

test('repository L2V3AC artifacts preserve controlled no-write verification execution semantics when generated', () => {
    const artifactPath =
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.enriched_no_write_verification_result.phase521l2v3ac.json';
    if (!fs.existsSync(path.join(PROJECT_ROOT, artifactPath))) {
        return;
    }

    const manifest = readJson('docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json');
    const artifact = readJson(artifactPath);
    const report = readText('docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AC.md');

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3AC');
    assert.equal(artifact.verification_execution_performed, true);
    assert.equal(artifact.live_fetch_performed, false);
    assert.equal(artifact.detail_fetch_performed, false);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.accepted_mapping_count, 0);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(artifact.enriched_target_count, 50);
    assert.equal(artifact.verified_target_count, 50);
    assert.equal(artifact.raw_write_ready_target_count, 0);
    assert.equal(artifact.raw_write_runner_blocked, true);
    assert.equal(manifest.phase_5_21_l2v3ac_execution_status, artifact.artifact_status);
    assert.equal(manifest.raw_write_ready_for_execution, false);
    assert.equal(manifest.accepted_mapping_count, 0);
    assert.ok(
        [
            'identity_mapping_acceptance_review_planning',
            'identity_mapping_acceptance_review_execution',
            'baseline_acceptance_planning',
            'baseline_acceptance_execution',
            'final_db_write_authorization_planning',
            'final_db_write_authorization_execution',
            'controlled_raw_match_data_write_execution_planning',
        ].includes(manifest.next_required_step)
    );
    assert.match(report, /verification_status=passed_no_write_source_controlled/i);
    assert.match(report, /broad node --test accidental write-path attempt reviewed=true/i);
    assert.match(report, /accidental attempt was not a successful DB write/i);
});
