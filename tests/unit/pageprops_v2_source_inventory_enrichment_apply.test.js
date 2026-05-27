'use strict';
/* eslint-disable max-lines -- L2V3V implementation safety contract is audited together. */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const Module = require('node:module');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/pageprops_v2_source_inventory_enrichment_apply.js');
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
        target_id: `batch:53_20252026_${externalId}`,
        batch_id: 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001',
        source: 'fotmob',
        route: 'html_hydration',
        raw_data_version: 'fotmob_pageprops_v2',
        hash_strategy: 'stable_pageprops_payload_v1',
        match_id: `53_20252026_${externalId}`,
        external_id: externalId,
        source_path: 'l1_api_data_leagues',
        league_id: 53,
        league_name: 'Ligue 1',
        season: '2025/2026',
        home_team: `Home ${index}`,
        away_team: `Away ${index}`,
        kickoff_time: '2025-08-15T18:45:00.000Z',
        match_date: '2025-08-15T18:45:00.000Z',
        status: 'finished',
        preflight_status: 'hash_baseline_ready',
        baseline_hash: 'c0365494bedfad7f49c59db649dc52d45bd364e7991f518261085349bebd530b',
        write_status: 'not_authorized',
        raw_write_ready_for_execution: false,
        ...overrides,
    };
}

function syntheticManifest(overrides = {}) {
    return {
        batch_id: 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001',
        source: 'fotmob',
        route: 'html_hydration',
        raw_data_version: 'fotmob_pageprops_v2',
        hash_strategy: 'stable_pageprops_payload_v1',
        league: {
            league_id: 53,
            league_name: 'Ligue 1',
            season: '2025/2026',
        },
        target_manifest_schema: [{ field: 'target_id', required_for_future_target: true }],
        known_completed_targets: Array.from({ length: 8 }, (_, index) => ({
            external_id: String(4830746 + index),
            existing_versions: ['fotmob_html_hyd_v1', 'fotmob_pageprops_v2'],
        })),
        candidate_targets: Array.from({ length: 50 }, (_, index) => candidate(index)),
        next_required_step: 'source_inventory_enrichment_implementation',
        recommended_next_step: 'Phase 5.21L2V3V: source inventory enrichment implementation',
        raw_write_ready_for_execution: false,
        accepted_mapping_count: 0,
        requires_separate_identity_mapping_acceptance: true,
        requires_separate_baseline_acceptance: true,
        requires_separate_final_db_write_authorization: true,
        ...overrides,
    };
}

function syntheticL2V3UArtifact(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3U',
        artifact_status: 'completed_no_write_source_inventory_enrichment_planning',
        raw_write_ready_for_execution: false,
        accepted_mapping_count: 0,
        analyzed_inventory_path_count: 19,
        source_inventory_file_count: 5,
        missing_source_page_url_count: 50,
        missing_page_url_base_count: 50,
        missing_url_fragment_external_id_count: 50,
        missing_source_record_key_count: 50,
        proposed_new_field_count: 12,
        enrichment_confidence: 'medium',
        requires_followup_implementation: true,
        requires_target_regeneration: true,
        next_required_step: 'source_inventory_enrichment_implementation',
        ...overrides,
    };
}

function sourceTextByPath() {
    return {
        'src/infrastructure/services/FotMobSourceInventoryAdapter.js':
            'deriveSourceInventoryIdentityEvidence source_page_url_base source_url_fragment_external_id',
        'scripts/ops/single_league_target_discovery_source_inventory_preflight.js':
            'source_inventory_record_key identity_evidence_status',
        'scripts/ops/single_league_small_batch_target_manifest_plan.js':
            'source_inventory_record_key identity_evidence_status',
    };
}

function buildSyntheticRunResult(overrides = {}) {
    return mod.runSourceInventoryEnrichmentApply({
        manifest: syntheticManifest(),
        l2v3uArtifact: syntheticL2V3UArtifact(),
        sourceTextByPath: sourceTextByPath(),
        writeFiles: false,
        ...overrides,
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

test('L2V3V artifact records no-write source inventory enrichment implementation', () => {
    const result = buildSyntheticRunResult();
    assert.equal(result.ok, true);

    const artifact = result.artifact;
    const manifest = result.updated_manifest;

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3V');
    assert.equal(artifact.no_write, true);
    assert.equal(artifact.live_source_check_performed, false);
    assert.equal(artifact.network_request_performed, false);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_insert_performed, false);
    assert.equal(artifact.matches_write_performed, false);
    assert.equal(artifact.matches_external_id_modified, false);
    assert.equal(artifact.identity_mapping_acceptance_performed, false);
    assert.equal(artifact.baseline_acceptance_performed, false);
    assert.equal(artifact.raw_write_retry_performed, false);
    assert.equal(artifact.accepted_mapping_count, 0);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(artifact.implemented_enrichment_field_count, mod.ENRICHMENT_FIELDS.length);
    assert.equal(artifact.source_inventory_adapter_updated, true);
    assert.equal(artifact.manifest_candidate_builder_updated, true);
    assert.equal(manifest.phase_5_21_l2v3v_implementation_status, artifact.artifact_status);
    assert.equal(manifest.accepted_mapping_count, 0);
    assert.equal(manifest.raw_write_ready_for_execution, false);
});

test('current 50 candidates remain missing requested-side URL evidence without fabrication', () => {
    const result = buildSyntheticRunResult();
    const artifact = result.artifact;
    const target = result.updated_manifest.candidate_targets[0];

    assert.equal(artifact.candidate_targets_checked, 50);
    assert.equal(artifact.candidate_targets_with_source_page_url, 0);
    assert.equal(artifact.candidate_targets_with_source_page_url_base, 0);
    assert.equal(artifact.candidate_targets_with_source_url_fragment_external_id, 0);
    assert.equal(artifact.candidate_targets_with_source_inventory_record_key, 0);
    assert.equal(artifact.identity_evidence_complete_count, 0);
    assert.equal(artifact.identity_evidence_partial_count, 0);
    assert.equal(artifact.identity_evidence_missing_count, 50);
    assert.equal(artifact.raw_write_blocked_count, 50);
    assert.equal(target.source_page_url, null);
    assert.equal(target.source_page_url_base, null);
    assert.equal(target.source_url_fragment_external_id, null);
    assert.equal(target.source_inventory_record_key, null);
    assert.equal(target.identity_evidence_status, 'missing');
});

test('source-controlled URL fields can be enriched but do not imply accepted mapping or raw write readiness', () => {
    const manifest = syntheticManifest({
        candidate_targets: [
            candidate(0, {
                source_page_url: '/matches/home-vs-away/abcd12#9000001',
                source_inventory_record_key: 'l1_api_data_leagues:fixtures.allMatches.0:9000001',
            }),
            ...Array.from({ length: 49 }, (_, index) => candidate(index + 1)),
        ],
    });
    const result = buildSyntheticRunResult({ manifest });
    const target = result.updated_manifest.candidate_targets[0];

    assert.equal(target.source_page_url_base, '/matches/home-vs-away/abcd12');
    assert.equal(target.source_url_fragment_external_id, '9000001');
    assert.equal(target.source_slug, 'home-vs-away');
    assert.equal(target.source_route_code, 'abcd12');
    assert.equal(target.source_url_path_slug, 'abcd12');
    assert.equal(target.detail_external_id_candidate, '9000001');
    assert.equal(target.detail_identity_source, 'url_hash_fragment');
    assert.equal(target.identity_evidence_status, 'complete');
    assert.equal(result.artifact.identity_evidence_complete_count, 1);
    assert.equal(result.artifact.accepted_mapping_count, 0);
    assert.equal(result.artifact.raw_write_ready_for_execution, false);
    assert.equal(
        result.artifact.safety_contract.source_url_fragment_external_id_match_does_not_imply_accepted_mapping,
        true
    );
    assert.equal(
        result.artifact.safety_contract.source_page_url_base_match_does_not_imply_raw_write_ready_for_execution,
        true
    );
});

test('manifest schema includes all requested source inventory enrichment fields', () => {
    const result = buildSyntheticRunResult();
    const fields = new Set(result.updated_manifest.target_manifest_schema.map(entry => entry.field));

    for (const field of mod.ENRICHMENT_FIELDS) {
        assert.equal(fields.has(field), true, `${field} should be present`);
    }
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

test('helper does not import network, DB, browser, proxy, odds, or harvest modules', t => {
    installImportGuard(t);
    const loaded = loadFreshModule();
    assert.equal(typeof loaded.runSourceInventoryEnrichmentApply, 'function');
});

test('runSourceInventoryEnrichmentApply can write outputs to explicit temp paths', () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'l2v3v-enrichment-'));
    const artifactPath = path.join(tmpDir, 'artifact.json');
    const reportPath = path.join(tmpDir, 'report.md');
    const manifestPath = path.join(tmpDir, 'manifest.json');

    try {
        const result = buildSyntheticRunResult({
            writeFiles: true,
            artifactOutputPath: artifactPath,
            reportOutputPath: reportPath,
            manifestOutputPath: manifestPath,
        });

        assert.equal(result.ok, true);
        assert.equal(JSON.parse(fs.readFileSync(artifactPath, 'utf8')).proposal_phase, 'Phase 5.21L2V3V');
        assert.match(fs.readFileSync(reportPath, 'utf8'), /enriched source inventory result is not accepted mapping/i);
        assert.equal(JSON.parse(fs.readFileSync(manifestPath, 'utf8')).raw_write_ready_for_execution, false);
    } finally {
        fs.rmSync(tmpDir, { recursive: true, force: true });
    }
});

test('CLI parsing covers help, unknowns, and write-files option', () => {
    const parsed = mod.parseArgs(['--write-files=false', '--mystery', 'positional', '--h']);
    const splitParsed = mod.parseArgs(['--write-files', 'maybe']);
    const invalid = mod.validateCliOptions({ unknown: ['mystery'] });

    assert.equal(parsed.writeFiles, false);
    assert.equal(parsed.help, true);
    assert.deepEqual(parsed.unknown, ['mystery', 'positional']);
    assert.equal(splitParsed.writeFiles, true);
    assert.equal(invalid.ok, false);
    assert.match(invalid.errors.join('\n'), /unknown arguments/);
});

test('runCli covers help, invalid options, and repository no-write success', () => {
    let helpOutput = '';
    let invalidOutput = '';
    let successOutput = '';

    const helpStatus = mod.runCli(['--help'], { stdout: text => (helpOutput += text) });
    const invalidStatus = mod.runCli(['--unknown'], { stdout: text => (invalidOutput += text) });
    const successStatus = mod.runCli(['--write-files=false'], { stdout: text => (successOutput += text) });

    assert.equal(helpStatus, 0);
    assert.match(helpOutput, /Usage:/);
    assert.equal(invalidStatus, 2);
    assert.match(invalidOutput, /unknown arguments/);
    assert.equal(successStatus, 0);
    assert.match(successOutput, /Phase 5.21L2V3V/);
    assert.match(successOutput, /raw_write_ready_for_execution/);
});

test('validateInputs fails closed on unsafe manifest and L2V3U states', () => {
    const invalidManifest = mod.validateInputs(
        syntheticManifest({
            next_required_step: 'raw_write_retry',
            raw_write_ready_for_execution: true,
            accepted_mapping_count: 1,
        }),
        syntheticL2V3UArtifact()
    );
    const invalidU = mod.validateInputs(
        syntheticManifest(),
        syntheticL2V3UArtifact({
            proposal_phase: 'Phase 5.21L2V3T',
            raw_write_ready_for_execution: true,
            accepted_mapping_count: 1,
            requires_followup_implementation: false,
            next_required_step: 'raw_write_retry',
        })
    );

    assert.equal(invalidManifest.ok, false);
    assert.match(invalidManifest.errors.join('\n'), /next_required_step/);
    assert.match(invalidManifest.errors.join('\n'), /raw_write_ready_for_execution/);
    assert.match(invalidManifest.errors.join('\n'), /accepted_mapping_count/);
    assert.equal(invalidU.ok, false);
    assert.match(invalidU.errors.join('\n'), /L2V3U artifact/);
    assert.match(invalidU.errors.join('\n'), /raw_write_ready_for_execution/);
    assert.match(invalidU.errors.join('\n'), /accepted_mapping_count/);
    assert.match(invalidU.errors.join('\n'), /requires_followup_implementation/);
});

test('repository L2V3V artifacts preserve implementation-only safety when generated', () => {
    const artifactPath =
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.source_inventory_enrichment_implementation.phase521l2v3v.json';
    if (!fs.existsSync(path.join(PROJECT_ROOT, artifactPath))) {
        return;
    }

    const manifest = readJson('docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json');
    const artifact = readJson(artifactPath);
    const report = readText('docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3V.md');

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3V');
    assert.equal(artifact.no_write, true);
    assert.equal(artifact.network_request_performed, false);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_insert_performed, false);
    assert.equal(artifact.matches_write_performed, false);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(artifact.accepted_mapping_count, 0);
    assert.equal(artifact.candidate_targets_checked, 50);
    assert.equal(artifact.identity_evidence_missing_count, 50);
    assert.equal(manifest.phase_5_21_l2v3v_implementation_status, artifact.artifact_status);
    assert.equal(manifest.raw_write_ready_for_execution, false);
    assert.equal(manifest.accepted_mapping_count, 0);
    assert.match(report, /enriched source inventory result is not raw write authorization/i);
});
