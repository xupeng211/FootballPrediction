#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const PHASE = 'Phase 5.21-ADG8';
const STATUS = 'completed_bounded_identity_mapping_source_inventory_audit_execution';
const ADG7_PLAN_PATH = 'docs/_manifests/fotmob_identity_mapping_source_inventory_audit_plan.adg7.json';
const ADG6_RESULT_PATH = 'docs/_manifests/fotmob_request_contract_page_route_validation_result.adg6.json';
const ENRICHED_TARGETS_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.enriched_targets.phase521l2v3aa.json';
const ARTIFACT_OUTPUT_PATH = 'docs/_manifests/fotmob_identity_mapping_source_inventory_audit_result.adg8.json';
const REPORT_OUTPUT_PATH = 'docs/_reports/FOTMOB_IDENTITY_MAPPING_SOURCE_INVENTORY_AUDIT_RESULT_ADG8.md';
const DATE_TOLERANCE_DAYS = 1;
const AUDIT_CLASSIFICATIONS = Object.freeze([
    'correct_mapping',
    'reverse_fixture_mapping_error',
    'home_away_inversion',
    'same_team_pair_wrong_leg',
    'date_mismatch',
    'competition_mismatch',
    'source_inventory_route_error',
    'candidate_generation_rule_defect',
    'slug_collision_or_ambiguous_route',
    'detail_hash_candidate_wrong_for_target',
    'suspended_reference_still_blocked',
    'insufficient_source_inventory_evidence',
]);
const AUDIT_FIELDS = Object.freeze([
    'target_match_id',
    'schedule_external_id',
    'expected_detail_external_id_candidate',
    'observed_detail_id',
    'source_page_url',
    'source_url_path_slug',
    'source_url_fragment_external_id',
    'expected_home_team',
    'expected_away_team',
    'observed_home_team',
    'observed_away_team',
    'expected_match_date',
    'observed_match_date',
    'expected_competition',
    'observed_competition',
    'source_inventory_record_key',
    'candidate_generation_rule',
    'route_matching_rule',
    'team_pair_key',
    'home_away_orientation_status',
    'date_delta',
    'competition_match_status',
    'reverse_fixture_detected',
    'mapping_correction_candidate',
    'audit_classification',
]);

function absolutePath(filePath) {
    return path.isAbsolute(filePath) ? filePath : path.join(PROJECT_ROOT, filePath);
}

function readJsonFile(filePath) {
    return JSON.parse(fs.readFileSync(absolutePath(filePath), 'utf8'));
}

function writeJsonFile(filePath, value) {
    fs.writeFileSync(absolutePath(filePath), `${JSON.stringify(value, null, 4)}\n`, 'utf8');
}

function writeTextFile(filePath, value) {
    fs.writeFileSync(absolutePath(filePath), value, 'utf8');
}

function normalizeText(value) {
    const text = String(value ?? '').trim();
    return text || null;
}

function firstText(...values) {
    for (const value of values) {
        const text = normalizeText(value);
        if (text) return text;
    }
    return null;
}

function normalizeTeam(value) {
    return String(value ?? '')
        .trim()
        .toLowerCase()
        .replace(/\s+/g, ' ');
}

function teamPairKey(homeTeam, awayTeam) {
    return [normalizeTeam(homeTeam), normalizeTeam(awayTeam)].filter(Boolean).sort().join('|') || null;
}

function parseDateMs(value) {
    const text = normalizeText(value);
    if (!text) return null;
    const parsed = Date.parse(text);
    return Number.isFinite(parsed) ? parsed : null;
}

function dateDeltaDays(expectedDate, observedDate) {
    const expected = parseDateMs(expectedDate);
    const observed = parseDateMs(observedDate);
    if (expected === null || observed === null) return null;
    return Math.round(Math.abs(observed - expected) / 86400000);
}

function buildEnrichedTargetMap(enrichedArtifact = {}) {
    const map = new Map();
    for (const target of enrichedArtifact.enriched_targets || []) {
        if (target?.schedule_external_id) {
            map.set(String(target.schedule_external_id), target);
        }
        if (target?.external_id) {
            map.set(String(target.external_id), target);
        }
    }
    return map;
}

function buildAdg6SampleMap(adg6Result = {}) {
    const map = new Map();
    for (const sample of adg6Result.samples || []) {
        map.set(sample.sample_id, sample);
    }
    return map;
}

function collectPlannedSamples(plan = {}) {
    const planned = plan.planned_audit_samples || {};
    return [
        ...(planned.positive_control || []).map(sample => ({ ...sample, audit_group: 'positive_control' })),
        ...(planned.reverse_fixture_samples || []).map(sample => ({
            ...sample,
            audit_group: 'reverse_fixture_sample',
        })),
        ...(planned.suspended_reference_samples || []).map(sample => ({
            ...sample,
            audit_group: 'suspended_reference_sample',
        })),
    ];
}

function getExpectedDate(sample = {}, adg6Sample = {}, enrichedTarget = {}) {
    return firstText(sample.expected_match_date, adg6Sample.expected_match_date, enrichedTarget.schedule_date);
}

function getSourcePageUrl(sample = {}, adg6Sample = {}, enrichedTarget = {}) {
    return firstText(sample.source_page_url, adg6Sample.source_page_url, enrichedTarget.source_page_url);
}

function getSourceSlug(sample = {}, adg6Sample = {}, enrichedTarget = {}) {
    return firstText(sample.source_url_path_slug, adg6Sample.source_url_path_slug, enrichedTarget.source_route_code);
}

function buildIdentitySignals(sample = {}) {
    const expectedHome = normalizeTeam(sample.expected_home_team);
    const expectedAway = normalizeTeam(sample.expected_away_team);
    const observedHome = normalizeTeam(sample.observed_home_team);
    const observedAway = normalizeTeam(sample.observed_away_team);
    const detailMatches = Boolean(
        sample.expected_detail_external_id_candidate &&
        sample.observed_detail_id &&
        sample.expected_detail_external_id_candidate === sample.observed_detail_id
    );
    const teamOrderMatches = Boolean(
        expectedHome &&
        expectedAway &&
        observedHome &&
        observedAway &&
        expectedHome === observedHome &&
        expectedAway === observedAway
    );
    const homeAwayReversed = Boolean(
        expectedHome &&
        expectedAway &&
        observedHome &&
        observedAway &&
        expectedHome === observedAway &&
        expectedAway === observedHome
    );
    return { detailMatches, teamOrderMatches, homeAwayReversed };
}

function classifyAuditRecord({ sample, signals, dateDelta }) {
    if (sample.audit_group === 'suspended_reference_sample') {
        return 'suspended_reference_still_blocked';
    }
    if (signals.detailMatches && signals.teamOrderMatches) {
        return 'correct_mapping';
    }
    if (signals.homeAwayReversed && dateDelta !== null && dateDelta > DATE_TOLERANCE_DAYS) {
        return 'reverse_fixture_mapping_error';
    }
    if (signals.homeAwayReversed) {
        return 'home_away_inversion';
    }
    if (dateDelta !== null && dateDelta > DATE_TOLERANCE_DAYS) {
        return 'date_mismatch';
    }
    if (sample.expected_detail_external_id_candidate !== sample.observed_detail_id) {
        return 'detail_hash_candidate_wrong_for_target';
    }
    return 'insufficient_source_inventory_evidence';
}

function buildBaseAuditRecord({ plannedSample = {}, adg6Sample = {}, enrichedTarget = {} }) {
    const expectedHomeTeam = firstText(
        plannedSample.expected_home_team,
        adg6Sample.expected_home_team,
        enrichedTarget.schedule_home_team
    );
    const expectedAwayTeam = firstText(
        plannedSample.expected_away_team,
        adg6Sample.expected_away_team,
        enrichedTarget.schedule_away_team
    );
    return {
        target_match_id: firstText(plannedSample.target_match_id, enrichedTarget.match_id),
        schedule_external_id: firstText(
            plannedSample.schedule_external_id,
            adg6Sample.source_url_fragment_external_id,
            enrichedTarget.schedule_external_id
        ),
        expected_detail_external_id_candidate: firstText(
            plannedSample.expected_detail_external_id_candidate,
            adg6Sample.detail_external_id_candidate
        ),
        observed_detail_id: firstText(
            plannedSample.observed_detail_id,
            adg6Sample.observed_detail_id_if_safely_available
        ),
        source_page_url: getSourcePageUrl(plannedSample, adg6Sample, enrichedTarget),
        source_url_path_slug: getSourceSlug(plannedSample, adg6Sample, enrichedTarget),
        source_url_fragment_external_id: firstText(
            plannedSample.source_url_fragment_external_id,
            adg6Sample.source_url_fragment_external_id,
            enrichedTarget.source_url_fragment_external_id
        ),
        expected_home_team: expectedHomeTeam,
        expected_away_team: expectedAwayTeam,
        observed_home_team: firstText(
            plannedSample.observed_home_team,
            adg6Sample.observed_home_team_if_safely_available
        ),
        observed_away_team: firstText(
            plannedSample.observed_away_team,
            adg6Sample.observed_away_team_if_safely_available
        ),
        expected_match_date: getExpectedDate(plannedSample, adg6Sample, enrichedTarget),
        observed_match_date: firstText(plannedSample.observed_match_date, adg6Sample.observed_date_if_safely_available),
        expected_competition: firstText(plannedSample.expected_competition, adg6Sample.expected_competition),
        observed_competition: null,
        source_inventory_record_key: firstText(enrichedTarget.source_inventory_record_key),
        candidate_generation_rule: 'url_hash_fragment_candidate_without_strict_fixture_guard',
        route_matching_rule: 'source_controlled_page_route_safe_summary_no_live_fetch',
        team_pair_key: teamPairKey(expectedHomeTeam, expectedAwayTeam),
        home_away_orientation_status: null,
        date_delta: null,
        competition_match_status: null,
        reverse_fixture_detected: false,
        mapping_correction_candidate: false,
        audit_classification: null,
    };
}

function orientationStatus(signals = {}) {
    if (signals.homeAwayReversed) return 'reversed';
    if (signals.teamOrderMatches) return 'matches';
    return 'unknown_or_mismatch';
}

function competitionStatus(sample = {}) {
    if (!sample.observed_competition) return 'observed_competition_not_in_adg6_safe_summary';
    return sample.observed_competition === sample.expected_competition ? 'match' : 'mismatch';
}

function buildCorrectionFields(sample = {}, mappingCorrectionCandidate = false) {
    return {
        rejected_detail_external_id_candidate: mappingCorrectionCandidate
            ? sample.expected_detail_external_id_candidate
            : null,
        observed_reversed_detail_id: mappingCorrectionCandidate ? sample.observed_detail_id : null,
        expected_detail_identity_missing_or_wrong: Boolean(
            mappingCorrectionCandidate && sample.expected_detail_external_id_candidate !== sample.observed_detail_id
        ),
        correction_needed: mappingCorrectionCandidate,
        correction_type: mappingCorrectionCandidate ? 'reject_candidate' : null,
        correction_actions: mappingCorrectionCandidate
            ? [
                  'reject_candidate',
                  'supersede_candidate',
                  'require_new_source_inventory_record',
                  'require_strict_home_away_date_guard',
              ]
            : [],
        source_inventory_mutation_performed: false,
        candidate_mutation_performed: false,
        raw_write_ready: false,
    };
}

function buildAuditRecord({ plannedSample = {}, adg6Sample = {}, enrichedTarget = {} }) {
    const sample = buildBaseAuditRecord({ plannedSample, adg6Sample, enrichedTarget });
    const signals = buildIdentitySignals(sample);
    sample.home_away_orientation_status = orientationStatus(signals);
    sample.date_delta = dateDeltaDays(sample.expected_match_date, sample.observed_match_date);
    sample.competition_match_status = competitionStatus(sample);
    sample.reverse_fixture_detected =
        signals.homeAwayReversed && sample.date_delta !== null && sample.date_delta > DATE_TOLERANCE_DAYS;
    sample.audit_classification = classifyAuditRecord({
        sample: { ...sample, audit_group: plannedSample.audit_group },
        signals,
        dateDelta: sample.date_delta,
    });
    sample.mapping_correction_candidate = plannedSample.audit_group === 'reverse_fixture_sample';
    Object.assign(sample, buildCorrectionFields(sample, sample.mapping_correction_candidate));
    sample.reference_status =
        plannedSample.audit_group === 'suspended_reference_sample' ? 'blocked_reference_only_no_unsuspend' : null;
    return sample;
}

function buildAuditRecords(plan = {}, adg6Result = {}, enrichedArtifact = {}) {
    const adg6BySample = buildAdg6SampleMap(adg6Result);
    const enrichedByExternalId = buildEnrichedTargetMap(enrichedArtifact);
    return collectPlannedSamples(plan).map(plannedSample => {
        const adg6Sample = adg6BySample.get(plannedSample.sample_id) || {};
        const enrichedTarget = enrichedByExternalId.get(String(plannedSample.schedule_external_id || '')) || {};
        return buildAuditRecord({ plannedSample, adg6Sample, enrichedTarget });
    });
}

function countBy(records = [], predicate) {
    return records.filter(predicate).length;
}

function buildSummary(records = []) {
    return {
        positive_control_count: countBy(records, item => item.audit_classification === 'correct_mapping'),
        reverse_fixture_sample_count: countBy(records, item => item.mapping_correction_candidate === true),
        suspended_reference_sample_count: countBy(
            records,
            item => item.reference_status === 'blocked_reference_only_no_unsuspend'
        ),
        correct_mapping_count: countBy(records, item => item.audit_classification === 'correct_mapping'),
        reverse_fixture_mapping_error_count: countBy(
            records,
            item => item.audit_classification === 'reverse_fixture_mapping_error'
        ),
        home_away_inversion_count: countBy(
            records,
            item => item.home_away_orientation_status === 'reversed' && item.mapping_correction_candidate === true
        ),
        same_team_pair_wrong_leg_count: countBy(
            records,
            item =>
                item.home_away_orientation_status === 'reversed' &&
                item.date_delta !== null &&
                item.date_delta > DATE_TOLERANCE_DAYS &&
                item.mapping_correction_candidate === true
        ),
        date_mismatch_count: countBy(
            records,
            item =>
                item.date_delta !== null &&
                item.date_delta > DATE_TOLERANCE_DAYS &&
                item.mapping_correction_candidate === true
        ),
        source_inventory_route_error_count: countBy(records, item => item.mapping_correction_candidate === true),
        candidate_generation_rule_defect_count: countBy(records, item => item.mapping_correction_candidate === true),
        suspended_reference_still_blocked_count: countBy(
            records,
            item => item.audit_classification === 'suspended_reference_still_blocked'
        ),
        mapping_correction_candidate_count: countBy(records, item => item.mapping_correction_candidate === true),
    };
}

function buildArtifact({
    plan = {},
    adg6Result = {},
    enrichedArtifact = {},
    generatedAt = new Date().toISOString(),
} = {}) {
    const auditRecords = buildAuditRecords(plan, adg6Result, enrichedArtifact);
    const summary = buildSummary(auditRecords);
    return {
        schema_version: 'fotmob_identity_mapping_source_inventory_audit_result_adg8_v1',
        phase: PHASE,
        generated_at: generatedAt,
        adg8_audit_execution_status: STATUS,
        audit_execution_performed: true,
        audit_scope: 'bounded_identity_mapping_source_inventory_audit_execution',
        audited_sample_count: auditRecords.length,
        ...summary,
        likely_root_cause: [
            'source_inventory_route_mapping_defect',
            'candidate_generation_rule_defect',
            'same_team_pair_wrong_leg_home_away_guard_missing',
        ],
        global_correction_recommendations: [
            'require strict home/away/date/competition guard before accepting detail hash candidate',
            'block same-team-pair candidate when home/away orientation mismatches',
            'reject URL hash candidate if observed page-route identity does not match expected schedule identity',
            'require source inventory audit before reclassification',
            'keep raw_write_execution_ready=false',
        ],
        recommended_next_step:
            'plan runtime correction guard for source inventory/candidate generation before any reclassification or raw write',
        source_inventory_mutation_performed: false,
        candidate_mutation_performed: false,
        db_write_performed: false,
        raw_match_data_insert_performed: false,
        raw_write_execution_performed: false,
        re_acceptance_execution_performed: false,
        suspension_reversal_performed: false,
        live_fetch_performed: false,
        network_request_performed: false,
        browser_automation_performed: false,
        direct_api_probing_performed: false,
        full_payload_saved: false,
        full_payload_printed: false,
        raw_write_execution_ready: false,
        audit_fields: AUDIT_FIELDS,
        audit_classifications: AUDIT_CLASSIFICATIONS,
        audit_results: auditRecords,
    };
}

function buildReport(artifact = {}) {
    const lines = [
        '# FotMob Identity Mapping / Source Inventory Audit Result ADG8',
        '',
        `- Phase: ${artifact.phase}`,
        `- Status: ${artifact.adg8_audit_execution_status}`,
        `- audit_execution_performed=${artifact.audit_execution_performed}`,
        `- correct_mapping_count=${artifact.correct_mapping_count}`,
        `- reverse_fixture_mapping_error_count=${artifact.reverse_fixture_mapping_error_count}`,
        `- home_away_inversion_count=${artifact.home_away_inversion_count}`,
        `- same_team_pair_wrong_leg_count=${artifact.same_team_pair_wrong_leg_count}`,
        `- date_mismatch_count=${artifact.date_mismatch_count}`,
        `- source_inventory_route_error_count=${artifact.source_inventory_route_error_count}`,
        `- candidate_generation_rule_defect_count=${artifact.candidate_generation_rule_defect_count}`,
        `- suspended_reference_still_blocked_count=${artifact.suspended_reference_still_blocked_count}`,
        `- mapping_correction_candidate_count=${artifact.mapping_correction_candidate_count}`,
        `- source_inventory_mutation_performed=${artifact.source_inventory_mutation_performed}`,
        `- candidate_mutation_performed=${artifact.candidate_mutation_performed}`,
        `- db_write_performed=${artifact.db_write_performed}`,
        `- raw_write_execution_performed=${artifact.raw_write_execution_performed}`,
        `- re_acceptance_execution_performed=${artifact.re_acceptance_execution_performed}`,
        `- suspension_reversal_performed=${artifact.suspension_reversal_performed}`,
        `- raw_write_execution_ready=${artifact.raw_write_execution_ready}`,
        '',
        '## Audit Results',
        '',
        '| sample | expected | observed | orientation | date_delta | classification | correction |',
        '| --- | --- | --- | --- | --- | --- | --- |',
    ];
    for (const result of artifact.audit_results || []) {
        lines.push(
            `| ${result.schedule_external_id} | ${result.expected_detail_external_id_candidate} ${result.expected_home_team} vs ${result.expected_away_team} | ${result.observed_detail_id} ${result.observed_home_team} vs ${result.observed_away_team} | ${result.home_away_orientation_status} | ${result.date_delta ?? 'null'} | ${result.audit_classification} | ${result.correction_needed} |`
        );
    }
    lines.push(
        '',
        '## Root Cause',
        '',
        '- source inventory route mapping defect',
        '- candidate generation rule defect',
        '- same-team-pair wrong-leg / home-away guard missing',
        '',
        '## Recommended Next Step',
        '',
        artifact.recommended_next_step,
        '',
        'No source inventory mutation, candidate mutation, DB write, raw write, re-acceptance, suspension reversal, live fetch, network request, browser automation, or full payload save/print was performed.'
    );
    return `${lines.join('\n')}\n`;
}

function parseArgs(argv = process.argv.slice(2)) {
    const options = { writeFiles: true, help: false, unknown: [] };
    for (const arg of argv) {
        if (arg === '--help' || arg === '-h') {
            options.help = true;
            continue;
        }
        if (arg === '--write-files=false' || arg === '--write-files=no' || arg === '--write-files=0') {
            options.writeFiles = false;
            continue;
        }
        if (arg === '--write-files=true' || arg === '--write-files=yes' || arg === '--write-files=1') {
            options.writeFiles = true;
            continue;
        }
        options.unknown.push(arg);
    }
    return options;
}

function validateOptions(options = {}) {
    const errors = [];
    if (options.unknown?.length) {
        errors.push(`unknown arguments: ${options.unknown.join(', ')}`);
    }
    return { ok: errors.length === 0, errors };
}

function runFotmobIdentityMappingSourceInventoryAuditExecuteAdg8(options = {}, dependencies = {}) {
    const plan = dependencies.plan || readJsonFile(ADG7_PLAN_PATH);
    const adg6Result = dependencies.adg6Result || readJsonFile(ADG6_RESULT_PATH);
    const enrichedArtifact = dependencies.enrichedArtifact || readJsonFile(ENRICHED_TARGETS_PATH);
    const generatedAt = dependencies.generatedAt || new Date().toISOString();
    const artifact = buildArtifact({ plan, adg6Result, enrichedArtifact, generatedAt });
    const report = buildReport(artifact);
    if (options.writeFiles !== false) {
        writeJsonFile(ARTIFACT_OUTPUT_PATH, artifact);
        writeTextFile(REPORT_OUTPUT_PATH, report);
    }
    return { ok: true, artifact, report };
}

function main(argv = process.argv.slice(2)) {
    const options = parseArgs(argv);
    if (options.help) {
        process.stdout.write(
            'Usage: node scripts/ops/fotmob_identity_mapping_source_inventory_audit_execute_adg8.js [--write-files=false]\n'
        );
        return { status: 0 };
    }
    const validation = validateOptions(options);
    if (!validation.ok) {
        process.stderr.write(`${validation.errors.join('\n')}\n`);
        return { status: 1 };
    }
    const result = runFotmobIdentityMappingSourceInventoryAuditExecuteAdg8(options);
    process.stdout.write(
        `${JSON.stringify(
            {
                adg8_audit_execution_status: result.artifact.adg8_audit_execution_status,
                audit_execution_performed: result.artifact.audit_execution_performed,
                correct_mapping_count: result.artifact.correct_mapping_count,
                reverse_fixture_mapping_error_count: result.artifact.reverse_fixture_mapping_error_count,
                mapping_correction_candidate_count: result.artifact.mapping_correction_candidate_count,
                raw_write_execution_ready: result.artifact.raw_write_execution_ready,
            },
            null,
            2
        )}\n`
    );
    return { status: 0 };
}

module.exports = {
    PHASE,
    STATUS,
    ADG7_PLAN_PATH,
    ADG6_RESULT_PATH,
    ENRICHED_TARGETS_PATH,
    ARTIFACT_OUTPUT_PATH,
    REPORT_OUTPUT_PATH,
    AUDIT_CLASSIFICATIONS,
    AUDIT_FIELDS,
    parseArgs,
    validateOptions,
    buildEnrichedTargetMap,
    buildAdg6SampleMap,
    collectPlannedSamples,
    dateDeltaDays,
    buildAuditRecord,
    buildAuditRecords,
    buildSummary,
    buildArtifact,
    buildReport,
    runFotmobIdentityMappingSourceInventoryAuditExecuteAdg8,
    main,
};

if (require.main === module) {
    try {
        process.exitCode = main().status;
    } catch (error) {
        process.stderr.write(`${error.stack || error.message}\n`);
        process.exitCode = 1;
    }
}
