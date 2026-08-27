'use strict';

const { sha256Text } = require('./contracts');
const { sanitizeRequestParameters } = require('./evidenceStore');

const API_HOST = 'api.the-odds-api.com';
const API_PATH = '/v4/sports/soccer_epl/odds';
const MAX_REQUESTS = 3;

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

function captureEplOdds({ request = {}, requestFn } = {}) {
    const requestCount = Number(request.request_count || 0);
    if (!Number.isInteger(requestCount) || requestCount < 0) {
        throw new Error('live request count is invalid');
    }
    if (requestCount >= MAX_REQUESTS) throw new Error(`live request limit exceeded (${MAX_REQUESTS})`);
    if (typeof requestFn !== 'function') throw new Error('a ProxyProvider-backed request transport is required');
    const url = buildRequestUrl(request);
    const started = new Date().toISOString();
    return new Promise((resolve, reject) => {
        const req = requestFn(url, { headers: { 'User-Agent': 'FootballPrediction-stage-c-pilot/1.0' } }, response => {
            const chunks = [];
            response.on('data', chunk => chunks.push(Buffer.from(chunk)));
            response.on('end', () => {
                const rawText = Buffer.concat(chunks).toString('utf8');
                const received = new Date().toISOString();
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
            response.on('error', reject);
        });
        req.on('error', reject);
    });
}

function createTheOddsApiClient({ requestFn } = {}) {
    let requestCount = 0;
    return Object.freeze({
        get request_count() {
            return requestCount;
        },
        capture(request = {}) {
            if (requestCount >= MAX_REQUESTS) throw new Error(`live request limit exceeded (${MAX_REQUESTS})`);
            if (!process.env.THE_ODDS_API_KEY) throw new Error('THE_ODDS_API_KEY is required for live capture');
            requestCount += 1;
            return captureEplOdds({ request: { ...request, request_count: requestCount - 1 }, requestFn });
        },
    });
}

module.exports = {
    API_HOST,
    API_PATH,
    MAX_REQUESTS,
    buildRequestUrl,
    captureEplOdds,
    createTheOddsApiClient,
    sanitizeHeaders,
};
