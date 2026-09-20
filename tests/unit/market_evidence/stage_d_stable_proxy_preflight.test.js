'use strict';

// Stage D dedicated stable HTTP CONNECT proxy: endpoint resolution, probe-target
// resolution, secret resolution, credential fidelity and the HMAC target attestation.
//
// The centre of gravity here is one attack.  A responder that answers CONNECT with a
// 2xx, reads the client's challenge and reflects it back -- without ever dialing the
// configured target -- must FAIL.  It fails because the pass condition is a keyed MAC
// over a fresh challenge, and a reflector does not hold the key.  Reflection is not
// distinguishable from forwarding by framing alone; only secret material makes it so.
//
// Every network interaction in this file is a loopback listener created by the test
// itself: a stand-in proxy, and a stand-in project-controlled attestation target.
// Nothing here resolves a provider DNS name, contacts a provider or consumes quota, and
// the only host name that ever appears in a probe request is 127.0.0.1.  The credentials
// and the shared secret below are obvious fakes; no real secret appears in any
// assertion, and no test reads the operator's environment or a local .env file.

const assert = require('node:assert/strict');
const { EventEmitter } = require('node:events');
const fs = require('node:fs');
const net = require('node:net');
const path = require('node:path');
const test = require('node:test');

const { HttpsProxyAgent } = require('https-proxy-agent');

const {
    STAGE_D_PROXY_ENDPOINT_ENV_VAR,
    STAGE_D_PROXY_PREFLIGHT_TARGET_ENV_VAR,
    STAGE_D_PROXY_PREFLIGHT_SECRET_ENV_VAR,
    STAGE_D_PROXY_PREFLIGHT_TIMEOUT_MS,
    STAGE_D_PROXY_ATTESTATION_PROTOCOL,
    STAGE_D_PROXY_ATTESTATION_MIN_SECRET_BYTES,
    STAGE_D_PROXY_CHALLENGE_BYTES,
    STAGE_D_PROXY_RUN_ID_BYTES,
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
    PROXY_CONNECT_ATTESTATION_MALFORMED,
    PROXY_CONNECT_ATTESTATION_RUN_ID_MISMATCH,
    PROXY_CONNECT_ATTESTATION_MAC_INVALID,
    PROXY_CONNECT_ATTESTATION_TIMEOUT,
    PROXY_AUTHENTICATION_CONFIGURATION_FAILURE,
    PROXY_PREFLIGHT_TARGET_CONFIGURATION_MISSING,
    PROXY_PREFLIGHT_TARGET_URL_INVALID,
    PROXY_PREFLIGHT_TARGET_CONFLICTS_WITH_PROXY,
    PROXY_PREFLIGHT_TARGET_EXTERNAL_HOST,
    PREFLIGHT_ATTESTATION_SECRET_MISSING,
    PREFLIGHT_ATTESTATION_SECRET_INVALID,
    STAGE_D_PROXY_PREFLIGHT_CONFIGURATION_INVALID,
    PROXY_PREFLIGHT_CLASSIFICATIONS,
    resolveStageDStableProxyEndpoint,
    resolveStageDPreflightTarget,
    resolveStageDPreflightSecret,
    buildStageDProxyAgentUrl,
    buildStageDProxyAuthorizationHeader,
    buildStageDAttestationMessage,
    buildStageDAttestationResponse,
    classifyStageDProxySocketError,
    createStageDHttpConnectProxyPreflight,
} = require('../../../src/infrastructure/market_evidence/stageDStableProxy');

const FAKE_USERNAME = 'stage-d-fake-proxy-user';
const FAKE_PASSWORD = 'stage-d-fake-proxy-password';

// An obvious fake.  It is long enough to clear the module's 32-byte floor, it is not
// derived from anything, and it exists only in this file.  Production never sees it.
const TEST_SECRET_TEXT = 'stage-d-test-secret-not-production-0123456789abcdef';
const OTHER_SECRET_TEXT = 'stage-d-other-fake-secret-0123456789abcdefghij';

function secretEnv(text = TEST_SECRET_TEXT) {
    return { [STAGE_D_PROXY_PREFLIGHT_SECRET_ENV_VAR]: Buffer.from(text, 'utf8').toString('base64') };
}

function testSecret(text = TEST_SECRET_TEXT) {
    return resolveStageDPreflightSecret(secretEnv(text));
}

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

// The project-controlled attestation target: a plain TCP listener that answers each
// `stage-d-proxy-preflight/v1 <run_id> <challenge>` line with the HMAC the shared
// secret produces over that challenge.  This is the whole of what the Stage D contract
// asks of whatever the Owner eventually deploys, and it is the only behaviour a
// conformant responder has that a reflector does not.
//
// `connections` counts every inbound socket, which is how the reflector tests below
// prove the target was never reached: the assertion is not merely that the preflight
// failed, but that it failed for the right reason.
function startProbeTarget(t, { secret = testSecret(), respond = null } = {}) {
    return new Promise(resolve => {
        const lines = [];
        let connections = 0;
        const server = net.createServer(socket => {
            connections += 1;
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
                    if (parts.length !== 3 || parts[0] !== STAGE_D_PROXY_ATTESTATION_PROTOCOL) continue;
                    if (respond) {
                        respond(socket, { runId: parts[1], challenge: parts[2], secret });
                        continue;
                    }
                    socket.write(buildStageDAttestationResponse({ secret, runId: parts[1], challenge: parts[2] }));
                }
            });
        });
        server.listen(0, '127.0.0.1', () => {
            t.after(() => new Promise(done => { server.close(() => done()); }));
            resolve({ port: server.address().port, lines, connectionCount: () => connections });
        });
    });
}

// A conformant HTTP CONNECT proxy: it dials the destination named in the request and
// pipes bytes both ways.  This is what a real deployment's proxy does, and it is the
// shape a reflector merely imitates.  It dials whatever port the CONNECT names, so a
// caller can point the preflight at a target of its choosing -- `target` here only
// names the default one this helper stands up for its own convenience.
async function startTunnellingProxy(t, { behavior = null, secret = testSecret(), target = null } = {}) {
    target = target || await startProbeTarget(t, { secret });
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

async function preflight(port, {
    timeoutMs = STAGE_D_PROXY_PREFLIGHT_TIMEOUT_MS,
    credentials = null,
    target = null,
    secret = testSecret(),
} = {}) {
    const result = await createStageDHttpConnectProxyPreflight({
        endpoint: resolveEndpoint({ port, credentials }),
        target: target || testTarget(INERT_TARGET_PORT),
        secret,
        timeoutMs,
    }).run();
    observedOutcomes.add(result.classification);
    return result;
}

test('a proxy that really tunnels to the configured target passes the HMAC attestation', async t => {
    const { proxy, target } = await startTunnellingProxy(t);
    const result = await preflight(proxy.port, { target: testTarget(target.port, { proxyPort: proxy.port }) });

    assert.equal(result.passed, true);
    assert.equal(result.classification, PROXY_PREFLIGHT_PASS);
    assert.equal(result.detail, 'connect_2xx_target_hmac_attested');
    assert.equal(result.target_attested, true);
    assert.equal(result.attestation_algorithm, 'HMAC-SHA-256');
    assert.equal(result.proof_level, 'AUTHENTICATED_PROJECT_CONTROLLED_TARGET_REACHABILITY');
    assert.equal(result.has_credentials, false);
    // The claim this proof makes is bounded, and the result says so itself: a proven
    // tunnel to a secret-holding target is not a proven provider path.
    assert.equal(result.provider_reachability_proven, false);
    assert.equal(result.provider_contacted, false);
    assert.equal(result.provider_dns_resolved, false);

    // The load-bearing proof that the preflight is provider-independent: the only bytes
    // the endpoint ever sees ask it to tunnel to the configured loopback target.  No
    // provider hostname, path or credential can appear here.
    const request = proxy.requestText();
    assert.match(request, new RegExp(`^CONNECT 127\\.0\\.0\\.1:${target.port} HTTP/1\\.1\r\n`));
    assert.match(request, new RegExp(`\r\nHost: 127\\.0\\.0\\.1:${target.port}\r\n`));
    assert.equal(/the-odds-api/i.test(request), false);
    assert.equal(/api\./.test(request), false);

    // The pass is a data-plane fact, not a status line: the target actually received a
    // fresh challenge through the tunnel, and the client's acceptance rests on a MAC
    // that only the secret holder could have produced.
    assert.equal(target.lines.length, 1);
    const [runId, challenge] = target.lines[0].split(' ').slice(1);
    assert.match(runId, new RegExp(`^[0-9a-f]{${STAGE_D_PROXY_RUN_ID_BYTES * 2}}$`));
    assert.match(challenge, new RegExp(`^[0-9a-f]{${STAGE_D_PROXY_CHALLENGE_BYTES * 2}}$`));
    assert.equal(request.includes(target.lines[0]), true);
});

test('the challenge is fresh every run, so no two preflights share a MAC input', async t => {
    const { proxy, target } = await startTunnellingProxy(t);
    const probeTarget = testTarget(target.port, { proxyPort: proxy.port });
    await preflight(proxy.port, { target: probeTarget });
    await preflight(proxy.port, { target: probeTarget });

    assert.equal(target.lines.length, 2);
    const [firstRunId, firstChallenge] = target.lines[0].split(' ').slice(1);
    const [secondRunId, secondChallenge] = target.lines[1].split(' ').slice(1);
    assert.notEqual(firstRunId, secondRunId);
    assert.notEqual(firstChallenge, secondChallenge);
});

test('a synthetic 200 that opens no tunnel fails the data-plane proof', async t => {
    // The mandatory §26 case: an endpoint that answers "200 Connection Established" and
    // then does nothing at all looks like a working proxy to any status-line check.  It
    // must fail, because no tunnel ever carried a byte for us.  Once a 2xx is on the
    // wire the classification is always attestation-specific, never the bare protocol
    // timeout that precedes it, so this case has exactly one outcome.
    const proxy = await startProxyStandIn(t, socket => socket.write('HTTP/1.1 200 Connection Established\r\n\r\n'));
    const result = await preflight(proxy.port, { timeoutMs: 250, target: testTarget(INERT_TARGET_PORT) });

    assert.equal(result.passed, false);
    assert.equal(result.classification, PROXY_CONNECT_ATTESTATION_TIMEOUT);
    assert.equal(result.detail, 'attestation_inactivity');
    assert.equal(result.target_attested, false);
});

test('an informed reflector that never dials the target cannot pass', async t => {
    // THE attack this design exists to defeat, reproduced from the independent review
    // that rejected the previous nonce-echo proof.  The endpoint:
    //
    //   1. answers CONNECT with a strict 2xx;
    //   2. reads the client's challenge in full;
    //   3. replies with a syntactically perfect response line, correctly bound to the
    //      run id the client just sent;
    //   4. never opens a connection to the configured target.
    //
    // Under the old contract this passed, because the response was a value the client
    // itself had just supplied.  It must now fail: the MAC is computable only by an
    // entity holding the shared secret, and this endpoint does not have it.  Note that
    // the reflector is given every advantage -- it sees the exact protocol version, the
    // exact run id and the exact challenge, and it answers immediately -- and still
    // cannot produce a passing reply, because the missing ingredient is not information.
    const target = await startProbeTarget(t);
    const reflector = await startProxyStandIn(t, socket => {
        socket.write('HTTP/1.1 200 Connection Established\r\n\r\n');
        let buffer = '';
        socket.on('data', chunk => {
            buffer += chunk.toString('latin1');
            const lineEnd = buffer.indexOf('\n');
            if (lineEnd === -1) return;
            const parts = buffer.slice(0, lineEnd).replace(/\r$/, '').split(' ');
            if (parts.length !== 3 || parts[0] !== STAGE_D_PROXY_ATTESTATION_PROTOCOL) return;
            // Reflect the challenge as though it were a MAC: the naive forger.
            socket.write(`${STAGE_D_PROXY_ATTESTATION_PROTOCOL} ${parts[1]} ${parts[2]}\n`);
        });
    });

    const result = await preflight(reflector.port, { target: testTarget(target.port, { proxyPort: reflector.port }) });

    assert.equal(result.passed, false, 'a reflector must never pass');
    assert.equal(result.classification, PROXY_CONNECT_ATTESTATION_MAC_INVALID);
    assert.equal(result.detail, 'attestation_mac_invalid');
    assert.equal(result.target_attested, false);
    assert.equal(target.connectionCount(), 0, 'the configured target must never have been contacted');
    assert.equal(target.lines.length, 0);

    // An "informed" variant that also guesses a well-formed 64-hex MAC fares no better,
    // which is the point: the response space is not searchable, so the only way to pass
    // is to actually reach the secret holder.
    const guesser = await startProxyStandIn(t, socket => {
        socket.write('HTTP/1.1 200 Connection Established\r\n\r\n');
        let buffer = '';
        socket.on('data', chunk => {
            buffer += chunk.toString('latin1');
            const lineEnd = buffer.indexOf('\n');
            if (lineEnd === -1) return;
            const parts = buffer.slice(0, lineEnd).replace(/\r$/, '').split(' ');
            if (parts.length !== 3 || parts[0] !== STAGE_D_PROXY_ATTESTATION_PROTOCOL) return;
            socket.write(`${STAGE_D_PROXY_ATTESTATION_PROTOCOL} ${parts[1]} ${'ab'.repeat(32)}\n`);
        });
    });
    const guessed = await preflight(guesser.port, { target: testTarget(target.port, { proxyPort: guesser.port }) });

    assert.equal(guessed.passed, false);
    assert.equal(guessed.classification, PROXY_CONNECT_ATTESTATION_MAC_INVALID);
    assert.equal(target.connectionCount(), 0);
});

test('a well-formed response computed with the wrong secret fails', async t => {
    // The strongest possible near-miss: a genuine, correctly framed, correctly bound,
    // correctly encoded HMAC -- produced by an entity that really does hold a secret,
    // just not the configured one.  Every superficial property of a valid response is
    // present, so this is what separates keyed verification from shape validation.
    const wrongKeyTarget = await startProbeTarget(t, { secret: testSecret(OTHER_SECRET_TEXT) });
    const { proxy } = await startTunnellingProxy(t, { target: wrongKeyTarget });
    const result = await preflight(proxy.port, {
        target: testTarget(wrongKeyTarget.port, { proxyPort: proxy.port }),
        secret: testSecret(),
    });

    assert.equal(result.passed, false, 'a response under the wrong key must not pass');
    assert.equal(result.classification, PROXY_CONNECT_ATTESTATION_MAC_INVALID);
    assert.equal(result.detail, 'attestation_mac_invalid');
    // The tunnel really was established and the challenge really did reach the target:
    // this failure is about the key, not about a missing tunnel.
    assert.equal(wrongKeyTarget.lines.length, 1);
    assert.equal(wrongKeyTarget.connectionCount(), 1);
});

test('a response bound to another run id is refused before its MAC is examined', async t => {
    const wrongRunId = await startTunnellingProxy(t, {
        behavior: socket => {
            socket.write('HTTP/1.1 200 Connection Established\r\n\r\n');
            let buffer = '';
            socket.on('data', chunk => {
                buffer += chunk.toString('latin1');
                const lineEnd = buffer.indexOf('\n');
                if (lineEnd === -1) return;
                const parts = buffer.slice(0, lineEnd).replace(/\r$/, '').split(' ');
                if (parts.length !== 3 || parts[0] !== STAGE_D_PROXY_ATTESTATION_PROTOCOL) return;
                socket.write(`${STAGE_D_PROXY_ATTESTATION_PROTOCOL} ${'0'.repeat(32)} ${'0'.repeat(64)}\n`);
            });
        },
    });
    const result = await preflight(wrongRunId.proxy.port, { target: testTarget(wrongRunId.target.port, { proxyPort: wrongRunId.proxy.port }) });

    assert.equal(result.passed, false);
    assert.equal(result.classification, PROXY_CONNECT_ATTESTATION_RUN_ID_MISMATCH);
    assert.equal(result.detail, 'attestation_run_id_mismatch');
});

test('a malformed or unbound attestation response fails closed without waiting', async t => {
    const cases = [
        ['', 'empty_attestation_response'],
        ['not-the-protocol 0 0', 'attestation_response_malformed'],
        [`${STAGE_D_PROXY_ATTESTATION_PROTOCOL} only-two-fields`, 'attestation_response_malformed'],
        [`${STAGE_D_PROXY_ATTESTATION_PROTOCOL} a b c d`, 'attestation_response_malformed'],
    ];
    for (const [payload, detail] of cases) {
        const proxy = await startProxyStandIn(t, socket => {
            socket.write('HTTP/1.1 200 Connection Established\r\n\r\n');
            socket.write(`${payload}\n`);
        });
        const result = await preflight(proxy.port, { timeoutMs: 30000 });

        assert.equal(result.passed, false, `${JSON.stringify(payload)} must not pass`);
        assert.equal(result.classification, PROXY_CONNECT_ATTESTATION_MALFORMED, `${JSON.stringify(payload)} must be malformed`);
        assert.equal(result.detail, detail);
    }

    // A non-conformant target that answers with a MAC that is the right protocol and the
    // right run id but the wrong shape: too short, non-hex, uppercase hex, or truncated.
    // These are framing defects rather than wrong-key results, so they are classified as
    // malformed -- and none of them passes.
    for (const mac of ['ab', 'zz'.repeat(32), 'AB'.repeat(32), 'ab'.repeat(31), '']) {
        const target = await startProbeTarget(t, {
            respond: (socket, { runId }) => socket.write(`${STAGE_D_PROXY_ATTESTATION_PROTOCOL} ${runId} ${mac}\n`),
        });
        const { proxy } = await startTunnellingProxy(t, { target });
        const result = await preflight(proxy.port, { target: testTarget(target.port, { proxyPort: proxy.port }) });

        assert.equal(result.passed, false, `MAC ${JSON.stringify(mac)} must not pass`);
        assert.equal(result.classification, PROXY_CONNECT_ATTESTATION_MALFORMED, `MAC ${JSON.stringify(mac)} must be malformed`);
        assert.equal(target.connectionCount(), 1);
    }
});

test('a response replayed from an earlier run does not validate against a new challenge', async t => {
    // Replay resistance is a property of the challenge, not of a nonce store: the MAC is
    // bound to a challenge this execution has never seen before, so a response captured
    // from any earlier run cannot satisfy it.  This is the regression §13 requires, and
    // it is checked against a response that was genuinely valid when it was produced.
    const secret = testSecret();
    let captured = null;
    const capturingTarget = await startProbeTarget(t, {
        secret,
        respond: (socket, { runId, challenge }) => {
            const response = buildStageDAttestationResponse({ secret, runId, challenge });
            if (captured === null) captured = response;
            socket.write(response);
        },
    });

    // Run one: an honest tunnel to an honest target.  The bytes captured here are a
    // response the verifier genuinely accepted, not a sample we fabricated.
    const { proxy: honest } = await startTunnellingProxy(t, { target: capturingTarget });
    const first = await preflight(honest.port, { target: testTarget(capturingTarget.port, { proxyPort: honest.port }) });
    assert.equal(first.passed, true);
    assert.notEqual(captured, null, 'the capture must have produced a genuinely valid response');
    const capturedMac = captured.trim().split(' ')[2];

    // Replay A -- the response verbatim.  It carries the earlier run id, so it is refused
    // on binding before its MAC is even compared.
    const { proxy: verbatim } = await startTunnellingProxy(t, {
        behavior: socket => {
            socket.write('HTTP/1.1 200 Connection Established\r\n\r\n');
            let buffer = '';
            socket.on('data', chunk => {
                buffer += chunk.toString('latin1');
                if (buffer.includes('\n')) socket.write(captured);
            });
        },
    });
    const replayedVerbatim = await preflight(verbatim.port, { target: testTarget(capturingTarget.port, { proxyPort: verbatim.port }) });
    assert.equal(replayedVerbatim.passed, false, 'a replayed response must never pass');
    assert.equal(replayedVerbatim.classification, PROXY_CONNECT_ATTESTATION_RUN_ID_MISMATCH);

    // Replay B -- the harder case.  The attacker strips the stale run id and re-stamps
    // the MAC with this execution's own run id, so binding passes and the key itself
    // must do the rejecting.  It does: the MAC was computed over a different challenge.
    const { proxy: rebound } = await startTunnellingProxy(t, {
        behavior: socket => {
            socket.write('HTTP/1.1 200 Connection Established\r\n\r\n');
            let buffer = '';
            socket.on('data', chunk => {
                buffer += chunk.toString('latin1');
                const lineEnd = buffer.indexOf('\n');
                if (lineEnd === -1) return;
                const parts = buffer.slice(0, lineEnd).replace(/\r$/, '').split(' ');
                if (parts.length !== 3 || parts[0] !== STAGE_D_PROXY_ATTESTATION_PROTOCOL) return;
                socket.write(`${STAGE_D_PROXY_ATTESTATION_PROTOCOL} ${parts[1]} ${capturedMac}\n`);
            });
        },
    });
    const replayedRebound = await preflight(rebound.port, { target: testTarget(capturingTarget.port, { proxyPort: rebound.port }) });
    assert.equal(replayedRebound.passed, false, 'a re-bound replay must never pass');
    assert.equal(replayedRebound.classification, PROXY_CONNECT_ATTESTATION_MAC_INVALID);
    assert.equal(replayedRebound.target_attested, false);
});

test('a tunnel that closes before attesting itself fails closed', async t => {
    const closing = await startTunnellingProxy(t, {
        behavior: socket => socket.end('HTTP/1.1 200 Connection Established\r\n\r\n'),
    });
    const result = await preflight(closing.proxy.port, { timeoutMs: 30000, target: testTarget(closing.target.port, { proxyPort: closing.proxy.port }) });

    assert.equal(result.passed, false);
    assert.equal(result.classification, PROXY_CONNECT_TUNNEL_PROOF_FAILED);
    assert.equal(result.detail, 'tunnel_closed_before_attestation');
});

test('a target that accepts the challenge but never answers fails rather than passing', async t => {
    const silent = await startProbeTarget(t, { respond: () => undefined });
    const proxy = await startProxyStandIn(t, (socket, head) => {
        const port = Number(head.split(' ')[1].split(':').pop());
        const upstream = net.connect({ host: '127.0.0.1', port });
        upstream.once('connect', () => {
            socket.write('HTTP/1.1 200 Connection Established\r\n\r\n');
            socket.pipe(upstream);
            upstream.pipe(socket);
        });
        socket.once('close', () => upstream.destroy());
    });
    const result = await preflight(proxy.port, { timeoutMs: 250, target: testTarget(silent.port, { proxyPort: proxy.port }) });

    assert.equal(result.passed, false);
    assert.equal(result.classification, PROXY_CONNECT_ATTESTATION_TIMEOUT);
    assert.equal(silent.lines.length, 1, 'the challenge must have reached the target');
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
    //
    // The agent is driven through its own `connect(req, opts)` -- the method agent-base
    // declares as its connection entry point and that the Node HTTP client reaches
    // through `createSocket` on every proxied request.  Calling it directly exercises
    // the library's real CONNECT and credential construction against a real loopback
    // socket, while keeping the exchange entirely inside this process: no request is
    // dispatched and no remote host is named.  `connect` touches only `emit` and `once`
    // on the request object, so an `EventEmitter` is the whole of what it is handed --
    // nothing in the agent itself is stubbed, aliased or reimplemented.
    const secret = { username: 'stage-d@fake', password: 'p@ss:word%40' };
    const standIn = await startProxyStandIn(t, socket => socket.end('HTTP/1.1 502 Bad Gateway\r\n\r\n'));
    const url = `http://${encodeURIComponent(secret.username)}:${encodeURIComponent(secret.password)}@127.0.0.1:${standIn.port}`;

    const agent = new HttpsProxyAgent(url);
    t.after(() => agent.destroy());

    // Resolves only once the proxy's response has been parsed, so the CONNECT head is
    // already on the wire by the time this returns.
    const agentSocket = await agent.connect(new EventEmitter(), { host: '127.0.0.1', port: 1, secureEndpoint: true });
    t.after(() => agentSocket.destroy());

    const requestText = standIn.requestText();
    assert.equal(/^CONNECT 127\.0\.0\.1:1 HTTP\/1\.1\r\n/.test(requestText), true, 'the real agent must have written the CONNECT head');
    const transportHeader = /Proxy-Authorization: ([^\r\n]+)/i.exec(requestText);
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

test('a probe target that names an external provider host is rejected before any socket', async t => {
    // Independent review found this: the target contract accepted any well-formed
    // tcp://host:port, so an operator could name the Stage D provider itself.  The
    // preflight would then have resolved and dialed The Odds API, voiding the proof (a
    // provider is not a project-controlled attesting target) and producing exactly the
    // provider DNS and TCP contact the Stage D invariants forbid -- all before the
    // one-shot authorization is consumed.  Rejection happens at resolution, so no
    // socket is ever opened.
    const providerTargets = [
        'tcp://api.the-odds-api.com:443', // the Stage D provider, the concrete review finding
        'tcp://the-odds-api.com:443', // the apex
        'tcp://API.THE-ODDS-API.COM:443', // case must not be an escape hatch
        'tcp://api.the-odds-api.com.:443', // a trailing dot is the same host, different string
        'tcp://api.oddsportal.com:443', // a listed apex reached through a subdomain
        'tcp://www.fotmob.com:443',
        'tcp://www.football-data.co.uk:443',
        'tcp://resources.premierleague.com:443',
        'tcp://api.telegram.org:443',
        'tcp://api.ipify.org:443',
        'tcp://tls.browserleaks.com:443',
        'tcp://httpbin.org:443',
    ];
    for (const url of providerTargets) {
        assert.throws(
            () => resolveStageDPreflightTarget({ [STAGE_D_PROXY_PREFLIGHT_TARGET_ENV_VAR]: url }),
            error => error.code === PROXY_PREFLIGHT_TARGET_EXTERNAL_HOST,
            `${url} must be rejected as an external host`,
        );
    }

    // The rejection precedes every socket operation, including the TCP connect.
    const proxy = await startProxyStandIn(t, socket => socket.end('HTTP/1.1 200 Connection Established\r\n\r\n'));
    const runner = createStageDHttpConnectProxyPreflight({
        endpoint: resolveEndpoint({ port: proxy.port }),
        env: { [STAGE_D_PROXY_PREFLIGHT_TARGET_ENV_VAR]: 'tcp://api.the-odds-api.com:443' },
        secret: testSecret(),
    });
    await assert.rejects(runner.run(), error => error.code === PROXY_PREFLIGHT_TARGET_EXTERNAL_HOST);
    assert.equal(proxy.requestText(), '', 'no proxy socket may be opened for a rejected target');

    // Names that merely resemble a denied apex are not denied, and an unrelated internal
    // name is still accepted: the rule matches on label boundaries, not substrings.
    for (const host of ['notthe-odds-api.com', 'the-odds-api.com.evil.internal', 'probe.internal']) {
        assert.equal(
            resolveStageDPreflightTarget({ [STAGE_D_PROXY_PREFLIGHT_TARGET_ENV_VAR]: `tcp://${host}:9999` }).host,
            host,
        );
    }
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

test('an unbounded response head fails closed instead of growing without limit', async t => {
    // Every stage is bounded: a peer that streams bytes without ever completing a status
    // line, or without ever terminating the response head, is cut off rather than allowed
    // to hold the preflight -- and the process -- open indefinitely.
    const endlessStatusLine = await startProxyStandIn(t, socket => socket.write(`HTTP/1.1 200 ${'x'.repeat(9000)}`));
    const statusLine = await preflight(endlessStatusLine.port, { timeoutMs: 30000 });
    assert.equal(statusLine.passed, false);
    assert.equal(statusLine.classification, PROXY_CONNECT_PROTOCOL_INVALID);
    assert.equal(statusLine.detail, 'response_too_large');

    const endlessHead = await startProxyStandIn(t, socket => socket.write(`HTTP/1.1 200 Connection Established\r\nX-Pad: ${'x'.repeat(9000)}\r\n`));
    const head = await preflight(endlessHead.port, { timeoutMs: 30000 });
    assert.equal(head.passed, false);
    assert.equal(head.classification, PROXY_CONNECT_PROTOCOL_INVALID);
    assert.equal(head.detail, 'connect_response_head_too_large');
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

test('a bracketed IPv6 endpoint dials the bare address instead of failing to resolve it', async t => {
    // URI syntax and socket addressing disagree on exactly one host form, and the
    // disagreement is not cosmetic: handing "[::1]" to net.connect makes the socket layer
    // treat it as a DNS name, so a perfectly valid endpoint is reported as an
    // address-resolution failure and can never pass the preflight.  This is the falsifiable
    // form of that regression -- dialing the bracketed form at a closed port yields
    // ENOTFOUND and the DNS classification, while dialing the bare address yields a
    // transport refusal (ECONNREFUSED here, ENETUNREACH/EADDRNOTAVAIL on a host without
    // IPv6 loopback -- all three are PROXY_TCP_CONNECT_FAILED, none is a resolution
    // failure, so the assertion holds either way).  Loopback only; no external network.
    const endpoint = resolveEndpoint({ port: 1, host: '[::1]' });
    const result = await createStageDHttpConnectProxyPreflight({
        endpoint,
        target: testTarget(INERT_TARGET_PORT),
        secret: testSecret(),
        timeoutMs: 2000,
    }).run();

    assert.equal(result.passed, false);
    assert.equal(result.classification, PROXY_TCP_CONNECT_FAILED);
    assert.notEqual(result.classification, PROXY_DNS_OR_ADDRESS_RESOLUTION_FAILURE);
    // The evidence record keeps the URI form even though the socket used the bare one.
    assert.equal(result.host, '[::1]');
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

// The generic dev proxy variables are real, are set to a real workstation endpoint by
// docker-compose.dev.yml, and must never be able to satisfy the Stage D provider proxy.
// These three fixtures are the composition-layer fallbacks, expressed as environment:
// the generic family, the host-gateway family, and the port family.  Each one is
// witnessed as actually present before the assertion runs, so a fixture that silently
// stopped being populated could not make the test pass vacuously.
const GENERIC_PROXY_AMBIENT_ENV = Object.freeze({
    HTTP_PROXY: 'http://host.docker.internal:7897',
    HTTPS_PROXY: 'http://host.docker.internal:7897',
    ALL_PROXY: 'socks5://host.docker.internal:7897',
    http_proxy: 'http://host.docker.internal:7897',
    https_proxy: 'http://host.docker.internal:7897',
    all_proxy: 'socks5://host.docker.internal:7897',
});

const HOST_GATEWAY_AMBIENT_ENV = Object.freeze({
    PROXY_LOOPBACK_GATEWAY: 'host.docker.internal',
    DEV_PROXY_HOST: 'host.docker.internal',
    WSL2_PROXY_HOST: 'host.docker.internal',
    DEV_HOST_PROXY_PORT: '7897',
    DEV_PROXY_PORT: '7897',
    DEV_PROXY_PORT_START: '7897',
    DEV_PROXY_PORT_END: '7897',
    DEV_PROXY_PORTS: '7897',
    PROXY_HOST: 'host.docker.internal',
    PROXY_PORT: '7897',
});

test('an ambient generic proxy cannot satisfy the Stage D provider proxy', () => {
    // Witness the precondition: the generic family really is populated.
    for (const [key, value] of Object.entries(GENERIC_PROXY_AMBIENT_ENV)) {
        assert.equal(GENERIC_PROXY_AMBIENT_ENV[key], value);
        assert.notEqual(value, '', `${key} fixture must be non-empty to be a real fallback`);
    }
    assert.throws(
        () => resolveStageDStableProxyEndpoint({ ...GENERIC_PROXY_AMBIENT_ENV }),
        error => error.code === PROXY_CONFIGURATION_MISSING && error.message.includes(STAGE_D_PROXY_ENDPOINT_ENV_VAR),
    );
});

test('the dev host-gateway and port family cannot satisfy the Stage D provider proxy', () => {
    for (const [key, value] of Object.entries(HOST_GATEWAY_AMBIENT_ENV)) {
        assert.notEqual(value, '', `${key} fixture must be non-empty to be a real fallback`);
    }
    assert.throws(
        () => resolveStageDStableProxyEndpoint({ ...HOST_GATEWAY_AMBIENT_ENV }),
        error => error.code === PROXY_CONFIGURATION_MISSING,
    );
    // Both fallback families together still cannot name an endpoint.
    assert.throws(
        () => resolveStageDStableProxyEndpoint({ ...HOST_GATEWAY_AMBIENT_ENV, ...GENERIC_PROXY_AMBIENT_ENV }),
        error => error.code === PROXY_CONFIGURATION_MISSING,
    );
});

test('an explicitly configured endpoint is used exactly, not merged with any fallback', () => {
    const configured = 'http://stage-d-proxy.internal:3128';
    for (const ambient of [{}, GENERIC_PROXY_AMBIENT_ENV, HOST_GATEWAY_AMBIENT_ENV, { ...GENERIC_PROXY_AMBIENT_ENV, ...HOST_GATEWAY_AMBIENT_ENV }]) {
        const endpoint = resolveStageDStableProxyEndpoint({ ...ambient, [STAGE_D_PROXY_ENDPOINT_ENV_VAR]: configured });
        assert.equal(endpoint.host, 'stage-d-proxy.internal');
        assert.equal(endpoint.dial_host, 'stage-d-proxy.internal');
        assert.equal(endpoint.port, 3128);
        assert.equal(endpoint.scheme, 'http');
        assert.equal(buildStageDProxyAgentUrl(endpoint), configured);
        // None of the ambient values may leak into the governed endpoint.
        for (const leaked of ['host.docker.internal', '7897', 'socks5']) {
            assert.ok(!buildStageDProxyAgentUrl(endpoint).includes(leaked), `ambient value leaked: ${leaked}`);
        }
    }
});

test('an absent endpoint opens no socket at all, so there is no direct or fallback dial', async t => {
    // A live listener stands in for "some proxy that a fallback could have reached".
    // If resolution fell back to anything -- the harvesting pool, the workstation proxy,
    // a direct connection -- this listener would observe a connection.
    let connections = 0;
    const listener = net.createServer(socket => {
        connections += 1;
        socket.destroy();
    });
    await new Promise(resolve => listener.listen(0, '127.0.0.1', resolve));
    t.after(() => new Promise(resolve => listener.close(resolve)));
    const port = listener.address().port;
    assert.ok(port > 0, 'the witness listener must be bound before the assertion');

    const env = {
        ...GENERIC_PROXY_AMBIENT_ENV,
        ...HOST_GATEWAY_AMBIENT_ENV,
        [STAGE_D_PROXY_PREFLIGHT_TARGET_ENV_VAR]: `tcp://127.0.0.1:${port}`,
        [STAGE_D_PROXY_PREFLIGHT_SECRET_ENV_VAR]: testSecret(),
    };
    const runner = createStageDHttpConnectProxyPreflight({ env });
    await assert.rejects(runner.run(), error => error.code === PROXY_CONFIGURATION_MISSING);

    // Nothing was dialled, so the listener stayed silent.
    await new Promise(resolve => setTimeout(resolve, 50));
    assert.equal(connections, 0, 'a missing endpoint must not dial anything, including a fallback');
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

    // parseable.host keeps IPv6 bracketing intact for agent URL reconstruction, and
    // dial_host is the same address in the form a socket actually accepts.
    const ipv6Endpoint = resolveStageDStableProxyEndpoint({ [STAGE_D_PROXY_ENDPOINT_ENV_VAR]: `http://[::1]:3128` });
    assert.equal(ipv6Endpoint.host, '[::1]');
    assert.equal(ipv6Endpoint.dial_host, '::1');
    assert.equal(ipv6Endpoint.authority, '[::1]:3128');
    assert.equal(buildStageDProxyAgentUrl(ipv6Endpoint), 'http://[::1]:3128');

    const longIpv6 = resolveEndpoint({ port: 3128, host: '[2001:db8::1]' });
    assert.equal(longIpv6.host, '[2001:db8::1]');
    assert.equal(longIpv6.dial_host, '2001:db8::1');

    // Every host that is not an IPv6 literal is identical in both representations, so
    // normalization cannot strip a character from a DNS name or an IPv4 address.
    for (const host of ['127.0.0.1', 'localhost', 'proxy.internal']) {
        const endpoint = resolveEndpoint({ port: 3128, host });
        assert.equal(endpoint.dial_host, endpoint.host, `${host}: the dial host must equal the URI host`);
        assert.equal(endpoint.dial_host, host, `${host}: normalization must not alter a non-IPv6 host`);
    }
    // Case folding is the URL parser's, not this contract's: both representations agree.
    const mixedCase = resolveEndpoint({ port: 3128, host: 'PROXY.Internal' });
    assert.equal(mixedCase.dial_host, mixedCase.host);
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
    // `dial_host` is the socket-facing form of `host` -- the same address, unbracketed for
    // an IPv6 literal -- and for this endpoint it is bit-identical to `host`; it is a
    // network address, never a credential.
    assert.deepEqual(Object.keys(endpoint).sort(), ['authority', 'dial_host', 'has_credentials', 'host', 'port', 'redacted', 'scheme']);
    assert.equal(typeof endpoint.has_credentials, 'boolean');
    assert.equal(endpoint.authority, '127.0.0.1:3128');
    assert.equal(endpoint.dial_host, '127.0.0.1');

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

test('a missing, blank or malformed attestation secret fails closed before any socket', async t => {
    // §6: the secret is a required deployment input.  It is never generated, never
    // defaulted and never falls back to a test value, so its absence is a deterministic
    // local configuration failure -- and it is decided before the network is touched.
    const proxy = await startProxyStandIn(t, socket => socket.end('HTTP/1.1 200 Connection Established\r\n\r\n'));
    const target = await startProbeTarget(t);

    for (const env of [
        {},
        { [STAGE_D_PROXY_PREFLIGHT_SECRET_ENV_VAR]: '' },
        { [STAGE_D_PROXY_PREFLIGHT_SECRET_ENV_VAR]: '   ' },
    ]) {
        assert.throws(
            () => resolveStageDPreflightSecret(env),
            error => error.code === PREFLIGHT_ATTESTATION_SECRET_MISSING
                && error.message.includes(STAGE_D_PROXY_PREFLIGHT_SECRET_ENV_VAR),
        );
    }

    // A present but unusable value: not base64 at all, not canonical base64, padded
    // wrongly, or simply shorter than the floor.  Each is a provisioning mistake that
    // must surface as a refusal rather than as an intermittent attestation failure.
    const tooShort = Buffer.from('short', 'utf8').toString('base64');
    const floorBytes = Buffer.alloc(STAGE_D_PROXY_ATTESTATION_MIN_SECRET_BYTES - 1, 7).toString('base64');
    for (const [value, label] of [
        ['not base64 at all!!', 'non-base64'],
        [Buffer.from('x'.repeat(40), 'utf8').toString('base64').replace(/=+$/, ''), 'unpadded'],
        ['AAAA=', 'bad padding length'],
        [tooShort, 'too short'],
        [floorBytes, 'just under the entropy floor'],
    ]) {
        assert.throws(
            () => resolveStageDPreflightSecret({ [STAGE_D_PROXY_PREFLIGHT_SECRET_ENV_VAR]: value }),
            error => error.code === PREFLIGHT_ATTESTATION_SECRET_INVALID,
            `${label} must be rejected`,
        );
    }

    // Exactly at the floor is accepted: the contract is a minimum, not an equality.
    const atFloor = Buffer.alloc(STAGE_D_PROXY_ATTESTATION_MIN_SECRET_BYTES, 7).toString('base64');
    assert.equal(resolveStageDPreflightSecret({ [STAGE_D_PROXY_PREFLIGHT_SECRET_ENV_VAR]: atFloor }).configured, true);

    // And a preflight told to resolve its own secret with none configured refuses
    // without opening the proxy socket.
    const runner = createStageDHttpConnectProxyPreflight({
        endpoint: resolveEndpoint({ port: proxy.port }),
        target: testTarget(target.port, { proxyPort: proxy.port }),
        env: {},
    });
    await assert.rejects(runner.run(), error => error.code === PREFLIGHT_ATTESTATION_SECRET_MISSING);
    assert.equal(proxy.requestText(), '', 'no proxy socket may be opened when the secret is unconfigured');
});

test('the attestation secret never reaches an enumerable surface or an error message', async t => {
    const secretText = TEST_SECRET_TEXT;
    const secret = testSecret();
    const encoded = Buffer.from(secretText, 'utf8').toString('base64');

    // The resolved object carries no key material, no digest of it, and no shape hint:
    // not the bytes, not a hash, not a length, not a prefix.  The whole point of a
    // dedicated secret is defeated if its fingerprint travels with the evidence.
    assert.deepEqual(Object.keys(secret).sort(), ['algorithm', 'configured', 'encoding']);
    assert.deepEqual(JSON.parse(JSON.stringify(secret)), { configured: true, encoding: 'base64', algorithm: 'HMAC-SHA-256' });
    const serializedSecret = JSON.stringify({ ...secret });
    assert.equal(serializedSecret.includes(secretText), false);
    assert.equal(serializedSecret.includes(encoded), false);
    assert.equal(serializedSecret.includes(String(secretText.length)), false);

    // A passing preflight result is what actually lands in evidence, so it is the one
    // that matters most.
    const { proxy, target } = await startTunnellingProxy(t);
    const result = await preflight(proxy.port, { target: testTarget(target.port, { proxyPort: proxy.port }) });
    assert.equal(result.passed, true);
    const serializedResult = JSON.stringify(result);
    assert.equal(serializedResult.includes(secretText), false);
    assert.equal(serializedResult.includes(encoded), false);
    // The MAC itself must not be echoed into evidence either: it is a valid response for
    // a challenge that is still live, so publishing it hands over a replayable value.
    assert.equal(/[0-9a-f]{64}/.test(serializedResult), false);

    // A wrong-key failure is the other path that builds an error-ish message.  It must
    // not carry the configured secret either.
    const wrongKey = await startProbeTarget(t, { secret: testSecret(OTHER_SECRET_TEXT) });
    const { proxy: tunnelling } = await startTunnellingProxy(t, { target: wrongKey });
    const failed = await preflight(tunnelling.port, { target: testTarget(wrongKey.port, { proxyPort: tunnelling.port }) });
    assert.equal(failed.passed, false);
    assert.equal(JSON.stringify(failed).includes(secretText), false);
    assert.equal(JSON.stringify(failed).includes(encoded), false);
});

test('the MAC input is length-prefixed, so distinct field pairs cannot collide', () => {
    // A delimiter-joined protocol has an encoding ambiguity: ("ab","cd") and ("abc","d")
    // concatenate identically, so one valid response would validate for a different
    // challenge.  Length prefixes make the encoding injective, and this pins that.
    const message = buildStageDAttestationMessage({ runId: 'ab', challenge: 'cd' });
    const collision = buildStageDAttestationMessage({ runId: 'abc', challenge: 'd' });

    assert.equal(Buffer.isBuffer(message), true);
    assert.notEqual(message.toString('hex'), collision.toString('hex'));
    // The pair that collides under naive concatenation produces messages of the *same*
    // total length here: the defence is that the field boundaries are encoded, not that
    // the messages differ in size.  `'ab'+'cd'` and `'abc'+'d'` are both `'abcd'`.
    assert.equal(`${'ab'}${'cd'}`, `${'abc'}${'d'}`);
    assert.equal(message.length, collision.length);

    // The signed bytes are exactly: magic, NUL, u32be(len), run id, u32be(len), challenge.
    const magicLength = STAGE_D_PROXY_ATTESTATION_PROTOCOL.length;
    assert.equal(message.length, magicLength + 1 + 4 + 2 + 4 + 2);
    assert.equal(message.subarray(0, magicLength).toString('ascii'), STAGE_D_PROXY_ATTESTATION_PROTOCOL);
    assert.equal(message[magicLength], 0, 'the domain-separation byte must follow the version');
    assert.equal(message.readUInt32BE(magicLength + 1), 2);
    assert.equal(message.subarray(magicLength + 5, magicLength + 7).toString('ascii'), 'ab');
    assert.equal(message.readUInt32BE(magicLength + 7), 2);
    assert.equal(message.subarray(magicLength + 11).toString('ascii'), 'cd');

    // The same inputs always produce the same bytes: the encoding is deterministic, so
    // an independent target implementation can reproduce it exactly.
    assert.equal(
        buildStageDAttestationMessage({ runId: 'ab', challenge: 'cd' }).toString('hex'),
        message.toString('hex'),
    );
});

test('the reference target and the verifier agree on the protocol end to end', async t => {
    // The exported response builder is what a dev/CI target is expected to use, so the
    // two halves of the contract are pinned against each other here rather than being
    // restated independently and left to drift.
    const secret = testSecret();
    const runId = 'a'.repeat(STAGE_D_PROXY_RUN_ID_BYTES * 2);
    const challenge = 'b'.repeat(STAGE_D_PROXY_CHALLENGE_BYTES * 2);
    const response = buildStageDAttestationResponse({ secret, runId, challenge });

    assert.equal(response.endsWith('\n'), true);
    const parts = response.trim().split(' ');
    assert.equal(parts.length, 3);
    assert.equal(parts[0], STAGE_D_PROXY_ATTESTATION_PROTOCOL);
    assert.equal(parts[1], runId);
    assert.match(parts[2], /^[0-9a-f]{64}$/);

    // The response carries the MAC and nothing else -- in particular, not the secret.
    assert.equal(response.includes(TEST_SECRET_TEXT), false);

    // A different challenge yields a different MAC under the same key, and the same
    // challenge under a different key does too.  Neither is a function of the other.
    const otherChallenge = buildStageDAttestationResponse({ secret, runId, challenge: 'c'.repeat(64) });
    const otherKey = buildStageDAttestationResponse({ secret: testSecret(OTHER_SECRET_TEXT), runId, challenge });
    assert.notEqual(response, otherChallenge);
    assert.notEqual(response, otherKey);
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
    // An endpoint carrying every legacy key but no dial host is refused rather than dialed.
    // net.connect() substitutes localhost for an undefined host, so a hand-built endpoint
    // missing dial_host would silently become a connection to the local machine.
    assert.throws(
        () => createStageDHttpConnectProxyPreflight({
            endpoint: { scheme: 'http', host: '127.0.0.1', port: 3128, redacted: 'http://127.0.0.1:3128' },
        }),
        error => error.code === STAGE_D_PROXY_PREFLIGHT_CONFIGURATION_INVALID,
    );
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
