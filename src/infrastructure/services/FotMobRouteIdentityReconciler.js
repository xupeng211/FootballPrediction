'use strict';
/* eslint-disable complexity, max-lines */

const IDENTITY_MATCH = 'identity_match';
const REQUESTED_OBSERVED_MISMATCH = 'requested_vs_observed_external_id_mismatch';
const UNRESOLVED_MAPPING = 'unresolved_schedule_detail_mapping';
const ACCEPTED_MAPPING_REQUIRED = 'accepted_schedule_detail_mapping_required';
const FETCH_OR_PARSE_FAILURE = 'fetch_or_parse_failure';
const BLOCK_OR_CAPTCHA = 'block_or_captcha';
const METADATA_TARGET_MISMATCH = 'metadata_target_mismatch';
const DATE_MATCH = 'date_match';
const SAME_UTC_DAY = 'same_utc_day';
const TIMEZONE_ONLY_MISMATCH = 'timezone_only_mismatch';
const POSTPONED_OR_RESCHEDULED_EXPLAINED = 'postponed_or_rescheduled_explained';
const REVERSE_FIXTURE_DETECTED = 'reverse_fixture_detected';
const CROSS_SEASON_SLUG_REUSE = 'cross_season_slug_reuse';
const UNRESOLVED_LARGE_GAP = 'unresolved_large_gap';
const UNKNOWN_DATE_COMPATIBILITY = 'unknown';
const LARGE_DATE_GAP_DAYS = 30;
const BLOCKED_ROUTE_IDENTITY_STRATEGY = 'blocked_until_reaccepted_identity_contract';
const ACCEPTED_DETAIL_ROUTE_IDENTITY_STRATEGY = 'accepted_detail_external_id';
const BLOCKED_CANONICAL_IDENTITY_SOURCE = 'none_until_reaccepted_mapping_baseline';
const REACCEPTED_CANONICAL_IDENTITY_SOURCE = 'reaccepted_mapping_baseline';
const DETAIL_IDENTITY_SOURCE_URL_HASH_FRAGMENT = 'url_hash_fragment';

// ADG9: Strict fixture identity guard
const FIXTURE_IDENTITY_GUARD_PASSED = 'passed';
const FIXTURE_IDENTITY_GUARD_BLOCKED = 'blocked';
const STRICT_DATE_TOLERANCE_DAYS = 1;
const AUDIT_CLASSIFICATION_CORRECT_MAPPING = 'correct_mapping';
const AUDIT_CLASSIFICATION_REVERSE_FIXTURE_MAPPING_ERROR = 'reverse_fixture_mapping_error';
const AUDIT_CLASSIFICATION_HOME_AWAY_INVERSION = 'home_away_inversion';
const AUDIT_CLASSIFICATION_SAME_TEAM_PAIR_WRONG_LEG = 'same_team_pair_wrong_leg';
const AUDIT_CLASSIFICATION_DATE_MISMATCH = 'date_mismatch';
const AUDIT_CLASSIFICATION_COMPETITION_MISMATCH = 'competition_mismatch';
const AUDIT_CLASSIFICATION_SUSPENDED_REFERENCE_STILL_BLOCKED = 'suspended_reference_still_blocked';
const AUDIT_CLASSIFICATION_INSUFFICIENT_EVIDENCE = 'insufficient_source_inventory_evidence';

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

function firstBooleanTrue(...values) {
    return values.some(value => value === true || normalizeLower(value) === 'true');
}

function statusMatches(value, pattern) {
    return pattern.test(normalizeLower(value));
}

function isSuspendedEffectiveStatus(value) {
    return statusMatches(value, /suspended|blocked_or_superseded|invalidated_for_current_write_plan/);
}

function isReacceptedEffectiveStatus(value) {
    return statusMatches(value, /re[-_]?accept|accepted_after_re[-_]?accept|completed_re[-_]?accept/);
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

function parseDateInfo(value) {
    const text = normalizeText(value);
    if (!text) return { ok: false, reason: 'missing', text: null };
    const parsed = new Date(text);
    if (Number.isNaN(parsed.getTime())) return { ok: false, reason: 'invalid', text };
    const literalDate = text.match(/\d{4}-\d{2}-\d{2}/)?.[0] || null;
    return {
        ok: true,
        text,
        ms: parsed.getTime(),
        utc_date: parsed.toISOString().slice(0, 10),
        literal_date: literalDate,
    };
}

function normalizeSeason(value) {
    const text = normalizeText(value);
    if (!text) return null;
    const compact = text.replace(/[^0-9]/g, '');
    if (/^\d{8}$/.test(compact)) return `${compact.slice(0, 4)}/${compact.slice(4, 8)}`;
    const match = text.match(/(\d{4})\D+(\d{4})/);
    if (match) return `${match[1]}/${match[2]}`;
    return text;
}

function seasonFromDateInfo(dateInfo) {
    if (!dateInfo?.ok) return null;
    const date = new Date(dateInfo.ms);
    const year = date.getUTCFullYear();
    const month = date.getUTCMonth() + 1;
    return month >= 7 ? `${year}/${year + 1}` : `${year - 1}/${year}`;
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
                general.pageUrl,
                general.pageURL,
                general.canonicalUrl,
                pageProps.pageUrl,
                pageProps.canonicalUrl,
                input.canonicalPageUrl,
                input.finalUrl
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
        observed_season: normalizeSeason(
            firstText(
                input.observedSeason,
                general.season,
                general.leagueSeason,
                general.parentLeagueSeason,
                pageProps.season,
                pageProps.leagueSeason
            )
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
        requested_detail_external_id: firstId(
            input.requestedDetailExternalId,
            input.recaptureExpectedIdentity,
            input.acceptedDetailExternalId,
            input.accepted_detail_external_id,
            target.accepted_detail_external_id,
            target.recapture_expected_identity
        ),
        requested_schedule_external_id: firstId(
            input.requestedScheduleExternalId,
            input.scheduleExternalId,
            input.schedule_external_id,
            input.externalId,
            input.external_id,
            target.schedule_external_id,
            target.external_id
        ),
        requested_url: firstText(input.requestedUrl, input.request_url, target.source_page_url, target.request_url),
        requested_page_url_base: normalizePageUrlBase(
            firstText(
                input.requestedPageUrlBase,
                input.sourceInventoryPageUrlBase,
                input.manifestPageUrlBase,
                target.source_page_url_base,
                target.page_url_base,
                target.source_inventory_page_url_base,
                target.manifest_page_url_base
            )
        ),
        requested_home_team: firstText(input.requestedHomeTeam, target.home_team, target.homeTeam),
        requested_away_team: firstText(input.requestedAwayTeam, target.away_team, target.awayTeam),
        requested_match_date: firstText(input.requestedMatchDate, target.match_date, target.kickoff_time, target.date),
        requested_season: normalizeSeason(
            firstText(input.requestedSeason, target.season, target.league_season, target.leagueSeason)
        ),
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

function hasExplicitRescheduleEvidence(input = {}) {
    if (
        input.postponedOrRescheduledEvidence === true ||
        input.rescheduleEvidence === true ||
        input.explicitRescheduleEvidence === true
    ) {
        return true;
    }
    const evidence = firstText(
        input.postponedOrRescheduledEvidence,
        input.rescheduleEvidence,
        input.explicitRescheduleEvidence,
        input.dateMismatchExplanation,
        input.dateMismatchEvidence
    );
    if (!evidence) return false;
    return /postpon|reschedul|human_review|explicit/i.test(evidence);
}

function buildTeamPairEvidence(requested = {}, observed = {}) {
    const requestedHome = normalizeTeam(requested.requested_home_team);
    const requestedAway = normalizeTeam(requested.requested_away_team);
    const observedHome = normalizeTeam(observed.observed_home_team);
    const observedAway = normalizeTeam(observed.observed_away_team);
    const teamsKnown = Boolean(requestedHome && requestedAway && observedHome && observedAway);
    const sameOrder = teamsKnown && requestedHome === observedHome && requestedAway === observedAway;
    const reversedOrder = teamsKnown && requestedHome === observedAway && requestedAway === observedHome;
    return {
        teams_known: teamsKnown,
        same_order: sameOrder,
        reversed_home_away: reversedOrder,
        same_pair_any_order: sameOrder || reversedOrder,
    };
}

function buildDateCompatibilityResult(status, details = {}) {
    const hardBlockStatuses = new Set([
        REVERSE_FIXTURE_DETECTED,
        CROSS_SEASON_SLUG_REUSE,
        UNRESOLVED_LARGE_GAP,
        UNKNOWN_DATE_COMPATIBILITY,
    ]);
    return {
        date_compatibility_status: status,
        status,
        positive_evidence: status === DATE_MATCH || status === SAME_UTC_DAY,
        review_required:
            status === TIMEZONE_ONLY_MISMATCH ||
            status === POSTPONED_OR_RESCHEDULED_EXPLAINED ||
            hardBlockStatuses.has(status),
        blocks_identity_mapping_acceptance: hardBlockStatuses.has(status),
        blocks_raw_write: hardBlockStatuses.has(status),
        ...details,
    };
}

function buildSeasonContext(requested = {}, observed = {}, requestedDate = {}, observedDate = {}) {
    const requestedSeason = normalizeSeason(requested.requested_season) || seasonFromDateInfo(requestedDate);
    const observedSeason = normalizeSeason(observed.observed_season) || seasonFromDateInfo(observedDate);
    const seasonKnown = Boolean(requestedSeason && observedSeason);
    const sameSeason = seasonKnown ? requestedSeason === observedSeason : null;
    return { requestedSeason, observedSeason, seasonKnown, sameSeason };
}

function buildDateGap(requestedDate = {}, observedDate = {}) {
    if (!requestedDate.ok || !observedDate.ok) {
        return { dateGapHours: null, dateGapDays: null, largeDateGap: false };
    }
    const dateGapHours = Math.abs(observedDate.ms - requestedDate.ms) / 36e5;
    const dateGapDays = dateGapHours === null ? null : dateGapHours / 24;
    const largeDateGap = dateGapDays !== null && dateGapDays > LARGE_DATE_GAP_DAYS;
    return { dateGapHours, dateGapDays, largeDateGap };
}

function buildDateCompatibilityBaseDetails(context = {}) {
    const { requestedDate, observedDate, seasonContext, dateGap, teamEvidence, pageUrlStatus } = context;
    return {
        requested_date_valid: requestedDate.ok,
        observed_date_valid: observedDate.ok,
        requested_date_error: requestedDate.ok ? null : requestedDate.reason,
        observed_date_error: observedDate.ok ? null : observedDate.reason,
        requested_utc_date: requestedDate.utc_date || null,
        observed_utc_date: observedDate.utc_date || null,
        requested_season: seasonContext.requestedSeason,
        observed_season: seasonContext.observedSeason,
        same_season: seasonContext.sameSeason,
        date_gap_hours: dateGap.dateGapHours === null ? null : Number(dateGap.dateGapHours.toFixed(3)),
        date_gap_days: dateGap.dateGapDays === null ? null : Number(dateGap.dateGapDays.toFixed(3)),
        same_pair_any_order: teamEvidence.same_pair_any_order,
        reversed_home_away: teamEvidence.reversed_home_away,
        page_url_base_match_status: pageUrlStatus,
    };
}

function buildDateCompatibilityContext(input = {}) {
    const requested = input.requested || extractRequestedMetadata(input);
    const observed = input.observed || extractObservedMetadata(input);
    const pageUrlStatus =
        input.pageUrlStatus || comparePageUrlBases(requested.requested_page_url_base, observed.observed_page_url_base);
    const requestedDate = parseDateInfo(requested.requested_match_date);
    const observedDate = parseDateInfo(observed.observed_match_date);
    const teamEvidence = buildTeamPairEvidence(requested, observed);
    const seasonContext = buildSeasonContext(requested, observed, requestedDate, observedDate);
    const dateGap = buildDateGap(requestedDate, observedDate);
    const baseDetails = buildDateCompatibilityBaseDetails({
        requestedDate,
        observedDate,
        seasonContext,
        dateGap,
        teamEvidence,
        pageUrlStatus,
    });

    return {
        requestedDate,
        observedDate,
        pageUrlStatus,
        seasonKnown: seasonContext.seasonKnown,
        sameSeason: seasonContext.sameSeason,
        teamEvidence,
        largeDateGap: dateGap.largeDateGap,
        baseDetails,
    };
}

function hasTimezoneOnlyMismatch(requestedDate, observedDate) {
    return (
        requestedDate.ms === observedDate.ms &&
        requestedDate.literal_date &&
        observedDate.literal_date &&
        requestedDate.literal_date !== observedDate.literal_date
    );
}

function pickDateCompatibilityStatus(input = {}, context = {}) {
    const rules = [
        {
            status: UNKNOWN_DATE_COMPATIBILITY,
            matches: () => !context.requestedDate.ok || !context.observedDate.ok,
        },
        {
            status: CROSS_SEASON_SLUG_REUSE,
            matches: () => context.seasonKnown && context.sameSeason === false && context.pageUrlStatus === 'match',
        },
        {
            status: REVERSE_FIXTURE_DETECTED,
            matches: () =>
                input.reverseFixtureDetected === true ||
                (context.pageUrlStatus === 'match' &&
                    context.teamEvidence.reversed_home_away === true &&
                    context.largeDateGap),
        },
        {
            status: TIMEZONE_ONLY_MISMATCH,
            matches: () => hasTimezoneOnlyMismatch(context.requestedDate, context.observedDate),
        },
        {
            status: DATE_MATCH,
            matches: () => context.requestedDate.ms === context.observedDate.ms,
        },
        {
            status: SAME_UTC_DAY,
            matches: () => context.requestedDate.utc_date === context.observedDate.utc_date,
        },
        {
            status: POSTPONED_OR_RESCHEDULED_EXPLAINED,
            matches: () => hasExplicitRescheduleEvidence(input) === true,
        },
        {
            status: UNRESOLVED_LARGE_GAP,
            matches: () => context.largeDateGap,
        },
    ];
    return rules.find(rule => rule.matches())?.status || UNKNOWN_DATE_COMPATIBILITY;
}

function evaluateDateCompatibility(input = {}) {
    const context = buildDateCompatibilityContext(input);
    const status = pickDateCompatibilityStatus(input, context);
    return buildDateCompatibilityResult(status, context.baseDetails);
}

function compareExternalIds(requestedId, observedId) {
    if (requestedId && observedId && requestedId === observedId) return IDENTITY_MATCH;
    if (requestedId && observedId && requestedId !== observedId) return REQUESTED_OBSERVED_MISMATCH;
    return 'unknown';
}

function buildIdentityStatuses(input = {}, externalIdStatus = 'unknown') {
    if (input.fetchOrParseFailure === true) {
        return {
            canonicalIdentityStatus: FETCH_OR_PARSE_FAILURE,
            identityReconciliationStatus: FETCH_OR_PARSE_FAILURE,
        };
    }
    if (input.blockOrCaptcha === true || (Array.isArray(input.blockMarkers) && input.blockMarkers.length > 0)) {
        return {
            canonicalIdentityStatus: BLOCK_OR_CAPTCHA,
            identityReconciliationStatus: BLOCK_OR_CAPTCHA,
        };
    }
    if (externalIdStatus === REQUESTED_OBSERVED_MISMATCH) {
        return {
            canonicalIdentityStatus: REQUESTED_OBSERVED_MISMATCH,
            identityReconciliationStatus:
                input.acceptedIdentityMappingPresent === true ? 'accepted_schedule_detail_mapping' : UNRESOLVED_MAPPING,
        };
    }
    return {
        canonicalIdentityStatus: externalIdStatus,
        identityReconciliationStatus: externalIdStatus,
    };
}

function inferMappingConfidence({ externalIdStatus, pageUrlStatus, teamDateStatus, dateCompatibility }) {
    if (externalIdStatus === IDENTITY_MATCH) return 'high';
    if (externalIdStatus !== REQUESTED_OBSERVED_MISMATCH) return 'unknown';
    if (dateCompatibility?.blocks_identity_mapping_acceptance === true) return 'blocked';
    if (pageUrlStatus === 'match' && teamDateStatus === 'compatible') return 'medium';
    if (pageUrlStatus === 'match') return 'low';
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
    dateCompatibility,
}) {
    const blockers = new Set();
    const blockMarkers = Array.isArray(input.blockMarkers) ? input.blockMarkers : [];
    const addWhen = (condition, blocker) => {
        if (condition) blockers.add(blocker);
    };
    const requestedIdentityId = requested.requested_detail_external_id || requested.requested_schedule_external_id;
    addWhen(blockMarkers.length > 0 || input.blockOrCaptcha === true, BLOCK_OR_CAPTCHA);
    addWhen(input.fetchOrParseFailure === true, FETCH_OR_PARSE_FAILURE);
    addWhen(!requestedIdentityId, 'missing_requested_detail_external_id');
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
    if (dateCompatibility?.blocks_raw_write === true) {
        blockers.add(dateCompatibility.date_compatibility_status || UNKNOWN_DATE_COMPATIBILITY);
    }
    if (externalIdStatus === REQUESTED_OBSERVED_MISMATCH) {
        addWhen(
            pageUrlStatus === 'match' && dateCompatibility?.positive_evidence !== true,
            'page_url_base_alone_insufficient_for_acceptance'
        );
    }
    addWhen(input.multipleDetailIdsForSameScheduleId === true, 'multiple_detail_ids_for_same_schedule_id');
    addWhen(input.multipleScheduleIdsForSameDetailId === true, 'multiple_schedule_ids_for_same_detail_id');
    addWhen(input.metadataTargetMismatch === true, METADATA_TARGET_MISMATCH);
    return [...blockers].sort();
}

// eslint-disable-next-line complexity
function resolveRecaptureIdentityContract(input = {}) {
    const target = isPlainObject(input.target) ? input.target : input;
    const scheduleExternalId = firstId(
        input.scheduleExternalId,
        input.schedule_external_id,
        input.requestedScheduleExternalId,
        input.externalId,
        input.external_id,
        target.schedule_external_id,
        target.external_id
    );
    const sourceUrlFragmentExternalId = firstId(
        input.sourceUrlFragmentExternalId,
        input.source_url_fragment_external_id,
        target.source_url_fragment_external_id
    );
    const sourcePageUrl = firstText(input.sourcePageUrl, input.source_page_url, target.source_page_url);
    const sourcePageUrlBase = normalizePageUrlBase(
        firstText(
            input.sourcePageUrlBase,
            input.source_page_url_base,
            target.source_page_url_base,
            target.page_url_base
        )
    );
    const acceptedDetailExternalId = firstId(
        input.acceptedDetailExternalId,
        input.accepted_detail_external_id,
        input.recaptureExpectedIdentity,
        input.recapture_expected_identity,
        target.accepted_detail_external_id,
        target.recapture_expected_identity
    );
    const detailExternalIdCandidate = firstId(
        input.detailExternalIdCandidate,
        input.detail_external_id_candidate,
        target.detail_external_id_candidate,
        sourceUrlFragmentExternalId
    );
    const detailIdentitySource = firstText(
        input.detailIdentitySource,
        input.detail_identity_source,
        target.detail_identity_source,
        detailExternalIdCandidate && detailExternalIdCandidate === sourceUrlFragmentExternalId
            ? DETAIL_IDENTITY_SOURCE_URL_HASH_FRAGMENT
            : null
    );
    const recaptureExpectedIdentity = acceptedDetailExternalId || detailExternalIdCandidate;
    const observedDetailExternalId = firstId(
        input.observedDetailExternalId,
        input.observed_detail_external_id,
        target.observed_detail_external_id
    );
    const mappingEffectiveStatus = firstText(
        input.currentMappingEffectiveStatus,
        input.current_mapping_effective_status,
        input.mappingEffectiveStatus,
        target.current_mapping_effective_status,
        target.mapping_effective_status
    );
    const baselineEffectiveStatus = firstText(
        input.currentBaselineEffectiveStatus,
        input.current_baseline_effective_status,
        input.baselineEffectiveStatus,
        target.current_baseline_effective_status,
        target.baseline_effective_status
    );
    const reAcceptancePerformed =
        firstBooleanTrue(
            input.reAcceptanceExecutionPerformed,
            input.re_acceptance_execution_performed,
            target.re_acceptance_execution_performed
        ) ||
        isReacceptedEffectiveStatus(mappingEffectiveStatus) ||
        isReacceptedEffectiveStatus(baselineEffectiveStatus);
    const mappingOrBaselineSuspended =
        isSuspendedEffectiveStatus(mappingEffectiveStatus) || isSuspendedEffectiveStatus(baselineEffectiveStatus);
    const reverseFixtureDetected =
        firstBooleanTrue(
            input.reverseFixtureDetected,
            input.reverse_fixture_detected,
            target.reverse_fixture_detected
        ) ||
        normalizeLower(
            input.dateCompatibilityStatus || input.date_compatibility_status || target.date_compatibility_status
        ) === REVERSE_FIXTURE_DETECTED;
    const hashMismatch =
        input.hashMatchesBaseline === false ||
        target.hash_matches_baseline === false ||
        statusMatches(
            input.hashValidationStatus || input.hash_validation_status || target.hash_validation_status,
            /hash_mismatch/
        );

    const blockers = new Set();
    if (mappingOrBaselineSuspended) blockers.add('suspended_mapping_or_baseline');
    if (!reAcceptancePerformed) blockers.add('missing_re_acceptance');
    if (!acceptedDetailExternalId) blockers.add('missing_accepted_detail_external_id');
    if (
        (sourcePageUrl || sourcePageUrlBase || sourceUrlFragmentExternalId || detailExternalIdCandidate) &&
        (!acceptedDetailExternalId || !reAcceptancePerformed)
    ) {
        blockers.add('page_url_base_alone_insufficient');
    }
    if (observedDetailExternalId && acceptedDetailExternalId && observedDetailExternalId !== acceptedDetailExternalId) {
        blockers.add('identity_mismatch');
    }
    if (reverseFixtureDetected) blockers.add(REVERSE_FIXTURE_DETECTED);
    if (blockers.has('identity_mismatch') && hashMismatch) {
        blockers.add('hash_mismatch_secondary_to_identity_mismatch');
    }

    const recaptureAllowed = blockers.size === 0;
    const hashValidationStatus = blockers.has('hash_mismatch_secondary_to_identity_mismatch')
        ? 'secondary_to_identity_mismatch'
        : firstText(
              input.hashValidationStatus,
              input.hash_validation_status,
              target.hash_validation_status,
              'not_evaluated'
          );

    return {
        schedule_external_id: scheduleExternalId,
        source_url_fragment_external_id: sourceUrlFragmentExternalId,
        source_page_url: sourcePageUrl || null,
        source_page_url_base: sourcePageUrlBase,
        detail_external_id_candidate: detailExternalIdCandidate,
        detail_identity_source: detailIdentitySource,
        accepted_detail_external_id: acceptedDetailExternalId,
        observed_detail_external_id: observedDetailExternalId,
        recapture_request_identity: recaptureAllowed ? acceptedDetailExternalId : null,
        recapture_expected_identity: recaptureExpectedIdentity,
        recapture_request_allowed: recaptureAllowed,
        route_identity_strategy: recaptureAllowed
            ? ACCEPTED_DETAIL_ROUTE_IDENTITY_STRATEGY
            : BLOCKED_ROUTE_IDENTITY_STRATEGY,
        canonical_identity_source: recaptureAllowed
            ? REACCEPTED_CANONICAL_IDENTITY_SOURCE
            : BLOCKED_CANONICAL_IDENTITY_SOURCE,
        current_mapping_effective_status: mappingEffectiveStatus || null,
        current_baseline_effective_status: baselineEffectiveStatus || null,
        re_acceptance_execution_performed: reAcceptancePerformed,
        mapping_or_baseline_suspended: mappingOrBaselineSuspended,
        page_url_base_alone_insufficient_enforced: blockers.has('page_url_base_alone_insufficient'),
        baseline_update_allowed: false,
        baseline_re_acceptance_allowed: false,
        hash_validation_status: hashValidationStatus,
        raw_write_execution_ready: false,
        blockers: [...blockers].sort(),
    };
}

function reconcileRouteIdentity(input = {}) {
    const requested = extractRequestedMetadata(input);
    const observed = extractObservedMetadata(input);
    const requestedId = requested.requested_detail_external_id || requested.requested_schedule_external_id;
    const observedId = observed.observed_detail_external_id;

    const externalIdStatus = compareExternalIds(requestedId, observedId);
    const pageUrlStatus = comparePageUrlBases(requested.requested_page_url_base, observed.observed_page_url_base);
    const teamDateStatus = compareTeamDateStatus(requested, observed);
    const dateCompatibility = evaluateDateCompatibility({
        ...input,
        requested,
        observed,
        pageUrlStatus,
    });
    const dateCompatibilityBlocksRawWrite = dateCompatibility.blocks_raw_write === true;
    const mappingConfidence = inferMappingConfidence({
        externalIdStatus,
        pageUrlStatus,
        teamDateStatus,
        dateCompatibility,
    });
    const safetyBlockers = buildSafetyBlockers({
        input,
        requested,
        observed,
        externalIdStatus,
        pageUrlStatus,
        teamDateStatus,
        dateCompatibility,
    });

    const { canonicalIdentityStatus, identityReconciliationStatus } = buildIdentityStatuses(input, externalIdStatus);

    const rawWriteBlocked =
        dateCompatibilityBlocksRawWrite ||
        (identityReconciliationStatus !== IDENTITY_MATCH &&
            identityReconciliationStatus !== 'accepted_schedule_detail_mapping');

    return {
        requested_detail_external_id: requested.requested_detail_external_id,
        requested_schedule_external_id: requested.requested_schedule_external_id,
        recapture_expected_identity: requestedId,
        observed_detail_external_id: observedId,
        requested_url: requested.requested_url,
        requested_page_url_base: requested.requested_page_url_base,
        observed_page_url_base: observed.observed_page_url_base,
        page_url_base_match_status: pageUrlStatus,
        team_date_status_match_status: teamDateStatus,
        date_compatibility_status: dateCompatibility.date_compatibility_status,
        date_compatibility_result: dateCompatibility,
        date_gap_days: dateCompatibility.date_gap_days,
        date_gap_hours: dateCompatibility.date_gap_hours,
        reverse_fixture_detected: dateCompatibility.date_compatibility_status === REVERSE_FIXTURE_DETECTED,
        date_compatibility_blocks_raw_write: dateCompatibilityBlocksRawWrite,
        date_compatibility_blocks_identity_mapping_acceptance:
            dateCompatibility.blocks_identity_mapping_acceptance === true &&
            externalIdStatus === REQUESTED_OBSERVED_MISMATCH,
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
        !blockers.includes(REVERSE_FIXTURE_DETECTED) &&
        !blockers.includes(CROSS_SEASON_SLUG_REUSE) &&
        !blockers.includes(UNRESOLVED_LARGE_GAP) &&
        !blockers.includes(UNKNOWN_DATE_COMPATIBILITY) &&
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

// ADG9: Strict fixture identity guard — validates expected (schedule) vs observed (detail) identity.
// Blocks candidates with home/away inversion, date mismatch, same-team-pair wrong-leg.
// URL hash fragment alone is insufficient for candidate acceptance.
function validateStrictFixtureIdentity(input = {}) {
    const expectedScheduleExternalId = firstId(
        input.schedule_external_id,
        input.expected_schedule_external_id,
        input.scheduleExternalId
    );
    const detailExternalIdCandidate = firstId(
        input.detail_external_id_candidate,
        input.expected_detail_external_id_candidate,
        input.detailExternalIdCandidate
    );
    const expectedHomeTeam = normalizeTeam(
        firstText(input.expected_home_team, input.home_team, input.expectedHomeTeam)
    );
    const expectedAwayTeam = normalizeTeam(
        firstText(input.expected_away_team, input.away_team, input.expectedAwayTeam)
    );
    const observedHomeTeam = normalizeTeam(
        firstText(input.observed_home_team, input.observedHomeTeam)
    );
    const observedAwayTeam = normalizeTeam(
        firstText(input.observed_away_team, input.observedAwayTeam)
    );
    const expectedMatchDate = firstText(
        input.expected_match_date, input.match_date, input.expectedMatchDate
    );
    const observedMatchDate = firstText(
        input.observed_match_date, input.observedMatchDate
    );
    const expectedCompetition = normalizeLower(
        firstText(input.expected_competition, input.competition, input.expectedCompetition)
    );
    const observedCompetition = normalizeLower(
        firstText(input.observed_competition, input.observedCompetition)
    );
    const expectedSeason = normalizeSeason(
        firstText(input.expected_season, input.season, input.expectedSeason)
    );
    const observedSeason = normalizeSeason(
        firstText(input.observed_season, input.observedSeason)
    );
    const observedDetailId = firstId(
        input.observed_detail_id,
        input.observed_detail_external_id,
        input.observedDetailId
    );
    const isSuspended = Boolean(
        input.is_suspended_reference === true ||
        input.isSuspendedReference === true ||
        input.reference_status === 'blocked_reference_only_no_unsuspend'
    );

    const teamsKnown = Boolean(expectedHomeTeam && expectedAwayTeam && observedHomeTeam && observedAwayTeam);
    const detailCandidateKnown = Boolean(detailExternalIdCandidate);
    const observedDetailKnown = Boolean(observedDetailId);
    const detailIdsDiffer = observedDetailKnown && detailCandidateKnown && detailExternalIdCandidate !== observedDetailId;
    const sameOrder = teamsKnown && expectedHomeTeam === observedHomeTeam && expectedAwayTeam === observedAwayTeam;
    const reversedOrder =
        teamsKnown && expectedHomeTeam === observedAwayTeam && expectedAwayTeam === observedHomeTeam;
    const samePairAnyOrder = sameOrder || reversedOrder;

    const expectedDateMs = parseDateInfo(expectedMatchDate);
    const observedDateMs = parseDateInfo(observedMatchDate);
    const dateDelta = dateDeltaDays(expectedDateMs, observedDateMs);
    const dateWithinTolerance = dateDelta !== null && dateDelta <= STRICT_DATE_TOLERANCE_DAYS;
    const dateLargeDelta = dateDelta !== null && dateDelta > STRICT_DATE_TOLERANCE_DAYS;

    const competitionKnown = Boolean(expectedCompetition && observedCompetition);
    const competitionMatches = competitionKnown && expectedCompetition === observedCompetition;
    const competitionMismatch = competitionKnown && !competitionMatches;

    const seasonKnown = Boolean(expectedSeason && observedSeason);
    const seasonMatches = seasonKnown && expectedSeason === observedSeason;

    // Classification logic
    let auditClassification = AUDIT_CLASSIFICATION_INSUFFICIENT_EVIDENCE;
    let guardStatus = FIXTURE_IDENTITY_GUARD_BLOCKED;
    let guardReason = null;
    let correctionNeeded = false;
    let correctionType = null;

    if (isSuspended) {
        auditClassification = AUDIT_CLASSIFICATION_SUSPENDED_REFERENCE_STILL_BLOCKED;
        guardStatus = FIXTURE_IDENTITY_GUARD_BLOCKED;
        guardReason = 'suspended_reference_cannot_be_reactivated_by_guard';
        correctionNeeded = false;
    } else if (sameOrder && !detailIdsDiffer) {
        auditClassification = AUDIT_CLASSIFICATION_CORRECT_MAPPING;
        guardStatus = FIXTURE_IDENTITY_GUARD_PASSED;
        guardReason = null;
        correctionNeeded = false;
    } else if (reversedOrder && teamsKnown && dateLargeDelta) {
        auditClassification = AUDIT_CLASSIFICATION_REVERSE_FIXTURE_MAPPING_ERROR;
        guardStatus = FIXTURE_IDENTITY_GUARD_BLOCKED;
        guardReason = 'home_away_inversion_with_date_mismatch_indicates_reverse_fixture_not_this_target';
        correctionNeeded = true;
        correctionType = 'reject_candidate';
    } else if (reversedOrder && teamsKnown) {
        auditClassification = AUDIT_CLASSIFICATION_HOME_AWAY_INVERSION;
        guardStatus = FIXTURE_IDENTITY_GUARD_BLOCKED;
        guardReason = 'home_and_away_teams_reversed_vs_expected_schedule';
        correctionNeeded = true;
        correctionType = 'reject_candidate';
    } else if (samePairAnyOrder && dateLargeDelta) {
        auditClassification = AUDIT_CLASSIFICATION_SAME_TEAM_PAIR_WRONG_LEG;
        guardStatus = FIXTURE_IDENTITY_GUARD_BLOCKED;
        guardReason = 'same_team_pair_but_date_delta_indicates_wrong_leg_of_home_away_fixture';
        correctionNeeded = true;
        correctionType = 'reject_candidate';
    } else if (dateLargeDelta && teamsKnown) {
        auditClassification = AUDIT_CLASSIFICATION_DATE_MISMATCH;
        guardStatus = FIXTURE_IDENTITY_GUARD_BLOCKED;
        guardReason = 'match_date_differs_beyond_tolerance';
        correctionNeeded = true;
        correctionType = 'reject_candidate';
    } else if (competitionMismatch) {
        auditClassification = AUDIT_CLASSIFICATION_COMPETITION_MISMATCH;
        guardStatus = FIXTURE_IDENTITY_GUARD_BLOCKED;
        guardReason = 'expected_competition_does_not_match_observed';
        correctionNeeded = true;
        correctionType = 'reject_candidate';
    }

    const correctionActions = correctionNeeded
        ? ['reject_candidate', 'supersede_candidate', 'require_new_source_inventory_record', 'require_strict_home_away_date_guard']
        : [];

    const blockers = [];
    if (isSuspended) blockers.push('suspended_reference_still_blocked');
    if (detailExternalIdCandidate && !teamsKnown && !dateDelta) {
        blockers.push('url_hash_alone_insufficient');
    }
    if (reversedOrder) blockers.push('home_away_inversion');
    if (dateLargeDelta) blockers.push('date_mismatch');
    if (competitionMismatch) blockers.push('competition_mismatch');
    if (detailIdsDiffer && samePairAnyOrder && dateLargeDelta) blockers.push('same_team_pair_wrong_leg');

    const rejectedDetailId = correctionNeeded ? detailExternalIdCandidate : null;
    const observedReversedDetailId =
        reversedOrder && detailIdsDiffer && observedDetailKnown ? observedDetailId : null;

    return {
        fixture_identity_guard_status: guardStatus,
        fixture_identity_guard_reason: guardReason,
        audit_classification: auditClassification,
        schedule_external_id: expectedScheduleExternalId,
        detail_external_id_candidate: detailExternalIdCandidate,
        rejected_detail_external_id_candidate: rejectedDetailId,
        observed_reversed_detail_id: observedReversedDetailId,
        observed_detail_id: observedDetailId,
        expected_home_team: expectedHomeTeam || null,
        expected_away_team: expectedAwayTeam || null,
        observed_home_team: observedHomeTeam || null,
        observed_away_team: observedAwayTeam || null,
        expected_match_date: expectedMatchDate,
        observed_match_date: observedMatchDate,
        expected_competition: expectedCompetition || null,
        observed_competition: observedCompetition || null,
        expected_season: expectedSeason,
        observed_season: observedSeason,
        home_away_orientation_status: sameOrder ? 'matches' : reversedOrder ? 'reversed' : 'unknown_or_mismatch',
        team_pair_match: samePairAnyOrder,
        date_delta_days: dateDelta,
        date_within_tolerance: dateWithinTolerance,
        competition_match: competitionMatches,
        season_match: seasonMatches,
        detail_identity_candidate_validated: guardStatus === FIXTURE_IDENTITY_GUARD_PASSED,
        url_hash_alone_insufficient: Boolean(detailCandidateKnown && !teamsKnown),
        correction_needed: correctionNeeded,
        correction_type: correctionType,
        correction_actions: correctionActions,
        raw_write_execution_ready: false,
        is_suspended_reference: isSuspended,
        blockers,
    };
}

function dateDeltaDays(expected, observed) {
    if (!expected?.ok || !observed?.ok) return null;
    return Math.round(Math.abs(observed.ms - expected.ms) / 86400000);
}

// ADG14: Classification of detail candidate identity during source inventory generation.
// Uses limited source-controlled evidence (no live fetch required).
// Returns candidate_status: accepted_validated | rejected_home_away_inversion |
//   rejected_reverse_fixture_mapping | requires_new_source_inventory_record |
//   unknown_insufficient_evidence
function classifyDetailCandidateIdentity(input = {}) {
    const expectedHome = normalizeTeam(
        firstText(input.expected_home_team, input.schedule_home_team)
    );
    const expectedAway = normalizeTeam(
        firstText(input.expected_away_team, input.schedule_away_team)
    );
    const sourceHome = normalizeTeam(
        firstText(input.source_home_team, input.observed_home_team)
    );
    const sourceAway = normalizeTeam(
        firstText(input.source_away_team, input.observed_away_team)
    );
    const expectedDate = firstText(
        input.expected_match_date, input.schedule_match_date, input.schedule_date
    );
    const sourceDate = firstText(
        input.source_match_date, input.observed_match_date
    );
    const detailCandidate = firstId(
        input.detail_external_id_candidate, input.source_url_fragment_external_id
    );
    const expectedCompetition = normalizeLower(
        firstText(input.expected_competition, input.league_name)
    );
    const sourceCompetition = normalizeLower(
        firstText(input.source_competition, input.observed_competition)
    );

    const teamsKnown = Boolean(expectedHome && expectedAway && sourceHome && sourceAway);
    const sameOrder = teamsKnown && expectedHome === sourceHome && expectedAway === sourceAway;
    const isReversed = teamsKnown && expectedHome === sourceAway && expectedAway === sourceHome;

    const expectedDateMs = expectedDate ? parseDateInfo(expectedDate) : null;
    const sourceDateMs = sourceDate ? parseDateInfo(sourceDate) : null;
    const dateDelta = dateDeltaDays(expectedDateMs, sourceDateMs);
    const dateLargeGap = dateDelta !== null && dateDelta > STRICT_DATE_TOLERANCE_DAYS;

    const competitionMismatch =
        Boolean(expectedCompetition && sourceCompetition && expectedCompetition !== sourceCompetition);

    // Classification logic
    let candidateStatus = 'unknown_insufficient_evidence';
    let guardStatus = FIXTURE_IDENTITY_GUARD_BLOCKED;
    let correctionNeeded = false;
    let correctionType = null;

    if (!detailCandidate) {
        candidateStatus = 'unknown_insufficient_evidence';
        guardStatus = FIXTURE_IDENTITY_GUARD_BLOCKED;
    } else if (isReversed && dateLargeGap) {
        candidateStatus = 'rejected_reverse_fixture_mapping';
        guardStatus = FIXTURE_IDENTITY_GUARD_BLOCKED;
        correctionNeeded = true;
        correctionType = 'reject_candidate';
    } else if (isReversed) {
        candidateStatus = 'rejected_home_away_inversion';
        guardStatus = FIXTURE_IDENTITY_GUARD_BLOCKED;
        correctionNeeded = true;
        correctionType = 'reject_candidate';
    } else if (dateLargeGap) {
        candidateStatus = 'rejected_reverse_fixture_mapping';
        guardStatus = FIXTURE_IDENTITY_GUARD_BLOCKED;
        correctionNeeded = true;
        correctionType = 'require_new_source_inventory_record';
    } else if (competitionMismatch) {
        candidateStatus = 'requires_new_source_inventory_record';
        guardStatus = FIXTURE_IDENTITY_GUARD_BLOCKED;
        correctionNeeded = true;
        correctionType = 'require_new_source_inventory_record';
    } else if (sameOrder && detailCandidate) {
        candidateStatus = 'accepted_validated';
        guardStatus = FIXTURE_IDENTITY_GUARD_PASSED;
        correctionNeeded = false;
    } else if (detailCandidate && !teamsKnown) {
        candidateStatus = 'unknown_insufficient_evidence';
        guardStatus = FIXTURE_IDENTITY_GUARD_BLOCKED;
    }

    return {
        detail_identity_candidate_status: candidateStatus,
        fixture_identity_guard_status: guardStatus,
        detail_external_id_candidate: detailCandidate,
        expected_home_team: expectedHome || null,
        expected_away_team: expectedAway || null,
        source_home_team: sourceHome || null,
        source_away_team: sourceAway || null,
        home_away_orientation: sameOrder ? 'matches' : isReversed ? 'reversed' : 'unknown',
        date_delta_days: dateDelta,
        correction_needed: correctionNeeded,
        correction_type: correctionType,
        correction_actions: correctionNeeded
            ? ['reject_candidate', 'supersede_candidate', 'require_strict_home_away_date_guard']
            : [],
        raw_write_execution_ready: false,
        url_hash_alone_insufficient: Boolean(detailCandidate && !teamsKnown && !dateDelta),
    };
}

// ADG17: Select the oriented fixture record from multiple source inventory candidates.
// Given expected identity and a list of candidate records (each with home/away/date/external_id),
// selects the best match. Rejects if only reverse fixture is available.
function selectOrientedFixtureRecord({ expectedHome, expectedAway, expectedDate, expectedCompetition, candidates = [] } = {}) {
    const expHome = normalizeTeam(expectedHome);
    const expAway = normalizeTeam(expectedAway);
    const expDate = expectedDate ? parseDateInfo(expectedDate) : null;
    const sorted = (Array.isArray(candidates) ? candidates : []).map(c => {
        const cHome = normalizeTeam(c.home_team || c.observed_home_team);
        const cAway = normalizeTeam(c.away_team || c.observed_away_team);
        const cDate = (c.match_date || c.observed_match_date) ? parseDateInfo(c.match_date || c.observed_match_date) : null;
        const sameOrder = cHome === expHome && cAway === expAway;
        const reversed = cHome === expAway && cAway === expHome;
        const dateDelta = dateDeltaDays(expDate, cDate);
        const dateClose = dateDelta !== null && dateDelta <= STRICT_DATE_TOLERANCE_DAYS;
        let score = 0;
        if (sameOrder) score += 100;
        if (reversed) score -= 50;
        if (dateClose) score += 50;
        if (dateDelta !== null && dateDelta > 1) score -= dateDelta;
        return { ...c, _sameOrder: sameOrder, _reversed: reversed, _dateDelta: dateDelta, _score: score };
    }).sort((a, b) => b._score - a._score);

    if (sorted.length === 0) return { selected: null, status: 'no_candidates', raw_write_ready: false };

    const best = sorted[0];
    if (best._sameOrder) {
        return { selected: best, status: 'oriented_match_selected',
            selection_method: best._dateDelta <= STRICT_DATE_TOLERANCE_DAYS ? 'home_away_date_match' : 'home_away_match_date_delta',
            raw_write_ready: false };
    }
    if (best._reversed) {
        return { selected: null, rejected_candidate: best, status: 'rejected_reverse_fixture_mapping',
            selection_method: 'only_reverse_available', correction_needed: true,
            raw_write_ready: false };
    }
    return { selected: sorted.find(c => !c._reversed) || null, status: 'oriented_best_effort',
        selection_method: 'fallback_no_perfect_match', raw_write_ready: false };
}

module.exports = {
    IDENTITY_MATCH,
    REQUESTED_OBSERVED_MISMATCH,
    UNRESOLVED_MAPPING,
    ACCEPTED_MAPPING_REQUIRED,
    FETCH_OR_PARSE_FAILURE,
    BLOCK_OR_CAPTCHA,
    METADATA_TARGET_MISMATCH,
    DATE_MATCH,
    SAME_UTC_DAY,
    TIMEZONE_ONLY_MISMATCH,
    POSTPONED_OR_RESCHEDULED_EXPLAINED,
    REVERSE_FIXTURE_DETECTED,
    CROSS_SEASON_SLUG_REUSE,
    UNRESOLVED_LARGE_GAP,
    UNKNOWN_DATE_COMPATIBILITY,
    // ADG9: Strict fixture identity guard
    FIXTURE_IDENTITY_GUARD_PASSED,
    FIXTURE_IDENTITY_GUARD_BLOCKED,
    STRICT_DATE_TOLERANCE_DAYS,
    AUDIT_CLASSIFICATION_CORRECT_MAPPING,
    AUDIT_CLASSIFICATION_REVERSE_FIXTURE_MAPPING_ERROR,
    AUDIT_CLASSIFICATION_HOME_AWAY_INVERSION,
    AUDIT_CLASSIFICATION_SAME_TEAM_PAIR_WRONG_LEG,
    AUDIT_CLASSIFICATION_DATE_MISMATCH,
    AUDIT_CLASSIFICATION_COMPETITION_MISMATCH,
    AUDIT_CLASSIFICATION_SUSPENDED_REFERENCE_STILL_BLOCKED,
    AUDIT_CLASSIFICATION_INSUFFICIENT_EVIDENCE,
    validateStrictFixtureIdentity,
    classifyDetailCandidateIdentity,
    selectOrientedFixtureRecord,
    normalizePageUrlBase,
    normalizeDateOnly,
    normalizeSeason,
    resolveRecaptureIdentityContract,
    extractRequestedMetadata,
    extractObservedMetadata,
    compareTeamDateStatus,
    evaluateDateCompatibility,
    reconcileRouteIdentity,
    assertRawWriteIdentityGate,
};
