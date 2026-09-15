'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const { installNetworkTripwire } = require('../../../helpers/network_tripwire');
const {
    loadLiveTargetIdentity,
    parseTargetIdentity,
    LiveTargetIdentityError,
    LIVE_TARGET_IDENTITY_SCHEMA_VERSION,
} = require('../../../../src/infrastructure/market_evidence/backup/liveTargetIdentity');

// Non-secret or not, a target identity is what aims a backup at a provider, so
// the loader that reads it is sealed like everything else on this path.
const tripwire = installNetworkTripwire();
test.after(() => {
    assert.deepEqual(tripwire.attempts, [], 'no test in this file may attempt outbound network access');
    tripwire.restore();
});

const REPOSITORY_ROOT = path.resolve(__dirname, '../../../../');

function validIdentity(overrides = {}) {
    return {
        schema_version: LIVE_TARGET_IDENTITY_SCHEMA_VERSION,
        provider: 'cloudflare-r2',
        endpoint: 'https://0123456789abcdef0123456789abcdef.r2.cloudflarestorage.com',
        bucket: 'footballprediction-stage-d-backup-prod',
        region: 'auto',
        prefix: 'footballprediction/stage-d/transaction-v1/snapshots',
        environment: 'production',
        project: 'footballprediction',
        purpose: 'stage-d-transaction-backup',
        ...overrides,
    };
}

function temporary(t, prefix) {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), prefix));
    t.after(() => fs.rmSync(dir, { recursive: true, force: true }));
    return dir;
}

function writeFile(t, contents, { name = 'target-identity.json', mode = 0o600 } = {}) {
    const file = path.join(temporary(t, 'stage-d-identity-'), name);
    fs.writeFileSync(file, typeof contents === 'string' ? contents : JSON.stringify(contents, null, 2), { mode });
    fs.chmodSync(file, mode);
    return file;
}

// Every rejection in this file goes through one shape: an identity file is
// written, loading it is expected to fail, and the failure must not be an
// identity that slipped through.
function refuses(t, contents, matcher) {
    const file = writeFile(t, contents);
    assert.throws(() => loadLiveTargetIdentity({ targetIdentityFile: file }), error => {
        assert.equal(error instanceof LiveTargetIdentityError, true, `expected a LiveTargetIdentityError, got ${error.name}: ${error.message}`);
        assert.equal(error.code, 'LIVE_TARGET_IDENTITY_INVALID');
        return matcher.test(error.message);
    }, `${matcher} must be reported`);
}

test('a well-formed identity loads, is frozen, and carries a stable non-secret fingerprint', t => {
    const identity = loadLiveTargetIdentity({ targetIdentityFile: writeFile(t, validIdentity()) });

    assert.equal(identity.schema_version, LIVE_TARGET_IDENTITY_SCHEMA_VERSION);
    assert.equal(identity.provider, 'cloudflare-r2');
    assert.equal(identity.bucket, 'footballprediction-stage-d-backup-prod');
    assert.equal(identity.region, 'auto');
    assert.equal(identity.prefix, 'footballprediction/stage-d/transaction-v1/snapshots');
    assert.equal(identity.environment, 'production');
    assert.equal(Object.isFrozen(identity), true);
    assert.match(identity.target_fingerprint, /^[a-f0-9]{16}$/);

    // Stable for the same target, and different for a different one.  The
    // fingerprint exists so evidence can name which target a run addressed
    // without republishing the account-bearing endpoint.
    assert.equal(loadLiveTargetIdentity({ targetIdentityFile: writeFile(t, validIdentity()) }).target_fingerprint, identity.target_fingerprint);
    assert.notEqual(loadLiveTargetIdentity({ targetIdentityFile: writeFile(t, validIdentity({ bucket: 'footballprediction-stage-d-backup-dr' })) }).target_fingerprint, identity.target_fingerprint);
});

test('the file path is required explicitly and has no default', () => {
    for (const argument of [undefined, null, '', '   ', 42, {}]) {
        assert.throws(() => loadLiveTargetIdentity({ targetIdentityFile: argument }), LiveTargetIdentityError);
    }
    assert.throws(() => loadLiveTargetIdentity(), LiveTargetIdentityError);
    assert.throws(() => loadLiveTargetIdentity({}), error => error instanceof LiveTargetIdentityError && /explicitly/.test(error.message));
});

test('a file that does not exist is refused rather than defaulted', t => {
    const dir = temporary(t, 'stage-d-identity-missing-');
    assert.throws(() => loadLiveTargetIdentity({ targetIdentityFile: path.join(dir, 'absent.json') }), LiveTargetIdentityError);
});

test('an unknown field is refused, not ignored', t => {
    refuses(t, validIdentity({ endpont: 'https://typo.invalid' }), /does not define.*endpont/s);
});

test('a field name that is itself secret-shaped is not printed', t => {
    // The name is the one part of an unknown field this loader would normally
    // report, so a secret pasted as a JSON key must not become a diagnostic.
    const file = writeFile(t, validIdentity({ AKIAIOSFODNN7EXAMPLE: 'x' }));
    assert.throws(() => loadLiveTargetIdentity({ targetIdentityFile: file }), error => {
        assert.match(error.message, /<unprintable field name>/);
        assert.equal(error.message.includes('AKIAIOSFODNN7EXAMPLE'), false);
        return true;
    });
});

test('a missing required field is named', t => {
    const identity = validIdentity();
    delete identity.bucket;
    refuses(t, identity, /missing required fields: bucket/);
});

test('the schema version is pinned', t => {
    refuses(t, validIdentity({ schema_version: 'stage-d-live-target-identity/v2' }), /schema_version/);
});

test('the provider and the region are closed enums', t => {
    // The enums record which target classes this code path has been adjudicated
    // for, so the guarantee under test is that an unrecognised value is refused
    // -- not which particular values happen to be members.
    refuses(t, validIdentity({ provider: 'backblaze-b2' }), /provider must be one of: cloudflare-r2, aws-s3/);
    refuses(t, validIdentity({ provider: 'wasabi' }), /provider must be one of: cloudflare-r2, aws-s3/);
    refuses(t, validIdentity({ provider: 'r2' }), /provider must be one of: cloudflare-r2, aws-s3/);
    refuses(t, validIdentity({ region: 'us-east-1' }), /region must be one of: auto for provider cloudflare-r2/);
});

test('a region is validated against the provider it was named with, not against a union', t => {
    // `auto` is a valid region and `aws-s3` is a valid provider, but the pair
    // names a target that cannot resolve, because region vocabularies do not
    // overlap between providers.  A flat union would admit this, and the
    // failure would then surface as an endpoint or signature error somewhere
    // less legible than a refusal to address a target that was never
    // adjudicated.
    refuses(t, validIdentity({ provider: 'aws-s3', region: 'auto' }), /region must be one of: ap-southeast-1 for provider aws-s3/);
    refuses(t, validIdentity({ provider: 'aws-s3', region: 'eu-west-1' }), /region must be one of: ap-southeast-1 for provider aws-s3/);
});

test('an endpoint is validated against the provider it was named with', t => {
    // The regression this pins: closing the provider enum closed the set of
    // provider NAMES but not the set of hosts a request can reach, because the
    // endpoint was free-form.  A target declaring `aws-s3` while naming an R2
    // endpoint loaded successfully, and the transport would then have signed
    // requests with an AWS region and sent them to a host the enum says is not
    // admitted.  A closed provider name that does not bind the destination is a
    // weaker guarantee than it appears.
    refuses(
        t,
        validIdentity({
            provider: 'aws-s3',
            region: 'ap-southeast-1',
            endpoint: 'https://0123456789abcdef0123456789abcdef.r2.cloudflarestorage.com',
        }),
        /endpoint must be https:\/\/s3\.ap-southeast-1\.amazonaws\.com for provider aws-s3/,
    );
    // Same provider, wrong region: an S3 endpoint for a region the target did
    // not declare would sign for one region and address another.
    refuses(
        t,
        validIdentity({ provider: 'aws-s3', region: 'ap-southeast-1', endpoint: 'https://s3.eu-west-1.amazonaws.com' }),
        /endpoint must be https:\/\/s3\.ap-southeast-1\.amazonaws\.com for provider aws-s3/,
    );
    // A host that merely resembles the expected one is not the expected one.  A
    // suffix match would admit any host ending in the provider's domain, which
    // is how a closed enum quietly stops being closed.
    refuses(
        t,
        validIdentity({ provider: 'aws-s3', region: 'ap-southeast-1', endpoint: 'https://s3.ap-southeast-1.amazonaws.com.attacker.example' }),
        /endpoint must be https:\/\/s3\.ap-southeast-1\.amazonaws\.com for provider aws-s3/,
    );
    // The reverse direction, so the binding is not one-way.
    refuses(
        t,
        validIdentity({ endpoint: 'https://s3.ap-southeast-1.amazonaws.com' }),
        /endpoint must be an endpoint belonging to provider cloudflare-r2/,
    );
});

test('an identity naming the second admitted provider loads', t => {
    const identity = loadLiveTargetIdentity({
        targetIdentityFile: writeFile(t, validIdentity({
            provider: 'aws-s3',
            endpoint: 'https://s3.ap-southeast-1.amazonaws.com',
            region: 'ap-southeast-1',
        })),
    });
    assert.equal(identity.provider, 'aws-s3');
    assert.equal(identity.region, 'ap-southeast-1');
    assert.equal(identity.endpoint, 'https://s3.ap-southeast-1.amazonaws.com');
    assert.equal(Object.isFrozen(identity), true);
});

test('the endpoint must be an unambiguous https origin', t => {
    refuses(t, validIdentity({ endpoint: 'http://account.r2.cloudflarestorage.com' }), /must use https/);
    refuses(t, validIdentity({ endpoint: 'https://user:pass@account.r2.cloudflarestorage.com' }), /must not carry userinfo/);
    refuses(t, validIdentity({ endpoint: 'https://account.r2.cloudflarestorage.com/?token=abc' }), /must not carry a query or a fragment/);
    refuses(t, validIdentity({ endpoint: 'https://account.r2.cloudflarestorage.com/#frag' }), /must not carry a query or a fragment/);
    refuses(t, validIdentity({ endpoint: 'https://account.r2.cloudflarestorage.com/bucket' }), /must not carry a path/);
    refuses(t, validIdentity({ endpoint: 'https://localhost' }), /fully qualified host/);
    refuses(t, validIdentity({ endpoint: 'not-a-url' }), /absolute URL/);
    // The normalized origin is what reaches the transport, so a trailing slash
    // cannot make two spellings of one target look like two targets.
    const normalized = loadLiveTargetIdentity({ targetIdentityFile: writeFile(t, validIdentity({ endpoint: 'https://account.r2.cloudflarestorage.com/' })) });
    assert.equal(normalized.endpoint, 'https://account.r2.cloudflarestorage.com');
});

test('the bucket must satisfy the provider name rules', t => {
    refuses(t, validIdentity({ bucket: 'Uppercase-Bucket' }), /lowercase letters/);
    refuses(t, validIdentity({ bucket: 'ab' }), /3-63 characters/);
    refuses(t, validIdentity({ bucket: '-leading-hyphen' }), /beginning and ending alphanumeric/);
    refuses(t, validIdentity({ bucket: 'trailing-hyphen-' }), /beginning and ending alphanumeric/);
    refuses(t, validIdentity({ bucket: 'under_score' }), /lowercase letters/);
    refuses(t, validIdentity({ bucket: `${'a'.repeat(64)}` }), /3-63 characters/);
});

test('the prefix must be a well-formed object-key path', t => {
    refuses(t, validIdentity({ prefix: '/leading-slash' }), /prefix must be a relative object-key path/);
    refuses(t, validIdentity({ prefix: 'trailing/slash/' }), /prefix must be a relative object-key path/);
    refuses(t, validIdentity({ prefix: 'a//b' }), /prefix must be a relative object-key path/);
    refuses(t, validIdentity({ prefix: 'a/../b' }), /prefix must be a relative object-key path/);
    refuses(t, validIdentity({ prefix: 'back\\slash' }), /prefix must be a relative object-key path/);
    // Every key segment must begin alphanumeric, which the probe namespace in
    // the design already accounts for: `preflight-probe/…`, not `_probe/…`.
    refuses(t, validIdentity({ prefix: '_probe/snapshots' }), /prefix must be a relative object-key path/);
    refuses(t, validIdentity({ prefix: '' }), /must be a non-empty string/);
});

test('the labels are bounded and lowercase', t => {
    refuses(t, validIdentity({ environment: 'Production' }), /lowercase alphanumeric/);
    refuses(t, validIdentity({ project: '1st-project' }), /lowercase alphanumeric/);
    refuses(t, validIdentity({ purpose: `${'p'.repeat(33)}` }), /at most 32 characters/);
    refuses(t, validIdentity({ purpose: 'stage d backup' }), /lowercase alphanumeric/);
});

test('a value shaped like a secret is refused wherever it sits', t => {
    // The schema has no secret field, so the remaining risk is a secret typed
    // into a field that does have one.  That is checked for rather than assumed
    // away, because a target identity file is recorded in evidence.
    //
    // Only a field whose own rule permits a long opaque string can carry one
    // this far: the labels are at most 32 characters and the endpoint has to be
    // a URL, so the two below are the fields that can actually reach the check.
    refuses(t, validIdentity({ prefix: `snapshots/${'a'.repeat(64)}` }), /shaped like a secret/);
    refuses(t, validIdentity({ bucket: 'a1b2c3d4e5f60718293a4b5c6d7e8f9012345678' }), /shaped like a secret/);
});

test('a value with surrounding whitespace or a control character is refused', t => {
    refuses(t, validIdentity({ purpose: ' stage-d-backup' }), /surrounding whitespace/);
    refuses(t, validIdentity({ purpose: 'stage\td-backup' }), /surrounding whitespace|control characters/);
    refuses(t, validIdentity({ purpose: 'stage\nd-backup' }), /control characters/);
});

test('a symbolic link, a directory and an oversized file are all refused', t => {
    const dir = temporary(t, 'stage-d-identity-shape-');
    const real = path.join(dir, 'real.json');
    fs.writeFileSync(real, JSON.stringify(validIdentity()), { mode: 0o600 });
    const link = path.join(dir, 'link.json');
    fs.symlinkSync(real, link);
    assert.throws(() => loadLiveTargetIdentity({ targetIdentityFile: link }), error => error instanceof LiveTargetIdentityError && /regular file that is not a symbolic link/.test(error.message));

    assert.throws(() => loadLiveTargetIdentity({ targetIdentityFile: dir }), error => error instanceof LiveTargetIdentityError && /regular file/.test(error.message));

    const empty = path.join(dir, 'empty.json');
    fs.writeFileSync(empty, '');
    assert.throws(() => loadLiveTargetIdentity({ targetIdentityFile: empty }), error => error instanceof LiveTargetIdentityError && /is empty/.test(error.message));

    const large = path.join(dir, 'large.json');
    fs.writeFileSync(large, JSON.stringify(validIdentity()).padEnd(70 * 1024, ' '));
    assert.throws(() => loadLiveTargetIdentity({ targetIdentityFile: large }), error => error instanceof LiveTargetIdentityError && /exceeds the 65536 byte limit/.test(error.message));
});

test('an identity file inside the repository is refused', () => {
    // Not created: the location is checked before the file is opened, so this
    // must be refused for where it is rather than for what it holds.  Creating
    // it would dirty the very tree the rule exists to keep clear.
    const inside = path.join(REPOSITORY_ROOT, 'target-identity.json');
    assert.equal(fs.existsSync(inside), false);
    assert.throws(
        () => loadLiveTargetIdentity({ targetIdentityFile: inside }),
        error => error instanceof LiveTargetIdentityError && /must not live inside the repository/.test(error.message),
    );
});

test('malformed JSON is refused without quoting the file back', t => {
    const secretLooking = '{"schema_version": "stage-d-live-target-identity/v1", "accessKeyId": "AKIAIOSFODNN7EXAMPLE"';
    const file = writeFile(t, secretLooking);
    assert.throws(() => loadLiveTargetIdentity({ targetIdentityFile: file }), error => {
        assert.match(error.message, /not valid JSON/);
        assert.equal(error.message.includes('AKIAIOSFODNN7EXAMPLE'), false, 'a parse failure must not echo the input');
        return true;
    });
});

test('a JSON document that is not an object is refused', t => {
    for (const contents of ['[]', '"string"', '42', 'null']) {
        refuses(t, contents, /must contain a single JSON object/);
    }
});

test('no rejection echoes a field value', t => {
    // The rule is absolute rather than best effort: a value is never printed,
    // so a secret mistyped into any field stays out of the message.  Each case
    // carries a distinctive marker the message must not contain.
    const cases = [
        { endpoint: 'https://marker-value.invalid:not-a-port' },
        { bucket: 'MARKER-VALUE-BUCKET' },
        { prefix: 'marker-value' + '/..' },
        { environment: 'marker-value-env!' },
        { provider: 'marker-value-provider' },
        { region: 'marker-value-region' },
        { purpose: 'marker-value-purpose!' },
        { schema_version: 'marker-value-schema' },
    ];
    for (const override of cases) {
        const file = writeFile(t, validIdentity(override));
        assert.throws(() => loadLiveTargetIdentity({ targetIdentityFile: file }), error => {
            assert.equal(error.message.includes('marker-value'), false, `the message for ${Object.keys(override)[0]} must not echo its value: ${error.message}`);
            return error instanceof LiveTargetIdentityError;
        });
    }
});

test('the parser is reachable directly, and reads the same document the same way', t => {
    const parsed = parseTargetIdentity(JSON.stringify(validIdentity()), 'inline');
    const loaded = loadLiveTargetIdentity({ targetIdentityFile: writeFile(t, validIdentity()) });
    assert.deepEqual({ ...parsed }, { ...loaded });
});
