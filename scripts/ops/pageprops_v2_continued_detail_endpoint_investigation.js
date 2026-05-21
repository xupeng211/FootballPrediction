#!/usr/bin/env node
/* eslint-disable complexity, max-lines, max-statements */
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const feasibility = require('./pageprops_v2_detail_api_endpoint_feasibility');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const PHASE = 'Phase 5.21L2V3T';
const PHASE_NAME = 'continued_detail_endpoint_investigation';
const ARTIFACT_STATUS = 'completed_no_write_continued_detail_endpoint_investigation';
const GENERATED_AT = '2026-05-21T00:00:00Z';
const MANIFEST_PATH = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json';
const L2V3Q_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.continued_metadata_investigation.phase521l2v3q.json';
const L2V3R_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.detail_url_construction_fix_plan.phase521l2v3r.json';
const L2V3S_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.detail_api_endpoint_feasibility.phase521l2v3s.json';
const FOTMOB_ROUTE_SELECTOR_REPORT_PATH = 'docs/_reports/FOTMOB_DETAIL_ROUTE_SELECTOR_PHASE5_12L2B.md';
const FOTMOB_ROUTE_AUDIT_REPORT_PATH = 'docs/_reports/FOTMOB_RAW_DETAIL_ACCESS_ROUTE_AUDIT_PHASE5_12L2A.md';
const ARTIFACT_OUTPUT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.continued_detail_endpoint_investigation.phase521l2v3t.json';
const REPORT_PATH = 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3T.md';
const PREVIOUS_ENDPOINT_STATUS = 'blocked_http_403';
const MAX_CONTROLLED_TARGETS = 1;
const NEXT_REQUIRED_STEP = 'source_inventory_enrichment_planning';
const NEXT_RECOMMENDED_STEP = 'Phase 5.21L2V3U: source inventory enrichment planning';
const PRECISE_IMPLEMENTATION_STEP = 'precise_detail_endpoint_strategy_implementation';
const PRECISE_IMPLEMENTATION_RECOMMENDATION = 'Phase 5.21L2V3U: precise detail endpoint strategy implementation';
const ROUTE_REGENERATION_STEP = 'route_target_regeneration_planning';
const ROUTE_REGENERATION_RECOMMENDATION = 'Phase 5.21L2V3U: route target regeneration planning';
const CONTINUED_INVESTIGATION_STEP = 'continued_endpoint_source_inventory_investigation';
const CONTINUED_INVESTIGATION_RECOMMENDATION = 'Phase 5.21L2V3U: continued endpoint/source inventory investigation';

const SOURCE_FILES = Object.freeze([
    {
        key: 'source_inventory_preflight',
        path: 'scripts/ops/single_league_target_discovery_source_inventory_preflight.js',
        patterns: ['match?.pageUrl', 'match?.matchUrl', 'match?.url', 'match?.href'],
    },
    {
        key: 'source_inventory_reconciliation_plan',
        path: 'scripts/ops/pageprops_v2_target_source_inventory_reconciliation_plan.js',
        patterns: ['page_url_base', 'page_url_anchor', 'source_inventory_page_url_base'],
    },
    {
        key: 'fotmob_raw_detail_fetcher',
        path: 'src/infrastructure/services/FotMobRawDetailFetcher.js',
        patterns: ['buildFotMobMatchUrl', 'pageUrlBase'],
    },
    {
        key: 'fotmob_api_client',
        path: 'src/infrastructure/network/FotMobApiClient.js',
        patterns: ['/api/data/matchDetails', 'fetchMatchDetails'],
    },
    {
        key: 'l2_raw_detail_preview',
        path: 'scripts/ops/l2_raw_detail_preview.js',
        patterns: ['api/data/matchDetails', 'api_match_details', 'alternate_route'],
    },
    {
        key: 'fotmob_detail_route_selector',
        path: 'src/infrastructure/services/FotMobDetailRouteSelector.js',
        patterns: ['html_hydration', 'api_match_details', 'alternate_route'],
    },
    {
        key: 'marathon_service',
        path: 'src/infrastructure/services/MarathonService.js',
        patterns: ['api/data/matchDetails', 'api/matchDetails'],
    },
    {
        key: 'next_data_parser',
        path: 'src/parsers/fotmob/NextDataParser.js',
        patterns: ['__NEXT_DATA__', 'props.pageProps'],
    },
]);

const BUILD_DATA_CONTEXT_FILES = Object.freeze([
    {
        key: 'raw_storage_strategy_revision_plan',
        path: 'docs/_reports/RAW_STORAGE_STRATEGY_REVISION_PLANNING_PHASE5_21L2C.md',
        patterns: ['buildId'],
    },
    {
        key: 'pageprops_v2_no_write_preview_test',
        path: 'tests/unit/pageprops_v2_no_write_preview.test.js',
        patterns: ['buildId'],
    },
    {
        key: 'html_hydration_source_fidelity_test',
        path: 'tests/unit/html_hydration_source_fidelity_live_compare.test.js',
        patterns: ['buildId'],
    },
]);

function absolutePath(filePath) {
    if (path.isAbsolute(filePath)) return filePath;
    return path.join(PROJECT_ROOT, filePath);
}

function readTextFile(filePath) {
    return fs.readFileSync(absolutePath(filePath), 'utf8');
}

function readJsonFile(filePath) {
    return JSON.parse(readTextFile(filePath));
}

function writeJsonFile(filePath, value) {
    fs.writeFileSync(absolutePath(filePath), `${JSON.stringify(value, null, 4)}\n`, 'utf8');
}

function writeTextFile(filePath, value) {
    fs.writeFileSync(absolutePath(filePath), value, 'utf8');
}

function normalizeText(value) {
    return String(value ?? '').trim();
}

function normalizeLower(value) {
    return normalizeText(value).toLowerCase();
}

function normalizeBooleanFlag(value, fallback = false) {
    if (typeof value === 'boolean') return value;
    if (value === null || value === undefined || value === '') return fallback;
    const text = normalizeLower(value);
    if (['1', 'true', 'yes', 'y', 'on'].includes(text)) return true;
    if (['0', 'false', 'no', 'n', 'off'].includes(text)) return false;
    return fallback;
}

function parseInteger(value, fallback = null) {
    if (value === null || value === undefined || value === '') return fallback;
    const text = normalizeText(value);
    if (!/^\d+$/.test(text)) return Number.NaN;
    return Number.parseInt(text, 10);
}

function sourceTextFor(item, dependencies = {}) {
    if (
        dependencies.sourceTextByPath &&
        Object.prototype.hasOwnProperty.call(dependencies.sourceTextByPath, item.path)
    ) {
        return dependencies.sourceTextByPath[item.path];
    }
    return readTextFile(item.path);
}

function analyzeSourceFiles(sourceFiles = SOURCE_FILES, dependencies = {}) {
    return sourceFiles.map(item => {
        const text = sourceTextFor(item, dependencies);
        const matched_patterns = item.patterns.filter(pattern => text.includes(pattern));
        return {
            key: item.key,
            path: item.path,
            matched_patterns,
            matched_pattern_count: matched_patterns.length,
            evidence_found: matched_patterns.length === item.patterns.length,
        };
    });
}

function sanitizeSourceFileAnalysis(sourceFileAnalysis = []) {
    return sourceFileAnalysis.map(item => ({
        key: item.key,
        path: item.path,
        matched_pattern_count: Number(item.matched_pattern_count || 0),
        evidence_found: item.evidence_found === true,
    }));
}

function analyzeBuildDataContext(dependencies = {}) {
    const analysis = analyzeSourceFiles(BUILD_DATA_CONTEXT_FILES, dependencies);
    const contextMentionCount = analysis.filter(item => item.evidence_found === true).length;
    const executableBuilderFound = analyzeSourceFiles(
        SOURCE_FILES.filter(item => item.key !== 'next_data_parser'),
        dependencies
    ).some(item =>
        item.matched_patterns.some(pattern => pattern.includes('_next/data') || pattern.includes('buildId'))
    );
    return {
        context_files: analysis,
        context_mention_count: contextMentionCount,
        executable_builder_found: executableBuilderFound,
        docs_or_tests_only: contextMentionCount > 0 && executableBuilderFound !== true,
    };
}

function sanitizeBuildDataContext(buildDataContext = {}) {
    return {
        context_files: sanitizeSourceFileAnalysis(buildDataContext.context_files || []),
        context_mention_count: Number(buildDataContext.context_mention_count || 0),
        executable_builder_found: buildDataContext.executable_builder_found === true,
        docs_or_tests_only: buildDataContext.docs_or_tests_only === true,
    };
}

function parseArgs(argv = process.argv.slice(2)) {
    const options = {
        controlledLiveCheck: false,
        networkAuthorization: false,
        maxTargets: MAX_CONTROLLED_TARGETS,
        writeFiles: true,
        help: false,
        unknown: [],
    };
    const keyMap = {
        'controlled-live-check': 'controlledLiveCheck',
        controlled_live_check: 'controlledLiveCheck',
        'network-authorization': 'networkAuthorization',
        network_authorization: 'networkAuthorization',
        'max-targets': 'maxTargets',
        max_targets: 'maxTargets',
        'write-files': 'writeFiles',
        write_files: 'writeFiles',
        help: 'help',
        h: 'help',
    };

    for (let index = 0; index < argv.length; index += 1) {
        const arg = String(argv[index]);
        if (!arg.startsWith('--')) {
            options.unknown.push(arg);
            continue;
        }
        const key = arg.replace(/^--/, '').split('=')[0];
        const mapped = keyMap[key];
        if (!mapped) {
            options.unknown.push(key);
            continue;
        }
        const value = arg.includes('=')
            ? arg.slice(arg.indexOf('=') + 1)
            : argv[index + 1] && !String(argv[index + 1]).startsWith('--')
              ? argv[++index]
              : true;
        if (['controlledLiveCheck', 'networkAuthorization', 'writeFiles', 'help'].includes(mapped)) {
            options[mapped] = normalizeBooleanFlag(value, true);
        } else {
            options[mapped] = parseInteger(value, options[mapped]);
        }
    }

    return options;
}

function validateCliOptions(options = {}) {
    const errors = [];
    if (Array.isArray(options.unknown) && options.unknown.length > 0) {
        errors.push(`unknown arguments: ${options.unknown.join(', ')}`);
    }
    if (options.controlledLiveCheck === true && options.networkAuthorization !== true) {
        errors.push('network-authorization=yes is required for controlled live endpoint check');
    }
    if (
        !Number.isInteger(options.maxTargets) ||
        options.maxTargets < 0 ||
        options.maxTargets > MAX_CONTROLLED_TARGETS
    ) {
        errors.push(`max-targets must be between 0 and ${MAX_CONTROLLED_TARGETS}`);
    }
    return { ok: errors.length === 0, errors };
}

function validateInputs(manifest = {}, l2v3rArtifact = {}, l2v3qArtifact = {}, l2v3sArtifact = {}) {
    const errors = [];
    const nextRequiredStep = normalizeText(manifest.next_required_step);
    const alreadyCompleted =
        nextRequiredStep === NEXT_REQUIRED_STEP &&
        normalizeText(manifest.phase_5_21_l2v3t_investigation_status) === ARTIFACT_STATUS;

    if (nextRequiredStep !== 'continued_detail_endpoint_investigation' && !alreadyCompleted) {
        errors.push(
            'manifest next_required_step must be continued_detail_endpoint_investigation or completed L2V3T output'
        );
    }
    if (manifest.raw_write_ready_for_execution !== false) {
        errors.push('manifest raw_write_ready_for_execution must remain false');
    }
    if (Number(manifest.accepted_mapping_count || 0) !== 0) {
        errors.push('manifest accepted_mapping_count must remain 0');
    }
    if (normalizeText(manifest.phase_5_21_l2v3s_feasibility_status) !== feasibility.ARTIFACT_STATUS) {
        errors.push('manifest phase_5_21_l2v3s_feasibility_status must record completed L2V3S output');
    }
    if (normalizeText(l2v3rArtifact.current_url_strategy) !== 'fotmob_match_external_id_route') {
        errors.push('L2V3R current_url_strategy must remain fotmob_match_external_id_route');
    }
    if (l2v3rArtifact.slug_reuse_risk !== true) {
        errors.push('L2V3R slug_reuse_risk must remain true');
    }
    if (Number(l2v3qArtifact.missing_pageurl_base_count || 0) !== 42) {
        errors.push('L2V3Q missing_pageurl_base_count must be 42');
    }
    if (Number(l2v3qArtifact.route_target_regeneration_needed_count || 0) !== 0) {
        errors.push('L2V3Q route_target_regeneration_needed_count must remain 0');
    }
    if (normalizeText(l2v3sArtifact.proposal_phase) !== 'Phase 5.21L2V3S') {
        errors.push('L2V3S artifact must remain Phase 5.21L2V3S');
    }
    if (l2v3sArtifact.controlled_live_check_performed !== true) {
        errors.push('L2V3S controlled_live_check_performed must remain true');
    }
    if (Number(l2v3sArtifact.block_or_captcha_count || 0) !== 1) {
        errors.push('L2V3S block_or_captcha_count must remain 1');
    }
    if (normalizeText(l2v3sArtifact.precise_detail_endpoint_found) !== 'unknown') {
        errors.push('L2V3S precise_detail_endpoint_found must remain unknown');
    }
    if (normalizeText(l2v3sArtifact.endpoint_avoids_slug_reuse) !== 'unknown') {
        errors.push('L2V3S endpoint_avoids_slug_reuse must remain unknown');
    }
    if (l2v3sArtifact.raw_write_ready_for_execution !== false) {
        errors.push('L2V3S raw_write_ready_for_execution must remain false');
    }
    if (Number(l2v3sArtifact.accepted_mapping_count || 0) !== 0) {
        errors.push('L2V3S accepted_mapping_count must remain 0');
    }
    return { ok: errors.length === 0, errors };
}

function summarizeManifestUrlFields(manifest = {}) {
    const targets = Array.isArray(manifest.candidate_targets) ? manifest.candidate_targets : [];
    const countWith = key => targets.filter(target => Boolean(normalizeText(target[key]))).length;
    return {
        candidate_targets_count: targets.length,
        page_url_count: countWith('page_url'),
        page_url_base_count: countWith('page_url_base'),
        source_inventory_page_url_base_count: countWith('source_inventory_page_url_base'),
        manifest_page_url_base_count: countWith('manifest_page_url_base'),
    };
}

function buildEndpointHints(sourceFileAnalysis = [], buildDataContext = {}, l2v3rArtifact = {}, l2v3sArtifact = {}) {
    const hasEvidence = key => sourceFileAnalysis.some(item => item.key === key && item.evidence_found === true);
    return [
        {
            endpoint_hint_key: 'source_inventory_schedule_api',
            route_candidate: '/api/data/leagues?id={leagueId}&season={season}',
            hint_type: 'schedule_inventory',
            code_evidence_found: hasEvidence('source_inventory_preflight'),
            current_pageprops_detail_usage: false,
            safe_conclusion: 'supports_target_inventory_and_pageUrl_recovery_not_precise_detail_payload',
        },
        {
            endpoint_hint_key: 'html_match_external_id_route',
            route_candidate: '/match/{externalId}',
            hint_type: 'html_detail_route',
            code_evidence_found: hasEvidence('fotmob_raw_detail_fetcher'),
            current_pageprops_detail_usage: true,
            precise_detail_candidate: false,
            safe_conclusion: 'current_route_exists_but_schedule_external_id_alone_remains_slug_reuse_risk',
        },
        {
            endpoint_hint_key: 'api_data_match_details',
            route_candidate: '/api/data/matchDetails?matchId={externalId}',
            hint_type: 'json_detail_api',
            code_evidence_found: hasEvidence('fotmob_api_client') || hasEvidence('l2_raw_detail_preview'),
            previous_status: PREVIOUS_ENDPOINT_STATUS,
            precise_detail_candidate: true,
            safe_conclusion:
                normalizeText(l2v3sArtifact.controlled_endpoint_check?.stop_reason) ===
                'CONTROLLED_BLOCK_SIGNAL:HTTP_403'
                    ? 'public_no_write_access_still_blocked_by_http_403'
                    : 'public_no_write_access_status_unknown',
        },
        {
            endpoint_hint_key: 'api_match_details_alternate',
            route_candidate: '/api/matchDetails?matchId={externalId}',
            hint_type: 'json_detail_api_legacy_or_alternate',
            code_evidence_found: hasEvidence('marathon_service') || hasEvidence('fotmob_detail_route_selector'),
            precise_detail_candidate: true,
            plan_only: true,
            safe_conclusion: 'legacy_or_browser_associated_route_not_adopted_without_future_authorization',
        },
        {
            endpoint_hint_key: 'source_inventory_page_url_slug_route',
            route_candidate: '/matches/{slug}#{externalId}',
            hint_type: 'source_inventory_identity_route',
            code_evidence_found:
                hasEvidence('source_inventory_preflight') || hasEvidence('source_inventory_reconciliation_plan'),
            precise_detail_candidate: 'unknown',
            requires_manifest_page_url_base: true,
            safe_conclusion:
                l2v3rArtifact.source_inventory_evidence?.all_pairs_share_page_url_base === true
                    ? 'source_inventory_preserves_pageUrl_identity_hints_but_current_manifest_does_not_store_them'
                    : 'source_inventory_identity_route_remains_unconfirmed',
        },
        {
            endpoint_hint_key: 'nextjs_build_data_route',
            route_candidate: 'unknown_nextjs_build_data_route_shape',
            hint_type: 'nextjs_build_data_route',
            code_evidence_found: buildDataContext.executable_builder_found === true,
            docs_or_tests_only: buildDataContext.docs_or_tests_only === true,
            precise_detail_candidate: 'unknown',
            safe_conclusion:
                buildDataContext.executable_builder_found === true
                    ? 'executable_build_data_route_builder_exists'
                    : 'no_executable_buildId_route_builder_found_in_runtime_code',
        },
    ];
}

function buildEvidenceSummary(manifest = {}, l2v3qArtifact = {}, l2v3rArtifact = {}, buildDataContext = {}) {
    const manifestUrls = summarizeManifestUrlFields(manifest);
    return {
        manifest_candidate_targets_count: manifestUrls.candidate_targets_count,
        manifest_page_url_count: manifestUrls.page_url_count,
        manifest_page_url_base_count: manifestUrls.page_url_base_count,
        manifest_source_inventory_page_url_base_count: manifestUrls.source_inventory_page_url_base_count,
        manifest_page_url_base_missing_count: manifestUrls.candidate_targets_count - manifestUrls.page_url_base_count,
        l2v3q_missing_pageurl_base_count: Number(l2v3qArtifact.missing_pageurl_base_count || 0),
        l2v3q_detail_url_construction_suspect_count: Number(l2v3qArtifact.detail_url_construction_suspect_count || 0),
        l2v3q_route_target_regeneration_needed_count: Number(l2v3qArtifact.route_target_regeneration_needed_count || 0),
        l2v3e_shared_page_url_base_pair_count: Number(
            l2v3rArtifact.source_inventory_evidence?.shared_page_url_base_pair_count || 0
        ),
        l2v3e_all_pairs_share_page_url_base:
            l2v3rArtifact.source_inventory_evidence?.all_pairs_share_page_url_base === true,
        source_inventory_page_url_extraction_supported:
            l2v3rArtifact.source_inventory_evidence?.source_inventory_route_used === 'source_inventory',
        current_writer_uses_source_inventory_page_url: l2v3rArtifact.uses_source_inventory_page_url === true,
        build_data_route_context_mention_count: Number(buildDataContext.context_mention_count || 0),
        build_data_route_executable_builder_found: buildDataContext.executable_builder_found === true,
        source_inventory_enrichment_required:
            manifestUrls.candidate_targets_count > 0 &&
            manifestUrls.page_url_base_count === 0 &&
            Number(l2v3qArtifact.missing_pageurl_base_count || 0) > 0,
        route_target_regeneration_indicated: Number(l2v3qArtifact.route_target_regeneration_needed_count || 0) > 0,
    };
}

function selectControlledLiveTarget(l2v3sArtifact = {}) {
    const firstTarget = Array.isArray(l2v3sArtifact.controlled_endpoint_check?.checked_targets)
        ? l2v3sArtifact.controlled_endpoint_check.checked_targets[0]
        : null;
    if (!firstTarget) return null;

    const requestedTeams = normalizeText(firstTarget.team_safe_summary?.requested).split('-');
    return {
        target_category: 'continued_public_api_recheck',
        requested_schedule_external_id: normalizeText(firstTarget.requested_schedule_external_id),
        match_id: normalizeText(firstTarget.match_id),
        requested_home_team: requestedTeams[0] || null,
        requested_away_team: requestedTeams[1] || null,
        requested_match_date: normalizeText(firstTarget.schedule_detail_date_safe_summary?.requested_date) || null,
        requested_status: normalizeText(firstTarget.status_safe_summary?.requested_status) || null,
    };
}

async function executeControlledLiveCheck(target = {}, dependencies = {}) {
    const fetchFn = dependencies.fetchFn || global.fetch;
    if (typeof fetchFn !== 'function') {
        throw new Error('FETCH_DEPENDENCY_MISSING');
    }
    const request = feasibility.buildDetailApiRequest({
        schedule_external_id: target.requested_schedule_external_id,
    });
    let response;
    let bodyText = '';
    try {
        response = await fetchFn(request.url, {
            method: request.method,
            headers: request.headers,
            redirect: 'follow',
        });
        bodyText = typeof response.text === 'function' ? await response.text() : '';
        return feasibility.buildSafeEndpointSummary({ target, request, response, bodyText });
    } catch (error) {
        return feasibility.buildSafeEndpointSummary({
            target,
            request,
            response: { status: 0 },
            bodyText,
            error,
        });
    }
}

function summarizeControlledLiveCheck(result = {}, performed = false) {
    const checkedTargets = Array.isArray(result.checked_targets) ? result.checked_targets : [];
    const firstTarget = checkedTargets[0] || null;
    const preciseDetailEndpointFound =
        firstTarget?.identity_match === true &&
        firstTarget?.team_safe_summary?.status === 'same_order' &&
        firstTarget?.date_rule_status === 'date_match'
            ? true
            : 'unknown';
    const endpointAvoidsSlugReuse = firstTarget?.whether_endpoint_avoids_slug_reuse === true ? true : 'unknown';
    return {
        controlled_live_check_performed: performed,
        checked_target_count: checkedTargets.length,
        precise_detail_endpoint_found: preciseDetailEndpointFound,
        endpoint_avoids_slug_reuse: endpointAvoidsSlugReuse,
        parse_failure_count: checkedTargets.filter(item => item.parsed !== true).length,
        block_or_captcha_count: checkedTargets.filter(item => (item.block_signals || []).length > 0).length,
        stopped_early: result.stopped_early === true,
        stop_reason: result.stop_reason || null,
        targets: checkedTargets,
    };
}

function buildRecommendedStrategy(evidenceSummary = {}, controlledSummary = {}) {
    if (
        controlledSummary.precise_detail_endpoint_found === true &&
        controlledSummary.endpoint_avoids_slug_reuse === true
    ) {
        return {
            endpoint_investigation_result:
                'controlled_metadata_only_recheck_identified_a_candidate_precise_endpoint_but_raw_write_remains_blocked',
            recommended_strategy: PRECISE_IMPLEMENTATION_RECOMMENDATION,
            strategy_confidence: 'medium',
            requires_followup_implementation: true,
            recommended_next_step: PRECISE_IMPLEMENTATION_RECOMMENDATION,
            next_required_step: PRECISE_IMPLEMENTATION_STEP,
            new_endpoint_candidate_count: 1,
        };
    }
    if (evidenceSummary.source_inventory_enrichment_required === true) {
        return {
            endpoint_investigation_result:
                'no_new_safe_public_detail_endpoint_candidate_found_public_api_403_remains_and_source_inventory_pageUrl_metadata_is_missing_from_manifest',
            recommended_strategy: NEXT_RECOMMENDED_STEP,
            strategy_confidence: 'medium',
            requires_followup_implementation: false,
            recommended_next_step: NEXT_RECOMMENDED_STEP,
            next_required_step: NEXT_REQUIRED_STEP,
            new_endpoint_candidate_count: 0,
        };
    }
    if (evidenceSummary.route_target_regeneration_indicated === true) {
        return {
            endpoint_investigation_result:
                'source_controlled_evidence_indicates_route_target_regeneration_should_precede_further_endpoint_work',
            recommended_strategy: ROUTE_REGENERATION_RECOMMENDATION,
            strategy_confidence: 'low',
            requires_followup_implementation: false,
            recommended_next_step: ROUTE_REGENERATION_RECOMMENDATION,
            next_required_step: ROUTE_REGENERATION_STEP,
            new_endpoint_candidate_count: 0,
        };
    }
    return {
        endpoint_investigation_result:
            'endpoint_and_source_inventory_evidence_remain_inconclusive_for_a_precise_detail_request_strategy',
        recommended_strategy: CONTINUED_INVESTIGATION_RECOMMENDATION,
        strategy_confidence: 'low',
        requires_followup_implementation: false,
        recommended_next_step: CONTINUED_INVESTIGATION_RECOMMENDATION,
        next_required_step: CONTINUED_INVESTIGATION_STEP,
        new_endpoint_candidate_count: 0,
    };
}

function buildQuestionAnswers(evidenceSummary = {}, endpointHints = [], strategy = {}) {
    const publicApi = endpointHints.find(item => item.endpoint_hint_key === 'api_data_match_details');
    const buildData = endpointHints.find(item => item.endpoint_hint_key === 'nextjs_build_data_route');
    return {
        is_public_api_route_suitable_for_server_side_no_write_access:
            publicApi?.safe_conclusion === 'public_no_write_access_still_blocked_by_http_403' ? false : 'unknown',
        repo_has_other_detail_endpoint_hints: endpointHints.length > 1,
        nextjs_hydration_or_build_data_route_status:
            buildData?.code_evidence_found === true
                ? 'possible_existing_builder'
                : 'unknown_no_executable_builder_found',
        source_inventory_metadata_sufficiency:
            evidenceSummary.source_inventory_enrichment_required === true
                ? 'partial_source_inventory_can_preserve_pageUrl_but_current_manifest_lacks_page_url_base'
                : 'unknown',
        should_abandon_public_api_endpoint_path:
            publicApi?.safe_conclusion === 'public_no_write_access_still_blocked_by_http_403'
                ? 'deprioritize_public_api_match_details_keep_source_inventory_and_html_hydration_identity_work_separate'
                : 'unknown',
        precise_detail_request_strategy_summary:
            'requested_schedule_external_id_remains_primary_identity_and_observed_detail_external_id_must_equal_requested_schedule_external_id_before_any_future_acceptance',
        recommended_phase_5_21_l2v3u: strategy.recommended_next_step,
    };
}

function buildArtifact({
    manifest,
    l2v3qArtifact,
    l2v3rArtifact,
    l2v3sArtifact,
    sourceFileAnalysis,
    buildDataContext,
    controlledSummary,
    generatedAt = GENERATED_AT,
} = {}) {
    const endpointHints = buildEndpointHints(sourceFileAnalysis, buildDataContext, l2v3rArtifact, l2v3sArtifact);
    const evidenceSummary = buildEvidenceSummary(manifest, l2v3qArtifact, l2v3rArtifact, buildDataContext);
    const strategy = buildRecommendedStrategy(evidenceSummary, controlledSummary);
    const safeSourceFileAnalysis = sanitizeSourceFileAnalysis(sourceFileAnalysis);
    const safeBuildDataContext = sanitizeBuildDataContext(buildDataContext);
    return {
        artifact_type: 'continued_detail_endpoint_investigation',
        artifact_status: ARTIFACT_STATUS,
        proposal_phase: PHASE,
        phase_name: PHASE_NAME,
        source_phase: 'Phase 5.21L2V3S',
        generated_at: generatedAt,
        no_write: true,
        live_source_check_performed: controlledSummary.controlled_live_check_performed,
        controlled_live_check_performed: controlledSummary.controlled_live_check_performed,
        network_request_performed: controlledSummary.controlled_live_check_performed,
        db_write_performed: false,
        raw_insert_performed: false,
        matches_write_performed: false,
        matches_external_id_modified: false,
        schema_migration_performed: false,
        parser_features_training_prediction_performed: false,
        browser_proxy_captcha_bypass_performed: false,
        identity_mapping_acceptance_performed: false,
        baseline_acceptance_performed: false,
        raw_write_retry_performed: false,
        raw_write_ready_for_execution: false,
        accepted_mapping_count: 0,
        previous_endpoint_status: PREVIOUS_ENDPOINT_STATUS,
        analyzed_endpoint_hint_count: endpointHints.length,
        checked_target_count: controlledSummary.checked_target_count,
        block_or_captcha_count: controlledSummary.block_or_captcha_count,
        new_endpoint_candidate_count: strategy.new_endpoint_candidate_count,
        precise_detail_endpoint_found: controlledSummary.precise_detail_endpoint_found,
        endpoint_avoids_slug_reuse: controlledSummary.endpoint_avoids_slug_reuse,
        endpoint_investigation_result: strategy.endpoint_investigation_result,
        recommended_strategy: strategy.recommended_strategy,
        strategy_confidence: strategy.strategy_confidence,
        requires_followup_implementation: strategy.requires_followup_implementation,
        endpoint_hints: endpointHints,
        source_code_evidence: {
            analyzed_source_file_count: safeSourceFileAnalysis.length,
            source_files: safeSourceFileAnalysis,
        },
        build_data_context: safeBuildDataContext,
        evidence_summary: evidenceSummary,
        controlled_endpoint_check: {
            max_allowed_targets: MAX_CONTROLLED_TARGETS,
            supported_route_keys: ['api_data_match_details'],
            stopped_early: controlledSummary.stopped_early,
            stop_reason: controlledSummary.stop_reason,
            checked_targets: controlledSummary.targets,
        },
        upstream_context: {
            l2v3r_current_url_strategy: l2v3rArtifact.current_url_strategy,
            l2v3r_uses_match_external_id_route: l2v3rArtifact.uses_match_external_id_route,
            l2v3r_uses_source_inventory_page_url: l2v3rArtifact.uses_source_inventory_page_url,
            l2v3r_slug_reuse_risk: l2v3rArtifact.slug_reuse_risk,
            l2v3q_detail_url_construction_suspect_count: l2v3qArtifact.detail_url_construction_suspect_count,
            l2v3q_missing_pageurl_base_count: l2v3qArtifact.missing_pageurl_base_count,
            l2v3s_previous_stop_reason: l2v3sArtifact.controlled_endpoint_check?.stop_reason || null,
        },
        question_answers: buildQuestionAnswers(evidenceSummary, endpointHints, strategy),
        safety_contract: {
            endpoint_investigation_result_is_not_accepted_mapping: true,
            endpoint_investigation_result_is_not_raw_write_authorization: true,
            endpoint_investigation_result_is_not_baseline_acceptance: true,
            endpoint_investigation_result_is_not_raw_write_retry: true,
            public_api_403_remains_blocked_or_unknown: true,
            controlled_live_check_cannot_save_full_payload: true,
            controlled_live_check_cannot_write_db: true,
            no_browser_proxy_captcha_bypass: true,
            separate_identity_mapping_acceptance_required: true,
            separate_baseline_acceptance_required: true,
            separate_final_db_write_authorization_required: true,
        },
        recommended_next_step: strategy.recommended_next_step,
        next_required_step: strategy.next_required_step,
    };
}

function updateManifestMetadata(manifest = {}, artifact = {}) {
    return {
        ...manifest,
        phase_5_21_l2v3t_investigation_status: artifact.artifact_status,
        continued_detail_endpoint_investigation_status: artifact.artifact_status,
        phase_5_21_l2v3t_artifact_path: ARTIFACT_OUTPUT_PATH,
        phase_5_21_l2v3t_report_path: REPORT_PATH,
        analyzed_endpoint_hint_count: artifact.analyzed_endpoint_hint_count,
        phase_5_21_l2v3t_analyzed_endpoint_hint_count: artifact.analyzed_endpoint_hint_count,
        controlled_live_check_performed: artifact.controlled_live_check_performed,
        phase_5_21_l2v3t_controlled_live_check_performed: artifact.controlled_live_check_performed,
        previous_endpoint_status: artifact.previous_endpoint_status,
        phase_5_21_l2v3t_previous_endpoint_status: artifact.previous_endpoint_status,
        new_endpoint_candidate_count: artifact.new_endpoint_candidate_count,
        phase_5_21_l2v3t_new_endpoint_candidate_count: artifact.new_endpoint_candidate_count,
        precise_detail_endpoint_found: artifact.precise_detail_endpoint_found,
        phase_5_21_l2v3t_precise_detail_endpoint_found: artifact.precise_detail_endpoint_found,
        endpoint_avoids_slug_reuse: artifact.endpoint_avoids_slug_reuse,
        phase_5_21_l2v3t_endpoint_avoids_slug_reuse: artifact.endpoint_avoids_slug_reuse,
        endpoint_investigation_result: artifact.endpoint_investigation_result,
        phase_5_21_l2v3t_endpoint_investigation_result: artifact.endpoint_investigation_result,
        recommended_strategy: artifact.recommended_strategy,
        phase_5_21_l2v3t_recommended_strategy: artifact.recommended_strategy,
        strategy_confidence: artifact.strategy_confidence,
        phase_5_21_l2v3t_strategy_confidence: artifact.strategy_confidence,
        requires_followup_implementation: artifact.requires_followup_implementation,
        phase_5_21_l2v3t_requires_followup_implementation: artifact.requires_followup_implementation,
        accepted_mapping_count: 0,
        phase_5_21_l2v3t_accepted_mapping_count: 0,
        identity_mapping_acceptance_performed: false,
        baseline_acceptance_performed: false,
        raw_write_retry_performed: false,
        raw_write_ready_for_execution: false,
        phase_5_21_l2v3t_identity_mapping_acceptance_performed: false,
        phase_5_21_l2v3t_baseline_acceptance_performed: false,
        phase_5_21_l2v3t_raw_write_retry_performed: false,
        phase_5_21_l2v3t_raw_write_ready_for_execution: false,
        requires_separate_identity_mapping_acceptance: true,
        requires_separate_baseline_acceptance: true,
        requires_separate_final_db_write_authorization: true,
        recommended_next_step: artifact.recommended_next_step,
        next_required_step: artifact.next_required_step,
    };
}

function buildReport(artifact = {}) {
    return `# Data Entrypoint Governance - Phase 5.21 L2V3T

## Scope

- phase=${PHASE}
- phase_name=${PHASE_NAME}
- source_phase=Phase 5.21L2V3S
- no_write=true
- controlled_live_check_performed=${artifact.controlled_live_check_performed}
- network_request_performed=${artifact.network_request_performed}
- db_write_performed=false
- raw_insert_performed=false
- matches_write_performed=false
- matches_external_id_modified=false
- schema_migration_performed=false
- parser_features_training_prediction_performed=false
- browser_proxy_captcha_bypass_performed=false

## Safety Contract

- endpoint investigation result is not an accepted mapping.
- endpoint investigation result is not raw write authorization.
- endpoint investigation result is not baseline acceptance.
- endpoint investigation result is not raw write retry.
- accepted_mapping_count=0.
- raw_write_ready_for_execution=false.
- separate identity mapping acceptance, baseline acceptance, and final DB-write authorization remain required.

## Classification Summary

- analyzed_endpoint_hint_count=${artifact.analyzed_endpoint_hint_count}
- controlled_live_check_performed=${artifact.controlled_live_check_performed}
- checked_target_count=${artifact.checked_target_count}
- previous_endpoint_status=${artifact.previous_endpoint_status}
- new_endpoint_candidate_count=${artifact.new_endpoint_candidate_count}
- precise_detail_endpoint_found=${artifact.precise_detail_endpoint_found}
- endpoint_avoids_slug_reuse=${artifact.endpoint_avoids_slug_reuse}
- endpoint_investigation_result=${artifact.endpoint_investigation_result}
- recommended_strategy=${artifact.recommended_strategy}
- strategy_confidence=${artifact.strategy_confidence}
- requires_followup_implementation=${artifact.requires_followup_implementation}

## Key Findings

- public_api_match_details_status=${artifact.endpoint_hints.find(item => item.endpoint_hint_key === 'api_data_match_details')?.safe_conclusion}
- source_inventory_page_url_extraction_supported=${artifact.evidence_summary?.source_inventory_page_url_extraction_supported}
- manifest_page_url_base_count=${artifact.evidence_summary?.manifest_page_url_base_count}
- l2v3q_missing_pageurl_base_count=${artifact.evidence_summary?.l2v3q_missing_pageurl_base_count}
- l2v3e_shared_page_url_base_pair_count=${artifact.evidence_summary?.l2v3e_shared_page_url_base_pair_count}
- build_data_route_executable_builder_found=${artifact.evidence_summary?.build_data_route_executable_builder_found}

## Questions Answered

1. /api/data/matchDetails?matchId={externalId} is still not a safe public no-write server-side path for this workflow. L2V3S already captured HTTP 403, and this phase found no stronger source-controlled evidence that the public route is currently usable without separate session/browser handling.
2. The repository does contain other detail-route hints: current html_hydration /match/{externalId}, alternate /api/matchDetails, source inventory pageUrl / page_url_base extraction, and a pure Next.js hydration parser.
3. A precise Next.js build-data route is still unknown. The repo has buildId mentions in docs/tests, but no executable runtime builder for a FotMob _next/data detail route was found.
4. Source inventory appears to preserve enough identity metadata in principle to help, because the repo already extracts pageUrl and page_url_base; the current blocker is that the proposal manifest does not retain those fields for the 50 candidate targets.
5. The public API endpoint path should be deprioritized, not accepted. The stronger next move is to enrich source-controlled target metadata rather than keep probing blocked public JSON routes.
6. Any future precise detail request strategy must keep requested_schedule_external_id as the primary identity and fail closed unless observed_detail_external_id === requested_schedule_external_id with compatible date/team/status metadata.
7. Recommended next step: ${artifact.recommended_next_step}

## Next Step

${artifact.recommended_next_step}
`;
}

async function runContinuedDetailEndpointInvestigation(dependencies = {}) {
    const options = {
        controlledLiveCheck: dependencies.controlledLiveCheck === true,
        networkAuthorization: dependencies.networkAuthorization === true,
        maxTargets:
            dependencies.maxTargets === undefined
                ? MAX_CONTROLLED_TARGETS
                : parseInteger(dependencies.maxTargets, MAX_CONTROLLED_TARGETS),
    };
    const optionGate = validateCliOptions({ ...options, unknown: [] });
    if (!optionGate.ok) return { ok: false, status: 2, errors: optionGate.errors };

    const manifest = dependencies.manifest || readJsonFile(MANIFEST_PATH);
    const l2v3qArtifact = dependencies.l2v3qArtifact || readJsonFile(L2V3Q_ARTIFACT_PATH);
    const l2v3rArtifact = dependencies.l2v3rArtifact || readJsonFile(L2V3R_ARTIFACT_PATH);
    const l2v3sArtifact = dependencies.l2v3sArtifact || readJsonFile(L2V3S_ARTIFACT_PATH);
    const inputGate = validateInputs(manifest, l2v3rArtifact, l2v3qArtifact, l2v3sArtifact);
    if (!inputGate.ok) return { ok: false, status: 3, errors: inputGate.errors };

    const sourceFileAnalysis = analyzeSourceFiles(SOURCE_FILES, dependencies);
    const buildDataContext = analyzeBuildDataContext(dependencies);
    const selectedTarget = options.controlledLiveCheck === true ? selectControlledLiveTarget(l2v3sArtifact) : null;
    const controlledResult =
        options.controlledLiveCheck === true && selectedTarget
            ? {
                  checked_targets: [await executeControlledLiveCheck(selectedTarget, dependencies)],
                  stopped_early: true,
                  stop_reason: null,
              }
            : { checked_targets: [], stopped_early: false, stop_reason: null };
    const controlledSummary = summarizeControlledLiveCheck(controlledResult, options.controlledLiveCheck === true);
    const artifact = buildArtifact({
        manifest,
        l2v3qArtifact,
        l2v3rArtifact,
        l2v3sArtifact,
        sourceFileAnalysis,
        buildDataContext,
        controlledSummary,
        generatedAt: dependencies.generatedAt || GENERATED_AT,
    });
    const updatedManifest = updateManifestMetadata(manifest, artifact);
    const report = buildReport(artifact);

    if (dependencies.writeFiles !== false) {
        writeJsonFile(dependencies.artifactOutputPath || ARTIFACT_OUTPUT_PATH, artifact);
        writeTextFile(dependencies.reportOutputPath || REPORT_PATH, report);
        writeJsonFile(dependencies.manifestOutputPath || MANIFEST_PATH, updatedManifest);
    }

    return {
        ok: true,
        status: 0,
        artifact,
        updated_manifest: updatedManifest,
        report,
    };
}

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/pageprops_v2_continued_detail_endpoint_investigation.js --controlled-live-check=no --network-authorization=no --max-targets=0',
        '  node scripts/ops/pageprops_v2_continued_detail_endpoint_investigation.js --controlled-live-check=yes --network-authorization=yes --max-targets=1',
        '',
        'Safety:',
        '  L2V3T is a no-write continued endpoint investigation phase. It never writes DB/raw/matches and never saves or prints full payloads.',
    ].join('\n');
}

async function runCli(argv = process.argv.slice(2), streams = {}) {
    const stdout = streams.stdout || (text => process.stdout.write(text));
    const options = parseArgs(argv);
    if (options.help) {
        stdout(`${usage()}\n`);
        return 0;
    }
    const optionGate = validateCliOptions(options);
    if (!optionGate.ok) {
        stdout(`${JSON.stringify({ ok: false, phase: PHASE, errors: optionGate.errors }, null, 2)}\n`);
        return 2;
    }
    const result = await runContinuedDetailEndpointInvestigation({
        controlledLiveCheck: options.controlledLiveCheck,
        networkAuthorization: options.networkAuthorization,
        maxTargets: options.maxTargets,
        writeFiles: options.writeFiles,
    });
    if (!result.ok) {
        stdout(`${JSON.stringify({ ok: false, phase: PHASE, errors: result.errors }, null, 2)}\n`);
        return result.status;
    }
    stdout(
        `${JSON.stringify(
            {
                ok: true,
                phase: PHASE,
                artifact: ARTIFACT_OUTPUT_PATH,
                report: REPORT_PATH,
                analyzed_endpoint_hint_count: result.artifact.analyzed_endpoint_hint_count,
                controlled_live_check_performed: result.artifact.controlled_live_check_performed,
                checked_target_count: result.artifact.checked_target_count,
                previous_endpoint_status: result.artifact.previous_endpoint_status,
                new_endpoint_candidate_count: result.artifact.new_endpoint_candidate_count,
                precise_detail_endpoint_found: result.artifact.precise_detail_endpoint_found,
                endpoint_avoids_slug_reuse: result.artifact.endpoint_avoids_slug_reuse,
                endpoint_investigation_result: result.artifact.endpoint_investigation_result,
                recommended_strategy: result.artifact.recommended_strategy,
                strategy_confidence: result.artifact.strategy_confidence,
                requires_followup_implementation: result.artifact.requires_followup_implementation,
                raw_write_ready_for_execution: result.artifact.raw_write_ready_for_execution,
                accepted_mapping_count: result.artifact.accepted_mapping_count,
                recommended_next_step: result.artifact.recommended_next_step,
            },
            null,
            2
        )}\n`
    );
    return result.status;
}

module.exports = {
    PHASE,
    PHASE_NAME,
    ARTIFACT_STATUS,
    MANIFEST_PATH,
    L2V3Q_ARTIFACT_PATH,
    L2V3R_ARTIFACT_PATH,
    L2V3S_ARTIFACT_PATH,
    ARTIFACT_OUTPUT_PATH,
    REPORT_PATH,
    PREVIOUS_ENDPOINT_STATUS,
    NEXT_REQUIRED_STEP,
    NEXT_RECOMMENDED_STEP,
    PRECISE_IMPLEMENTATION_STEP,
    PRECISE_IMPLEMENTATION_RECOMMENDATION,
    parseArgs,
    validateCliOptions,
    analyzeSourceFiles,
    analyzeBuildDataContext,
    validateInputs,
    summarizeManifestUrlFields,
    buildEndpointHints,
    buildEvidenceSummary,
    selectControlledLiveTarget,
    executeControlledLiveCheck,
    summarizeControlledLiveCheck,
    buildRecommendedStrategy,
    buildQuestionAnswers,
    buildArtifact,
    updateManifestMetadata,
    buildReport,
    runContinuedDetailEndpointInvestigation,
    runCli,
};

if (require.main === module) {
    runCli()
        .then(status => {
            process.exitCode = status;
        })
        .catch(error => {
            process.stdout.write(`${JSON.stringify({ ok: false, phase: PHASE, error: error.message }, null, 2)}\n`);
            process.exitCode = 1;
        });
}
