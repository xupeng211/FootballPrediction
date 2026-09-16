'use strict';

// Stage D dedicated stable HTTP CONNECT proxy: endpoint resolution and protocol preflight.
//
// Every network interaction in this file is a loopback listener created by the test
// itself.  The probe destination is the contract's own unusable loopback address, so
// these tests resolve no provider DNS name, contact no provider, and consume no quota.
// The credentials below are obvious fakes; no real secret appears in any assertion.

const assert = require('node:assert/strict');
const fs = require('node:fs');
const net = require('node:net');
const path = require('node:path');
const test = require('node:test');

const {
    STAGE_D_PROXY_ENDPOINT_ENV_VAR,
    STAGE_D_PROXY_PREFLIGHT_TIMEOUT_MS,
    PROXY_PREFLIGHT_PASS,
    PROXY_CONFIGURATION_MISSING,
    PROXY_URL_INVALID,
    PROXY_DNS_OR_ADDRESS_RESOLUTION_FAILURE,
    PROXY_TCP_CONNECT_FAILED,
    PROXY_TLS_HANDSHAKE_FAILED,
    PROXY_CONNECT_PROTOCOL_INVALID,
    PROXY_CONNECT_PREFLIGHT_TIMEOUT,
    PROXY_AUTHENTICATION_CONFIGURATION_FAILURE,
    STAGE_D_PROXY_PREFLIGHT_CONFIGURATION_INVALID,
    PROXY_PREFLIGHT_CLASSIFICATIONS,
    PROXY_CONNECT_PROOF_STATUSES,
    resolveStageDStableProxyEndpoint,
    buildStageDProxyAgentUrl,
    classifyStageDProxySocketError,
    createStageDHttpConnectProxyPreflight,
} = require('../../../src/infrastructure/market_evidence/stageDStableProxy');

const FAKE_USERNAME = 'stage-d-fake-proxy-user';
const FAKE_PASSWORD = 'stage-d-fake-proxy-password';

// Every classification the probe actually returned while this file ran, so the last test
// can prove the probe never invents an outcome outside its declared taxonomy.
const observedOutcomes = new Set();

function endpointUrl({ port, scheme = 'http', credentials = null, host = '127.0.0.1' }) {
    const auth = credentials ? `${credentials.username}:${credentials.password}@` : '';
    return `${scheme}://${auth}${host}:${port}`;
}

function resolveEndpoint(options) {
    return resolveStageDStableProxyEndpoint({ [STAGE_D_PROXY_ENDPOINT_ENV_VAR]: endpointUrl(options) });
}

// A loopback stand-in for an HTTP CONNECT proxy.  `respond` is called once per
// completed request head with the raw bytes the probe sent.
function startProxyStandIn(t, respond) {
    return new Promise(resolve => {
        const sent = [];
        const sockets = new Set();
        const server = net.createServer(socket => {
            sockets.add(socket);
            socket.on('close', () => sockets.delete(socket));
            socket.on('error', () => undefined);
            socket.on('data', chunk => {
                sent.push(chunk.toString('latin1'));
                const head = sent.join('');
                if (head.includes('\r\n\r\n')) respond(socket, head);
            });
        });
        server.listen(0, '127.0.0.1', () => {
            t.after(() => new Promise(done => {
                for (const socket of sockets) socket.destroy();
                server.close(() => done());
            }));
            resolve({ port: server.address().port, sent, requestText: () => sent.join('') });
        });
    });
}

async function preflight(port, { timeoutMs = STAGE_D_PROXY_PREFLIGHT_TIMEOUT_MS, credentials = null } = {}) {
    const result = await createStageDHttpConnectProxyPreflight({
        endpoint: resolveEndpoint({ port, credentials }),
        timeoutMs,
    }).run();
    observedOutcomes.add(result.classification);
    return result;
}

test('a CONNECT-speaking endpoint passes, and the probe names no provider', async t => {
    const proxy = await startProxyStandIn(t, socket => socket.end('HTTP/1.1 200 Connection Established\r\n\r\n'));
    const result = await preflight(proxy.port);

    assert.equal(result.passed, true);
    assert.equal(result.classification, PROXY_PREFLIGHT_PASS);
    assert.equal(result.has_credentials, false);

    // The load-bearing proof that the preflight is provider-independent: the only
    // bytes the endpoint ever sees ask it to tunnel to the contract's loopback probe
    // address.  No provider hostname, path or credential can appear here.
    const request = proxy.requestText();
    assert.match(request, /^CONNECT 127\.0\.0\.1:1 HTTP\/1\.1\r\n/);
    assert.match(request, /\r\nHost: 127\.0\.0\.1:1\r\n/);
    assert.equal(/the-odds-api/i.test(request), false);
    assert.equal(/api\./.test(request), false);
});

test('an endpoint that demands authentication the caller did not configure fails closed', async t => {
    // The endpoint would authenticate the governed request no better than it authenticated
    // this probe, so passing here would spend the one-shot authorization on a request that
    // cannot succeed.  It has to fail closed instead.
    const proxy = await startProxyStandIn(t, socket => socket.end('HTTP/1.1 407 Proxy Authentication Required\r\nProxy-Authenticate: Basic realm="stage-d"\r\n\r\n'));
    const result = await preflight(proxy.port);

    assert.equal(result.passed, false);
    assert.equal(result.classification, PROXY_AUTHENTICATION_CONFIGURATION_FAILURE);
    assert.equal(result.detail, 'proxy_authentication_required_but_no_credentials_configured');
    assert.equal(result.has_credentials, false);
    assert.equal(/Proxy-Authorization/i.test(proxy.requestText()), false);
});

test('an ordinary HTTP origin server is not mistaken for a CONNECT proxy', async t => {
    // The statuses a plain web server answers to a CONNECT it does not implement.  Each one
    // is a well-formed HTTP status line, which is exactly why accepting "any status line"
    // would let a non-proxy endpoint through the last gate before authorization is spent.
    for (const [status, reason] of [[400, 'Bad Request'], [404, 'Not Found'], [405, 'Method Not Allowed'], [501, 'Not Implemented']]) {
        const origin = await startProxyStandIn(t, socket => socket.end(`HTTP/1.1 ${status} ${reason}\r\nContent-Length: 0\r\n\r\n`));
        const result = await preflight(origin.port);

        assert.equal(result.passed, false, `${status} must not pass`);
        assert.equal(result.classification, PROXY_CONNECT_PROTOCOL_INVALID, `${status} must be classified as a non-proxy response`);
        assert.equal(result.detail, `non_proxy_status_${status}`);
    }
});

test('only proxy-class refusals of the unreachable probe target count as protocol proof', async t => {
    // The probe destination is deliberately unusable, so a working proxy refuses the tunnel
    // rather than opening it.  These are the refusals only a CONNECT-implementing proxy
    // produces; the set is pinned so widening it has to be a reviewed decision.
    assert.deepEqual([...PROXY_CONNECT_PROOF_STATUSES], [403, 502, 503, 504]);
    for (const [status, reason] of [[403, 'Forbidden'], [502, 'Bad Gateway'], [503, 'Service Unavailable'], [504, 'Gateway Timeout']]) {
        const proxy = await startProxyStandIn(t, socket => socket.end(`HTTP/1.1 ${status} ${reason}\r\n\r\n`));
        const result = await preflight(proxy.port);

        assert.equal(result.passed, true, `${status} is a proxy-class tunnel refusal and must pass`);
        assert.equal(result.classification, PROXY_PREFLIGHT_PASS);
        assert.equal(result.detail, `proxy_status_${status}`);
    }
    for (const status of [400, 404, 405, 501]) {
        assert.equal(PROXY_CONNECT_PROOF_STATUSES.includes(status), false, `${status} must stay outside the proof set`);
    }
});

test('an endpoint that rejects the configured credentials fails closed without leaking them', async t => {
    const proxy = await startProxyStandIn(t, socket => socket.end('HTTP/1.1 407 Proxy Authentication Required\r\n\r\n'));
    const result = await preflight(proxy.port, { credentials: { username: FAKE_USERNAME, password: FAKE_PASSWORD } });

    assert.equal(result.passed, false);
    assert.equal(result.classification, PROXY_AUTHENTICATION_CONFIGURATION_FAILURE);
    assert.equal(result.has_credentials, true);

    const expected = Buffer.from(`${FAKE_USERNAME}:${FAKE_PASSWORD}`, 'utf8').toString('base64');
    assert.equal(proxy.requestText().includes(`Proxy-Authorization: Basic ${expected}\r\n`), true);

    // The credential must survive into the request but never into the evidence.
    const serialized = JSON.stringify(result);
    assert.equal(serialized.includes(FAKE_PASSWORD), false);
    assert.equal(serialized.includes(expected), false);
    assert.equal(result.endpoint, `http://<redacted>@127.0.0.1:${proxy.port}`);
});

test('a non-HTTP listener is not mistaken for a CONNECT proxy', async t => {
    const proxy = await startProxyStandIn(t, socket => socket.end(Buffer.from([0x05, 0x00])));
    const result = await preflight(proxy.port);

    assert.equal(result.passed, false);
    assert.equal(result.classification, PROXY_CONNECT_PROTOCOL_INVALID);
});

test('a listener that closes before completing a status line fails closed promptly', async t => {
    const proxy = await startProxyStandIn(t, socket => socket.end('HTTP/1.1 200'));
    const startedAt = Date.now();
    const result = await preflight(proxy.port, { timeoutMs: 30000 });

    assert.equal(result.passed, false);
    assert.equal(result.classification, PROXY_CONNECT_PROTOCOL_INVALID);
    assert.equal(result.detail, 'connection_closed_before_status_line');
    assert.equal(Date.now() - startedAt < 5000, true, 'an incomplete status line must not wait out the inactivity timeout');
});

test('a silent listener times out rather than passing', async t => {
    const proxy = await startProxyStandIn(t, () => undefined);
    const result = await preflight(proxy.port, { timeoutMs: 150 });

    assert.equal(result.passed, false);
    assert.equal(result.classification, PROXY_CONNECT_PREFLIGHT_TIMEOUT);
});

test('a dead endpoint fails closed instead of falling back anywhere', async t => {
    // Port 1 is privileged and never bound, so this is refused deterministically rather
    // than racing an ephemeral port that another parallel test file could reclaim.
    const result = await preflight(1);

    assert.equal(result.passed, false);
    assert.equal(result.classification, PROXY_TCP_CONNECT_FAILED);
    assert.equal(result.detail, 'ECONNREFUSED');
});

test('an absent endpoint fails closed while the rotating harvesting pool remains configured', () => {
    // The pool this contract must never fall back to is present and untouched.
    const poolConfigPath = path.join(__dirname, '../../../config/proxy_pools.json');
    assert.equal(fs.existsSync(poolConfigPath), true);
    const pool = JSON.parse(fs.readFileSync(poolConfigPath, 'utf8'));
    assert.equal(pool.default.protocol, 'socks5');
    assert.equal(pool.default.ports.length, 40, 'the rotating default pool must still exist, unshrunk, for harvesting');

    for (const env of [{}, { [STAGE_D_PROXY_ENDPOINT_ENV_VAR]: '' }, { [STAGE_D_PROXY_ENDPOINT_ENV_VAR]: '   ' }]) {
        assert.throws(
            () => resolveStageDStableProxyEndpoint(env),
            error => error.code === PROXY_CONFIGURATION_MISSING && error.message.includes(STAGE_D_PROXY_ENDPOINT_ENV_VAR),
        );
    }
});

test('the SOCKS scheme of the harvesting pool is rejected for the Stage D provider transport', () => {
    for (const url of ['socks5://127.0.0.1:10001', 'socks5h://127.0.0.1:10001', 'socks4://127.0.0.1:10001']) {
        assert.throws(
            () => resolveStageDStableProxyEndpoint({ [STAGE_D_PROXY_ENDPOINT_ENV_VAR]: url }),
            error => error.code === PROXY_URL_INVALID,
        );
    }
});

test('a malformed endpoint is rejected rather than guessed at', () => {
    for (const url of ['not-a-url', 'proxy.internal:3128', 'http://', 'ftp://proxy.internal:3128', 'http://proxy.internal:0']) {
        assert.throws(
            () => resolveStageDStableProxyEndpoint({ [STAGE_D_PROXY_ENDPOINT_ENV_VAR]: url }),
            error => error.code === PROXY_URL_INVALID,
        );
    }
});

test('the resolved endpoint applies scheme defaults and stays credential-free when enumerable', () => {
    const httpEndpoint = resolveStageDStableProxyEndpoint({ [STAGE_D_PROXY_ENDPOINT_ENV_VAR]: 'http://proxy.internal' });
    assert.equal(httpEndpoint.port, 80);
    assert.equal(httpEndpoint.scheme, 'http');
    assert.equal(httpEndpoint.redacted, 'http://proxy.internal:80');

    const httpsEndpoint = resolveStageDStableProxyEndpoint({ [STAGE_D_PROXY_ENDPOINT_ENV_VAR]: 'https://proxy.internal' });
    assert.equal(httpsEndpoint.port, 443);
    assert.equal(httpsEndpoint.scheme, 'https');

    // parseable.host keeps IPv6 bracketing intact for agent URL reconstruction.
    const ipv6Endpoint = resolveStageDStableProxyEndpoint({ [STAGE_D_PROXY_ENDPOINT_ENV_VAR]: `http://[::1]:3128` });
    assert.equal(ipv6Endpoint.host, '[::1]');
    assert.equal(buildStageDProxyAgentUrl(ipv6Endpoint), 'http://[::1]:3128');
});

test('proxy credentials are never reachable through enumeration or serialization', () => {
    const url = endpointUrl({ port: 3128, credentials: { username: FAKE_USERNAME, password: FAKE_PASSWORD } });
    const endpoint = resolveStageDStableProxyEndpoint({ [STAGE_D_PROXY_ENDPOINT_ENV_VAR]: url });

    assert.equal(endpoint.has_credentials, true);
    assert.equal(endpoint.redacted, 'http://<redacted>@127.0.0.1:3128');
    assert.equal(JSON.stringify(endpoint).includes(FAKE_PASSWORD), false);
    assert.equal(JSON.stringify({ ...endpoint }).includes(FAKE_PASSWORD), false);
    // Pin the entire enumerable surface.  Adding any enumerable field here is exactly
    // the change that could leak a secret into evidence, so it must fail this test and
    // be reviewed deliberately.  `authority` is parseable.host and carries no credentials.
    assert.deepEqual(Object.keys(endpoint).sort(), ['authority', 'has_credentials', 'host', 'port', 'redacted', 'scheme']);
    assert.equal(typeof endpoint.has_credentials, 'boolean');
    assert.equal(endpoint.authority, '127.0.0.1:3128');

    // Only the agent-URL builder re-attaches them.  URL pre-encodes userinfo, so the
    // builder must splice it back verbatim rather than encoding it a second time.
    assert.equal(buildStageDProxyAgentUrl(endpoint), url);
    // The two characters that break naive URL assembly: an "@" in the username and a ":"
    // plus an "@" in the secret.  Splicing the encoded userinfo through verbatim is what
    // keeps these intact; encoding it a second time would mangle both.
    const awkwardUserInfo = 'fake:p@ss';
    const special = resolveEndpoint({ port: 3128, credentials: { username: 'fake@user', password: awkwardUserInfo } });
    assert.equal(buildStageDProxyAgentUrl(special), 'http://fake%40user:fake%3Ap%40ss@127.0.0.1:3128');
});

test('the preflight rejects an unusable timeout before it can open a socket', () => {
    for (const timeoutMs of [0, -1, 1.5, '5000', null]) {
        assert.throws(
            () => createStageDHttpConnectProxyPreflight({ timeoutMs }),
            error => error.code === STAGE_D_PROXY_PREFLIGHT_CONFIGURATION_INVALID,
        );
    }
});

test('socket failures are classified, and an unrecognized failure is never a pass', () => {
    const classifications = [
        ['ENOTFOUND', PROXY_DNS_OR_ADDRESS_RESOLUTION_FAILURE],
        ['EAI_AGAIN', PROXY_DNS_OR_ADDRESS_RESOLUTION_FAILURE],
        ['ECONNREFUSED', PROXY_TCP_CONNECT_FAILED],
        ['EHOSTUNREACH', PROXY_TCP_CONNECT_FAILED],
        ['ETIMEDOUT', PROXY_TCP_CONNECT_FAILED],
        ['ERR_TLS_CERT_ALTNAME_INVALID', PROXY_TLS_HANDSHAKE_FAILED],
        ['DEPTH_ZERO_SELF_SIGNED_CERT', PROXY_TLS_HANDSHAKE_FAILED],
        ['ERR_SSL_WRONG_VERSION_NUMBER', PROXY_TLS_HANDSHAKE_FAILED],
    ];
    for (const [code, expected] of classifications) {
        assert.equal(classifyStageDProxySocketError({ code }, { scheme: 'http', tlsEstablished: false }), expected, code);
    }

    const unrecognized = { code: 'ESOMETHING_NEW' };
    assert.equal(classifyStageDProxySocketError(unrecognized, { scheme: 'http', tlsEstablished: false }), PROXY_TCP_CONNECT_FAILED);
    assert.equal(classifyStageDProxySocketError(unrecognized, { scheme: 'https', tlsEstablished: false }), PROXY_TLS_HANDSHAKE_FAILED);
    assert.equal(classifyStageDProxySocketError(unrecognized, { scheme: 'https', tlsEstablished: true }), PROXY_TCP_CONNECT_FAILED);
    assert.equal(classifyStageDProxySocketError({}, { scheme: 'http', tlsEstablished: false }), PROXY_TCP_CONNECT_FAILED);
    assert.equal(classifyStageDProxySocketError(new Error('no code'), { scheme: 'http', tlsEstablished: false }), PROXY_TCP_CONNECT_FAILED);

    // No classification, including the ones above, may be the pass sentinel.
    for (const [, classification] of classifications) assert.notEqual(classification, PROXY_PREFLIGHT_PASS);
});

test('the probe never returns an outcome outside its declared taxonomy', () => {
    assert.equal(new Set(PROXY_PREFLIGHT_CLASSIFICATIONS).size, PROXY_PREFLIGHT_CLASSIFICATIONS.length);
    assert.equal(PROXY_PREFLIGHT_CLASSIFICATIONS.includes(PROXY_PREFLIGHT_PASS), true);

    for (const classification of observedOutcomes) {
        assert.equal(PROXY_PREFLIGHT_CLASSIFICATIONS.includes(classification), true, `undeclared outcome: ${classification}`);
    }
    // Guard against the taxonomy test passing vacuously because nothing ran.
    assert.equal(observedOutcomes.size >= 5, true, `only ${observedOutcomes.size} outcomes were exercised`);
    assert.equal([...observedOutcomes].some(classification => classification === PROXY_PREFLIGHT_PASS), true);
    assert.equal([...observedOutcomes].some(classification => classification !== PROXY_PREFLIGHT_PASS), true);
});
