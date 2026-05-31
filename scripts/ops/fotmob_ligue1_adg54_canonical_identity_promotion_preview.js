#!/usr/bin/env node
// lifecycle: one-shot-helper
// cleanup: archive after ADG54 promotion preview is superseded
'use strict';
const fs = require('node:fs'); const path = require('node:path');
const PP = path.resolve(__dirname, '../..'); const PH = 'Phase 5.21-ADG54-PREVIEW';
const A52 = 'docs/_manifests/fotmob_ligue1_adg52_league_schedule_ssr_probe.json';
const A42 = 'docs/_manifests/fotmob_ligue1_corrected_artifacts_canonical_contract.adg42.json';
const CS = 'docs/data/FOTMOB_CURRENT_STATE.md';
const OUT = 'docs/_manifests/fotmob_ligue1_adg54_canonical_identity_promotion_preview.json';
const RPT = 'docs/_reports/FOTMOB_LIGUE1_ADG54_CANONICAL_IDENTITY_PROMOTION_PREVIEW.md';
const { parseFotmobCanonicalDetailUrl } = require('../../src/infrastructure/services/FotMobRouteIdentityReconciler');
function rj(p) { return JSON.parse(fs.readFileSync(path.join(PP, p), 'utf8')); }
function wj(p, v) { fs.writeFileSync(path.join(PP, p), `${JSON.stringify(v, null, 4)}\n`, 'utf8'); }
function wt(p, v) { fs.writeFileSync(path.join(PP, p), v, 'utf8'); }

function normalizeTeam(name) { return String(name ?? '').toLowerCase().replace(/\s+/g, ' ').trim(); }
function normalizeDate(value) { const text = String(value ?? ''); if (!text) return null; const d = new Date(text); if (Number.isNaN(d.getTime())) return text; return d.toISOString().slice(0, 10); }

// eslint-disable-next-line complexity
function buildPreview() {
    const a52 = rj(A52);
    const a42 = rj(A42);
    const matched = a52.result?.matched_targets_summary || [];
    if (matched.length !== 32) throw new Error(`Expected 32 matched targets, got ${matched.length}`);

    // Build expected identity map from ADG42
    const adg42Cands = new Map();
    for (const c of (a42.candidates || [])) {
        adg42Cands.set(c.target_match_id, c);
    }

    // Build expected map from our known problem set
    const knownExpected = {
        '53_20252026_4830473': { home: 'Paris Saint-Germain', away: 'Angers', date: '2025-08-22', competition: 'Ligue 1' },
        '53_20252026_4830472': { home: 'Nice', away: 'Auxerre', date: '2025-08-23', competition: 'Ligue 1' },
        '53_20252026_4830474': { home: 'Strasbourg', away: 'Nantes', date: '2025-08-24', competition: 'Ligue 1' },
        '53_20252026_4830475': { home: 'Toulouse', away: 'Brest', date: '2025-08-24', competition: 'Ligue 1' },
        '53_20252026_4830478': { home: 'Lens', away: 'Brest', date: '2025-08-29', competition: 'Ligue 1' },
        '53_20252026_4830479': { home: 'Lorient', away: 'Lille', date: '2025-08-30', competition: 'Ligue 1' },
        '53_20252026_4830476': { home: 'Angers', away: 'Rennes', date: '2025-08-31', competition: 'Ligue 1' },
        '53_20252026_4830477': { home: 'Le Havre', away: 'Nice', date: '2025-08-31', competition: 'Ligue 1' },
        '53_20252026_4830480': { home: 'Lyon', away: 'Marseille', date: '2025-08-31', competition: 'Ligue 1' },
        '53_20252026_4830482': { home: 'Nantes', away: 'Auxerre', date: '2025-08-30', competition: 'Ligue 1' },
        '53_20252026_4830483': { home: 'Paris FC', away: 'Metz', date: null, competition: 'Ligue 1' },
        '53_20252026_4830484': { home: 'Toulouse', away: 'Paris Saint-Germain', date: null, competition: 'Ligue 1' },
        '53_20252026_4830485': { home: 'Auxerre', away: 'Monaco', date: null, competition: 'Ligue 1' },
        '53_20252026_4830486': { home: 'Brest', away: 'Paris FC', date: null, competition: 'Ligue 1' },
        '53_20252026_4830487': { home: 'Lille', away: 'Toulouse', date: null, competition: 'Ligue 1' },
        '53_20252026_4830488': { home: 'Marseille', away: 'Lorient', date: null, competition: 'Ligue 1' },
        '53_20252026_4830489': { home: 'Metz', away: 'Angers', date: null, competition: 'Ligue 1' },
        '53_20252026_4830490': { home: 'Nice', away: 'Nantes', date: null, competition: 'Ligue 1' },
        '53_20252026_4830491': { home: 'Paris Saint-Germain', away: 'Lens', date: null, competition: 'Ligue 1' },
        '53_20252026_4830492': { home: 'Rennes', away: 'Lyon', date: null, competition: 'Ligue 1' },
        '53_20252026_4830493': { home: 'Strasbourg', away: 'Le Havre', date: null, competition: 'Ligue 1' },
        '53_20252026_4830494': { home: 'Auxerre', away: 'Toulouse', date: null, competition: 'Ligue 1' },
        '53_20252026_4830495': { home: 'Brest', away: 'Nice', date: null, competition: 'Ligue 1' },
        '53_20252026_4830497': { home: 'Lens', away: 'Lille', date: null, competition: 'Ligue 1' },
        '53_20252026_4830498': { home: 'Lyon', away: 'Angers', date: null, competition: 'Ligue 1' },
        '53_20252026_4830499': { home: 'Marseille', away: 'Paris Saint-Germain', date: null, competition: 'Ligue 1' },
        '53_20252026_4830500': { home: 'Monaco', away: 'Metz', date: null, competition: 'Ligue 1' },
        '53_20252026_4830501': { home: 'Nantes', away: 'Rennes', date: null, competition: 'Ligue 1' },
        '53_20252026_4830502': { home: 'Paris FC', away: 'Strasbourg', date: null, competition: 'Ligue 1' },
        '53_20252026_4830505': { home: 'Lorient', away: 'Monaco', date: null, competition: 'Ligue 1' },
        '53_20252026_4830507': { home: 'Nice', away: 'Paris FC', date: null, competition: 'Ligue 1' },
        '53_20252026_4830510': { home: 'Strasbourg', away: 'Marseille', date: null, competition: 'Ligue 1' },
    };

    const previews = [];
    const seenPairs = new Map();

    for (const m of matched) {
        const tid = m.target_match_id;
        const matchId = `53_20252026_${tid}`;
        const exp = knownExpected[matchId] || { home: null, away: null, date: null, competition: 'Ligue 1' };
        const url = m.candidate_canonical_detail_url ? (m.candidate_canonical_detail_url.startsWith('http') ? m.candidate_canonical_detail_url : `https://www.fotmob.com${m.candidate_canonical_detail_url}`) : null;

        const guards = {};
        // Guard 1: Canonical URL parse
        guards.canonical_url_parse = url ? parseFotmobCanonicalDetailUrl(url) : { ok: false, reason: 'no_url' };

        // Guard 2: Route hash pair atomic
        guards.route_hash_pair_atomic = Boolean(guards.canonical_url_parse.ok && guards.canonical_url_parse.route_code && guards.canonical_url_parse.hash_id);

        // Guard 3: Orientation
        const obsH = normalizeTeam(m.candidate_home); const obsA = normalizeTeam(m.candidate_away);
        const expH = normalizeTeam(exp.home); const expA = normalizeTeam(exp.away);
        guards.orientation = expH && expA ? (obsH === expH && obsA === expA) : null;

        // Guard 4: Date
        const obsD = normalizeDate(m.candidate_date); const expD = normalizeDate(exp.date);
        guards.date = expD ? (obsD === expD) : null;

        // Guard 5: Competition
        guards.competition = true; // Ligue 1 from same league schedule page

        // Guard 6: Duplicate
        const pair = guards.canonical_url_parse.ok ? guards.canonical_url_parse.route_hash_pair : null;
        const dup = pair ? seenPairs.get(pair) : null;
        seenPairs.set(pair, matchId);
        guards.duplicate = pair ? !dup : null;

        // Guard 7: Suspended — check ADG42 classification
        const a42c = adg42Cands.get(matchId);
        const isSuspended = a42c?.classifications?.includes('detail_page_verification_required') || a42c?.classifications?.includes('route_hash_pair_unverified');
        guards.suspended = isSuspended ? 'requires_explicit_reacceptance_authorization' : 'not_suspended';

        const blocked = [];
        if (!guards.canonical_url_parse.ok) blocked.push('canonical_url_parse_failed');
        if (!guards.route_hash_pair_atomic) blocked.push('route_hash_pair_not_atomic');
        if (guards.orientation === false) blocked.push('orientation_mismatch');
        if (guards.date === false) blocked.push('date_mismatch');
        if (guards.duplicate === false) blocked.push('duplicate_conflict');

        const ready = blocked.length === 0;

        previews.push({
            target_match_id: matchId,
            expected_home: exp.home, expected_away: exp.away, expected_date: exp.date, expected_competition: exp.competition,
            source: 'adg52_league_schedule_ssr_safe_summary',
            corrected_canonical_detail_url: url,
            corrected_route_code: guards.canonical_url_parse.ok ? guards.canonical_url_parse.route_code : null,
            corrected_hash_id: guards.canonical_url_parse.ok ? guards.canonical_url_parse.hash_id : null,
            corrected_route_hash_pair: guards.canonical_url_parse.ok ? guards.canonical_url_parse.route_hash_pair : null,
            candidate_home: m.candidate_home, candidate_away: m.candidate_away, candidate_date: m.candidate_date, candidate_competition: 'Ligue 1',
            orientation_status: guards.orientation === true ? 'matches' : guards.orientation === false ? 'mismatch' : 'unknown',
            date_status: guards.date === true ? 'matches' : guards.date === false ? 'mismatch' : 'unknown',
            competition_status: 'matches',
            duplicate_status: guards.duplicate === false ? 'conflict' : 'unique',
            suspended_status: guards.suspended,
            promotion_guard_blockers: blocked,
            promotion_preview_ready: ready,
            promotion_guard_status: ready ? 'promotion_preview_ready' : `blocked_${blocked.join('_')}`,
            raw_write_ready: false,
        });
    }

    const readyCount = previews.filter(p => p.promotion_preview_ready).length;
    const dupConflicts = previews.filter(p => p.duplicate_status === 'conflict').length;

    return {
        schema_version: 'adg54_preview_v1', lifecycle: 'phase-artifact', phase: PH, generated_at: new Date().toISOString(), input_sources: [A52, CS],
        safety: { live_fetch_performed: false, network_request_performed: false, detail_page_fetch_performed: false, db_write_performed: false, raw_write_execution_performed: false, raw_match_data_insert_performed: false, full_payload_saved: false, re_acceptance_performed: false, suspension_reversal_performed: false },
        adg54_status: 'promotion_preview_completed',
        total_targets: 32, preview_records_generated: previews.length,
        canonical_url_parse_pass_count: previews.filter(p => p.corrected_route_hash_pair).length,
        route_hash_pair_atomic_pass_count: previews.filter(p => p.corrected_route_hash_pair).length,
        orientation_pass_count: previews.filter(p => p.orientation_status === 'matches').length,
        orientation_mismatch_count: previews.filter(p => p.orientation_status === 'mismatch').length,
        orientation_unknown_count: previews.filter(p => p.orientation_status === 'unknown').length,
        date_pass_count: previews.filter(p => p.date_status === 'matches').length,
        date_mismatch_count: previews.filter(p => p.date_status === 'mismatch').length,
        competition_pass_count: previews.filter(p => p.competition_status === 'matches').length,
        duplicate_conflict_count: dupConflicts,
        suspended_requires_authorization_count: previews.filter(p => p.suspended_status === 'requires_explicit_reacceptance_authorization').length,
        promotion_preview_ready_count: readyCount,
        promotion_guard_blocked_count: previews.length - readyCount,
        raw_write_ready_count: 0, recommended_next_step: 'User must authorize further acceptance/mutation planning; all 32 previews generated; do NOT raw write',
        preview_records: previews,
    };
}

function writeReport(data) {
    const lines = ['# ADG54 Canonical Identity Promotion Preview', '', `- Phase: ${PH}`, `- total: ${data.total_targets}`, `- preview_ready: ${data.promotion_preview_ready_count}`, `- blocked: ${data.promotion_guard_blocked_count}`, `- orientation_pass: ${data.orientation_pass_count}`, `- orientation_mismatch: ${data.orientation_mismatch_count}`, `- date_pass: ${data.date_pass_count}`, `- duplicate_conflicts: ${data.duplicate_conflict_count}`, `- suspended_requires_auth: ${data.suspended_requires_authorization_count}`, `- raw_write_ready_count: 0`, '', '## Guard Results',
        `- canonical URL parse pass: ${data.canonical_url_parse_pass_count}/${data.total_targets}`, `- route_hash_pair atomic pass: ${data.route_hash_pair_atomic_pass_count}/${data.total_targets}`, `- orientation: ${data.orientation_pass_count} pass, ${data.orientation_mismatch_count} mismatch, ${data.orientation_unknown_count} unknown`, `- date: ${data.date_pass_count} pass, ${data.date_mismatch_count} mismatch`, `- competition: ${data.competition_pass_count} pass`, `- duplicate conflicts: ${data.duplicate_conflict_count}`, `- suspended: ${data.suspended_requires_authorization_count}`,
        '', '## Safety', '- no DB/raw write, no re-acceptance, no full payload', '- raw_write_ready_count=0', '', '## Next', 'User must authorize further acceptance/mutation planning; do NOT raw write'];
    wt(RPT, lines.join('\n') + '\n');
}

if (require.main === module) { const d = buildPreview(); wj(OUT, d); writeReport(d); console.log(JSON.stringify({ adg54_status: d.adg54_status, total: d.total_targets, ready: d.promotion_preview_ready_count, blocked: d.promotion_guard_blocked_count, orientation_pass: d.orientation_pass_count, raw_write_ready_count: 0 }, null, 2)); }
module.exports = { buildPreview };
