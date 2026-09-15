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
    refuses(t, validIdentity({ provider: 'aws-s3' }), /provider must be one of: cloudflare-r2/);
    refuses(t, validIdentity({ region: 'us-east-1' }), /region must be one of: auto/);
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
    // The self-hosted class reaches four refusals the cases above cannot, since
    // they are evaluated only for that provider.  Each is driven with the value
    // it refuses, so the assertion is about the rule that ran rather than about
    // whichever rule happened to run first.
    for (const endpoint of [
        'https://marker-value.example.internal:9000',   // not a literal
        'https://010.011.012.013:9000',                 // non-canonical spelling
        'https://127.0.0.1:9000',                       // loopback
        'https://203.0.113.10:9000',                    // globally routable
    ]) {
        const file = writeFile(t, selfHostedIdentity({ endpoint }));
        assert.throws(() => loadLiveTargetIdentity({ targetIdentityFile: file }), error => {
            assert.equal(error.message.includes(endpoint), false, `the refusal must not echo the endpoint: ${error.message}`);
            assert.equal(error.message.includes(new URL(endpoint).hostname), false, `the refusal must not echo the host: ${error.message}`);
            return error instanceof LiveTargetIdentityError;
        });
    }
});

test('the parser is reachable directly, and reads the same document the same way', t => {
    const parsed = parseTargetIdentity(JSON.stringify(validIdentity()), 'inline');
    const loaded = loadLiveTargetIdentity({ targetIdentityFile: writeFile(t, validIdentity()) });
    assert.deepEqual({ ...parsed }, { ...loaded });
});

// ---------------------------------------------------------------------------
// The self-hosted target class
// ---------------------------------------------------------------------------

function selfHostedIdentity(overrides = {}) {
    return validIdentity({
        provider: 'self-hosted-s3',
        endpoint: 'https://192.168.11.70:9000',
        region: 'us-east-1',
        ...overrides,
    });
}

test('the self-hosted provider is admitted with a private literal endpoint', t => {
    const identity = loadLiveTargetIdentity({ targetIdentityFile: writeFile(t, selfHostedIdentity()) });
    assert.equal(identity.provider, 'self-hosted-s3');
    assert.equal(identity.endpoint, 'https://192.168.11.70:9000');
    assert.equal(identity.region, 'us-east-1');
    // The port is part of the origin, so a target on a non-default port keeps it
    // rather than being silently reduced to the scheme default.
    assert.equal(identity.endpoint.includes(':9000'), true);
});

test('every non-publicly-routable range is admitted, and the range boundaries are exact', t => {
    const admitted = [
        '10.0.0.1', '10.255.255.254',
        '100.64.0.1', '100.127.255.254',
        '169.254.1.1',
        '172.16.0.1', '172.31.255.254',
        '192.168.0.1', '192.168.255.254',
    ];
    for (const host of admitted) {
        const identity = loadLiveTargetIdentity({ targetIdentityFile: writeFile(t, selfHostedIdentity({ endpoint: `https://${host}:9000` })) });
        assert.equal(identity.endpoint, `https://${host}:9000`);
    }
    // One address on each side of every boundary.  A range rule that is off by
    // one admits or refuses exactly one address per edge, which is the kind of
    // defect that never shows up in a happy-path test.
    const refused = ['9.255.255.255', '11.0.0.0', '100.63.255.255', '100.128.0.0', '172.15.255.255', '172.32.0.0', '192.167.255.255', '192.169.0.0'];
    for (const host of refused) {
        refuses(t, selfHostedIdentity({ endpoint: `https://${host}:9000` }), /not globally routable/);
    }
});

test('a loopback endpoint is refused, and is named as loopback rather than as an unremarkable out-of-range address', t => {
    // Loopback is the one refusal in this class that has a specific reason: it
    // is the current machine, so it shares the failure domain the off-host
    // target exists to survive.  It would also fail the range test, so the
    // point of the separate check is that the diagnosis names the real problem.
    refuses(t, selfHostedIdentity({ endpoint: 'https://127.0.0.1:9000' }), /must not be a loopback address/);
    refuses(t, selfHostedIdentity({ endpoint: 'https://127.1.2.3:9000' }), /must not be a loopback address/);
});

test('a publicly routable endpoint is refused for the self-hosted provider', t => {
    // This is what keeps the class from becoming a way to ship production bytes
    // to an arbitrary public destination: the provider can only name a host on a
    // network the operator already controls.
    refuses(t, selfHostedIdentity({ endpoint: 'https://8.8.8.8:9000' }), /not globally routable/);
    refuses(t, selfHostedIdentity({ endpoint: 'https://203.0.113.10:9000' }), /not globally routable/);
});

test('a self-hosted endpoint must be a literal address, because a name cannot be checked offline', t => {
    // A loader that resolved a name would make a network call, and a name it
    // does not resolve is a destination it has not checked.  Both are refused
    // rather than being admitted on the strength of how the name looks.
    refuses(t, selfHostedIdentity({ endpoint: 'https://minio.internal:9000' }), /literal private IPv4 address/);
    refuses(t, selfHostedIdentity({ endpoint: 'https://192.168.11.70.nip.io:9000' }), /literal private IPv4 address/);
    refuses(t, selfHostedIdentity({ endpoint: 'https://[fd00::1]:9000' }), /IPv6 endpoint is not admitted/);
});

test('a non-canonical spelling is refused, because the parser rewrites it to a different address', t => {
    // The URL parser applies the WHATWG legacy IPv4 rules to the host, and those
    // rules REWRITE the text rather than preserving it.  An earlier version of
    // this test asserted the opposite -- that the spellings normalise to one
    // origin -- on the reasoning that normalisation is what makes two spellings
    // of one address one target.  The measurement disproved it: the octets of
    // `192.168.011.070` are read as OCTAL, so the host becomes 192.168.9.56, and
    // the short form `192.168.11` is read as a 24-bit tail, so the host becomes
    // 192.168.0.11.  Both land inside 192.168.0.0/16 and would therefore have
    // passed the private-range test while the transport dialled a host the
    // identity file does not name -- the one failure this class exists to make
    // impossible.
    //
    // What each spelling denotes is computed here rather than read out of the
    // refusal, because the refusal does not restate it: no field value is
    // echoed in an error.  The first two are the dangerous ones, because they
    // denote a different machine from the one the text reads as --
    // 192.168.9.56 is not 192.168.11.70, and it is a range a range test alone
    // would have admitted.
    const rewritten = [
        ['192.168.011.070', '192.168.9.56'],   // octal octets
        ['192.168.11', '192.168.0.11'],        // 24-bit tail
        ['3232238406', '192.168.11.70'],       // one integer
        ['0xc0a80b46', '192.168.11.70'],       // hexadecimal
    ];
    for (const [written, dialled] of rewritten) {
        const endpoint = `https://${written}:9000`;
        // The premise of the rule, asserted rather than assumed: if the platform
        // ever stops rewriting the legacy IPv4 forms, this says so instead of
        // letting the rule become vacuous without a failure.
        assert.equal(new URL(endpoint).hostname, dialled, 'the legacy IPv4 rewrite this rule exists to catch has changed');
        assert.throws(() => loadLiveTargetIdentity({ targetIdentityFile: writeFile(t, selfHostedIdentity({ endpoint })) }), error => {
            assert.equal(error instanceof LiveTargetIdentityError, true);
            assert.match(error.message, /must be written as the IPv4 literal it denotes/);
            // The last two spellings denote the SAME address as the canonical
            // one and are refused anyway: the rule is that the field is written
            // as the literal it denotes, not that it resolves to an admitted
            // address, because an identity whose target can only be known by
            // parsing it is an identity a reviewer cannot read.
            assert.equal(error.message.includes(written), false, `the refusal must not restate the spelling: ${error.message}`);
            assert.equal(error.message.includes(dialled), false, `the refusal must not restate the address it resolves to: ${error.message}`);
            return true;
        });
    }

    // The canonical spelling of the same host still loads, so the rule refuses
    // spellings rather than the address -- without this the test would pass for
    // a loader that admitted no self-hosted endpoint at all.
    const canonical = loadLiveTargetIdentity({ targetIdentityFile: writeFile(t, selfHostedIdentity({ endpoint: 'https://192.168.11.70:9000' })) });
    assert.equal(canonical.endpoint, 'https://192.168.11.70:9000');
});

// ---------------------------------------------------------------------------
// Binding the endpoint to the provider it was declared with
// ---------------------------------------------------------------------------

test('the region is validated against the provider it was named with, not against a union', t => {
    // `us-east-1` is a valid region for one provider and `auto` for the other,
    // so a flat union would admit both cross pairs.  Each names a target that
    // cannot resolve: the region reaches the signature, so the mismatched pair
    // signs for one target and addresses another.
    refuses(t, validIdentity({ region: 'us-east-1' }), /region must be one of: auto for provider cloudflare-r2/);
    refuses(t, selfHostedIdentity({ region: 'auto' }), /region must be one of: us-east-1 for provider self-hosted-s3/);
    refuses(t, selfHostedIdentity({ region: 'eu-west-1' }), /region must be one of: us-east-1 for provider self-hosted-s3/);
});

test('an R2 endpoint must be an account host under the provider domain', t => {
    refuses(t, validIdentity({ endpoint: 'https://storage.example.com' }), /must be an account host under \.r2\.cloudflarestorage\.com/);
    // A host that merely CONTAINS the provider's domain ends somewhere else.
    refuses(t, validIdentity({ endpoint: 'https://account.r2.cloudflarestorage.com.attacker.example' }), /must be an account host under \.r2\.cloudflarestorage\.com/);
    // The bare registrable domain carries no account label, so it names no
    // target even though it is the provider's own domain.
    refuses(t, validIdentity({ endpoint: 'https://r2.cloudflarestorage.com' }), /must be an account host under \.r2\.cloudflarestorage\.com/);
    // A leading dot is the other spelling of "no account label": the host ends
    // with the suffix and is not the bare domain, so it passed both of the
    // obvious tests while naming no account, and the loader addressed it.
    refuses(t, validIdentity({ endpoint: 'https://.r2.cloudflarestorage.com' }), /must be an account host under \.r2\.cloudflarestorage\.com/);
    // More than one label stays admitted, because a virtual-hosted-style
    // endpoint puts the bucket in front of the account id: the rule is that an
    // account label is present, not that it is the only one.
    const virtualHosted = loadLiveTargetIdentity({ targetIdentityFile: writeFile(t, validIdentity({ endpoint: 'https://bucket.0123456789abcdef0123456789abcdef.r2.cloudflarestorage.com' })) });
    assert.equal(virtualHosted.endpoint, 'https://bucket.0123456789abcdef0123456789abcdef.r2.cloudflarestorage.com');
    // A publicly routable address is not an R2 endpoint either.
    refuses(t, validIdentity({ endpoint: 'https://203.0.113.10' }), /must be an account host under \.r2\.cloudflarestorage\.com/);
});

test('the two providers cannot be aimed at each other, in either direction', t => {
    // The pairing the binding exists to refuse: a valid endpoint for one
    // provider declared with the other provider's name and region.  Either half
    // alone looks correct, and only the pair is wrong.
    refuses(t, validIdentity({ endpoint: 'https://192.168.11.70:9000' }), /must be an account host under \.r2\.cloudflarestorage\.com/);
    refuses(t, selfHostedIdentity({ endpoint: 'https://0123456789abcdef0123456789abcdef.r2.cloudflarestorage.com' }), /literal private IPv4 address/);
});

test('a self-hosted identity carries the port through to the fingerprint', t => {
    // Two targets on one host differing only by port are different targets, so
    // the fingerprint has to distinguish them -- otherwise evidence recorded
    // against one would be read as evidence about the other.
    const a = parseTargetIdentity(JSON.stringify(selfHostedIdentity({ endpoint: 'https://192.168.11.70:9000' })), 'inline');
    const b = parseTargetIdentity(JSON.stringify(selfHostedIdentity({ endpoint: 'https://192.168.11.70:9001' })), 'inline');
    assert.notEqual(a.target_fingerprint, b.target_fingerprint);
    const again = parseTargetIdentity(JSON.stringify(selfHostedIdentity({ endpoint: 'https://192.168.11.70:9000' })), 'inline');
    assert.equal(a.target_fingerprint, again.target_fingerprint);
});
