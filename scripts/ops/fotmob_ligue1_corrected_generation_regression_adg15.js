#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const PHASE = 'Phase 5.21-ADG15';

const PROPOSAL_PATH = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json';
const ADG12_RESULT_PATH = 'docs/_manifests/fotmob_observed_identity_evidence_acquisition_result.adg12.json';
const SUSPENDED_REVIEW_PATH = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.suspended_target_review_result.phase521l2v3ba.json';
const ARTIFACT_OUTPUT_PATH = 'docs/_manifests/fotmob_ligue1_corrected_generation_regression.adg15.json';
const REPORT_OUTPUT_PATH = 'docs/_reports/FOTMOB_LIGUE1_CORRECTED_GENERATION_REGRESSION_ADG15.md';

const { classifyDetailCandidateIdentity, FIXTURE_IDENTITY_GUARD_PASSED, FIXTURE_IDENTITY_GUARD_BLOCKED } =
    require('../../src/infrastructure/services/FotMobRouteIdentityReconciler');

function abs(p) { return path.isAbsolute(p) ? p : path.join(PROJECT_ROOT, p); }
function readJson(p) { return JSON.parse(fs.readFileSync(abs(p), 'utf8')); }
function writeJson(p, v) { fs.writeFileSync(abs(p), `${JSON.stringify(v, null, 4)}\n`, 'utf8'); }
function writeText(p, v) { fs.writeFileSync(abs(p), v, 'utf8'); }

function buildObservedMap(adg12) {
    const m = new Map();
    for (const r of adg12.batch_results || []) {
        if (r.schedule_external_id && r.observed_detail_id)
            {m.set(r.schedule_external_id, r);}
    }
    return m;
}

function buildSuspendedSet(review) {
    return new Set(
        (review.review_cases || [])
            .filter(c => c.current_effective_status === 'suspended' && c.requested_external_id)
            .map(c => String(c.requested_external_id))
    );
}

function buildCompletedSet(proposal) {
    return new Set((proposal.known_completed_targets || []).map(t => String(t.external_id)));
}

function classifyTarget(candidate, observed, isSuspended) {
    const eid = String(candidate.external_id || '');
    const base = {
        external_id: eid,
        match_id: candidate.match_id || null,
        expected_home: candidate.schedule_home_team || candidate.home_team,
        expected_away: candidate.schedule_away_team || candidate.away_team,
        expected_date: candidate.schedule_date || candidate.match_date,
        expected_competition: candidate.league_name,
        is_suspended: isSuspended,
        has_observed: Boolean(observed),
    };

    if (isSuspended) return { ...base, classification: 'suspended_still_blocked', status: FIXTURE_IDENTITY_GUARD_BLOCKED, correction: false, raw_write_ready: false };

    const result = classifyDetailCandidateIdentity({
        schedule_home_team: base.expected_home,
        schedule_away_team: base.expected_away,
        schedule_date: base.expected_date,
        expected_competition: base.expected_competition,
        source_home_team: observed?.observed_home_team,
        source_away_team: observed?.observed_away_team,
        source_match_date: observed?.observed_match_date,
        detail_external_id_candidate: eid,
    });

    return {
        ...base,
        classification: result.detail_identity_candidate_status,
        status: result.fixture_identity_guard_status,
        correction: result.correction_needed,
        raw_write_ready: false,
        orientation: result.home_away_orientation,
        date_delta: result.date_delta_days,
    };
}

function run(deps = {}) {
    const proposal = deps.proposal || readJson(PROPOSAL_PATH);
    const adg12 = deps.adg12 || readJson(ADG12_RESULT_PATH);
    const suspendedReview = deps.suspendedReview || readJson(SUSPENDED_REVIEW_PATH);

    const observedMap = buildObservedMap(adg12);
    const suspendedSet = buildSuspendedSet(suspendedReview);
    const completedSet = buildCompletedSet(proposal);

    const results = [];
    for (const c of proposal.candidate_targets || []) {
        const eid = String(c.external_id || '');
        if (completedSet.has(eid)) continue;
        results.push(classifyTarget(c, observedMap.get(eid) || null, suspendedSet.has(eid)));
    }
    // Add positive control
    const pcObserved = observedMap.get('4813735');
    results.push(classifyTarget(
        { external_id: '4813735', home_team: 'AFC Bournemouth', away_team: 'Manchester City', match_date: '2026-05-19T18:30:00.000Z', league_name: 'Premier League', match_id: '55_20252026_4813735' },
        pcObserved || null, false));

    return results;
}

function cnt(list, pred) { return list.filter(pred).length; }

function buildArtifact(deps = {}) {
    const generatedAt = deps.generatedAt || new Date().toISOString();
    const results = run(deps);
    const s = {
        total_batch_target_count: results.length,
        request_contract_target_count: cnt(results, r => !r.is_suspended && r.external_id !== '4813735'),
        suspended_target_count: cnt(results, r => r.is_suspended),
        positive_control_count: cnt(results, r => r.external_id === '4813735'),
        accepted_validated_no_write_count: cnt(results, r => r.classification === 'accepted_validated'),
        rejected_reverse_fixture_mapping_count: cnt(results, r => r.classification === 'rejected_reverse_fixture_mapping'),
        rejected_home_away_inversion_count: cnt(results, r => r.classification === 'rejected_home_away_inversion'),
        requires_new_source_inventory_record_count: cnt(results, r => r.classification === 'requires_new_source_inventory_record'),
        unknown_insufficient_evidence_count: cnt(results, r => r.classification === 'unknown_insufficient_evidence'),
        suspended_still_blocked_count: cnt(results, r => r.classification === 'suspended_still_blocked'),
        correction_candidate_required_count: cnt(results, r => r.correction === true),
        raw_write_ready_count: 0,
        re_acceptance_candidate_count: 0,
    };

    const rec = s.unknown_insufficient_evidence_count > 25
        ? 'many targets lack observed identity; recommend evidence acquisition planning; do not raw write'
        : s.rejected_reverse_fixture_mapping_count > 3
            ? 'source inventory correction path confirmed; recommend correction implementation planning; do not raw write'
            : 'corrected generation path functional; recommend no-write acceptance review planning; do not raw write';

    return {
        schema_version: 'fotmob_ligue1_corrected_generation_regression_adg15_v1',
        phase: PHASE, generated_at: generatedAt,
        adg15_regression_status: 'completed_corrected_generation_regression',
        regression_execution_performed: true,
        no_live_fetch: true, no_network_request: true, no_db_write: true, no_raw_write: true,
        no_re_acceptance: true, no_suspension_reversal: true,
        source_inventory_mutation_performed: false, candidate_mutation_performed: false,
        raw_write_execution_performed: false, full_payload_saved: false,
        ...s, recommended_next_step: rec, regression_results: results,
    };
}

function buildReport(a) {
    const l = [
        '# Ligue 1 Corrected Generation Regression ADG15',
        '', `- Phase: ${a.phase}`, `- Status: ${a.adg15_regression_status}`, '',
        '## Counts',
        '| Metric | Count |', '| --- | --- |',
        `| total_batch | ${a.total_batch_target_count} |`,
        `| request_contract | ${a.request_contract_target_count} |`,
        `| suspended | ${a.suspended_target_count} |`,
        `| positive_control | ${a.positive_control_count} |`,
        `| accepted_validated_no_write | ${a.accepted_validated_no_write_count} |`,
        `| rejected_reverse_fixture_mapping | ${a.rejected_reverse_fixture_mapping_count} |`,
        `| unknown_insufficient_evidence | ${a.unknown_insufficient_evidence_count} |`,
        `| suspended_still_blocked | ${a.suspended_still_blocked_count} |`,
        `| correction_candidate_required | ${a.correction_candidate_required_count} |`,
        `| raw_write_ready | ${a.raw_write_ready_count} |`, '',
        '## Results',
        '| ext_id | expected | classification | status | correction | delta |',
        '| --- | --- | --- | --- | --- | --- |',
    ];
    for (const r of a.regression_results || []) {
        l.push(`| ${r.external_id} | ${r.expected_home} vs ${r.expected_away} | ${r.classification} | ${r.status} | ${r.correction} | ${r.date_delta ?? 'null'} |`);
    }
    l.push('', '## Safety', '', '- no live fetch / network / DB write / raw write', '- no re-acceptance / suspension reversal', '- no source inventory / candidate production mutation', '- raw_write_ready_count=0', '',
        `## Recommended Next Step`, '', a.recommended_next_step);
    return `${l.join('\n')}\n`;
}

function main() {
    const a = buildArtifact();
    writeJson(ARTIFACT_OUTPUT_PATH, a);
    writeText(REPORT_OUTPUT_PATH, buildReport(a));
    process.stdout.write(JSON.stringify({
        accepted: a.accepted_validated_no_write_count, rejected: a.rejected_reverse_fixture_mapping_count,
        unknown: a.unknown_insufficient_evidence_count, suspended: a.suspended_still_blocked_count,
        correction: a.correction_candidate_required_count, raw_write_ready: a.raw_write_ready_count,
    }, null, 2) + '\n');
    return { status: 0 };
}

module.exports = { PHASE, run, buildArtifact, buildReport, main };
if (require.main === module) { try { process.exitCode = main().status; } catch (e) { process.stderr.write(e.stack + '\n'); process.exitCode = 1; } }
