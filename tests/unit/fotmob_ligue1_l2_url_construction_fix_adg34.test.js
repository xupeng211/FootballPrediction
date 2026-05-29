'use strict'; // lifecycle: test-fixture
const assert = require('node:assert/strict'); const fs = require('node:fs'); const path = require('node:path'); const test = require('node:test');
const { buildCorrectedFotmobDetailUrl } = require('../../src/infrastructure/services/FotMobRouteIdentityReconciler');
const RP = path.resolve(__dirname, '../../docs/_manifests/fotmob_ligue1_l2_url_construction_fix.adg34.json');
function r() { return JSON.parse(fs.readFileSync(RP, 'utf8')); }

test('ADG34 4830473 regression: built URL does not reuse Angers-first slug', () => {
    const built = buildCorrectedFotmobDetailUrl({ correctedDetailExternalId: '4830473', expectedHomeTeam: 'Paris Saint-Germain', expectedAwayTeam: 'Angers' });
    assert.equal(built.ok, true);
    assert.equal(built.historical_enriched_url_used, false);
    assert.ok(built.slug.startsWith('paris-saint-germain'), `slug should start with PSG: ${built.slug}`);
    assert.equal(built.raw_write_ready, false);
});

test('ADG34 missing fields returns blocked', () => {
    const r = buildCorrectedFotmobDetailUrl({ correctedDetailExternalId: null, expectedHomeTeam: 'A', expectedAwayTeam: 'B' });
    assert.equal(r.ok, false);
    assert.equal(r.reason, 'missing_required_identity_fields');
});

test('ADG34 32/32 URLs constructed, 4830473 fixed', () => { const a = r(); assert.equal(a.constructed, 32); assert.equal(a.adg32_4830473_fixed, true); assert.equal(a.slug_mismatch_detected > 0, true); });
test('ADG34 raw_write_ready=0 and safety', () => { const a = r(); assert.equal(a.raw_write_ready, 0); assert.equal(a.no_network, true); assert.equal(a.no_db_write, true); assert.equal(a.no_raw_write, true); assert.equal(a.full_payload_saved, false); });
