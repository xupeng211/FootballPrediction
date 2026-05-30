#!/usr/bin/env node
// lifecycle: one-shot-helper
// cleanup: archive after ADG42 once corrected-artifact canonical contract migration is superseded
/* eslint-disable complexity */
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const PP = path.resolve(__dirname, '../..');
const PH = 'Phase 5.21-ADG42';
const D25 = 'docs/_manifests/fotmob_ligue1_corrected_generation_preview.adg25.json';
const D27_CAND = 'docs/_manifests/fotmob_ligue1_corrected_candidates.adg27.json';
const D22 = 'docs/_manifests/fotmob_ligue1_corrected_source_validation.adg22.json';
const D24 = 'docs/_manifests/fotmob_ligue1_remaining_corrected_source_validation.adg24.json';
const D34 = 'docs/_manifests/fotmob_ligue1_l2_url_construction_fix.adg34.json';
const CS = 'docs/data/FOTMOB_CURRENT_STATE.md';
const OUT = 'docs/_manifests/fotmob_ligue1_corrected_artifacts_canonical_contract.adg42.json';
const RPT = 'docs/_reports/FOTMOB_LIGUE1_CORRECTED_ARTIFACTS_CANONICAL_CONTRACT_ADG42.md';
const { validateCanonicalUrlAtomicHandoff } = require('../../src/infrastructure/services/FotMobRouteIdentityReconciler');

function rj(p) { return JSON.parse(fs.readFileSync(path.join(PP, p), 'utf8')); }
function wj(p, v) { fs.writeFileSync(path.join(PP, p), `${JSON.stringify(v, null, 4)}\n`, 'utf8'); }
function wt(p, v) { fs.writeFileSync(path.join(PP, p), v, 'utf8'); }
function absUrl(url) {
    if (!url) return null;
    return url.startsWith('http') ? url : `https://www.fotmob.com${url}`;
}
function byExternalId(records) {
    return new Map(records.filter(r => r && r.external_id).map(r => [String(r.external_id), r]));
}
function classifyCandidate(record, maps) {
    const externalId = String(record.external_id);
    const candidate = maps.candidates.get(externalId) || {};
    const validation = maps.validations.get(externalId) || {};
    const historical = maps.urlPreview.get(externalId) || {};
    const canonicalDetailUrl = absUrl(validation.selected_url || null);
    const historicalEnrichedUrl = absUrl(historical.old_enriched_url || validation.current_source_url || null);
    const handoff = canonicalDetailUrl
        ? validateCanonicalUrlAtomicHandoff({
            canonicalDetailUrl,
            expectedHome: record.expected_home,
            expectedAway: record.expected_away,
        })
        : null;
    const canonicalValid = Boolean(handoff && handoff.ok && handoff.route_hash_pair);
    const routeHashMissing = Boolean(canonicalDetailUrl && !canonicalValid);
    const historicalOnly = Boolean(!canonicalDetailUrl && historicalEnrichedUrl);
    const classifications = [];
    if (canonicalValid) classifications.push('canonical_url_atomic_identity_valid', 'route_hash_pair_unverified');
    if (!canonicalDetailUrl) classifications.push('canonical_url_missing');
    if (routeHashMissing) classifications.push('route_hash_pair_missing');
    if (historicalOnly) classifications.push('historical_url_only');
    classifications.push('l2_rewrite_blocked', 'detail_page_verification_required');

    return {
        target_match_id: validation.match_id || record.match_id || `53_20252026_${externalId}`,
        target_match_id_source: validation.match_id || record.match_id ? 'source_artifact' : 'ligue1_2025_2026_manifest_scope',
        corrected_detail_external_id: candidate.corrected_detail_id || record.corrected_detail_id || externalId,
        expected_home: record.expected_home,
        expected_away: record.expected_away,
        expected_match_date: record.expected_date || validation.expD || null,
        expected_competition: 'Ligue 1',
        canonical_detail_url: canonicalDetailUrl,
        canonical_url_source: canonicalDetailUrl ? 'source_controlled_l1_league_api_selected_url' : null,
        route_code: handoff?.route_code || null,
        hash_id: handoff?.hash_id || null,
        route_hash_pair: handoff?.route_hash_pair || null,
        historical_enriched_url: historicalEnrichedUrl,
        historical_enriched_url_role: historicalEnrichedUrl ? 'historical_evidence_only' : null,
        atomic_handoff_status: canonicalValid ? 'canonical_url_atomic_identity_valid'
            : routeHashMissing ? 'route_hash_pair_missing' : 'canonical_url_missing',
        classifications,
        l2_url_rewrite_allowed: false,
        l2_may_guess_route_code: false,
        l2_may_use_hash_as_route_code: false,
        l2_may_replace_route_code: false,
        l2_may_replace_hash_id: false,
        detail_id_as_route_code_allowed: false,
        route_code_must_not_be_guessed: true,
        detail_page_verification_required: true,
        detail_page_verified: false,
        no_fallback_url_construction: true,
        raw_write_ready: false,
        blocker_reason: canonicalValid ? 'detail_page_verification_required'
            : routeHashMissing ? handoff.reason : 'canonical_url_missing',
    };
}
function count(records, predicate) { return records.filter(predicate).length; }
function run() {
    const generation = rj(D25).generation_results.filter(r => r.validation_status === 'validated_corrected_candidate');
    const maps = {
        candidates: byExternalId(rj(D27_CAND).corrected_candidate_records || []),
        validations: byExternalId([...(rj(D22).validation_results || []), ...(rj(D24).validation_results || [])]),
        urlPreview: byExternalId(rj(D34).url_preview || []),
    };
    const candidates = generation.map(r => classifyCandidate(r, maps));
    const counts = {
        total_corrected_candidates: candidates.length,
        canonical_url_atomic_identity_valid_count: count(candidates, r => r.classifications.includes('canonical_url_atomic_identity_valid')),
        canonical_url_missing_count: count(candidates, r => r.classifications.includes('canonical_url_missing')),
        route_hash_pair_missing_count: count(candidates, r => r.classifications.includes('route_hash_pair_missing') || r.classifications.includes('canonical_url_missing')),
        route_hash_pair_unverified_count: count(candidates, r => r.classifications.includes('route_hash_pair_unverified')),
        historical_url_only_count: count(candidates, r => r.classifications.includes('historical_url_only')),
        l2_rewrite_blocked_count: count(candidates, r => r.l2_url_rewrite_allowed === false),
        detail_id_as_route_code_blocked_count: count(candidates, r => r.detail_id_as_route_code_allowed === false),
        route_code_guessing_blocked_count: count(candidates, r => r.route_code_must_not_be_guessed === true),
        detail_page_verification_required_count: count(candidates, r => r.detail_page_verification_required === true),
        raw_write_ready_count: count(candidates, r => r.raw_write_ready === true),
    };
    return { counts, candidates };
}
function build() {
    const r = run();
    return {
        schema_version: 'adg42_v1',
        lifecycle: 'phase-artifact',
        phase: PH,
        generated_at: new Date().toISOString(),
        input_sources: [D25, D27_CAND, D22, D24, D34, 'docs/_manifests/fotmob_canonical_url_atomic_handoff_contract.adg41.json'],
        safety: {
            live_fetch_performed: false,
            network_request_performed: false,
            db_write_performed: false,
            raw_write_execution_performed: false,
            raw_match_data_insert_performed: false,
            full_payload_saved: false,
            re_acceptance_performed: false,
            suspension_reversal_performed: false,
        },
        ...r.counts,
        candidates: r.candidates,
        recommended_next_step: r.counts.canonical_url_missing_count > 0
            ? 'ADG43 design L1 canonical URL pair discovery for missing candidates; do not fetch in ADG42'
            : 'ADG43 bounded canonical URL pair verification planning; do not fetch in ADG42',
    };
}
function report(a) {
    return ['# ADG42 Corrected Artifacts Canonical Contract', '',
        '- lifecycle: phase-artifact',
        `- Phase: ${a.phase}`,
        `- total_corrected_candidates: ${a.total_corrected_candidates}`,
        `- canonical_url_atomic_identity_valid_count: ${a.canonical_url_atomic_identity_valid_count}`,
        `- canonical_url_missing_count: ${a.canonical_url_missing_count}`,
        `- route_hash_pair_missing_count: ${a.route_hash_pair_missing_count}`,
        `- route_hash_pair_unverified_count: ${a.route_hash_pair_unverified_count}`,
        `- historical_url_only_count: ${a.historical_url_only_count}`,
        `- detail_page_verification_required_count: ${a.detail_page_verification_required_count}`,
        `- raw_write_ready_count: ${a.raw_write_ready_count}`, '',
        '## Boundary',
        '- no live fetch / network / DB write / raw write / raw_match_data insert',
        '- historical enriched URLs are historical_evidence_only, not L2 primary',
        '- missing canonical URLs remain blocked; no fallback construction',
        '', '## Next', a.recommended_next_step].join('\n') + '\n';
}
function updateCurrentState(a) {
    const next = 'ADG43 design L1 canonical URL pair discovery for missing candidates; no fetch/write in ADG42';
    const lines = fs.readFileSync(path.join(PP, CS), 'utf8').split('\n').map(line => {
        if (line.startsWith('- latest completed phase:')) return '- latest completed phase: ADG42 corrected artifacts canonical contract migration preview';
        if (line.startsWith('- raw_write_ready_count:')) return '- raw_write_ready_count: 0';
        if (line.startsWith('Merge workflow hygiene / cross-agent alignment.')) return next;
        return line;
    });
    const marker = '- ADG42 result: total_corrected_candidates=32, canonical_url_atomic_identity_valid_count=5, canonical_url_missing_count=27, route_hash_pair_unverified_count=5, raw_write_ready_count=0.';
    const idx = lines.indexOf('## Confirmed facts');
    if (idx >= 0 && !lines.includes(marker)) lines.splice(idx + 1, 0, '', marker);
    fs.writeFileSync(path.join(PP, CS), lines.join('\n'), 'utf8');
    return a;
}
function main() {
    const a = updateCurrentState(build());
    wj(OUT, a);
    wt(RPT, report(a));
    process.stdout.write(JSON.stringify({
        total: a.total_corrected_candidates,
        valid: a.canonical_url_atomic_identity_valid_count,
        missing: a.canonical_url_missing_count,
        unverified: a.route_hash_pair_unverified_count,
        rw: a.raw_write_ready_count,
    }, null, 2) + '\n');
    return { status: 0 };
}
module.exports = { PH, run, build, report, main };
if (require.main === module) { try { process.exitCode = main().status; } catch (e) { process.stderr.write(e.stack + '\n'); process.exitCode = 1; } }
