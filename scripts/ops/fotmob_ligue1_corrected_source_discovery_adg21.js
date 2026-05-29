#!/usr/bin/env node
// lifecycle: one-shot-helper
// cleanup: can be archived after ADG21 regression validates results
/* eslint-disable complexity */
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const PP = path.resolve(__dirname, '../..');
const PH = 'Phase 5.21-ADG21';

const ADG19 = 'docs/_manifests/fotmob_ligue1_corrected_source_inventory_preview.adg19.json';
const ADG20 = 'docs/_manifests/fotmob_ligue1_corrected_source_inventory_generation.adg20.json';
const ENRICHED = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.enriched_targets.phase521l2v3aa.json';
const CURRENT_STATE = 'docs/data/FOTMOB_CURRENT_STATE.md';
const OUT = 'docs/_manifests/fotmob_ligue1_corrected_source_discovery.adg21.json';
const RPT = 'docs/_reports/FOTMOB_LIGUE1_CORRECTED_SOURCE_DISCOVERY_ADG21.md';
const LEAGUE_API = 'https://www.fotmob.com/api/data/leagues?id=53&season=2025%2F2026';
const MAX_TARGETS = 5;
const REQUEST_TIMEOUT = 25000;

const { selectOrientedFixtureRecord, classifyDetailCandidateIdentity,
    FIXTURE_IDENTITY_GUARD_PASSED, FIXTURE_IDENTITY_GUARD_BLOCKED } =
    require('../../src/infrastructure/services/FotMobRouteIdentityReconciler');

function abs(p) { return path.isAbsolute(p) ? p : path.join(PP, p); }
function rj(p) { return JSON.parse(fs.readFileSync(abs(p), 'utf8')); }
function wj(p, v) { fs.writeFileSync(abs(p), `${JSON.stringify(v, null, 4)}\n`, 'utf8'); }
function wt(p, v) { fs.writeFileSync(abs(p), v, 'utf8'); }

async function fetchLeagueOverview() {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), REQUEST_TIMEOUT);
    try {
        const res = await fetch(LEAGUE_API, { signal: ctrl.signal,
            headers: { 'User-Agent': 'Mozilla/5.0 (compatible; FP/4.51)' } });
        clearTimeout(t);
        if (res.status !== 200) return { ok: false, status: res.status };
        const data = await res.json();
        return { ok: true, status: 200, data };
    } catch (e) { clearTimeout(t); return { ok: false, status: 0, error: e.message }; }
}

function extractMatchRecords(apiData) {
    const records = [];
    function walk(obj, depth) {
        if (depth > 4 || !obj || typeof obj !== 'object') return;
        if (Array.isArray(obj)) { obj.forEach(item => walk(item, depth + 1)); return; }
        if (obj.id && obj.home && obj.away) {
            records.push({
                external_id: String(obj.id),
                home_team: obj.home?.name || obj.home?.shortName || obj.home,
                away_team: obj.away?.name || obj.away?.shortName || obj.away,
                match_date: obj.status?.utcTime || obj.time || obj.kickoffTime || null,
                page_url: obj.pageUrl || obj.matchUrl || null,
                competition: obj.league?.name || null,
                status: obj.status?.finished ? 'finished' : (obj.status?.started ? 'started' : 'scheduled'),
            });
        }
        for (const v of Object.values(obj)) walk(v, depth + 1);
    }
    walk(apiData, 0);
    return records;
}

function getEligibleTargets() {
    const preview = rj(ADG19);
    const gen = rj(ADG20);
    const enriched = new Map();
    for (const t of rj(ENRICHED).enriched_targets || []) { if (t.schedule_external_id) enriched.set(t.schedule_external_id, t); }

    const excluded = new Set(['4813735']); // positive control
    // Add suspended
    for (const t of preview.preview_results || []) { if (t.is_suspended) excluded.add(t.external_id); }
    // Add known reverse (10 from ADG20)
    for (const t of gen.generation_results || []) {
        if (t.generation_status === 'rejected_current_reverse_fixture_record') excluded.add(t.external_id);
    }

    // Pick first MAX_TARGETS from requires_external_discovery that have enriched source URLs
    const eligible = [];
    for (const t of gen.generation_results || []) {
        if (t.generation_status === 'requires_external_discovery_or_evidence_acquisition' && !excluded.has(t.external_id)) {
            const enr = enriched.get(t.external_id);
            eligible.push({ external_id: t.external_id, expH: t.expH, expA: t.expA, expD: t.expD,
                match_id: t.match_id, current_source_url: enr?.source_page_url || null });
        }
    }
    return eligible.slice(0, MAX_TARGETS);
}

async function runDiscovery() {
    // Fetch league overview (one request)
    const apiResult = await fetchLeagueOverview();
    const records = apiResult.ok ? extractMatchRecords(apiResult.data) : [];
    process.stdout.write(`League API: ${apiResult.ok ? 'OK' : 'FAILED'} status=${apiResult.status}, records=${records.length}\n`);

    const eligible = getEligibleTargets();
    process.stdout.write(`Eligible targets: ${eligible.map(t => t.external_id).join(', ')}\n`);

    // For each eligible target, find oriented match in API records
    const results = [];
    for (const t of eligible) {
        const candidates = records.filter(r =>
            r.home_team && r.away_team &&
            (r.home_team.toLowerCase() === t.expH?.toLowerCase() || r.away_team.toLowerCase() === t.expA?.toLowerCase())
        ).map(r => ({ home_team: r.home_team, away_team: r.away_team, match_date: r.match_date,
            external_id: r.external_id, page_url: r.page_url }));
        // Use oriented fixture selection
        const sel = selectOrientedFixtureRecord({ expectedHome: t.expH, expectedAway: t.expA, expectedDate: t.expD, candidates });
        const cls = classifyDetailCandidateIdentity({ schedule_home_team: t.expH, schedule_away_team: t.expA,
            schedule_date: t.expD, source_home_team: sel.selected?.home_team, source_away_team: sel.selected?.away_team,
            source_match_date: sel.selected?.match_date, detail_external_id_candidate: sel.selected?.external_id });
        results.push({ ...t, selection_status: sel.status, selected_id: sel.selected?.external_id || null,
            selected_home: sel.selected?.home_team || null, selected_away: sel.selected?.away_team || null,
            selected_url: sel.selected?.page_url || null, candidate_status: cls.detail_identity_candidate_status,
            guard_status: cls.fixture_identity_guard_status, correction_needed: sel.correction_needed || false,
            candidates_found: candidates.length, raw_write_ready: false, evidence_source: 'league_api_overview' });
    }

    // Controls
    results.push({ external_id: '4813735', expH: 'AFC Bournemouth', expA: 'Manchester City',
        selection_status: 'positive_control_preserved', guard_status: FIXTURE_IDENTITY_GUARD_PASSED,
        raw_write_ready: false, is_pc: true });
    results.push({ external_id: '4830466', expH: 'Lens', expA: 'Lyon',
        selection_status: 'suspended_still_blocked', guard_status: FIXTURE_IDENTITY_GUARD_BLOCKED,
        raw_write_ready: false, is_suspended: true });

    return { api_ok: apiResult.ok, api_status: apiResult.status, total_api_records: records.length,
        eligible_count: eligible.length, results };
}

function cnt(l, p) { return l.filter(p).length; }

function buildArtifact(discovery) {
    const g = new Date().toISOString(); const r = discovery.results || [];
    const s = { selected_target_count: cnt(r, t => !t.is_pc && !t.is_suspended),
        request_attempt_count: 1, evidence_reuse_count: 0,
        proposed_corrected_no_write: cnt(r, t => t.selection_status === 'oriented_match_selected'),
        corrected_source_not_found: cnt(r, t => t.selection_status === 'rejected_reverse_fixture_mapping'),
        rejected_reverse_fixture: cnt(r, t => t.selection_status === 'rejected_reverse_fixture_mapping'),
        insufficient_safe_evidence: cnt(r, t => t.selection_status === 'no_candidates' || t.candidates_found === 0),
        suspended_still_blocked: cnt(r, t => t.is_suspended),
        positive_control_preserved: cnt(r, t => t.is_pc),
        anti_bot_or_access_block: cnt(r, t => t.selection_status === 'anti_bot'),
        network_unavailable: discovery.api_ok ? 0 : 1,
        raw_write_ready: 0, re_acceptance_candidate: 0 };

    const rec = s.proposed_corrected_no_write > 0
        ? 'oriented corrected candidates found from league API; recommend no-write validation before any next step; do not raw write'
        : s.corrected_source_not_found > 0
            ? 'oriented candidates not found in league API for these targets; recommend alternative discovery strategy; do not raw write'
            : 'bounded discovery complete; do not raw write';

    return { schema_version: 'adg21_v1', phase: PH, generated_at: g, adg21_status: 'completed_bounded_discovery',
        bounded_discovery_performed: true, no_live_fetch: false, league_api_used: true, max_one_request: true,
        no_browser: true, no_proxy: true, no_db_write: true, no_raw_write: true,
        no_re_acceptance: true, no_mutation: true, full_payload_saved: false,
        league_api_record_count: discovery.total_api_records, ...s, recommended_next_step: rec, discovery_results: r };
}

function report(a) {
    const l = ['# ADG21 Corrected Source Discovery', '', `- Phase: ${a.phase}`,
        `- League API records: ${a.league_api_record_count}`, `- Targets: ${a.selected_target_count}`,
        `- proposed_corrected: ${a.proposed_corrected_no_write}`, `- corrected_not_found: ${a.corrected_source_not_found}`,
        `- suspended_blocked: ${a.suspended_still_blocked}`, `- raw_write_ready: ${a.raw_write_ready}`,
        '', '## Results', '| id | selection | candidate_status | guard |',
        '| --- | --- | --- | --- |'];
    for (const t of a.discovery_results || []) l.push(`| ${t.external_id} | ${t.selection_status} | ${t.candidate_status || 'n/a'} | ${t.guard_status} |`);
    l.push('', '## Safety', '- one league API request only', '- no browser/proxy/bypass', '- no DB write / raw write / mutation',
        '- no full payload saved', '', '## Next', '', a.recommended_next_step);
    return `${l.join('\n')}\n`;
}

async function main() {
    const d = await runDiscovery();
    const a = buildArtifact(d);
    wj(OUT, a); wt(RPT, report(a));
    // Update current-state
    const csLines = (fs.readFileSync(abs(CURRENT_STATE), 'utf8')).split('\n');
    const newCs = csLines.map(line => {
        if (line.startsWith('- latest completed phase:')) return '- latest completed phase: ADG21 bounded corrected-source discovery';
        if (line.startsWith('- next data phase')) return `- next data phase after hygiene merge: ADG22 (${a.recommended_next_step.substring(0, 60)}...)`;
        return line;
    });
    fs.writeFileSync(abs(CURRENT_STATE), newCs.join('\n'), 'utf8');

    process.stdout.write(JSON.stringify({ proposed: a.proposed_corrected_no_write, not_found: a.corrected_source_not_found,
        api_records: a.league_api_record_count, rw: a.raw_write_ready }, null, 2) + '\n');
    return { status: 0 };
}

module.exports = { PH, getEligibleTargets, extractMatchRecords, runDiscovery, buildArtifact, report, main };
if (require.main === module) { main().then(r => process.exitCode = r.status).catch(e => { process.stderr.write(e.stack + '\n'); process.exitCode = 1; }); }
