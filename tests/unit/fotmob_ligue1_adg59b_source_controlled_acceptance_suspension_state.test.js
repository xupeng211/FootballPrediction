'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const { build } = require('../../scripts/ops/fotmob_ligue1_adg59b_source_controlled_acceptance_suspension_state');

const MANIFEST = path.resolve(
    __dirname,
    '../../docs/_manifests/fotmob_ligue1_adg59b_source_controlled_acceptance_suspension_state.json'
);

test('ADG59B build accepts and resolves exactly 32 source-controlled targets', () => {
    const artifact = build();
    assert.equal(artifact.target_count, 32);
    assert.equal(artifact.accepted_count, 32);
    assert.equal(artifact.suspension_resolved_count, 32);
    assert.equal(artifact.duplicate_conflict, 0);
});

test('ADG59B preserves orientation, date and competition guards', () => {
    const artifact = build();
    assert.equal(artifact.orientation_pass, 32);
    assert.equal(artifact.date_pass, 32);
    assert.equal(artifact.competition_pass, 32);
});

test('ADG59B is artifact-only and blocks DB/raw/ADG60 surfaces', () => {
    const artifact = build();
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_write_performed, false);
    assert.equal(artifact.raw_match_data_insert_performed, false);
    assert.equal(artifact.raw_write_ready_count, 0);
    assert.equal(artifact.safety.matches_table_modified, false);
    assert.equal(artifact.safety.pipeline_status_modified, false);
    assert.equal(artifact.safety.schema_migration_performed, false);
    assert.equal(artifact.safety.adg60_performed, false);
});

test('ADG59B written artifacts carry source-controlled state only', () => {
    const manifest = JSON.parse(fs.readFileSync(MANIFEST, 'utf8'));
    assert.equal(manifest.lifecycle, 'source-controlled-artifact');
    assert.equal(manifest.state_targets.length, 32);
    assert.ok(manifest.state_targets.every(target => target.accepted === true && target.suspension_resolved === true));
    assert.ok(manifest.state_targets.every(target => target.db_write_performed === false && target.raw_write_ready === false));
});
