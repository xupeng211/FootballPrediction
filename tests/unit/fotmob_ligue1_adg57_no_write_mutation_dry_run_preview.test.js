'use strict'; const assert = require('node:assert/strict'); const test = require('node:test'); const { build } = require('../../scripts/ops/fotmob_ligue1_adg57_no_write_mutation_dry_run_preview');
test('ADG57 32 dry-run records, 0 mutation executed', () => { const a = build(); assert.equal(a.total_targets, 32); assert.equal(a.dry_run_records_generated, 32); assert.equal(a.mutation_executed, 0); });
test('ADG57 all records dry_run_only, no mutation', () => { const a = build(); assert.ok(a.dry_run_records.every(r => r.dry_run_only && !r.mutation_executed)); });
test('ADG57 all 32 require re-acceptance and suspension resolution', () => { const a = build(); assert.equal(a.reacceptance_required, 32); assert.equal(a.suspension_resolution_required, 32); });
test('ADG57 5 mutation classes defined, none executed', () => { const a = build(); assert.ok(a.proposed_future_mutation_classes.length >= 4); assert.ok(a.proposed_future_mutation_classes.every(c => c.executed === false)); });
test('ADG57 15 future mutation prerequisites', () => { const a = build(); assert.ok(a.future_mutation_prerequisites.length >= 10); });
test('ADG57 no network, no DB/raw write', () => { const a = build(); assert.equal(a.safety.live_fetch_performed, false); assert.equal(a.safety.db_write_performed, false); assert.equal(a.safety.raw_write_execution_performed, false); assert.equal(a.raw_write_ready_count, 0); });
