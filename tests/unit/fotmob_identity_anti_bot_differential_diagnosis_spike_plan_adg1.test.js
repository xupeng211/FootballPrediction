'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const PLAN_PATH = path.join(
    PROJECT_ROOT,
    'docs/_manifests/fotmob_identity_anti_bot_differential_diagnosis_spike_plan.adg1.json'
);
const REPORT_PATH = path.join(
    PROJECT_ROOT,
    'docs/_reports/FOTMOB_IDENTITY_ANTI_BOT_DIFFERENTIAL_DIAGNOSIS_SPIKE_PLAN_ADG1.md'
);

function readJson(filePath) {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

test('ADG1 records spike planning only with no runtime, network, DB, or raw write execution', () => {
    const plan = readJson(PLAN_PATH);

    assert.equal(plan.phase, 'Phase 5.21-ADG1');
    assert.equal(plan.plan_status, 'completed_spike_planning_only');
    assert.equal(plan.runtime_code_change, false);
    assert.equal(plan.safety_status.planning_only, true);
    assert.equal(plan.safety_status.spike_execution_performed, false);
    assert.equal(plan.safety_status.live_fetch_performed, false);
    assert.equal(plan.safety_status.detail_fetch_performed, false);
    assert.equal(plan.safety_status.network_request_performed, false);
    assert.equal(plan.safety_status.browser_automation_performed, false);
    assert.equal(plan.safety_status.db_write_performed, false);
    assert.equal(plan.safety_status.raw_match_data_insert_performed, false);
    assert.equal(plan.safety_status.raw_write_execution_performed, false);
    assert.equal(plan.safety_status.re_acceptance_execution_performed, false);
});

test('ADG1 preserves architecture decision gate state from PR 1334', () => {
    const plan = readJson(PLAN_PATH);
    const context = plan.architecture_decision_gate_context;

    assert.equal(context.source_pr, 1334);
    assert.equal(context.source_pr_merged, true);
    assert.equal(context.main_production_gate_green_before_adg1, true);
    assert.equal(context.architecture_decision_gate_triggered, true);
    assert.equal(context.no_progress_stop_rule_triggered, true);
    assert.equal(context.current_raw_write_route_paused, true);
    assert.equal(context.current_50_target_batch_not_raw_write_ready, true);
    assert.equal(context.needs_new_evidence_target_count, 42);
    assert.equal(context.suspended_target_count, 8);
    assert.equal(context.clean_candidate_count, 0);
    assert.equal(context.eligible_for_re_acceptance_review_count, 0);
    assert.equal(context.raw_write_execution_ready, false);
});

test('ADG1 includes positive sample 4813735 and URL hash extraction requirements', () => {
    const plan = readJson(PLAN_PATH);
    const reportText = fs.readFileSync(REPORT_PATH, 'utf8');

    assert.equal(plan.positive_sample.url_hash_id, '4813735');
    assert.equal(plan.positive_sample.url_path_slug_or_route_fragment, '2feiv3');
    assert.equal(
        plan.positive_sample.source_page_url,
        'https://www.fotmob.com/zh-Hans/matches/manchester-city-vs-afc-bournemouth/2feiv3#4813735'
    );
    assert.equal(reportText.includes('Does discovery extract URL hash ids like `#4813735`?'), true);
    assert.equal(plan.current_chain_audit_focus.discovery_extracts_url_hash_id, 'must_verify_in_adg2');
    assert.equal(
        plan.current_chain_audit_focus
            .recapture_uses_detail_external_id_or_url_hash_candidate_instead_of_schedule_external_id,
        'must_verify_in_adg2'
    );
});

test('ADG1 plans bounded sample groups with 8 suspended targets and 8 needs-new-evidence samples', () => {
    const plan = readJson(PLAN_PATH);
    const suspendedMap = new Map(
        plan.sample_groups.suspended_targets.map(item => [item.schedule_external_id, item.observed_detail_external_id])
    );

    assert.equal(plan.sample_groups.suspended_targets.length, 8);
    assert.equal(plan.sample_groups.needs_new_evidence_sample_external_ids.length, 8);
    assert.equal(plan.sample_groups.needs_new_evidence_population_count, 42);
    assert.equal(plan.sample_groups.bounded_sample_count_max, 17);

    assert.equal(suspendedMap.get('4830461'), '4830758');
    assert.equal(suspendedMap.get('4830463'), '4830622');
    assert.equal(suspendedMap.get('4830465'), '4830619');
    assert.equal(suspendedMap.get('4830466'), '4830759');
    assert.equal(suspendedMap.get('4830481'), '4830763');
    assert.equal(suspendedMap.get('4830496'), '4830757');
    assert.equal(suspendedMap.get('4830508'), '4830620');
    assert.equal(suspendedMap.get('4830511'), '4830760');
    assert.equal(plan.sample_groups.old_good_samples.status, 'unavailable');
    assert.equal(plan.sample_groups.old_good_samples.do_not_fabricate, true);
});

test('ADG1 diagnostic fields and classifications cover identity and anti-bot risks', () => {
    const plan = readJson(PLAN_PATH);
    const fields = new Set(plan.planned_identity_fields);
    const classifications = new Set(plan.classification_taxonomy);

    for (const field of [
        'schedule_external_id',
        'source_inventory_record_key',
        'source_page_url',
        'url_path_slug_or_route_fragment',
        'url_hash_id',
        'accepted_detail_external_id',
        'detail_request_id_to_be_used',
        'observed_payload_match_id',
        'observed_detail_external_id',
        'http_status',
        'content_type',
        'redirect_chain',
        'anti_bot_signs',
    ]) {
        assert.equal(fields.has(field), true, `${field} should be planned`);
    }

    for (const category of [
        'URL hash id not extracted',
        'URL hash id extracted but not persisted',
        'URL hash id persisted but not used by recapture runner',
        'schedule_external_id incorrectly used as detail id',
        'direct API identity differs from browser/page route identity',
        'missing headers/session/locale/region contract',
        'anti-bot/block/captcha/403/401 issue',
        'second source required for canonical fixture identity',
    ]) {
        assert.equal(classifications.has(category), true, `${category} should be planned`);
    }
});

test('ADG2 execution boundaries require separate authorization and remain no-write by default', () => {
    const plan = readJson(PLAN_PATH);
    const boundaries = plan.adg2_execution_boundaries;

    assert.equal(boundaries.requires_separate_explicit_authorization, true);
    assert.equal(boundaries.default_no_db_write, true);
    assert.equal(boundaries.default_no_raw_write, true);
    assert.equal(boundaries.network_browser_api_requires_explicit_authorization, true);
    assert.equal(boundaries.save_full_raw_data_pageprops_source_body, false);
    assert.equal(boundaries.safe_summary_only, true);
    assert.equal(boundaries.stop_sample_on_401_403_captcha_block_or_identity_mismatch, true);
    assert.equal(boundaries.captcha_bypass_allowed, false);
    assert.equal(boundaries.proxy_bypass_allowed, false);
    assert.equal(boundaries.large_scale_fetch_allowed, false);
    assert.equal(boundaries.bounded_sample_count_required, true);
});

test('ADG1 artifacts avoid full payload markers', () => {
    const planText = fs.readFileSync(PLAN_PATH, 'utf8');
    const reportText = fs.readFileSync(REPORT_PATH, 'utf8');

    for (const text of [planText, reportText]) {
        assert.equal(text.includes('"raw_data":'), false);
        assert.equal(text.includes('"pageProps":'), false);
        assert.equal(text.includes('__NEXT_DATA__'), false);
        assert.equal(text.includes('<!DOCTYPE'), false);
        assert.equal(text.includes('"body":'), false);
        assert.equal(text.includes('"source_body":'), false);
    }
});
