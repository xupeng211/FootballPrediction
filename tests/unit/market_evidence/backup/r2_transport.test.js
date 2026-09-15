'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');

const backup = require('../../../../src/infrastructure/market_evidence/backup');
const { installNetworkTripwire } = require('../../../helpers/network_tripwire');
const { ObjectAlreadyExistsError, SnapshotIntegrityError } = require('../../../../src/infrastructure/market_evidence/backup/transport');

// The whole file runs behind the tripwire.  Every test here drives the R2
// transport, which is the one component in the tree that *can* address a remote
// endpoint; substituting a stub SDK is what keeps the file offline, and the
// tripwire is what proves the substitution was complete.
const tripwire = installNetworkTripwire();
test.after(() => {
    assert.deepEqual(tripwire.attempts, [], 'no test in this file may attempt outbound network access');
    tripwire.restore();
});

const { createR2Transport } = backup.loadR2Transport();

const ENDPOINT = 'https://account.r2.cloudflarestorage.com';
const BUCKET = 'stage-d-backup-test';
const LONG_LIVED = Object.freeze({ accessKeyId: 'AKIASYNTHETICLONGTERM', secretAccessKey: 'synthetic-long-lived-secret' });
const TEMPORARY = Object.freeze({ accessKeyId: 'ASIASYNTETHICTEMPORARY', secretAccessKey: 'synthetic-temporary-secret', sessionToken: 'synthetic-session-token-value' });

class PreconditionFailed extends Error {
    constructor() {
        super('PreconditionFailed');
        this.name = 'PreconditionFailed';
        this.$metadata = { httpStatusCode: 412 };
    }
}

class StubNotFound extends Error {
    constructor() {
        super('NotFound');
        this.name = 'NotFound';
        this.$metadata = { httpStatusCode: 404 };
    }
}

class StubServerError extends Error {
    constructor() {
        super('InternalError');
        this.name = 'InternalError';
        this.$metadata = { httpStatusCode: 500 };
    }
}

// An in-memory object store behind the SDK surface the transport validates.  It
// models the two things this transport's correctness rests on: `If-None-Match:
// '*'` failing with 412 when the key exists, and `ListObjectsV2` truncating at
// `pageSize` with a continuation token.  1000 is the provider's own page limit,
// and it is the default here so a test that wants a second page has to ask for
// the real one.
function createStubR2({ pageSize = 1000, failWith = null } = {}) {
    const objects = new Map();
    const calls = [];
    const clientOptions = [];

    const command = operation => class StubCommand {
        constructor(input) {
            this.operation = operation;
            this.input = input;
        }
    };

    class StubS3Client {
        constructor(options) {
            clientOptions.push(options);
        }

        async send(request) {
            const { operation, input } = request;
            calls.push(Object.freeze({ operation, input }));
            if (failWith !== null) throw failWith;
            switch (operation) {
                case 'PutObject': {
                    if (input.IfNoneMatch === '*' && objects.has(input.Key)) throw new PreconditionFailed();
                    objects.set(input.Key, Buffer.from(input.Body));
                    return { ETag: `"stub-etag-${input.Key.length}"` };
                }
                case 'GetObject': {
                    if (!objects.has(input.Key)) throw new StubNotFound();
                    const body = objects.get(input.Key);
                    return { Body: { transformToByteArray: async () => new Uint8Array(body) }, ContentLength: body.length };
                }
                case 'HeadObject': {
                    if (!objects.has(input.Key)) throw new StubNotFound();
                    const body = objects.get(input.Key);
                    return { ContentLength: body.length, ETag: `"stub-etag-${input.Key.length}"` };
                }
                case 'ListObjects': {
                    const scope = input.Prefix || '';
                    const matching = [...objects.keys()].filter(key => key.startsWith(scope)).sort();
                    const start = input.ContinuationToken === undefined ? 0 : Number(input.ContinuationToken);
                    const page = matching.slice(start, start + pageSize);
                    const next = start + page.length;
                    return {
                        Contents: page.map(key => ({ Key: key, Size: objects.get(key).length })),
                        IsTruncated: next < matching.length,
                        ...(next < matching.length ? { NextContinuationToken: String(next) } : {}),
                    };
                }
                default:
                    throw new Error(`the stub SDK received an operation it does not model: ${operation}`);
            }
        }
    }

    return Object.freeze({
        sdk: {
            S3Client: StubS3Client,
            PutObjectCommand: command('PutObject'),
            GetObjectCommand: command('GetObject'),
            HeadObjectCommand: command('HeadObject'),
            ListObjectsV2Command: command('ListObjects'),
        },
        objects,
        calls,
        clientOptions,
    });
}

function transportFor(stub, { prefix = '', credentials = LONG_LIVED } = {}) {
    return createR2Transport({
        endpoint: ENDPOINT,
        bucket: BUCKET,
        region: 'auto',
        prefix,
        credentials,
        sdk: stub.sdk,
    });
}

// The pinned SDK mutates the credential object it is handed.
//
// `@aws-sdk/core`'s `resolveAwsSdkSigV4Config` wraps the caller's credentials in
// an async provider and, on first resolution, annotates *that same object* in
// place with `$source` and a `CREDENTIALS_CODE` feature flag.  There is no copy
// on that path, and the mutation is deferred to provider resolution -- which
// happens while signing, not at construction -- so a frozen object fails at the
// first signed request with:
//
//     TypeError: Cannot set properties of undefined (setting 'CREDENTIALS_CODE')
//
// and a probe that only constructs the client reports success for both shapes.
// That is how the freeze reached main in the first place, and it is why these
// tests drive the real client: a stub the transport itself supplies cannot
// exhibit a behaviour of the library it stands in for.
//
// Nothing is sent.  Resolving a static credential performs no I/O, and the
// tripwire installed for this file proves no socket was opened.
const realSdk = require('@aws-sdk/client-s3');

// The transport builds its own client and never exposes it, so the client is
// captured by subclassing the one member of the SDK surface it constructs.
// Everything else about the construction path is the transport's own.
function transportOnRealSdk(credentials) {
    const built = [];
    class CapturingS3Client extends realSdk.S3Client {
        constructor(config) {
            super(config);
            built.push(this);
        }
    }
    const transport = createR2Transport({
        endpoint: ENDPOINT,
        bucket: BUCKET,
        region: 'auto',
        credentials,
        sdk: {
            S3Client: CapturingS3Client,
            PutObjectCommand: realSdk.PutObjectCommand,
            GetObjectCommand: realSdk.GetObjectCommand,
            HeadObjectCommand: realSdk.HeadObjectCommand,
            ListObjectsV2Command: realSdk.ListObjectsV2Command,
        },
    });
    return { transport, built };
}

// The step that failed.  This is what signing does to the client's credential
// provider before it can compute a signature.
async function resolveCredentialProvider(client) {
    const provider = client.config && client.config.credentials;
    assert.equal(typeof provider, 'function', 'the client the transport built must expose a resolvable credential provider');
    return provider({});
}

function seed(stub, entries) {
    for (const [key, value] of Object.entries(entries)) stub.objects.set(key, Buffer.from(value));
}

test('describe() reports the target and the credential class, and never a credential value', () => {
    const stub = createStubR2();
    const described = transportFor(stub, { prefix: 'snapshots', credentials: TEMPORARY }).describe();

    assert.equal(described.kind, 'r2-s3');
    assert.equal(described.endpoint, ENDPOINT);
    assert.equal(described.bucket, BUCKET);
    assert.equal(described.region, 'auto');
    assert.equal(described.prefix, 'snapshots');
    assert.equal(described.create_only, true);
    assert.equal(described.delete_exposed, false);
    assert.equal(described.credentials_injected, true);
    assert.equal(described.credential_source, 'INJECTED_EXPLICIT');
    assert.equal(described.environment_fallback, false);
    // A temporary credential is reported as a class, not as a value.  The class
    // belongs in an evidence record; the token does not.
    assert.equal(described.session_token_present, true);
    assert.equal(transportFor(createStubR2(), { credentials: LONG_LIVED }).describe().session_token_present, false);

    const serialized = JSON.stringify(described);
    for (const secret of Object.values(TEMPORARY)) {
        assert.equal(serialized.includes(secret), false, 'describe() must be safe to serialize');
    }
});

test('the credentials reach the SDK client explicitly, with no discovery left to run', () => {
    const stub = createStubR2();
    transportFor(stub, { credentials: TEMPORARY });

    assert.equal(stub.clientOptions.length, 1, 'the transport builds exactly one client');
    const [options] = stub.clientOptions;
    assert.deepEqual(options.credentials, { ...TEMPORARY });
    assert.equal(options.endpoint, ENDPOINT);
    assert.equal(options.region, 'auto');
    assert.equal(options.forcePathStyle, true);
    // Nothing that could resolve a credential from somewhere else is passed.
    // The SDK's provider chain is only consulted when `credentials` is absent,
    // so its absence here is the entire guarantee.
    assert.deepEqual(Object.keys(options).sort(), ['credentials', 'endpoint', 'forcePathStyle', 'region']);
});

test('a temporary credential is not swallowed: the session token reaches the client', () => {
    const stub = createStubR2();
    transportFor(stub, { credentials: TEMPORARY });
    assert.equal(stub.clientOptions[0].credentials.sessionToken, TEMPORARY.sessionToken);
});

test('a create-only write sends If-None-Match: * against the physical key', async () => {
    const stub = createStubR2();
    const transport = transportFor(stub, { prefix: 'snapshots' });
    await transport.putObjectCreateOnly({ key: 'snap-1/MANIFEST.json', bytes: Buffer.from('body') });

    const put = stub.calls.find(call => call.operation === 'PutObject');
    assert.equal(put.input.IfNoneMatch, '*', 'the condition is what makes the write create-only');
    assert.equal(put.input.Key, 'snapshots/snap-1/MANIFEST.json');
    assert.equal(put.input.Bucket, BUCKET);
    assert.equal(stub.objects.has('snapshots/snap-1/MANIFEST.json'), true);
});

test('the second create of the same key is refused as already existing, not retried', async () => {
    const stub = createStubR2();
    const transport = transportFor(stub, { prefix: 'snapshots' });
    await transport.putObjectCreateOnly({ key: 'snap-1/MANIFEST.json', bytes: Buffer.from('first') });

    await assert.rejects(
        () => transport.putObjectCreateOnly({ key: 'snap-1/MANIFEST.json', bytes: Buffer.from('second') }),
        error => error instanceof ObjectAlreadyExistsError && error.code === 'OBJECT_ALREADY_EXISTS',
    );
    assert.equal(stub.objects.get('snapshots/snap-1/MANIFEST.json').toString('utf8'), 'first', 'a refused create must leave the original byte-for-byte');
});

test('a conditional-request conflict is also reported as already existing', async () => {
    const stub = createStubR2({ failWith: Object.assign(new Error('ConditionalRequestConflict'), { name: 'ConditionalRequestConflict', $metadata: { httpStatusCode: 409 } }) });
    const transport = transportFor(stub);
    await assert.rejects(
        () => transport.putObjectCreateOnly({ key: 'snap-1/MANIFEST.json', bytes: Buffer.from('x') }),
        error => error instanceof ObjectAlreadyExistsError,
    );
});

test('a server failure is never reinterpreted as an existing key', async () => {
    // The distinction is load-bearing: "the key exists" and "the write broke"
    // call for different responses, and reporting a lost generation as a benign
    // collision would leave the operator believing their data is stored.
    const stub = createStubR2({ failWith: new StubServerError() });
    const transport = transportFor(stub);
    for (const attempt of [
        () => transport.putObjectCreateOnly({ key: 'snap-1/MANIFEST.json', bytes: Buffer.from('x') }),
        () => transport.getObject({ key: 'snap-1/MANIFEST.json' }),
        () => transport.headObject({ key: 'snap-1/MANIFEST.json' }),
        () => transport.listObjects({ prefix: 'snap-1/' }),
    ]) {
        await assert.rejects(attempt, error => error instanceof SnapshotIntegrityError && !(error instanceof ObjectAlreadyExistsError) && /InternalError status=500/.test(error.message));
    }
});

test('a missing object reads back as absent rather than as a failure', async () => {
    const stub = createStubR2();
    const transport = transportFor(stub, { prefix: 'snapshots' });
    assert.equal(await transport.getObject({ key: 'snap-1/COMPLETE' }), null);
    assert.equal(await transport.headObject({ key: 'snap-1/COMPLETE' }), null);
});

test('an object that is present reads back with its bytes, size and etag', async () => {
    const stub = createStubR2();
    seed(stub, { 'snapshots/snap-1/payload/state.json': 'payload-bytes' });
    const transport = transportFor(stub, { prefix: 'snapshots' });

    assert.equal((await transport.getObject({ key: 'snap-1/payload/state.json' })).toString('utf8'), 'payload-bytes');
    const head = await transport.headObject({ key: 'snap-1/payload/state.json' });
    assert.equal(head.size, 'payload-bytes'.length);
    assert.equal(head.key, 'snapshots/snap-1/payload/state.json');
});

test('listing past 1000 objects follows the continuation token to the end', async () => {
    const stub = createStubR2();
    const generated = {};
    for (let index = 0; index < 1500; index += 1) {
        generated[`snapshots/snap-1/payload/object-${String(index).padStart(4, '0')}.json`] = `object-${index}`;
    }
    seed(stub, generated);

    const transport = transportFor(stub, { prefix: 'snapshots' });
    const listed = await transport.listObjects({ prefix: 'snap-1/' });

    assert.equal(listed.length, 1500, 'every object past the first page must be returned');
    assert.equal(listed[0].key, 'snap-1/payload/object-0000.json');
    assert.equal(listed[1499].key, 'snap-1/payload/object-1499.json');
    assert.equal(new Set(listed.map(entry => entry.key)).size, 1500, 'no object is returned twice');
    assert.equal(listed[0].size, 'object-0'.length);
    assert.equal(listed[1234].size, 'object-1234'.length, 'a size read past the page boundary belongs to the right object');

    const listCalls = stub.calls.filter(call => call.operation === 'ListObjects');
    assert.equal(listCalls.length, 2, 'the page boundary is exactly what the provider reports');
    assert.equal(listCalls[0].input.ContinuationToken, undefined);
    assert.equal(listCalls[1].input.ContinuationToken, '1000');
    assert.equal(listCalls[1].input.Prefix, 'snapshots/snap-1/', 'every page is asked for in physical keys');
});

test('the configured prefix is an addressing detail: it never appears in a listed key', async () => {
    const stub = createStubR2();
    seed(stub, {
        'snapshots/snap-1/MANIFEST.json': 'a',
        'snapshots/snap-1/payload/state.json': 'bb',
        // The same bucket, a different namespace.  It is not evidence about this
        // generation, and a transport that reported it would make the verifier's
        // exact-set comparison fail for a generation that is perfectly intact.
        'other-tenant/snap-1/MANIFEST.json': 'ccc',
    });
    const transport = transportFor(stub, { prefix: 'snapshots' });

    const listed = await transport.listObjects({ prefix: 'snap-1/' });
    assert.deepEqual(listed.map(entry => entry.key), ['snap-1/MANIFEST.json', 'snap-1/payload/state.json']);

    // Reading and heading are scoped the same way: a key that exists in the
    // bucket but outside the configured prefix is invisible here, because the
    // transport never addresses it without the prefix in front.
    assert.equal((await transport.getObject({ key: 'snap-1/MANIFEST.json' })).toString('utf8'), 'a');
    assert.equal(await transport.getObject({ key: 'MANIFEST.json' }), null, 'an unprefixed key must not resolve to another namespace\'s object');
    assert.equal(await transport.headObject({ key: 'MANIFEST.json' }), null);
});

test('a provider that returns a key outside the requested scope has it discarded', async () => {
    // The defensive branch is only reachable through a provider that answers a
    // scoped request with unscoped data -- which is what a misconfigured bucket,
    // a proxy or a key-collision would look like.  The stub therefore answers
    // the way the transport does not expect, and the extra key must not become
    // evidence about the generation.
    const command = operation => class StubCommand {
        constructor(input) {
            this.operation = operation;
            this.input = input;
        }
    };
    const sdk = {
        S3Client: class {
            async send(request) {
                if (request.operation !== 'ListObjects') throw new Error('this stub only answers list requests');
                return {
                    Contents: [
                        { Key: 'snapshots/snap-1/MANIFEST.json', Size: 1 },
                        { Key: 'elsewhere/snap-1/MANIFEST.json', Size: 2 },
                        { Key: 'snapshots-sibling/snap-1/MANIFEST.json', Size: 3 },
                    ],
                    IsTruncated: false,
                };
            }
        },
        PutObjectCommand: command('PutObject'),
        GetObjectCommand: command('GetObject'),
        HeadObjectCommand: command('HeadObject'),
        ListObjectsV2Command: command('ListObjects'),
    };
    const transport = createR2Transport({ endpoint: ENDPOINT, bucket: BUCKET, region: 'auto', prefix: 'snapshots', credentials: LONG_LIVED, sdk });

    assert.deepEqual(
        (await transport.listObjects({ prefix: 'snap-1/' })).map(entry => entry.key),
        ['snap-1/MANIFEST.json'],
        'a key outside the configured scope is not an object of this generation',
    );
});

test('the transport exposes no deletion verb, and cannot acquire one from the SDK surface', async () => {
    const stub = createStubR2();
    // An SDK that offers deletion is the interesting case: the seam validates a
    // surface, so a stub carrying extra members is accepted -- and the transport
    // must still be unable to call one, because it destructures exactly the four
    // classes it needs and never captures a reference to anything else.
    const deleteCalls = [];
    const sdkWithDelete = {
        ...stub.sdk,
        DeleteObjectCommand: class {
            constructor(input) {
                this.input = input;
                deleteCalls.push(input);
            }
        },
        DeleteObjectsCommand: class {
            constructor(input) {
                this.input = input;
                deleteCalls.push(input);
            }
        },
    };
    const transport = createR2Transport({
        endpoint: ENDPOINT,
        bucket: BUCKET,
        region: 'auto',
        credentials: LONG_LIVED,
        sdk: sdkWithDelete,
    });

    await transport.putObjectCreateOnly({ key: 'snap-1/MANIFEST.json', bytes: Buffer.from('x') });
    await transport.getObject({ key: 'snap-1/MANIFEST.json' });
    await transport.headObject({ key: 'snap-1/MANIFEST.json' });
    await transport.listObjects({ prefix: 'snap-1/' });

    assert.deepEqual(deleteCalls, [], 'no delete command may be constructed, let alone sent');
    assert.deepEqual(stub.calls.map(call => call.operation), ['PutObject', 'GetObject', 'HeadObject', 'ListObjects']);
    for (const verb of ['deleteObject', 'deleteObjects', 'deletePrefix', 'deleteGeneration', 'emptyBucket', 'removeObject', 'overwriteAcceptedSnapshot', 'putObjectOverwrite', 'createBucket', 'deleteBucket', 'configureBucket', 'putBucketLock', 'putBucketLifecycle', 'putBucketPolicy']) {
        assert.equal(transport[verb], undefined, `the transport must not expose ${verb}`);
    }
    assert.equal(backup.assertTransportContract(transport), transport);
});

test('a frozen credential still signs: the client the transport builds resolves its provider', async () => {
    // The credential the caller injects is frozen by the caller here, and the
    // transport freezes its own record of it independently.  Both are the shape
    // a loader that reads a credential file and seals it would produce.
    const injected = Object.freeze({ accessKeyId: 'AKIASYNTHETICFROZEN', secretAccessKey: 'synthetic-frozen-secret' });
    const { transport, built } = transportOnRealSdk(injected);
    assert.equal(built.length, 1, 'the transport must build exactly one client');

    const resolved = await resolveCredentialProvider(built[0]);

    assert.equal(resolved.accessKeyId, injected.accessKeyId);
    assert.equal(resolved.secretAccessKey, injected.secretAccessKey);
    // The SDK annotated the object it was given, which is the mutation that a
    // frozen object cannot accept.  Reaching this line at all is the repair.
    assert.deepEqual(Object.keys(resolved.$source || {}), ['CREDENTIALS_CODE']);
    // And it annotated its own copy: the caller's object is a different object
    // and is untouched, so a mutation performed by the SDK cannot reach the
    // credential the caller handed over.
    assert.notEqual(resolved, injected);
    assert.equal(injected.$source, undefined);
    assert.equal(Object.isFrozen(injected), true);
    assert.equal(transport.describe().credential_source, 'INJECTED_EXPLICIT');
    assert.equal(transport.describe().environment_fallback, false);
});

test('a frozen temporary credential keeps its session token through the same path', async () => {
    const injected = Object.freeze({ accessKeyId: 'ASIASYNTHETICFROZEN', secretAccessKey: 'synthetic-frozen-secret', sessionToken: 'synthetic-session-token-value' });
    const { transport, built } = transportOnRealSdk(injected);
    const resolved = await resolveCredentialProvider(built[0]);

    assert.equal(resolved.sessionToken, injected.sessionToken, 'session-token handling is unchanged by the copy');
    assert.deepEqual(Object.keys(resolved.$source || {}), ['CREDENTIALS_CODE']);
    assert.notEqual(resolved, injected);
    assert.equal(injected.sessionToken, 'synthetic-session-token-value');
    assert.equal(transport.describe().session_token_present, true);
    assert.equal(JSON.stringify(transport.describe()).includes(injected.sessionToken), false, 'the token is a class in the report, never a value');
});

test('two transports never share the credential object the SDK sees', async () => {
    const first = transportOnRealSdk(Object.freeze({ ...LONG_LIVED }));
    const second = transportOnRealSdk(Object.freeze({ ...LONG_LIVED }));
    const resolvedFirst = await resolveCredentialProvider(first.built[0]);
    const resolvedSecond = await resolveCredentialProvider(second.built[0]);

    assert.notEqual(resolvedFirst, resolvedSecond, 'a shared object would let one transport observe the other\'s SDK state');
    assert.deepEqual(Object.keys(resolvedFirst).sort(), ['$source', 'accessKeyId', 'secretAccessKey']);
});

test('the pinned SDK mutates the credential object it is handed, which is what the copy is for', async () => {
    // This asserts a behaviour of the pinned dependency, not of this repository:
    // it is the premise the repair is written against, and it is here so that a
    // future SDK that stops mutating is a signal to revisit the copy rather than
    // a silent divergence.  The mutable arm is the control: without it, the
    // refusal in the frozen arm would be consistent with any number of causes.
    const mutable = { ...LONG_LIVED };
    const mutableClient = new realSdk.S3Client({ endpoint: ENDPOINT, region: 'auto', forcePathStyle: true, credentials: mutable });
    const annotated = await resolveCredentialProvider(mutableClient);
    assert.equal(annotated, mutable, 'the SDK annotates the object it was given rather than a copy of it');
    assert.deepEqual(Object.keys(mutable.$source || {}), ['CREDENTIALS_CODE']);

    const frozenClient = new realSdk.S3Client({ endpoint: ENDPOINT, region: 'auto', forcePathStyle: true, credentials: Object.freeze({ ...LONG_LIVED }) });
    await assert.rejects(
        () => resolveCredentialProvider(frozenClient),
        error => error instanceof TypeError && /CREDENTIALS_CODE/.test(error.message),
    );
});
