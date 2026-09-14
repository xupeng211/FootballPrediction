'use strict';

// Fail-closed credential loader for the live off-host target.
//
// The live path has exactly one way to obtain a credential: an explicit file
// path handed to this loader by the caller.  There is no default location, no
// `~/.aws`, no `AWS_PROFILE`, no `AWS_*` environment variable, no SDK provider
// chain and no instance metadata.  Nothing in this module reads the environment
// at all, which is the point: a credential that can be discovered cannot be
// accounted for, and an executor that silently picks one up reports a source it
// did not choose.
//
// Fail-closed means every one of these is a refusal rather than a degradation:
// a missing path, a path that is not a regular file, a symbolic link, a file
// readable or writable by anyone but its owner, an oversized file, malformed
// JSON, an unknown field, or an empty value.  There is no partial load and no
// fallback to an ambient credential.
//
// Secret handling: the file is read once, into a Buffer, which is zeroed as
// soon as it has been decoded.  Values are never logged, never echoed in an
// error, never returned in a descriptor and never written anywhere.  The
// decoded string itself cannot be zeroed -- JavaScript strings are immutable and
// the engine may copy them -- so zeroization here is best effort over the bytes
// this module owns, and is reported as such rather than claimed as complete.

const fs = require('fs');
const path = require('path');

const CREDENTIAL_FIELDS = Object.freeze(['accessKeyId', 'secretAccessKey', 'sessionToken']);
const REQUIRED_CREDENTIAL_FIELDS = Object.freeze(['accessKeyId', 'secretAccessKey']);

const MAX_CREDENTIAL_FILE_BYTES = 64 * 1024;
// Generous on purpose: an access key id is short, but a temporary credential's
// session token is a signed document and can be well over a kilobyte.
const MAX_CREDENTIAL_VALUE_LENGTH = 4096;

// A credential file is found by accident in one place far more often than
// anywhere else: inside an evidence directory that is about to be sealed and
// handed to a reviewer.  The convention is recognisable, so it is refused.
// This guard is a named convention, not a proof -- it can only recognise the
// shape it was written against, and a credential file elsewhere inside a
// published tree would pass it.  Keeping the file outside both the repository
// and any evidence root remains an operator obligation.
const EVIDENCE_DIRECTORY_PATTERN = /\.artifacts$/i;

const SAFE_FIELD_NAME_PATTERN = /^[A-Za-z_][A-Za-z0-9_]{0,40}$/;
const SECRET_SHAPED_NAME_PATTERN = /(?:access.?key|secret|token|password|passwd|credential|private|bearer|session|signature)/i;
const UNPRINTABLE_FIELD_NAME = '<unprintable field name>';

// The value shapes a credential actually takes.  Applied to the values a file
// carries -- and to its field names, because `{"AKIA…": "x"}` is a JSON object
// whose key is the credential, and a name like that satisfies every lexical
// rule a name has to.
const SECRET_VALUE_PATTERNS = Object.freeze([
    /AKIA[0-9A-Z]{16}/,
    /-----BEGIN [A-Z ]*PRIVATE KEY-----/,
    /^(?:Bearer|Basic)\s+\S+/i,
    /^[A-Za-z0-9+/]{40,}={0,2}$/,
    /^[a-f0-9]{40,}$/i,
]);

class LiveCredentialError extends Error {
    constructor(message) {
        super(message);
        this.name = 'LiveCredentialError';
        this.code = 'LIVE_CREDENTIAL_INVALID';
    }
}

function safeFieldName(name) {
    if (typeof name !== 'string') return UNPRINTABLE_FIELD_NAME;
    if (!SAFE_FIELD_NAME_PATTERN.test(name)) return UNPRINTABLE_FIELD_NAME;
    if (SECRET_SHAPED_NAME_PATTERN.test(name)) return UNPRINTABLE_FIELD_NAME;
    for (const pattern of SECRET_VALUE_PATTERNS) {
        if (pattern.test(name)) return UNPRINTABLE_FIELD_NAME;
    }
    return name;
}

// Anchored on this file rather than on the process's working directory: cwd is
// chosen by whoever ran the command, and containment checks anchored on a
// directory the caller can pick prove nothing.
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
        if (parent === candidate) throw new LiveCredentialError('could not locate the repository root, so a credential file cannot be proven to be outside it');
        candidate = parent;
    }
}

function assertLocationIsAllowed(resolved, label) {
    const root = repositoryRoot();
    const relative = path.relative(root, resolved);
    if (relative === '' || (!relative.startsWith('..') && !path.isAbsolute(relative))) {
        throw new LiveCredentialError(`${label} must not live inside the repository; a credential file is never part of it`);
    }
    for (const segment of resolved.split(path.sep)) {
        if (EVIDENCE_DIRECTORY_PATTERN.test(segment)) {
            throw new LiveCredentialError(`${label} must not live inside an evidence directory; evidence is sealed and shared, and a credential file in one would be published with it`);
        }
    }
}

// Deliberately duplicated from the target identity reader rather than shared:
// the two files have different rules, and a shared reader would mean a change
// made for one of them silently changes the other's guarantees.
//
// `O_NOFOLLOW` refuses a symlink in the final component -- the component the
// operator names.  Parent components are not walked: a symlinked parent is
// ordinary on Linux, and the file is read once and re-checked afterwards
// instead.  Ownership is not checked either; the permission bits already
// establish that nobody but the owner can reach the file, and a shared
// credential owned by a deploy user is a legitimate arrangement.
function readOnceAsRestrictedRegularFile(resolved, { label, maxBytes }) {
    let descriptor;
    try {
        descriptor = fs.openSync(resolved, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW);
    } catch (error) {
        // The path is not secret and is what the operator needs to see; the
        // file's contents never appear in any message this module builds.
        throw new LiveCredentialError(`${label} could not be opened as a regular file that is not a symbolic link`);
    }
    try {
        const before = fs.fstatSync(descriptor);
        if (!before.isFile()) throw new LiveCredentialError(`${label} must be a regular file`);
        if (before.size === 0) throw new LiveCredentialError(`${label} is empty`);
        if (before.size > maxBytes) throw new LiveCredentialError(`${label} exceeds the ${maxBytes} byte limit for this file`);
        if ((before.mode & 0o077) !== 0) throw new LiveCredentialError(`${label} must not be readable or writable by group or other; 0600 or stricter is required`);
        const bytes = fs.readFileSync(descriptor);
        const after = fs.fstatSync(descriptor);
        // A pathname is re-resolved by the kernel at open time, so the file that
        // was measured and the file that was read can differ.  What was read is
        // trusted only once it is known to be the same object, at the same size,
        // with the same modification time, as the one that was checked.
        if (after.dev !== before.dev || after.ino !== before.ino || after.size !== before.size || after.mtimeMs !== before.mtimeMs) {
            throw new LiveCredentialError(`${label} changed while it was being read; a partially read credential is refused`);
        }
        return bytes;
    } finally {
        fs.closeSync(descriptor);
    }
}

function credentialValue(value, field) {
    if (typeof value !== 'string' || value === '') throw new LiveCredentialError(`credential field ${field} must be a non-empty string`);
    if (value !== value.trim()) throw new LiveCredentialError(`credential field ${field} must not carry surrounding whitespace`);
    if (value.length > MAX_CREDENTIAL_VALUE_LENGTH) throw new LiveCredentialError(`credential field ${field} exceeds the ${MAX_CREDENTIAL_VALUE_LENGTH} character limit`);
    // eslint-disable-next-line no-control-regex
    if (/[\x00-\x1f\x7f]/.test(value)) throw new LiveCredentialError(`credential field ${field} must not contain control characters`);
    return value;
}

function parseCredentialDocument(text) {
    let raw;
    try {
        raw = JSON.parse(text);
    } catch (error) {
        // The parser's message quotes the input it choked on, and the input here
        // is a credential file.  It is replaced, never forwarded.
        throw new LiveCredentialError('credential file is not valid JSON');
    }
    if (raw === null || typeof raw !== 'object' || Array.isArray(raw)) throw new LiveCredentialError('credential file must contain a single JSON object');

    const unknown = Object.keys(raw).filter(key => !CREDENTIAL_FIELDS.includes(key));
    if (unknown.length) {
        throw new LiveCredentialError(`credential file carries fields this loader does not define, and an undefined field is refused rather than ignored: ${unknown.map(safeFieldName).join(', ')}`);
    }
    const missing = REQUIRED_CREDENTIAL_FIELDS.filter(field => !Object.prototype.hasOwnProperty.call(raw, field));
    if (missing.length) throw new LiveCredentialError(`credential file is missing required fields: ${missing.join(', ')}`);

    const accessKeyId = credentialValue(raw.accessKeyId, 'accessKeyId');
    const secretAccessKey = credentialValue(raw.secretAccessKey, 'secretAccessKey');
    const sessionToken = raw.sessionToken === undefined ? undefined : credentialValue(raw.sessionToken, 'sessionToken');

    // Frozen, so the one object that reaches the transport cannot be extended or
    // mutated after validation.
    return Object.freeze({
        accessKeyId,
        secretAccessKey,
        ...(sessionToken === undefined ? {} : { sessionToken }),
    });
}

// Explicit path in, validated frozen credentials out.  `credentialFile` has no
// default and is never resolved from the environment, a profile or a
// conventional location.
function loadLiveCredentials({ credentialFile } = {}) {
    if (typeof credentialFile !== 'string' || credentialFile.trim() === '') {
        throw new LiveCredentialError('a credential file must be supplied explicitly; this loader has no default location, no profile and no environment fallback');
    }
    const resolved = path.resolve(credentialFile);
    assertLocationIsAllowed(resolved, 'the credential file');
    const bytes = readOnceAsRestrictedRegularFile(resolved, { label: 'credential file', maxBytes: MAX_CREDENTIAL_FILE_BYTES });
    let text;
    try {
        text = bytes.toString('utf8');
    } finally {
        // The bytes this module owns are wiped as soon as they have been
        // decoded.  The decoded string cannot be wiped afterwards, because
        // JavaScript strings are immutable; that limitation is stated in the
        // module header rather than glossed over.
        bytes.fill(0);
    }
    return parseCredentialDocument(text);
}

// The only thing about a credential that may appear in a report, a log line or
// an evidence file.  Deliberately excludes the values and the file path: a path
// to secret material is itself a pointer worth not publishing.
function describeCredentialPresence(credentials) {
    if (credentials === null || typeof credentials !== 'object') throw new LiveCredentialError('describeCredentialPresence requires a credentials object');
    return Object.freeze({
        credential_source: 'EXPLICIT_FILE',
        implicit_discovery: false,
        session_token_present: credentials.sessionToken !== undefined,
    });
}

module.exports = {
    loadLiveCredentials,
    describeCredentialPresence,
    parseCredentialDocument,
    LiveCredentialError,
    CREDENTIAL_FIELDS,
    MAX_CREDENTIAL_FILE_BYTES,
    MAX_CREDENTIAL_VALUE_LENGTH,
};
