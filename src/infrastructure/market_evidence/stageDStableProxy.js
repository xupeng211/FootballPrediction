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
//      returned something HTTP-shaped, and it is not proven by anything the client
//      can manufacture on its own.  It is proven only when it accepts CONNECT for a
//      project-controlled target, answers with a strict 2xx, and then carries a fresh
//      random challenge through the tunnel that the target answers with an HMAC-SHA-256
//      over that challenge under a secret held by the target and this verifier alone.
//      The preflight never names the provider, so it cannot resolve provider DNS,
//      cannot send provider traffic, and cannot consume provider quota.
//
// Why a client-authored challenge is not enough on its own.  An earlier revision of
// this module proved the data plane by writing a random nonce through the tunnel and
// requiring the target to echo it verbatim.  Independent review rejected that, and
// the objection is exact: a nonce the client invents is a value the client already
// knows, so any responder that reads it -- and never dials the configured target --
// can produce the expected reply.  Reflection is indistinguishable from forwarding
// when the challenge carries no secret.  The proof therefore has to rest on material
// the responder cannot compute: the target contributes a keyed MAC, and only an
// entity holding the shared secret can answer a fresh challenge.  Nothing the client
// sends is ever, by itself, sufficient to pass.
//
// What this does and does not prove.  A passing preflight proves the CONNECT tunnel
// reached an entity that holds the configured preflight shared secret -- target
// identity and control, to the strength of that secret.  It does NOT prove The Odds
// API is reachable, that the provider would accept a request, that quota exists, that
// general external egress works, or that the network will hold.  A compromised shared
// secret would let a hostile responder forge attestation; that is the accepted
// failure domain of a symmetric design, which is why the secret is dedicated,
// high-entropy, never logged, and rotatable.
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

// A third contract, separate from both the proxy endpoint and the target address:
// the key material the target must possess to answer a challenge.  It is deliberately
// not derived from, and shares no bytes with, the provider key, the proxy credentials,
// any authorization or ledger hash, or any machine identity -- a secret reused across
// purposes is a secret whose blast radius is the union of those purposes.
const STAGE_D_PROXY_PREFLIGHT_SECRET_ENV_VAR = 'STAGE_D_PROXY_PREFLIGHT_SHARED_SECRET';

const STAGE_D_PROXY_PROBE_MAX_RESPONSE_BYTES = 8192;

// The data-plane proof.  The verifier writes one challenge line through the
// established tunnel; the project-controlled target answers with an HMAC-SHA-256 over
// a canonical, length-prefixed message under the shared secret.  The challenge is
// fresh per execution and is not itself a secret: its job is to be unguessable and
// never reused, so that no earlier response can be replayed against it.
const STAGE_D_PROXY_ATTESTATION_PROTOCOL = 'stage-d-proxy-preflight/v1';
const STAGE_D_PROXY_CHALLENGE_BYTES = 32;
const STAGE_D_PROXY_RUN_ID_BYTES = 16;
const STAGE_D_PROXY_ATTESTATION_MAC_BYTES = 32;

// A shared secret shorter than this is not a meaningful attestation key.  Enforcing a
// floor here means a mis-provisioned secret fails closed at configuration time rather
// than silently degrading the proof to something a guesser could satisfy.
const STAGE_D_PROXY_ATTESTATION_MIN_SECRET_BYTES = 32;

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
const PROXY_PREFLIGHT_TARGET_EXTERNAL_HOST = 'PROXY_PREFLIGHT_TARGET_EXTERNAL_HOST';

// Attestation configuration failures are thrown rather than returned, because they are
// decided before a socket exists and must leave no room for a caller to treat them as a
// probe outcome.  Attestation *outcomes* are returned like every other probe result.
const PREFLIGHT_ATTESTATION_SECRET_MISSING = 'PREFLIGHT_ATTESTATION_SECRET_MISSING';
const PREFLIGHT_ATTESTATION_SECRET_INVALID = 'PREFLIGHT_ATTESTATION_SECRET_INVALID';

const PROXY_CONNECT_ATTESTATION_MALFORMED = 'PROXY_CONNECT_ATTESTATION_MALFORMED';
const PROXY_CONNECT_ATTESTATION_RUN_ID_MISMATCH = 'PROXY_CONNECT_ATTESTATION_RUN_ID_MISMATCH';
const PROXY_CONNECT_ATTESTATION_MAC_INVALID = 'PROXY_CONNECT_ATTESTATION_MAC_INVALID';
const PROXY_CONNECT_ATTESTATION_TIMEOUT = 'PROXY_CONNECT_ATTESTATION_TIMEOUT';

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
    PROXY_CONNECT_ATTESTATION_MALFORMED,
    PROXY_CONNECT_ATTESTATION_RUN_ID_MISMATCH,
    PROXY_CONNECT_ATTESTATION_MAC_INVALID,
    PROXY_CONNECT_ATTESTATION_TIMEOUT,
    PROXY_CONNECT_PREFLIGHT_TIMEOUT,
    PROXY_AUTHENTICATION_CONFIGURATION_FAILURE,
]);

const PREFLIGHT_ATTESTATION_CONFIGURATION_CLASSIFICATIONS = Object.freeze([
    PREFLIGHT_ATTESTATION_SECRET_MISSING,
    PREFLIGHT_ATTESTATION_SECRET_INVALID,
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

// The attestation secret is held the same way, and for a stronger reason: it must not
// reach an evidence record, an error message, a JSON report or a log line.  Nothing
// reads it except the MAC computation, and no representation of it -- not the bytes,
// not a hash, not a length, not a prefix -- is ever placed on the enumerable surface.
const PREFLIGHT_SECRET_BYTES = Symbol('stageDPreflightSecretBytes');

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

// Hosts the preflight target must never be.
//
// A preflight target is only meaningful if the project controls it: the pass condition is
// that the tunnel reached an entity holding the configured shared secret.  A target that
// is actually one of the project's upstream providers proves nothing about a
// project-controlled listener, and reaching it would additionally make the preflight an
// outbound contact with a third party -- which is exactly what the Stage D provider
// zero-contact invariant forbids.  An operator who points the target at The Odds API
// would therefore both void the proof and generate provider DNS and TCP traffic before
// the one-shot authorization is consumed.
//
// These are the external hosts this repository actually talks to, so the list is
// traceable rather than invented: The Odds API is the Stage D provider named by
// theOddsApiClient.js; the harvesting and historical sources appear in the acquisition
// configuration; the remainder are third-party utilities referenced from src.
//
// This is a denylist, and a denylist is not a completeness proof: it cannot enumerate
// every public host.  The primary control remains that the target is explicit operator
// configuration with no default.  What this closes is the concrete, plausible
// misconfiguration of naming a known provider.
const STAGE_D_PREFLIGHT_DENIED_TARGET_APEXES = Object.freeze([
    'the-odds-api.com', // the Stage D provider itself (theOddsApiClient.js API_HOST)
    'oddsportal.com', // harvesting source
    'fotmob.com', // harvesting source
    'football-data.co.uk', // historical results source
    'premierleague.com', // fixtures and resources source
    'telegram.org', // alert transport
    'ipify.org', // public egress-address probe
    'browserleaks.com', // TLS fingerprint probe
    'httpbin.org', // public echo service
]);

// Matches the apex itself and anything beneath it, so a provider subdomain is denied
// even though only the apex is listed.  Comparison is case-insensitive and tolerates a
// single trailing dot, because "api.the-odds-api.com." is the same host as the listed
// name while being a different string.
function stageDPreflightTargetHostIsExternal(hostname) {
    const normalized = String(hostname).toLowerCase().replace(/\.$/, '');
    return STAGE_D_PREFLIGHT_DENIED_TARGET_APEXES.some(
        apex => normalized === apex || normalized.endsWith(`.${apex}`),
    );
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
    // Rejected before the port check and before any socket exists, so a provider target
    // cannot be resolved, dialed or even reported as a probe outcome.
    if (stageDPreflightTargetHostIsExternal(parsed.hostname)) {
        failStageDProxy(
            PROXY_PREFLIGHT_TARGET_EXTERNAL_HOST,
            `${STAGE_D_PROXY_PREFLIGHT_TARGET_ENV_VAR} must name a project-controlled target; `
            + 'it must not name an external provider host, whose contact this preflight is required to avoid',
        );
    }
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

// Resolves the attestation secret, or fails closed.
//
// The representation is canonical base64 of opaque bytes: base64 is the one encoding
// that survives an environment variable, a secret store and a deploy manifest without
// re-interpretation, and it lets this contract state an entropy floor in bytes rather
// than in characters.  The value is validated strictly -- a lenient decode would
// accept a corrupted or truncated secret and turn a provisioning mistake into an
// intermittent attestation failure against a live target instead of a startup refusal.
function isCanonicalBase64(value) {
    if (value.length === 0 || value.length % 4 !== 0) return false;
    if (!/^[A-Za-z0-9+/]+={0,2}$/.test(value)) return false;
    // Round-tripping rejects non-canonical trailing bits, which Buffer.from would
    // otherwise accept and silently decode to different bytes than the operator encoded.
    return Buffer.from(value, 'base64').toString('base64') === value;
}

function resolveStageDPreflightSecret(env = process.env) {
    const raw = env?.[STAGE_D_PROXY_PREFLIGHT_SECRET_ENV_VAR];
    if (typeof raw !== 'string' || raw.trim() === '') {
        // Fails closed before any socket is opened, and is never generated on the fly:
        // a secret this process invents cannot be known by the target, so a silently
        // generated value would turn a missing deployment input into a confusing
        // attestation failure rather than a configuration error.
        failStageDProxy(
            PREFLIGHT_ATTESTATION_SECRET_MISSING,
            `Stage D requires ${STAGE_D_PROXY_PREFLIGHT_SECRET_ENV_VAR}, the shared secret the project-controlled preflight target `
            + 'attests with; there is no default, no generated fallback and no reuse of any other credential',
        );
    }
    const value = raw.trim();
    if (!isCanonicalBase64(value)) {
        failStageDProxy(
            PREFLIGHT_ATTESTATION_SECRET_INVALID,
            `${STAGE_D_PROXY_PREFLIGHT_SECRET_ENV_VAR} must be canonical base64 of the raw secret bytes`,
        );
    }
    const bytes = Buffer.from(value, 'base64');
    if (bytes.length < STAGE_D_PROXY_ATTESTATION_MIN_SECRET_BYTES) {
        // The message states the requirement, never the observed length: a secret's
        // size is not something an operator needs echoed back at them, and error text
        // travels further than the configuration it describes.
        failStageDProxy(
            PREFLIGHT_ATTESTATION_SECRET_INVALID,
            `${STAGE_D_PROXY_PREFLIGHT_SECRET_ENV_VAR} must decode to at least ${STAGE_D_PROXY_ATTESTATION_MIN_SECRET_BYTES} bytes of key material`,
        );
    }
    return freezeStageDPreflightSecret(bytes);
}

function freezeStageDPreflightSecret(bytes) {
    // The non-enumerable slot is installed before the freeze: freezing first would make
    // the object non-extensible and the key material could not be attached at all.
    const secret = { configured: true, encoding: 'base64', algorithm: 'HMAC-SHA-256' };
    Object.defineProperty(secret, PREFLIGHT_SECRET_BYTES, { value: bytes, enumerable: false });
    return Object.freeze(secret);
}

// The canonical MAC input, and the reason it is built this way rather than assembled
// from a template string: an HMAC is only as unambiguous as its message encoding.  A
// delimiter-joined string lets distinct field pairs collide when a field can contain
// the delimiter; length prefixes make every encoding injective, so the bytes signed
// are exactly the fields intended and nothing else.
//
//   message = "stage-d-proxy-preflight/v1" 0x00
//             uint32be(byteLength(run_id))   run_id      (ASCII hex)
//             uint32be(byteLength(challenge)) challenge  (ASCII hex)
function buildStageDAttestationMessage({ runId, challenge }) {
    const magic = Buffer.from(STAGE_D_PROXY_ATTESTATION_PROTOCOL, 'ascii');
    const runIdBytes = Buffer.from(runId, 'ascii');
    const challengeBytes = Buffer.from(challenge, 'ascii');
    const runIdLength = Buffer.alloc(4);
    const challengeLength = Buffer.alloc(4);
    runIdLength.writeUInt32BE(runIdBytes.length, 0);
    challengeLength.writeUInt32BE(challengeBytes.length, 0);
    return Buffer.concat([
        magic, Buffer.from([0]),
        runIdLength, runIdBytes,
        challengeLength, challengeBytes,
    ]);
}

// The target's half of the protocol, exported so a dev/CI attestation target can be
// built from the same definition the verifier checks against rather than from a
// hand-copied restatement of it.  Importing this module starts no listener and opens
// no socket: no reference target is provisioned by the existence of this function.
function buildStageDAttestationResponse({ secret, runId, challenge }) {
    const bytes = secret?.[PREFLIGHT_SECRET_BYTES];
    if (!bytes) {
        failStageDProxy(PREFLIGHT_ATTESTATION_SECRET_MISSING, 'a resolved preflight secret is required to compute an attestation response');
    }
    const mac = crypto
        .createHmac('sha256', bytes)
        .update(buildStageDAttestationMessage({ runId, challenge }))
        .digest('hex');
    return `${STAGE_D_PROXY_ATTESTATION_PROTOCOL} ${runId} ${mac}\n`;
}

function buildStageDAttestationChallengeRequest({ runId, challenge }) {
    return `${STAGE_D_PROXY_ATTESTATION_PROTOCOL} ${runId} ${challenge}\n`;
}

function createStageDPreflightChallenge() {
    return Object.freeze({
        runId: crypto.randomBytes(STAGE_D_PROXY_RUN_ID_BYTES).toString('hex'),
        challenge: crypto.randomBytes(STAGE_D_PROXY_CHALLENGE_BYTES).toString('hex'),
    });
}

// Constant-time comparison of a received MAC against the expected one.  Length is
// checked first because timingSafeEqual throws on a length mismatch, and a length
// difference is a framing defect rather than a wrong-key result, so it is classified
// separately by the caller.
function stageDAttestationMacMatches(expected, receivedHex) {
    const received = Buffer.from(receivedHex, 'hex');
    if (received.length !== expected.length) return false;
    return crypto.timingSafeEqual(expected, received);
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

// Locates the end of the CONNECT response head.  The tunnel's data plane begins
// immediately after it, so anything already buffered past this point belongs to the
// challenge exchange rather than to the HTTP response.
function findConnectResponseHeadEnd(buffer) {
    const crlf = buffer.indexOf('\r\n\r\n');
    if (crlf !== -1) return crlf + 4;
    const lf = buffer.indexOf('\n\n');
    if (lf !== -1) return lf + 2;
    return -1;
}

function probeStageDHttpConnectProxy({ endpoint, target, secret, timeoutMs, clock, challenge }) {
    return new Promise(resolve => {
        const startedAt = clock();
        let settled = false;
        let socket = null;
        let overallTimer = null;
        let tlsEstablished = false;
        let buffer = '';
        let phase = 'connect_response';

        // Computed once, before the socket exists.  The expected MAC is a function of
        // the challenge and the secret alone, so there is nothing the peer can send
        // that changes what we are comparing against.
        const expectedMac = crypto
            .createHmac('sha256', secret[PREFLIGHT_SECRET_BYTES])
            .update(buildStageDAttestationMessage(challenge))
            .digest();

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
                schema_version: 'footballprediction-stage-d-http-connect-proxy-preflight/v2',
                proxy_contract: STAGE_D_STABLE_PROXY_CONTRACT,
                attestation_protocol: STAGE_D_PROXY_ATTESTATION_PROTOCOL,
                attestation_algorithm: 'HMAC-SHA-256',
                proof_level: 'AUTHENTICATED_PROJECT_CONTROLLED_TARGET_REACHABILITY',
                classification,
                passed: classification === PROXY_PREFLIGHT_PASS,
                endpoint: endpoint.redacted,
                scheme: endpoint.scheme,
                host: endpoint.host,
                port: endpoint.port,
                has_credentials: endpoint.has_credentials,
                target: target.redacted,
                target_attested: classification === PROXY_PREFLIGHT_PASS,
                provider_contacted: false,
                provider_dns_resolved: false,
                provider_reachability_proven: false,
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

        // The target attestation.  A 2xx can be synthesised without any tunnel existing,
        // and so can any reply the client could have predicted; the pass condition is
        // therefore a valid HMAC over this execution's fresh challenge, which only a
        // responder that actually reached the secret-holding target can produce.
        // Every rejection below is a distinct, deterministic failure -- none of them
        // waits, and none of them degrades into a generic timeout.
        const readAttestationResponse = () => {
            const lineEnd = buffer.indexOf('\n');
            if (lineEnd === -1) {
                if (buffer.length > STAGE_D_PROXY_PROBE_MAX_RESPONSE_BYTES) {
                    settle(PROXY_CONNECT_ATTESTATION_MALFORMED, 'attestation_response_too_large');
                }
                return; // bounded by the socket inactivity timeout and the overall deadline
            }
            const line = buffer.slice(0, lineEnd).replace(/\r$/, '');
            const parts = line.split(' ');
            if (parts.length !== 3 || parts[0] !== STAGE_D_PROXY_ATTESTATION_PROTOCOL) {
                settle(
                    PROXY_CONNECT_ATTESTATION_MALFORMED,
                    line === '' ? 'empty_attestation_response' : 'attestation_response_malformed',
                );
                return;
            }
            const [, responseRunId, macHex] = parts;
            // A response bound to another execution is refused before the MAC is even
            // examined: it cannot be a legitimate answer to this challenge, and
            // treating it as a mere MAC failure would blur replay into a key mismatch.
            if (responseRunId !== challenge.runId) {
                settle(PROXY_CONNECT_ATTESTATION_RUN_ID_MISMATCH, 'attestation_run_id_mismatch');
                return;
            }
            if (!/^[0-9a-f]{64}$/.test(macHex)) {
                settle(PROXY_CONNECT_ATTESTATION_MALFORMED, 'attestation_mac_malformed');
                return;
            }
            if (!stageDAttestationMacMatches(expectedMac, macHex)) {
                settle(PROXY_CONNECT_ATTESTATION_MAC_INVALID, 'attestation_mac_invalid');
                return;
            }
            settle(PROXY_PREFLIGHT_PASS, 'connect_2xx_target_hmac_attested');
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
                // anything -- a successful preflight must still end in 2xx plus a valid
                // target attestation.
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
            phase = 'attestation';
            try {
                socket.write(buildStageDAttestationChallengeRequest(challenge));
            } catch (error) {
                settle(classifyProxySocketError(error, { scheme: endpoint.scheme, tlsEstablished }), error?.code || null);
                return;
            }
            readAttestationResponse();
        };

        const onData = chunk => {
            buffer += chunk.toString('latin1');
            // Each reader bounds its own buffer, so there is no cap here: a proxy that
            // pipelines data behind its response head must not be failed for the head.
            if (phase === 'connect_response') readConnectResponse();
            if (!settled && phase === 'attestation') readAttestationResponse();
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
        // received, failing to complete the target attestation is ALWAYS an attestation
        // classification, never the bare protocol timeout that precedes it.  That is what
        // makes the "synthetic 200 that opens no tunnel" case a single unambiguous
        // classification instead of a race between the two timers.  Before the 2xx, a
        // stall is still an ordinary protocol timeout.
        overallTimer = setTimeout(() => settle(
            phase === 'attestation' ? PROXY_CONNECT_ATTESTATION_TIMEOUT : PROXY_CONNECT_PREFLIGHT_TIMEOUT,
            phase === 'attestation' ? 'attestation_inactivity' : 'overall_deadline_exceeded',
        ), timeoutMs * 3);
        socket.setTimeout(timeoutMs);
        socket.once('timeout', () => settle(
            phase === 'attestation' ? PROXY_CONNECT_ATTESTATION_TIMEOUT : PROXY_CONNECT_PREFLIGHT_TIMEOUT,
            phase === 'attestation' ? 'attestation_inactivity' : null,
        ));
        socket.once('error', onSocketError);
        // A peer that accepts the connection and closes before the proof completes is
        // never a pass.  For https:// the close before the handshake is a TLS failure
        // instead, since the tunnel was never established.
        socket.once('close', () => {
            if (phase === 'attestation') {
                settle(PROXY_CONNECT_TUNNEL_PROOF_FAILED, 'tunnel_closed_before_attestation');
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
    secret = null,
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
    if (secret !== null) {
        // An injected secret must carry the non-enumerable key bytes, so a caller cannot
        // satisfy the attestation contract with a plain object that merely looks like one.
        if (typeof secret !== 'object' || !secret[PREFLIGHT_SECRET_BYTES]) {
            failStageDProxy(PREFLIGHT_ATTESTATION_SECRET_MISSING, 'proxy preflight secret must be a resolved secret carrying key material');
        }
    }
    if (typeof challengeFactory !== 'function') {
        failStageDProxy(STAGE_D_PROXY_PREFLIGHT_CONFIGURATION_INVALID, 'proxy preflight challenge factory must be callable');
    }
    return Object.freeze({
        schema_version: 'footballprediction-stage-d-http-connect-proxy-preflight/v2',
        proxy_contract: STAGE_D_STABLE_PROXY_CONTRACT,
        attestation_protocol: STAGE_D_PROXY_ATTESTATION_PROTOCOL,
        attestation_algorithm: 'HMAC-SHA-256',
        timeout_ms: timeoutMs,
        async run() {
            // All three contracts are resolved before any socket is opened, so a missing
            // proxy endpoint, a missing probe target or a missing/invalid attestation
            // secret fails closed without touching the network.
            const resolved = endpoint || resolveStageDStableProxyEndpoint(env);
            const probeTarget = target || resolveStageDPreflightTarget(env, { proxyEndpoint: resolved });
            const resolvedSecret = secret || resolveStageDPreflightSecret(env);
            return probeStageDHttpConnectProxy({
                endpoint: resolved,
                target: probeTarget,
                secret: resolvedSecret,
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
    STAGE_D_PROXY_PREFLIGHT_CONFIGURATION_INVALID,
    STAGE_D_PROXY_PREFLIGHT_SECRET_ENV_VAR,
    STAGE_D_PROXY_ATTESTATION_PROTOCOL,
    STAGE_D_PROXY_ATTESTATION_MAC_BYTES,
    STAGE_D_PROXY_ATTESTATION_MIN_SECRET_BYTES,
    STAGE_D_PROXY_CHALLENGE_BYTES,
    STAGE_D_PROXY_RUN_ID_BYTES,
    PROXY_PREFLIGHT_CLASSIFICATIONS,
    PREFLIGHT_ATTESTATION_CONFIGURATION_CLASSIFICATIONS,
    PREFLIGHT_ATTESTATION_SECRET_MISSING,
    PREFLIGHT_ATTESTATION_SECRET_INVALID,
    PROXY_CONNECT_ATTESTATION_MALFORMED,
    PROXY_CONNECT_ATTESTATION_RUN_ID_MISMATCH,
    PROXY_CONNECT_ATTESTATION_MAC_INVALID,
    PROXY_CONNECT_ATTESTATION_TIMEOUT,
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
    PROXY_PREFLIGHT_TARGET_EXTERNAL_HOST,
    resolveStageDStableProxyEndpoint,
    resolveStageDPreflightTarget,
    resolveStageDPreflightSecret,
    buildStageDProxyAgentUrl,
    buildStageDProxyAuthorizationHeader,
    buildStageDAttestationMessage,
    buildStageDAttestationResponse,
    buildStageDAttestationChallengeRequest,
    classifyStageDProxySocketError: classifyProxySocketError,
    createStageDHttpConnectProxyPreflight,
};
