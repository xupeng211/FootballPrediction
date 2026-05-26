'use strict';
/* eslint-disable max-lines -- L2V3AA safety contract is audited together. */

const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const Module = require('node:module');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/pageprops_v2_enriched_target_regeneration_execute.js');
const rawWrite = require('../../scripts/ops/renewed_pageprops_v2_raw_write_execute');

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

function syntheticManifest(overrides = {}) {
    return {
        batch_id: 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001',
        candidate_targets: Array.from({ length: 50 }, (_, index) => candidate(index)),
        next_required_step: 'controlled_enriched_target_regeneration_execution',
        recommended_next_step: 'Phase 5.21L2V3AA: controlled enriched target regeneration execution',
        raw_write_ready_for_execution: false,
        accepted_mapping_count: 0,
        requires_separate_identity_mapping_acceptance: true,
        requires_separate_baseline_acceptance: true,
        requires_separate_final_db_write_authorization: true,
        phase_5_21_l2v3z_planning_status: 'completed_no_write_enriched_target_regeneration_planning',
        enriched_target_regeneration_planning_status: 'completed_no_write_enriched_target_regeneration_planning',
        ...overrides,
    };
}

function syntheticL2V3YArtifact(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3Y',
        artifact_status: 'completed_metadata_only_source_inventory_acquisition_execution',
        live_fetch_performed: true,
        db_write_performed: false,
        candidate_scope_count: 50,
        candidate_targets_matched_count: 50,
        candidate_targets_with_source_page_url: 50,
        candidate_targets_with_source_page_url_base: 50,
        candidate_targets_with_source_url_fragment_external_id: 50,
        candidate_targets_with_source_inventory_record_key: 50,
        identity_evidence_complete_count: 50,
        accepted_mapping_count: 0,
        raw_write_ready_for_execution: false,
        source_inventory_metadata_records: Array.from({ length: 50 }, (_, index) => sourceRecord(index)),
        ...overrides,
    };
}

function syntheticL2V3ZArtifact(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3Z',
        planned_mapping_key: 'target_id',
        planned_cross_check_keys: ['match_id', 'schedule_external_id', 'source_url_fragment_external_id'],
        one_to_one_mapping_expected: true,
        duplicate_source_record_key_count: 0,
        duplicate_fragment_external_id_count: 0,
        missing_source_page_url_count: 0,
        missing_source_page_url_base_count: 0,
        missing_source_url_fragment_external_id_count: 0,
        missing_source_inventory_record_key_count: 0,
        regeneration_execution_authorization_required: true,
        no_write_verification_required: true,
        accepted_mapping_count: 0,
        raw_write_ready_for_execution: false,
        ...overrides,
    };
}

function buildSyntheticRunResult(overrides = {}) {
    return mod.runEnrichedTargetRegenerationExecution({
        manifest: syntheticManifest(overrides.manifest || {}),
        l2v3yArtifact: syntheticL2V3YArtifact(overrides.l2v3yArtifact || {}),
        l2v3zArtifact: syntheticL2V3ZArtifact(overrides.l2v3zArtifact || {}),
        writeFiles: false,
    });
}

function installImportGuard(t) {
    const originalLoad = Module._load;
    Module._load = function patchedLoad(request, parent, isMain) {
        if (
            /pg|http|https|child_process|playwright|puppeteer|ProductionHarvester|odds_harvest_pipeline/i.test(request)
        ) {
            throw new Error(`blocked import: ${request}`);
        }
        return originalLoad.call(this, request, parent, isMain);
    };
    t.after(() => {
        Module._load = originalLoad;
    });
}

test('L2V3AA records controlled no-write enriched target regeneration execution', () => {
    const result = buildSyntheticRunResult();
    const artifact = result.artifact;
    const manifest = result.updated_manifest;

    assert.equal(result.ok, true);
    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3AA');
    assert.equal(artifact.regeneration_attempted, true);
    assert.equal(artifact.no_write, true);
    assert.equal(artifact.live_fetch_performed, false);
    assert.equal(artifact.network_request_performed, false);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_match_data_insert_performed, false);
    assert.equal(artifact.matches_write_performed, false);
    assert.equal(artifact.matches_external_id_modified, false);
    assert.equal(artifact.identity_mapping_acceptance_performed, false);
    assert.equal(artifact.baseline_acceptance_performed, false);
    assert.equal(artifact.raw_write_retry_performed, false);
    assert.equal(artifact.enriched_target_regeneration_execution_performed, true);
    assert.equal(artifact.candidate_scope_count, 50);
    assert.equal(artifact.acquired_source_record_count, 50);
    assert.equal(artifact.regenerated_target_count, 50);
    assert.equal(artifact.blocked_target_count, 0);
    assert.equal(artifact.one_to_one_mapping_count, 50);
    assert.equal(artifact.identity_evidence_complete_count, 50);
    assert.equal(artifact.raw_write_ready_target_count, 0);
    assert.equal(artifact.accepted_mapping_count, 0);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(artifact.no_write_verification_required, true);
    assert.equal(artifact.recommended_next_step, 'Phase 5.21L2V3AB: enriched no-write verification planning');
    assert.equal(manifest.phase_5_21_l2v3aa_execution_status, artifact.artifact_status);
    assert.equal(manifest.enriched_target_regeneration_execution_status, artifact.artifact_status);
    assert.equal(manifest.raw_write_ready_for_execution, false);
    assert.equal(manifest.accepted_mapping_count, 0);
    assert.equal(manifest.next_required_step, 'enriched_no_write_verification_planning');
});

test('enriched targets use target_id one-to-one mapping and required cross-check fields', () => {
    const result = buildSyntheticRunResult();
    const target = result.artifact.enriched_targets[0];

    assert.equal(target.target_id, 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001:53_20252026_9000001');
    assert.equal(target.match_id, '53_20252026_9000001');
    assert.equal(target.external_id, '9000001');
    assert.equal(target.schedule_external_id, '9000001');
    assert.equal(target.source_url_fragment_external_id, '9000001');
    assert.equal(target.source_page_url_base, '/matches/home-0-away-0/route-0');
    assert.deepEqual(target.regeneration_blockers, []);
    assert.equal(target.regeneration_status, 'regenerated_no_write');
    assert.equal(target.raw_write_ready_for_execution, false);
});

test('missing metadata or duplicate keys block targets without enabling acceptance or raw write readiness', () => {
    const records = Array.from({ length: 50 }, (_, index) =>
        sourceRecord(index, {
            source_inventory_record_key:
                index < 2 ? 'duplicate-key' : `l1_api_data_leagues:record.${index}:900000${index}`,
            source_page_url_base: index === 2 ? null : `/matches/home-${index}-away-${index}/route-${index}`,
            source_url_fragment_external_id: index === 3 ? '' : String(9000001 + index),
        })
    );
    const result = buildSyntheticRunResult({
        l2v3yArtifact: { source_inventory_metadata_records: records },
    });

    assert.equal(result.artifact.blocked_target_count, 50);
    assert.equal(result.artifact.regenerated_target_count, 0);
    assert.equal(result.artifact.duplicate_source_record_key_count, 1);
    assert.equal(result.artifact.missing_source_page_url_base_count, 1);
    assert.equal(result.artifact.missing_source_url_fragment_external_id_count, 1);
    assert.equal(result.artifact.raw_write_ready_target_count, 0);
    assert.equal(result.artifact.accepted_mapping_count, 0);
    assert.equal(result.artifact.raw_write_ready_for_execution, false);
    assert.match(
        result.artifact.enriched_targets.map(target => target.regeneration_blockers.join(',')).join('\n'),
        /duplicate_source_inventory_record_key_detected|missing_source_page_url_base|missing_source_url_fragment_external_id/
    );
});

test('fragment mismatches and schedule metadata mismatches block targets', () => {
    const records = Array.from({ length: 50 }, (_, index) =>
        sourceRecord(
            index,
            index === 0
                ? {
                      source_url_fragment_external_id: 'DIFF',
                  }
                : index === 1
                  ? {
                        schedule_home_team: 'Wrong Home',
                    }
                  : {}
        )
    );
    const result = buildSyntheticRunResult({
        l2v3yArtifact: { source_inventory_metadata_records: records },
    });

    assert.equal(result.artifact.fragment_schedule_id_mismatch_count, 1);
    assert.equal(result.artifact.schedule_metadata_mismatch_count, 1);
    assert.equal(result.artifact.blocked_target_count, 2);
    assert.match(
        result.artifact.enriched_targets[0].regeneration_blockers.join(','),
        /fragment_schedule_external_id_mismatch/
    );
    assert.match(result.artifact.enriched_targets[1].regeneration_blockers.join(','), /schedule_home_team_mismatch/);
});

test('enriched target result is not accepted mapping or raw write authorization', () => {
    const result = buildSyntheticRunResult();
    const artifact = result.artifact;

    assert.equal(artifact.safety_contract.enriched_target_result_is_not_accepted_mapping, true);
    assert.equal(artifact.safety_contract.enriched_target_result_is_not_raw_write_authorization, true);
    assert.equal(
        artifact.safety_contract.identity_evidence_complete_does_not_imply_raw_write_ready_for_execution,
        true
    );
    assert.equal(artifact.accepted_mapping_count, 0);
    assert.equal(artifact.raw_write_ready_for_execution, false);
});

test('updated manifest remains rejected by the raw write runner gate', () => {
    const result = buildSyntheticRunResult();
    const gate = rawWrite.validateManifestGate(result.updated_manifest);

    assert.equal(gate.ok, false);
    assert.match(gate.errors.join('\n'), /required_next_step|write_execution_status|raw_match_data_write_status/i);
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
    assert.match(validation.errors.join('\n'), /live-fetch=yes is blocked/);
    assert.match(validation.errors.join('\n'), /print-full-json=yes is blocked/);
});

test('helper does not import network, DB, browser, proxy, odds, or harvest modules', t => {
    installImportGuard(t);
    const loaded = loadFreshModule();
    assert.equal(typeof loaded.runEnrichedTargetRegenerationExecution, 'function');
});

test('validateInputs fails closed on unsafe manifest and invalid upstream artifacts', () => {
    const invalid = mod.validateInputs(
        syntheticManifest({
            next_required_step: 'wrong-step',
            candidate_targets: [candidate(0)],
            raw_write_ready_for_execution: true,
            accepted_mapping_count: 1,
        }),
        syntheticL2V3YArtifact({
            candidate_scope_count: 49,
            candidate_targets_matched_count: 49,
            identity_evidence_complete_count: 49,
            accepted_mapping_count: 1,
            raw_write_ready_for_execution: true,
            source_inventory_metadata_records: Array.from({ length: 49 }, (_, index) => sourceRecord(index)),
        }),
        syntheticL2V3ZArtifact({
            planned_mapping_key: 'match_id',
            one_to_one_mapping_expected: false,
            duplicate_source_record_key_count: 1,
            duplicate_fragment_external_id_count: 1,
            missing_source_page_url_count: 1,
            missing_source_page_url_base_count: 1,
            missing_source_url_fragment_external_id_count: 1,
            missing_source_inventory_record_key_count: 1,
            accepted_mapping_count: 1,
            raw_write_ready_for_execution: true,
            regeneration_execution_authorization_required: false,
            no_write_verification_required: false,
        })
    );

    assert.equal(invalid.ok, false);
    assert.match(
        invalid.errors.join('\n'),
        /manifest next_required_step must be controlled_enriched_target_regeneration_execution/
    );
    assert.match(invalid.errors.join('\n'), /manifest candidate_targets must contain 50 targets/);
    assert.match(invalid.errors.join('\n'), /L2V3Y candidate_scope_count must be 50/);
    assert.match(invalid.errors.join('\n'), /L2V3Z planned_mapping_key must be target_id/);
    assert.match(invalid.errors.join('\n'), /L2V3Z no_write_verification_required must remain true/);
});

test('runEnrichedTargetRegenerationExecution can write outputs to explicit temp paths', () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'l2v3aa-regeneration-execute-'));
    const artifactPath = path.join(tmpDir, 'artifact.json');
    const reportPath = path.join(tmpDir, 'report.md');
    const manifestPath = path.join(tmpDir, 'manifest.json');

    try {
        const result = mod.runEnrichedTargetRegenerationExecution({
            manifest: syntheticManifest(),
            l2v3yArtifact: syntheticL2V3YArtifact(),
            l2v3zArtifact: syntheticL2V3ZArtifact(),
            writeFiles: true,
            artifactOutputPath: artifactPath,
            reportOutputPath: reportPath,
            manifestOutputPath: manifestPath,
        });

        assert.equal(result.ok, true);
        assert.equal(JSON.parse(fs.readFileSync(artifactPath, 'utf8')).proposal_phase, 'Phase 5.21L2V3AA');
        assert.match(fs.readFileSync(reportPath, 'utf8'), /regeneration_attempted=true/i);
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
    assert.match(helpOutput, /L2V3AA is a controlled no-write enriched target regeneration execution phase/);
    assert.equal(invalidStatus, 2);
    assert.match(invalidOutput, /unknown arguments/);
    assert.equal(successStatus, 0);
    assert.match(successOutput, /"regeneration_attempted": true/);
    assert.match(successOutput, /"raw_write_ready_for_execution": false/);
});

test('main entrypoint prints help and blocked option output', () => {
    const help = spawnSync(process.execPath, [MODULE_PATH, '--help'], {
        cwd: PROJECT_ROOT,
        encoding: 'utf8',
    });
    assert.equal(help.status, 0);
    assert.match(help.stdout, /L2V3AA is a controlled no-write enriched target regeneration execution phase/);

    const blocked = spawnSync(process.execPath, [MODULE_PATH, '--allow-db-write=yes'], {
        cwd: PROJECT_ROOT,
        encoding: 'utf8',
    });
    assert.equal(blocked.status, 2);
    assert.match(blocked.stdout, /allow-db-write=yes is blocked/);
});

test('repository L2V3AA artifacts preserve controlled no-write semantics when generated', () => {
    const artifactPath =
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.enriched_targets.phase521l2v3aa.json';
    if (!fs.existsSync(path.join(PROJECT_ROOT, artifactPath))) {
        return;
    }

    const manifest = readJson('docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json');
    const artifact = readJson(artifactPath);
    const report = readText('docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AA.md');

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3AA');
    assert.equal(artifact.live_fetch_performed, false);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_match_data_insert_performed, false);
    assert.equal(artifact.matches_write_performed, false);
    assert.equal(artifact.accepted_mapping_count, 0);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(artifact.regenerated_target_count, 50);
    assert.equal(artifact.blocked_target_count, 0);
    assert.equal(manifest.phase_5_21_l2v3aa_execution_status, artifact.artifact_status);
    assert.equal(manifest.raw_write_ready_for_execution, false);
    assert.equal(manifest.accepted_mapping_count, 0);
    assert.ok(
        [
            'Phase 5.21L2V3AB: enriched no-write verification planning',
            'Phase 5.21L2V3AC: controlled enriched no-write verification execution',
            'Phase 5.21L2V3AD: identity mapping acceptance review planning',
            'Phase 5.21L2V3AE: identity mapping acceptance review execution',
            'Phase 5.21L2V3AF: baseline acceptance planning',
            'Phase 5.21L2V3AG: baseline acceptance execution',
            'Phase 5.21L2V3AH: final DB-write authorization planning',
            'Phase 5.21L2V3AI: final DB-write authorization execution',
            'Phase 5.21L2V3AJ: controlled raw_match_data write execution planning',
            'Phase 5.21L2V3AK: controlled raw_match_data write execution',
            'Phase 5.21L2V3AK: controlled raw write execution blocker resolution',
            'Phase 5.21L2V3AK: continued controlled raw write planning',
            'Phase 5.21L2V3AL: controlled payload source declaration planning',
            'Phase 5.21L2V3AM: controlled payload source declaration execution',
            'Phase 5.21L2V3AN: controlled no-write payload recapture planning',
            'Phase 5.21L2V3AO: controlled no-write payload recapture execution',
            'Phase 5.21L2V3AP: no-write payload recapture blocker investigation',
            'Phase 5.21L2V3AP: partial recapture review planning',
            'Phase 5.21L2V3AP: controlled recapture result verification planning',
            'Phase 5.21L2V3AQ: accepted mapping and baseline contradiction review planning',
            'Phase 5.21L2V3AQ: recapture runner identity input contract fix planning',
            'Phase 5.21L2V3AQ: continued no-write recapture blocker investigation',
            'Phase 5.21L2V3AR: accepted mapping and baseline contradiction review execution',
            'Phase 5.21L2V3AR: accepted mapping and baseline suspension planning',
            'Phase 5.21L2V3AS: accepted mapping and baseline suspension planning',
            'Phase 5.21L2V3AR: expanded accepted mapping/baseline contradiction review planning',
            'Phase 5.21L2V3AR: recapture runner identity input contract fix planning',
        ].includes(manifest.recommended_next_step)
    );
    assert.ok(
        [
            'enriched_no_write_verification_planning',
            'controlled_enriched_no_write_verification_execution',
            'identity_mapping_acceptance_review_planning',
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
            'controlled_payload_source_declaration_execution',
            'controlled_no_write_payload_recapture_planning',
            'controlled_no_write_payload_recapture_execution',
            'no_write_payload_recapture_blocker_investigation',
            'partial_recapture_review_planning',
            'controlled_recapture_result_verification_planning',
            'accepted_mapping_and_baseline_contradiction_review_planning',
            'accepted_mapping_and_baseline_contradiction_review_execution',
            'accepted_mapping_and_baseline_suspension_planning',
            'expanded_accepted_mapping_baseline_contradiction_review_planning',
            'recapture_runner_identity_input_contract_fix_planning',
            'continued_no_write_recapture_blocker_investigation',
        ].includes(manifest.next_required_step)
    );
    assert.match(report, /planned_mapping_key=target_id/i);
});
