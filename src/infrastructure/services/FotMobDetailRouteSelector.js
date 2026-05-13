'use strict';

function createFotMobDetailRouteSelector(dependencies = {}) {
    const {
        TARGET,
        ROUTES,
        validatePreviewInput,
        normalizePreviewInput,
        buildFotMobDetailRoutePlan,
        fetchPreviewBody,
        extractJsonOrHydrationPreview,
        getHeaderValue,
        sha256,
        PHASE,
        NEXT_REQUIRED_PHASE,
    } = dependencies;

    function listOrEmpty(value) {
        return Array.isArray(value) ? value : [];
    }

    function valueOrFallback(value, fallback) {
        return value === null || value === undefined ? fallback : value;
    }

    function buildPlannedRouteAttempt(routePlanItem) {
        return {
            route: routePlanItem.route,
            request_url: routePlanItem.request.url,
            executed: false,
            status: null,
            http_status: null,
            content_type: '',
            parse_ok: false,
            json_parse_ok: false,
            hydration_parse_ok: false,
            hydration_transform_ok: false,
            contains_match_id: false,
            contains_home_team: false,
            contains_away_team: false,
            looks_like_valid_match_detail: false,
            hydration_or_json_markers: [],
            candidate_raw_data_paths: [],
            top_level_keys: [],
            block_signals: [],
            controlled_error: routePlanItem.plan_only ? 'PLAN_ONLY_ROUTE_NOT_EXECUTED' : null,
            body_byte_length: 0,
            body_sha256: sha256(''),
        };
    }

    function buildExecutedRouteAttempt({ route, request, response = {}, body = '', extraction = null, error = null }) {
        const bodyText = String(body || '');
        const httpStatus = Number(response.status || response.statusCode || 0) || null;
        const contentType = getHeaderValue(response.headers, 'content-type');
        const preview =
            extraction ||
            extractJsonOrHydrationPreview(bodyText, contentType, {
                externalId: TARGET.externalId,
                homeTeam: TARGET.homeTeam,
                awayTeam: TARGET.awayTeam,
                httpStatus,
            });
        const controlledError = error
            ? String(error.message || error)
            : preview.block_signals.length > 0
              ? `CONTROLLED_BLOCK_SIGNAL:${preview.block_signals.join(',')}`
              : null;

        return {
            route,
            request_url: request?.url || '',
            final_url: response.url || request?.url || '',
            executed: true,
            status: httpStatus,
            http_status: httpStatus,
            content_type: contentType,
            parse_ok: preview.json_parse_ok || preview.hydration_parse_ok,
            json_parse_ok: preview.json_parse_ok,
            hydration_parse_ok: preview.hydration_parse_ok,
            hydration_transform_ok: preview.hydration_transform_ok,
            contains_match_id: preview.contains_match_id,
            contains_home_team: preview.contains_home_team,
            contains_away_team: preview.contains_away_team,
            looks_like_valid_match_detail: preview.looks_like_valid_match_detail,
            hydration_or_json_markers: preview.hydration_or_json_markers,
            candidate_raw_data_paths: preview.candidate_raw_data_paths,
            top_level_keys: preview.top_level_keys,
            block_signals: preview.block_signals,
            parse_error: preview.parse_error,
            controlled_error: controlledError,
            body_byte_length: Buffer.byteLength(bodyText, 'utf8'),
            body_sha256: sha256(bodyText),
        };
    }

    function shouldStopRouteSelector(attempt) {
        if (!attempt || !attempt.executed) {
            return false;
        }
        if (attempt.looks_like_valid_match_detail) {
            return true;
        }
        return attempt.block_signals.some(signal => /^HTTP_(403|429)$/.test(signal));
    }

    function buildFallbackRoutesPlanned(routePlan, attemptedRoutes) {
        const attemptedRouteNames = new Set(attemptedRoutes.filter(route => route.executed).map(route => route.route));
        return routePlan
            .filter(route => !attemptedRouteNames.has(route.route) || route.plan_only)
            .map(route => ({
                route: route.route,
                request_url: route.request.url,
                executed: false,
                plan_only: true,
                reason: route.plan_only ? 'alternate route is planning-only' : 'not reached by selector',
            }));
    }

    function buildExistingClientIntegrationSummary() {
        return {
            fotmob_api_client_considered: true,
            fotmob_api_client_route_aligned: true,
            fotmob_api_client_imported: false,
            fotmob_strategy_hydration_considered: true,
            next_data_parser_reused: true,
            production_harvester_used: false,
            legacy_backfill_used: false,
            browser_runtime_used: false,
            proxy_runtime_used: false,
        };
    }

    function buildInvalidSelectorResult(validation) {
        return {
            ok: false,
            plan_only: true,
            selected_route: 'none',
            attempted_routes: [],
            fallback_routes_planned: [],
            controlled_error: `INVALID_PREVIEW_INPUT:${validation.errors.join('; ')}`,
            live_network_used: false,
            existing_client_integration: buildExistingClientIntegrationSummary(),
        };
    }

    function canExecuteRoutes(validation, selectorDependencies) {
        return (
            selectorDependencies.allowRouteExecution === true ||
            (validation.value.networkAuthorization === true && validation.value.livePreviewAuthorization === true)
        );
    }

    function buildPlanOnlySelectorResult(routePlan, validation) {
        const attemptedRoutes = routePlan.map(buildPlannedRouteAttempt);
        const controlledError =
            validation.value.networkAuthorization === true
                ? 'LIVE_PREVIEW_BLOCKED:LIVE_PREVIEW_AUTHORIZATION=yes is required for external execution'
                : 'PLAN_ONLY:network authorization is not enabled';

        return {
            ok: false,
            plan_only: true,
            selected_route: 'none',
            attempted_routes: attemptedRoutes,
            fallback_routes_planned: buildFallbackRoutesPlanned(routePlan, []),
            controlled_error: controlledError,
            live_network_used: false,
            existing_client_integration: buildExistingClientIntegrationSummary(),
        };
    }

    function routePlanItemCanExecute(routePlanItem) {
        return routePlanItem.executable === true && routePlanItem.plan_only !== true;
    }

    async function executeRoutePlanItem(routePlanItem, selectorDependencies) {
        try {
            const { response, body } = await fetchPreviewBody(routePlanItem.request, selectorDependencies);
            return buildExecutedRouteAttempt({
                route: routePlanItem.route,
                request: routePlanItem.request,
                response,
                body,
            });
        } catch (error) {
            return buildExecutedRouteAttempt({
                route: routePlanItem.route,
                request: routePlanItem.request,
                response: {
                    status: null,
                    url: routePlanItem.request.url,
                    headers: {},
                },
                body: '',
                error,
            });
        }
    }

    function appendAlternatePlan(routePlan, attemptedRoutes) {
        const plannedAlternate = routePlan.find(route => route.route === ROUTES.ALTERNATE_ROUTE);
        if (plannedAlternate) {
            attemptedRoutes.push(buildPlannedRouteAttempt(plannedAlternate));
        }
    }

    async function executeRoutePlan(routePlan, selectorDependencies) {
        const attemptedRoutes = [];
        let selectedRoute = 'none';

        for (const routePlanItem of routePlan) {
            if (!routePlanItemCanExecute(routePlanItem)) {
                continue;
            }

            const attempt = await executeRoutePlanItem(routePlanItem, selectorDependencies);
            attemptedRoutes.push(attempt);

            if (attempt.looks_like_valid_match_detail) {
                selectedRoute = routePlanItem.route;
                break;
            }
            if (attempt.controlled_error || shouldStopRouteSelector(attempt)) {
                break;
            }
        }

        appendAlternatePlan(routePlan, attemptedRoutes);
        return { attemptedRoutes, selectedRoute };
    }

    function buildExecutedSelectorResult(routePlan, execution, selectorDependencies, validation) {
        const selectedAttempt = execution.attemptedRoutes.find(route => route.route === execution.selectedRoute);
        const lastExecutedAttempt = [...execution.attemptedRoutes].reverse().find(route => route.executed);
        const noPayloadError = execution.selectedRoute === 'none' ? 'NO_VALID_ROUTE_PAYLOAD' : null;

        return {
            ok: Boolean(selectedAttempt?.looks_like_valid_match_detail),
            plan_only: false,
            selected_route: execution.selectedRoute,
            attempted_routes: execution.attemptedRoutes,
            fallback_routes_planned: buildFallbackRoutesPlanned(routePlan, execution.attemptedRoutes),
            controlled_error:
                selectedAttempt?.controlled_error || lastExecutedAttempt?.controlled_error || noPayloadError,
            live_network_used:
                selectorDependencies.allowRouteExecution === true ? false : validation.value.networkAuthorization,
            existing_client_integration: buildExistingClientIntegrationSummary(),
        };
    }

    async function runFotMobDetailRouteSelector(input = {}, selectorDependencies = {}) {
        const validation = validatePreviewInput(input);
        if (!validation.ok) {
            return buildInvalidSelectorResult(validation);
        }

        const routePlan = buildFotMobDetailRoutePlan(validation.value);
        if (!canExecuteRoutes(validation, selectorDependencies)) {
            return buildPlanOnlySelectorResult(routePlan, validation);
        }

        const execution = await executeRoutePlan(routePlan, selectorDependencies);
        return buildExecutedSelectorResult(routePlan, execution, selectorDependencies, validation);
    }

    function findSelectedAttempt(selectorResult = {}) {
        const attemptedRoutes = listOrEmpty(selectorResult.attempted_routes);
        const selectedAttempt =
            attemptedRoutes.find(route => route.route === selectorResult.selected_route) ||
            attemptedRoutes.find(route => route.executed);
        return valueOrFallback(selectedAttempt, valueOrFallback(attemptedRoutes[0], {}));
    }

    function buildRouteSelectorPreviewSummary(input = {}, selectorResult = {}) {
        const normalized = normalizePreviewInput(input);
        const selectedAttempt = findSelectedAttempt(selectorResult);
        const httpStatus = valueOrFallback(selectedAttempt.http_status, valueOrFallback(selectedAttempt.status, null));

        return {
            phase: PHASE,
            preview_only: true,
            plan_only: selectorResult.plan_only === true,
            source: TARGET.source,
            match_id: TARGET.matchId,
            external_id: TARGET.externalId,
            home_team: TARGET.homeTeam,
            away_team: TARGET.awayTeam,
            requested_route: normalized.route,
            route_selector_enabled: true,
            selected_route: valueOrFallback(selectorResult.selected_route, 'none'),
            attempted_routes: listOrEmpty(selectorResult.attempted_routes),
            fallback_routes_planned: listOrEmpty(selectorResult.fallback_routes_planned),
            existing_client_integration: valueOrFallback(
                selectorResult.existing_client_integration,
                buildExistingClientIntegrationSummary()
            ),
            network_authorization_used: normalized.networkAuthorization === true,
            live_preview_authorization_used: normalized.livePreviewAuthorization === true,
            external_network_used: selectorResult.live_network_used === true,
            live_network_used: selectorResult.live_network_used === true,
            request_url: valueOrFallback(selectedAttempt.request_url, ''),
            final_url: valueOrFallback(selectedAttempt.final_url, valueOrFallback(selectedAttempt.request_url, '')),
            http_status: httpStatus,
            ok: selectorResult.ok === true,
            controlled_error: valueOrFallback(
                selectorResult.controlled_error,
                valueOrFallback(selectedAttempt.controlled_error, null)
            ),
            content_type: valueOrFallback(selectedAttempt.content_type, ''),
            body_byte_length: valueOrFallback(selectedAttempt.body_byte_length, 0),
            body_sha256: valueOrFallback(selectedAttempt.body_sha256, sha256('')),
            contains_match_id: selectedAttempt.contains_match_id === true,
            contains_home_team: selectedAttempt.contains_home_team === true,
            contains_away_team: selectedAttempt.contains_away_team === true,
            looks_like_valid_match_detail: selectedAttempt.looks_like_valid_match_detail === true,
            json_parse_ok: selectedAttempt.json_parse_ok === true,
            hydration_parse_ok: selectedAttempt.hydration_parse_ok === true,
            hydration_transform_ok: selectedAttempt.hydration_transform_ok === true,
            hydration_or_json_markers: listOrEmpty(selectedAttempt.hydration_or_json_markers),
            top_level_keys: listOrEmpty(selectedAttempt.top_level_keys),
            candidate_raw_data_paths: listOrEmpty(selectedAttempt.candidate_raw_data_paths),
            raw_match_data_write_allowed: false,
            db_write_allowed: false,
            would_write_raw_match_data: false,
            would_write_db: false,
            would_train: false,
            would_predict: false,
            browser_used: false,
            proxy_used: false,
            body_printed: false,
            body_saved: false,
            next_required_phase: NEXT_REQUIRED_PHASE,
        };
    }

    return {
        buildExistingClientIntegrationSummary,
        runFotMobDetailRouteSelector,
        buildRouteSelectorPreviewSummary,
    };
}

module.exports = {
    createFotMobDetailRouteSelector,
};
