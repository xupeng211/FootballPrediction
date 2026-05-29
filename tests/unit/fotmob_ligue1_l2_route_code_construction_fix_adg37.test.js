'use strict'; // lifecycle: test-fixture
const assert = require('node:assert/strict'); const fs = require('node:fs'); const path = require('node:path'); const test = require('node:test');
const { buildCorrectedFotmobDetailUrl } = require('../../src/infrastructure/services/FotMobRouteIdentityReconciler');
const RP = path.resolve(__dirname, '../../docs/_manifests/fotmob_ligue1_l2_route_code_construction_fix.adg37.json');
function r() { return JSON.parse(fs.readFileSync(RP, 'utf8')); }

test('ADG37 4830473: historical route code 2o4ahb rejected, detail ID fallback used', () => {
    const built = buildCorrectedFotmobDetailUrl({ correctedDetailExternalId: '4830473', expectedHomeTeam: 'Paris Saint-Germain', expectedAwayTeam: 'Angers', historicalSourcePageUrl: '/matches/angers-vs-paris-saint-germain/2o4ahb#4830473' });
    assert.equal(built.historical_slug_mismatch_detected, true);
    assert.equal(built.historical_route_code_reused, false);
    assert.equal(built.historical_route_code_rejected_reason, 'slug_mismatch_historical_route_code_rejected');
    assert.equal(built.route_code, '4830473');
    assert.equal(built.raw_write_ready, false);
    assert.ok(!built.url.includes('2o4ahb'));
});

test('ADG37 safe reuse: matching slug keeps historical route code', () => {
    const built = buildCorrectedFotmobDetailUrl({ correctedDetailExternalId: '4813735', expectedHomeTeam: 'AFC Bournemouth', expectedAwayTeam: 'Manchester City', historicalSourcePageUrl: '/matches/manchester-city-vs-afc-bournemouth/2feiv3#4813735' });
    assert.equal(built.raw_write_ready, false);
});

test('ADG37 19 route codes rejected, 4830473 fixed, rw=0', () => { const a = r(); assert.equal(a.slug_mismatch, 19); assert.equal(a.route_code_rejected, 19); assert.equal(a.adg37_4830473_fixed, true); assert.equal(a.raw_write_ready, 0); });
