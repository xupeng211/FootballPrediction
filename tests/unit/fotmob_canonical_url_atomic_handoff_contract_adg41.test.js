'use strict'; // lifecycle: test-fixture
const assert = require('node:assert/strict'); const fs = require('node:fs'); const path = require('node:path'); const test = require('node:test');
const { parseFotmobCanonicalDetailUrl, validateCanonicalUrlAtomicHandoff } = require('../../src/infrastructure/services/FotMobRouteIdentityReconciler');
const RP = path.resolve(__dirname, '../../docs/_manifests/fotmob_canonical_url_atomic_handoff_contract.adg41.json');
function r() { return JSON.parse(fs.readFileSync(RP, 'utf8')); }

test('ADG41 same route code + different hash = different route_hash_pair', () => {
    const a = parseFotmobCanonicalDetailUrl('https://www.fotmob.com/zh-Hans/matches/manchester-city-vs-afc-bournemouth/2feiv3#4813735');
    const b = parseFotmobCanonicalDetailUrl('https://www.fotmob.com/zh-Hans/matches/manchester-city-vs-afc-bournemouth/2feiv3#4813470');
    assert.equal(a.route_code, b.route_code, 'same route code');
    assert.notEqual(a.route_hash_pair, b.route_hash_pair, 'different route_hash_pair');
});

test('ADG41 missing route_code or hash_id returns not ok', () => {
    assert.equal(parseFotmobCanonicalDetailUrl(null).ok, false);
    assert.equal(parseFotmobCanonicalDetailUrl('https://www.fotmob.com/matches/a-vs-b/xxx').ok, false);
});

test('ADG41 L2 URL rewriting blocked', () => {
    const v = validateCanonicalUrlAtomicHandoff({ canonicalDetailUrl: 'https://www.fotmob.com/zh-Hans/matches/angers-vs-paris-saint-germain/2o4ahb#4830473', expectedHome: 'Paris Saint-Germain', expectedAway: 'Angers' });
    assert.equal(v.l2_url_rewrite_allowed, false);
    assert.equal(v.detail_id_as_route_code_allowed, false);
    assert.equal(v.l2_may_replace_route_code, false);
    assert.equal(v.raw_write_ready, false);
});

test('ADG41 canonical URL atomic, slug not home/away authority', () => {
    const v = validateCanonicalUrlAtomicHandoff({ canonicalDetailUrl: 'https://www.fotmob.com/zh-Hans/matches/angers-vs-paris-saint-germain/2o4ahb#4830473', expectedHome: 'Paris Saint-Germain', expectedAway: 'Angers' });
    assert.equal(v.slug_not_home_away_authority, true);
    assert.equal(v.canonical_url_must_be_atomic, true);
});

test('ADG41 raw_write_ready=0', () => { const a = r(); assert.equal(a.raw_write_ready, 0); assert.equal(a.no_network, true); assert.equal(a.no_db_write, true); });
