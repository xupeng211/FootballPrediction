'use strict'; // lifecycle: test-fixture
const assert = require('node:assert/strict'); const fs = require('node:fs'); const path = require('node:path'); const test = require('node:test');
const RP = path.resolve(__dirname, '../../docs/_manifests/fotmob_canonical_url_identity_model.adg40.json');
function r() { return JSON.parse(fs.readFileSync(RP, 'utf8')); }

test('ADG40 route_code not unique fixture identity', () => { assert.equal(r().route_code_not_unique, true); });
test('ADG40 hash_id is fixture selector within route', () => { assert.equal(r().hash_id_fixture_selector, true); });
test('ADG40 slug not authoritative for home/away', () => { assert.equal(r().slug_not_authoritative, true); });
test('ADG40 route_hash_pair required', () => { assert.equal(r().route_hash_pair_required, true); });
test('ADG40 L2 URL rewriting blocked', () => { assert.equal(r().l2_url_rewriting_blocked, true); assert.equal(r().detail_id_as_route_code_blocked, true); });
test('ADG40 existing builder requires change', () => { assert.equal(r().existing_builder_requires_change, true); });
test('ADG40 L2 prohibitions defined', () => { assert.ok(r().l2_prohibitions.length >= 3); });
test('ADG40 raw_write_ready=0', () => { assert.equal(r().raw_write_ready, 0); assert.equal(r().no_network, true); assert.equal(r().no_db_write, true); });
