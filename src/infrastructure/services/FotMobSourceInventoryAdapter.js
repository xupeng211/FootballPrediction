'use strict';

const { DiscoveryParser } = require('./DiscoveryParser');
const { L1ConfigManager } = require('./L1ConfigManager');
const { SeasonStrategyFactory } = require('./SeasonStrategy');

const SOURCE = 'fotmob';
const ROUTE_KIND = 'l1_api_data_leagues';

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
        const parsedFixtures = this.parser.parse(sourceJson, target.leagueId, target.season, false, {
            fullSync: true,
        });
        const guardedFixtures = this.filterBySeasonWindow(parsedFixtures, target.leagueId, target.season);

        return guardedFixtures.map((fixture, index) => this.toManifestCandidateSeed(fixture, index + 1));
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

    toManifestCandidateSeed(fixture, priority = null) {
        const externalId = String(fixture?.external_id || '').trim();
        return {
            source: SOURCE,
            source_inventory_route: ROUTE_KIND,
            match_id: fixture?.match_id || null,
            external_id: externalId || null,
            valid_external_id: isNumericExternalId(externalId),
            league_name: fixture?.league_name || null,
            season: fixture?.season || null,
            home_team: fixture?.home_team || null,
            away_team: fixture?.away_team || null,
            kickoff_time: toIsoText(fixture?.match_date),
            match_date: toIsoText(fixture?.match_date),
            status: fixture?.status || 'scheduled',
            data_source: fixture?.data_source || 'FotMob',
            source_path: ROUTE_KIND,
            source_url: null,
            priority,
        };
    }
}

module.exports = {
    FotMobSourceInventoryAdapter,
    ROUTE_KIND,
};
