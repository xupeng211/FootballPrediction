'use strict';

const IDENTITY_MATCH = 'identity_match';
const REQUESTED_OBSERVED_MISMATCH = 'requested_vs_observed_external_id_mismatch';
const UNRESOLVED_MAPPING = 'unresolved_schedule_detail_mapping';
const ACCEPTED_MAPPING_REQUIRED = 'accepted_schedule_detail_mapping_required';
const FETCH_OR_PARSE_FAILURE = 'fetch_or_parse_failure';
const BLOCK_OR_CAPTCHA = 'block_or_captcha';
const METADATA_TARGET_MISMATCH = 'metadata_target_mismatch';

function normalizeText(value) {
    return String(value ?? '').trim();
}

function normalizeLower(value) {
    return normalizeText(value).toLowerCase();
}

function normalizeId(value) {
    const text = normalizeText(value);
    return /^\d+$/.test(text) ? text : null;
}

function isPlainObject(value) {
    return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function firstText(...values) {
    for (const value of values) {
        const text = normalizeText(value);
        if (text) return text;
    }
    return null;
}

function firstId(...values) {
    for (const value of values) {
        const id = normalizeId(value);
        if (id) return id;
    }
    return null;
}

function normalizePageUrlBase(value) {
    const text = normalizeText(value);
    if (!text) return null;

    try {
        const parsed = new URL(text, 'https://www.fotmob.com');
        return normalizeText(parsed.pathname).replace(/\/+$/, '') || '/';
    } catch {
        const withoutHash = text.split('#')[0].split('?')[0].trim();
        return withoutHash.replace(/\/+$/, '') || null;
    }
}

function normalizeTeam(value) {
    return normalizeLower(value).replace(/\s+/g, ' ');
}

function normalizeDateOnly(value) {
    const text = normalizeText(value);
    if (!text) return null;
    const parsed = new Date(text);
    if (!Number.isNaN(parsed.getTime())) return parsed.toISOString().slice(0, 10);
    const match = text.match(/\d{4}-\d{2}-\d{2}/);
    return match ? match[0] : text;
}

function normalizeStatus(value) {
    if (isPlainObject(value)) {
        return firstText(value.type, value.status, value.reason, value.long, value.short);
    }
    return normalizeLower(value);
}

function extractTeamName(value) {
    if (isPlainObject(value)) {
        return firstText(value.name, value.shortName, value.longName, value.fullName);
    }
    return firstText(value);
}

function extractHeaderTeam(pageProps = {}, index) {
    const teams = pageProps.header?.teams || pageProps.header?.participants || [];
    if (!Array.isArray(teams)) return null;
    return extractTeamName(teams[index]);
}

function extractObservedMetadata(input = {}) {
    const pageProps = isPlainObject(input.pageProps) ? input.pageProps : {};
    const observedPayload = isPlainObject(input.observedPayload) ? input.observedPayload : {};
    const general = pageProps.general || observedPayload.general || {};
    const header = pageProps.header || observedPayload.header || {};

    return {
        observed_detail_external_id: firstId(
            input.observedDetailExternalId,
            observedPayload.matchId,
            observedPayload.match_id,
            general.matchId,
            general.match_id,
            pageProps.matchId,
            pageProps.match_id
        ),
        observed_page_url_base: normalizePageUrlBase(
            firstText(
                input.observedPageUrlBase,
                input.canonicalPageUrl,
                input.finalUrl,
                general.pageUrl,
                general.pageURL,
                general.canonicalUrl,
                pageProps.pageUrl,
                pageProps.canonicalUrl
            )
        ),
        observed_home_team: firstText(
            input.observedHomeTeam,
            extractTeamName(general.homeTeam),
            extractHeaderTeam(pageProps, 0),
            extractTeamName(header.homeTeam)
        ),
        observed_away_team: firstText(
            input.observedAwayTeam,
            extractTeamName(general.awayTeam),
            extractHeaderTeam(pageProps, 1),
            extractTeamName(header.awayTeam)
        ),
        observed_match_date: firstText(
            input.observedMatchDate,
            general.matchTimeUTC,
            general.matchDate,
            header.matchTimeUTC,
            header.utcTime,
            header.status?.utcTime
        ),
        observed_status: firstText(
            input.observedStatus,
            normalizeStatus(general.status),
            normalizeStatus(header.status)
        ),
    };
}

function extractRequestedMetadata(input = {}) {
    const target = isPlainObject(input.target) ? input.target : {};
    return {
        requested_schedule_external_id: firstId(
            input.requestedScheduleExternalId,
            input.externalId,
            input.external_id,
            target.external_id
        ),
        requested_url: firstText(input.requestedUrl, input.request_url, target.request_url),
        requested_page_url_base: normalizePageUrlBase(
            firstText(
                input.requestedPageUrlBase,
                input.sourceInventoryPageUrlBase,
                input.manifestPageUrlBase,
                target.page_url_base,
                target.source_inventory_page_url_base,
                target.manifest_page_url_base
            )
        ),
        requested_home_team: firstText(input.requestedHomeTeam, target.home_team, target.homeTeam),
        requested_away_team: firstText(input.requestedAwayTeam, target.away_team, target.awayTeam),
        requested_match_date: firstText(input.requestedMatchDate, target.match_date, target.kickoff_time, target.date),
        requested_status: firstText(input.requestedStatus, target.status),
    };
}

function comparePageUrlBases(requestedBase, observedBase) {
    if (!requestedBase || !observedBase) return 'missing_page_url_base';
    return requestedBase === observedBase ? 'match' : 'mismatch';
}

function buildTeamDateStatusFlags(requested = {}, observed = {}) {
    const requestedHome = normalizeTeam(requested.requested_home_team);
    const requestedAway = normalizeTeam(requested.requested_away_team);
    const observedHome = normalizeTeam(observed.observed_home_team);
    const observedAway = normalizeTeam(observed.observed_away_team);
    const teamsKnown = Boolean(requestedHome && requestedAway && observedHome && observedAway);

    const requestedDate = normalizeDateOnly(requested.requested_match_date);
    const observedDate = normalizeDateOnly(observed.observed_match_date);
    const dateKnown = Boolean(requestedDate && observedDate);

    const requestedStatus = normalizeStatus(requested.requested_status);
    const observedStatus = normalizeStatus(observed.observed_status);
    const statusKnown = Boolean(requestedStatus && observedStatus);

    return {
        teamsMatch: teamsKnown ? requestedHome === observedHome && requestedAway === observedAway : null,
        dateMatch: dateKnown ? requestedDate === observedDate : null,
        statusMatch: statusKnown ? requestedStatus === observedStatus : null,
    };
}

function compareTeamDateStatus(requested = {}, observed = {}) {
    const { teamsMatch, dateMatch, statusMatch } = buildTeamDateStatusFlags(requested, observed);
    if (teamsMatch === true && dateMatch === true && (statusMatch === true || statusMatch === null)) {
        return 'compatible';
    }
    const failedParts = [
        ['team', teamsMatch],
        ['date', dateMatch],
        ['status', statusMatch],
    ]
        .filter(([, matched]) => matched === false)
        .map(([name]) => name);
    if (failedParts.length === 0) return 'unknown';
    if (failedParts.length === 3) return 'team_date_status_mismatch';
    if (failedParts.length === 2) return `${failedParts[0]}_and_${failedParts[1]}_mismatch`;
    if (failedParts[0] === 'team') return 'team_mismatch';
    if (failedParts[0] === 'date') return 'date_mismatch';
    if (failedParts[0] === 'status') return 'status_mismatch';
    return 'unknown';
}

function inferMappingConfidence({ externalIdStatus, pageUrlStatus, teamDateStatus }) {
    if (externalIdStatus === IDENTITY_MATCH) return 'high';
    if (externalIdStatus !== REQUESTED_OBSERVED_MISMATCH) return 'unknown';
    if (pageUrlStatus === 'match' && teamDateStatus === 'compatible') return 'medium';
    if (pageUrlStatus === 'match') return 'medium';
    if (pageUrlStatus === 'missing_page_url_base' || teamDateStatus === 'unknown') return 'unknown';
    return 'low';
}

function buildSafetyBlockers({
    input = {},
    requested = {},
    observed = {},
    externalIdStatus,
    pageUrlStatus,
    teamDateStatus,
}) {
    const blockers = new Set();
    const blockMarkers = Array.isArray(input.blockMarkers) ? input.blockMarkers : [];
    const addWhen = (condition, blocker) => {
        if (condition) blockers.add(blocker);
    };
    addWhen(blockMarkers.length > 0 || input.blockOrCaptcha === true, BLOCK_OR_CAPTCHA);
    addWhen(input.fetchOrParseFailure === true, FETCH_OR_PARSE_FAILURE);
    addWhen(!requested.requested_schedule_external_id, 'missing_requested_schedule_external_id');
    addWhen(!observed.observed_detail_external_id, 'missing_observed_detail_external_id');
    if (externalIdStatus === REQUESTED_OBSERVED_MISMATCH) {
        blockers.add(ACCEPTED_MAPPING_REQUIRED);
        addWhen(input.acceptedIdentityMappingPresent !== true, 'accepted_identity_mapping_missing');
        addWhen(
            input.proposalMappingPresent === true || input.proposalOnlyMapping === true,
            'proposal_only_mapping_not_accepted'
        );
    }
    addWhen(pageUrlStatus === 'missing_page_url_base', 'missing_page_url_base');
    addWhen(pageUrlStatus === 'mismatch', 'page_url_base_mismatch');
    addWhen(teamDateStatus !== 'compatible' && teamDateStatus !== 'unknown', 'team_date_status_mismatch');
    addWhen(input.multipleDetailIdsForSameScheduleId === true, 'multiple_detail_ids_for_same_schedule_id');
    addWhen(input.multipleScheduleIdsForSameDetailId === true, 'multiple_schedule_ids_for_same_detail_id');
    addWhen(input.metadataTargetMismatch === true, METADATA_TARGET_MISMATCH);
    return [...blockers].sort();
}

function reconcileRouteIdentity(input = {}) {
    const requested = extractRequestedMetadata(input);
    const observed = extractObservedMetadata(input);
    const requestedId = requested.requested_schedule_external_id;
    const observedId = observed.observed_detail_external_id;

    let externalIdStatus = 'unknown';
    if (requestedId && observedId && requestedId === observedId) externalIdStatus = IDENTITY_MATCH;
    if (requestedId && observedId && requestedId !== observedId) externalIdStatus = REQUESTED_OBSERVED_MISMATCH;

    const pageUrlStatus = comparePageUrlBases(requested.requested_page_url_base, observed.observed_page_url_base);
    const teamDateStatus = compareTeamDateStatus(requested, observed);
    const mappingConfidence = inferMappingConfidence({
        externalIdStatus,
        pageUrlStatus,
        teamDateStatus,
    });
    const safetyBlockers = buildSafetyBlockers({
        input,
        requested,
        observed,
        externalIdStatus,
        pageUrlStatus,
        teamDateStatus,
    });

    let canonicalIdentityStatus = externalIdStatus;
    let identityReconciliationStatus = externalIdStatus;
    if (input.fetchOrParseFailure === true) {
        canonicalIdentityStatus = FETCH_OR_PARSE_FAILURE;
        identityReconciliationStatus = FETCH_OR_PARSE_FAILURE;
    } else if (input.blockOrCaptcha === true || (Array.isArray(input.blockMarkers) && input.blockMarkers.length > 0)) {
        canonicalIdentityStatus = BLOCK_OR_CAPTCHA;
        identityReconciliationStatus = BLOCK_OR_CAPTCHA;
    } else if (externalIdStatus === REQUESTED_OBSERVED_MISMATCH) {
        canonicalIdentityStatus = REQUESTED_OBSERVED_MISMATCH;
        identityReconciliationStatus =
            input.acceptedIdentityMappingPresent === true ? 'accepted_schedule_detail_mapping' : UNRESOLVED_MAPPING;
    }

    const rawWriteBlocked =
        identityReconciliationStatus !== IDENTITY_MATCH &&
        identityReconciliationStatus !== 'accepted_schedule_detail_mapping';

    return {
        requested_schedule_external_id: requestedId,
        observed_detail_external_id: observedId,
        requested_url: requested.requested_url,
        requested_page_url_base: requested.requested_page_url_base,
        observed_page_url_base: observed.observed_page_url_base,
        page_url_base_match_status: pageUrlStatus,
        team_date_status_match_status: teamDateStatus,
        schedule_external_id_vs_detail_external_id_status: externalIdStatus,
        canonical_identity_status: canonicalIdentityStatus,
        identity_reconciliation_status: identityReconciliationStatus,
        mapping_confidence: mappingConfidence,
        accepted_identity_mapping_present: input.acceptedIdentityMappingPresent === true,
        proposal_mapping_used_for_raw_write: false,
        raw_write_blocked: rawWriteBlocked,
        accepted_identity_mapping_required: rawWriteBlocked && externalIdStatus === REQUESTED_OBSERVED_MISMATCH,
        safety_blockers: safetyBlockers,
    };
}

function assertRawWriteIdentityGate(reconciliation = {}) {
    const blockers = Array.isArray(reconciliation.safety_blockers) ? reconciliation.safety_blockers : [];
    const ok =
        reconciliation.raw_write_blocked !== true &&
        reconciliation.proposal_mapping_used_for_raw_write !== true &&
        !blockers.includes('proposal_only_mapping_not_accepted') &&
        !blockers.includes('accepted_identity_mapping_missing');
    return {
        ok,
        blocked_reason: ok ? null : 'ROUTE_IDENTITY_GATE_BLOCKED',
        transaction_began: false,
        inserted_raw_match_data_count: 0,
        safety_blockers: blockers,
    };
}

module.exports = {
    IDENTITY_MATCH,
    REQUESTED_OBSERVED_MISMATCH,
    UNRESOLVED_MAPPING,
    ACCEPTED_MAPPING_REQUIRED,
    FETCH_OR_PARSE_FAILURE,
    BLOCK_OR_CAPTCHA,
    METADATA_TARGET_MISMATCH,
    normalizePageUrlBase,
    normalizeDateOnly,
    extractRequestedMetadata,
    extractObservedMetadata,
    compareTeamDateStatus,
    reconcileRouteIdentity,
    assertRawWriteIdentityGate,
};
