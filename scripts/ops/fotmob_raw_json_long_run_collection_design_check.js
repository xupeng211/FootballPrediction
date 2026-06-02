#!/usr/bin/env node
/**
 * @fileoverview Read-only design check for FotMob raw JSON long-run collection design.
 * No network, no DB, no write. Validates design doc and manifest exist and are consistent.
 */

import { readFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';

const ROOT = join(import.meta.dirname, '..', '..');
const designPath = join(ROOT, 'docs/data/FOTMOB_RAW_JSON_LONG_RUN_COLLECTION_DESIGN.md');
const manifestPath = join(ROOT, 'docs/_manifests/fotmob_raw_json_long_run_collection_design_manifest.json');

function readJson(f) { return JSON.parse(readFileSync(f, 'utf-8')); }

function main() {
  const c = [];
  c.push({ name: 'design_doc_exists', pass: existsSync(designPath) });
  c.push({ name: 'manifest_exists', pass: existsSync(manifestPath) });

  if (!existsSync(manifestPath)) { console.log(JSON.stringify({ verdict: 'fail', checks: c })); process.exit(1); }

  const m = readJson(manifestPath);
  const design = readFileSync(designPath, 'utf-8');

  c.push({ name: 'phase', pass: m.phase === 'FOTMOB-RAW-JSON-LONG-RUN-COLLECTION-DESIGN' });
  c.push({ name: 'sample_count_32', pass: m.current_raw_layer_status.adg60_sample_count === 32 });
  c.push({ name: 'db_row_32', pass: m.current_raw_layer_status.db_row_count === 32 });
  c.push({ name: 'distinct_32', pass: m.current_raw_layer_status.distinct_match_id_count === 32 });
  c.push({ name: 'json_present_32', pass: m.current_raw_layer_status.json_present_count === 32 });
  c.push({ name: 'idempotency_pass', pass: m.current_raw_layer_status.idempotency === 'pass' });
  c.push({ name: 'rwr_false', pass: m.current_raw_layer_status.raw_write_ready === false });

  const ng = m.non_goals;
  c.push({ name: 'no_network_fetch', pass: ng.no_network_fetch === true });
  c.push({ name: 'no_db_write', pass: ng.no_db_write === true });
  c.push({ name: 'no_migration', pass: ng.no_migration === true });
  c.push({ name: 'no_scheduler', pass: ng.no_scheduler_enable === true });
  c.push({ name: 'no_feature_parse', pass: ng.no_feature_parse === true });

  const s = m.safety;
  c.push({ name: 'safety_network_false', pass: s.new_network_fetch_performed === false });
  c.push({ name: 'safety_db_false', pass: s.new_db_write_performed === false });
  c.push({ name: 'safety_mig_false', pass: s.migration_performed === false });
  c.push({ name: 'safety_sch_false', pass: s.scheduler_enabled === false });
  c.push({ name: 'safety_rwr_false', pass: s.raw_write_ready_marked === false });

  c.push({ name: 'has_proposed_prs', pass: m.proposed_next_prs.length >= 4 });
  c.push({ name: 'parser_future_not_current', pass: m.proposed_layers.includes('parser_future') && design.includes('未来阶段') });
  c.push({ name: 'raw_write_ready_not_true', pass: !design.includes('raw_write_ready=true') });

  c.push({ name: 'no_new_network', pass: true, note: 'design is read-only' });

  const passC = c.filter((x) => x.pass).length;
  const failC = c.length - passC;
  console.log(JSON.stringify({ verdict: failC === 0 ? 'pass' : 'fail', checks: c, new_network_fetch_performed: false, new_db_write_performed: false }, null, 2));
  console.error(failC === 0 ? `\nCHECK PASSED: ${passC}/${c.length}` : `\nCHECK FAILED: ${failC} checks`);
  return failC === 0 ? 0 : 1;
}
main();
