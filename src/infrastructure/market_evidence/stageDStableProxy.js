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
//   2. PROVEN TUNNEL, NOT A PROVEN STATUS LINE.  A proxy is not proven because it
//      returned something HTTP-shaped.  It is proven only when it accepts CONNECT
//      for a project-controlled target, answers with a strict 2xx, and then carries
//      a fresh random nonce through the tunnel that the target echoes back.  The
//      preflight never names the provider, so it cannot resolve provider DNS, cannot
//      send provider traffic, and cannot consume provider quota.
//
// Why the strict 2xx rule needs the probe target to be genuinely reachable: a proxy
// answers a CONNECT for a destination it cannot reach with a proxy-class refusal
// (502/504).  Those refusals are indistinguishable from what an ordinary origin
// server returns to a CONNECT it does not implement, so accepting any non-2xx would
// admit a non-proxy endpoint through the last gate before one-shot authority is
// spent.  Requiring 2xx therefore only works against a target the proxy can
// actually tunnel to -- which is why this module takes one as explicit
// configuration rather than probing a deliberately unusable address.

const crypto = require('node:crypto');
const net = require('node:net');
const tls = require('node:tls');

const STAGE_D_STABLE_PROXY_CONTRACT = 'stage-d-dedicated-single-stable-http-connect-proxy/v1';

// The canonical existing variable for the proxy endpoint.  It is reused rather than
// duplicated: a second name for the same endpoint would be a configuration
// ambiguity, which is the failure mode this contract exists to remove.
const STAGE_D_PROXY_ENDPOINT_ENV_VAR = 'THE_ODDS_API_PROXY_URL';

// A separate contract from the proxy endpoint: the proxy is the thing being proven,
// the target is the thing it must prove itself against.  Conflating them would let an
// endpoint prove itself by talking to itself.
const STAGE_D_PROXY_PREFLIGHT_TARGET_ENV_VAR = 'STAGE_D_PROXY_PREFLIGHT_TARGET_URL';
const STAGE_D_PROXY_PREFLIGHT_TARGET_PROTOCOL = 'tcp:';

const STAGE_D_PROXY_SUPPORTED_PROTOCOLS = Object.freeze(['http:', 'https:']);
const STAGE_D_PROXY_DEFAULT_PORTS = Object.freeze({ 'http:': 80, 'https:': 443 });

// A bounded probe.  The proxy and its target are expected to be project-controlled,
// so the ceiling is deliberately far below the provider request timeout rather than
// inherited from it.  It bounds each stage by inactivity; the probe additionally
// enforces a hard overall deadline so no stage can extend the total.
const STAGE_D_PROXY_PREFLIGHT_TIMEOUT_MS = 5000;

const STAGE_D_PROXY_PROBE_MAX_RESPONSE_BYTES = 8192;
const STAGE_D_PROXY_NONCE_BYTES = 16;

// The data-plane proof.  The binder writes one line through the established tunnel
// and the project-controlled target must echo the nonce back verbatim.  The nonce is
// random per run and is not a secret: its only job is to be unguessable by a stale,
// synthetic or third-party responder that never actually carried bytes for us.
const STAGE_D_PROXY_NONCE_PROTOCOL = 'stage-d-preflight-nonce-echo/v1';
const STAGE_D_PROXY_NONCE_REQUEST_PREFIX = 'STAGE-D-PREFLIGHT';

const PROXY_PREFLIGHT_PASS = 'PROXY_PREFLIGHT_PASS';
const PROXY_CONFIGURATION_MISSING = 'PROXY_CONFIGURATION_MISSING';
const PROXY_URL_INVALID = 'PROXY_URL_INVALID';
const PROXY_DNS_OR_ADDRESS_RESOLUTION_FAILURE = 'PROXY_DNS_OR_ADDRESS_RESOLUTION_FAILURE';
const PROXY_TCP_CONNECT_FAILED = 'PROXY_TCP_CONNECT_FAILED';
const PROXY_TLS_HANDSHAKE_FAILED = 'PROXY_TLS_HANDSHAKE_FAILED';
const PROXY_CONNECT_PROTOCOL_INVALID = 'PROXY_CONNECT_PROTOCOL_INVALID';
const PROXY_CONNECT_TUNNEL_REFUSED = 'PROXY_CONNECT_TUNNEL_REFUSED';
const PROXY_CONNECT_TUNNEL_PROOF_FAILED = 'PROXY_CONNECT_TUNNEL_PROOF_FAILED';
const PROXY_CONNECT_PREFLIGHT_TIMEOUT = 'PROXY_CONNECT_PREFLIGHT_TIMEOUT';
const PROXY_AUTHENTICATION_CONFIGURATION_FAILURE = 'PROXY_AUTHENTICATION_CONFIGURATION_FAILURE';
const STAGE_D_PROXY_PREFLIGHT_CONFIGURATION_INVALID = 'STAGE_D_PROXY_PREFLIGHT_CONFIGURATION_INVALID';
const PROXY_PREFLIGHT_TARGET_CONFIGURATION_MISSING = 'PROXY_PREFLIGHT_TARGET_CONFIGURATION_MISSING';
const PROXY_PREFLIGHT_TARGET_URL_INVALID = 'PROXY_PREFLIGHT_TARGET_URL_INVALID';
const PROXY_PREFLIGHT_TARGET_CONFLICTS_WITH_PROXY = 'PROXY_PREFLIGHT_TARGET_CONFLICTS_WITH_PROXY';

const PROXY_PREFLIGHT_CLASSIFICATIONS = Object.freeze([
    PROXY_PREFLIGHT_PASS,
    PROXY_CONFIGURATION_MISSING,
    PROXY_URL_INVALID,
    PROXY_DNS_OR_ADDRESS_RESOLUTION_FAILURE,
    PROXY_TCP_CONNECT_FAILED,
    PROXY_TLS_HANDSHAKE_FAILED,
    PROXY_CONNECT_PROTOCOL_INVALID,
    PROXY_CONNECT_TUNNEL_REFUSED,
    PROXY_CONNECT_TUNNEL_PROOF_FAILED,
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
// into evidence by accident.  Only buildStageDProxyAuthorizationHeader reads them.
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

// Resolves the single configured preflight target, or fails closed.
//
// The target is a project-controlled TCP listener that the proxy must be able to
// reach THROUGH ITS FORWARDING PATH -- not the proxy listener itself, not a public
// website, not a provider host.  Its address is expressed in the proxy's coordinate
// system, so it is explicit configuration in every environment; nothing here infers
// it from socket.localAddress, host routes, a Docker gateway or anything else about
// the current workstation.
function parseStageDPreflightTargetUrl(candidate) {
    let parsed;
    try {
        parsed = new URL(candidate);
    } catch {
        failStageDProxy(PROXY_PREFLIGHT_TARGET_URL_INVALID, `${STAGE_D_PROXY_PREFLIGHT_TARGET_ENV_VAR} must be an absolute URL of the form tcp://host:port`);
    }
    if (parsed.protocol !== STAGE_D_PROXY_PREFLIGHT_TARGET_PROTOCOL) {
        failStageDProxy(
            PROXY_PREFLIGHT_TARGET_URL_INVALID,
            `${STAGE_D_PROXY_PREFLIGHT_TARGET_ENV_VAR} must use the tcp: scheme; `
            + `scheme "${parsed.protocol.replace(':', '')}" is not permitted for the preflight probe target`,
        );
    }
    if (parsed.username !== '' || parsed.password !== '') {
        failStageDProxy(PROXY_PREFLIGHT_TARGET_URL_INVALID, `${STAGE_D_PROXY_PREFLIGHT_TARGET_ENV_VAR} must not carry userinfo; the probe target carries no credentials`);
    }
    if (parsed.pathname !== '' || parsed.search !== '' || parsed.hash !== '') {
        failStageDProxy(PROXY_PREFLIGHT_TARGET_URL_INVALID, `${STAGE_D_PROXY_PREFLIGHT_TARGET_ENV_VAR} must be exactly tcp://host:port with no path, query or fragment`);
    }
    if (typeof parsed.hostname !== 'string' || parsed.hostname === '') {
        failStageDProxy(PROXY_PREFLIGHT_TARGET_URL_INVALID, `${STAGE_D_PROXY_PREFLIGHT_TARGET_ENV_VAR} must name a host`);
    }
    if (parsed.port === '') {
        failStageDProxy(PROXY_PREFLIGHT_TARGET_URL_INVALID, `${STAGE_D_PROXY_PREFLIGHT_TARGET_ENV_VAR} must name an explicit port; the tcp: scheme has no default port`);
    }
    return parsed;
}

function resolveStageDPreflightTarget(env = process.env, { proxyEndpoint = null } = {}) {
    const raw = env?.[STAGE_D_PROXY_PREFLIGHT_TARGET_ENV_VAR];
    if (typeof raw !== 'string' || raw.trim() === '') {
        failStageDProxy(
            PROXY_PREFLIGHT_TARGET_CONFIGURATION_MISSING,
            `Stage D requires an explicit ${STAGE_D_PROXY_PREFLIGHT_TARGET_ENV_VAR} naming one project-controlled TCP target `
            + 'reachable through the proxy forwarding path; there is no default target and no public-Internet fallback',
        );
    }
    const parsed = parseStageDPreflightTargetUrl(raw.trim());
    const port = Number(parsed.port);
    if (!Number.isInteger(port) || port < 1 || port > 65535) {
        failStageDProxy(PROXY_PREFLIGHT_TARGET_URL_INVALID, `${STAGE_D_PROXY_PREFLIGHT_TARGET_ENV_VAR} must name a port between 1 and 65535`);
    }
    const target = Object.freeze({
        host: parsed.hostname,
        port,
        redacted: `tcp://${parsed.hostname}:${port}`,
    });
    // An endpoint cannot prove itself by talking to itself: if the target is the proxy
    // listener, a CONNECT would be answered by the very thing under test.  This is a
    // literal host:port comparison, not a DNS equivalence check, so it only rejects
    // the case that is decidable without resolution.
    if (proxyEndpoint && proxyEndpoint.host === target.host && proxyEndpoint.port === target.port) {
        failStageDProxy(
            PROXY_PREFLIGHT_TARGET_CONFLICTS_WITH_PROXY,
            `${STAGE_D_PROXY_PREFLIGHT_TARGET_ENV_VAR} must not name the proxy listener itself (${target.redacted} is the configured ${STAGE_D_PROXY_ENDPOINT_ENV_VAR})`,
        );
    }
    return target;
}

// Canonical HTTP CONNECT credential attachment, shared by the preflight and the
// governed transport.
//
// `https-proxy-agent` builds the header as
//   Basic base64(decodeURIComponent(user) + ':' + decodeURIComponent(pass))
// -- it percent-DECODES the URL userinfo before encoding the Basic payload.  The
// preflight must produce byte-identical material, or it would authenticate with
// different credentials than the transport it exists to gate: a secret containing
// "@" or ":" would reach the proxy as "%40"/"%3A" and be rejected with a 407 that
// says nothing about the transport's real chances.
function buildStageDProxyAuthorizationHeader(endpoint) {
    const credentials = endpoint[PROXY_CREDENTIALS];
    if (!credentials) return null;
    let username;
    let password;
    try {
        username = decodeURIComponent(credentials.username);
        password = decodeURIComponent(credentials.password);
    } catch {
        failStageDProxy(
            PROXY_AUTHENTICATION_CONFIGURATION_FAILURE,
            `${STAGE_D_PROXY_ENDPOINT_ENV_VAR} carries userinfo that is not valid percent-encoding`,
        );
    }
    return `Basic ${Buffer.from(`${username}:${password}`, 'utf8').toString('base64')}`;
}

// Re-attaches credentials only at the point the agent is constructed.  Callers must
// never log, persist or include the returned URL in an error message.
//
// `URL` hands back userinfo already percent-encoded, so re-encoding here would
// double-encode it and the agent's own decodeURIComponent would then yield the wrong
// secret.  The values are spliced in verbatim so the agent decodes exactly what the
// operator configured.
function buildStageDProxyAgentUrl(endpoint) {
    const credentials = endpoint[PROXY_CREDENTIALS];
    const auth = credentials
        ? `${credentials.username}:${credentials.password}@`
        : '';
    return `${endpoint.scheme}://${auth}${endpoint.authority}`;
}

function buildStageDConnectProbe(endpoint, target) {
    const destination = `${target.host}:${target.port}`;
    const authorization = buildStageDProxyAuthorizationHeader(endpoint);
    return `CONNECT ${destination} HTTP/1.1\r\n`
        + `Host: ${destination}\r\n`
        + (authorization ? `Proxy-Authorization: ${authorization}\r\n` : '')
        + '\r\n';
}

function buildStageDNonceProbe(challenge) {
    return `${STAGE_D_PROXY_NONCE_REQUEST_PREFIX} ${challenge.probe_id} ${challenge.nonce}\n`;
}

function createStageDPreflightChallenge() {
    return Object.freeze({
        probe_id: crypto.randomBytes(8).toString('hex'),
        nonce: crypto.randomBytes(STAGE_D_PROXY_NONCE_BYTES).toString('hex'),
    });
}

// Locates the end of the CONNECT response head.  The tunnel's data plane begins
// immediately after it, so anything already buffered past this point belongs to the
// nonce exchange rather than to the HTTP response.
function findConnectResponseHeadEnd(buffer) {
    const crlf = buffer.indexOf('\r\n\r\n');
    if (crlf !== -1) return crlf + 4;
    const lf = buffer.indexOf('\n\n');
    if (lf !== -1) return lf + 2;
    return -1;
}

function probeStageDHttpConnectProxy({ endpoint, target, timeoutMs, clock, challenge }) {
    return new Promise(resolve => {
        const startedAt = clock();
        let settled = false;
        let socket = null;
        let overallTimer = null;
        let tlsEstablished = false;
        let buffer = '';
        let phase = 'connect_response';

        const settle = (classification, detail) => {
            if (settled) return;
            settled = true;
            if (overallTimer) clearTimeout(overallTimer);
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
                nonce_protocol: STAGE_D_PROXY_NONCE_PROTOCOL,
                proof_level: 'L3',
                classification,
                passed: classification === PROXY_PREFLIGHT_PASS,
                endpoint: endpoint.redacted,
                scheme: endpoint.scheme,
                host: endpoint.host,
                port: endpoint.port,
                has_credentials: endpoint.has_credentials,
                target: target.redacted,
                nonce_verified: classification === PROXY_PREFLIGHT_PASS,
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
                socket.write(buildStageDConnectProbe(endpoint, target));
            } catch (error) {
                settle(classifyProxySocketError(error, { scheme: endpoint.scheme, tlsEstablished }), error?.code || null);
            }
        };

        // The tunnel proof.  A 2xx alone can be synthesised without any tunnel existing,
        // so the pass condition is that a fresh random nonce written through the tunnel
        // comes back verbatim.  Anything else fails closed.
        const readNonceEcho = () => {
            const lineEnd = buffer.indexOf('\n');
            if (lineEnd === -1) {
                if (buffer.length > STAGE_D_PROXY_PROBE_MAX_RESPONSE_BYTES) {
                    settle(PROXY_CONNECT_TUNNEL_PROOF_FAILED, 'nonce_response_too_large');
                }
                return; // bounded by the socket inactivity timeout and the overall deadline
            }
            const line = buffer.slice(0, lineEnd).replace(/\r$/, '');
            if (line === challenge.nonce) {
                settle(PROXY_PREFLIGHT_PASS, 'connect_2xx_nonce_round_trip');
                return;
            }
            settle(PROXY_CONNECT_TUNNEL_PROOF_FAILED, line === '' ? 'empty_nonce_response' : 'nonce_mismatch');
        };

        const readConnectResponse = () => {
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
                // The endpoint is a proxy that understands CONNECT but will not
                // authenticate this request.  Whether the configured secret is wrong or
                // none was configured, the governed request could not be authenticated
                // either, so the endpoint is not usable.  A 407 is never itself proof of
                // anything -- a successful preflight must still end in 2xx plus a nonce.
                settle(
                    PROXY_AUTHENTICATION_CONFIGURATION_FAILURE,
                    endpoint.has_credentials
                        ? 'proxy_rejected_configured_credentials'
                        : 'proxy_authentication_required_but_no_credentials_configured',
                );
                return;
            }
            if (status < 200 || status > 299) {
                // A syntactically valid refusal.  It proves the tunnel was NOT
                // established, and it is exactly what an ordinary origin server or a
                // fronting gateway returns to a CONNECT it does not implement, so no
                // such status is ever accepted as capability proof.
                settle(PROXY_CONNECT_TUNNEL_REFUSED, `non_2xx_status_${status}`);
                return;
            }
            const headEnd = findConnectResponseHeadEnd(buffer);
            if (headEnd === -1) {
                if (buffer.length > STAGE_D_PROXY_PROBE_MAX_RESPONSE_BYTES) settle(PROXY_CONNECT_PROTOCOL_INVALID, 'connect_response_head_too_large');
                return; // wait for the rest of the response head before trusting the tunnel
            }
            // Everything past the response head is data-plane bytes from the target.
            buffer = buffer.slice(headEnd);
            phase = 'tunnel_proof';
            try {
                socket.write(buildStageDNonceProbe(challenge));
            } catch (error) {
                settle(classifyProxySocketError(error, { scheme: endpoint.scheme, tlsEstablished }), error?.code || null);
                return;
            }
            readNonceEcho();
        };

        const onData = chunk => {
            buffer += chunk.toString('latin1');
            if (buffer.length > STAGE_D_PROXY_PROBE_MAX_RESPONSE_BYTES && phase === 'connect_response') {
                settle(PROXY_CONNECT_PROTOCOL_INVALID, 'response_too_large');
                return;
            }
            if (phase === 'connect_response') readConnectResponse();
            if (!settled && phase === 'tunnel_proof') readNonceEcho();
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

        // A hard ceiling over the whole probe, so a peer that trickles bytes cannot keep
        // any single stage alive indefinitely on top of the inactivity timeout.
        //
        // Both timers are phase-aware, which keeps one invariant exact: once a 2xx has been
        // received, failing to complete the nonce round trip is ALWAYS a tunnel proof
        // failure, never a bare timeout.  That is what makes the "synthetic 200 that opens
        // no tunnel" case a single unambiguous classification instead of a race between the
        // two timers.  Before the 2xx, a stall is still an ordinary protocol timeout.
        overallTimer = setTimeout(() => settle(
            phase === 'tunnel_proof' ? PROXY_CONNECT_TUNNEL_PROOF_FAILED : PROXY_CONNECT_PREFLIGHT_TIMEOUT,
            phase === 'tunnel_proof' ? 'nonce_round_trip_inactivity' : 'overall_deadline_exceeded',
        ), timeoutMs * 3);
        socket.setTimeout(timeoutMs);
        socket.once('timeout', () => settle(
            phase === 'tunnel_proof' ? PROXY_CONNECT_TUNNEL_PROOF_FAILED : PROXY_CONNECT_PREFLIGHT_TIMEOUT,
            phase === 'tunnel_proof' ? 'nonce_round_trip_inactivity' : null,
        ));
        socket.once('error', onSocketError);
        // A peer that accepts the connection and closes before the proof completes is
        // never a pass.  For https:// the close before the handshake is a TLS failure
        // instead, since the tunnel was never established.
        socket.once('close', () => {
            if (phase === 'tunnel_proof') {
                settle(PROXY_CONNECT_TUNNEL_PROOF_FAILED, 'tunnel_closed_before_nonce_proof');
                return;
            }
            settle(
                endpoint.scheme === 'https' && !tlsEstablished ? PROXY_TLS_HANDSHAKE_FAILED : PROXY_CONNECT_PROTOCOL_INVALID,
                'connection_closed_before_status_line',
            );
        });
        socket.on('data', onData);
    });
}

// The preflight is the last gate before one-shot authority is spent.  Configuration
// problems are thrown (so they carry their own precise code); probe outcomes are
// returned so the caller can record non-secret evidence either way.
function createStageDHttpConnectProxyPreflight({
    endpoint = null,
    target = null,
    timeoutMs = STAGE_D_PROXY_PREFLIGHT_TIMEOUT_MS,
    clock = () => new Date().toISOString(),
    challengeFactory = createStageDPreflightChallenge,
    env = process.env,
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
    if (target !== null) {
        const required = ['host', 'port', 'redacted'];
        if (typeof target !== 'object' || required.some(key => target[key] === undefined)) {
            failStageDProxy(STAGE_D_PROXY_PREFLIGHT_CONFIGURATION_INVALID, 'proxy preflight target must be a resolved target object');
        }
    }
    if (typeof challengeFactory !== 'function') {
        failStageDProxy(STAGE_D_PROXY_PREFLIGHT_CONFIGURATION_INVALID, 'proxy preflight challenge factory must be callable');
    }
    return Object.freeze({
        schema_version: 'footballprediction-stage-d-http-connect-proxy-preflight/v1',
        proxy_contract: STAGE_D_STABLE_PROXY_CONTRACT,
        nonce_protocol: STAGE_D_PROXY_NONCE_PROTOCOL,
        timeout_ms: timeoutMs,
        async run() {
            // Both contracts are resolved before any socket is opened, so a missing proxy
            // endpoint or a missing probe target fails closed without touching the network.
            const resolved = endpoint || resolveStageDStableProxyEndpoint(env);
            const probeTarget = target || resolveStageDPreflightTarget(env, { proxyEndpoint: resolved });
            return probeStageDHttpConnectProxy({
                endpoint: resolved,
                target: probeTarget,
                timeoutMs,
                clock,
                challenge: challengeFactory(),
            });
        },
    });
}

module.exports = {
    STAGE_D_STABLE_PROXY_CONTRACT,
    STAGE_D_PROXY_ENDPOINT_ENV_VAR,
    STAGE_D_PROXY_PREFLIGHT_TARGET_ENV_VAR,
    STAGE_D_PROXY_PREFLIGHT_TARGET_PROTOCOL,
    STAGE_D_PROXY_SUPPORTED_PROTOCOLS,
    STAGE_D_PROXY_PREFLIGHT_TIMEOUT_MS,
    STAGE_D_PROXY_NONCE_PROTOCOL,
    STAGE_D_PROXY_NONCE_REQUEST_PREFIX,
    STAGE_D_PROXY_PREFLIGHT_CONFIGURATION_INVALID,
    PROXY_PREFLIGHT_CLASSIFICATIONS,
    PROXY_PREFLIGHT_PASS,
    PROXY_CONFIGURATION_MISSING,
    PROXY_URL_INVALID,
    PROXY_DNS_OR_ADDRESS_RESOLUTION_FAILURE,
    PROXY_TCP_CONNECT_FAILED,
    PROXY_TLS_HANDSHAKE_FAILED,
    PROXY_CONNECT_PROTOCOL_INVALID,
    PROXY_CONNECT_TUNNEL_REFUSED,
    PROXY_CONNECT_TUNNEL_PROOF_FAILED,
    PROXY_CONNECT_PREFLIGHT_TIMEOUT,
    PROXY_AUTHENTICATION_CONFIGURATION_FAILURE,
    PROXY_PREFLIGHT_TARGET_CONFIGURATION_MISSING,
    PROXY_PREFLIGHT_TARGET_URL_INVALID,
    PROXY_PREFLIGHT_TARGET_CONFLICTS_WITH_PROXY,
    resolveStageDStableProxyEndpoint,
    resolveStageDPreflightTarget,
    buildStageDProxyAgentUrl,
    buildStageDProxyAuthorizationHeader,
    classifyStageDProxySocketError: classifyProxySocketError,
    createStageDHttpConnectProxyPreflight,
};
