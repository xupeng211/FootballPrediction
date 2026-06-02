#!/usr/bin/env node
/**
 * @fileoverview __NEXT_DATA__/pageProps extraction smoke from gitignored raw payloads.
 *
 * lifecycle: phase-artifact
 * phase: ADG60-RAW-PAYLOAD-STORAGE-FOUNDATION-AND-CAPTURE-NO-DB
 *
 * Reads the capture manifest, opens each gitignored raw payload file,
 * extracts __NEXT_DATA__ JSON, locates pageProps structure, emits
 * structural summary only — never saves full JSON body.
 *
 * No DB write, no raw_match_data insert, no ADG60 write.
 */

import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';

const DEFAULT_MANIFEST_IN = 'docs/_manifests/fotmob_raw_payload_capture_adg60_manifest.json';
const DEFAULT_MANIFEST_OUT = 'docs/_manifests/fotmob_raw_payload_extract_smoke_adg60_manifest.json';

function parseStrArg(args, flag) {
  const eq = args.findIndex((a) => a.startsWith(`${flag}=`));
  if (eq >= 0) return args[eq].split('=')[1];
  const fi = args.indexOf(flag);
  return fi >= 0 && fi + 1 < args.length ? args[fi + 1] : null;
}

/**
 * Find and parse the __NEXT_DATA__ JSON block within the HTML.
 */
function findAndParseNextData(html) {
  const idx = html.indexOf('__NEXT_DATA__');
  if (idx === -1) return null;
  const scriptStart = html.indexOf('>', idx);
  const scriptEnd = html.indexOf('</script>', idx);
  if (scriptStart === -1 || scriptEnd === -1) return null;
  const jsonText = html.substring(scriptStart + 1, scriptEnd).trim();
  if (!jsonText) return null;
  try { return JSON.parse(jsonText); } catch { return null; }
}

/**
 * Locate pageProps within the parsed __NEXT_DATA__ object.
 */
function findPageProps(parsed) {
  if (parsed.props && parsed.props.pageProps) return { found: true, keys: Object.keys(parsed.props.pageProps) };
  if (parsed.pageProps) return { found: true, keys: Object.keys(parsed.pageProps) };
  return { found: false, keys: [] };
}

/**
 * Extract __NEXT_DATA__ JSON from HTML body without saving full JSON.
 * Returns structural summary only.
 */
function extractNextData(html) {
  const result = {
    next_data_found: false, next_data_parse_ok: false, page_props_found: false,
    top_level_keys: [], page_props_top_level_keys: [],
    candidate_match_detail_key_paths: [], body_saved: false,
  };

  const parsed = findAndParseNextData(html);
  if (!parsed) { result.next_data_found = !!html.includes('__NEXT_DATA__'); return result; }
  result.next_data_found = true;
  result.next_data_parse_ok = true;
  result.top_level_keys = Object.keys(parsed);

  const pp = findPageProps(parsed);
  result.page_props_found = pp.found;
  result.page_props_top_level_keys = pp.keys;

  // Find candidate match detail paths
  for (const p of ['props.pageProps', 'pageProps']) {
    const parts = p.split('.');
    let obj = parsed; let found = true;
    for (const part of parts) {
      if (obj && typeof obj === 'object' && part in obj) { obj = obj[part]; }
      else { found = false; break; }
    }
    if (found && obj && typeof obj === 'object') result.candidate_match_detail_key_paths.push(p);
  }

  return result;
}

function main() {
  const args = process.argv.slice(2);
  const inManifestPath = parseStrArg(args, '--input-manifest') || DEFAULT_MANIFEST_IN;
  const outManifestPath = parseStrArg(args, '--output-manifest') || DEFAULT_MANIFEST_OUT;

  if (!existsSync(inManifestPath)) {
    console.error(`ERROR: input manifest not found: ${inManifestPath}`);
    process.exit(1);
  }

  const captureManifest = JSON.parse(readFileSync(inManifestPath, 'utf-8'));

  const results = [];
  let nextDataFound = 0;
  let nextDataParseOk = 0;
  let pagePropsFound = 0;

  for (const entry of captureManifest.per_target_results) {
    if (!entry.file_saved || !entry.raw_payload_relative_path) {
      results.push({
        target_index: entry.target_index,
        target_match_id: entry.target_match_id,
        extraction_status: 'skipped_no_file',
        next_data_found: false,
        page_props_found: false,
      });
      continue;
    }

    const payloadPath = entry.raw_payload_relative_path;
    let extraction;

    if (!existsSync(payloadPath)) {
      extraction = {
        target_index: entry.target_index,
        target_match_id: entry.target_match_id,
        extraction_status: 'file_missing',
        next_data_found: false,
        page_props_found: false,
      };
    } else {
      const html = readFileSync(payloadPath, 'utf-8');
      const nd = extractNextData(html);

      extraction = {
        target_index: entry.target_index,
        target_match_id: entry.target_match_id,
        expected_home: entry.expected_home,
        expected_away: entry.expected_away,
        extraction_status: nd.next_data_parse_ok ? 'ok' : (nd.next_data_found ? 'parse_failed' : 'no_next_data'),
        next_data_found: nd.next_data_found,
        next_data_parse_ok: nd.next_data_parse_ok,
        page_props_found: nd.page_props_found,
        top_level_keys: nd.top_level_keys,
        page_props_top_level_keys: nd.page_props_top_level_keys,
        candidate_match_detail_key_paths: nd.candidate_match_detail_key_paths,
        body_saved: false,
        db_write: false,
        raw_match_data_insert: false,
      };

      if (nd.next_data_found) nextDataFound++;
      if (nd.next_data_parse_ok) nextDataParseOk++;
      if (nd.page_props_found) pagePropsFound++;
    }

    results.push(extraction);
  }

  const manifest = {
    schema_version: 'adg60_raw_payload_extract_smoke_no_db_v1',
    phase: 'ADG60-RAW-PAYLOAD-STORAGE-FOUNDATION-AND-CAPTURE-NO-DB',
    generated_at: new Date().toISOString(),
    source_manifest: inManifestPath,
    aggregate: {
      total_entries: results.length,
      next_data_found: nextDataFound,
      next_data_parse_ok: nextDataParseOk,
      page_props_found: pagePropsFound,
      extraction_ok: results.filter((r) => r.extraction_status === 'ok').length,
    },
    per_target_results: results,
    safety: {
      body_saved: false,
      full_json_committed: false,
      page_props_committed: false,
      db_write: false,
      raw_match_data_insert: false,
      adg60_write: false,
      raw_write_ready_marked: false,
    },
  };

  writeFileSync(outManifestPath, JSON.stringify(manifest, null, 2));

  console.log(JSON.stringify(manifest, null, 2));
  console.error(`\n=== Extract Smoke Summary ===`);
  console.error(`Entries: ${results.length}`);
  console.error(`__NEXT_DATA__ found: ${nextDataFound}`);
  console.error(`JSON parse OK: ${nextDataParseOk}`);
  console.error(`pageProps found: ${pagePropsFound}`);
  console.error(`Body saved: false | DB write: false`);

  return 0;
}

main();
