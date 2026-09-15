'use strict';

// Non-secret target identity for the live off-host backup target.
//
// This is the addressing half of a live target: provider, endpoint, bucket,
// region, prefix, and the labels that say what the target is for.  It carries no
// credential material and it has no field that could hold any.  The schema is a
// closed allowlist of nine names, so a credential pasted into the file is
// rejected as an unknown field rather than accepted and ignored -- and rejecting
// it is the point.  A field the loader does not understand is a field the
// operator believes is doing something.
//
// There is no default location and no discovery.  A caller that does not name a
// file gets an error, never a guess: a loader that can find a target on its own
// cannot be reasoned about, because the target it found is not the one the
// operator meant.
//
// Values are never echoed in an error message.  A field is named, and only when
// that name is itself safe to print -- `endpont` is a typo worth reporting; an
// access key id used as a JSON key is not.  Rules are stated instead of values,
// so a diagnosis costs the operator a second look rather than costing the log a
// secret.

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const { canonicalizeKey } = require('./localTransport');

const LIVE_TARGET_IDENTITY_SCHEMA_VERSION = 'stage-d-live-target-identity/v1';

// A closed enum, and it stays closed.  A closed enum is a stronger statement
// than a validated string: it records which target classes this code path has
// been adjudicated for, and every member is a design decision rather than a
// configuration value.  That is why widening it is a reviewed act rather than
// an edit.
//
// Two members, each admitted on its own decision:
//
//   cloudflare-r2 -- the original target class.
//
//   aws-s3        -- admitted after R2's provisioning was blocked on a payment
//                    method the Owner could not supply and the work had to
//                    continue against a different off-host target.  It was
//                    admitted on official documentation rather than on a live
//                    probe: conditional create is Amazon S3's own published
//                    contract (`If-None-Match: "*"` on PutObject, 412 on an
//                    existing key), Object Lock in compliance mode is
//                    documented as irreversible by any principal including the
//                    account root, and delete is independently deniable.  Its
//                    create-only capability is therefore DOCUMENTED_SUPPORTED
//                    and NOT live-proven.  Nothing here should be read as
//                    claiming otherwise -- the live capability probe remains a
//                    precondition of any real backup reaching this target.
const ALLOWED_PROVIDERS = Object.freeze(['cloudflare-r2', 'aws-s3']);

// The region each admitted provider accepts, keyed by provider rather than held
// as one flat list.  Region vocabularies do not overlap: `auto` is R2's S3 API's
// own region value and is meaningless to Amazon S3, while an AWS region name is
// meaningless to R2.  A pair drawn from two different providers names a target
// that cannot resolve, so the pair is refused rather than forwarded -- the same
// reason the provider list is closed.  A region is part of a target's identity,
// not a tuning knob.
const PROVIDER_REGIONS = Object.freeze({
    'cloudflare-r2': Object.freeze(['auto']),
    'aws-s3': Object.freeze(['ap-southeast-1']),
});

// The union, kept as the module's stated surface.  Validation uses
// PROVIDER_REGIONS, because a union cannot say which region belongs to which
// provider.
const ALLOWED_REGIONS = Object.freeze([...new Set(Object.values(PROVIDER_REGIONS).flat())]);

const REQUIRED_FIELDS = Object.freeze([
    'schema_version',
    'provider',
    'endpoint',
    'bucket',
    'region',
    'prefix',
    'environment',
    'project',
    'purpose',
]);

const MAX_IDENTITY_FILE_BYTES = 64 * 1024;
const MAX_LABEL_LENGTH = 32;
const LABEL_PATTERN = /^[a-z][a-z0-9-]*$/;

// The adjudicated bucket-name rules, which every admitted provider accepts:
// 3-63 characters, lowercase letters, digits and hyphens, beginning and ending
// alphanumeric.  These are R2's documented rules exactly, and Amazon S3's are a
// superset that additionally permits dots -- so every name this pattern admits
// is valid for both.  The pattern is deliberately the intersection rather than
// the union: a name one admitted provider accepts and another refuses is not a
// target, it is a provisioning mistake this file exists to catch.
const BUCKET_PATTERN = /^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$/;

// A field name is printed only when it is safe to print.  Two independent
// conditions, because they fail differently: the pattern rejects a name that is
// not a name at all, and the shape test rejects a name that is being used to
// smuggle a value out through the diagnostic -- `{"AKIA…": "x"}` is a JSON
// object whose key is the secret.
const SAFE_FIELD_NAME_PATTERN = /^[A-Za-z_][A-Za-z0-9_]{0,40}$/;
const SECRET_SHAPED_NAME_PATTERN = /(?:access.?key|secret|token|password|passwd|credential|private|bearer|session|signature)/i;
const UNPRINTABLE_FIELD_NAME = '<unprintable field name>';

// Values are additionally checked against the shapes a credential actually
// takes, so `TARGET_IDENTITY_CONTAINS_SECRET=NO` is a check the loader performs
// rather than a claim the schema implies.  A non-secret identity never trips
// these: bucket names are short and lowercase, the prefix is a short-segment
// key, and the labels are bounded.
const SECRET_VALUE_PATTERNS = Object.freeze([
    /AKIA[0-9A-Z]{16}/,
    /-----BEGIN [A-Z ]*PRIVATE KEY-----/,
    /^(?:Bearer|Basic)\s+\S+/i,
    /^[A-Za-z0-9+/]{40,}={0,2}$/,
    /^[a-f0-9]{40,}$/i,
]);

class LiveTargetIdentityError extends Error {
    constructor(message) {
        super(message);
        this.name = 'LiveTargetIdentityError';
        this.code = 'LIVE_TARGET_IDENTITY_INVALID';
    }
}

function safeFieldName(name) {
    if (typeof name !== 'string') return UNPRINTABLE_FIELD_NAME;
    if (!SAFE_FIELD_NAME_PATTERN.test(name)) return UNPRINTABLE_FIELD_NAME;
    if (SECRET_SHAPED_NAME_PATTERN.test(name)) return UNPRINTABLE_FIELD_NAME;
    // A name can also *be* the secret: `{"AKIA…": "x"}` is a JSON object whose
    // key is the credential, and it satisfies every lexical rule a name has to.
    // The value shapes are therefore applied to the name as well.
    for (const pattern of SECRET_VALUE_PATTERNS) {
        if (pattern.test(name)) return UNPRINTABLE_FIELD_NAME;
    }
    return name;
}

// The repository root is found by walking up from this file, not from the
// process's working directory: cwd is chosen by whoever ran the command, and a
// containment check anchored on a directory the caller can pick proves nothing.
let cachedRepositoryRoot = null;
function repositoryRoot() {
    if (cachedRepositoryRoot !== null) return cachedRepositoryRoot;
    let candidate = __dirname;
    for (;;) {
        if (fs.existsSync(path.join(candidate, 'package.json'))) {
            cachedRepositoryRoot = candidate;
            return candidate;
        }
        const parent = path.dirname(candidate);
        if (parent === candidate) throw new LiveTargetIdentityError('could not locate the repository root, so a target identity file cannot be proven to be outside it');
        candidate = parent;
    }
}

function assertOutsideRepository(resolved, label) {
    const root = repositoryRoot();
    const relative = path.relative(root, resolved);
    if (relative === '' || (!relative.startsWith('..') && !path.isAbsolute(relative))) {
        throw new LiveTargetIdentityError(`${label} must not live inside the repository; a live target address belongs outside it`);
    }
}

// `O_NOFOLLOW` refuses a symlink in the final component, which is the component
// the operator names.  Parent components are deliberately not walked here: a
// symlinked parent is ordinary on Linux (`/var/run`, mounted scratch space), and
// refusing it would break legitimate paths while proving nothing -- the file is
// read once and its identity is re-checked afterwards instead.
function readOnceAsRegularFile(resolved, { label, maxBytes }) {
    let descriptor;
    try {
        descriptor = fs.openSync(resolved, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW);
    } catch (error) {
        throw new LiveTargetIdentityError(`${label} could not be opened as a regular file that is not a symbolic link`);
    }
    try {
        const before = fs.fstatSync(descriptor);
        if (!before.isFile()) throw new LiveTargetIdentityError(`${label} must be a regular file`);
        if (before.size === 0) throw new LiveTargetIdentityError(`${label} is empty`);
        if (before.size > maxBytes) throw new LiveTargetIdentityError(`${label} exceeds the ${maxBytes} byte limit for this file`);
        const bytes = fs.readFileSync(descriptor);
        const after = fs.fstatSync(descriptor);
        // A pathname is re-resolved by the kernel, so the file that was opened
        // and the file that was read can differ if something swapped it in
        // between.  What was read is therefore only trusted once it is known to
        // be the same object, at the same size, with the same modification time,
        // as the one that was measured.
        if (after.dev !== before.dev || after.ino !== before.ino || after.size !== before.size || after.mtimeMs !== before.mtimeMs) {
            throw new LiveTargetIdentityError(`${label} changed while it was being read; a partially read file is refused`);
        }
        return bytes;
    } finally {
        fs.closeSync(descriptor);
    }
}

function stringField(value, field) {
    if (typeof value !== 'string' || value.trim() === '') throw new LiveTargetIdentityError(`target identity field ${field} must be a non-empty string`);
    if (value !== value.trim()) throw new LiveTargetIdentityError(`target identity field ${field} must not carry surrounding whitespace`);
    // eslint-disable-next-line no-control-regex
    if (/[\x00-\x1f\x7f]/.test(value)) throw new LiveTargetIdentityError(`target identity field ${field} must not contain control characters`);
    return value;
}

function assertNoSecretShape(value, field) {
    for (const pattern of SECRET_VALUE_PATTERNS) {
        if (pattern.test(value)) throw new LiveTargetIdentityError(`target identity field ${field} carries a value shaped like a secret; a target identity file is non-secret by construction`);
    }
}

function validateEndpoint(value) {
    const text = stringField(value, 'endpoint');
    let parsed;
    try {
        parsed = new URL(text);
    } catch (error) {
        throw new LiveTargetIdentityError('target identity field endpoint must be an absolute URL');
    }
    if (parsed.protocol !== 'https:') throw new LiveTargetIdentityError('target identity field endpoint must use https');
    if (parsed.username || parsed.password) throw new LiveTargetIdentityError('target identity field endpoint must not carry userinfo');
    if (parsed.search || parsed.hash) throw new LiveTargetIdentityError('target identity field endpoint must not carry a query or a fragment');
    if (parsed.pathname !== '/' && parsed.pathname !== '') throw new LiveTargetIdentityError('target identity field endpoint must not carry a path; the snapshot namespace is the separate prefix field');
    // A bare hostname is refused: `https://localhost` or `https://r2` addresses
    // whatever the resolver happens to answer, which is exactly the ambiguity a
    // live target must not have.
    if (!parsed.hostname.includes('.')) throw new LiveTargetIdentityError('target identity field endpoint must name a fully qualified host');
    return parsed.origin;
}

function validateLabel(value, field) {
    const text = stringField(value, field);
    if (text.length > MAX_LABEL_LENGTH) throw new LiveTargetIdentityError(`target identity field ${field} must be at most ${MAX_LABEL_LENGTH} characters`);
    if (!LABEL_PATTERN.test(text)) throw new LiveTargetIdentityError(`target identity field ${field} must be lowercase alphanumeric with single hyphens, starting with a letter`);
    return text;
}

function parseTargetIdentity(text, source) {
    let raw;
    try {
        raw = JSON.parse(text);
    } catch (error) {
        // The parser's own message quotes the input it choked on, and the input
        // is the entire file.  It is replaced rather than forwarded.
        throw new LiveTargetIdentityError('target identity file is not valid JSON');
    }
    if (raw === null || typeof raw !== 'object' || Array.isArray(raw)) throw new LiveTargetIdentityError('target identity file must contain a single JSON object');

    const unknown = Object.keys(raw).filter(key => !REQUIRED_FIELDS.includes(key));
    if (unknown.length) {
        throw new LiveTargetIdentityError(`target identity file carries fields this schema does not define, and an undefined field is refused rather than ignored: ${unknown.map(safeFieldName).join(', ')}`);
    }
    const missing = REQUIRED_FIELDS.filter(field => !Object.prototype.hasOwnProperty.call(raw, field));
    if (missing.length) throw new LiveTargetIdentityError(`target identity file is missing required fields: ${missing.join(', ')}`);

    const schemaVersion = stringField(raw.schema_version, 'schema_version');
    if (schemaVersion !== LIVE_TARGET_IDENTITY_SCHEMA_VERSION) throw new LiveTargetIdentityError(`target identity field schema_version must be ${LIVE_TARGET_IDENTITY_SCHEMA_VERSION}`);

    const provider = stringField(raw.provider, 'provider');
    if (!ALLOWED_PROVIDERS.includes(provider)) throw new LiveTargetIdentityError(`target identity field provider must be one of: ${ALLOWED_PROVIDERS.join(', ')}`);

    const endpoint = validateEndpoint(raw.endpoint);

    const bucket = stringField(raw.bucket, 'bucket');
    if (!BUCKET_PATTERN.test(bucket)) throw new LiveTargetIdentityError('target identity field bucket must be 3-63 characters of lowercase letters, digits and hyphens, beginning and ending alphanumeric');

    const region = stringField(raw.region, 'region');
    const allowedRegions = PROVIDER_REGIONS[provider];
    if (!allowedRegions.includes(region)) throw new LiveTargetIdentityError(`target identity field region must be one of: ${allowedRegions.join(', ')} for provider ${provider}`);

    const prefix = stringField(raw.prefix, 'prefix');
    try {
        canonicalizeKey(prefix);
    } catch (error) {
        // The canonicaliser quotes the key it rejected.  The rule is reported
        // instead, so a secret mistyped into this field stays out of the log.
        throw new LiveTargetIdentityError('target identity field prefix must be a relative object-key path with no leading, trailing or empty segments, no traversal segments, no backslashes and no null byte');
    }

    const environment = validateLabel(raw.environment, 'environment');
    const project = validateLabel(raw.project, 'project');
    const purpose = validateLabel(raw.purpose, 'purpose');

    for (const [field, value] of Object.entries({ endpoint, bucket, region, prefix, environment, project, purpose })) {
        assertNoSecretShape(value, field);
    }

    // A stable, non-secret handle for the target.  Evidence and reports can name
    // which target a run addressed without restating the account-bearing
    // endpoint, and two runs can be compared for "same target" without either
    // one publishing the address.
    const targetFingerprint = crypto
        .createHash('sha256')
        .update(JSON.stringify({ provider, endpoint, bucket, region, prefix }))
        .digest('hex')
        .slice(0, 16);

    return Object.freeze({
        schema_version: LIVE_TARGET_IDENTITY_SCHEMA_VERSION,
        provider,
        endpoint,
        bucket,
        region,
        prefix,
        environment,
        project,
        purpose,
        target_fingerprint: targetFingerprint,
    });
}

// Explicit path in, validated frozen identity out.  `targetIdentityFile` has no
// default and is never resolved from the environment, a profile or a
// conventional location.
function loadLiveTargetIdentity({ targetIdentityFile } = {}) {
    if (typeof targetIdentityFile !== 'string' || targetIdentityFile.trim() === '') {
        throw new LiveTargetIdentityError('a target identity file must be supplied explicitly; this loader has no default location and no discovery path');
    }
    const resolved = path.resolve(targetIdentityFile);
    assertOutsideRepository(resolved, 'the target identity file');
    const bytes = readOnceAsRegularFile(resolved, { label: 'target identity file', maxBytes: MAX_IDENTITY_FILE_BYTES });
    return parseTargetIdentity(bytes.toString('utf8'), resolved);
}

module.exports = {
    loadLiveTargetIdentity,
    parseTargetIdentity,
    LiveTargetIdentityError,
    LIVE_TARGET_IDENTITY_SCHEMA_VERSION,
    ALLOWED_PROVIDERS,
    ALLOWED_REGIONS,
    PROVIDER_REGIONS,
    REQUIRED_FIELDS,
    MAX_IDENTITY_FILE_BYTES,
};
