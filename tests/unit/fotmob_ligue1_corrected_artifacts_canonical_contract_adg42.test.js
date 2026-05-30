'use strict'; // lifecycle: test-fixture
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const { build } = require('../../scripts/ops/fotmob_ligue1_corrected_artifacts_canonical_contract_adg42');

const MANIFEST = path.resolve(__dirname, '../../docs/_manifests/fotmob_ligue1_corrected_artifacts_canonical_contract.adg42.json');
function artifact() {
    return JSON.parse(fs.readFileSync(MANIFEST, 'utf8'));
}

test('ADG42 processes 32 corrected candidates without raw readiness', () => {
    const a = build();
    assert.equal(a.total_corrected_candidates, 32);
    assert.equal(a.candidates.length, 32);
    assert.equal(a.raw_write_ready_count, 0);
    assert.ok(a.candidates.every(c => c.classifications.length > 0));
    assert.ok(a.candidates.every(c => c.no_fallback_url_construction === true));
});

test('ADG42 canonical URLs parse route_code and hash_id into route_hash_pair', () => {
    const a = build();
    const valid = a.candidates.filter(c => c.canonical_detail_url);
    assert.equal(valid.length, 5);
    for (const c of valid) {
        assert.ok(c.route_code);
        assert.ok(c.hash_id);
        assert.equal(c.route_hash_pair, `${c.route_code}#${c.hash_id}`);
        assert.equal(c.atomic_handoff_status, 'canonical_url_atomic_identity_valid');
    }
});

test('ADG42 missing canonical URL blocks without guessed URL generation', () => {
    const a = build();
    const missing = a.candidates.filter(c => c.atomic_handoff_status === 'canonical_url_missing');
    assert.equal(missing.length, 27);
    assert.ok(missing.every(c => c.canonical_detail_url === null));
    assert.ok(missing.every(c => c.route_code === null));
    assert.ok(missing.every(c => c.no_fallback_url_construction === true));
});

test('ADG42 historical enriched URL is evidence only and never primary', () => {
    const a = build();
    const historicalOnly = a.candidates.filter(c => c.classifications.includes('historical_url_only'));
    assert.equal(historicalOnly.length, 27);
    assert.ok(a.candidates.every(c => c.historical_enriched_url_role === 'historical_evidence_only'));
    assert.ok(historicalOnly.every(c => c.canonical_url_source === null));
});

test('ADG42 preserves L2 rewrite and route guessing blockers', () => {
    const a = build();
    assert.equal(a.l2_rewrite_blocked_count, 32);
    assert.equal(a.detail_id_as_route_code_blocked_count, 32);
    assert.equal(a.route_code_guessing_blocked_count, 32);
    assert.ok(a.candidates.every(c => c.l2_url_rewrite_allowed === false));
    assert.ok(a.candidates.every(c => c.l2_may_replace_route_code === false));
    assert.ok(a.candidates.every(c => c.l2_may_use_hash_as_route_code === false));
});

test('ADG42 keeps every candidate detail-page verification required', () => {
    const a = artifact();
    assert.equal(a.detail_page_verification_required_count, 32);
    assert.equal(a.raw_write_ready_count, 0);
    assert.ok(a.candidates.every(c => c.detail_page_verification_required === true));
    assert.ok(a.candidates.every(c => c.raw_write_ready === false));
});
