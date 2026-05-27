'use strict';

const { DiscoveryParser } = require('./DiscoveryParser');
const { L1ConfigManager } = require('./L1ConfigManager');
const { SeasonStrategyFactory } = require('./SeasonStrategy');

const SOURCE = 'fotmob';
const ROUTE_KIND = 'l1_api_data_leagues';
const FOTMOB_BASE_URL = 'https://www.fotmob.com';
const DETAIL_IDENTITY_SOURCE_URL_HASH_FRAGMENT = 'url_hash_fragment';

function noopLogger() {
    return {
        info() {},
        warn() {},
        error() {},
    };
}

function parseDate(value) {
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function toIsoText(value) {
    const parsed = parseDate(value);
    return parsed ? parsed.toISOString() : null;
}

function isNumericExternalId(value) {
    return /^\d+$/.test(String(value || '').trim());
}

function pickSourcePageUrl(match = {}) {
    return (
        [
            match.source_page_url,
            match.pageUrl,
            match.page_url,
            match.matchUrl,
            match.match_url,
            match.href,
            match.url,
            match.link,
        ]
            .find(value => typeof value === 'string' && value.trim())
            ?.trim() || null
    );
}

function parseSourcePageUrl(sourcePageUrl) {
    const normalized = typeof sourcePageUrl === 'string' && sourcePageUrl.trim() ? sourcePageUrl.trim() : null;
    if (!normalized) {
        return {
            source_page_url: null,
            source_page_url_base: null,
            source_url_fragment_external_id: null,
            source_slug: null,
            source_route_code: null,
            source_url_path_slug: null,
        };
    }

    const hashIndex = normalized.indexOf('#');
    const sourcePageUrlBase = hashIndex >= 0 ? normalized.slice(0, hashIndex) : normalized;
    let fragmentExternalId = null;
    let sourceSlug = null;
    let sourceRouteCode = null;

    try {
        const parsed = new URL(normalized, FOTMOB_BASE_URL);
        const fragmentMatch = decodeURIComponent(parsed.hash || '').match(/\d+/);
        fragmentExternalId = fragmentMatch ? fragmentMatch[0] : null;
        const segments = parsed.pathname.split('/').filter(Boolean);
        const matchesIndex = segments.indexOf('matches');
        if (matchesIndex >= 0) {
            sourceSlug = segments[matchesIndex + 1] || null;
            sourceRouteCode = segments[matchesIndex + 2] || null;
        }
    } catch {
        fragmentExternalId = (normalized.slice(hashIndex + 1).match(/\d+/) || [null])[0];
    }

    return {
        source_page_url: normalized,
        source_page_url_base: sourcePageUrlBase || null,
        source_url_fragment_external_id: fragmentExternalId,
        source_slug: sourceSlug,
        source_route_code: sourceRouteCode,
        source_url_path_slug: sourceRouteCode,
    };
}

function buildSourceInventoryRecordKey(sourcePath, externalId) {
    const pathPart = String(sourcePath || 'unknown').trim() || 'unknown';
    const idPart = String(externalId || 'unknown').trim() || 'unknown';
    return `${ROUTE_KIND}:${pathPart}:${idPart}`;
}

function fallback(value, defaultValue = null) {
    return value || defaultValue;
}

function buildDetailIdentityFields(evidence = {}) {
    const detailExternalIdCandidate = isNumericExternalId(evidence.source_url_fragment_external_id)
        ? String(evidence.source_url_fragment_external_id).trim()
        : null;
    return {
        detail_external_id_candidate: detailExternalIdCandidate,
        detail_identity_source: detailExternalIdCandidate ? DETAIL_IDENTITY_SOURCE_URL_HASH_FRAGMENT : null,
    };
}

function buildSourceEvidenceFields(evidence = {}) {
    return {
        source_url: fallback(evidence.source_page_url),
        source_page_url: fallback(evidence.source_page_url),
        source_page_url_base: fallback(evidence.source_page_url_base),
        source_url_fragment_external_id: fallback(evidence.source_url_fragment_external_id),
        source_slug: fallback(evidence.source_slug),
        source_route_code: fallback(evidence.source_route_code),
        source_url_path_slug: fallback(evidence.source_url_path_slug || evidence.source_route_code),
        ...buildDetailIdentityFields(evidence),
        source_inventory_record_key: fallback(evidence.source_inventory_record_key),
        source_inventory_generated_at: fallback(evidence.source_inventory_generated_at, 'unknown'),
        identity_evidence_status: fallback(evidence.identity_evidence_status, 'missing'),
    };
}

function buildScheduleEvidenceFields(fixture = {}, externalId = null) {
    return {
        schedule_external_id: fallback(externalId),
        schedule_date: toIsoText(fixture?.match_date),
        schedule_home_team: fallback(fixture?.home_team),
        schedule_away_team: fallback(fixture?.away_team),
    };
}

function classifyIdentityEvidence(evidence, externalId) {
    if (!evidence.source_page_url) {
        return 'missing';
    }
    if (
        externalId &&
        evidence.source_page_url_base &&
        evidence.source_url_fragment_external_id &&
        evidence.source_inventory_record_key &&
        String(evidence.source_url_fragment_external_id) === String(externalId)
    ) {
        return 'complete';
    }
    return 'partial';
}

function deriveSourceInventoryIdentityEvidence({
    match = {},
    sourcePath = null,
    externalId = null,
    generatedAt = null,
} = {}) {
    const resolvedExternalId = String(externalId || match?.external_id || match?.id || match?.matchId || '').trim();
    const parsedUrl = parseSourcePageUrl(pickSourcePageUrl(match));
    const recordKey = buildSourceInventoryRecordKey(sourcePath, resolvedExternalId);
    const evidence = {
        ...parsedUrl,
        source_inventory_record_key: recordKey,
        source_inventory_generated_at: generatedAt || 'unknown',
    };

    return {
        ...evidence,
        ...buildDetailIdentityFields(evidence),
        identity_evidence_status: classifyIdentityEvidence(evidence, resolvedExternalId),
    };
}

function isObjectLike(value) {
    return Boolean(value) && typeof value === 'object';
}

function getRawExternalId(match = {}) {
    return match.id ?? match.matchId ?? match.match_id ?? match.external_id ?? match.eventId ?? null;
}

function looksLikeRawMatch(value) {
    return isObjectLike(value) && getRawExternalId(value) !== null;
}

function scanSourceInventoryNode(node, sourcePath, depth, state) {
    if (depth > 6 || !isObjectLike(node)) {
        return;
    }

    if (Array.isArray(node)) {
        node.forEach((item, index) => {
            const itemPath = sourcePath ? `${sourcePath}.${index}` : String(index);
            scanSourceInventoryNode(item, itemPath, depth + 1, state);
        });
        return;
    }

    if (state.seenObjects.has(node)) {
        return;
    }
    state.seenObjects.add(node);

    if (looksLikeRawMatch(node)) {
        const externalId = String(getRawExternalId(node) || '').trim();
        if (externalId && !state.evidenceByExternalId.has(externalId)) {
            state.evidenceByExternalId.set(
                externalId,
                deriveSourceInventoryIdentityEvidence({
                    match: node,
                    sourcePath,
                    externalId,
                    generatedAt: state.generatedAt,
                })
            );
        }
    }

    for (const [key, value] of Object.entries(node)) {
        scanSourceInventoryNode(value, sourcePath ? `${sourcePath}.${key}` : key, depth + 1, state);
    }
}

function extractSourceInventoryEvidence(sourceJson, options = {}) {
    const state = {
        evidenceByExternalId: new Map(),
        seenObjects: new WeakSet(),
        generatedAt: options.sourceInventoryGeneratedAt || options.generatedAt || 'unknown',
    };
    scanSourceInventoryNode(sourceJson, '', 0, state);
    return state.evidenceByExternalId;
}

class FotMobSourceInventoryAdapter {
    constructor(options = {}) {
        this.logger = options.logger || noopLogger();
        this.configManager = options.configManager || new L1ConfigManager({ logger: this.logger });
        this.seasonStrategyFactory =
            options.seasonStrategyFactory ||
            new SeasonStrategyFactory({
                singleYearLeagues:
                    typeof this.configManager.getSingleYearLeagueIds === 'function'
                        ? this.configManager.getSingleYearLeagueIds()
                        : [],
            });
        this.parser =
            options.parser ||
            new DiscoveryParser(
                this.logger,
                this.configManager.getRuntimeConfig?.() || this.configManager.runtimeConfig
            );
    }

    resolveTarget(options = {}) {
        const source = String(options.source || SOURCE)
            .trim()
            .toLowerCase();
        if (source !== SOURCE) {
            throw new Error('FotMobSourceInventoryAdapter only supports source=fotmob');
        }

        const leagueId = Number(options.leagueId ?? options.league_id);
        if (!Number.isInteger(leagueId) || leagueId <= 0) {
            throw new Error('FotMobSourceInventoryAdapter requires a positive leagueId');
        }

        const season = String(options.season || '').trim();
        if (!season) {
            throw new Error('FotMobSourceInventoryAdapter requires season');
        }

        const league =
            typeof this.configManager.getLeagueById === 'function' ? this.configManager.getLeagueById(leagueId) : null;
        if (!league) {
            throw new Error(`league config not found for FotMob source inventory target ${leagueId}`);
        }

        const formattedSeason = this.seasonStrategyFactory.format(leagueId, season);
        const providerLeagueId =
            typeof this.configManager.getProviderLeagueId === 'function'
                ? this.configManager.getProviderLeagueId(leagueId)
                : league.providerId || leagueId;

        return {
            source,
            leagueId,
            providerLeagueId,
            league,
            season,
            formattedSeason,
            routeKind: ROUTE_KIND,
        };
    }

    buildSourceInventoryUrl(options = {}) {
        const target = this.resolveTarget(options);
        return this.configManager.buildLeagueApiUrl(target.leagueId, target.formattedSeason);
    }

    buildFetchRequest(options = {}) {
        const target = this.resolveTarget(options);
        return {
            source: SOURCE,
            routeKind: ROUTE_KIND,
            leagueId: target.leagueId,
            providerLeagueId: target.providerLeagueId,
            season: target.season,
            formattedSeason: target.formattedSeason,
            sourceUrl: this.configManager.buildLeagueApiUrl(target.leagueId, target.formattedSeason),
            target: target.league,
        };
    }

    parseSourceInventory(sourceJson, options = {}) {
        const target = this.resolveTarget(options);
        const evidenceByExternalId = extractSourceInventoryEvidence(sourceJson, options);
        const parsedFixtures = this.parser.parse(sourceJson, target.leagueId, target.season, false, {
            fullSync: true,
        });
        const guardedFixtures = this.filterBySeasonWindow(parsedFixtures, target.leagueId, target.season);

        return guardedFixtures.map((fixture, index) =>
            this.toManifestCandidateSeed(fixture, index + 1, evidenceByExternalId.get(String(fixture?.external_id)))
        );
    }

    filterBySeasonWindow(fixtures, leagueId, season) {
        const window =
            typeof this.configManager.getSeasonDateWindow === 'function'
                ? this.configManager.getSeasonDateWindow(leagueId, season)
                : null;
        if (!window?.start || !window?.end) {
            return Array.isArray(fixtures) ? fixtures : [];
        }

        const start = parseDate(`${window.start}T00:00:00.000Z`);
        const end = parseDate(`${window.end}T23:59:59.999Z`);
        if (!start || !end) {
            return Array.isArray(fixtures) ? fixtures : [];
        }

        return (Array.isArray(fixtures) ? fixtures : []).filter(fixture => {
            const matchDate = parseDate(fixture?.match_date);
            return !matchDate || (matchDate >= start && matchDate <= end);
        });
    }

    toManifestCandidateSeed(fixture, priority = null, sourceEvidence = {}) {
        const externalId = String(fixture?.external_id || '').trim();
        const evidence = sourceEvidence || {};
        return {
            source: SOURCE,
            source_inventory_route: ROUTE_KIND,
            match_id: fallback(fixture?.match_id),
            external_id: fallback(externalId),
            valid_external_id: isNumericExternalId(externalId),
            league_name: fallback(fixture?.league_name),
            season: fallback(fixture?.season),
            home_team: fallback(fixture?.home_team),
            away_team: fallback(fixture?.away_team),
            kickoff_time: toIsoText(fixture?.match_date),
            match_date: toIsoText(fixture?.match_date),
            status: fallback(fixture?.status, 'scheduled'),
            data_source: fallback(fixture?.data_source, 'FotMob'),
            source_path: ROUTE_KIND,
            ...buildSourceEvidenceFields(evidence),
            ...buildScheduleEvidenceFields(fixture, externalId),
            priority,
        };
    }
}

module.exports = {
    FotMobSourceInventoryAdapter,
    ROUTE_KIND,
    DETAIL_IDENTITY_SOURCE_URL_HASH_FRAGMENT,
    deriveSourceInventoryIdentityEvidence,
    extractSourceInventoryEvidence,
    parseSourcePageUrl,
};
