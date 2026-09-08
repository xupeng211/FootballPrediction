'use strict';

const API_HOST = 'api.the-odds-api.com';
const API_PATH = '/v4/sports/soccer_epl/odds';
const MAX_REQUESTS = 3;
const DIRECT_TRANSPORT = 'DIRECT';
const STABLE_PROXY_TRANSPORT = 'STABLE_PROXY';
const DEFAULT_TIMEOUT_MS = 15000;

function sanitizeHeaders(headers = {}) {
    const quotaHeader =
        /^(?:x-(?:requests|ratelimit|credits)-(?:remaining|used|limit|reset)|ratelimit-(?:remaining|used|limit|reset))$/i;
    return Object.entries(headers).reduce((result, [key, value]) => {
        const normalizedKey = key.toLowerCase();
        if (!quotaHeader.test(normalizedKey)) return result;
        result[normalizedKey] = String(value);
        return result;
    }, {});
}

function failRetiredLiveTransport() {
    throw new Error(
        'The Odds API live transport is retired: a future transmission requires the Stage D controlled adapter, '
        + 'global run lock, durable request ledger and verified quota gate'
    );
}

function buildRequestUrl({ regions = 'uk', markets = 'h2h', oddsFormat = 'decimal' } = {}) {
    void regions;
    void markets;
    void oddsFormat;
    return failRetiredLiveTransport();
}

function createDirectRequestFn({ httpsModule = null, timeoutMs = DEFAULT_TIMEOUT_MS, agent } = {}) {
    void httpsModule;
    void timeoutMs;
    void agent;
    return failRetiredLiveTransport();
}

function createStableProxyRequestFn({
    proxyUrl = process.env.THE_ODDS_API_PROXY_URL,
    timeoutMs = DEFAULT_TIMEOUT_MS,
    agent,
} = {}) {
    void proxyUrl;
    void timeoutMs;
    void agent;
    return failRetiredLiveTransport();
}

function resolveTransportPolicy(value = process.env.THE_ODDS_API_TRANSPORT || 'direct') {
    const normalized = String(value).trim().toLowerCase();
    if (normalized === 'direct') return DIRECT_TRANSPORT;
    if (normalized === 'stable_proxy') return STABLE_PROXY_TRANSPORT;
    throw new Error('THE_ODDS_API_TRANSPORT must be direct or stable_proxy');
}

function createTransportRequestFn(options = {}) {
    const policy = resolveTransportPolicy(options.transport);
    if (policy === DIRECT_TRANSPORT) return createDirectRequestFn(options);
    return createStableProxyRequestFn(options);
}

function captureEplOdds({ request = {}, requestFn = createDirectRequestFn(), captureNon200 = false } = {}) {
    void request;
    void requestFn;
    void captureNon200;
    return failRetiredLiveTransport();
}

function createTheOddsApiClient(options = {}) {
    void options;
    return Object.freeze({
        get request_count() {
            return 0;
        },
        transport: 'RETIRED',
        capture(request = {}) {
            void request;
            return failRetiredLiveTransport();
        },
    });
}

module.exports = {
    API_HOST,
    API_PATH,
    DIRECT_TRANSPORT,
    STABLE_PROXY_TRANSPORT,
    DEFAULT_TIMEOUT_MS,
    MAX_REQUESTS,
    buildRequestUrl,
    createDirectRequestFn,
    createStableProxyRequestFn,
    createTransportRequestFn,
    captureEplOdds,
    createTheOddsApiClient,
    resolveTransportPolicy,
    sanitizeHeaders,
};
