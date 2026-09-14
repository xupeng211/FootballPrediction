'use strict';

// S3-compatible transport for the future off-host backup target.
//
// Signing is delegated entirely to @aws-sdk/client-s3.  No Signature V4
// logic is written here: canonical-request construction, signing-key
// derivation and credential signing are all provider-supplied.  That is a
// deliberate architecture decision, not an omission.
//
// What this module refuses to do:
//   - discover credentials.  There is no environment fallback, no ~/.aws
//     fallback, no instance-metadata fallback and no default provider chain.
//     The SDK ships a credential-provider chain; this transport never lets it
//     run, because an executor that silently picks up ambient credentials
//     cannot be reasoned about.  Credentials are injected or the transport
//     refuses to construct.
//   - delete.  There is no delete verb in the transport contract, so none is
//     implemented here.
//   - administer.  Bucket creation, bucket locks, lifecycle rules and the
//     Cloudflare REST API are all out of scope.  This transport speaks S3 to
//     one bucket and nothing else.
//   - run at import time.  Constructing the module performs no I/O and no
//     network access; a client is built only when the caller asks for one.

const { ObjectAlreadyExistsError, SnapshotIntegrityError, TransportContractError } = require('./transport');
const { canonicalizeKey } = require('./localTransport');

const R2_TRANSPORT_VERSION = 'stage-d-r2-s3-transport/v1';

// @aws-sdk/client-s3 is linked on demand, not at import time.  Requiring this
// module must not pull the network client into the process: a caller that only
// wants to inspect the transport's surface, or a test that asserts the SDK is
// absent, would otherwise link the very dependency the on-demand boundary
// exists to keep out.  Only constructing a transport -- the one thing a caller
// has to ask for by name -- links it.
let s3Sdk = null;
function loadS3Sdk() {
    if (s3Sdk === null) s3Sdk = require('@aws-sdk/client-s3');
    return s3Sdk;
}

function assertNonEmptyString(value, label) {
    if (typeof value !== 'string' || !value.trim()) throw new TransportContractError(`${label} is required and must be supplied explicitly`);
    return value;
}

// A precondition failure means the key already exists.  R2 and S3 both report
// this as 412; some proxies surface 409.  Anything else is a real failure and
// must not be silently reinterpreted as "already exists", because swallowing a
// genuine write error as a benign collision would lose a generation.
function isPreconditionFailure(error) {
    const status = error && error.$metadata ? error.$metadata.httpStatusCode : undefined;
    if (status === 412 || status === 409) return true;
    return error && (error.name === 'PreconditionFailed' || error.name === 'ConditionalRequestConflict');
}

function isNotFound(error) {
    const status = error && error.$metadata ? error.$metadata.httpStatusCode : undefined;
    return status === 404 || (error && (error.name === 'NotFound' || error.name === 'NoSuchKey'));
}

// Errors are rebuilt from provider-supplied identifiers only.  Nothing from the
// client configuration is interpolated, so a secret cannot reach a message, a
// stack trace assembled here, or a report.
function describeAwsError(error, operation) {
    const name = error && typeof error.name === 'string' ? error.name : 'UnknownError';
    const status = error && error.$metadata && error.$metadata.httpStatusCode !== undefined ? ` status=${error.$metadata.httpStatusCode}` : '';
    return `${operation} failed: ${name}${status}`;
}

// Three fields, one shape, two credential classes.  A long-lived R2 API token
// and a temporary credential both arrive as an access key id plus a secret; a
// temporary credential additionally carries a session token, and that is the
// only difference this transport can see.  It deliberately does not classify
// them further: the provider's and the operator's models of what a credential
// may do are not decidable from its bytes, and a transport that guessed would be
// reporting a scope it never checked.  Whatever is injected here is passed
// straight to the SDK, which is the only component that knows how to sign with
// a session token; nothing is added to the credential on the way.
function assertExplicitCredentials(credentials) {
    if (credentials === null || typeof credentials !== 'object') throw new TransportContractError('credentials must be injected explicitly; no environment or profile fallback exists');
    assertNonEmptyString(credentials.accessKeyId, 'credentials.accessKeyId');
    assertNonEmptyString(credentials.secretAccessKey, 'credentials.secretAccessKey');
    if (credentials.sessionToken !== undefined) assertNonEmptyString(credentials.sessionToken, 'credentials.sessionToken');
    const frozen = Object.freeze({
        accessKeyId: credentials.accessKeyId,
        secretAccessKey: credentials.secretAccessKey,
        ...(credentials.sessionToken === undefined ? {} : { sessionToken: credentials.sessionToken }),
    });
    return frozen;
}

const REQUIRED_SDK_MEMBERS = Object.freeze([
    'S3Client',
    'PutObjectCommand',
    'GetObjectCommand',
    'HeadObjectCommand',
    'ListObjectsV2Command',
]);

// The seam is the SDK *surface*, never a client instance.  A caller-supplied
// client could be backed by the SDK's default provider chain, and validating
// the `credentials` argument would prove nothing about it: the transport would
// be sending through a credential source it cannot name while reporting
// `credential_source: INJECTED_EXPLICIT`.  Handing over the classes instead
// keeps the client construction where it can be reasoned about -- this module
// always builds its own client from the credentials it has already validated,
// and there is no path that reaches a client it did not build.
function assertInjectedSdk(sdk) {
    if (sdk === null || typeof sdk !== 'object') throw new TransportContractError('an injected SDK surface must be an object');
    for (const member of REQUIRED_SDK_MEMBERS) {
        if (typeof sdk[member] !== 'function') throw new TransportContractError(`an injected SDK surface must provide ${member}`);
    }
    return sdk;
}

function createR2Transport({ endpoint, bucket, region, credentials = null, prefix = '', sdk = null, client = null, forcePathStyle = true } = {}) {
    const resolvedEndpoint = assertNonEmptyString(endpoint, 'endpoint');
    const resolvedBucket = assertNonEmptyString(bucket, 'bucket');
    const resolvedRegion = assertNonEmptyString(region, 'region');
    if (prefix !== '' && typeof prefix !== 'string') throw new TransportContractError('prefix must be a string when supplied');
    const normalizedPrefix = prefix.replace(/^\/+|\/+$/g, '');

    // Credentials are validated unconditionally, before any client exists.
    // "Refuses to construct without injected credentials" has to hold on every
    // path or it does not hold, so this runs before anything else can decide
    // what to build.
    const resolvedCredentials = assertExplicitCredentials(credentials);

    // A client instance is refused outright rather than ignored.  Accepting one
    // is what made the credential guarantee unprovable; ignoring one silently
    // would be worse still, because the caller would believe their client was
    // in use.  Constructing the transport is the only supported way.
    if (client !== null && client !== undefined) {
        throw new TransportContractError('a client instance is not accepted; this transport builds its own client from the injected credentials');
    }

    // Linked here rather than at import time.  Requiring this module must not
    // pull the network client into the process, and a test may supply the
    // surface directly.
    const {
        S3Client,
        PutObjectCommand,
        GetObjectCommand,
        HeadObjectCommand,
        ListObjectsV2Command,
    } = sdk === null ? loadS3Sdk() : assertInjectedSdk(sdk);

    // The one client this transport will ever send through, built here from the
    // credentials validated above.  `credentials` is passed explicitly, so the
    // SDK's provider chain is never consulted -- there is nothing left for it
    // to discover.
    const resolvedClient = new S3Client({
        endpoint: resolvedEndpoint,
        region: resolvedRegion,
        forcePathStyle,
        credentials: resolvedCredentials,
    });
    if (resolvedClient === null || typeof resolvedClient !== 'object' || typeof resolvedClient.send !== 'function') {
        throw new TransportContractError('the SDK surface must produce a client exposing send()');
    }

    const objectKey = key => (normalizedPrefix ? `${normalizedPrefix}/${canonicalizeKey(key)}` : canonicalizeKey(key));
    const classify = (operation, error) => {
        if (isPreconditionFailure(error)) return new ObjectAlreadyExistsError(operation);
        const wrapped = new SnapshotIntegrityError(describeAwsError(error, operation));
        wrapped.cause = undefined;
        return wrapped;
    };

    return {
        async putObjectCreateOnly({ key, bytes } = {}) {
            if (!Buffer.isBuffer(bytes)) throw new SnapshotIntegrityError('putObjectCreateOnly requires a Buffer');
            const target = objectKey(key);
            try {
                // If-None-Match: * is the atomic create-only condition.  The
                // existence check and the write are one server-side operation,
                // so a HEAD-then-PUT emulation is never used: that pattern is
                // race-prone and would let two writers both believe they
                // created the same generation.
                await resolvedClient.send(new PutObjectCommand({ Bucket: resolvedBucket, Key: target, Body: bytes, IfNoneMatch: '*' }));
            } catch (error) {
                if (isPreconditionFailure(error)) throw new ObjectAlreadyExistsError(target);
                throw classify('putObjectCreateOnly', error);
            }
            return Object.freeze({ key: target, size: bytes.length });
        },

        async getObject({ key } = {}) {
            const target = objectKey(key);
            try {
                const response = await resolvedClient.send(new GetObjectCommand({ Bucket: resolvedBucket, Key: target }));
                const bytes = await response.Body.transformToByteArray();
                return Buffer.from(bytes);
            } catch (error) {
                if (isNotFound(error)) return null;
                throw classify('getObject', error);
            }
        },

        async headObject({ key } = {}) {
            const target = objectKey(key);
            try {
                const response = await resolvedClient.send(new HeadObjectCommand({ Bucket: resolvedBucket, Key: target }));
                return Object.freeze({ key: target, size: response.ContentLength, etag: response.ETag });
            } catch (error) {
                if (isNotFound(error)) return null;
                throw classify('headObject', error);
            }
        },

        async listObjects({ prefix: listPrefix = '' } = {}) {
            const results = [];
            // Every other method on this transport speaks logical keys, and so
            // do the manifest and the verifier: putObjectCreateOnly maps a
            // logical key onto `<prefix>/<key>`, getObject and headObject map
            // it back, and the manifest records the logical one.  Listing is
            // the one place the provider forces a physical key on us, so the
            // configured prefix is stripped here rather than leaked outward.
            // Leaking it would make the verifier's exact set comparison report
            // every object as unexpected *and* every expected object as
            // missing, so a prefixed transport could never verify a generation
            // it had just written itself.
            const scope = normalizedPrefix ? `${normalizedPrefix}/` : '';
            let continuationToken;
            do {
                const target = `${scope}${listPrefix}`;
                const response = await resolvedClient
                    .send(new ListObjectsV2Command({ Bucket: resolvedBucket, Prefix: target, ContinuationToken: continuationToken }))
                    .catch(error => { throw classify('listObjects', error); });
                for (const item of response.Contents || []) {
                    if (typeof item.Key !== 'string') continue;
                    // Defensive: a provider that returns something outside the
                    // scope we asked for is not evidence about this generation.
                    if (scope && !item.Key.startsWith(scope)) continue;
                    results.push(Object.freeze({ key: scope ? item.Key.slice(scope.length) : item.Key, size: item.Size }));
                }
                continuationToken = response.IsTruncated ? response.NextContinuationToken : undefined;
            } while (continuationToken);
            return Object.freeze(results);
        },

        describe() {
            // Deliberately excludes credentials: this object is safe to
            // serialize into a report or an error envelope.  Whether a session
            // token is present is reported, because it changes which credential
            // class the run used and that belongs in an evidence record; the
            // token itself is not, because it is a secret.
            return Object.freeze({
                kind: 'r2-s3',
                version: R2_TRANSPORT_VERSION,
                create_only: true,
                delete_exposed: false,
                bucket: resolvedBucket,
                endpoint: resolvedEndpoint,
                region: resolvedRegion,
                prefix: normalizedPrefix,
                credentials_injected: true,
                credential_source: 'INJECTED_EXPLICIT',
                environment_fallback: false,
                session_token_present: resolvedCredentials.sessionToken !== undefined,
            });
        },
    };
}

module.exports = { createR2Transport, R2_TRANSPORT_VERSION, isPreconditionFailure, isNotFound };
