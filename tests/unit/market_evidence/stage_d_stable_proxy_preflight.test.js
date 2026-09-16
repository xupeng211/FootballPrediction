'use strict';

// Stage D dedicated stable HTTP CONNECT proxy: endpoint resolution, probe-target
// resolution, credential fidelity and the strict tunnel proof.
//
// Every network interaction in this file is a loopback listener created by the test
// itself: a stand-in proxy, and a stand-in project-controlled probe target.  Nothing
// here resolves a provider DNS name, contacts a provider or consumes quota, and the
// only host name that ever appears in a probe request is 127.0.0.1.  The credentials
// below are obvious fakes; no real secret appears in any assertion.

const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const net = require('node:net');
const path = require('node:path');
const test = require('node:test');

const { HttpsProxyAgent } = require('https-proxy-agent');

const {
    STAGE_D_PROXY_ENDPOINT_ENV_VAR,
    STAGE_D_PROXY_PREFLIGHT_TARGET_ENV_VAR,
    STAGE_D_PROXY_PREFLIGHT_TIMEOUT_MS,
    STAGE_D_PROXY_NONCE_REQUEST_PREFIX,
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
    STAGE_D_PROXY_PREFLIGHT_CONFIGURATION_INVALID,
    PROXY_PREFLIGHT_CLASSIFICATIONS,
    resolveStageDStableProxyEndpoint,
    resolveStageDPreflightTarget,
    buildStageDProxyAgentUrl,
    buildStageDProxyAuthorizationHeader,
    classifyStageDProxySocketError,
    createStageDHttpConnectProxyPreflight,
} = require('../../../src/infrastructure/market_evidence/stageDStableProxy');

const FAKE_USERNAME = 'stage-d-fake-proxy-user';
const FAKE_PASSWORD = 'stage-d-fake-proxy-password';

// The standardized discard port.  It is privileged and essentially never bound, so a
// target on it is usable as an explicitly configured probe destination in the tests
// that expect the probe to fail before any tunnel could be needed.  It is never a
// default in the module: the contract requires the target to be configured.
const INERT_TARGET_PORT = 9;

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

function testTarget(port, { proxyPort = null, host = '127.0.0.1' } = {}) {
    return resolveStageDPreflightTarget(
        { [STAGE_D_PROXY_PREFLIGHT_TARGET_ENV_VAR]: `tcp://${host}:${port}` },
        { proxyEndpoint: proxyPort === null ? null : resolveEndpoint({ port: proxyPort }) },
    );
}

async function waitFor(predicate, timeoutMs = 2000) {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
        if (predicate()) return true;
        await new Promise(done => { setTimeout(done, 10); });
    }
    return predicate();
}

// A loopback stand-in for an HTTP CONNECT endpoint.  It captures every byte of the
// request and hands the completed request head to `respond` exactly once per
// connection, so a test can script any response shape without a real proxy.
function startProxyStandIn(t, respond) {
    return new Promise(resolve => {
        const sent = [];
        const sockets = new Set();
        const state = { respond };
        const server = net.createServer(socket => {
            sockets.add(socket);
            socket.on('close', () => sockets.delete(socket));
            socket.on('error', () => undefined);
            let handled = false;
            socket.on('data', chunk => {
                sent.push(chunk.toString('latin1'));
                const head = sent.join('');
                if (!handled && head.includes('\r\n\r\n')) {
                    handled = true;
                    state.respond(socket, head);
                }
            });
        });
        server.listen(0, '127.0.0.1', () => {
            t.after(() => new Promise(done => {
                for (const socket of sockets) socket.destroy();
                server.close(() => done());
            }));
            resolve({
                port: server.address().port,
                requestText: () => sent.join(''),
                openSocketCount: () => sockets.size,
                setRespond: fn => { state.respond = fn; },
            });
        });
    });
}

// The project-controlled probe target: a plain TCP listener that echoes the nonce out
// of each `STAGE-D-PREFLIGHT <probe_id> <nonce>` line, which is the only behaviour the
// Stage D contract asks of whatever the Owner eventually deploys.
function startProbeTarget(t, { mutateEcho = null } = {}) {
    return new Promise(resolve => {
        const lines = [];
        const server = net.createServer(socket => {
            socket.on('error', () => undefined);
            let buffer = '';
            socket.on('data', chunk => {
                buffer += chunk.toString('latin1');
                let index;
                while ((index = buffer.indexOf('\n')) !== -1) {
                    const line = buffer.slice(0, index).replace(/\r$/, '');
                    buffer = buffer.slice(index + 1);
                    lines.push(line);
                    const parts = line.split(' ');
                    if (parts[0] !== STAGE_D_PROXY_NONCE_REQUEST_PREFIX || parts.length !== 3) continue;
                    socket.write(mutateEcho ? mutateEcho(parts[2]) : `${parts[2]}\n`);
                }
            });
        });
        server.listen(0, '127.0.0.1', () => {
            t.after(() => new Promise(done => { server.close(() => done()); }));
            resolve({ port: server.address().port, lines });
        });
    });
}

// A conformant HTTP CONNECT proxy: it dials the destination named in the request and
// pipes bytes both ways.  This is what a real deployment's proxy does, and it is the
// only shape that can carry the nonce proof.
async function startTunnellingProxy(t, { behavior = null } = {}) {
    const target = await startProbeTarget(t);
    const proxy = await startProxyStandIn(t, (socket, head) => {
        const match = /^CONNECT ([^\s]+) HTTP\/1\.1\r\n/.exec(head);
        const destination = match ? match[1] : '';
        const port = Number(destination.split(':').pop());
        if (behavior) {
            behavior(socket, { destination, port, head });
            return;
        }
        const upstream = net.connect({ host: '127.0.0.1', port });
        upstream.once('connect', () => {
            socket.write('HTTP/1.1 200 Connection Established\r\n\r\n');
            socket.pipe(upstream);
            upstream.pipe(socket);
        });
        upstream.once('error', () => socket.end('HTTP/1.1 502 Bad Gateway\r\n\r\n'));
        socket.once('close', () => upstream.destroy());
    });
    return { proxy, target };
}

async function preflight(port, { timeoutMs = STAGE_D_PROXY_PREFLIGHT_TIMEOUT_MS, credentials = null, target = null } = {}) {
    const result = await createStageDHttpConnectProxyPreflight({
        endpoint: resolveEndpoint({ port, credentials }),
        target: target || testTarget(INERT_TARGET_PORT),
        timeoutMs,
    }).run();
    observedOutcomes.add(result.classification);
    return result;
}

test('a proxy that really tunnels to the configured target passes the nonce proof', async t => {
    const { proxy, target } = await startTunnellingProxy(t);
    const result = await preflight(proxy.port, { target: testTarget(target.port, { proxyPort: proxy.port }) });

    assert.equal(result.passed, true);
    assert.equal(result.classification, PROXY_PREFLIGHT_PASS);
    assert.equal(result.detail, 'connect_2xx_nonce_round_trip');
    assert.equal(result.nonce_verified, true);
    assert.equal(result.proof_level, 'L3');
    assert.equal(result.has_credentials, false);

    // The load-bearing proof that the preflight is provider-independent: the only bytes
    // the endpoint ever sees ask it to tunnel to the configured loopback target.  No
    // provider hostname, path or credential can appear here.
    const request = proxy.requestText();
    assert.match(request, new RegExp(`^CONNECT 127\\.0\\.0\\.1:${target.port} HTTP/1\\.1\r\n`));
    assert.match(request, new RegExp(`\r\nHost: 127\\.0\\.0\\.1:${target.port}\r\n`));
    assert.equal(/the-odds-api/i.test(request), false);
    assert.equal(/api\./.test(request), false);

    // The pass is a data-plane fact, not a status line: the target actually received a
    // challenge line and echoed its nonce back through the tunnel.
    assert.equal(target.lines.length, 1);
    const [probeId, nonce] = target.lines[0].split(' ').slice(1);
    assert.match(probeId, /^[0-9a-f]{16}$/);
    assert.match(nonce, /^[0-9a-f]{32}$/);
    assert.equal(request.includes(target.lines[0]), true);
});

test('a synthetic 200 that opens no tunnel fails the data-plane proof', async t => {
    // The mandatory §26 case: an endpoint that answers "200 Connection Established" and
    // then does nothing at all looks like a working proxy to any status-line check.  It
    // must fail, because no tunnel ever carried a byte for us.
    const proxy = await startProxyStandIn(t, socket => socket.write('HTTP/1.1 200 Connection Established\r\n\r\n'));
    const result = await preflight(proxy.port, { timeoutMs: 250, target: testTarget(INERT_TARGET_PORT) });

    assert.equal(result.passed, false);
    assert.equal(result.classification, PROXY_CONNECT_TUNNEL_PROOF_FAILED);
    assert.equal(result.detail, 'nonce_round_trip_inactivity');
    assert.equal(result.nonce_verified, false);
});

test('a 200 that is followed by a stale or synthetic echo fails the proof', async t => {
    // A responder that answers the CONNECT but replays something other than the nonce it
    // was just sent -- a cached response, a fixed banner, or a proxy that never actually
    // forwarded the write.  Each shape fails closed.
    const wrongNonce = await startTunnellingProxy(t, {
        behavior: socket => {
            socket.write('HTTP/1.1 200 Connection Established\r\n\r\n');
            socket.write(`${'0'.repeat(32)}\n`);
        },
    });
    const wrong = await preflight(wrongNonce.proxy.port, { target: testTarget(wrongNonce.target.port, { proxyPort: wrongNonce.proxy.port }) });
    assert.equal(wrong.passed, false);
    assert.equal(wrong.classification, PROXY_CONNECT_TUNNEL_PROOF_FAILED);
    assert.equal(wrong.detail, 'nonce_mismatch');

    const emptyLine = await startTunnellingProxy(t, {
        behavior: socket => {
            socket.write('HTTP/1.1 200 Connection Established\r\n\r\n');
            socket.write('\n');
        },
    });
    const empty = await preflight(emptyLine.proxy.port, { target: testTarget(emptyLine.target.port, { proxyPort: emptyLine.proxy.port }) });
    assert.equal(empty.passed, false);
    assert.equal(empty.classification, PROXY_CONNECT_TUNNEL_PROOF_FAILED);
    assert.equal(empty.detail, 'empty_nonce_response');
});

test('a tunnel that closes before proving itself fails closed', async t => {
    const closing = await startTunnellingProxy(t, {
        behavior: socket => socket.end('HTTP/1.1 200 Connection Established\r\n\r\n'),
    });
    const result = await preflight(closing.proxy.port, { timeoutMs: 30000, target: testTarget(closing.target.port, { proxyPort: closing.proxy.port }) });

    assert.equal(result.passed, false);
    assert.equal(result.classification, PROXY_CONNECT_TUNNEL_PROOF_FAILED);
    assert.equal(result.detail, 'tunnel_closed_before_nonce_proof');
});

test('no non-2xx response is accepted as proof of anything', async t => {
    // §7 is explicit that 403, 407, 502, 503 and 504 get no special acceptance.  Every
    // one of these is a syntactically valid HTTP response, and none of them is a tunnel:
    // 403/502/503/504 are what a proxy says when it could not open one, and
    // 400/404/405/501 are what an ordinary origin server says to a CONNECT it does not
    // implement.  A status code cannot tell the two apart, so neither is allowed to pass.
    assert.equal(PROXY_PREFLIGHT_PASS, 'PROXY_PREFLIGHT_PASS');
    for (const [status, reason] of [
        [400, 'Bad Request'], [403, 'Forbidden'], [404, 'Not Found'], [405, 'Method Not Allowed'],
        [501, 'Not Implemented'], [502, 'Bad Gateway'], [503, 'Service Unavailable'], [504, 'Gateway Timeout'],
    ]) {
        const proxy = await startProxyStandIn(t, socket => socket.end(`HTTP/1.1 ${status} ${reason}\r\nContent-Length: 0\r\n\r\n`));
        const result = await preflight(proxy.port);

        assert.equal(result.passed, false, `${status} must not pass`);
        assert.equal(result.classification, PROXY_CONNECT_TUNNEL_REFUSED, `${status} must be classified as a refused tunnel`);
        assert.equal(result.detail, `non_2xx_status_${status}`);
    }
});

test('an endpoint that demands authentication the caller did not configure fails closed', async t => {
    // The endpoint would authenticate the governed request no better than it authenticated
    // this probe, so passing here would spend the one-shot authorization on a request that
    // cannot succeed.  It has to fail closed instead, and a 407 is not proof of a tunnel.
    const proxy = await startProxyStandIn(t, socket => socket.end('HTTP/1.1 407 Proxy Authentication Required\r\nProxy-Authenticate: Basic realm="stage-d"\r\n\r\n'));
    const result = await preflight(proxy.port);

    assert.equal(result.passed, false);
    assert.equal(result.classification, PROXY_AUTHENTICATION_CONFIGURATION_FAILURE);
    assert.equal(result.detail, 'proxy_authentication_required_but_no_credentials_configured');
    assert.equal(result.has_credentials, false);
    assert.equal(/Proxy-Authorization/i.test(proxy.requestText()), false);
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

test('the preflight attaches credentials byte-identically to the agent that transmits', async t => {
    // The regression §11/§13 requires.  `https-proxy-agent` percent-DECODES the URL
    // userinfo before building the Basic payload; a preflight that base64-encoded the
    // still-encoded userinfo would authenticate with different bytes than the transport
    // it exists to gate, and a secret containing "@", ":" or "%" would reach the proxy
    // mangled -- producing a 407 that says nothing about the transport's real chances.
    const secret = { username: 'stage-d@fake', password: 'p@ss:word%40' };
    const standIn = await startProxyStandIn(t, socket => socket.end('HTTP/1.1 502 Bad Gateway\r\n\r\n'));
    const url = `http://${encodeURIComponent(secret.username)}:${encodeURIComponent(secret.password)}@127.0.0.1:${standIn.port}`;

    const agent = new HttpsProxyAgent(url);
    t.after(() => agent.destroy());
    await new Promise(resolve => {
        const req = http.request({ host: '127.0.0.1', port: 1, path: '/', agent, timeout: 2000 }, () => undefined);
        req.on('error', () => resolve());
        req.on('close', () => resolve());
        req.end();
    });

    const transportHeader = /Proxy-Authorization: ([^\r\n]+)/i.exec(standIn.requestText());
    assert.notEqual(transportHeader, null, 'the real agent must have attached a credential');

    const endpoint = resolveStageDStableProxyEndpoint({ [STAGE_D_PROXY_ENDPOINT_ENV_VAR]: url });
    const preflightHeader = buildStageDProxyAuthorizationHeader(endpoint);

    assert.equal(preflightHeader, transportHeader[1]);
    // And the shared value is the raw secret, not its percent-encoded spelling.
    assert.equal(preflightHeader, `Basic ${Buffer.from(`${secret.username}:${secret.password}`, 'utf8').toString('base64')}`);
    assert.equal(preflightHeader.includes('%40'), false);
    assert.equal(preflightHeader.includes('%3A'), false);

    // A credential-less endpoint sends no authorization header at all, rather than an
    // empty one a proxy might read as a failed attempt.
    assert.equal(buildStageDProxyAuthorizationHeader(resolveEndpoint({ port: 3128 })), null);
});

test('an unconfigured probe target fails closed before any socket is opened', async t => {
    const proxy = await startProxyStandIn(t, socket => socket.end('HTTP/1.1 200 Connection Established\r\n\r\n'));
    const runner = createStageDHttpConnectProxyPreflight({ endpoint: resolveEndpoint({ port: proxy.port }), env: {} });

    await assert.rejects(runner.run(), error => error.code === PROXY_PREFLIGHT_TARGET_CONFIGURATION_MISSING);
    assert.equal(proxy.requestText(), '', 'no proxy socket may be opened when the target is unconfigured');
});

test('a probe target must be exactly tcp://host:port, with no default', () => {
    for (const url of [undefined, '', '   ']) {
        const env = url === undefined ? {} : { [STAGE_D_PROXY_PREFLIGHT_TARGET_ENV_VAR]: url };
        assert.throws(
            () => resolveStageDPreflightTarget(env),
            error => error.code === PROXY_PREFLIGHT_TARGET_CONFIGURATION_MISSING
                && error.message.includes(STAGE_D_PROXY_PREFLIGHT_TARGET_ENV_VAR),
        );
    }

    // A default port, a path, a query, a fragment, userinfo, credentials, another scheme,
    // a hostless URL and an out-of-range port are each rejected rather than interpreted.
    // Nothing here accepts a public Internet fallback or infers an address.
    for (const url of [
        'tcp://probe.internal',
        'tcp://probe.internal:0',
        'tcp://probe.internal:65536',
        'tcp://probe.internal:9999/',
        'tcp://probe.internal:9999/health',
        'tcp://probe.internal:9999?a=1',
        'tcp://probe.internal:9999#frag',
        'tcp://user:pass@probe.internal:9999',
        'tcp://:9999',
        'http://probe.internal:9999',
        'https://probe.internal:9999',
        'probe.internal:9999',
        'not-a-url',
    ]) {
        assert.throws(
            () => resolveStageDPreflightTarget({ [STAGE_D_PROXY_PREFLIGHT_TARGET_ENV_VAR]: url }),
            error => error.code === PROXY_PREFLIGHT_TARGET_URL_INVALID,
            `${url} must be rejected`,
        );
    }

    const target = resolveStageDPreflightTarget({ [STAGE_D_PROXY_PREFLIGHT_TARGET_ENV_VAR]: 'tcp://127.0.0.1:9' });
    assert.deepEqual(Object.keys(target).sort(), ['host', 'port', 'redacted']);
    assert.equal(target.redacted, 'tcp://127.0.0.1:9');
    assert.equal(target.port, 9);
});

test('a probe target that names the proxy listener itself is rejected', () => {
    // An endpoint must not be able to prove itself by talking to itself.  This is a
    // literal host:port comparison, so it only rejects the decidable case and makes no
    // unreliable DNS-equivalence assumption.
    assert.throws(
        () => testTarget(3128, { proxyPort: 3128 }),
        error => error.code === PROXY_PREFLIGHT_TARGET_CONFLICTS_WITH_PROXY,
    );
    // A different port on the same host is a different listener and stays legal.
    assert.equal(testTarget(3129, { proxyPort: 3128 }).port, 3129);
});

test('a non-HTTP listener is not mistaken for a CONNECT proxy', async t => {
    // A SOCKS5 greeting: valid for a SOCKS listener, meaningless as a status line.  The
    // contract is for HTTP CONNECT, so this must never pass.
    const socksGreeting = await startProxyStandIn(t, socket => socket.end(Buffer.concat([Buffer.from([0x05, 0x00]), Buffer.from('\n')])));
    const result = await preflight(socksGreeting.port);

    assert.equal(result.passed, false);
    assert.equal(result.classification, PROXY_CONNECT_PROTOCOL_INVALID);
    assert.equal(result.detail, 'non_http_status_line');

    // Binary noise with no line terminator at all: neither a status line nor a completed
    // response, so the close is what ends it.  Still never a pass.
    const binary = await startProxyStandIn(t, socket => socket.end(Buffer.from([0x05, 0x00])));
    const closed = await preflight(binary.port);

    assert.equal(closed.passed, false);
    assert.equal(closed.classification, PROXY_CONNECT_PROTOCOL_INVALID);
    assert.equal(closed.detail, 'connection_closed_before_status_line');
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

test('the probe closes every socket it opened, on the pass and fail paths alike', async t => {
    const { proxy, target } = await startTunnellingProxy(t);
    const passed = await preflight(proxy.port, { target: testTarget(target.port, { proxyPort: proxy.port }) });
    assert.equal(passed.passed, true);
    assert.equal(await waitFor(() => proxy.openSocketCount() === 0), true, 'the tunnel socket must be closed after a pass');

    const dead = await startProxyStandIn(t, socket => socket.end('HTTP/1.1 403 Forbidden\r\n\r\n'));
    const failed = await preflight(dead.port);
    assert.equal(failed.passed, false);
    assert.equal(await waitFor(() => dead.openSocketCount() === 0), true, 'the socket must be closed after a classified failure');
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

    // And an absent endpoint fails closed even when a valid probe target is configured:
    // there is no path from "target present" to "endpoint guessed".
    const runner = createStageDHttpConnectProxyPreflight({ env: { [STAGE_D_PROXY_PREFLIGHT_TARGET_ENV_VAR]: 'tcp://127.0.0.1:9' } });
    return assert.rejects(runner.run(), error => error.code === PROXY_CONFIGURATION_MISSING);
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

test('the preflight rejects a malformed endpoint or target object before it can open a socket', () => {
    for (const endpoint of [{}, { host: '127.0.0.1' }, 'http://127.0.0.1:3128', 42]) {
        assert.throws(
            () => createStageDHttpConnectProxyPreflight({ endpoint }),
            error => error.code === STAGE_D_PROXY_PREFLIGHT_CONFIGURATION_INVALID,
        );
    }
    for (const target of [{}, { host: '127.0.0.1' }, 'tcp://127.0.0.1:9', 42]) {
        assert.throws(
            () => createStageDHttpConnectProxyPreflight({ target }),
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
