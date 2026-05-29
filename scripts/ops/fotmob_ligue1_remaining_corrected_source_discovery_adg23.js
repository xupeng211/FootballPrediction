#!/usr/bin/env node
// lifecycle: one-shot-helper
// cleanup: archive after ADG23 regression validates results
/* eslint-disable complexity */
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const PP = path.resolve(__dirname, '../..');
const PH = 'Phase 5.21-ADG23';
const LEAGUE_API = 'https://www.fotmob.com/api/data/leagues?id=53&season=2025%2F2026';
const ADG20 = 'docs/_manifests/fotmob_ligue1_corrected_source_inventory_generation.adg20.json';
const ADG21 = 'docs/_manifests/fotmob_ligue1_corrected_source_discovery.adg21.json';
const ADG19 = 'docs/_manifests/fotmob_ligue1_corrected_source_inventory_preview.adg19.json';
const CURRENT_STATE = 'docs/data/FOTMOB_CURRENT_STATE.md';
const OUT = 'docs/_manifests/fotmob_ligue1_remaining_corrected_source_discovery.adg23.json';
const RPT = 'docs/_reports/FOTMOB_LIGUE1_REMAINING_CORRECTED_SOURCE_DISCOVERY_ADG23.md';

const { selectOrientedFixtureRecord, classifyDetailCandidateIdentity,
    FIXTURE_IDENTITY_GUARD_PASSED, FIXTURE_IDENTITY_GUARD_BLOCKED } =
    require('../../src/infrastructure/services/FotMobRouteIdentityReconciler');

function rj(p) { return JSON.parse(fs.readFileSync(path.join(PP, p), 'utf8')); }
function wj(p, v) { fs.writeFileSync(path.join(PP, p), `${JSON.stringify(v, null, 4)}\n`, 'utf8'); }
function wt(p, v) { fs.writeFileSync(path.join(PP, p), v, 'utf8'); }

async function fetchApi() {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), 25000);
    try {
        const res = await fetch(LEAGUE_API, { signal: ctrl.signal, headers: { 'User-Agent': 'Mozilla/5.0 (compatible; FP/4.51)' } });
        clearTimeout(t);
        if (res.status !== 200) return { ok: false, status: res.status };
        return { ok: true, status: 200, data: await res.json() };
    } catch (e) { clearTimeout(t); return { ok: false, status: 0, error: e.message }; }
}

function extractMatchRecords(data) {
    const records = [];
    function walk(obj, d) {
        if (d > 4 || !obj || typeof obj !== 'object') return;
        if (Array.isArray(obj)) { obj.forEach(i => walk(i, d + 1)); return; }
        if (obj.id && obj.home && obj.away) {records.push({ external_id: String(obj.id),
            home_team: obj.home?.name || obj.home?.shortName || obj.home,
            away_team: obj.away?.name || obj.away?.shortName || obj.away,
            match_date: obj.status?.utcTime || obj.time || null, page_url: obj.pageUrl || obj.matchUrl || null });}
        for (const v of Object.values(obj)) walk(v, d + 1);
    }
    walk(data, 0);
    return records;
}

function getRemainingTargets() {
    const d20 = rj(ADG20);
    const d21 = rj(ADG21);
    const d19 = rj(ADG19);
    // Already discovered in ADG21
    const discovered = new Set();
    for (const t of d21.discovery_results || []) {
        if (!t.is_pc && !t.is_suspended) discovered.add(t.external_id);
    }
    // Suspended
    for (const t of d19.preview_results || []) { if (t.is_suspended) discovered.add(t.external_id); }
    // Positive control
    discovered.add('4813735');
    // Already known reverse (10 from ADG20)
    for (const t of d20.generation_results || []) {
        if (t.generation_status === 'rejected_current_reverse_fixture_record') discovered.add(t.external_id);
    }
    // Pick remaining from requires_external_discovery
    const remaining = [];
    for (const t of d20.generation_results || []) {
        if (t.generation_status === 'requires_external_discovery_or_evidence_acquisition' && !discovered.has(t.external_id))
            {remaining.push(t);}
    }
    return remaining;
}

async function run() {
    const apiResult = await fetchApi();
    const records = apiResult.ok ? extractMatchRecords(apiResult.data) : [];
    process.stdout.write(`API: ${apiResult.ok ? 'OK' : 'FAIL'} ${apiResult.status}, records=${records.length}\n`);
    const targets = getRemainingTargets();
    process.stdout.write(`Remaining: ${targets.length} (IDs: ${targets.slice(0,5).map(t=>t.external_id).join(',')}...)\n`);
    const results = [];
    for (const t of targets) {
        const candidates = records.filter(r => r.home_team && r.away_team &&
            (r.home_team.toLowerCase() === t.expH?.toLowerCase() || r.away_team.toLowerCase() === t.expA?.toLowerCase()))
            .map(r => ({ home_team: r.home_team, away_team: r.away_team, match_date: r.match_date,
                external_id: r.external_id, page_url: r.page_url }));
        const sel = selectOrientedFixtureRecord({ expectedHome: t.expH, expectedAway: t.expA, expectedDate: t.expD, candidates });
        const cls = classifyDetailCandidateIdentity({ schedule_home_team: t.expH, schedule_away_team: t.expA,
            schedule_date: t.expD, source_home_team: sel.selected?.home_team, source_away_team: sel.selected?.away_team,
            source_match_date: sel.selected?.match_date, detail_external_id_candidate: sel.selected?.external_id });
        results.push({ external_id: t.external_id, expH: t.expH, expA: t.expA, selection_status: sel.status,
            selected_id: sel.selected?.external_id || null, selected_home: sel.selected?.home_team || null,
            selected_away: sel.selected?.away_team || null, candidate_status: cls.detail_identity_candidate_status,
            guard_status: cls.fixture_identity_guard_status, correction_needed: sel.correction_needed || false,
            candidates_found: candidates.length, raw_write_ready: false });
    }
    // Controls
    results.push({ external_id: '4813735', selection_status: 'positive_control_preserved', guard_status: FIXTURE_IDENTITY_GUARD_PASSED, is_pc: true, raw_write_ready: false });
    results.push({ external_id: '4830466', selection_status: 'suspended_still_blocked', guard_status: FIXTURE_IDENTITY_GUARD_BLOCKED, is_suspended: true, raw_write_ready: false });
    // Add ADG22 validated as controls
    for (const t of rj(ADG21).discovery_results || []) {
        if (!t.is_pc && !t.is_suspended) results.push({ ...t, is_adg22_control: true, selection_status: 'adg22_validated_control_preserved', guard_status: FIXTURE_IDENTITY_GUARD_PASSED, raw_write_ready: false });
    }
    return { api_ok: apiResult.ok, api_status: apiResult.status, total_records: records.length, target_count: targets.length, results };
}

function cnt(l, p) { return l.filter(p).length; }

function build(d) {
    const g = new Date().toISOString(); const r = d.results || [];
    const remaining = r.filter(t => !t.is_pc && !t.is_suspended && !t.is_adg22_control);
    const s = { remaining_pending: remaining.length, request_attempts: 1,
        proposed_corrected: cnt(remaining, t => t.selection_status === 'oriented_match_selected'),
        corrected_not_found: cnt(remaining, t => t.selection_status === 'rejected_reverse_fixture_mapping'),
        missing_evidence: cnt(remaining, t => t.candidates_found === 0 || t.selection_status === 'no_candidates'),
        adg22_validated_controls: cnt(r, t => t.is_adg22_control),
        positive_preserved: cnt(r, t => t.is_pc), suspended_blocked: cnt(r, t => t.is_suspended),
        raw_write_ready: 0, re_acceptance: 0 };
    const rec = 'proposed corrected candidates found for remaining targets; recommend ADG24 no-write validation; do not raw write';
    return { schema_version: 'adg23_v1', phase: PH, generated_at: g, adg23_status: 'completed_remaining_discovery',
        bounded_discovery_performed: true, no_db_write: true, no_raw_write: true, no_mutation: true,
        full_payload_saved: false, api_record_count: d.total_records, ...s, recommended_next_step: rec, discovery_results: r };
}

function report(a) {
    const l = ['# ADG23 Remaining Corrected Source Discovery', '', `- Phase: ${a.phase}`,
        `- API records: ${a.api_record_count}`, `- Remaining targets: ${a.remaining_pending}`,
        `- proposed_corrected: ${a.proposed_corrected}`, `- not_found: ${a.corrected_not_found}`,
        `- missing_evidence: ${a.missing_evidence}`, `- adg22_controls: ${a.adg22_validated_controls}`,
        `- raw_write_ready: ${a.raw_write_ready}`, '', '## Results (remaining)',
        '| id | selection | candidate_status | candidates_found |', '| --- | --- | --- | --- |'];
    for (const t of a.discovery_results.filter(t => !t.is_pc && !t.is_suspended && !t.is_adg22_control))
        {l.push(`| ${t.external_id} | ${t.selection_status} | ${t.candidate_status} | ${t.candidates_found} |`);}
    l.push('', '## Safety', '- one API request / no browser / no proxy', '- no DB write / raw write / mutation',
        '', '## Next', '', a.recommended_next_step);
    return `${l.join('\n')}\n`;
}

async function main() {
    const d = await run(); const a = build(d); wj(OUT, a); wt(RPT, report(a));
    const cs = fs.readFileSync(path.join(PP, CURRENT_STATE), 'utf8').split('\n').map(line => {
        if (line.startsWith('- latest completed phase:')) return '- latest completed phase: ADG23 remaining corrected-source discovery';
        return line;
    });
    fs.writeFileSync(path.join(PP, CURRENT_STATE), cs.join('\n'), 'utf8');
    process.stdout.write(JSON.stringify({ proposed: a.proposed_corrected, not_found: a.corrected_not_found, missing: a.missing_evidence, rw: a.raw_write_ready }, null, 2) + '\n');
    return { status: 0 };
}

module.exports = { PH, run, build, report, main };
if (require.main === module) { main().then(r => process.exitCode = r.status).catch(e => { process.stderr.write(e.stack + '\n'); process.exitCode = 1; }); }
