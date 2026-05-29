'use strict'; // lifecycle: test-fixture
const assert = require('node:assert/strict'); const fs = require('node:fs'); const path = require('node:path'); const test = require('node:test');
const { buildCorrectedFotmobDetailUrl } = require('../../src/infrastructure/services/FotMobRouteIdentityReconciler');
const RP = path.resolve(__dirname, '../../docs/_manifests/fotmob_ligue1_bounded_l2_detail_fetch_route_code_reexecution.adg38.json');
function r() { return JSON.parse(fs.readFileSync(RP, 'utf8')); }

test('ADG38 4830473: detail ID as route code → page not found (route code fix insufficient)', () => {
    const a = r(); const s0 = a.fetch_results[0];
    assert.equal(s0.status, 'hydration_identity_missing', 'detail ID as route code fails to resolve match page');
});
test('ADG38 4830487: matching-slug route code → STILL reversed', () => {
    const a = r(); const s1 = a.fetch_results[1];
    assert.equal(s1.status, 'validation_failed');
    assert.equal(s1.orientation, 'reversed', 'even matching-slug historical route code points to reverse leg');
});
test('ADG38 raw_write_ready=0', () => { const a = r(); assert.equal(a.rw, 0); assert.equal(a.no_db_write, true); assert.equal(a.no_browser, true); });
