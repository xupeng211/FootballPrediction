'use strict'; // lifecycle: test-fixture
const assert = require('node:assert/strict');
const test = require('node:test');
const fs = require('node:fs');
const path = require('node:path');

const MANIFEST = path.resolve(__dirname, '../../docs/_manifests/fotmob_ligue1_adg44_bounded_diagnostic_probe.json');

test('ADG44 probe manifest exists and has valid structure', () => {
    const a = JSON.parse(fs.readFileSync(MANIFEST, 'utf8'));
    assert.equal(a.planned_probe_target_count, 5);
    assert.equal(a.user_authorization_confirmed, true);
    assert.equal(a.authorization_gate_merged, true);
    assert.ok(Array.isArray(a.results));
    assert.equal(a.results.length, 5);
});

test('ADG44 probe all 5 targets have valid classifications', () => {
    const a = JSON.parse(fs.readFileSync(MANIFEST, 'utf8'));
    const validClasses = new Set([
        'canonical_url_pair_discovered_no_write',
        'route_hash_pair_verified_no_write',
        'route_hash_pair_reverse_fixture_rejected',
        'canonical_url_not_found',
        'blocked_403',
        'blocked_captcha_or_access_wall',
        'blocked_network_error',
        'blocked_api_endpoint_not_found',
        'blocked_unsafe_payload_requirement',
        'identity_mismatch_stop',
        'not_attempted_due_to_prior_stop',
        'probe_not_attempted_preflight_failed',
    ]);
    for (const r of a.results) {
        assert.ok(validClasses.has(r.classification), `invalid classification: ${r.classification}`);
        assert.equal(r.raw_write_ready, false);
    }
});

test('ADG44 probe safety flags are correct', () => {
    const a = JSON.parse(fs.readFileSync(MANIFEST, 'utf8'));
    const s = a.safety;
    assert.equal(s.db_write_performed, false);
    assert.equal(s.raw_write_execution_performed, false);
    assert.equal(s.raw_match_data_insert_performed, false);
    assert.equal(s.full_payload_saved, false);
    assert.equal(s.full_html_saved, false);
    assert.equal(s.full_pageprops_saved, false);
    assert.equal(s.full_raw_data_saved, false);
    assert.equal(s.full_source_body_saved, false);
    assert.equal(s.re_acceptance_performed, false);
    assert.equal(s.suspension_reversal_performed, false);
    assert.equal(s.proxy_used, false);
    assert.equal(s.captcha_bypass, false);
    assert.equal(s.browser_bypass_performed, false);
});

test('ADG44 probe raw_write_ready_count is 0', () => {
    const a = JSON.parse(fs.readFileSync(MANIFEST, 'utf8'));
    assert.equal(a.raw_write_ready_count, 0);
    assert.ok(a.results.every(r => r.raw_write_ready === false));
});

test('ADG44 count fields are consistent: endpoint requests vs target classifications', () => {
    const a = JSON.parse(fs.readFileSync(MANIFEST, 'utf8'));
    assert.equal(a.planned_probe_target_count, 5);
    assert.equal(a.target_classified_count, 5);
    assert.equal(a.endpoint_http_request_count, 2);
    assert.equal(a.attempted_http_request_count, 2);
    assert.equal(a.endpoint_404_count, 2);
    // endpoint_http_request_count (HTTP requests) != target_classified_count (targets classified)
    assert.notEqual(a.endpoint_http_request_count, a.target_classified_count, 'HTTP request count must differ from target count');
    assert.equal(a.endpoint_http_request_count, 2, 'exactly 2 HTTP endpoints were probed');
    assert.equal(a.target_classified_count, 5, 'exactly 5 targets were classified');
    assert.equal(a.successful_http_200_count, 0);
});

test('ADG44 probe targets match authorization gate selection', () => {
    const a = JSON.parse(fs.readFileSync(MANIFEST, 'utf8'));
    const targetIds = a.results.map(r => r.target_match_id).sort();
    const expected = [
        '53_20252026_4830473',
        '53_20252026_4830474',
        '53_20252026_4830478',
        '53_20252026_4830480',
        '53_20252026_4830499',
    ].sort();
    assert.deepEqual(targetIds, expected);
});

test('ADG44 probe has recommended next step and does not authorize raw write', () => {
    const a = JSON.parse(fs.readFileSync(MANIFEST, 'utf8'));
    assert.ok(a.recommended_next_step);
    assert.ok(a.recommended_next_step.includes('raw write'));
    assert.ok(/do not .*raw write/i.test(a.recommended_next_step), 'must explicitly forbid raw write');
});
