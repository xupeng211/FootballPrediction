'use strict';

// Stage D / The Odds API transport proxy contract.
//
// The Owner architecture decision for Stage D is a DEDICATED, PROJECT-CONTROLLED,
// SINGLE, STABLE HTTP CONNECT proxy endpoint.  It is deliberately not the
// rotating multi-node SOCKS5 pool that serves bulk harvesting (FotMob, OddsPortal,
// Playwright workers): that pool is sized for one worker per port, while a Stage D
// cycle issues at most one governed provider request.
//
// Two properties are load-bearing here and are enforced by construction:
//
//   1. FAIL CLOSED.  An absent or invalid endpoint raises before anything can be
//      transmitted.  There is no fallback to the rotating pool, to a workstation
//      proxy, or to a direct connection -- a silent fallback is exactly the defect
//      that spent the previous one-shot authorization.
//
//   2. PROVIDER-INDEPENDENT PROOF.  The preflight proves the endpoint speaks HTTP
//      CONNECT by sending a CONNECT for a deliberately unusable loopback address.
//      It never names the provider, so it cannot resolve provider DNS, cannot send
//      provider traffic, and cannot consume provider quota.

const net = require('node:net');
const tls = require('node:tls');

const STAGE_D_STABLE_PROXY_CONTRACT = 'stage-d-dedicated-single-stable-http-connect-proxy/v1';

// The canonical existing variable for this concept.  It is reused rather than
// duplicated: a second name for the same endpoint would be a configuration
// ambiguity, which is the failure mode this contract exists to remove.
const STAGE_D_PROXY_ENDPOINT_ENV_VAR = 'THE_ODDS_API_PROXY_URL';

const STAGE_D_PROXY_SUPPORTED_PROTOCOLS = Object.freeze(['http:', 'https:']);
const STAGE_D_PROXY_DEFAULT_PORTS = Object.freeze({ 'http:': 80, 'https:': 443 });

// A bounded probe.  The endpoint is expected to be local, on the LAN, or otherwise
// project-controlled, so the ceiling is deliberately far below the provider request
// timeout rather than inherited from it.
const STAGE_D_PROXY_PREFLIGHT_TIMEOUT_MS = 5000;

// The CONNECT target is a privileged, essentially never-bound loopback port on the
// proxy's own host, so the probe never asks the endpoint to reach anything real.  Because
// the destination is unusable by construction, a working proxy answers with a proxy-class
// refusal rather than an open tunnel; PROXY_CONNECT_PROOF_STATUSES below is the exact set
// of responses this contract treats as proof of HTTP CONNECT support.
const STAGE_D_PROXY_PROBE_DESTINATION = Object.freeze({ host: '127.0.0.1', port: 1 });

const STAGE_D_PROXY_PROBE_MAX_RESPONSE_BYTES = 8192;

// The only statuses that prove the endpoint implements HTTP CONNECT for this request.
//
// A 2xx means the tunnel opened.  403 is a proxy policy refusal, and 502/503/504 are the
// proxy failure classes for a tunnel that could not be established.  The probe destination
// is deliberately unusable, so a working proxy cannot answer 2xx here: a proxy-class
// refusal is the expected positive result, and 2xx is the rarer case.
//
// Everything else fails closed, because it proves nothing about the endpoint's ability to
// proxy the governed request.  400, 404, 405 and 501 are specifically what an ordinary HTTP
// origin server answers to a CONNECT it does not implement, and 405/501 are the signatures
// the reviewer of this contract named.  Accepting them would let a non-proxy endpoint pass
// the last gate before the one-shot authorization is spent -- the exact fail-open the
// STAGE_D_PROXY_FALLBACK=NONE invariant exists to prevent.  A missing status here is
// therefore a deliberate refusal, not an oversight.
const PROXY_CONNECT_PROOF_STATUSES = Object.freeze([403, 502, 503, 504]);

const PROXY_PREFLIGHT_PASS = 'PROXY_PREFLIGHT_PASS';
const PROXY_CONFIGURATION_MISSING = 'PROXY_CONFIGURATION_MISSING';
const PROXY_URL_INVALID = 'PROXY_URL_INVALID';
const PROXY_DNS_OR_ADDRESS_RESOLUTION_FAILURE = 'PROXY_DNS_OR_ADDRESS_RESOLUTION_FAILURE';
const PROXY_TCP_CONNECT_FAILED = 'PROXY_TCP_CONNECT_FAILED';
const PROXY_TLS_HANDSHAKE_FAILED = 'PROXY_TLS_HANDSHAKE_FAILED';
const PROXY_CONNECT_PROTOCOL_INVALID = 'PROXY_CONNECT_PROTOCOL_INVALID';
const PROXY_CONNECT_PREFLIGHT_TIMEOUT = 'PROXY_CONNECT_PREFLIGHT_TIMEOUT';
const PROXY_AUTHENTICATION_CONFIGURATION_FAILURE = 'PROXY_AUTHENTICATION_CONFIGURATION_FAILURE';
const STAGE_D_PROXY_PREFLIGHT_CONFIGURATION_INVALID = 'STAGE_D_PROXY_PREFLIGHT_CONFIGURATION_INVALID';

const PROXY_PREFLIGHT_CLASSIFICATIONS = Object.freeze([
    PROXY_PREFLIGHT_PASS,
    PROXY_CONFIGURATION_MISSING,
    PROXY_URL_INVALID,
    PROXY_DNS_OR_ADDRESS_RESOLUTION_FAILURE,
    PROXY_TCP_CONNECT_FAILED,
    PROXY_TLS_HANDSHAKE_FAILED,
    PROXY_CONNECT_PROTOCOL_INVALID,
    PROXY_CONNECT_PREFLIGHT_TIMEOUT,
    PROXY_AUTHENTICATION_CONFIGURATION_FAILURE,
]);

const DNS_FAILURE_CODES = Object.freeze(['ENOTFOUND', 'EAI_AGAIN', 'EAI_NODATA', 'EAI_FAIL', 'EAI_NONAME']);
const TLS_FAILURE_CODES = Object.freeze([
    'ERR_TLS_CERT_ALTNAME_INVALID',
    'ERR_SSL_WRONG_VERSION_NUMBER',
    'DEPTH_ZERO_SELF_SIGNED_CERT',
    'SELF_SIGNED_CERT_IN_CHAIN',
    'UNABLE_TO_GET_ISSUER_CERT_LOCALLY',
    'UNABLE_TO_VERIFY_LEAF_SIGNATURE',
    'CERT_HAS_EXPIRED',
    'CERT_NOT_YET_VALID',
]);
const TRANSPORT_FAILURE_CODES = Object.freeze([
    'ECONNREFUSED', 'ECONNRESET', 'EHOSTUNREACH', 'ENETUNREACH', 'EPIPE', 'ETIMEDOUT', 'EADDRNOTAVAIL',
]);

// Proxy credentials are held off the enumerable surface of the endpoint object so
// that JSON.stringify, Object.keys, spread and structured logging cannot carry them
// into evidence by accident.  Only buildStageDProxyAgentUrl reads them.
const PROXY_CREDENTIALS = Symbol('stageDStableProxyCredentials');

function failStageDProxy(code, message) {
    const error = new Error(message);
    error.code = code;
    throw error;
}

function classifyProxySocketError(error, { scheme, tlsEstablished }) {
    const code = typeof error?.code === 'string' ? error.code : '';
    if (DNS_FAILURE_CODES.includes(code)) return PROXY_DNS_OR_ADDRESS_RESOLUTION_FAILURE;
    if (TLS_FAILURE_CODES.includes(code) || code.startsWith('ERR_TLS') || code.startsWith('ERR_SSL')) return PROXY_TLS_HANDSHAKE_FAILED;
    if (TRANSPORT_FAILURE_CODES.includes(code)) return PROXY_TCP_CONNECT_FAILED;
    // An unclassified failure during an https:// handshake is a TLS problem; during
    // an http:// connect it is a transport problem.  Neither is ever treated as a pass.
    return scheme === 'https' && !tlsEstablished ? PROXY_TLS_HANDSHAKE_FAILED : PROXY_TCP_CONNECT_FAILED;
}

function redactStageDProxyEndpoint({ scheme, host, port, hasCredentials }) {
    return `${scheme}://${hasCredentials ? '<redacted>@' : ''}${host}:${port}`;
}

// Resolves the single stable endpoint, or fails closed.  This is the only place the
// Stage D proxy endpoint is read, so the transport and the preflight can never
// disagree about which endpoint is governed.
function resolveStageDStableProxyEndpoint(env = process.env) {
    const raw = env?.[STAGE_D_PROXY_ENDPOINT_ENV_VAR];
    if (typeof raw !== 'string' || raw.trim() === '') {
        // Repository-equivalent of PRODUCTION_PROXY_ENDPOINT_NOT_CONFIGURED.
        failStageDProxy(
            PROXY_CONFIGURATION_MISSING,
            `Stage D requires an explicit ${STAGE_D_PROXY_ENDPOINT_ENV_VAR} naming one stable HTTP CONNECT proxy endpoint; `
            + 'the rotating harvesting pool, a workstation proxy and a direct connection are all forbidden fallbacks',
        );
    }
    const candidate = raw.trim();
    let parsed;
    try {
        parsed = new URL(candidate);
    } catch {
        failStageDProxy(PROXY_URL_INVALID, `${STAGE_D_PROXY_ENDPOINT_ENV_VAR} must be an absolute URL such as http://proxy.internal:3128`);
    }
    if (!STAGE_D_PROXY_SUPPORTED_PROTOCOLS.includes(parsed.protocol)) {
        failStageDProxy(
            PROXY_URL_INVALID,
            `${STAGE_D_PROXY_ENDPOINT_ENV_VAR} must use http:// or https:// (HTTP CONNECT); `
            + `scheme "${parsed.protocol.replace(':', '')}" is not permitted for the Stage D provider transport`,
        );
    }
    if (typeof parsed.hostname !== 'string' || parsed.hostname === '') {
        failStageDProxy(PROXY_URL_INVALID, `${STAGE_D_PROXY_ENDPOINT_ENV_VAR} must name a host`);
    }
    const port = parsed.port === '' ? STAGE_D_PROXY_DEFAULT_PORTS[parsed.protocol] : Number(parsed.port);
    if (!Number.isInteger(port) || port < 1 || port > 65535) {
        failStageDProxy(PROXY_URL_INVALID, `${STAGE_D_PROXY_ENDPOINT_ENV_VAR} must name a port between 1 and 65535`);
    }
    const username = parsed.username;
    const password = parsed.password;
    const hasCredentials = username !== '' || password !== '';
    const endpoint = {
        scheme: parsed.protocol.slice(0, -1),
        host: parsed.hostname,
        // parsed.host preserves IPv6 bracketing for URL reconstruction.
        authority: parsed.host,
        port,
        has_credentials: hasCredentials,
        redacted: redactStageDProxyEndpoint({
            scheme: parsed.protocol.slice(0, -1),
            host: parsed.hostname,
            port,
            hasCredentials,
        }),
    };
    Object.defineProperty(endpoint, PROXY_CREDENTIALS, {
        value: hasCredentials ? Object.freeze({ username, password }) : null,
        enumerable: false,
    });
    return Object.freeze(endpoint);
}

// Re-attaches credentials only at the point the agent is constructed.  Callers must
// never log, persist or include the returned URL in an error message.
//
// `URL` hands back userinfo already percent-encoded, so re-encoding here would
// double-encode it: a password containing "@" would reach the proxy as "%40" and be
// rejected with a confusing 407.  The values are spliced in verbatim.
function buildStageDProxyAgentUrl(endpoint) {
    const credentials = endpoint[PROXY_CREDENTIALS];
    const auth = credentials
        ? `${credentials.username}:${credentials.password}@`
        : '';
    return `${endpoint.scheme}://${auth}${endpoint.authority}`;
}

function buildStageDConnectProbe(endpoint) {
    const destination = STAGE_D_PROXY_PROBE_DESTINATION;
    const credentials = endpoint[PROXY_CREDENTIALS];
    const authLine = credentials
        ? `Proxy-Authorization: Basic ${Buffer.from(`${credentials.username}:${credentials.password}`, 'utf8').toString('base64')}\r\n`
        : '';
    return `CONNECT ${destination.host}:${destination.port} HTTP/1.1\r\n`
        + `Host: ${destination.host}:${destination.port}\r\n`
        + authLine
        + '\r\n';
}

function probeStageDHttpConnectProxy({ endpoint, timeoutMs, clock }) {
    return new Promise(resolve => {
        const startedAt = clock();
        let settled = false;
        let socket = null;
        let tlsEstablished = false;
        let buffer = '';

        const settle = (classification, detail) => {
            if (settled) return;
            settled = true;
            if (socket) {
                socket.removeAllListeners();
                // destroy() itself emits only 'close', but a pending write or an RST can
                // still surface as 'error' with no listener left, which would throw out
                // of the event loop and take the governed process down with it.  A
                // classified failure must never become a crash.
                socket.on('error', () => undefined);
                socket.destroy();
            }
            resolve(Object.freeze({
                schema_version: 'footballprediction-stage-d-http-connect-proxy-preflight/v1',
                proxy_contract: STAGE_D_STABLE_PROXY_CONTRACT,
                classification,
                passed: classification === PROXY_PREFLIGHT_PASS,
                endpoint: endpoint.redacted,
                scheme: endpoint.scheme,
                host: endpoint.host,
                port: endpoint.port,
                has_credentials: endpoint.has_credentials,
                probe_destination: `${STAGE_D_PROXY_PROBE_DESTINATION.host}:${STAGE_D_PROXY_PROBE_DESTINATION.port}`,
                provider_contacted: false,
                provider_dns_resolved: false,
                started_at: startedAt,
                completed_at: clock(),
                detail: detail === undefined ? null : detail,
            }));
        };

        const onSocketError = error => {
            settle(classifyProxySocketError(error, { scheme: endpoint.scheme, tlsEstablished }), error?.code || null);
        };

        const onConnected = () => {
            if (endpoint.scheme === 'https') tlsEstablished = true;
            try {
                socket.write(buildStageDConnectProbe(endpoint));
            } catch (error) {
                settle(classifyProxySocketError(error, { scheme: endpoint.scheme, tlsEstablished }), error?.code || null);
            }
        };

        const onData = chunk => {
            buffer += chunk.toString('latin1');
            const firstLineEnd = buffer.indexOf('\n');
            if (firstLineEnd === -1) {
                if (buffer.length > STAGE_D_PROXY_PROBE_MAX_RESPONSE_BYTES) settle(PROXY_CONNECT_PROTOCOL_INVALID, 'response_too_large');
                return;
            }
            const firstLine = buffer.slice(0, firstLineEnd).replace(/\r$/, '');
            const match = /^HTTP\/1\.[01] (\d{3})(?: .*)?$/.exec(firstLine);
            if (!match) {
                // A listener that completes a first line which is not an HTTP status
                // line is not an HTTP proxy, no matter how long we wait.
                settle(PROXY_CONNECT_PROTOCOL_INVALID, 'non_http_status_line');
                return;
            }
            const status = Number(match[1]);
            if (status === 407) {
                // The endpoint is a proxy that understands CONNECT but will not authenticate
                // this request.  Whether that is because the configured secret is wrong or
                // because none was configured at all, the governed provider request could
                // not be authenticated either way, so the endpoint is not usable.  Failing
                // closed here is what keeps the one-shot authorization unspent.
                settle(
                    PROXY_AUTHENTICATION_CONFIGURATION_FAILURE,
                    endpoint.has_credentials
                        ? 'proxy_rejected_configured_credentials'
                        : 'proxy_authentication_required_but_no_credentials_configured',
                );
                return;
            }
            if ((status >= 200 && status < 300) || PROXY_CONNECT_PROOF_STATUSES.includes(status)) {
                settle(PROXY_PREFLIGHT_PASS, status >= 200 && status < 300 ? 'proxy_tunnel_established' : `proxy_status_${status}`);
                return;
            }
            // Anything else -- 400, 404, 405, 501 and the rest -- is what an ordinary HTTP
            // origin server answers to a CONNECT it does not implement.  It proves nothing
            // about the endpoint's ability to proxy the governed request, so it fails
            // closed rather than being recorded as a protocol proof.
            settle(PROXY_CONNECT_PROTOCOL_INVALID, `non_proxy_status_${status}`);
        };

        try {
            if (endpoint.scheme === 'https') {
                socket = tls.connect({
                    host: endpoint.host,
                    port: endpoint.port,
                    servername: net.isIP(endpoint.host) ? undefined : endpoint.host,
                });
                socket.once('secureConnect', onConnected);
            } else {
                socket = net.connect({ host: endpoint.host, port: endpoint.port });
                socket.once('connect', onConnected);
            }
        } catch (error) {
            settle(classifyProxySocketError(error, { scheme: endpoint.scheme, tlsEstablished }), error?.code || null);
            return;
        }

        socket.setTimeout(timeoutMs);
        socket.once('timeout', () => settle(PROXY_CONNECT_PREFLIGHT_TIMEOUT, null));
        socket.once('error', onSocketError);
        // A peer that accepts the connection and closes without completing a status
        // line is not an HTTP CONNECT proxy.  Classify it immediately rather than
        // waiting out the inactivity timeout.  For https:// the close is a handshake
        // failure instead, since the tunnel was never established.
        socket.once('close', () => settle(
            endpoint.scheme === 'https' && !tlsEstablished ? PROXY_TLS_HANDSHAKE_FAILED : PROXY_CONNECT_PROTOCOL_INVALID,
            'connection_closed_before_status_line',
        ));
        socket.on('data', onData);
    });
}

// The preflight is the last gate before one-shot authority is spent.  Configuration
// problems are thrown (so they carry their own precise code); probe outcomes are
// returned so the caller can record non-secret evidence either way.
function createStageDHttpConnectProxyPreflight({
    endpoint = null,
    timeoutMs = STAGE_D_PROXY_PREFLIGHT_TIMEOUT_MS,
    clock = () => new Date().toISOString(),
} = {}) {
    if (!Number.isInteger(timeoutMs) || timeoutMs <= 0) {
        failStageDProxy(STAGE_D_PROXY_PREFLIGHT_CONFIGURATION_INVALID, 'proxy preflight timeout must be a positive integer');
    }
    if (endpoint !== null) {
        const required = ['scheme', 'host', 'port', 'redacted'];
        if (typeof endpoint !== 'object' || required.some(key => endpoint[key] === undefined)) {
            failStageDProxy(STAGE_D_PROXY_PREFLIGHT_CONFIGURATION_INVALID, 'proxy preflight endpoint must be a resolved endpoint object');
        }
    }
    return Object.freeze({
        schema_version: 'footballprediction-stage-d-http-connect-proxy-preflight/v1',
        proxy_contract: STAGE_D_STABLE_PROXY_CONTRACT,
        timeout_ms: timeoutMs,
        async run() {
            const resolved = endpoint || resolveStageDStableProxyEndpoint();
            return probeStageDHttpConnectProxy({ endpoint: resolved, timeoutMs, clock });
        },
    });
}

module.exports = {
    STAGE_D_STABLE_PROXY_CONTRACT,
    STAGE_D_PROXY_ENDPOINT_ENV_VAR,
    STAGE_D_PROXY_SUPPORTED_PROTOCOLS,
    STAGE_D_PROXY_PREFLIGHT_TIMEOUT_MS,
    STAGE_D_PROXY_PROBE_DESTINATION,
    STAGE_D_PROXY_PREFLIGHT_CONFIGURATION_INVALID,
    PROXY_CONNECT_PROOF_STATUSES,
    PROXY_PREFLIGHT_CLASSIFICATIONS,
    PROXY_PREFLIGHT_PASS,
    PROXY_CONFIGURATION_MISSING,
    PROXY_URL_INVALID,
    PROXY_DNS_OR_ADDRESS_RESOLUTION_FAILURE,
    PROXY_TCP_CONNECT_FAILED,
    PROXY_TLS_HANDSHAKE_FAILED,
    PROXY_CONNECT_PROTOCOL_INVALID,
    PROXY_CONNECT_PREFLIGHT_TIMEOUT,
    PROXY_AUTHENTICATION_CONFIGURATION_FAILURE,
    resolveStageDStableProxyEndpoint,
    buildStageDProxyAgentUrl,
    classifyStageDProxySocketError: classifyProxySocketError,
    createStageDHttpConnectProxyPreflight,
};
