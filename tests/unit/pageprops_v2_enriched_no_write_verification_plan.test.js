'use strict';
/* eslint-disable max-lines -- L2V3AB safety contract is audited together. */

const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const Module = require('node:module');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/pageprops_v2_enriched_no_write_verification_plan.js');

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

function candidate(index, overrides = {}) {
    const externalId = String(9000001 + index);
    return {
        target_id: `fotmob-pageprops-v2-ligue1-2025-2026-profile-001:53_20252026_${externalId}`,
        batch_id: 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001',
        source: 'fotmob',
        route: 'html_hydration',
        source_inventory_route: 'source_inventory',
        raw_data_version: 'fotmob_pageprops_v2',
        hash_strategy: 'stable_pageprops_payload_v1',
        match_id: `53_20252026_${externalId}`,
        external_id: externalId,
        league_id: 53,
        league_name: 'Ligue 1',
        season: '2025/2026',
        home_team: `Home ${index}`,
        away_team: `Away ${index}`,
        kickoff_time: '2025-08-15T18:45:00.000Z',
        match_date: '2025-08-15T18:45:00.000Z',
        source_page_url: null,
        source_page_url_base: null,
        source_url_fragment_external_id: null,
        source_slug: null,
        source_route_code: null,
        schedule_external_id: externalId,
        schedule_date: '2025-08-15T18:45:00.000Z',
        schedule_home_team: `Home ${index}`,
        schedule_away_team: `Away ${index}`,
        source_inventory_record_key: null,
        source_inventory_generated_at: 'unknown',
        identity_evidence_status: 'missing',
        write_execution_status: 'RECAPTURE_HASH_GATE_BLOCKED',
        raw_match_data_write_status: 'not_executed',
        required_next_step: 'renewed_controlled_pageprops_v2_raw_write_execution_blocked_review',
        raw_write_ready_for_execution: false,
        ...overrides,
    };
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
        candidate_targets: Array.from({ length: 50 }, (_, index) => candidate(index)),
        next_required_step: 'enriched_no_write_verification_planning',
        recommended_next_step: 'Phase 5.21L2V3AB: enriched no-write verification planning',
        required_next_step: 'renewed_controlled_pageprops_v2_raw_write_execution_blocked_review',
        write_execution_status: 'RECAPTURE_HASH_GATE_BLOCKED',
        raw_match_data_write_status: 'not_executed',
        raw_write_ready_for_execution: false,
        accepted_mapping_count: 0,
        requires_separate_identity_mapping_acceptance: true,
        requires_separate_baseline_acceptance: true,
        requires_separate_final_db_write_authorization: true,
        phase_5_21_l2v3aa_execution_status: 'completed_controlled_no_write_enriched_target_regeneration_execution',
        enriched_target_regeneration_execution_status:
            'completed_controlled_no_write_enriched_target_regeneration_execution',
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
        raw_write_guard_result: {
            raw_write_ready_for_execution: false,
            transaction_began: false,
            inserted_raw_match_data_count: 0,
        },
        ...overrides,
    };
}

function syntheticL2V3AAReport() {
    return `# Data Entrypoint Governance - Phase 5.21 L2V3AA

- regenerated_target_count=50
- blocked_target_count=0
- no_write_verification_required=true
- planned_mapping_key=target_id
`;
}

function sourceTextByPath() {
    return {
        'scripts/ops/renewed_pageprops_v2_raw_write_execute.js':
            'function validateManifestGate(manifest = {}) { required_next_step raw_match_data_write_status }',
    };
}

function stubRawWriteGate(manifest = {}) {
    return {
        ok: false,
        errors: [
            'required_next_step must be renewed_controlled_pageprops_v2_raw_write_execution',
            'write_execution_status must retain prior blocked_missing_matches_fk_prerequisite before retry',
            'raw_match_data_write_status must be not_executed before retry',
        ],
        manifest_summary: {
            required_next_step: manifest.required_next_step || null,
        },
    };
}

function buildSyntheticRunResult(overrides = {}) {
    return mod.runEnrichedNoWriteVerificationPlan({
        manifest: syntheticManifest(overrides.manifest || {}),
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

test('L2V3AB records enriched no-write verification planning semantics', () => {
    const result = buildSyntheticRunResult();
    const artifact = result.artifact;
    const manifest = result.updated_manifest;

    assert.equal(result.ok, true);
    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3AB');
    assert.equal(artifact.no_write, true);
    assert.equal(artifact.live_fetch_performed, false);
    assert.equal(artifact.network_request_performed, false);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_match_data_insert_performed, false);
    assert.equal(artifact.matches_write_performed, false);
    assert.equal(artifact.matches_external_id_modified, false);
    assert.equal(artifact.verification_execution_performed, false);
    assert.equal(artifact.identity_mapping_acceptance_performed, false);
    assert.equal(artifact.baseline_acceptance_performed, false);
    assert.equal(artifact.raw_write_retry_performed, false);
    assert.equal(artifact.enriched_target_count, 50);
    assert.equal(artifact.planned_verification_rule_count, mod.VERIFICATION_RULES.length);
    assert.equal(artifact.planned_verification_input_artifact_count, 5);
    assert.equal(artifact.accepted_mapping_count, 0);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(artifact.verification_execution_authorization_required, true);
    assert.equal(
        artifact.recommended_next_step,
        'Phase 5.21L2V3AC: controlled enriched no-write verification execution'
    );
    assert.equal(manifest.phase_5_21_l2v3ab_planning_status, artifact.artifact_status);
    assert.equal(manifest.enriched_no_write_verification_planning_status, artifact.artifact_status);
    assert.equal(manifest.accepted_mapping_count, 0);
    assert.equal(manifest.raw_write_ready_for_execution, false);
    assert.equal(manifest.next_required_step, 'controlled_enriched_no_write_verification_execution');
});

test('planned rules cover one-to-one integrity, uniqueness, metadata completeness, and source consistency', () => {
    const result = buildSyntheticRunResult();
    const analysis = result.artifact.verification_analysis;

    assert.equal(analysis.enriched_target_count, 50);
    assert.equal(analysis.duplicate_target_id_count, 0);
    assert.equal(analysis.duplicate_match_id_count, 0);
    assert.equal(analysis.duplicate_source_record_key_count, 0);
    assert.equal(analysis.duplicate_fragment_external_id_count, 0);
    assert.equal(analysis.missing_source_page_url_count, 0);
    assert.equal(analysis.missing_source_page_url_base_count, 0);
    assert.equal(analysis.missing_source_url_fragment_external_id_count, 0);
    assert.equal(analysis.missing_source_inventory_record_key_count, 0);
    assert.equal(analysis.fragment_schedule_id_mismatch_count, 0);
    assert.equal(analysis.non_regenerated_target_count, 0);
    assert.equal(analysis.non_empty_regeneration_blockers_count, 0);
    assert.equal(analysis.source_inventory_consistency_count, 50);
    assert.equal(analysis.one_to_one_integrity_expected, true);
});

test('verification plan remains non-accepted and non-executable even with complete identity evidence', () => {
    const result = buildSyntheticRunResult();
    const artifact = result.artifact;

    assert.equal(artifact.safety_contract.verification_plan_is_not_accepted_mapping, true);
    assert.equal(artifact.safety_contract.verification_plan_is_not_raw_write_authorization, true);
    assert.equal(artifact.safety_contract.verification_plan_is_not_identity_mapping_acceptance, true);
    assert.equal(artifact.safety_contract.verification_plan_is_not_baseline_acceptance, true);
    assert.equal(artifact.safety_contract.verification_plan_is_not_verification_execution, true);
    assert.equal(artifact.safety_contract.source_url_fragment_external_id_match_does_not_imply_accepted_mapping, true);
    assert.equal(
        artifact.safety_contract.identity_evidence_complete_does_not_imply_raw_write_ready_for_execution,
        true
    );
    assert.equal(artifact.accepted_mapping_count, 0);
    assert.equal(artifact.raw_write_ready_for_execution, false);
});

test('date rule context and raw write guard remain explicit blocking dependencies', () => {
    const result = buildSyntheticRunResult();

    assert.equal(result.artifact.date_rule_context.integrated_with_raw_write_guard, true);
    assert.deepEqual(result.artifact.date_rule_context.blocking_statuses, [
        'reverse_fixture_detected',
        'cross_season_slug_reuse',
        'unresolved_large_gap',
        'unknown',
    ]);
    assert.equal(result.artifact.raw_write_guard_analysis.ok, false);
    assert.match(
        result.artifact.raw_write_guard_analysis.errors_excerpt.join('\n'),
        /required_next_step|raw_match_data_write_status/i
    );
});

test('missing fields, duplicate keys, or blockers force continued planning', () => {
    const targets = Array.from({ length: 50 }, (_, index) =>
        enrichedTarget(
            index,
            index === 0
                ? {
                      source_inventory_record_key: 'duplicate-key',
                  }
                : index === 1
                  ? {
                        source_inventory_record_key: 'duplicate-key',
                    }
                  : index === 2
                    ? {
                          source_page_url_base: null,
                      }
                    : index === 3
                      ? {
                            regeneration_blockers: ['fragment_schedule_external_id_mismatch'],
                        }
                      : {}
        )
    );
    const result = buildSyntheticRunResult({
        l2v3aaArtifact: { enriched_targets: targets },
    });

    assert.equal(
        result.artifact.recommended_next_step,
        'Phase 5.21L2V3AC: continued enriched no-write verification planning'
    );
    assert.equal(result.artifact.next_required_step, 'continued_enriched_no_write_verification_planning');
    assert.equal(result.artifact.verification_analysis.duplicate_source_record_key_count, 1);
    assert.equal(result.artifact.verification_analysis.missing_source_page_url_base_count, 1);
    assert.equal(result.artifact.verification_analysis.non_empty_regeneration_blockers_count, 1);
    assert.match(
        result.artifact.verification_analysis.blocking_reasons.join('\n'),
        /duplicate_source_inventory_record_key_detected|missing_source_page_url_base_detected|regeneration_blockers_present/
    );
});

test('missing raw write guard helper forces helper implementation next step', () => {
    const result = buildSyntheticRunResult({
        sourceTextByPath: {
            'scripts/ops/renewed_pageprops_v2_raw_write_execute.js': 'raw write guard unavailable',
        },
    });

    assert.equal(
        result.artifact.recommended_next_step,
        'Phase 5.21L2V3AC: enriched no-write verification helper implementation'
    );
    assert.equal(result.artifact.next_required_step, 'enriched_no_write_verification_helper_implementation');
});

test('outputs avoid full raw data pageProps and source body payloads', () => {
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

test('helper refuses live fetch, DB write, acceptance, and payload flags', () => {
    const parsed = mod.parseArgs([
        '--allow-db-write=yes',
        '--allow-network=yes',
        '--allow-raw-match-data-write=yes',
        '--allow-matches-write=yes',
        '--accept-identity-mapping=yes',
        '--accept-baseline=yes',
        '--allow-raw-write-retry=yes',
        '--execute=yes',
        '--live-fetch=yes',
        '--print-full-json=yes',
    ]);
    const validation = mod.validateCliOptions(parsed);

    assert.equal(validation.ok, false);
    assert.match(validation.errors.join('\n'), /allow-db-write=yes is blocked/);
    assert.match(validation.errors.join('\n'), /allow-network=yes is blocked/);
    assert.match(validation.errors.join('\n'), /allow-raw-match-data-write=yes is blocked/);
    assert.match(validation.errors.join('\n'), /allow-matches-write=yes is blocked/);
    assert.match(validation.errors.join('\n'), /accept-identity-mapping=yes is blocked/);
    assert.match(validation.errors.join('\n'), /accept-baseline=yes is blocked/);
    assert.match(validation.errors.join('\n'), /allow-raw-write-retry=yes is blocked/);
    assert.match(validation.errors.join('\n'), /execute=yes is blocked/);
    assert.match(validation.errors.join('\n'), /live-fetch=yes is blocked/);
    assert.match(validation.errors.join('\n'), /print-full-json=yes is blocked/);
});

test('helper does not import network, DB, browser, proxy, odds, or harvest modules on load', t => {
    installImportGuard(t);
    const loaded = loadFreshModule();
    assert.equal(typeof loaded.runEnrichedNoWriteVerificationPlan, 'function');
});

test('validateInputs fails closed on unsafe manifest and invalid upstream artifacts', () => {
    const invalid = mod.validateInputs(
        syntheticManifest({
            next_required_step: 'wrong-step',
            raw_write_ready_for_execution: true,
            accepted_mapping_count: 1,
        }),
        syntheticL2V3AAArtifact({
            regenerated_target_count: 49,
            blocked_target_count: 1,
            one_to_one_mapping_count: 49,
            identity_evidence_complete_count: 49,
            raw_write_ready_target_count: 1,
            accepted_mapping_count: 1,
            raw_write_ready_for_execution: true,
            no_write_verification_required: false,
            enriched_targets: Array.from({ length: 49 }, (_, index) => enrichedTarget(index)),
        }),
        '# broken report',
        syntheticL2V3YArtifact({
            candidate_scope_count: 49,
            identity_evidence_complete_count: 49,
            accepted_mapping_count: 1,
            raw_write_ready_for_execution: true,
            source_inventory_metadata_records: Array.from({ length: 49 }, (_, index) => sourceRecord(index)),
        }),
        syntheticL2V3MArtifact({
            integrated_with_raw_write_guard: false,
            raw_write_ready_for_execution: true,
            accepted_mapping_count: 1,
            blocking_statuses: [],
        })
    );

    assert.equal(invalid.ok, false);
    assert.match(
        invalid.errors.join('\n'),
        /manifest next_required_step must be enriched_no_write_verification_planning/
    );
    assert.match(invalid.errors.join('\n'), /L2V3AA regenerated_target_count must be 50/);
    assert.match(invalid.errors.join('\n'), /L2V3AA report must record regenerated_target_count=50/);
    assert.match(invalid.errors.join('\n'), /L2V3Y candidate_scope_count must be 50/);
    assert.match(invalid.errors.join('\n'), /L2V3M integrated_with_raw_write_guard must remain true/);
});

test('runEnrichedNoWriteVerificationPlan can write outputs to explicit temp paths', () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'l2v3ab-verification-plan-'));
    const artifactPath = path.join(tmpDir, 'artifact.json');
    const reportPath = path.join(tmpDir, 'report.md');
    const manifestPath = path.join(tmpDir, 'manifest.json');

    try {
        const result = mod.runEnrichedNoWriteVerificationPlan({
            manifest: syntheticManifest(),
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
        assert.equal(JSON.parse(fs.readFileSync(artifactPath, 'utf8')).proposal_phase, 'Phase 5.21L2V3AB');
        assert.match(fs.readFileSync(reportPath, 'utf8'), /planned_verification_scope=/i);
        assert.equal(JSON.parse(fs.readFileSync(manifestPath, 'utf8')).raw_write_ready_for_execution, false);
    } finally {
        fs.rmSync(tmpDir, { recursive: true, force: true });
    }
});

test('CLI covers help, invalid options, and no-write success output', () => {
    let helpOutput = '';
    let invalidOutput = '';
    let successOutput = '';

    const helpStatus = mod.runCli(['--help'], { stdout: text => (helpOutput += text) });
    const invalidStatus = mod.runCli(['--unknown'], { stdout: text => (invalidOutput += text) });
    const successStatus = mod.runCli(['--write-files=false'], { stdout: text => (successOutput += text) });

    assert.equal(helpStatus, 0);
    assert.match(helpOutput, /L2V3AB is an enriched no-write verification planning phase/);
    assert.equal(invalidStatus, 2);
    assert.match(invalidOutput, /unknown arguments/);
    assert.equal(successStatus, 0);
    assert.match(successOutput, /"verification_execution_performed": false/);
    assert.match(successOutput, /"raw_write_ready_for_execution": false/);
});

test('main entrypoint prints help and blocked option output', () => {
    const help = spawnSync(process.execPath, [MODULE_PATH, '--help'], {
        cwd: PROJECT_ROOT,
        encoding: 'utf8',
    });
    assert.equal(help.status, 0);
    assert.match(help.stdout, /L2V3AB is an enriched no-write verification planning phase/);

    const blocked = spawnSync(process.execPath, [MODULE_PATH, '--allow-db-write=yes'], {
        cwd: PROJECT_ROOT,
        encoding: 'utf8',
    });
    assert.equal(blocked.status, 2);
    assert.match(blocked.stdout, /allow-db-write=yes is blocked/);
});

test('repository L2V3AB artifacts preserve no-write verification planning semantics when generated', () => {
    const artifactPath =
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.enriched_no_write_verification_plan.phase521l2v3ab.json';
    if (!fs.existsSync(path.join(PROJECT_ROOT, artifactPath))) {
        return;
    }

    const manifest = readJson('docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json');
    const artifact = readJson(artifactPath);
    const report = readText('docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AB.md');

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3AB');
    assert.equal(artifact.live_fetch_performed, false);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.verification_execution_performed, false);
    assert.equal(artifact.accepted_mapping_count, 0);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(artifact.enriched_target_count, 50);
    assert.equal(artifact.planned_verification_input_artifact_count, 5);
    assert.equal(manifest.phase_5_21_l2v3ab_planning_status, artifact.artifact_status);
    assert.equal(manifest.raw_write_ready_for_execution, false);
    assert.equal(manifest.accepted_mapping_count, 0);
    assert.ok(
        [
            'Phase 5.21L2V3AC: controlled enriched no-write verification execution',
            'Phase 5.21L2V3AD: identity mapping acceptance review planning',
            'Phase 5.21L2V3AE: identity mapping acceptance review execution',
            'Phase 5.21L2V3AF: baseline acceptance planning',
            'Phase 5.21L2V3AG: baseline acceptance execution',
        ].includes(manifest.recommended_next_step)
    );
    assert.ok(
        [
            'controlled_enriched_no_write_verification_execution',
            'identity_mapping_acceptance_review_planning',
            'identity_mapping_acceptance_review_execution',
            'baseline_acceptance_planning',
            'baseline_acceptance_execution',
        ].includes(manifest.next_required_step)
    );
    assert.match(report, /raw_write_guard_ok=false/i);
});
