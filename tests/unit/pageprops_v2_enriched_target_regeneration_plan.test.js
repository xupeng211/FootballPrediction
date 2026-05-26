'use strict';
/* eslint-disable max-lines -- L2V3Z planning safety contract is audited in one place. */

const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const Module = require('node:module');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/pageprops_v2_enriched_target_regeneration_plan.js');
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
        required_next_step: 'renewed_controlled_pageprops_v2_raw_write_execution_blocked_review',
        raw_match_data_write_status: 'not_executed',
        write_execution_status: 'RECAPTURE_HASH_GATE_BLOCKED',
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
        next_required_step: 'enriched_target_regeneration_planning',
        recommended_next_step: 'Phase 5.21L2V3Z: enriched target regeneration planning',
        raw_write_ready_for_execution: false,
        accepted_mapping_count: 0,
        requires_separate_identity_mapping_acceptance: true,
        requires_separate_baseline_acceptance: true,
        requires_separate_final_db_write_authorization: true,
        ...overrides,
    };
}

function syntheticL2V3YArtifact(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3Y',
        artifact_status: 'completed_metadata_only_source_inventory_acquisition_execution',
        live_fetch_performed: true,
        db_write_performed: false,
        endpoint_used: '/api/data/leagues?id=53&season=20252026',
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

function syntheticL2V3XArtifact(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3X',
        planned_source_endpoint: '/api/data/leagues?id=53&season=20252026',
        planned_candidate_scope_count: 50,
        accepted_mapping_count: 0,
        raw_write_ready_for_execution: false,
        ...overrides,
    };
}

function syntheticL2V3WArtifact(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3W',
        requires_source_inventory_regeneration: true,
        ...overrides,
    };
}

function syntheticL2V3VArtifact(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3V',
        accepted_mapping_count: 0,
        raw_write_ready_for_execution: false,
        manifest_candidate_builder_updated: true,
        ...overrides,
    };
}

function sourceTextByPath() {
    return {
        'src/infrastructure/services/FotMobSourceInventoryAdapter.js':
            'deriveSourceInventoryIdentityEvidence source_page_url_base source_inventory_record_key',
        'scripts/ops/single_league_small_batch_target_manifest_plan.js':
            'source_page_url source_inventory_record_key identity_evidence_status',
        'scripts/ops/pageprops_v2_source_inventory_enrichment_apply.js':
            'enrichCandidateTarget source_url_fragment_external_id identity_evidence_status',
        'scripts/ops/pageprops_v2_no_write_preview.js': 'validatePreviewInput allow-db-write',
    };
}

function buildSyntheticRunResult(overrides = {}) {
    return mod.runEnrichedTargetRegenerationPlan({
        manifest: syntheticManifest(overrides.manifest || {}),
        l2v3yArtifact: syntheticL2V3YArtifact(overrides.l2v3yArtifact || {}),
        l2v3xArtifact: syntheticL2V3XArtifact(overrides.l2v3xArtifact || {}),
        l2v3wArtifact: syntheticL2V3WArtifact(overrides.l2v3wArtifact || {}),
        l2v3vArtifact: syntheticL2V3VArtifact(overrides.l2v3vArtifact || {}),
        sourceTextByPath: overrides.sourceTextByPath || sourceTextByPath(),
        writeFiles: false,
    });
}

function installImportGuard(t) {
    const originalLoad = Module._load;
    Module._load = function patchedLoad(request, parent, isMain) {
        if (/pg|child_process|playwright|puppeteer|ProductionHarvester|odds_harvest_pipeline/i.test(request)) {
            throw new Error(`blocked import: ${request}`);
        }
        return originalLoad.call(this, request, parent, isMain);
    };
    t.after(() => {
        Module._load = originalLoad;
    });
}

test('L2V3Z records planning-only enriched target regeneration semantics', () => {
    const result = buildSyntheticRunResult();
    const artifact = result.artifact;
    const manifest = result.updated_manifest;

    assert.equal(result.ok, true);
    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3Z');
    assert.equal(artifact.no_write, true);
    assert.equal(artifact.live_fetch_performed, false);
    assert.equal(artifact.network_request_performed, false);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_match_data_insert_performed, false);
    assert.equal(artifact.matches_write_performed, false);
    assert.equal(artifact.matches_external_id_modified, false);
    assert.equal(artifact.target_regeneration_execution_performed, false);
    assert.equal(artifact.identity_mapping_acceptance_performed, false);
    assert.equal(artifact.baseline_acceptance_performed, false);
    assert.equal(artifact.raw_write_retry_performed, false);
    assert.equal(artifact.accepted_mapping_count, 0);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(artifact.candidate_scope_count, 50);
    assert.equal(artifact.acquired_source_record_count, 50);
    assert.equal(artifact.planned_mapping_key, 'target_id');
    assert.equal(artifact.one_to_one_mapping_expected, true);
    assert.equal(artifact.duplicate_source_record_key_count, 0);
    assert.equal(artifact.duplicate_fragment_external_id_count, 0);
    assert.equal(artifact.missing_source_page_url_count, 0);
    assert.equal(artifact.missing_source_page_url_base_count, 0);
    assert.equal(artifact.missing_source_url_fragment_external_id_count, 0);
    assert.equal(artifact.missing_source_inventory_record_key_count, 0);
    assert.equal(artifact.planned_enriched_field_count, mod.PLANNED_ENRICHED_FIELDS.length);
    assert.equal(artifact.regeneration_execution_authorization_required, true);
    assert.equal(artifact.no_write_verification_required, true);
    assert.equal(artifact.recommended_next_step, 'Phase 5.21L2V3AA: controlled enriched target regeneration execution');
    assert.equal(manifest.phase_5_21_l2v3z_planning_status, artifact.artifact_status);
    assert.equal(manifest.enriched_target_regeneration_planning_status, artifact.artifact_status);
    assert.equal(manifest.accepted_mapping_count, 0);
    assert.equal(manifest.raw_write_ready_for_execution, false);
    assert.equal(manifest.next_required_step, 'controlled_enriched_target_regeneration_execution');
});

test('planned mapping uses target_id and keeps source_inventory_record_key as a uniqueness guard', () => {
    const result = buildSyntheticRunResult();
    const analysis = result.artifact.mapping_analysis;

    assert.equal(result.artifact.planned_mapping_key, 'target_id');
    assert.deepEqual(result.artifact.planned_cross_check_keys, [
        'match_id',
        'schedule_external_id',
        'source_url_fragment_external_id',
    ]);
    assert.equal(analysis.source_inventory_record_key_usage, 'uniqueness_guard_and_persistence_field');
    assert.equal(analysis.target_id_exact_match_count, 50);
    assert.equal(analysis.match_id_exact_match_count, 50);
    assert.equal(analysis.schedule_external_id_exact_match_count, 50);
    assert.equal(analysis.source_url_fragment_external_id_exact_match_count, 50);
    assert.equal(analysis.schedule_metadata_exact_match_count, 50);
});

test('plan remains non-accepted and non-executable even with complete identity evidence', () => {
    const result = buildSyntheticRunResult();
    const artifact = result.artifact;

    assert.equal(artifact.safety_contract.enriched_target_regeneration_plan_is_not_accepted_mapping, true);
    assert.equal(artifact.safety_contract.enriched_target_regeneration_plan_is_not_raw_write_authorization, true);
    assert.equal(artifact.safety_contract.acquired_source_url_evidence_does_not_imply_accepted_mapping, true);
    assert.equal(
        artifact.safety_contract.identity_evidence_complete_does_not_imply_raw_write_ready_for_execution,
        true
    );
    assert.equal(artifact.accepted_mapping_count, 0);
    assert.equal(artifact.raw_write_ready_for_execution, false);
});

test('duplicate or missing evidence keeps L2V3Z in continued planning', () => {
    const records = Array.from({ length: 50 }, (_, index) =>
        sourceRecord(index, {
            source_inventory_record_key:
                index < 2 ? 'duplicate-key' : `l1_api_data_leagues:record.${index}:900000${index}`,
            source_page_url_base: index === 49 ? null : `/matches/home-${index}-away-${index}/route-${index}`,
        })
    );
    const result = buildSyntheticRunResult({
        l2v3yArtifact: { source_inventory_metadata_records: records, missing_source_page_url_base_count: 1 },
    });

    assert.equal(result.artifact.one_to_one_mapping_expected, false);
    assert.equal(result.artifact.duplicate_source_record_key_count, 1);
    assert.equal(result.artifact.missing_source_page_url_base_count, 1);
    assert.equal(
        result.artifact.recommended_next_step,
        'Phase 5.21L2V3AA: continued enriched target regeneration planning'
    );
    assert.equal(result.updated_manifest.next_required_step, 'continued_enriched_target_regeneration_planning');
});

test('helper coverage gaps recommend helper implementation before execution', () => {
    const result = buildSyntheticRunResult({
        sourceTextByPath: {
            'src/infrastructure/services/FotMobSourceInventoryAdapter.js': 'missing expected coverage',
            'scripts/ops/single_league_small_batch_target_manifest_plan.js': 'missing expected coverage',
            'scripts/ops/pageprops_v2_source_inventory_enrichment_apply.js': 'missing expected coverage',
            'scripts/ops/pageprops_v2_no_write_preview.js': 'validatePreviewInput allow-db-write',
        },
    });

    assert.equal(result.artifact.helper_coverage.source_inventory_adapter_extracts_identity_evidence, false);
    assert.equal(result.artifact.helper_coverage.manifest_builder_schema_includes_required_fields, false);
    assert.equal(result.artifact.helper_coverage.source_inventory_enrichment_helper_present, false);
    assert.equal(
        result.artifact.recommended_next_step,
        'Phase 5.21L2V3AA: enriched target regeneration helper implementation'
    );
    assert.equal(result.updated_manifest.next_required_step, 'enriched_target_regeneration_helper_implementation');
});

test('updated manifest is still rejected by the raw write runner gate', () => {
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

test('helper refuses DB, network, execution, acceptance, and payload flags', () => {
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

test('helper does not import DB, browser, proxy, odds, or harvest modules', t => {
    installImportGuard(t);
    const loaded = loadFreshModule();
    assert.equal(typeof loaded.runEnrichedTargetRegenerationPlan, 'function');
});

test('runEnrichedTargetRegenerationPlan can write outputs to explicit temp paths', () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'l2v3z-regeneration-plan-'));
    const artifactPath = path.join(tmpDir, 'artifact.json');
    const reportPath = path.join(tmpDir, 'report.md');
    const manifestPath = path.join(tmpDir, 'manifest.json');

    try {
        const result = mod.runEnrichedTargetRegenerationPlan({
            manifest: syntheticManifest(),
            l2v3yArtifact: syntheticL2V3YArtifact(),
            l2v3xArtifact: syntheticL2V3XArtifact(),
            l2v3wArtifact: syntheticL2V3WArtifact(),
            l2v3vArtifact: syntheticL2V3VArtifact(),
            sourceTextByPath: sourceTextByPath(),
            writeFiles: true,
            artifactOutputPath: artifactPath,
            reportOutputPath: reportPath,
            manifestOutputPath: manifestPath,
        });

        assert.equal(result.ok, true);
        assert.equal(JSON.parse(fs.readFileSync(artifactPath, 'utf8')).proposal_phase, 'Phase 5.21L2V3Z');
        assert.match(fs.readFileSync(reportPath, 'utf8'), /planned_mapping_key=target_id/i);
        assert.equal(JSON.parse(fs.readFileSync(manifestPath, 'utf8')).raw_write_ready_for_execution, false);
    } finally {
        fs.rmSync(tmpDir, { recursive: true, force: true });
    }
});

test('CLI parsing covers help and unknown arguments', () => {
    const helpParsed = mod.parseArgs(['--help']);
    const parsed = mod.parseArgs(['positional', '--write-files', 'false', '--not-a-real-flag=value']);
    const invalid = mod.validateCliOptions(parsed);

    assert.equal(helpParsed.help, true);
    assert.equal(parsed.writeFiles, false);
    assert.deepEqual(parsed.unknown, ['positional', 'not-a-real-flag']);
    assert.equal(invalid.ok, false);
    assert.match(invalid.errors.join('\n'), /unknown arguments/);
});

test('analyzeInputPaths supports injected path analysis and default existence fallback', () => {
    const result = mod.analyzeInputPaths(
        [
            { key: 'injected', path: 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3Z.md', role: 'report' },
            { key: 'missing', path: 'docs/_reports/DOES_NOT_EXIST.phase521l2v3z.md', role: 'report' },
        ],
        {
            inputPathAnalysisByPath: {
                'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3Z.md': {
                    exists: true,
                    note: 'injected-analysis',
                },
            },
        }
    );

    assert.deepEqual(result[0], {
        key: 'injected',
        path: 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3Z.md',
        role: 'report',
        exists: true,
        note: 'injected-analysis',
    });
    assert.equal(result[1].key, 'missing');
    assert.equal(result[1].exists, false);
});

test('validateInputs accepts already-completed manifest reruns and rejects invalid upstream state', () => {
    const rerunGate = mod.validateInputs(
        syntheticManifest({
            next_required_step: 'controlled_enriched_target_regeneration_execution',
            phase_5_21_l2v3z_planning_status: mod.ARTIFACT_STATUS,
            enriched_target_regeneration_planning_status: mod.ARTIFACT_STATUS,
        }),
        syntheticL2V3YArtifact(),
        syntheticL2V3XArtifact(),
        syntheticL2V3WArtifact(),
        syntheticL2V3VArtifact()
    );
    assert.equal(rerunGate.ok, true);

    const invalidGate = mod.validateInputs(
        syntheticManifest({
            candidate_targets: [candidate(0)],
            next_required_step: 'wrong-step',
            raw_write_ready_for_execution: true,
            accepted_mapping_count: 1,
        }),
        syntheticL2V3YArtifact({
            proposal_phase: 'Phase 5.21L2V3Y_BAD',
            live_fetch_performed: false,
            db_write_performed: true,
            endpoint_used: '/api/data/leagues?id=53&season=bad',
            candidate_scope_count: 49,
            candidate_targets_matched_count: 49,
            candidate_targets_with_source_page_url: 49,
            candidate_targets_with_source_page_url_base: 49,
            candidate_targets_with_source_url_fragment_external_id: 49,
            candidate_targets_with_source_inventory_record_key: 49,
            identity_evidence_complete_count: 49,
            accepted_mapping_count: 1,
            raw_write_ready_for_execution: true,
            source_inventory_metadata_records: Array.from({ length: 49 }, (_, index) => sourceRecord(index)),
        }),
        syntheticL2V3XArtifact({
            proposal_phase: 'Phase 5.21L2V3X_BAD',
            planned_source_endpoint: '/bad',
            planned_candidate_scope_count: 49,
            accepted_mapping_count: 1,
            raw_write_ready_for_execution: true,
        }),
        syntheticL2V3WArtifact({
            proposal_phase: 'Phase 5.21L2V3W_BAD',
            requires_source_inventory_regeneration: false,
        }),
        syntheticL2V3VArtifact({
            proposal_phase: 'Phase 5.21L2V3V_BAD',
            accepted_mapping_count: 1,
            raw_write_ready_for_execution: true,
        })
    );

    assert.equal(invalidGate.ok, false);
    assert.match(
        invalidGate.errors.join('\n'),
        /manifest next_required_step must be enriched_target_regeneration_planning/
    );
    assert.match(invalidGate.errors.join('\n'), /manifest candidate_targets must contain 50 targets/);
    assert.match(invalidGate.errors.join('\n'), /L2V3Y live_fetch_performed must be true/);
    assert.match(invalidGate.errors.join('\n'), /L2V3Y source_inventory_metadata_records must contain 50 records/);
    assert.match(invalidGate.errors.join('\n'), /L2V3X artifact must be present/);
    assert.match(invalidGate.errors.join('\n'), /L2V3W requires_source_inventory_regeneration must remain true/);
    assert.match(invalidGate.errors.join('\n'), /L2V3V raw_write_ready_for_execution must remain false/);
});

test('runEnrichedTargetRegenerationPlan returns input-gate failure without writing files', () => {
    const result = mod.runEnrichedTargetRegenerationPlan({
        manifest: syntheticManifest({ candidate_targets: [candidate(0)] }),
        l2v3yArtifact: syntheticL2V3YArtifact(),
        l2v3xArtifact: syntheticL2V3XArtifact(),
        l2v3wArtifact: syntheticL2V3WArtifact(),
        l2v3vArtifact: syntheticL2V3VArtifact(),
        writeFiles: false,
    });

    assert.equal(result.ok, false);
    assert.equal(result.status, 3);
    assert.match(result.errors.join('\n'), /candidate_targets must contain 50 targets/);
});

test('analyzeMapping can fall back to match_id or block with unknown mapping key', () => {
    const matchIdFallback = mod.analyzeMapping(
        syntheticManifest(),
        syntheticL2V3YArtifact({
            source_inventory_metadata_records: Array.from({ length: 50 }, (_, index) =>
                sourceRecord(index, {
                    target_id: `unexpected-target-${index}`,
                })
            ),
        })
    );

    assert.equal(matchIdFallback.planned_mapping_key, 'match_id');
    assert.equal(matchIdFallback.one_to_one_mapping_expected, false);
    assert.equal(matchIdFallback.target_id_exact_match_count, 0);
    assert.equal(matchIdFallback.match_id_exact_match_count, 50);
    assert.match(matchIdFallback.blocking_reasons.join('\n'), /target_id_match_count_incomplete/);

    const unknown = mod.analyzeMapping(
        syntheticManifest(),
        syntheticL2V3YArtifact({
            source_inventory_metadata_records: Array.from({ length: 50 }, (_, index) =>
                sourceRecord(index, {
                    target_id: `unexpected-target-${index}`,
                    match_id: `unexpected-match-${index}`,
                    schedule_external_id: `unexpected-external-${index}`,
                    source_url_fragment_external_id: '',
                    source_inventory_record_key: index < 2 ? 'duplicate-key' : `unknown-record-${index}`,
                })
            ),
        })
    );

    assert.equal(unknown.planned_mapping_key, 'unknown');
    assert.equal(unknown.duplicate_source_record_key_count, 1);
    assert.equal(unknown.missing_source_url_fragment_external_id_count, 50);
    assert.match(unknown.blocking_reasons.join('\n'), /planned_mapping_key_unknown/);
    assert.match(unknown.blocking_reasons.join('\n'), /duplicate_source_inventory_record_key_detected/);
    assert.match(unknown.blocking_reasons.join('\n'), /missing_source_url_fragment_external_id_detected/);
});

test('runCli reports blocked flags and successful planning summaries without writing files', () => {
    let stdout = '';
    const blockedStatus = mod.runCli(['--allow-db-write=yes'], {
        stdout: text => {
            stdout += text;
        },
    });
    assert.equal(blockedStatus, 2);
    assert.match(stdout, /allow-db-write=yes is blocked/);

    let successStdout = '';
    const successStatus = mod.runCli(['--write-files=false'], {
        stdout: text => {
            successStdout += text;
        },
    });
    assert.equal(successStatus, 0);
    assert.match(successStdout, /"planned_mapping_key": "target_id"/);
    assert.match(successStdout, /"raw_write_ready_for_execution": false/);
});

test('main entrypoint prints help and blocked option output', () => {
    const help = spawnSync(process.execPath, [MODULE_PATH, '--help'], {
        cwd: PROJECT_ROOT,
        encoding: 'utf8',
    });
    assert.equal(help.status, 0);
    assert.match(help.stdout, /L2V3Z is a no-write enriched target regeneration planning phase/);

    const blocked = spawnSync(process.execPath, [MODULE_PATH, '--allow-db-write=yes'], {
        cwd: PROJECT_ROOT,
        encoding: 'utf8',
    });
    assert.equal(blocked.status, 2);
    assert.match(blocked.stdout, /allow-db-write=yes is blocked/);
});

test('repository L2V3Z artifacts preserve planning-only safety when generated', () => {
    const artifactPath =
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.enriched_target_regeneration_plan.phase521l2v3z.json';
    if (!fs.existsSync(path.join(PROJECT_ROOT, artifactPath))) {
        return;
    }

    const manifest = readJson('docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json');
    const artifact = readJson(artifactPath);
    const report = readText('docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3Z.md');

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3Z');
    assert.equal(artifact.no_write, true);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_match_data_insert_performed, false);
    assert.equal(artifact.matches_write_performed, false);
    assert.equal(artifact.accepted_mapping_count, 0);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(artifact.planned_mapping_key, 'target_id');
    assert.equal(artifact.one_to_one_mapping_expected, true);
    assert.equal(manifest.phase_5_21_l2v3z_planning_status, artifact.artifact_status);
    assert.equal(manifest.raw_write_ready_for_execution, false);
    assert.equal(manifest.accepted_mapping_count, 0);
    if (manifest.phase_5_21_l2v3aa_execution_status) {
        assert.equal(
            manifest.phase_5_21_l2v3aa_execution_status,
            'completed_controlled_no_write_enriched_target_regeneration_execution'
        );
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
                'Phase 5.21L2V3AT: accepted mapping and baseline suspension execution',
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
                'accepted_mapping_and_baseline_suspension_execution',
                'expanded_accepted_mapping_baseline_contradiction_review_planning',
                'recapture_runner_identity_input_contract_fix_planning',
                'continued_no_write_recapture_blocker_investigation',
            ].includes(manifest.next_required_step)
        );
    } else {
        assert.equal(
            manifest.recommended_next_step,
            'Phase 5.21L2V3AA: controlled enriched target regeneration execution'
        );
        assert.equal(manifest.next_required_step, 'controlled_enriched_target_regeneration_execution');
    }
    assert.match(report, /primary_mapping_key=target_id/i);
});
