#!/usr/bin/env node
/* eslint-disable complexity, max-lines, no-promise-executor-return */
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const PHASE = 'Phase 5.21-ADG16';

const ADG15_RESULT_PATH = 'docs/_manifests/fotmob_ligue1_corrected_generation_regression.adg15.json';
const ADG8_RESULT_PATH = 'docs/_manifests/fotmob_identity_mapping_source_inventory_audit_result.adg8.json';
const ADG12_RESULT_PATH = 'docs/_manifests/fotmob_observed_identity_evidence_acquisition_result.adg12.json';
const ENRICHED_PATH = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.enriched_targets.phase521l2v3aa.json';
const ARTIFACT_OUTPUT_PATH = 'docs/_manifests/fotmob_observed_identity_evidence_acquisition_batch_b.adg16.json';
const REPORT_OUTPUT_PATH = 'docs/_reports/FOTMOB_OBSERVED_IDENTITY_EVIDENCE_ACQUISITION_BATCH_B_ADG16.md';
const REQUEST_TIMEOUT_MS = 20000;
const DELAY_MIN = 10000;
const DELAY_MAX = 15000;
const FOTMOB_BASE = 'https://www.fotmob.com';
const BATCH_SIZE = 10;

const { classifyDetailCandidateIdentity, FIXTURE_IDENTITY_GUARD_PASSED, FIXTURE_IDENTITY_GUARD_BLOCKED } =
    require('../../src/infrastructure/services/FotMobRouteIdentityReconciler');
const { extractFromHtml } = require('../../src/parsers/fotmob/NextDataParser');

function abs(p) { return path.isAbsolute(p) ? p : path.join(PROJECT_ROOT, p); }
function readJson(p) { return JSON.parse(fs.readFileSync(abs(p), 'utf8')); }
function writeJson(p, v) { fs.writeFileSync(abs(p), `${JSON.stringify(v, null, 4)}\n`, 'utf8'); }
function writeText(p, v) { fs.writeFileSync(abs(p), v, 'utf8'); }

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

function buildEvidenceMap(adg8, adg12) {
    const m = new Map();
    for (const r of adg8.audit_results || []) {
        if (r.schedule_external_id && r.observed_detail_id)
            {m.set(r.schedule_external_id, { od: r.observed_detail_id, oh: r.observed_home_team, oa: r.observed_away_team, omd: r.observed_match_date, src: 'adg8_reuse' });}
    }
    for (const r of adg12.batch_results || []) {
        if (r.schedule_external_id && r.observed_detail_id)
            {m.set(r.schedule_external_id, { od: r.observed_detail_id, oh: r.observed_home_team, oa: r.observed_away_team, omd: r.observed_match_date, src: 'adg12_reuse' });}
    }
    return m;
}

function getUnknownIds(adg15) {
    return (adg15.regression_results || [])
        .filter(r => r.classification === 'unknown_insufficient_evidence')
        .map(r => r.external_id);
}

function getEnrichedUrlMap() {
    const m = new Map();
    for (const t of readJson(ENRICHED_PATH).enriched_targets || []) {
        if (t.schedule_external_id) m.set(t.schedule_external_id, t);
    }
    return m;
}

async function fetchPage(url) {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), REQUEST_TIMEOUT_MS);
    try {
        const res = await fetch(url, { signal: ctrl.signal, headers: { 'User-Agent': 'Mozilla/5.0 (compatible; FP/4.51)' } });
        clearTimeout(t);
        if (res.status !== 200) return { s: res.status, html: null };
        return { s: 200, html: await res.text() };
    } catch (e) { clearTimeout(t); return { s: 0, html: null, err: e.message }; }
}

async function runBatchB(deps = {}) {
    const adg15 = deps.adg15 || readJson(ADG15_RESULT_PATH);
    const adg8 = deps.adg8 || readJson(ADG8_RESULT_PATH);
    const adg12 = deps.adg12 || readJson(ADG12_RESULT_PATH);
    const evidenceMap = buildEvidenceMap(adg8, adg12);
    const urlMap = getEnrichedUrlMap();
    const unknownIds = getUnknownIds(adg15);

    const targets = unknownIds.slice(0, BATCH_SIZE);
    const results = [];
    let requests = 0, reused = 0;

    for (let i = 0; i < targets.length; i++) {
        const eid = targets[i];
        const enriched = urlMap.get(eid) || {};
        const existing = evidenceMap.get(eid);
        const base = { external_id: eid, expected_home: enriched.schedule_home_team, expected_away: enriched.schedule_away_team,
            expected_date: enriched.schedule_date, match_id: enriched.match_id };

        if (existing) {
            const cls = classifyDetailCandidateIdentity({
                schedule_home_team: base.expected_home, schedule_away_team: base.expected_away,
                schedule_date: base.expected_date, source_home_team: existing.oh, source_away_team: existing.oa,
                source_match_date: existing.omd, detail_external_id_candidate: eid,
            });
            results.push({ ...base, status: 'evidence_reused', evidence_src: existing.src, observed_id: existing.od,
                observed_home: existing.oh, observed_away: existing.oa, guard_classification: cls.detail_identity_candidate_status,
                guard_status: cls.fixture_identity_guard_status, correction: cls.correction_needed, orientation: cls.home_away_orientation,
                delta: cls.date_delta_days, raw_write_ready: false, fetched: false });
            reused++;
            continue;
        }

        const pagePath = enriched.source_page_url || `/matches/unknown#${eid}`;
        const url = pagePath.startsWith('http') ? pagePath : `${FOTMOB_BASE}${pagePath}`;
        const { s, html } = await fetchPage(url);
        requests++;

        if (s !== 200 || !html) {
            results.push({ ...base, status: s === 0 ? 'network_unavailable' : `http_${s}`, guard_classification: 'insufficient_safe_evidence',
                guard_status: FIXTURE_IDENTITY_GUARD_BLOCKED, raw_write_ready: false, fetched: true, html_len: 0 });
            continue;
        }

        const parsed = extractFromHtml(html);
        const pp = parsed?.data?.props?.pageProps;
        const g = pp?.general || {};
        const oh = g.homeTeam?.name || null;
        const oa = g.awayTeam?.name || null;
        const od = String(g.matchId || pp?.matchId || '');
        const omd = g.matchTimeUTC || null;

        if (!oh || !oa) {
            results.push({ ...base, status: 'hydration_present_identity_missing', observed_id: od,
                guard_classification: 'insufficient_safe_evidence', guard_status: FIXTURE_IDENTITY_GUARD_BLOCKED,
                raw_write_ready: false, fetched: true, html_len: html.length });
        } else {
            const cls = classifyDetailCandidateIdentity({
                schedule_home_team: base.expected_home, schedule_away_team: base.expected_away,
                schedule_date: base.expected_date, source_home_team: oh, source_away_team: oa,
                source_match_date: omd, detail_external_id_candidate: eid,
            });
            results.push({ ...base, status: 'observed_identity_acquired', evidence_src: 'batch_b_acquisition',
                observed_id: od, observed_home: oh, observed_away: oa,
                guard_classification: cls.detail_identity_candidate_status, guard_status: cls.fixture_identity_guard_status,
                correction: cls.correction_needed, orientation: cls.home_away_orientation, delta: cls.date_delta_days,
                raw_write_ready: false, fetched: true, html_len: html.length });
        }

        if (i < targets.length - 1) {
            const d = Math.floor(Math.random() * (DELAY_MAX - DELAY_MIN + 1) + DELAY_MIN);
            process.stdout.write(`  [delay ${d}ms after ${eid}]\n`);
            await sleep(d);
        }
    }
    return { results, requests, reused, targets };
}

function cnt(l, p) { return l.filter(p).length; }

function buildArtifact(deps = {}) {
    const g = deps.generatedAt || new Date().toISOString();
    const { results, requests, reused, targets } = deps.runResult || { results: [], requests: 0, reused: 0 };

    const s = {
        selected_unknown_target_count: targets.length,
        request_attempt_count: requests,
        evidence_reuse_count: reused,
        observed_identity_acquired_count: cnt(results, r => r.status === 'observed_identity_acquired'),
        observed_identity_missing_count: cnt(results, r => r.status.includes('missing') || r.status.includes('insufficient')),
        strict_guard_passed_no_write_count: cnt(results, r => r.guard_status === FIXTURE_IDENTITY_GUARD_PASSED),
        strict_guard_blocked_count: cnt(results, r => r.guard_status === FIXTURE_IDENTITY_GUARD_BLOCKED),
        reverse_fixture_mapping_error_count: cnt(results, r => r.guard_classification === 'rejected_reverse_fixture_mapping'),
        home_away_inversion_count: cnt(results, r => r.guard_classification === 'rejected_home_away_inversion'),
        date_mismatch_count: cnt(results, r => r.correction && r.delta && r.delta > 1),
        anti_bot_or_access_block_count: cnt(results, r => r.status.includes('http_')),
        network_unavailable_count: cnt(results, r => r.status === 'network_unavailable'),
        insufficient_safe_evidence_count: cnt(results, r => r.guard_classification === 'insufficient_safe_evidence'),
        raw_write_ready_count: 0,
        re_acceptance_candidate_count: 0,
    };

    return {
        schema_version: 'fotmob_observed_identity_evidence_acquisition_batch_b_adg16_v1',
        phase: PHASE, generated_at: g, adg16_execution_status: 'completed_batch_b_acquisition',
        evidence_acquisition_performed: true, batch_id: 'ADG16_BATCH_B',
        no_browser: true, no_db_write: true, no_raw_write: true, no_re_acceptance: true,
        no_mutation: true, full_body_saved: false, full_payload_saved: false,
        ...s, recommended_next_step: s.reverse_fixture_mapping_error_count > 2
            ? 'systematic_inversion_confirmed; source_inventory_correction_planning; do not raw write'
            : s.observed_identity_acquired_count > 3
                ? 'evidence_acquisition_working; consider_remaining_batches_or_acceptance_review; do not raw write'
                : 'insufficient_evidence; evidence_strategy_review; do not raw write',
        batch_results: results,
    };
}

function buildReport(a) {
    const l = ['# FotMob Batch B Evidence Acquisition ADG16', '',
        `- Phase: ${a.phase}`, `- Batch: ${a.batch_id}`, '', '## Results',
        '| ext_id | status | obs_home vs obs_away | guard | correction | delta |',
        '| --- | --- | --- | --- | --- | --- |'];
    for (const r of a.batch_results || [])
        {l.push(`| ${r.external_id} | ${r.status} | ${r.observed_home || '?'} vs ${r.observed_away || '?'} | ${r.guard_classification} | ${r.correction || false} | ${r.delta ?? 'null'} |`);}
    l.push('', '## Counts', '',
        `| acquired | ${a.observed_identity_acquired_count} |`, `| reused | ${a.evidence_reuse_count} |`,
        `| passed | ${a.strict_guard_passed_no_write_count} |`, `| blocked | ${a.strict_guard_blocked_count} |`,
        `| reverse_error | ${a.reverse_fixture_mapping_error_count} |`, `| raw_write_ready | ${a.raw_write_ready_count} |`,
        '', '## Safety', '- no browser / no DB write / no raw write / no full HTML saved',
        '', `## Next Step`, '', a.recommended_next_step);
    return `${l.join('\n')}\n`;
}

async function main() {
    process.stdout.write(`ADG16 Batch B: ${BATCH_SIZE} targets\n`);
    const deps = {};
    deps.runResult = await runBatchB(deps);
    const a = buildArtifact(deps);
    writeJson(ARTIFACT_OUTPUT_PATH, a);
    writeText(REPORT_OUTPUT_PATH, buildReport(a));
    process.stdout.write(JSON.stringify({ acquired: a.observed_identity_acquired_count, reused: a.evidence_reuse_count,
        passed: a.strict_guard_passed_no_write_count, blocked: a.strict_guard_blocked_count,
        reverse: a.reverse_fixture_mapping_error_count }, null, 2) + '\n');
    return { status: 0 };
}

module.exports = { PHASE, runBatchB, buildArtifact, buildReport, main };
if (require.main === module) { main().then(r => process.exitCode = r.status).catch(e => { process.stderr.write(e.stack + '\n'); process.exitCode = 1; }); }
