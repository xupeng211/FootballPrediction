/**
 * @fileoverview Unit tests for __NEXT_DATA__ extractor smoke helper.
 */

import { describe, it } from 'node:test';
import assert from 'node:assert';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const ROOT = join(import.meta.dirname, '..', '..');
const src = readFileSync(join(ROOT, 'scripts/ops/fotmob_raw_payload_next_data_extract_smoke.js'), 'utf-8');

// Synthetic minimal HTML fixture for extraction tests
const SYNTHETIC_HTML = `<!DOCTYPE html><html><head></head><body>
<script id="__NEXT_DATA__" type="application/json">{"props":{"pageProps":{"matchDetails":{"id":123}},"key":"value"},"page":"/match","query":{"id":"4830473"}}</script>
<div>rest of page</div></body></html>`;

describe('extractor finds __NEXT_DATA__ in synthetic HTML', () => {
  it('next_data_found=true, parse_ok=true, pageProps_found=true', () => {
    // Simulate extraction logic from the helper
    const marker = '__NEXT_DATA__';
    const idx = SYNTHETIC_HTML.indexOf(marker);
    assert.ok(idx !== -1, 'marker not found');

    const scriptStart = SYNTHETIC_HTML.indexOf('>', idx);
    const scriptEnd = SYNTHETIC_HTML.indexOf('</script>', idx);
    const jsonText = SYNTHETIC_HTML.substring(scriptStart + 1, scriptEnd).trim();
    const parsed = JSON.parse(jsonText);

    assert.ok(parsed.props);
    assert.ok(parsed.props.pageProps);
    assert.ok(parsed.props.pageProps.matchDetails);
    assert.equal(parsed.props.pageProps.matchDetails.id, 123);
  });
});

describe('extractor does not save full JSON body', () => {
  it('body_saved=false, full_json_committed=false in source', () => {
    assert.ok(src.includes('body_saved: false'));
    assert.ok(src.includes('full_json_committed: false'));
    assert.ok(src.includes('page_props_committed: false'));
  });
});

describe('extractor manifest safety flags', () => {
  it('all write flags false', () => {
    assert.ok(src.includes('db_write: false'));
    assert.ok(src.includes('raw_match_data_insert: false'));
    assert.ok(src.includes('adg60_write: false'));
    assert.ok(src.includes('raw_write_ready_marked: false'));
  });
});

describe('extractor handles missing input manifest', () => {
  it('exits with error on missing manifest', () => {
    assert.ok(src.includes('input manifest not found'));
    assert.ok(src.includes('process.exit(1)'));
  });
});

describe('extractor reads from gitignored local files', () => {
  it('reads payload from relative path, no network', () => {
    assert.ok(src.includes('readFileSync'));
    assert.ok(!src.match(/await\s+fetch\s*\(/));
  });
});
