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

// Two providers, each a target class this path has been adjudicated for.  A
// closed enum is a stronger statement than a validated string: adding an entry
// is a design decision rather than a configuration value, which is why this list
// is short and why each member carries its own endpoint rule below.
const ALLOWED_PROVIDERS = Object.freeze(['cloudflare-r2', 'self-hosted-s3']);

// Region vocabularies are per provider, not one flat union.  R2's S3 API takes
// `auto`; the self-hosted class takes `us-east-1`, which is the region this
// lineage of server reports and signs for.  The distinction matters because the
// region reaches the signature: `auto` is meaningless to a self-hosted server
// and `us-east-1` is not an R2 region, so a flat union would admit the two pairs
// that name no real target -- a request signed for one target and addressed to
// another.  With one provider a flat list was harmless; with two it is a defect.
const PROVIDER_REGIONS = Object.freeze({
    'cloudflare-r2': Object.freeze(['auto']),
    'self-hosted-s3': Object.freeze(['us-east-1']),
});

// Kept as the union, for a caller that wants to know which region strings exist
// at all.  It is deliberately NOT what an identity is validated against: the
// per-provider map above is, so the union cannot be used to admit a cross pair.
const ALLOWED_REGIONS = Object.freeze([...new Set(Object.values(PROVIDER_REGIONS).flat())]);

// R2's S3 endpoint is an account subdomain of this one registrable domain.  A
// request signed for R2 and sent anywhere else is a request aimed at a target
// nobody adjudicated, so the endpoint is bound to the provider that names it.
const R2_ENDPOINT_SUFFIX = '.r2.cloudflarestorage.com';

// Address ranges that only ever name a host on a network its operator already
// controls.  A self-hosted target must be addressed by a literal address in one
// of these, for two independent reasons:
//
//   * It cannot be loopback.  A loopback address IS the current machine, so a
//     "backup" written to one shares the exact failure domain it exists to
//     survive.  Loopback is refused with its own message below, because that is
//     the failure worth naming precisely.
//   * It cannot be publicly routable.  This is what keeps the class honest: a
//     self-hosted provider can only name a private host, so adding this class
//     cannot turn the live backup path into a way to ship production bytes to an
//     arbitrary public destination.
//
// The category is "not globally routable", which is the property all five ranges
// actually share and the property the rule needs.  It is deliberately NOT called
// "private-use": only 10/8, 172.16/12 and 192.168/16 are RFC 1918 private-use,
// while 100.64/10 is CGNAT (RFC 6598) and 169.254/16 is link-local (RFC 3927).
// A message that named the wrong category would send an operator looking for a
// rule that does not exist.
//
// Addresses are matched only as literals.  A DNS name is refused even when it
// looks private, because resolving one is a network call this loader must not
// make -- and a name it cannot resolve is a destination it cannot check.  The
// rule is narrower than "an operator may only use their own host", which is not
// something a loader can establish; what it establishes is the network the
// address sits in, and that is all it claims.
const NON_PUBLIC_IPV4_RANGES = Object.freeze([
    Object.freeze({ cidr: '10.0.0.0/8', first: 0x0a000000, mask: 0xff000000 }),
    Object.freeze({ cidr: '100.64.0.0/10', first: 0x64400000, mask: 0xffc00000 }),
    Object.freeze({ cidr: '169.254.0.0/16', first: 0xa9fe0000, mask: 0xffff0000 }),
    Object.freeze({ cidr: '172.16.0.0/12', first: 0xac100000, mask: 0xfff00000 }),
    Object.freeze({ cidr: '192.168.0.0/16', first: 0xc0a80000, mask: 0xffff0000 }),
]);

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

// R2's documented bucket rules: 3-63 characters, lowercase letters, digits and
// hyphens, beginning and ending alphanumeric.
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
    // An IPv6 authority is refused here rather than in a provider class,
    // because no class in this loader admits one: the R2 class requires a name
    // under its registrable domain and the self-hosted class requires an IPv4
    // literal.  It is refused before the dot test below, which would otherwise
    // reject `[fd00::1]` for containing no dot and report it as an unqualified
    // NAME -- a wrong diagnosis for an address that is fully qualified and
    // simply not an admitted form.
    if (parsed.hostname.startsWith('[')) {
        throw new LiveTargetIdentityError('target identity field endpoint must not be an IPv6 endpoint; an IPv6 endpoint is not admitted by any provider class here, so it is refused rather than admitted as an unchecked form');
    }
    // A bare hostname is refused: `https://localhost` or `https://r2` addresses
    // whatever the resolver happens to answer, which is exactly the ambiguity a
    // live target must not have.
    if (!parsed.hostname.includes('.')) throw new LiveTargetIdentityError('target identity field endpoint must name a fully qualified host');
    return { origin: parsed.origin, rawHostname: rawHostnameOf(text) };
}

// The host exactly as the identity file spells it, before the URL parser has
// rewritten it.  Everything else in this loader works from the parsed origin,
// where a non-canonical spelling has already been silently replaced; a check
// that the text and the parsed address agree needs the text.
//
// The scheme, userinfo, query, fragment and path are all rejected or constrained
// before this is called, so the authority is the segment between `://` and the
// first `/`, `?` or `#`.  The userinfo strip is kept as a guard rather than a
// live branch: it must not become the thing that decides which host is read.
function rawHostnameOf(text) {
    const afterScheme = text.slice(text.indexOf('://') + 3);
    const end = afterScheme.search(/[/?#]/);
    let authority = end === -1 ? afterScheme : afterScheme.slice(0, end);
    const at = authority.lastIndexOf('@');
    if (at !== -1) authority = authority.slice(at + 1);
    if (authority.startsWith('[')) {
        const close = authority.indexOf(']');
        return close === -1 ? authority : authority.slice(0, close + 1);
    }
    const colon = authority.indexOf(':');
    return colon === -1 ? authority : authority.slice(0, colon);
}

// A literal dotted quad, or null.  Only the canonical spelling is accepted, and
// in practice this function never sees anything else: the URL parser has already
// rewritten the host by the time it runs, so the non-canonical forms below never
// arrive here to be rejected.
//
// What this function is guarded by is the raw-spelling comparison in
// `assertSelfHostedEndpoint`, which runs first.  The parser does NOT leave a
// non-canonical spelling alone: it reads the octets of `192.168.011.070` as
// OCTAL and rewrites the host to `192.168.9.56`, and it reads the short form
// `192.168.11` as a 24-bit tail and rewrites it to `192.168.0.11`.  Both
// rewrites land inside a private range, so the range test below would admit
// them and the transport would dial a host the identity file does not name.
// That comparison is the only thing that can catch them, because by the time the
// address is a number the rewrite is invisible.
function parseIpv4Literal(hostname) {
    const parts = hostname.split('.');
    if (parts.length !== 4) return null;
    let value = 0;
    for (const part of parts) {
        if (!/^(?:0|[1-9][0-9]{0,2})$/.test(part)) return null;
        const octet = Number(part);
        if (octet > 255) return null;
        value = (value * 256) + octet;
    }
    return value;
}

function assertSelfHostedEndpoint(endpoint, rawHostname) {
    const host = new URL(endpoint).hostname;
    // The address must be written as the literal it denotes.  This is the one
    // rule that catches the URL parser's legacy IPv4 forms, and it is only
    // checkable here, where the raw spelling is still available: by the time the
    // origin is parsed, `192.168.011.070` is already `192.168.9.56` and the
    // rewrite is invisible.  That rewrite is the reason the rule exists -- the
    // spelling reads as one host and dials another, and this class exists to
    // prove which physical host receives the backup.
    //
    // It is stated only for this class.  A DNS name is case-insensitive by
    // definition, so requiring text equality there would refuse spellings that
    // legitimately denote one name; a literal has exactly one canonical
    // spelling, so requiring it costs nothing honest.
    // The message names the rule and restates neither the spelling nor the
    // address the spelling resolves to, because no field value is echoed in an
    // error and this is the rule it is most tempting to make an exception for:
    // the whole point is which host the spelling dials.  It stays out.  The
    // message is what reaches a log or an evidence file, and what names a target
    // there is the fingerprint, not the endpoint -- the one field this class
    // exists to pin to a physical host.
    if (rawHostname !== host) {
        throw new LiveTargetIdentityError('target identity field endpoint must be written as the IPv4 literal it denotes for provider self-hosted-s3; the WHATWG legacy IPv4 forms are refused because this parser resolves them to a host other than the one they read as, so the field would name one host while the transport dials another');
    }
    const value = parseIpv4Literal(host);
    if (value === null) {
        throw new LiveTargetIdentityError('target identity field endpoint must be a literal private IPv4 address for provider self-hosted-s3; a DNS name is refused because resolving one is a network call this loader does not make, and a name it cannot resolve is a destination it cannot check');
    }
    // Loopback is checked before the range test and reported separately: it
    // would fail the range test anyway, but "not private enough" is the wrong
    // diagnosis for the one address that is the current machine.
    // `>>> 0` is load-bearing rather than decorative.  A bitwise operator in
    // JavaScript produces a SIGNED 32-bit result, so every range whose high bit
    // is set -- 172.16/12, 192.168/16, 169.254/16 -- would otherwise be compared
    // as a negative number against a positive constant and never match, refusing
    // exactly the addresses the rule exists to admit.  The boundary test in
    // live_target_identity.test.js is what caught it; without that test the
    // happy path would have looked correct while the class admitted nothing.
    if (((value & 0xff000000) >>> 0) === 0x7f000000) {
        throw new LiveTargetIdentityError('target identity field endpoint must not be a loopback address for provider self-hosted-s3; a loopback target is the current machine, which shares the failure domain an off-host target exists to survive');
    }
    if (!NON_PUBLIC_IPV4_RANGES.some(range => ((value & range.mask) >>> 0) === range.first)) {
        throw new LiveTargetIdentityError('target identity field endpoint must be an address in a range that is not globally routable (10/8, 100.64/10, 169.254/16, 172.16/12, 192.168/16) for provider self-hosted-s3; a publicly routable endpoint is refused so this class cannot address a destination outside the operator\'s own network');
    }
    return host;
}

// The endpoint is checked against the provider it was declared with.  This is
// required by the second provider rather than optional alongside it: while the
// enum held one member, "the endpoint belongs to the declared provider" was
// trivially true of every endpoint that passed the origin rules, so leaving it
// unstated cost nothing.  With two members it stops being true, and an unbound
// endpoint means a request signed for one target can be sent to another.
function assertEndpointBelongsToProvider(endpoint, provider, rawHostname) {
    const host = new URL(endpoint).hostname;
    if (provider === 'cloudflare-r2') {
        // A suffix test, not `includes`: a host that merely CONTAINS the
        // provider's domain -- `account.r2.cloudflarestorage.com.attacker.example`
        // -- ends somewhere else and is refused.  The bare registrable domain is
        // also refused, because R2 addresses an account subdomain and a host with
        // no account label names no target.
        //
        // The length test refuses the other spelling of "no account label": a
        // leading dot leaves an empty first label, and `.r2.cloudflarestorage.com`
        // ends with the suffix and is not the bare domain, so it passes both of
        // the tests above while naming no account -- the same defect the bare
        // domain is refused for.  It is a length test rather than a label-count
        // test because more than one label is legitimate: a virtual-hosted-style
        // endpoint puts the bucket in front of the account id.
        if (host === R2_ENDPOINT_SUFFIX.slice(1) || !host.endsWith(R2_ENDPOINT_SUFFIX) || host.length === R2_ENDPOINT_SUFFIX.length) {
            throw new LiveTargetIdentityError(`target identity field endpoint must be an account host under ${R2_ENDPOINT_SUFFIX} for provider ${provider}; an endpoint belonging to another provider, or to no provider, is refused rather than addressed`);
        }
        return;
    }
    assertSelfHostedEndpoint(endpoint, rawHostname);
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

    const { origin: endpoint, rawHostname } = validateEndpoint(raw.endpoint);

    const bucket = stringField(raw.bucket, 'bucket');
    if (!BUCKET_PATTERN.test(bucket)) throw new LiveTargetIdentityError('target identity field bucket must be 3-63 characters of lowercase letters, digits and hyphens, beginning and ending alphanumeric');

    const region = stringField(raw.region, 'region');
    const allowedRegions = PROVIDER_REGIONS[provider];
    if (!allowedRegions.includes(region)) throw new LiveTargetIdentityError(`target identity field region must be one of: ${allowedRegions.join(', ')} for provider ${provider}`);

    // After both are known, because it reads the pair rather than either half.
    // The endpoint decides where the request goes and the region decides what
    // the signature says, so a mismatched pair aims a signed request at a
    // destination the identity did not name.
    assertEndpointBelongsToProvider(endpoint, provider, rawHostname);

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
