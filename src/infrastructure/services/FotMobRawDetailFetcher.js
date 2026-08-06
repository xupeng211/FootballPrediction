'use strict';

/**
 * FotMobRawDetailFetcher — reusable html_hydration raw detail acquisition.
 *
 * NOT tied to a single external_id. Takes external_id per call.
 * Uses injected fetchFn (default none → fails closed).
 * No DB writes, no browser/proxy, no body save/print.
 */

const crypto = require('node:crypto');
const { reconcileRouteIdentity } = require('./FotMobRouteIdentityReconciler');

const FOTMOB_BASE_URL = 'https://www.fotmob.com';
const HASH_STRATEGY_STABLE_RAW_PAYLOAD_V1 = 'stable_raw_payload_v1';
const METADATA_HASH_EXCLUDED_FIELDS = Object.freeze([
    '_meta.source',
    '_meta.route',
    '_meta.requested_route',
    '_meta.request_url',
    '_meta.final_url',
    '_meta.http_status',
    '_meta.content_type',
    '_meta.body_byte_length',
    '_meta.fetch_body_sha256',
    '_meta.parser',
    '_meta.data_version',
    '_meta.fetched_at',
    '_meta.full_html_body_stored',
    '_meta.http_response_string_stored',
    '_meta.has_stats',
    '_meta.has_lineup',
    '_meta.has_shotmap',
    '_meta.hash_strategy',
    '_meta.data_hash',
    '_meta.match_id_source',
    '_meta.metadata_hash_excluded_fields',
]);

// ══════════════════════════════════════════════════════════════════════════════
// URL builder
// ══════════════════════════════════════════════════════════════════════════════

function buildFotMobMatchUrl(externalId) {
    const id = String(externalId || '').trim();
    if (!id || !/^\d+$/.test(id)) {
        throw new Error(`INVALID_EXTERNAL_ID:${externalId}`);
    }
    const url = new URL(`/match/${id}`, FOTMOB_BASE_URL);
    return url.href;
}

function buildFotMobHtmlHydrationRequest(externalId) {
    return {
        route: 'html_hydration',
        method: 'GET',
        url: buildFotMobMatchUrl(externalId),
        headers: {
            accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'accept-language': 'en-US,en;q=0.9',
            'accept-encoding': 'identity',
            referer: FOTMOB_BASE_URL,
            'user-agent':
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        },
    };
}

// ══════════════════════════════════════════════════════════════════════════════
// Input / dependency validation
// ══════════════════════════════════════════════════════════════════════════════

// eslint-disable-next-line complexity
function validateFetchInput(input = {}) {
    const errors = [];
    const externalId = String(input.externalId || '').trim();
    if (!externalId || !/^\d+$/.test(externalId)) {
        errors.push('externalId is required and must be numeric');
    }
    if (input.matchId && typeof input.matchId !== 'string') {
        errors.push('matchId must be a string if provided');
    }
    const route = String(input.route || 'html_hydration').trim();
    if (route !== 'html_hydration') {
        errors.push('unsupported route: only html_hydration is supported');
    }
    if (input.printBody === true) {
        errors.push('printBody is blocked');
    }
    if (input.saveBody === true) {
        errors.push('saveBody is blocked');
    }
    if (input.retry > 0) {
        errors.push('retry > 0 is blocked');
    }
    if (input.requestUrl !== undefined && input.requestUrl !== null) {
        // Internal Reviewer A (P2): the request URL must always be derived
        // from the numeric external id — a free-form URL override would let
        // a direct caller target an arbitrary host. Rejected fail-closed.
        errors.push('requestUrl is not supported: the request URL is derived from the numeric external id');
    }
    if (input.allowBrowserRuntime === true) {
        errors.push('browser runtime is blocked');
    }
    if (input.allowProxyRuntime === true) {
        errors.push('proxy runtime is blocked');
    }
    return {
        ok: errors.length === 0,
        errors,
        value: {
            source: 'fotmob',
            route: 'html_hydration',
            externalId,
            matchId: input.matchId || null,
            homeTeam: input.homeTeam || null,
            awayTeam: input.awayTeam || null,
            matchDate: input.matchDate || input.kickoffTime || null,
            pageUrlBase: input.pageUrlBase || input.page_url_base || null,
            season: input.season || null,
            dataVersion: input.dataVersion || 'fotmob_html_hyd_v1',
            requestUrl: input.requestUrl || null,
            printBody: false,
            saveBody: false,
            allowBrowserRuntime: false,
            allowProxyRuntime: false,
            retry: 0,
        },
    };
}

function validateFetchDependencies(dependencies = {}) {
    const fetchFn = dependencies.fetchFn;
    if (typeof fetchFn !== 'function') {
        return {
            ok: false,
            error: 'FETCH_DEPENDENCY_MISSING: fetchFn is required and must be a function',
        };
    }
    return { ok: true };
}

// ══════════════════════════════════════════════════════════════════════════════
// JSON / hash helpers
// ══════════════════════════════════════════════════════════════════════════════

function canonicalizeJson(value) {
    if (value === null || typeof value !== 'object') return value;
    if (Array.isArray(value)) return value.map(canonicalizeJson);
    const sorted = {};
    for (const key of Object.keys(value).sort()) {
        // R15-P2-1 (Codex round 15): plain `sorted[key] = ...` would route a
        // legal JSON own key "__proto__" through the legacy __proto__ setter
        // (scalar values silently dropped, object values swapping the
        // prototype), so the canonical hash ignored the field. defineProperty
        // creates an ordinary enumerable data property — output identical
        // for every other key. Shared with the staging artifact hash path
        // (sha256CanonicalJson → canonicalJsonHash → staging projections).
        Object.defineProperty(sorted, key, {
            value: canonicalizeJson(value[key]),
            enumerable: true,
            writable: true,
            configurable: true,
        });
    }
    return sorted;
}

function sha256Text(text) {
    return crypto
        .createHash('sha256')
        .update(String(text || ''))
        .digest('hex');
}

function sha256CanonicalJson(value) {
    return sha256Text(JSON.stringify(canonicalizeJson(value)));
}

function normalizeText(value) {
    return String(value || '').trim();
}

function isNumericId(value) {
    return /^\d+$/.test(normalizeText(value));
}

function isPlainObject(value) {
    return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function jsonClone(value, fallback = {}) {
    if (!isPlainObject(value)) return { ...fallback };
    return JSON.parse(JSON.stringify(value));
}

function buildPayloadSearchText(payload = {}) {
    return JSON.stringify({
        content: payload.content || {},
        general: payload.general || {},
        header: payload.header || {},
        matchId: payload.matchId || null,
    }).toLowerCase();
}

function buildRequestSearchText(context = {}) {
    return `${normalizeText(context.requestUrl)} ${normalizeText(context.finalUrl)}`.toLowerCase();
}

function containsExpectedMarkers({ externalId, homeTeam, awayTeam, payloadText, requestText }) {
    const containsExternalId = !externalId || payloadText.includes(externalId) || requestText.includes(externalId);
    const containsHomeTeam = !homeTeam || payloadText.includes(homeTeam);
    const containsAwayTeam = !awayTeam || payloadText.includes(awayTeam);
    return containsExternalId && containsHomeTeam && containsAwayTeam;
}

// R15-P1 (Codex re-review on 55c450096): the parser derives
// normalized.home_team / away_team from an ORDERED fallback chain —
// `general.<side>Team.name` → `header.teams[0|1].name` →
// `content.lineup.<side>Team.name` → `general.<side>Team.shortName` —
// exactly as FotMobRawParser.extractTeams() does. The FIRST name the
// parser will emit for each side must equal the expected team: a marker
// that appears somewhere in the payload but in the WRONG position (e.g.
// reversed header/lineup teams) or an incomplete chain must fail closed —
// otherwise a page with the right match id but reversed teams would pass
// the loose anywhere-in-text check and persist swapped home/away.
//
// R16-P2 (Codex re-review on 101028e1a): SELECTION must mirror
// FotMobRawParser.firstValue() EXACTLY — it skips only undefined / null /
// the exact empty string. A whitespace-only name (e.g. `general.homeTeam
// .name === '   '`) IS selected by the parser and persisted as a whitespace
// normalized.home_team.name, so it must be SELECTED here too: the
// normalized comparison then fails closed instead of silently skipping to a
// lower-priority source and letting the gate pass.
function extractParserTeamName(payload, side) {
    const general = isPlainObject(payload.general) ? payload.general : {};
    const header = isPlainObject(payload.header) ? payload.header : {};
    const content = isPlainObject(payload.content) ? payload.content : {};
    const lineup = isPlainObject(content.lineup) ? content.lineup : {};
    const teamKey = side === 'home' ? 'homeTeam' : 'awayTeam';
    const headerIdx = side === 'home' ? 0 : 1;
    const fromGeneral = isPlainObject(general[teamKey]) ? general[teamKey] : {};
    const fromHeaderTeams = Array.isArray(header.teams) && isPlainObject(header.teams[headerIdx])
        ? header.teams[headerIdx] : {};
    const fromLineup = isPlainObject(lineup[teamKey]) ? lineup[teamKey] : {};
    const chain = [fromGeneral.name, fromHeaderTeams.name, fromLineup.name, fromGeneral.shortName];
    for (const candidate of chain) {
        if (candidate === undefined || candidate === null || candidate === '') continue;
        // The parser's selected value (a whitespace-only name normalizes to
        // '' here and therefore fails the expected-team comparison below).
        return normalizeText(candidate).toLowerCase();
    }
    return null; // the parser would emit a null name — incomplete marker
}

function expectedTeamMarkersMatch(rawData, expectedHome, expectedAway) {
    const expectedHomeName = normalizeText(expectedHome).toLowerCase();
    const expectedAwayName = normalizeText(expectedAway).toLowerCase();
    if (!expectedHomeName && !expectedAwayName) return true; // nothing to verify
    const parsedHome = extractParserTeamName(rawData, 'home');
    const parsedAway = extractParserTeamName(rawData, 'away');
    if (expectedHomeName && parsedHome === null) return false; // incomplete → fail closed
    if (expectedAwayName && parsedAway === null) return false;
    if (expectedHomeName && parsedHome !== expectedHomeName) return false; // wrong position/order
    if (expectedAwayName && parsedAway !== expectedAwayName) return false;
    return true;
}

/**
 * Extract the TRUSTED observed match id from the RAW hydration document,
 * BEFORE any transformer runs (Codex re-review P3-P1).
 *
 * The NextData transformer is allowed to inject the request-side match id
 * as payload.matchId (apiFormat.matchId = the passed-in externalId), so a
 * post-transform payload.matchId is SYNTHETIC and must never be treated as
 * observed identity. Only raw response fields qualify:
 *
 *   - raw pageProps.general.matchId → source name 'general.matchId'
 *   - raw top-level pageProps.matchId → source name 'matchId'
 *
 * When both raw fields are present and disagree, the resolution is a
 * conflict — fail-closed consumers must not treat either as observed.
 * Returns { observed_match_id, observed_match_id_source, response_derived,
 * conflict } where response_derived is true iff a raw allowlisted field
 * produced the id (untrusted fallbacks are never response-derived).
 */
function extractTrustedObservedMatchIdentity(rawHydration = {}) {
    // __NEXT_DATA__ nests pageProps under props ({ props: { pageProps } });
    // some parsers hand back the pageProps object directly. Both shapes
    // resolve to the same allowlist paths below.
    const raw = isPlainObject(rawHydration) ? rawHydration : {};
    const props = raw.props && isPlainObject(raw.props.pageProps)
        ? raw.props.pageProps
        : (isPlainObject(raw.pageProps) ? raw.pageProps : {});
    const generalMatchId = normalizeText(props.general && props.general.matchId);
    const topLevelMatchId = normalizeText(props.matchId);
    const conflict =
        isNumericId(generalMatchId) && isNumericId(topLevelMatchId) && generalMatchId !== topLevelMatchId;

    if (isNumericId(generalMatchId)) {
        return {
            observed_match_id: generalMatchId,
            // raw path: pageProps.general.matchId (spec section 八 wording)
            observed_match_id_source: 'general.matchId',
            response_derived: true,
            conflict,
        };
    }
    if (isNumericId(topLevelMatchId)) {
        return {
            observed_match_id: topLevelMatchId,
            // raw path: pageProps.matchId (top-level, extracted pre-transform)
            observed_match_id_source: 'matchId',
            response_derived: true,
            conflict,
        };
    }
    return {
        observed_match_id: null,
        observed_match_id_source: 'unresolved',
        response_derived: false,
        conflict,
    };
}

// ══════════════════════════════════════════════════════════════════════════════
// HTML hydration extraction
// ══════════════════════════════════════════════════════════════════════════════

function extractHydrationPayload(html, parserDeps = {}, input = {}) {
    const extractFn = parserDeps.extractFromHtml;
    const transformFn = parserDeps.transformToApiFormat;

    if (typeof extractFn !== 'function' || typeof transformFn !== 'function') {
        return { ok: false, error: 'PARSER_DEPENDENCY_MISSING' };
    }
    if (!html || typeof html !== 'string') {
        return { ok: false, error: 'EMPTY_HTML' };
    }

    let extracted;
    try {
        extracted = extractFn(html);
    } catch (err) {
        return { ok: false, error: `EXTRACT_ERROR:${err.message}` };
    }

    if (!extracted || extracted.success === false || !extracted.data) {
        return { ok: false, error: 'HYDRATION_PARSE_FAILED: no NextData payload found' };
    }

    // R3-P1: capture the trusted observed match id from the RAW hydration
    // BEFORE the transformer runs. The transformer may inject the request
    // side id as payload.matchId (synthetic) — that value must never become
    // the trusted observed identity.
    const trustedIdentity = extractTrustedObservedMatchIdentity(extracted.data);

    let transformed;
    try {
        transformed = transformFn(
            extracted.data,
            normalizeText(input.externalId) || normalizeText(input.matchId) || undefined
        );
    } catch (err) {
        return { ok: false, error: `TRANSFORM_ERROR:${err.message}` };
    }

    if (!transformed || typeof transformed !== 'object') {
        return { ok: false, error: 'TRANSFORM_FAILED: no structured match data' };
    }

    return { ok: true, data: transformed, trustedIdentity };
}

// ══════════════════════════════════════════════════════════════════════════════
// raw_data construction
// ══════════════════════════════════════════════════════════════════════════════

/**
 * Resolve the observed match id for the stable raw payload.
 *
 * R3-P1: the ONLY trusted sources are raw-hydration response fields
 * extracted pre-transform (pageProps.general.matchId / pageProps.matchId),
 * passed in as `trustedIdentity`. The transformed payload's own
 * payload.matchId is SYNTHETIC (the request-side id injected by
 * NextDataParser.transformToApiFormat) and is NEVER trusted.
 *
 * The untrusted input-external-id fallback remains as a marker-checked
 * derivation, but it is not a trusted observed id (consumers must fail
 * closed on it — it is not in TRUSTED_OBSERVED_ID_SOURCES).
 */
function normalizeMatchId(payload = {}, input = {}, context = {}, trustedIdentity = null) {
    const safePayload = isPlainObject(payload) ? payload : {};
    const externalId = normalizeText(input.externalId);
    const homeTeam = normalizeText(input.homeTeam).toLowerCase();
    const awayTeam = normalizeText(input.awayTeam).toLowerCase();
    const payloadText = buildPayloadSearchText(safePayload);
    const requestText = buildRequestSearchText(context);

    // Trusted branch: response-derived id from the raw hydration allowlist,
    // extracted before any transformer could inject a request-side id.
    if (trustedIdentity && isNumericId(trustedIdentity.observed_match_id)) {
        return {
            matchId: trustedIdentity.observed_match_id,
            matchIdSource: trustedIdentity.observed_match_id_source,
            conflict: trustedIdentity.conflict === true,
        };
    }

    // Untrusted fallback: request input id when every expected marker is
    // found in the response. Never a trusted observed identity (P1-4).
    if (
        isNumericId(externalId) &&
        containsExpectedMarkers({
            externalId,
            homeTeam,
            awayTeam,
            payloadText,
            requestText,
        })
    ) {
        return {
            matchId: externalId,
            matchIdSource: 'input_external_id_fallback',
            conflict: false,
        };
    }

    return {
        matchId: null,
        matchIdSource: 'unresolved',
        conflict: false,
    };
}

function buildStableRawPayload(payload = {}, input = {}, context = {}, trustedIdentity = null) {
    const safePayload = isPlainObject(payload) ? payload : {};
    const matchIdResolution = normalizeMatchId(safePayload, input, context, trustedIdentity);

    return {
        content: jsonClone(safePayload.content),
        general: jsonClone(safePayload.general),
        header: jsonClone(safePayload.header),
        matchId: matchIdResolution.matchId,
    };
}

function buildFetchMetadata(meta = {}) {
    return {
        source: 'fotmob',
        route: 'html_hydration',
        requested_route: normalizeText(meta.requestedRoute) || 'html_hydration',
        request_url: meta.requestUrl || null,
        final_url: meta.finalUrl || null,
        http_status: Number(meta.httpStatus || 0),
        content_type: meta.contentType || null,
        body_byte_length: Number(meta.bodyByteLength || 0),
        fetch_body_sha256: meta.bodySha256 || null,
        parser: 'NextDataParser',
        data_version: meta.dataVersion || 'fotmob_html_hyd_v1',
        fetched_at: meta.fetchedAt || null,
        full_html_body_stored: false,
        http_response_string_stored: false,
        has_stats: meta.hasStats === true,
        has_lineup: meta.hasLineup === true,
        has_shotmap: meta.hasShotmap === true,
        hash_strategy: HASH_STRATEGY_STABLE_RAW_PAYLOAD_V1,
        data_hash: meta.dataHash || null,
        match_id_source: meta.matchIdSource || null,
        metadata_hash_excluded_fields: [...METADATA_HASH_EXCLUDED_FIELDS],
    };
}

function buildRawDataFromStablePayload(stablePayload = {}, meta = {}) {
    const safePayload = isPlainObject(stablePayload) ? stablePayload : {};
    return {
        _meta: isPlainObject(meta) ? JSON.parse(JSON.stringify(meta)) : {},
        content: jsonClone(safePayload.content),
        general: jsonClone(safePayload.general),
        header: jsonClone(safePayload.header),
        matchId: normalizeText(safePayload.matchId) || null,
    };
}

function sha256StableRawPayload(stablePayload = {}) {
    return sha256CanonicalJson(stablePayload);
}

function computeRawDetailHashes(stableRawPayload = {}, rawData = {}) {
    const stableHash = sha256StableRawPayload(stableRawPayload);
    return {
        raw_data_hash: stableHash,
        stable_raw_payload_hash: stableHash,
        data_hash: stableHash,
        raw_data_with_meta_hash: sha256CanonicalJson(rawData),
        hash_strategy: HASH_STRATEGY_STABLE_RAW_PAYLOAD_V1,
        metadata_hash_excluded_fields: [...METADATA_HASH_EXCLUDED_FIELDS],
    };
}

function validateCanonicalRawDataShape(rawData = {}) {
    const errors = [];

    if (!isPlainObject(rawData)) {
        return ['raw_data must be a plain object'];
    }

    for (const key of ['_meta', 'content', 'general', 'header', 'matchId']) {
        if (!Object.prototype.hasOwnProperty.call(rawData, key)) {
            errors.push(`raw_data missing ${key}`);
        }
    }

    if (!/^\d+$/.test(normalizeText(rawData.matchId))) {
        errors.push('raw_data.matchId must be numeric');
    }
    if (rawData._meta?.full_html_body_stored !== false) {
        errors.push('raw_data._meta.full_html_body_stored must be false');
    }
    if (rawData._meta?.http_response_string_stored !== false) {
        errors.push('raw_data._meta.http_response_string_stored must be false');
    }

    return errors;
}

function buildRawDataFromTransformedPayload(payload = {}, meta = {}, input = {}, context = {}) {
    const stableRawPayload = buildStableRawPayload(payload, input, context);
    return buildRawDataFromStablePayload(stableRawPayload, meta);
}

function looksLikeValidRawDetail(rawData, input = {}) {
    if (!rawData || typeof rawData !== 'object') return false;
    const externalId = String(input.externalId || '').trim();
    const homeTeam = (input.homeTeam || '').toLowerCase();
    const awayTeam = (input.awayTeam || '').toLowerCase();
    const hasMatchId = isNumericId(rawData.matchId);
    const payloadText = buildPayloadSearchText(rawData);
    const requestText = buildRequestSearchText({
        requestUrl: rawData._meta?.request_url,
        finalUrl: rawData._meta?.final_url,
    });

    return (
        hasMatchId &&
        containsExpectedMarkers({
            externalId,
            homeTeam,
            awayTeam,
            payloadText,
            requestText,
        }) &&
        // R15-P1: the loose anywhere-in-text check is not enough — the
        // ORDERED parser chain must yield the expected teams (fail closed
        // on reversed or incomplete markers).
        expectedTeamMarkersMatch(rawData, homeTeam, awayTeam)
    );
}

function buildFetchRouteIdentity(input = {}, context = {}) {
    return reconcileRouteIdentity({
        requestedScheduleExternalId: input.externalId,
        requestedUrl: context.requestUrl,
        finalUrl: context.finalUrl,
        observedDetailExternalId: context.observedDetailExternalId,
        observedPayload: context.observedPayload,
        requestedHomeTeam: input.homeTeam,
        requestedAwayTeam: input.awayTeam,
        requestedMatchDate: input.matchDate,
        requestedPageUrlBase: input.pageUrlBase,
        requestedSeason: input.season,
        fetchOrParseFailure: context.fetchOrParseFailure === true,
        blockOrCaptcha: context.blockOrCaptcha === true,
    });
}

function isBlockHttpStatus(status) {
    return [403, 429].includes(Number(status || 0));
}

function resolveObservedDetailExternalId(payload = {}, stableRawPayload = {}) {
    const generalMatchId = normalizeText(payload?.general?.matchId);
    if (generalMatchId) return generalMatchId;
    return normalizeText(stableRawPayload?.matchId) || null;
}

// ══════════════════════════════════════════════════════════════════════════════
// Core fetch function
// ══════════════════════════════════════════════════════════════════════════════

/**
 * Fetch FotMob raw match detail via html_hydration.
 *
 * @param {object} input - { externalId, matchId?, homeTeam?, awayTeam?, dataVersion?, requestUrl? }
 * @param {object} dependencies - { fetchFn, now?, parser?, logger? }
 * @returns {Promise<object>} unified fetch result
 */
async function fetchFotMobRawDetail(input = {}, dependencies = {}) {
    const inputValidation = validateFetchInput(input);
    if (!inputValidation.ok) {
        const routeIdentity = buildFetchRouteIdentity(input, { fetchOrParseFailure: true });
        return {
            source: 'fotmob',
            route: 'html_hydration',
            external_id: null,
            match_id: null,
            home_team: null,
            away_team: null,
            request_url: null,
            final_url: null,
            http_status: 0,
            ok: false,
            controlled_error: `INVALID_FETCH_INPUT:${inputValidation.errors.join('; ')}`,
            content_type: null,
            body_byte_length: 0,
            body_sha256: null,
            hydration_parse_ok: false,
            transformed_api_format: false,
            raw_data: null,
            raw_data_hash: null,
            contains_external_id: false,
            contains_home_team: false,
            contains_away_team: false,
            looks_like_valid_match_detail: false,
            body_printed: false,
            body_saved: false,
            browser_used: false,
            proxy_used: false,
            ...routeIdentity,
        };
    }

    const depValidation = validateFetchDependencies(dependencies);
    if (!depValidation.ok) {
        const routeIdentity = buildFetchRouteIdentity(inputValidation.value, { fetchOrParseFailure: true });
        return {
            ...inputValidation.value,
            request_url: null,
            final_url: null,
            http_status: 0,
            ok: false,
            controlled_error: `FETCH_DEPENDENCY_INVALID:${depValidation.error}`,
            content_type: null,
            body_byte_length: 0,
            body_sha256: null,
            hydration_parse_ok: false,
            transformed_api_format: false,
            raw_data: null,
            raw_data_hash: null,
            contains_external_id: false,
            contains_home_team: false,
            contains_away_team: false,
            looks_like_valid_match_detail: false,
            body_printed: false,
            body_saved: false,
            browser_used: false,
            proxy_used: false,
            external_id: inputValidation.value.externalId,
            match_id: inputValidation.value.matchId,
            home_team: inputValidation.value.homeTeam,
            away_team: inputValidation.value.awayTeam,
            ...routeIdentity,
        };
    }

    const fetchFn = dependencies.fetchFn;
    const parser = dependencies.parser || {};
    const now = dependencies.now || (() => new Date().toISOString());
    const v = inputValidation.value;
    const request = buildFotMobHtmlHydrationRequest(v.externalId);
    const requestUrl = request.url;
    const fetchedAt = now();

    let response;
    let body = '';

    try {
        response = await fetchFn(requestUrl, {
            method: request.method,
            headers: request.headers,
            redirect: 'follow',
        });
        body = typeof response.text === 'function' ? await response.text() : '';
    } catch (err) {
        const routeIdentity = buildFetchRouteIdentity(v, {
            requestUrl,
            finalUrl: requestUrl,
            fetchOrParseFailure: true,
        });
        return {
            source: 'fotmob',
            route: 'html_hydration',
            external_id: v.externalId,
            match_id: v.matchId,
            home_team: v.homeTeam,
            away_team: v.awayTeam,
            request_url: requestUrl,
            final_url: requestUrl,
            http_status: 0,
            ok: false,
            controlled_error: `FETCH_ERROR:${err.message}`,
            content_type: null,
            body_byte_length: 0,
            body_sha256: null,
            hydration_parse_ok: false,
            transformed_api_format: false,
            raw_data: null,
            raw_data_hash: null,
            contains_external_id: false,
            contains_home_team: false,
            contains_away_team: false,
            looks_like_valid_match_detail: false,
            body_printed: false,
            body_saved: false,
            browser_used: false,
            proxy_used: false,
            ...routeIdentity,
        };
    }

    const httpStatus = response ? response.status : 0;
    const finalUrl = (response && response.url) || requestUrl;
    const contentType =
        response && typeof response.headers.get === 'function' ? response.headers.get('content-type') || '' : '';
    const bodyByteLength = Buffer.byteLength(body, 'utf8');
    const bodySha256 = sha256Text(body);
    const fetchedBodySha256 = bodySha256;

    const extraction = extractHydrationPayload(body, parser, v);

    if (!extraction.ok) {
        const routeIdentity = buildFetchRouteIdentity(v, {
            requestUrl,
            finalUrl,
            fetchOrParseFailure: true,
            blockOrCaptcha: isBlockHttpStatus(httpStatus),
        });
        return {
            source: 'fotmob',
            route: 'html_hydration',
            external_id: v.externalId,
            match_id: v.matchId,
            home_team: v.homeTeam,
            away_team: v.awayTeam,
            request_url: requestUrl,
            final_url: finalUrl,
            http_status: httpStatus,
            ok: false,
            controlled_error: extraction.error,
            content_type: contentType,
            body_byte_length: bodyByteLength,
            body_sha256: bodySha256,
            hydration_parse_ok: false,
            transformed_api_format: false,
            raw_data: null,
            raw_data_hash: null,
            contains_external_id: false,
            contains_home_team: false,
            contains_away_team: false,
            looks_like_valid_match_detail: false,
            body_printed: false,
            body_saved: false,
            browser_used: false,
            proxy_used: false,
            ...routeIdentity,
        };
    }

    // R3-P1: the trusted observed id comes from the raw hydration (captured
    // pre-transform in extractHydrationPayload), never from the synthetic
    // post-transform payload.matchId.
    const matchIdResolution = normalizeMatchId(extraction.data, v, { requestUrl, finalUrl }, extraction.trustedIdentity);
    const stableRawPayload = buildStableRawPayload(extraction.data, v, { requestUrl, finalUrl }, extraction.trustedIdentity);
    const stableHash = sha256StableRawPayload(stableRawPayload);
    const meta = buildFetchMetadata({
        requestedRoute: v.route,
        requestUrl,
        finalUrl,
        httpStatus,
        contentType,
        bodyByteLength,
        bodySha256: fetchedBodySha256,
        dataVersion: v.dataVersion,
        fetchedAt,
        hasStats: Boolean(stableRawPayload.content?.stats),
        hasLineup: Boolean(stableRawPayload.content?.lineup),
        hasShotmap: Boolean(stableRawPayload.content?.shotmap),
        dataHash: stableHash,
        matchIdSource: matchIdResolution.matchIdSource,
    });

    const rawData = buildRawDataFromStablePayload(stableRawPayload, meta);
    const hashInfo = computeRawDetailHashes(stableRawPayload, rawData);
    const valid = looksLikeValidRawDetail(rawData, v);
    const observedDetailExternalId = resolveObservedDetailExternalId(extraction.data, stableRawPayload);
    const routeIdentity = buildFetchRouteIdentity(v, {
        requestUrl,
        finalUrl,
        observedDetailExternalId,
        observedPayload: extraction.data,
    });

    return {
        source: 'fotmob',
        route: 'html_hydration',
        external_id: v.externalId,
        match_id: v.matchId,
        home_team: v.homeTeam,
        away_team: v.awayTeam,
        request_url: requestUrl,
        final_url: finalUrl,
        http_status: httpStatus,
        ok: true,
        content_type: contentType,
        body_byte_length: bodyByteLength,
        body_sha256: bodySha256,
        hydration_parse_ok: true,
        transformed_api_format: true,
        stable_raw_payload: stableRawPayload,
        stable_raw_payload_hash: hashInfo.stable_raw_payload_hash,
        raw_data: rawData,
        raw_data_hash: hashInfo.raw_data_hash,
        raw_data_with_meta_hash: hashInfo.raw_data_with_meta_hash,
        data_hash: hashInfo.data_hash,
        hash_strategy: hashInfo.hash_strategy,
        metadata_hash_excluded_fields: hashInfo.metadata_hash_excluded_fields,
        match_id_source: matchIdResolution.matchIdSource,
        observed_match_id_conflict: matchIdResolution.conflict === true,
        observed_match_id_response_derived:
            matchIdResolution.matchIdSource === 'general.matchId' ||
            matchIdResolution.matchIdSource === 'matchId',
        contains_external_id: valid,
        contains_home_team: valid,
        contains_away_team: valid,
        looks_like_valid_match_detail: valid,
        body_printed: false,
        body_saved: false,
        browser_used: false,
        proxy_used: false,
        ...routeIdentity,
    };
}

module.exports = {
    buildFotMobMatchUrl,
    buildFotMobHtmlHydrationRequest,
    validateFetchInput,
    validateFetchDependencies,
    canonicalizeJson,
    sha256Text,
    sha256CanonicalJson,
    HASH_STRATEGY_STABLE_RAW_PAYLOAD_V1,
    METADATA_HASH_EXCLUDED_FIELDS,
    extractHydrationPayload,
    extractTrustedObservedMatchIdentity,
    normalizeMatchId,
    buildStableRawPayload,
    buildFetchMetadata,
    buildRawDataFromStablePayload,
    sha256StableRawPayload,
    computeRawDetailHashes,
    validateCanonicalRawDataShape,
    buildRawDataFromTransformedPayload,
    looksLikeValidRawDetail,
    fetchFotMobRawDetail,
};
