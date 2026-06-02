/**
 * @fileoverview Tests for FotMob raw JSON long-run collection design.
 */

import { describe, it } from 'node:test';
import assert from 'node:assert';
import { readFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';

const ROOT = join(import.meta.dirname, '..', '..');
const designPath = join(ROOT, 'docs/data/FOTMOB_RAW_JSON_LONG_RUN_COLLECTION_DESIGN.md');
const manifest = JSON.parse(readFileSync(join(ROOT, 'docs/_manifests/fotmob_raw_json_long_run_collection_design_manifest.json'), 'utf-8'));
const design = existsSync(designPath) ? readFileSync(designPath, 'utf-8') : '';

describe('design phase and foundational PRs', () => {
  it('phase and reviewed PRs', () => {
    assert.equal(manifest.phase, 'FOTMOB-RAW-JSON-LONG-RUN-COLLECTION-DESIGN');
    assert.ok(manifest.reviewed_foundation_prs.includes(1420));
    assert.ok(manifest.reviewed_foundation_prs.includes(1421));
  });
});

describe('current raw layer status', () => {
  it('32 sample, 32 rows, 32 distinct, 32 json, idempotency pass', () => {
    const s = manifest.current_raw_layer_status;
    assert.equal(s.adg60_sample_count, 32);
    assert.equal(s.db_row_count, 32);
    assert.equal(s.distinct_match_id_count, 32);
    assert.equal(s.json_present_count, 32);
    assert.equal(s.idempotency, 'pass');
    assert.equal(s.raw_write_ready, false);
  });
});

describe('non-goals all confirmed', () => {
  it('no network, DB write, migration, scheduler, feature parse', () => {
    const ng = manifest.non_goals;
    assert.equal(ng.no_network_fetch, true);
    assert.equal(ng.no_db_write, true);
    assert.equal(ng.no_migration, true);
    assert.equal(ng.no_scheduler_enable, true);
    assert.equal(ng.no_feature_parse, true);
    assert.equal(ng.no_raw_match_data_insert, true);
    assert.equal(ng.no_raw_write_ready_marking, true);
  });
});

describe('safety flags all false', () => {
  it('no new network, DB write, migration, scheduler, rwr', () => {
    const s = manifest.safety;
    assert.equal(s.new_network_fetch_performed, false);
    assert.equal(s.new_db_write_performed, false);
    assert.equal(s.migration_performed, false);
    assert.equal(s.scheduler_enabled, false);
    assert.equal(s.feature_parse_performed, false);
    assert.equal(s.raw_write_ready_marked, false);
  });
});

describe('proposed roadmap exists', () => {
  it('target registry, dry-run, one-day, review, parser disco', () => {
    assert.ok(manifest.proposed_next_prs.length >= 4);
    assert.ok(manifest.proposed_next_prs.some((p) => p.includes('TARGET-REGISTRY')));
    assert.ok(manifest.proposed_next_prs.some((p) => p.includes('DRY-RUN')));
    assert.ok(manifest.proposed_next_prs.some((p) => p.includes('ONE-DAY')));
  });
});

describe('design doc covers key chapters', () => {
  it('target registry, raw fetch, scheduler, failure handling, roadmap', () => {
    assert.ok(design.includes('Target Registry'));
    assert.ok(design.includes('Raw Fetch'));
    assert.ok(design.includes('Scheduler'));
    assert.ok(design.includes('失败处理'));
    assert.ok(design.includes('路线图'));
    assert.ok(design.includes('未来阶段'));
  });
});

describe('parser and feature layer are future', () => {
  it('not in scope of this design PR execution', () => {
    assert.ok(manifest.proposed_layers.includes('parser_future'));
    assert.ok(manifest.proposed_layers.includes('feature_future'));
    assert.ok(design.includes('不属于当前阶段'));
  });
});
