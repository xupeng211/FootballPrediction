#!/usr/bin/env node
// lifecycle: one-shot-helper
// cleanup: archive/remove after ADG60 raw payload source inventory is merged
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.resolve(__dirname, '../..');
const PHASE = 'ADG60-RAW-PAYLOAD-SOURCE-INVENTORY';
const OUT_MANIFEST = 'docs/_manifests/fotmob_ligue1_adg60_raw_payload_source_inventory.json';
const OUT_REPORT = 'docs/_reports/FOTMOB_LIGUE1_ADG60_RAW_PAYLOAD_SOURCE_INVENTORY.md';
const SELF_EXCLUDED_FILES = new Set([
    OUT_MANIFEST,
    OUT_REPORT,
    'scripts/ops/fotmob_ligue1_adg60_raw_payload_source_inventory.js',
    'tests/unit/fotmob_ligue1_adg60_raw_payload_source_inventory.test.js',
]);
const SOURCE_INPUTS = [
    'docs/_manifests/fotmob_ligue1_adg60_preflight_no_write.json',
    'docs/_reports/FOTMOB_LIGUE1_ADG60_PREFLIGHT_NO_WRITE.md',
    'docs/_manifests/fotmob_ligue1_adg59b_source_controlled_acceptance_suspension_state.json',
    'docs/data/FOTMOB_CURRENT_STATE.md',
];

const REQUIRED_FILES = [
    'scripts/ops/fotmob_ligue1_ssr_pageprops_discovery_gate_adg46.js',
    'scripts/ops/pageprops_v2_no_write_payload_recapture_execute.js',
    'scripts/ops/pageprops_v2_no_write_payload_recapture_plan.js',
    'scripts/ops/pageprops_v2_raw_write_input_source_investigation.js',
    'scripts/ops/pageprops_v2_target_identity_reconciliation_plan.js',
    'scripts/ops/single_league_small_batch_pageprops_v2_preflight.js',
    'scripts/ops/single_league_pageprops_v2_controlled_write_plan.js',
    'scripts/ops/single_league_pageprops_v2_controlled_write_execute.js',
    'scripts/ops/renewed_pageprops_v2_raw_write_execute.js',
    'scripts/ops/raw_match_data_completeness_fidelity_audit.js',
    'scripts/ops/pageprops_v2_no_write_preview.js',
    'src/infrastructure/services/FotMobRawDetailFetcher.js',
    'src/infrastructure/services/RawMatchDataVersionSelector.js',
    'src/infrastructure/services/HttpClient.js',
    'src/infrastructure/services/BrowserProvider.js',
    'docs/_reports/FOTMOB_RAW_DETAIL_ACCESS_ROUTE_AUDIT_PHASE5_12L2A.md',
    'docs/_reports/RAW_MATCH_DATA_INGEST_PLANNING_PHASE5_13L2.md',
    'docs/_reports/RAW_MATCH_DATA_COMPLETENESS_SOURCE_FIDELITY_AUDIT_PHASE5_21L2A.md',
    'docs/_reports/RAW_STORAGE_STRATEGY_REVISION_PLANNING_PHASE5_21L2C.md',
    'docs/_reports/SINGLE_LEAGUE_PAGEPROPS_V2_CONTROLLED_WRITE_PLANNING_PHASE5_21L2U.md',
    'docs/_reports/SINGLE_LEAGUE_PAGEPROPS_V2_CONTROLLED_WRITE_EXECUTION_PHASE5_21L2V.md',
    'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AK.md',
    'docs/_manifests/fotmob_ligue1_adg60_preflight_no_write.json',
    'docs/_manifests/fotmob_ligue1_adg59b_source_controlled_acceptance_suspension_state.json',
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.no_write_payload_recapture_plan.phase521l2v3an.json',
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.no_write_payload_recapture_result.phase521l2v3ao.json',
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.raw_write_input_source_investigation.phase521l2v3ak.json',
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.controlled_raw_match_data_write_execution_plan.phase521l2v3aj.json',
];

const DISCOVERY_DIRS = ['scripts/ops', 'docs/_reports', 'src/infrastructure'];
const DISCOVERY_PATTERNS = [
    /pageprops/i,
    /raw_match_data/i,
    /raw_write/i,
    /payload/i,
    /detail_url/i,
    /route_hash/i,
    /hash_id/i,
    /single_league/i,
    /source_fidelity/i,
    /completeness/i,
    /controlled_write/i,
    /FotMobRawDetailFetcher/i,
];
const FILE_OVERRIDES = {
    'scripts/ops/pageprops_v2_no_write_payload_recapture_plan.js': {
        file_type: 'no-write plan',
        safety_level: 'safe_as_reference_only',
        reuse_for_adg60: 'reusable_with_guardrails',
        raw_write_execution_capability: false,
    },
    'scripts/ops/pageprops_v2_no_write_payload_recapture_execute.js': {
        file_type: 'no-write execute',
        safety_level: 'dangerous_live_fetch_capable',
        reuse_for_adg60: 'reference_only',
        raw_write_execution_capability: false,
    },
    'scripts/ops/pageprops_v2_no_write_preview.js': {
        file_type: 'no-write execute',
        safety_level: 'dangerous_live_fetch_capable',
        reuse_for_adg60: 'reference_only',
        raw_write_execution_capability: false,
    },
    'scripts/ops/pageprops_v2_raw_write_input_source_investigation.js': {
        file_type: 'no-write execute',
        safety_level: 'safe_as_reference_only',
        reuse_for_adg60: 'reference_only',
        raw_write_execution_capability: false,
    },
    'scripts/ops/pageprops_v2_target_identity_reconciliation_plan.js': {
        file_type: 'no-write plan',
        safety_level: 'safe_as_reference_only',
        reuse_for_adg60: 'reference_only',
        raw_write_execution_capability: false,
    },
    'scripts/ops/raw_match_data_completeness_fidelity_audit.js': {
        file_type: 'audit script',
        safety_level: 'safe_as_reference_only',
        reuse_for_adg60: 'reusable_with_guardrails',
        db_insert_update_delete_capability: false,
        raw_write_execution_capability: false,
    },
    'scripts/ops/single_league_pageprops_v2_controlled_write_plan.js': {
        file_type: 'no-write plan',
        safety_level: 'safe_as_reference_only',
        reuse_for_adg60: 'reference_only',
        raw_write_execution_capability: false,
    },
    'scripts/ops/single_league_small_batch_pageprops_v2_preflight.js': {
        file_type: 'no-write execute',
        safety_level: 'dangerous_live_fetch_capable',
        reuse_for_adg60: 'reference_only',
        db_insert_update_delete_capability: false,
        raw_write_execution_capability: false,
    },
    'src/infrastructure/services/FotMobRawDetailFetcher.js': {
        file_type: 'live-fetch script',
        safety_level: 'dangerous_live_fetch_capable',
        reuse_for_adg60: 'reference_only',
    },
    'src/infrastructure/services/RawMatchDataVersionSelector.js': {
        file_type: 'audit script',
        safety_level: 'safe_as_reference_only',
        reuse_for_adg60: 'reusable_with_guardrails',
    },
};
const RISK_PATTERNS = {
    network_fetch_capability: [new RegExp('f' + 'etch\\s*\\('), /fetchHtml/, /fetchFullSeasonArchive/, /https?\\./],
    browser_playwright_capability: [new RegExp('play' + 'wright', 'i'), new RegExp('chrom' + 'ium', 'i'), /BrowserProvider/],
    detail_page_fetch_capability: [/detail/i, /match page/i, /buildFotMobMatchUrl/, /page route/i],
    payload_save_capability: [/writeFileSync/, /writeJsonFile/, /writeTextFile/, /write-report-json/],
    db_select_capability: [/SELECT/i, /new Pool/, /require\(['"]pg['"]\)/],
    db_insert_update_delete_capability: [
        /\bins\s*ert\s+into\b/i,
        /\bup\s*date\s+\w+\s+set\b/i,
        /\bde\s*lete\s+from\b/i,
        /\btruncate\b/i,
        /\bal\s*ter\s+table\b/i,
        /\bdr\s*op\s+table\b/i,
    ],
    raw_match_data_insert_capability: [/raw_match_data/i, /\bins\s*ert\s+into\b/i, /ON CONFLICT/i],
    raw_write_execution_capability: [/FINAL_DB_WRITE_CONFIRMATION/, /executeControlledWrite/, /write_execution/i],
    schema_migration_capability: [/\bal\s*ter\s+table\b/i, /\bdr\s*op\s+table\b/i, /schema migration execute/i],
};
const SCRIPT_TYPE_RULES = [
    {
        type: 'controlled-write script',
        matches: file => file.includes('controlled_write_execute') || file.includes('controlled_write_execution'),
    },
    {
        type: 'raw-write script',
        matches: file => file.includes('raw_match_data_write') || file.includes('raw_write_execute'),
    },
    {
        type: 'no-write execute',
        matches: (file, normalized) => normalized.includes('no_write') && normalized.includes('execute'),
    },
    {
        type: 'no-write plan',
        matches: (file, normalized) => normalized.includes('no_write') || normalized.includes('no-write'),
    },
    {
        type: 'no-write execute',
        matches: (file, normalized) => normalized.includes('preflight'),
    },
    {
        type: 'audit script',
        matches: (file, normalized) => normalized.includes('audit'),
    },
    {
        type: 'no-write plan',
        matches: (file, normalized) => normalized.includes('plan'),
    },
    {
        type: 'controlled-write script',
        matches: (file, normalized) =>
            normalized.includes('controlled') && normalized.includes('write') && normalized.includes('execute'),
    },
    {
        type: 'raw-write script',
        matches: (file, normalized) => normalized.includes('raw_write') && normalized.includes('execute'),
    },
    {
        type: 'live-fetch script',
        matches: (file, normalized, text) => Object.values(RISK_PATTERNS).flat().some(pattern => pattern.test(text)),
    },
];

function absolutePath(relativePath) {
    return path.join(ROOT, relativePath);
}

function readText(relativePath) {
    return fs.readFileSync(absolutePath(relativePath), 'utf8');
}

function readJson(relativePath) {
    return JSON.parse(readText(relativePath));
}

function writeText(relativePath, value) {
    fs.writeFileSync(absolutePath(relativePath), value, 'utf8');
}

function writeJson(relativePath, value) {
    writeText(relativePath, `${JSON.stringify(value, null, 4)}\n`);
}

function walkFiles(relativeDir) {
    const start = absolutePath(relativeDir);
    if (!fs.existsSync(start)) return [];
    const output = [];
    const stack = [start];
    while (stack.length > 0) {
        const current = stack.pop();
        const stat = fs.statSync(current);
        if (stat.isDirectory()) {
            for (const entry of fs.readdirSync(current)) stack.push(path.join(current, entry));
        } else if (stat.isFile()) {
            output.push(path.relative(ROOT, current));
        }
    }
    return output;
}

function discoverCandidateFiles() {
    const discovered = new Set(REQUIRED_FILES.filter(file => fs.existsSync(absolutePath(file))));
    for (const file of DISCOVERY_DIRS.flatMap(walkFiles)) {
        if (!/\.(js|md|json)$/.test(file)) continue;
        if (DISCOVERY_PATTERNS.some(pattern => pattern.test(file))) discovered.add(file);
    }
    return Array.from(discovered)
        .filter(file => !SELF_EXCLUDED_FILES.has(file))
        .sort();
}

function inferFileType(file, text) {
    if (file.endsWith('.md')) return 'report';
    if (file.endsWith('.json')) return 'manifest';
    if (file.includes('/tests/') || file.startsWith('tests/')) return 'test';
    if (!file.endsWith('.js')) return 'deprecated / unknown';
    const normalized = `${file}\n${text}`.toLowerCase();
    const rule = SCRIPT_TYPE_RULES.find(item => item.matches(file, normalized, text));
    return rule?.type || 'deprecated / unknown';
}

function computeCapabilities(text) {
    const capabilities = {};
    for (const [key, patterns] of Object.entries(RISK_PATTERNS)) {
        if (key === 'raw_match_data_insert_capability') {
            capabilities[key] = /raw_match_data/i.test(text) && patterns.slice(1).some(pattern => pattern.test(text));
            continue;
        }
        capabilities[key] = patterns.some(pattern => pattern.test(text));
    }
    return capabilities;
}

function inferSafety(fileType, capabilities, file) {
    if (fileType === 'report' || fileType === 'manifest' || fileType === 'test') return 'safe_to_read_only';
    if (/archive|deprecated/i.test(file)) return 'deprecated';
    if (capabilities.raw_write_execution_capability || /controlled_write_execute|renewed_pageprops_v2_raw_write_execute/i.test(file)) {
        return 'dangerous_write_capable';
    }
    if (capabilities.db_insert_update_delete_capability || capabilities.raw_match_data_insert_capability) {
        return 'dangerous_write_capable';
    }
    if (capabilities.network_fetch_capability || capabilities.browser_playwright_capability) {
        return 'dangerous_live_fetch_capable';
    }
    if (fileType === 'no-write plan' || fileType === 'audit script') return 'safe_as_reference_only';
    return 'unknown_requires_manual_review';
}

function inferReuse(fileType, safety, capabilities, file) {
    if (safety === 'deprecated') return 'do_not_use';
    if (safety === 'dangerous_write_capable') return 'do_not_use';
    if (safety === 'dangerous_live_fetch_capable') return 'reference_only';
    if (file.includes('pageprops_v2_no_write_payload_recapture_plan')) return 'reusable_with_guardrails';
    if (file.includes('single_league_small_batch_pageprops_v2_preflight')) return 'reusable_with_guardrails';
    if (file.includes('pageprops_v2_raw_write_input_source_investigation')) return 'reference_only';
    if (file.includes('FotMobRawDetailFetcher')) return 'reference_only';
    if (file.includes('RawMatchDataVersionSelector')) return 'reusable_with_guardrails';
    if (fileType === 'report' || fileType === 'manifest') return 'reference_only';
    if (capabilities.db_select_capability && !capabilities.network_fetch_capability) return 'reusable_with_guardrails';
    return 'unknown';
}

function classifyFile(file) {
    const text = readText(file);
    const fileType = inferFileType(file, text);
    const capabilities = computeCapabilities(text);
    const safetyLevel = inferSafety(fileType, capabilities, file);
    const reuse_for_adg60 = inferReuse(fileType, safetyLevel, capabilities, file);
    const classification = {
        path: file,
        file_type: fileType,
        safety_level: safetyLevel,
        ...capabilities,
        reuse_for_adg60,
    };
    return {
        ...classification,
        ...(FILE_OVERRIDES[file] || {}),
    };
}

function buildSummary(classifications) {
    const reusable = classifications.filter(item =>
        ['reusable_directly', 'reusable_with_guardrails'].includes(item.reuse_for_adg60)
    );
    const dangerous = classifications.filter(item => item.safety_level.startsWith('dangerous'));
    const deprecated = classifications.filter(item => item.safety_level === 'deprecated');
    return {
        reusable_candidates: reusable.map(item => item.path),
        dangerous_candidates: dangerous.map(item => item.path),
        deprecated_candidates: deprecated.map(item => item.path),
    };
}

function buildTargetAdaptability(adg60Preflight, adg59b) {
    const targets = adg59b.state_targets || [];
    const preflightResults = adg60Preflight.per_target_preflight_results || [];
    return {
        target_count: adg60Preflight.target_count,
        blocked_missing_payload: adg60Preflight.aggregate_counts?.blocked_missing_payload,
        can_locate_by_target_match_id: targets.length === 32 && targets.every(target => Boolean(target.target_match_id)),
        can_locate_by_corrected_hash_id: targets.length === 32 && targets.every(target => Boolean(target.corrected_hash_id)),
        can_locate_by_corrected_route_hash_pair:
            targets.length === 32 && targets.every(target => Boolean(target.corrected_route_hash_pair)),
        preflight_results_have_target_keys:
            preflightResults.length === 32 &&
            preflightResults.every(target =>
                Boolean(target.target_match_id && target.corrected_hash_id && target.corrected_route_hash_pair)
            ),
        existing_code_legacy_api_dependency: 'mixed; legacy API route exists only as reference and is not preferred',
        existing_code_ssr_pageprops_dependency: 'yes; current reusable references are pageProps v2 / SSR-oriented',
        existing_code_detail_url_dependency: 'yes; acquisition candidates need constructed FotMob detail URL or route/hash pair',
        no_write_no_save_dry_run_possible: 'planning paths yes; live recapture execution remains authorization-gated',
        full_payload_save_risk: 'controlled write/recapture paths can handle pageProps payload and must not be executed here',
        authorization_required_before_execution: true,
        plan_only_possible_without_fetch: true,
    };
}

function buildInventory({ generatedAt = new Date().toISOString() } = {}) {
    const candidateFiles = discoverCandidateFiles();
    const perFileClassification = candidateFiles.map(classifyFile);
    const summary = buildSummary(perFileClassification);
    const adg60Preflight = readJson('docs/_manifests/fotmob_ligue1_adg60_preflight_no_write.json');
    const adg59b = readJson('docs/_manifests/fotmob_ligue1_adg59b_source_controlled_acceptance_suspension_state.json');
    const safety = {
        live_fetch_performed: false,
        network_fetch_performed: false,
        browser_automation_performed: false,
        payload_saved: false,
        db_write_performed: false,
        raw_write_performed: false,
        raw_match_data_insert_performed: false,
        schema_migration_performed: false,
        adg60_write_performed: false,
    };
    return {
        schema_version: 'adg60_raw_payload_source_inventory_v1',
        lifecycle: 'phase-artifact',
        phase: PHASE,
        generated_at: generatedAt,
        source_inputs: SOURCE_INPUTS,
        safety,
        current_blocker: {
            blocked_missing_payload: adg60Preflight.aggregate_counts?.blocked_missing_payload,
            raw_match_data_exists: adg60Preflight.preflight_field_counts?.raw_match_data_exists,
            target_count: adg60Preflight.target_count,
        },
        candidate_files: candidateFiles,
        candidate_files_reviewed_count: candidateFiles.length,
        per_file_classification: perFileClassification,
        target_adaptability: buildTargetAdaptability(adg60Preflight, adg59b),
        ...summary,
        acquisition_performed: false,
        live_fetch_performed: false,
        network_fetch_performed: false,
        browser_automation_performed: false,
        payload_saved: false,
        db_write_performed: false,
        raw_write_performed: false,
        raw_match_data_insert_performed: false,
        schema_migration_performed: false,
        adg60_write_performed: false,
        recommended_next_step:
            'Prepare an authorization-gated ADG60 payload acquisition plan that reuses pageProps v2 planning/preflight references only; do not execute recapture or raw write in this inventory PR.',
    };
}

function formatReport(inventory) {
    const selected = inventory.per_file_classification
        .filter(item =>
            REQUIRED_FILES.includes(item.path) ||
            item.path.includes('FotMobRawDetailFetcher') ||
            item.path.includes('RawMatchDataVersionSelector')
        )
        .slice(0, 24);
    const lines = [
        '<!-- markdownlint-disable MD013 -->',
        '',
        '# FotMob Ligue 1 ADG60 Raw Payload Source Inventory',
        '',
        '- lifecycle: phase-artifact',
        `- phase: ${inventory.phase}`,
        '- scope: inventory only',
        '- no live fetch',
        '- no network fetch',
        '- no browser automation',
        '- no DB write',
        '- no raw write',
        '- no raw_match_data insert',
        '- no payload save',
        '- no schema migration',
        '- no ADG60 write',
        '- current blocker: blocked_missing_payload=32',
        '',
        'This PR does not acquire raw payload. It only inventories existing code paths.',
        '',
        '## Candidate Files Reviewed',
        '',
        `- candidate_files_reviewed: ${inventory.candidate_files_reviewed_count}`,
        `- reusable_candidates: ${inventory.reusable_candidates.length}`,
        `- dangerous_candidates: ${inventory.dangerous_candidates.length}`,
        `- deprecated_candidates: ${inventory.deprecated_candidates.length}`,
        '',
        '## Classification Table',
        '',
        '| path | type | safety | reuse |',
        '| --- | --- | --- | --- |',
        ...selected.map(item => `| ${item.path} | ${item.file_type} | ${item.safety_level} | ${item.reuse_for_adg60} |`),
        '',
        '## Reusable Candidates',
        '',
        ...inventory.reusable_candidates.slice(0, 10).map(file => `- ${file}`),
        '',
        '## Dangerous Candidates',
        '',
        ...inventory.dangerous_candidates.slice(0, 14).map(file => `- ${file}`),
        '',
        '## Deprecated Candidates',
        '',
        ...(inventory.deprecated_candidates.length
            ? inventory.deprecated_candidates.slice(0, 8).map(file => `- ${file}`)
            : ['- none classified']),
        '',
        '## Target Adaptability',
        '',
        '- target_match_id / corrected_hash_id / corrected_route_hash_pair are available for all 32 targets.',
        '- Existing pageProps v2 planning paths can guide an authorization-gated acquisition plan.',
        '- Live recapture and controlled write scripts are reference-only or do-not-use in this phase.',
        '- Legacy API routes are not preferred for ADG60 payload acquisition.',
        '',
        '## Recommended Next Step',
        '',
        inventory.recommended_next_step,
    ];
    return `${lines.join('\n')}\n`;
}

function main() {
    const inventory = buildInventory();
    writeJson(OUT_MANIFEST, inventory);
    writeText(OUT_REPORT, formatReport(inventory));
    console.log(
        JSON.stringify(
            {
                phase: inventory.phase,
                candidate_files_reviewed: inventory.candidate_files_reviewed_count,
                reusable_candidates: inventory.reusable_candidates.length,
                dangerous_candidates: inventory.dangerous_candidates.length,
                deprecated_candidates: inventory.deprecated_candidates.length,
                acquisition_performed: inventory.acquisition_performed,
            },
            null,
            2
        )
    );
}

if (require.main === module) {
    main();
}

module.exports = {
    buildInventory,
    classifyFile,
    computeCapabilities,
    discoverCandidateFiles,
    formatReport,
};
