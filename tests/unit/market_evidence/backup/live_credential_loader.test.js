'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const { installNetworkTripwire } = require('../../../helpers/network_tripwire');
const {
    loadLiveCredentials,
    describeCredentialPresence,
    parseCredentialDocument,
    LiveCredentialError,
} = require('../../../../src/infrastructure/market_evidence/backup/liveCredentialLoader');

// The credential loader is the one component in the tree that holds a secret,
// so its file is sealed like the rest: a loader that reached out to validate a
// key would be both a leak and a contradiction of the offline claim.
const tripwire = installNetworkTripwire();
test.after(() => {
    assert.deepEqual(tripwire.attempts, [], 'no test in this file may attempt outbound network access');
    tripwire.restore();
});

const REPOSITORY_ROOT = path.resolve(__dirname, '../../../../');
const CREDENTIAL_MODULE = path.resolve(REPOSITORY_ROOT, 'src/infrastructure/market_evidence/backup/liveCredentialLoader.js');
const IDENTITY_MODULE = path.resolve(REPOSITORY_ROOT, 'src/infrastructure/market_evidence/backup/liveTargetIdentity.js');

// Every value here is synthetic and marked as such.  Nothing in this file uses,
// copies or resembles a real credential, and the markers exist so a leak is
// detectable rather than merely asserted to be absent.
const ACCESS_KEY_ID = 'synthetic-access-key-id-DO-NOT-USE';
const SECRET_ACCESS_KEY = 'synthetic-secret-access-key-DO-NOT-USE';
const SESSION_TOKEN = 'synthetic-session-token-DO-NOT-USE';
const ALL_VALUES = [ACCESS_KEY_ID, SECRET_ACCESS_KEY, SESSION_TOKEN];

function validCredentials(overrides = {}) {
    return { accessKeyId: ACCESS_KEY_ID, secretAccessKey: SECRET_ACCESS_KEY, ...overrides };
}

function temporary(t, prefix) {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), prefix));
    t.after(() => fs.rmSync(dir, { recursive: true, force: true }));
    return dir;
}

function writeFile(t, contents, { name = 'credentials.json', mode = 0o600 } = {}) {
    const file = path.join(temporary(t, 'stage-d-credential-'), name);
    fs.writeFileSync(file, typeof contents === 'string' ? contents : JSON.stringify(contents), { mode });
    // Explicit, because the creation mode is masked by the umask and the mode is
    // the thing under test.
    fs.chmodSync(file, mode);
    return file;
}

function refuses(t, contents, matcher, options) {
    const file = writeFile(t, contents, options);
    assert.throws(() => loadLiveCredentials({ credentialFile: file }), error => {
        assert.equal(error instanceof LiveCredentialError, true, `expected a LiveCredentialError, got ${error.name}: ${error.message}`);
        assert.equal(error.code, 'LIVE_CREDENTIAL_INVALID');
        return matcher.test(error.message);
    });
}

// A message may describe what is wrong with a credential file; it may never
// quote one.
function assertNoValueLeaked(text, label) {
    for (const value of ALL_VALUES) {
        assert.equal(text.includes(value), false, `${label} must not contain a credential value`);
    }
}

test('credentials load from an explicitly named 0600 file and come back frozen', t => {
    const credentials = loadLiveCredentials({ credentialFile: writeFile(t, validCredentials()) });
    assert.deepEqual({ ...credentials }, { accessKeyId: ACCESS_KEY_ID, secretAccessKey: SECRET_ACCESS_KEY });
    assert.equal(credentials.sessionToken, undefined, 'a long-lived credential has no session token');
    assert.equal(Object.isFrozen(credentials), true);
    assert.throws(() => { credentials.accessKeyId = 'other'; }, TypeError);
});

test('a temporary credential is supported: the session token is carried through', t => {
    const credentials = loadLiveCredentials({ credentialFile: writeFile(t, validCredentials({ sessionToken: SESSION_TOKEN })) });
    assert.equal(credentials.sessionToken, SESSION_TOKEN);
    assert.equal(describeCredentialPresence(credentials).session_token_present, true);
    assert.equal(describeCredentialPresence({ accessKeyId: ACCESS_KEY_ID, secretAccessKey: SECRET_ACCESS_KEY }).session_token_present, false);
});

test('the only thing reported about a credential is its class', t => {
    const credentials = loadLiveCredentials({ credentialFile: writeFile(t, validCredentials({ sessionToken: SESSION_TOKEN })) });
    const described = describeCredentialPresence(credentials);
    assert.deepEqual({ ...described }, { credential_source: 'EXPLICIT_FILE', implicit_discovery: false, session_token_present: true });
    assertNoValueLeaked(JSON.stringify(described), 'the descriptor');
});

test('the credential file path is required explicitly and has no default', () => {
    for (const argument of [undefined, null, '', '   ', 42, {}]) {
        assert.throws(() => loadLiveCredentials({ credentialFile: argument }), LiveCredentialError);
    }
    assert.throws(() => loadLiveCredentials(), LiveCredentialError);
    assert.throws(() => loadLiveCredentials({}), error => error instanceof LiveCredentialError && /explicitly/.test(error.message));
});

test('permissions stricter than 0600 are accepted, and anything looser is refused', t => {
    for (const mode of [0o600, 0o400, 0o500, 0o700]) {
        const credentials = loadLiveCredentials({ credentialFile: writeFile(t, validCredentials(), { mode }) });
        assert.equal(credentials.accessKeyId, ACCESS_KEY_ID, `mode ${mode.toString(8)} must be accepted`);
    }
    for (const mode of [0o640, 0o604, 0o644, 0o660, 0o606, 0o666, 0o777]) {
        refuses(t, validCredentials(), /must not be readable or writable by group or other/, { mode });
    }
});

test('a symbolic link, a directory, an empty file and an oversized file are refused', t => {
    const dir = temporary(t, 'stage-d-credential-shape-');
    const real = path.join(dir, 'real.json');
    fs.writeFileSync(real, JSON.stringify(validCredentials()), { mode: 0o600 });
    fs.chmodSync(real, 0o600);
    const link = path.join(dir, 'link.json');
    fs.symlinkSync(real, link);
    assert.throws(() => loadLiveCredentials({ credentialFile: link }), error => error instanceof LiveCredentialError && /regular file that is not a symbolic link/.test(error.message));

    assert.throws(() => loadLiveCredentials({ credentialFile: dir }), error => error instanceof LiveCredentialError && /regular file/.test(error.message));

    const empty = path.join(dir, 'empty.json');
    fs.writeFileSync(empty, '', { mode: 0o600 });
    assert.throws(() => loadLiveCredentials({ credentialFile: empty }), error => error instanceof LiveCredentialError && /is empty/.test(error.message));

    const large = path.join(dir, 'large.json');
    fs.writeFileSync(large, JSON.stringify({ accessKeyId: ACCESS_KEY_ID, secretAccessKey: 'x'.repeat(70 * 1024) }), { mode: 0o600 });
    assert.throws(() => loadLiveCredentials({ credentialFile: large }), error => error instanceof LiveCredentialError && /exceeds the 65536 byte limit/.test(error.message));
});

test('a credential file inside the repository is refused', () => {
    // Not created: the location is checked before the file is opened, so the
    // refusal is about where it is.  Creating it would leave a credential-shaped
    // path in the tree the rule exists to keep clear.
    const inside = path.join(REPOSITORY_ROOT, 'credentials.json');
    assert.equal(fs.existsSync(inside), false);
    assert.throws(
        () => loadLiveCredentials({ credentialFile: inside }),
        error => error instanceof LiveCredentialError && /must not live inside the repository/.test(error.message),
    );
});

test('a credential file inside an evidence directory is refused', t => {
    const evidence = path.join(temporary(t, 'stage-d-credential-evidence-'), 'FootballPrediction.artifacts');
    fs.mkdirSync(evidence, { mode: 0o700 });
    const file = path.join(evidence, 'credentials.json');
    fs.writeFileSync(file, JSON.stringify(validCredentials()), { mode: 0o600 });
    fs.chmodSync(file, 0o600);
    assert.throws(
        () => loadLiveCredentials({ credentialFile: file }),
        error => error instanceof LiveCredentialError && /must not live inside an evidence directory/.test(error.message),
    );
});

test('the required fields are required, and an unknown field is refused rather than ignored', t => {
    refuses(t, { accessKeyId: ACCESS_KEY_ID }, /missing required fields: secretAccessKey/);
    refuses(t, { secretAccessKey: SECRET_ACCESS_KEY }, /missing required fields: accessKeyId/);
    refuses(t, validCredentials({ region: 'auto' }), /does not define.*region/s);
    refuses(t, validCredentials({ profile: 'default' }), /does not define.*profile/s);
});

test('a field name that is itself secret-shaped is not printed', t => {
    const secretKeyed = { [`${ACCESS_KEY_ID}`]: 'x', accessKeyId: ACCESS_KEY_ID, secretAccessKey: SECRET_ACCESS_KEY };
    const file = writeFile(t, secretKeyed);
    assert.throws(() => loadLiveCredentials({ credentialFile: file }), error => {
        assert.match(error.message, /<unprintable field name>/);
        assertNoValueLeaked(error.message, 'an unknown-field error');
        return error instanceof LiveCredentialError;
    });
});

test('values must be non-empty, unpadded strings without control characters', t => {
    refuses(t, { accessKeyId: '', secretAccessKey: SECRET_ACCESS_KEY }, /accessKeyId must be a non-empty string/);
    refuses(t, { accessKeyId: 42, secretAccessKey: SECRET_ACCESS_KEY }, /accessKeyId must be a non-empty string/);
    refuses(t, { accessKeyId: ` ${ACCESS_KEY_ID}`, secretAccessKey: SECRET_ACCESS_KEY }, /surrounding whitespace/);
    refuses(t, { accessKeyId: ACCESS_KEY_ID, secretAccessKey: `${SECRET_ACCESS_KEY}\n` }, /surrounding whitespace/);
    refuses(t, validCredentials({ sessionToken: '' }), /sessionToken must be a non-empty string/);
    refuses(t, validCredentials({ sessionToken: 'a\x00b' }), /control characters/);
    refuses(t, validCredentials({ sessionToken: 'x'.repeat(4097) }), /character limit/);
});

test('malformed JSON is refused without quoting the file back', t => {
    const file = writeFile(t, `{"accessKeyId": "${ACCESS_KEY_ID}", "secretAccessKey": `);
    assert.throws(() => loadLiveCredentials({ credentialFile: file }), error => {
        assert.match(error.message, /not valid JSON/);
        assertNoValueLeaked(error.message, 'a parse error');
        return error instanceof LiveCredentialError;
    });
});

test('a document that is not an object is refused', t => {
    for (const contents of ['[]', '"string"', '42', 'null']) {
        refuses(t, contents, /must contain a single JSON object/);
    }
});

test('no rejection echoes a credential value', t => {
    const cases = [
        { accessKeyId: ACCESS_KEY_ID },
        validCredentials({ region: 'auto' }),
        { accessKeyId: `${ACCESS_KEY_ID} `, secretAccessKey: SECRET_ACCESS_KEY },
        { accessKeyId: ACCESS_KEY_ID, secretAccessKey: SECRET_ACCESS_KEY, sessionToken: 'a\x00b' },
    ];
    for (const contents of cases) {
        const file = writeFile(t, contents);
        assert.throws(() => loadLiveCredentials({ credentialFile: file }), error => {
            assertNoValueLeaked(error.message, 'a rejection message');
            assertNoValueLeaked(JSON.stringify(error), 'a serialized error');
            return error instanceof LiveCredentialError;
        });
    }
});

test('neither live loader can discover a credential: nothing in either reads the environment', () => {
    // The behavioural half: with the SDK's own environment variables set, a
    // load with no path still fails.  There is no fallback to fall back to.
    const previous = {};
    const planted = {
        AWS_ACCESS_KEY_ID: ACCESS_KEY_ID,
        AWS_SECRET_ACCESS_KEY: SECRET_ACCESS_KEY,
        AWS_SESSION_TOKEN: SESSION_TOKEN,
        AWS_PROFILE: 'stage-d',
        AWS_SHARED_CREDENTIALS_FILE: '/nonexistent/credentials',
        AWS_CONFIG_FILE: '/nonexistent/config',
        AWS_DEFAULT_REGION: 'auto',
    };
    for (const [name, value] of Object.entries(planted)) {
        previous[name] = process.env[name];
        process.env[name] = value;
    }
    try {
        assert.throws(() => loadLiveCredentials(), error => error instanceof LiveCredentialError && /explicitly/.test(error.message));
        assert.throws(() => loadLiveCredentials({}), LiveCredentialError);
    } finally {
        for (const [name, value] of Object.entries(previous)) {
            if (value === undefined) delete process.env[name];
            else process.env[name] = value;
        }
    }

    // The structural half: the property is that these modules never consult the
    // environment at all, which is stronger than any one variable being ignored
    // and is checkable without guessing which variable someone would add next.
    for (const modulePath of [CREDENTIAL_MODULE, IDENTITY_MODULE]) {
        const source = fs.readFileSync(modulePath, 'utf8');
        assert.equal(source.includes('process.env'), false, `${path.basename(modulePath)} must not read the environment`);
        assert.equal(source.includes('homedir'), false, `${path.basename(modulePath)} must not resolve a home directory`);
        assert.equal(/require\(['"]@aws-sdk/.test(source), false, `${path.basename(modulePath)} must not link the SDK`);
    }
});

test('the parser is reachable directly, and reads the same document the same way', t => {
    const parsed = parseCredentialDocument(JSON.stringify(validCredentials({ sessionToken: SESSION_TOKEN })));
    const loaded = loadLiveCredentials({ credentialFile: writeFile(t, validCredentials({ sessionToken: SESSION_TOKEN })) });
    assert.deepEqual({ ...parsed }, { ...loaded });
});

test('a credential file may legitimately hold a value long enough for a session token', t => {
    // A temporary credential's token is a signed document, not a short string,
    // so the bound has to accommodate one without becoming a memory foothold.
    const longToken = `synthetic.${'p'.repeat(2000)}.DO-NOT-USE`;
    const credentials = loadLiveCredentials({ credentialFile: writeFile(t, validCredentials({ sessionToken: longToken })) });
    assert.equal(credentials.sessionToken.length, longToken.length);
});
