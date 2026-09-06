'use strict';

const https = require('node:https');
const { HttpsProxyAgent } = require('https-proxy-agent');
const { sha256Text } = require('./contracts');
const { sanitizeRequestParameters } = require('./evidenceStore');

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

function buildRequestUrl({ regions = 'uk', markets = 'h2h', oddsFormat = 'decimal' } = {}) {
    const apiKey = process.env.THE_ODDS_API_KEY;
    if (!apiKey) throw new Error('THE_ODDS_API_KEY is required for live capture');
    if (markets !== 'h2h' || oddsFormat !== 'decimal') {
        throw new Error('Stage C live client only permits EPL h2h decimal odds');
    }
    const sanitized = sanitizeRequestParameters({ regions, markets, oddsFormat });
    const params = new URLSearchParams({ apiKey, ...sanitized });
    return `https://${API_HOST}${API_PATH}?${params.toString()}`;
}

function createDirectRequestFn({ httpsModule = https, timeoutMs = DEFAULT_TIMEOUT_MS, agent } = {}) {
    if (!Number.isInteger(timeoutMs) || timeoutMs <= 0) throw new Error('direct transport timeout must be positive');
    if (!httpsModule || typeof httpsModule.request !== 'function' || typeof httpsModule.Agent !== 'function') {
        throw new Error('native HTTPS transport is required');
    }
    // Node's native https.request has no environment proxy resolution. Supplying
    // a native Agent makes the provider policy explicit and excludes SOCKS agents.
    const directAgent = agent || new httpsModule.Agent({ keepAlive: false });
    return (url, options, callback) => {
        const parsed = new URL(url);
        if (parsed.protocol !== 'https:' || parsed.hostname !== API_HOST) {
            throw new Error('The Odds API direct transport target is invalid');
        }
        const request = httpsModule.request(
            {
                protocol: 'https:',
                hostname: API_HOST,
                port: 443,
                method: 'GET',
                path: `${parsed.pathname}${parsed.search}`,
                headers: options.headers,
                agent: directAgent,
                rejectUnauthorized: true,
            },
            callback
        );
        request.setTimeout(timeoutMs, () => request.destroy(new Error('The Odds API direct request timed out')));
        return request;
    };
}

function createStableProxyRequestFn({
    proxyUrl = process.env.THE_ODDS_API_PROXY_URL,
    timeoutMs = DEFAULT_TIMEOUT_MS,
    agent,
} = {}) {
    if (!Number.isInteger(timeoutMs) || timeoutMs <= 0) throw new Error('stable proxy timeout must be positive');
    if (typeof proxyUrl !== 'string' || !/^https?:\/\/[^\s]+$/i.test(proxyUrl)) {
        throw new Error('THE_ODDS_API_PROXY_URL must be an HTTP(S) proxy URL for stable_proxy transport');
    }
    // Request timeout is installed below. HttpsProxyAgent's own socket timeout
    // races CONNECT establishment on the local mixed proxy.
    const stableAgent = agent || new HttpsProxyAgent(proxyUrl, { keepAlive: false });
    return (url, options, callback) => {
        const parsed = new URL(url);
        if (parsed.protocol !== 'https:' || parsed.hostname !== API_HOST) {
            throw new Error('The Odds API stable proxy transport target is invalid');
        }
        const request = https.request(
            {
                protocol: 'https:',
                hostname: API_HOST,
                port: 443,
                method: 'GET',
                path: `${parsed.pathname}${parsed.search}`,
                headers: options.headers,
                agent: stableAgent,
                rejectUnauthorized: true,
            },
            callback
        );
        request.setTimeout(timeoutMs, () => request.destroy(new Error('The Odds API stable proxy request timed out')));
        return request;
    };
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

function directTransportError(error) {
    const code = typeof error?.code === 'string' && /^[A-Z0-9_]+$/.test(error.code) ? ` (${error.code})` : '';
    return new Error(`The Odds API direct transport failed${code}`);
}

function captureEplOdds({ request = {}, requestFn = createDirectRequestFn(), captureNon200 = false } = {}) {
    const requestCount = Number(request.request_count || 0);
    if (!Number.isInteger(requestCount) || requestCount < 0) {
        throw new Error('live request count is invalid');
    }
    if (requestCount >= MAX_REQUESTS) throw new Error(`live request limit exceeded (${MAX_REQUESTS})`);
    if (typeof requestFn !== 'function') throw new Error('a direct request transport is required');
    const url = buildRequestUrl(request);
    const started = new Date().toISOString();
    return new Promise((resolve, reject) => {
        const req = requestFn(url, { headers: { 'User-Agent': 'FootballPrediction-stage-c-pilot/1.0' } }, response => {
            const chunks = [];
            response.on('data', chunk => chunks.push(Buffer.from(chunk)));
            response.on('end', () => {
                const rawText = Buffer.concat(chunks).toString('utf8');
                const received = new Date().toISOString();
                if (response.statusCode !== 200 && !captureNon200) {
                    reject(
                        Object.assign(new Error(`The Odds API returned HTTP ${response.statusCode || 'UNKNOWN'}`), {
                            http_status: response.statusCode || null,
                        })
                    );
                    return;
                }
                resolve({
                    rawText,
                    raw_sha256: sha256Text(rawText),
                    request_started_at: started,
                    response_received_at: received,
                    ingested_at: received,
                    http_status: response.statusCode,
                    response_size_bytes: Buffer.byteLength(rawText),
                    provider_quota: sanitizeHeaders(response.headers),
                });
            });
            response.on('error', error => reject(directTransportError(error)));
        });
        req.on('error', error => reject(directTransportError(error)));
        if (typeof req.end === 'function') req.end();
    });
}

function createTheOddsApiClient(options = {}) {
    const transport = resolveTransportPolicy(options.transport);
    const requestFn = options.requestFn || createTransportRequestFn({ ...options, transport });
    let requestCount = 0;
    return Object.freeze({
        get request_count() {
            return requestCount;
        },
        transport,
        capture(request = {}) {
            if (requestCount >= MAX_REQUESTS) throw new Error(`live request limit exceeded (${MAX_REQUESTS})`);
            if (!process.env.THE_ODDS_API_KEY) throw new Error('THE_ODDS_API_KEY is required for live capture');
            requestCount += 1;
            return captureEplOdds({
                request: { ...request, request_count: requestCount - 1 },
                requestFn,
                captureNon200: options.captureNon200 === true,
            });
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
