'use strict'; // lifecycle: test-fixture
const assert = require('node:assert/strict'); const fs = require('node:fs'); const path = require('node:path'); const test = require('node:test');
const { buildCorrectedFotmobDetailUrl } = require('../../src/infrastructure/services/FotMobRouteIdentityReconciler');
const RP = path.resolve(__dirname, '../../docs/_manifests/fotmob_ligue1_detail_id_assignment_investigation.adg36.json');
function r() { return JSON.parse(fs.readFileSync(RP, 'utf8')); }

test('ADG36 root cause fix verified: route code 2o4ahb from wrong-leg URL is now rejected', () => {
    const built = buildCorrectedFotmobDetailUrl({ correctedDetailExternalId: '4830473', expectedHomeTeam: 'Paris Saint-Germain', expectedAwayTeam: 'Angers', historicalSourcePageUrl: '/matches/angers-vs-paris-saint-germain/2o4ahb#4830473' });
    assert.equal(built.historical_route_code_reused, false, 'route code 2o4ahb must be rejected');
    assert.equal(built.historical_slug_mismatch_detected, true);
    assert.equal(built.historical_enriched_url_used, false);
});
test('ADG36 investigation confirms route code controls page content', () => {
    const a = r();
    assert.equal(a.finding.root_cause.includes('route code'), true);
    assert.equal(a.finding.mechanism.includes('route code path segment'), true);
});
test('ADG36 safety: raw_write_ready=0', () => { const a = r(); assert.equal(a.raw_write_ready, 0); assert.equal(a.no_network, true); assert.equal(a.no_db_write, true); });
