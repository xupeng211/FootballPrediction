#!/usr/bin/env node
/* eslint-disable complexity, max-lines */
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const { L1ConfigManager } = require('../../src/infrastructure/services/L1ConfigManager');

const PHASE = 'PHASE5_05L1_CONTROLLED_L1_EXTERNAL_NETWORK_CANDIDATES_PREVIEW';
const SAFE_SOURCE = 'fotmob';
const CONTROLLED_CANDIDATES_SCOPE = 'controlled_candidates_preview';
const SAFE_SCOPES = new Set([
    'config_only_preview',
    'league_season_date',
    'league_season_window_preview',
    CONTROLLED_CANDIDATES_SCOPE,
]);
const DEFAULT_CONCURRENCY = 1;
const DEFAULT_MAX_TARGETS = 1;
const MAX_CONTROLLED_NETWORK_TARGETS = 10;
const DEFAULT_LOOKBACK = 30;
const DEFAULT_LOOKAHEAD = 7;
const NEXT_REQUIRED_PHASE = 'controlled matches seed commit planning with explicit user authorization';
const BLOCKED_COMMIT_MESSAGE = 'BLOCKED: L1 discovery safe preview wrapper does not execute writes in Phase 5.05L1.';
const REGISTRY_PATH = path.resolve(__dirname, '../../config/acquisition_engines.phase454.json');
const TARGET_MATCH_ID_CANDIDATE = '4830746';

function parseBooleanLike(value, fallback = undefined) {
    if (typeof value === 'boolean') {
        return value;
    }

    if (typeof value !== 'string') {
        return fallback;
    }

    const normalized = value.trim().toLowerCase();
    if (['1', 'true', 'yes', 'y', 'on'].includes(normalized)) {
        return true;
    }
    if (['0', 'false', 'no', 'n', 'off'].includes(normalized)) {
        return false;
    }

    return fallback;
}

function parseIntegerLike(value, fallback = null) {
    if (value === null || value === undefined || value === '') {
        return fallback;
    }

    const parsed = Number.parseInt(String(value), 10);
    return Number.isInteger(parsed) ? parsed : Number.NaN;
}

function parseOptionValue(currentArg, argv, index) {
    if (currentArg.includes('=')) {
        const separatorIndex = currentArg.indexOf('=');
        return {
            value: currentArg.slice(separatorIndex + 1),
            consumedNext: false,
        };
    }

    const nextArg = argv[index + 1];
    if (typeof nextArg === 'string' && !nextArg.startsWith('--')) {
        return { value: nextArg, consumedNext: true };
    }

    return { value: true, consumedNext: false };
}

function toDateOnlyText(date) {
    return date.toISOString().slice(0, 10);
}

function parseDateStrict(value) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(String(value || ''))) {
        return null;
    }

    const parsed = new Date(`${value}T00:00:00.000Z`);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function clampDateRange(referenceDate, daysOffset) {
    const next = new Date(referenceDate.getTime());
    next.setUTCDate(next.getUTCDate() + daysOffset);
    return next;
}

function safeReadJson(targetPath, dependencies = {}) {
    const readFileSync = dependencies.readFileSync || fs.readFileSync;
    return JSON.parse(readFileSync(targetPath, 'utf8'));
}

function loadTitanDiscoveryRegistryMetadata(dependencies = {}) {
    const registry = safeReadJson(REGISTRY_PATH, dependencies);
    const engine = Array.isArray(registry.engines)
        ? registry.engines.find(entry => entry && entry.id === 'titan_discovery') || null
        : null;

    return {
        path: REGISTRY_PATH,
        registry,
        engine,
    };
}

function parseArgs(argv = process.argv.slice(2)) {
    const options = {
        source: null,
        scope: null,
        leagueId: null,
        season: null,
        date: null,
        lookback: null,
        lookahead: null,
        concurrency: null,
        maxTargets: null,
        dryRun: undefined,
        commit: false,
        dbWrite: false,
        browser: false,
        proxy: false,
        all: false,
        allLeagues: false,
        fullSync: false,
        networkAuthorization: false,
        networkPreview: false,
        allowBrowserRuntime: false,
        allowProxyRuntime: false,
        allowDbWrite: false,
        help: false,
        json: true,
    };

    const keyMap = {
        source: 'source',
        scope: 'scope',
        'league-id': 'leagueId',
        league_id: 'leagueId',
        season: 'season',
        date: 'date',
        lookback: 'lookback',
        lookahead: 'lookahead',
        concurrency: 'concurrency',
        'max-targets': 'maxTargets',
        max_targets: 'maxTargets',
        'dry-run': 'dryRun',
        dry_run: 'dryRun',
        commit: 'commit',
        'db-write': 'dbWrite',
        db_write: 'dbWrite',
        browser: 'browser',
        proxy: 'proxy',
        all: 'all',
        'all-leagues': 'allLeagues',
        all_leagues: 'allLeagues',
        'full-sync': 'fullSync',
        full_sync: 'fullSync',
        'network-authorization': 'networkAuthorization',
        network_authorization: 'networkAuthorization',
        'network-preview': 'networkPreview',
        network_preview: 'networkPreview',
        'allow-network': 'networkPreview',
        allow_network: 'networkPreview',
        'allow-browser-runtime': 'allowBrowserRuntime',
        allow_browser_runtime: 'allowBrowserRuntime',
        'allow-proxy-runtime': 'allowProxyRuntime',
        allow_proxy_runtime: 'allowProxyRuntime',
        'allow-db-write': 'allowDbWrite',
        allow_db_write: 'allowDbWrite',
        help: 'help',
        h: 'help',
        json: 'json',
    };

    for (let index = 0; index < argv.length; index += 1) {
        const arg = argv[index];
        if (!arg.startsWith('--')) {
            continue;
        }

        const rawKey = arg.replace(/^--/, '').split('=')[0];
        const optionKey = keyMap[rawKey];
        if (!optionKey) {
            continue;
        }

        const { value, consumedNext } = parseOptionValue(arg, argv, index);
        if (consumedNext) {
            index += 1;
        }

        if (
            [
                'commit',
                'dbWrite',
                'browser',
                'proxy',
                'all',
                'allLeagues',
                'fullSync',
                'networkAuthorization',
                'networkPreview',
                'allowBrowserRuntime',
                'allowProxyRuntime',
                'allowDbWrite',
                'help',
                'json',
            ].includes(optionKey)
        ) {
            options[optionKey] = parseBooleanLike(value, true);
            continue;
        }

        if (optionKey === 'dryRun') {
            options.dryRun = parseBooleanLike(value, true);
            continue;
        }

        options[optionKey] = typeof value === 'boolean' ? String(value) : value;
    }

    return options;
}

function normalizeSafePreviewInput(input = {}) {
    const source = typeof input.source === 'string' ? input.source.trim().toLowerCase() : '';
    const scope = typeof input.scope === 'string' ? input.scope.trim() : '';
    const concurrency = parseIntegerLike(input.concurrency, DEFAULT_CONCURRENCY);
    const maxTargets = parseIntegerLike(input.maxTargets, DEFAULT_MAX_TARGETS);
    const lookback = parseIntegerLike(input.lookback, DEFAULT_LOOKBACK);
    const lookahead = parseIntegerLike(input.lookahead, DEFAULT_LOOKAHEAD);
    const leagueIdText =
        input.leagueId === null || input.leagueId === undefined || input.leagueId === ''
            ? null
            : String(input.leagueId).trim();
    const leagueIdNumber = leagueIdText === null ? null : parseIntegerLike(leagueIdText, Number.NaN);

    return {
        source,
        scope,
        leagueId: leagueIdText,
        leagueIdNumber: Number.isInteger(leagueIdNumber) ? leagueIdNumber : null,
        season: typeof input.season === 'string' ? input.season.trim() : null,
        date: typeof input.date === 'string' ? input.date.trim() : null,
        lookback,
        lookahead,
        concurrency,
        maxTargets,
        dryRun: input.dryRun === undefined ? true : parseBooleanLike(input.dryRun, undefined),
        commit: parseBooleanLike(input.commit, false),
        dbWrite: parseBooleanLike(input.dbWrite, false),
        browser: parseBooleanLike(input.browser, false),
        proxy: parseBooleanLike(input.proxy, false),
        networkPreview: parseBooleanLike(input.networkPreview, false),
        allowBrowserRuntime: parseBooleanLike(input.allowBrowserRuntime, false),
        allowProxyRuntime: parseBooleanLike(input.allowProxyRuntime, false),
        allowDbWrite: parseBooleanLike(input.allowDbWrite, false),
        all: parseBooleanLike(input.all, false),
        allLeagues: parseBooleanLike(input.allLeagues, false),
        fullSync: parseBooleanLike(input.fullSync, false),
        networkAuthorization: parseBooleanLike(input.networkAuthorization, false),
    };
}

function pushIf(condition, errors, message) {
    if (condition) {
        errors.push(message);
    }
}

function validateSourceAndScope(input, errors) {
    if (!input.source) {
        errors.push('missing source: provide --source=fotmob');
    } else if (input.source !== SAFE_SOURCE) {
        errors.push(`unsupported source: only ${SAFE_SOURCE} is allowed in Phase 5.04L1`);
    }

    if (!input.scope) {
        errors.push(
            'missing scope: provide --scope=<config_only_preview|league_season_date|league_season_window_preview|controlled_candidates_preview>'
        );
    } else if (!SAFE_SCOPES.has(input.scope)) {
        errors.push(`unsupported scope: ${input.scope}`);
    }
}

function validateBlockedFlags(input, errors) {
    pushIf(input.all, errors, 'bulk flag not allowed: --all is blocked in Phase 5.05L1');
    pushIf(input.allLeagues, errors, 'bulk flag not allowed: --all-leagues is blocked in Phase 5.05L1');
    pushIf(input.fullSync, errors, 'bulk flag not allowed: --full-sync is blocked in Phase 5.05L1');
    pushIf(input.commit, errors, BLOCKED_COMMIT_MESSAGE);
    pushIf(input.dryRun !== true, errors, 'dry_run=false is not allowed: preview wrapper is fixed to dry-run mode');
    pushIf(input.dbWrite === true, errors, 'db_write=true is not allowed in Phase 5.05L1');
    pushIf(input.allowDbWrite === true, errors, 'ALLOW_DB_WRITE=yes is not allowed in Phase 5.05L1');
    pushIf(input.browser === true, errors, 'browser=true is not allowed in Phase 5.05L1');
    pushIf(input.allowBrowserRuntime === true, errors, 'ALLOW_BROWSER_RUNTIME=yes is not allowed in Phase 5.05L1');
    pushIf(input.proxy === true, errors, 'proxy=true is not allowed in Phase 5.05L1');
    pushIf(input.allowProxyRuntime === true, errors, 'ALLOW_PROXY_RUNTIME=yes is not allowed in Phase 5.05L1');
}

function validateLimits(input, errors) {
    if (!Number.isInteger(input.concurrency) || input.concurrency < 1) {
        errors.push('invalid concurrency: provide a positive integer');
    } else if (input.concurrency > 1) {
        errors.push('concurrency > 1 is blocked in Phase 5.05L1');
    }

    if (!Number.isInteger(input.maxTargets) || input.maxTargets < 1) {
        errors.push('invalid max_targets: provide a positive integer');
    } else if (input.maxTargets > MAX_CONTROLLED_NETWORK_TARGETS) {
        errors.push(`max_targets > ${MAX_CONTROLLED_NETWORK_TARGETS} is blocked in Phase 5.05L1`);
    }

    if (!Number.isInteger(input.lookback) || input.lookback < 0) {
        errors.push('invalid lookback: provide a non-negative integer');
    }
    if (!Number.isInteger(input.lookahead) || input.lookahead < 0) {
        errors.push('invalid lookahead: provide a non-negative integer');
    }
}

function validateLeagueScope(input, errors) {
    const isLeagueScope =
        input.scope === 'league_season_date' ||
        input.scope === 'league_season_window_preview' ||
        input.scope === CONTROLLED_CANDIDATES_SCOPE;

    if (!isLeagueScope) {
        return;
    }

    if (!input.leagueId) {
        errors.push('missing league-id for league scope');
    } else if (!Number.isInteger(parseIntegerLike(input.leagueId, Number.NaN)) || Number(input.leagueId) <= 0) {
        errors.push('invalid league-id: provide a positive integer');
    }

    if (!input.season) {
        errors.push('missing season for league scope');
    }

    if (input.scope === 'league_season_date' || input.scope === CONTROLLED_CANDIDATES_SCOPE) {
        if (!input.date) {
            errors.push(`missing date for ${input.scope} scope`);
        } else if (!parseDateStrict(input.date)) {
            errors.push('invalid date: provide YYYY-MM-DD');
        }
    }
}

function validateNetworkPreview(input, errors) {
    if (!input.networkPreview) {
        return;
    }

    if (input.source !== SAFE_SOURCE) {
        return;
    }
    if (input.scope !== CONTROLLED_CANDIDATES_SCOPE) {
        errors.push('network preview requires scope=controlled_candidates_preview');
    }
    if (input.networkAuthorization !== true) {
        errors.push('network preview requires NETWORK_AUTHORIZATION=yes');
    }
    if (input.concurrency !== 1) {
        errors.push('network preview requires CONCURRENCY=1');
    }
    if (input.maxTargets > MAX_CONTROLLED_NETWORK_TARGETS) {
        errors.push(`network preview requires MAX_TARGETS<=${MAX_CONTROLLED_NETWORK_TARGETS}`);
    }
}

function validateSafePreviewInput(input) {
    const errors = [];
    const normalized = normalizeSafePreviewInput(input);

    validateSourceAndScope(normalized, errors);
    validateBlockedFlags(normalized, errors);
    validateLimits(normalized, errors);
    validateLeagueScope(normalized, errors);
    validateNetworkPreview(normalized, errors);

    return {
        ok: errors.length === 0,
        errors,
        value: {
            ...normalized,
            source: normalized.source || null,
            scope: normalized.scope || null,
            season: normalized.season || null,
            date: normalized.date || null,
            dryRun: true,
            commit: false,
            dbWrite: false,
            browser: false,
            proxy: false,
            networkPreview: normalized.networkPreview,
            allowBrowserRuntime: false,
            allowProxyRuntime: false,
            allowDbWrite: false,
            all: false,
            allLeagues: false,
            fullSync: false,
            networkAuthorization: normalized.networkAuthorization,
        },
    };
}

function loadLeagueConfigSafe(input, dependencies = {}) {
    const configManager = dependencies.configManager || new L1ConfigManager();
    if (!input.leagueIdNumber) {
        return { found: false, league: null };
    }

    const league = configManager.getLeagueById(input.leagueIdNumber);
    return {
        found: Boolean(league),
        league: league || null,
    };
}

function loadSeasonWindowSafe(input, dependencies = {}) {
    const configManager = dependencies.configManager || new L1ConfigManager();
    if (!input.leagueIdNumber || !input.season) {
        return {
            found: false,
            window: null,
            expectedMatches: null,
        };
    }

    const window = configManager.getSeasonDateWindow(input.leagueIdNumber, input.season);
    const expectedMatches = configManager.getExpectedMatches(input.leagueIdNumber, input.season);

    return {
        found: Boolean(window),
        window: window || null,
        expectedMatches: expectedMatches || null,
    };
}

function buildSafetySummary(input, metadata = {}) {
    return {
        phase: PHASE,
        preview_only: true,
        safe_for_ai_default: true,
        source: input.source,
        scope: input.scope,
        league_id: input.leagueId,
        season: input.season,
        date: input.date,
        concurrency: input.concurrency,
        max_targets: input.maxTargets,
        bulk_allowed: false,
        full_sync_allowed: false,
        all_leagues_allowed: false,
        network_execution_allowed: input.networkPreview === true && input.networkAuthorization === true,
        controlled_external_network_preview_allowed:
            input.networkPreview === true && input.networkAuthorization === true,
        browser_runtime_allowed: false,
        proxy_runtime_allowed: false,
        db_write_allowed: false,
        matches_write_allowed: false,
        raw_match_data_write_allowed: false,
        candidates_preview_available: input.scope === CONTROLLED_CANDIDATES_SCOPE,
        discover_candidates_available: true,
        training_allowed: false,
        prediction_allowed: false,
        would_access_network: input.networkPreview === true,
        external_network_used: false,
        network_authorization_used: false,
        source_url_used: null,
        would_launch_browser: false,
        would_use_proxy: false,
        would_call_titan_discovery: false,
        would_call_discovery_service_discover: false,
        would_call_fixture_repository_persist: false,
        would_call_persist: false,
        would_write_matches: false,
        would_write_raw_match_data: false,
        would_write_db: false,
        would_train: false,
        would_predict: false,
        would_create_files: false,
        would_spawn_child_process: false,
        network_authorization_requested: input.networkAuthorization === true,
        network_authorization_effective: input.networkPreview === true && input.networkAuthorization === true,
        network_authorization_status:
            input.networkAuthorization === true && input.networkPreview === true
                ? 'authorized_phase_5_05l1_controlled_network_preview'
                : input.networkAuthorization === true
                  ? 'blocked_without_network_preview_target'
                  : 'not_requested',
        candidate_count: 0,
        candidates: [],
        safety_classification: 'safe_preview_only',
        commit_gate: 'blocked',
        next_required_phase: NEXT_REQUIRED_PHASE,
        registry_reference: metadata.registryReference || null,
    };
}

function buildSourceUrlPreview(configManager, input) {
    if (input.leagueIdNumber && input.season) {
        return configManager.buildLeagueApiUrl(input.leagueIdNumber, input.season);
    }

    return 'https://www.fotmob.com/api/data/leagues?id={providerLeagueId}&season={season}';
}

function buildWindowPreview(input, seasonWindow, dependencies = {}) {
    if (!seasonWindow.found || !seasonWindow.window?.start || !seasonWindow.window?.end) {
        return null;
    }

    const referenceDate = dependencies.referenceDate instanceof Date ? dependencies.referenceDate : new Date();
    const seasonStart = parseDateStrict(seasonWindow.window.start);
    const seasonEnd = parseDateStrict(seasonWindow.window.end);
    if (!seasonStart || !seasonEnd) {
        return null;
    }

    const tentativeStart = clampDateRange(referenceDate, -1 * input.lookback);
    const tentativeEnd = clampDateRange(referenceDate, input.lookahead);
    const boundedStart = tentativeStart < seasonStart ? seasonStart : tentativeStart;
    const boundedEnd = tentativeEnd > seasonEnd ? seasonEnd : tentativeEnd;

    return {
        start: toDateOnlyText(boundedStart),
        end: toDateOnlyText(boundedEnd),
        season_start: seasonWindow.window.start,
        season_end: seasonWindow.window.end,
        reference_date: toDateOnlyText(referenceDate),
        lookback_days: input.lookback,
        lookahead_days: input.lookahead,
        source: seasonWindow.window.source || 'explicit_or_derived',
    };
}

function assertFotMobLeagueApiUrl(sourceUrl) {
    let parsed;
    try {
        parsed = new URL(sourceUrl);
    } catch (error) {
        throw new Error(`invalid FotMob source URL: ${error.message}`);
    }

    if (
        parsed.protocol !== 'https:' ||
        parsed.hostname !== 'www.fotmob.com' ||
        parsed.pathname !== '/api/data/leagues'
    ) {
        throw new Error('blocked source URL: only https://www.fotmob.com/api/data/leagues is allowed');
    }

    if (!parsed.searchParams.get('id') || !parsed.searchParams.get('season')) {
        throw new Error('blocked source URL: FotMob league API requires id and season');
    }
}

function classifyBlockText(bodyText) {
    const normalized = String(bodyText || '').toLowerCase();
    return ['captcha', 'cloudflare', 'access denied', 'too many requests', 'blocked', 'rate limit'].some(pattern =>
        normalized.includes(pattern)
    );
}

function buildNetworkError(message, context = {}) {
    const error = new Error(message);
    error.statusCode = context.statusCode || null;
    error.code = context.code || null;
    error.sourceUrl = context.sourceUrl || null;
    return error;
}

function createSafeFotMobNetworkClient(dependencies = {}) {
    const fetchImpl = dependencies.fetch || global.fetch;
    const timeoutMs = Number.parseInt(String(dependencies.timeoutMs || 15000), 10);

    return async request => {
        assertFotMobLeagueApiUrl(request.sourceUrl);
        if (request.source !== SAFE_SOURCE) {
            throw new Error(`unsupported source for safe network client: ${request.source}`);
        }
        if (request.concurrency !== 1) {
            throw new Error('safe network client requires concurrency=1');
        }
        if (
            !Number.isInteger(Number(request.maxTargets)) ||
            Number(request.maxTargets) > MAX_CONTROLLED_NETWORK_TARGETS
        ) {
            throw new Error(`safe network client requires maxTargets<=${MAX_CONTROLLED_NETWORK_TARGETS}`);
        }
        if (request.networkAuthorization !== true) {
            throw new Error('safe network client requires networkAuthorization=true');
        }
        if (typeof fetchImpl !== 'function') {
            throw new Error('global fetch is unavailable for controlled network preview');
        }

        const controller = typeof AbortController === 'function' ? new AbortController() : null;
        const timeout = controller
            ? setTimeout(() => {
                  controller.abort();
              }, timeoutMs)
            : null;

        try {
            const response = await fetchImpl(request.sourceUrl, {
                method: 'GET',
                headers: {
                    accept: 'application/json,text/plain;q=0.9,*/*;q=0.8',
                    'user-agent': 'FootballPrediction-L1CandidatesPreview/5.05',
                },
                signal: controller?.signal,
            });
            const statusCode = Number(response.status);
            const bodyText = await response.text();

            if (statusCode === 403 || statusCode === 429 || classifyBlockText(bodyText)) {
                throw buildNetworkError(`FotMob controlled network preview blocked with status ${statusCode}`, {
                    statusCode,
                    code: 'L1_DISCOVERY_CANDIDATES_NETWORK_BLOCKED',
                    sourceUrl: request.sourceUrl,
                });
            }
            if (!response.ok) {
                throw buildNetworkError(`FotMob controlled network preview failed with status ${statusCode}`, {
                    statusCode,
                    code: 'L1_DISCOVERY_CANDIDATES_FETCH_FAILED',
                    sourceUrl: request.sourceUrl,
                });
            }

            return JSON.parse(bodyText);
        } finally {
            if (timeout) {
                clearTimeout(timeout);
            }
        }
    };
}

function normalizeTeamName(value) {
    return String(value || '')
        .toLowerCase()
        .normalize('NFKD')
        .replace(/[\u0300-\u036f]/g, '')
        .replace(/[^a-z0-9]+/g, '');
}

function containsTargetMatchIdCandidate(candidates, targetId = TARGET_MATCH_ID_CANDIDATE) {
    return (Array.isArray(candidates) ? candidates : []).some(candidate =>
        [candidate?.external_id, candidate?.externalId, candidate?.id, candidate?.match_id, candidate?.matchId].some(
            value => String(value || '').includes(targetId)
        )
    );
}

function containsAngersStrasbourgCandidate(candidates) {
    return (Array.isArray(candidates) ? candidates : []).some(candidate => {
        const home = normalizeTeamName(candidate?.home || candidate?.home_team);
        const away = normalizeTeamName(candidate?.away || candidate?.away_team);
        return (
            (home.includes('angers') && away.includes('strasbourg')) ||
            (home.includes('strasbourg') && away.includes('angers'))
        );
    });
}

function resolveDiscoveryServiceFactory(dependencies = {}) {
    if (dependencies.discoveryService) {
        return () => dependencies.discoveryService;
    }

    if (typeof dependencies.createDiscoveryService === 'function') {
        return dependencies.createDiscoveryService;
    }

    if (dependencies.allowDiscoveryServiceImport === false) {
        return null;
    }

    return () => {
        const { DiscoveryService } = require('../../src/infrastructure/services/DiscoveryService');
        return new DiscoveryService({
            silent: true,
            disableDbPool: true,
            disableBrowserProvider: true,
            disableProxyProvider: true,
            disableHttpClient: true,
            disableFixtureRepository: true,
        });
    };
}

async function buildControlledCandidatesPreview(input, context, dependencies = {}) {
    const createDiscoveryService = resolveDiscoveryServiceFactory(dependencies);
    const basePreview = buildCandidatePreview(input, context, dependencies);

    basePreview.mode = 'controlled_candidates_preview';
    basePreview.plan_summary = {
        preview_kind: CONTROLLED_CANDIDATES_SCOPE,
        network_execution: input.networkPreview ? 'authorized_controlled_external_preview' : 'blocked_by_default',
        network_authorization_requested: input.networkAuthorization === true,
        network_authorization_effective: input.networkPreview === true && input.networkAuthorization === true,
        persistence: 'blocked',
        browser_runtime: 'blocked',
        proxy_runtime: 'blocked',
    };
    basePreview.discover_candidates_available = true;
    basePreview.candidates_preview_available = true;
    basePreview.external_network_used = false;
    basePreview.network_authorization_used = false;
    basePreview.source_url_used = null;
    basePreview.candidate_count = 0;
    basePreview.candidates = [];

    if (!createDiscoveryService) {
        basePreview.fetch_mode = 'plan_only_no_service_import';
        return {
            preview: basePreview,
            candidateResult: null,
        };
    }

    const fetchLeagueFixtures =
        dependencies.fetchLeagueFixtures ||
        (input.networkPreview
            ? createSafeFotMobNetworkClient({
                  fetch: dependencies.fetch,
                  timeoutMs: dependencies.timeoutMs,
              })
            : null);
    const networkKind = dependencies.networkKind || (input.networkPreview ? 'external' : 'none');
    const service = createDiscoveryService({ input, context, dependencies });
    if (!service || typeof service.discoverCandidates !== 'function') {
        throw new Error('discoverCandidates provider is not available');
    }

    try {
        const candidateResult = await service.discoverCandidates(
            {
                source: input.source,
                scope: input.scope,
                leagueId: input.leagueId,
                season: input.season,
                date: input.date,
                lookback: input.lookback,
                lookahead: input.lookahead,
                concurrency: input.concurrency,
                maxTargets: input.maxTargets,
                dryRun: true,
                allowNetwork: input.networkPreview === true || dependencies.allowFakeNetwork === true,
                networkAuthorization: input.networkAuthorization === true || dependencies.allowFakeNetwork === true,
                allowBrowserFallback: false,
                allowProxy: false,
                writeDb: false,
                previewOnly: true,
            },
            {
                fetchLeagueFixtures,
                parser: dependencies.parser,
                logger: dependencies.logger,
                repository: dependencies.repository,
                browserProvider: dependencies.browserProvider,
                networkKind: dependencies.allowFakeNetwork === true ? 'fake' : networkKind,
            }
        );

        const candidates = Array.isArray(candidateResult.candidates)
            ? candidateResult.candidates.slice(0, input.maxTargets)
            : [];
        basePreview.fetch_mode = candidateResult.fetch_mode || 'discover_candidates';
        basePreview.source_url_candidate = candidateResult.source_url_candidate || basePreview.source_url_template;
        basePreview.source_url_used = candidateResult.source_url_used || null;
        basePreview.external_network_used = candidateResult.external_network_used === true;
        basePreview.network_authorization_used = candidateResult.network_authorization_used === true;
        basePreview.candidate_count = Number(candidateResult.candidate_count) || candidates.length;
        basePreview.candidates = candidates;
        basePreview.safety_summary = candidateResult.safety_summary || null;

        return {
            preview: basePreview,
            candidateResult,
        };
    } finally {
        if (service && typeof service.close === 'function') {
            await service.close();
        }
    }
}

function buildCandidatePreview(input, context, dependencies = {}) {
    const { configManager, leagueConfig, seasonWindow } = context;
    const sourceUrlTemplate = buildSourceUrlPreview(configManager, input);

    const basePreview = {
        mode: 'config_only_or_plan_only',
        source_url_template: sourceUrlTemplate,
        league_config_found: leagueConfig.found,
        season_window_found: seasonWindow.found,
        estimated_target_limit: input.maxTargets,
        would_do: ['load local L1 config', 'load local season window config', 'emit bounded preview JSON only'],
    };

    if (leagueConfig.league) {
        basePreview.league = {
            id: leagueConfig.league.id,
            code: leagueConfig.league.code,
            name: leagueConfig.league.name,
            country: leagueConfig.league.country,
            tier: leagueConfig.league.tier,
            provider_id: leagueConfig.league.providerId,
        };
    }

    if (seasonWindow.window) {
        basePreview.season_window = {
            start: seasonWindow.window.start,
            end: seasonWindow.window.end,
            source: seasonWindow.window.source || 'explicit_or_derived',
            expected_matches: seasonWindow.expectedMatches,
        };
    }

    if (input.scope === 'config_only_preview') {
        basePreview.plan_summary = {
            preview_kind: 'config_only',
            network_execution: 'blocked',
            persistence: 'blocked',
            browser_runtime: 'blocked',
            proxy_runtime: 'blocked',
        };
        return basePreview;
    }

    if (input.scope === 'league_season_date') {
        const targetDate = parseDateStrict(input.date);
        basePreview.plan_summary = {
            preview_kind: 'single_date_plan',
            target_date: input.date,
            date_in_season_window: Boolean(
                targetDate &&
                seasonWindow.window?.start &&
                seasonWindow.window?.end &&
                input.date >= seasonWindow.window.start &&
                input.date <= seasonWindow.window.end
            ),
            bounded_target_count: 1,
        };
        return basePreview;
    }

    basePreview.plan_summary = {
        preview_kind: 'season_window_plan',
        bounded_window: buildWindowPreview(input, seasonWindow, dependencies),
        bounded_target_count: input.maxTargets,
    };
    return basePreview;
}

async function buildL1DiscoveryPlanPreview(input, dependencies = {}) {
    const validation = validateSafePreviewInput(input);
    if (!validation.ok) {
        const error = new Error(validation.errors[0]);
        error.validationErrors = validation.errors;
        throw error;
    }

    const normalizedInput = validation.value;
    const configManager = dependencies.configManager || new L1ConfigManager();
    const leagueConfig = loadLeagueConfigSafe(normalizedInput, { configManager });
    const seasonWindow = loadSeasonWindowSafe(normalizedInput, { configManager });
    const registryMetadata = loadTitanDiscoveryRegistryMetadata(dependencies);

    if (normalizedInput.scope !== 'config_only_preview' && !leagueConfig.found) {
        throw new Error(`league config not found for league-id ${normalizedInput.leagueId}`);
    }

    const registryReference = registryMetadata.engine
        ? {
              engine_id: registryMetadata.engine.id,
              accesses_network: registryMetadata.engine.accesses_network,
              writes_db: registryMetadata.engine.writes_db,
              dry_run_trust_level: registryMetadata.engine.dry_run_trust_level,
              safe_for_ai_default: registryMetadata.engine.safe_for_ai_default,
              phase454_policy: registryMetadata.engine.phase454_policy,
          }
        : null;

    const payload = {
        ...buildSafetySummary(normalizedInput, { registryReference }),
        candidate_preview: buildCandidatePreview(
            normalizedInput,
            {
                configManager,
                leagueConfig,
                seasonWindow,
            },
            dependencies
        ),
    };

    if (normalizedInput.scope !== CONTROLLED_CANDIDATES_SCOPE) {
        return payload;
    }

    const controlledPreview = await buildControlledCandidatesPreview(
        normalizedInput,
        {
            configManager,
            leagueConfig,
            seasonWindow,
        },
        dependencies
    );
    const candidateResult = controlledPreview.candidateResult || {};
    const candidates = Array.isArray(controlledPreview.preview.candidates) ? controlledPreview.preview.candidates : [];

    return {
        ...payload,
        candidates_preview_available: true,
        discover_candidates_available: true,
        external_network_used: controlledPreview.preview.external_network_used === true,
        network_authorization_used: controlledPreview.preview.network_authorization_used === true,
        candidate_count: Number(controlledPreview.preview.candidate_count) || candidates.length,
        candidates,
        candidates_preview: candidates,
        contains_target_match_id_candidate: containsTargetMatchIdCandidate(candidates),
        contains_anglers_strasbourg_candidate: containsAngersStrasbourgCandidate(candidates),
        contains_angers_strasbourg_candidate: containsAngersStrasbourgCandidate(candidates),
        source_url_template:
            controlledPreview.preview.source_url_template || buildSourceUrlPreview(configManager, normalizedInput),
        source_url_candidate:
            controlledPreview.preview.source_url_candidate || buildSourceUrlPreview(configManager, normalizedInput),
        source_url_used: controlledPreview.preview.source_url_used || null,
        network_used: controlledPreview.preview.external_network_used === true || candidateResult.network_used === true,
        browser_used: false,
        proxy_used: false,
        db_written: false,
        matches_written: false,
        raw_match_data_written: false,
        safety_summary: candidateResult.safety_summary || {
            would_write_db: false,
            would_call_persist: false,
            would_launch_browser: false,
            would_use_proxy: false,
        },
        candidate_preview: controlledPreview.preview,
    };
}

function buildErrorPayload(options, errors, mode = 'validation-error') {
    const safeInput = validateSafePreviewInput({
        ...options,
        source: options.source || null,
        scope: options.scope || null,
        dryRun: options.dryRun === undefined ? true : options.dryRun,
        commit: false,
        dbWrite: false,
        browser: false,
        proxy: false,
        networkPreview: options.networkPreview,
        allowBrowserRuntime: false,
        allowProxyRuntime: false,
        allowDbWrite: false,
        all: false,
        allLeagues: false,
        fullSync: false,
        networkAuthorization: options.networkAuthorization,
    }).value;

    return {
        ...buildSafetySummary(safeInput),
        ok: false,
        mode,
        errors: Array.isArray(errors) ? errors : [String(errors)],
        contains_target_match_id_candidate: false,
        contains_anglers_strasbourg_candidate: false,
        contains_angers_strasbourg_candidate: false,
    };
}

function showHelp(io = {}) {
    const stdout = io.stdout || (text => process.stdout.write(text));
    stdout(
        [
            'L1 discovery safe preview wrapper',
            '',
            '用法:',
            '  node scripts/ops/l1_discovery_safe_preview.js --source=fotmob --scope=league_season_date --league-id=53 --season=2025/2026 --date=2026-05-10 --concurrency=1 --max-targets=1',
            '  node scripts/ops/l1_discovery_safe_preview.js --network-preview=true --source=fotmob --scope=controlled_candidates_preview --league-id=53 --season=2025/2026 --date=2026-05-10 --concurrency=1 --max-targets=10 --network-authorization=yes',
            '',
            '允许 scope:',
            '  config_only_preview',
            '  league_season_date',
            '  league_season_window_preview',
            '  controlled_candidates_preview',
            '',
            'Phase 5.05L1 约束:',
            '  preview-only',
            '  network only when --network-preview=true and --network-authorization=yes',
            '  no browser',
            '  no proxy',
            '  no DB write',
            '  commit blocked',
            '',
        ].join('\n')
    );
}

async function runCli(argv = process.argv.slice(2), io = {}, dependencies = {}) {
    const stdout = io.stdout || (text => process.stdout.write(text));
    const stderr = io.stderr || (text => process.stderr.write(text));
    const options = parseArgs(argv);

    if (options.help) {
        showHelp({ stdout });
        return 0;
    }

    if (options.commit === true) {
        const payload = buildErrorPayload(options, [BLOCKED_COMMIT_MESSAGE], 'blocked-commit');
        payload.blocked_reason = BLOCKED_COMMIT_MESSAGE;
        stderr(`${BLOCKED_COMMIT_MESSAGE}\n`);
        stdout(`${JSON.stringify(payload, null, 2)}\n`);
        return 1;
    }

    const validation = validateSafePreviewInput(options);
    if (!validation.ok) {
        const payload = buildErrorPayload(options, validation.errors);
        stderr(`${validation.errors[0]}\n`);
        stdout(`${JSON.stringify(payload, null, 2)}\n`);
        return 1;
    }

    if (validation.value.networkAuthorization === true && validation.value.networkPreview !== true) {
        const payload = buildErrorPayload(
            options,
            ['BLOCKED: external L1 network execution requires data-l1-discovery-candidates-network-preview.'],
            'blocked-network-authorization'
        );
        payload.blocked_reason =
            'BLOCKED: external L1 network execution requires data-l1-discovery-candidates-network-preview.';
        payload.candidates_preview_available = validation.value.scope === CONTROLLED_CANDIDATES_SCOPE;
        payload.discover_candidates_available = true;
        payload.external_network_used = false;
        payload.network_execution_allowed = false;
        stderr(`${payload.blocked_reason}\n`);
        stdout(`${JSON.stringify(payload, null, 2)}\n`);
        return 1;
    }

    try {
        const payload = await buildL1DiscoveryPlanPreview(validation.value, dependencies);
        stdout(`${JSON.stringify(payload, null, 2)}\n`);
        return 0;
    } catch (error) {
        const mode =
            error.code === 'L1_DISCOVERY_CANDIDATES_NETWORK_BLOCKED'
                ? 'controlled-network-blocked'
                : error.code === 'L1_DISCOVERY_CANDIDATES_FETCH_FAILED'
                  ? 'controlled-network-error'
                  : 'validation-error';
        const payload = buildErrorPayload(options, error.validationErrors || [error.message], mode);
        payload.external_network_used = error.externalNetworkUsed === true;
        payload.network_authorization_used = error.networkAuthorizationUsed === true;
        payload.source_url_used = error.sourceUrl || null;
        payload.status_code = error.statusCode || null;
        payload.retry_count = Number.isInteger(error.retryCount) ? error.retryCount : 0;
        stderr(`${error.message}\n`);
        stdout(`${JSON.stringify(payload, null, 2)}\n`);
        return 1;
    }
}

if (require.main === module) {
    runCli()
        .then(exitCode => {
            process.exitCode = exitCode;
        })
        .catch(error => {
            process.stderr.write(`${error.message}\n`);
            process.exitCode = 1;
        });
}

module.exports = {
    parseArgs,
    validateSafePreviewInput,
    buildL1DiscoveryPlanPreview,
    loadLeagueConfigSafe,
    loadSeasonWindowSafe,
    buildSafetySummary,
    buildControlledCandidatesPreview,
    createSafeFotMobNetworkClient,
    containsTargetMatchIdCandidate,
    containsAngersStrasbourgCandidate,
    runCli,
};
