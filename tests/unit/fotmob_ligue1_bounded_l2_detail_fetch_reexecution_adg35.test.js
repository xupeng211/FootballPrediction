'use strict'; // lifecycle: test-fixture
const assert = require('node:assert/strict'); const fs = require('node:fs'); const path = require('node:path'); const test = require('node:test');
const { buildCorrectedFotmobDetailUrl } = require('../../src/infrastructure/services/FotMobRouteIdentityReconciler');
const RP = path.resolve(__dirname, '../../docs/_manifests/fotmob_ligue1_bounded_l2_detail_fetch_reexecution.adg35.json');
function r() { return JSON.parse(fs.readFileSync(RP, 'utf8')); }

test('ADG35 URL builder now rejects historical route code on slug mismatch', () => {
    const built = buildCorrectedFotmobDetailUrl({ correctedDetailExternalId: '4830473', expectedHomeTeam: 'Paris Saint-Germain', expectedAwayTeam: 'Angers', historicalSourcePageUrl: '/matches/angers-vs-paris-saint-germain/2o4ahb#4830473' });
    assert.equal(built.ok, true);
    assert.equal(built.historical_route_code_reused, false, 'route code 2o4ahb must be rejected due to slug mismatch');
    assert.equal(built.historical_slug_mismatch_detected, true);
    assert.equal(built.route_code_source.includes('fallback'), true);
    assert.ok(built.url.includes('paris-saint-germain-vs-angers'));
    assert.ok(!built.url.includes('/2o4ahb'), 'URL must no longer contain rejected route code 2o4ahb');
});

test('ADG35 URL construction works but detail ID points to reverse leg', () => {
    const a = r(); const s0 = a.fetch_results[0];
    assert.equal(s0.status, 'validation_failed');
    assert.equal(s0.orientation, 'reversed', 'detail page content is reverse even with corrected URL slug');
});

test('ADG35 safety: raw_write_ready=0, no full payload', () => { const a = r(); assert.equal(a.rw, 0); assert.equal(a.full_payload_saved, false); assert.equal(a.no_db_write, true); assert.equal(a.no_browser, true); });
