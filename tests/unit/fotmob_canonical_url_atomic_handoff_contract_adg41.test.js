'use strict'; // lifecycle: test-fixture
const assert = require('node:assert/strict'); const fs = require('node:fs'); const path = require('node:path'); const test = require('node:test');
const { parseFotmobCanonicalDetailUrl, validateCanonicalUrlAtomicHandoff } = require('../../src/infrastructure/services/FotMobRouteIdentityReconciler');
const RP = path.resolve(__dirname, '../../docs/_manifests/fotmob_canonical_url_atomic_handoff_contract.adg41.json');
const MAN_CITY_BOURNEMOUTH_URL = 'https://www.fotmob.com/zh-Hans/matches/manchester-city-vs-afc-bournemouth/2feiv3#4813735';
const MAN_CITY_BOURNEMOUTH_ALT_HASH_URL = 'https://www.fotmob.com/zh-Hans/matches/manchester-city-vs-afc-bournemouth/2feiv3#4813470';
function r() { return JSON.parse(fs.readFileSync(RP, 'utf8')); }

test('ADG41 parser exposes canonical URL atomic identity compatibility fields', () => {
    const parsed = parseFotmobCanonicalDetailUrl(MAN_CITY_BOURNEMOUTH_URL);
    assert.equal(parsed.ok, true);
    assert.equal(parsed.locale, 'zh-Hans');
    assert.equal(parsed.slug, 'manchester-city-vs-afc-bournemouth');
    assert.equal(parsed.route_code, '2feiv3');
    assert.equal(parsed.routeCode, '2feiv3');
    assert.equal(parsed.hash_id, '4813735');
    assert.equal(parsed.hashId, '4813735');
    assert.equal(parsed.route_hash_pair, '2feiv3#4813735');
    assert.equal(parsed.routeHashPair, '2feiv3#4813735');
    assert.equal(parsed.canonical_detail_url, MAN_CITY_BOURNEMOUTH_URL);
    assert.equal(parsed.canonicalDetailUrl, MAN_CITY_BOURNEMOUTH_URL);
    assert.equal(parsed.raw_write_ready, false);
});

test('ADG41 same route code + different hash = different route_hash_pair', () => {
    const a = parseFotmobCanonicalDetailUrl(MAN_CITY_BOURNEMOUTH_URL);
    const b = parseFotmobCanonicalDetailUrl(MAN_CITY_BOURNEMOUTH_ALT_HASH_URL);
    assert.equal(a.route_code, b.route_code, 'same route code');
    assert.notEqual(a.hash_id, b.hash_id, 'different hash id');
    assert.notEqual(a.route_hash_pair, b.route_hash_pair, 'different route_hash_pair');
});

test('ADG41 missing route_code or hash_id returns not ok', () => {
    assert.equal(parseFotmobCanonicalDetailUrl(null).ok, false);
    const noHash = parseFotmobCanonicalDetailUrl('https://www.fotmob.com/matches/a-vs-b/xxx');
    assert.equal(noHash.ok, false);
    assert.equal(noHash.reason, 'missing_hash_id');
    assert.equal(noHash.raw_write_ready, false);
});

test('ADG41 missing canonical URL blocks without fallback construction', () => {
    const v = validateCanonicalUrlAtomicHandoff({ home: 'AFC Bournemouth', away: 'Manchester City' });
    assert.equal(v.ok, false);
    assert.equal(v.reason, 'missing_canonical_detail_url');
    assert.equal(v.canonical_detail_url, null);
    assert.equal(v.detail_id_as_route_code_allowed, false);
    assert.equal(v.route_code_must_not_be_guessed, true);
    assert.equal(v.raw_write_ready, false);
});

test('ADG41 L2 URL rewriting blocked', () => {
    const v = validateCanonicalUrlAtomicHandoff({ canonicalDetailUrl: 'https://www.fotmob.com/zh-Hans/matches/angers-vs-paris-saint-germain/2o4ahb#4830473', expectedHome: 'Paris Saint-Germain', expectedAway: 'Angers' });
    assert.equal(v.l2_url_rewrite_allowed, false);
    assert.equal(v.detail_id_as_route_code_allowed, false);
    assert.equal(v.l2_may_replace_route_code, false);
    assert.equal(v.raw_write_ready, false);
});

test('ADG41 validator accepts required url/home/away contract shape', () => {
    const v = validateCanonicalUrlAtomicHandoff({
        url: MAN_CITY_BOURNEMOUTH_URL,
        home: 'AFC Bournemouth',
        away: 'Manchester City',
    });
    assert.equal(v.ok, true);
    assert.equal(v.route_code, '2feiv3');
    assert.equal(v.hash_id, '4813735');
    assert.equal(v.route_hash_pair, '2feiv3#4813735');
    assert.equal(v.canonical_detail_url, MAN_CITY_BOURNEMOUTH_URL);
    assert.equal(v.locale, 'zh-Hans');
    assert.equal(v.l2_url_rewrite_allowed, false);
    assert.equal(v.detail_id_as_route_code_allowed, false);
    assert.equal(v.route_code_must_not_be_guessed, true);
    assert.equal(v.raw_write_ready, false);
});

test('ADG41 validator keeps legacy canonicalDetailUrl/expectedHome/expectedAway shape', () => {
    const v = validateCanonicalUrlAtomicHandoff({
        canonicalDetailUrl: MAN_CITY_BOURNEMOUTH_URL,
        expectedHome: 'AFC Bournemouth',
        expectedAway: 'Manchester City',
    });
    assert.equal(v.ok, true);
    assert.equal(v.route_code, '2feiv3');
    assert.equal(v.hash_id, '4813735');
    assert.equal(v.route_hash_pair, '2feiv3#4813735');
    assert.equal(v.l2_may_replace_route_code, false);
    assert.equal(v.l2_may_replace_hash_id, false);
    assert.equal(v.raw_write_ready, false);
});

test('ADG41 canonical URL atomic, slug not home/away authority', () => {
    const v = validateCanonicalUrlAtomicHandoff({ canonicalDetailUrl: 'https://www.fotmob.com/zh-Hans/matches/angers-vs-paris-saint-germain/2o4ahb#4830473', expectedHome: 'Paris Saint-Germain', expectedAway: 'Angers' });
    assert.equal(v.slug_not_home_away_authority, true);
    assert.equal(v.canonical_url_must_be_atomic, true);
});

test('ADG41 raw_write_ready=0', () => { const a = r(); assert.equal(a.raw_write_ready, 0); assert.equal(a.no_network, true); assert.equal(a.no_db_write, true); });
