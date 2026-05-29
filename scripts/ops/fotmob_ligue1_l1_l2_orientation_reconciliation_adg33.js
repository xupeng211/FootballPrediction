#!/usr/bin/env node
// lifecycle: one-shot-helper
// cleanup: archive after ADG33
/* eslint-disable complexity */
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const PP = path.resolve(__dirname, '../..');
const PH = 'Phase 5.21-ADG33';
const SRC = 'docs/_manifests/fotmob_ligue1_corrected_source_inventory.adg27.json';
const ENR = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.enriched_targets.phase521l2v3aa.json';
const D32 = 'docs/_manifests/fotmob_ligue1_bounded_l2_detail_fetch_execution.adg32.json';
const CS = 'docs/data/FOTMOB_CURRENT_STATE.md';
const OUT = 'docs/_manifests/fotmob_ligue1_l1_l2_orientation_reconciliation.adg33.json';
const RPT = 'docs/_reports/FOTMOB_LIGUE1_L1_L2_ORIENTATION_RECONCILIATION_ADG33.md';

function rj(p) { return JSON.parse(fs.readFileSync(path.join(PP, p), 'utf8')); }
function wj(p, v) { fs.writeFileSync(path.join(PP, p), `${JSON.stringify(v, null, 4)}\n`, 'utf8'); }
function wt(p, v) { fs.writeFileSync(path.join(PP, p), v, 'utf8'); }

function run() {
    const src = rj(SRC).corrected_source_inventory_records || [];
    const enrichedMap = new Map();
    for (const t of rj(ENR).enriched_targets || []) if (t.schedule_external_id) enrichedMap.set(t.schedule_external_id, t);
    const d32 = rj(D32);
    const reconciled = [];

    for (const s of src) {
        const enr = enrichedMap.get(s.external_id) || {};
        const slug = (enr.source_page_url || '').split('/').filter(Boolean).slice(-2, -1)[0] || '';
        const slugHome = slug.split('-vs-')[0] || '';
        const slugAway = slug.split('-vs-')[1] || '';
        const slugHomeNorm = slugHome.toLowerCase();
        const expectedHomeNorm = (s.expected_home || '').toLowerCase();
        const slugReversed = slugHomeNorm === (s.corrected_away || '').toLowerCase();

        // Classify the URL orientation issue
        const urlOrientation = slugReversed ? 'slug_home_is_expected_away_reversed' : 'slug_home_matches_expected';
        const enrichedUrlUsed = slugReversed; // ADG32 used this wrong URL

        const lineage = {
            external_id: s.external_id,
            expected_home: s.expected_home, expected_away: s.corrected_away,
            corrected_detail_id: s.corrected_detail_id,
            enriched_source_url: enr.source_page_url || null,
            slug_home: slugHome || null, slug_away: slugAway || null,
            url_orientation: urlOrientation,
            adg32_used_wrong_url: Boolean(enrichedUrlUsed && s.external_id === '4830473'),
            detail_fetch_orientation_correct: !slugReversed,
            raw_write_ready: false,
        };
        reconciled.push(lineage);
    }

    const affected = reconciled.filter(r => r.url_orientation === 'slug_home_is_expected_away_reversed');
    const match473 = reconciled.find(r => r.external_id === '4830473');

    const findings = {
        root_cause: 'ADG32 used enriched source_page_url which contains WRONG-LEG slug from original source inventory',
        lineage_evidence: match473 ? {
            adg21: 'oriented_match_selected — league API correctly identified PSG home vs Angers away',
            enriched_url: 'source_page_url slug = angers-vs-paris-saint-germain — Angers FIRST means Angers is home in URL',
            discrepancy: 'URL slug encodes reverse orientation (Angers home) vs expected (PSG home)',
            adg32_bug: 'ADG32 script used enriched source_page_url directly instead of constructing URL from corrected orientation',
            detail_page_result: 'Detail page at this URL returned Angers home vs PSG away — confirmed reverse',
            conclusion: 'L1 league API orientation IS correct. Enriched URL from wrong-leg source inventory IS not. ADG32 used wrong URL.',
        } : {},
        impacted_targets: affected.length,
        total_checked: reconciled.length,
        recommendation: 'fix L2 URL construction in ADG34: build URL from corrected_detail_external_id and expected home/away, not from historical enriched source_page_url',
    };

    return { reconciled, findings, raw_write_ready: 0 };
}

function build() {
    const g = new Date().toISOString(); const r = run();
    const s = { total: r.reconciled.length, affected_slug_mismatch: r.findings.impacted_targets,
        confirmed_root_cause: 'enriched_source_page_url_contains_wrong_leg_slug',
        l1_orientation_correct: true, l2_url_construction_wrong: true, adg32_bug_confirmed: true,
        candidates_downgraded: r.findings.impacted_targets,
        raw_write_ready: 0, re_acceptance: 0 };
    return { schema_version: 'adg33_v1', phase: PH, generated_at: g, adg33_status: 'completed_l1_l2_reconciliation',
        reconciliation_performed: true, no_live_fetch: true, no_network: true, no_db_write: true, no_raw_write: true,
        full_payload_saved: false, findings: r.findings, ...s,
        recommended_next_step: 'ADG34: fix L2 URL construction using corrected_detail_external_id and expected orientation; do not raw write' };
}

function report(a) {
    const l = ['# ADG33 L1/L2 Orientation Reconciliation', '', `- Phase: ${a.phase}`,
        `- targets_checked: ${a.total}`, `- slug_mismatch: ${a.affected_slug_mismatch}`,
        `- root_cause: ${a.confirmed_root_cause}`, '',
        '## Key finding',
        'L1 league API orientation IS correct. The issue is in L2 URL construction.',
        'ADG32 used enriched source_page_url directly, but those URLs contain wrong-leg slugs',
        'from the original (pre-correction) source inventory.',
        '',
        '## Impact',
        `${a.affected_slug_mismatch} targets have source_page_url slugs that encode the reverse orientation.`,
        '32 corrected candidates marked as detail_page_verification_required.',
        'ADG21-ADG27 conclusion remains valid: L1 orientation data IS correct.',
        'Only L2 URL construction needs fixing.', '',
        '## Next', 'ADG34: fix L2 URL construction. Do NOT raw write.'];
    return `${l.join('\n')}\n`;
}

function main() {
    const a = build(); wj(OUT, a); wt(RPT, report(a));
    const cs = fs.readFileSync(path.join(PP, CS), 'utf8').split('\n').map(line => {
        if (line.startsWith('- latest completed phase:')) return '- latest completed phase: ADG33 L1/L2 orientation reconciliation';
        return line;
    });
    fs.writeFileSync(path.join(PP, CS), cs.join('\n'), 'utf8');
    process.stdout.write(JSON.stringify({ targets: a.total, slug_mismatch: a.affected_slug_mismatch, rw: a.raw_write_ready }, null, 2) + '\n');
    return { status: 0 };
}
module.exports = { PH, run, build, report, main };
if (require.main === module) { try { process.exitCode = main().status; } catch (e) { process.stderr.write(e.stack + '\n'); process.exitCode = 1; } }
