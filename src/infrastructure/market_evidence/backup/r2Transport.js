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

const {
    S3Client,
    PutObjectCommand,
    GetObjectCommand,
    HeadObjectCommand,
    ListObjectsV2Command,
} = require('@aws-sdk/client-s3');

const { ObjectAlreadyExistsError, SnapshotIntegrityError, TransportContractError } = require('./transport');
const { canonicalizeKey } = require('./localTransport');

const R2_TRANSPORT_VERSION = 'stage-d-r2-s3-transport/v1';

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

function createR2Transport({ endpoint, bucket, region, credentials = null, prefix = '', client = null, forcePathStyle = true } = {}) {
    const resolvedEndpoint = assertNonEmptyString(endpoint, 'endpoint');
    const resolvedBucket = assertNonEmptyString(bucket, 'bucket');
    const resolvedRegion = assertNonEmptyString(region, 'region');
    if (prefix !== '' && typeof prefix !== 'string') throw new TransportContractError('prefix must be a string when supplied');
    const normalizedPrefix = prefix.replace(/^\/+|\/+$/g, '');

    // Credentials are validated unconditionally, before any client exists.
    //
    // An injected client is a seam for the command mechanics, never a way to
    // bring a different credential source.  Validating only on the branch that
    // builds its own client would leave the guarantee conditional: a caller
    // could hand in a client backed by the SDK's default provider chain, and
    // the transport would then have no explicit-credential claim left to make.
    // "Refuses to construct without injected credentials" has to hold on every
    // path or it does not hold.
    const resolvedCredentials = assertExplicitCredentials(credentials);

    let resolvedClient = client;
    if (resolvedClient === null) {
        resolvedClient = new S3Client({
            endpoint: resolvedEndpoint,
            region: resolvedRegion,
            forcePathStyle,
            credentials: resolvedCredentials,
        });
    } else if (typeof resolvedClient.send !== 'function') {
        throw new TransportContractError('an injected client must expose send()');
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
            let continuationToken;
            do {
                const target = normalizedPrefix ? `${normalizedPrefix}/${listPrefix}` : listPrefix;
                const response = await resolvedClient
                    .send(new ListObjectsV2Command({ Bucket: resolvedBucket, Prefix: target, ContinuationToken: continuationToken }))
                    .catch(error => { throw classify('listObjects', error); });
                for (const item of response.Contents || []) results.push(Object.freeze({ key: item.Key, size: item.Size }));
                continuationToken = response.IsTruncated ? response.NextContinuationToken : undefined;
            } while (continuationToken);
            return Object.freeze(results);
        },

        describe() {
            // Deliberately excludes credentials: this object is safe to
            // serialize into a report or an error envelope.
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
            });
        },
    };
}

module.exports = { createR2Transport, R2_TRANSPORT_VERSION, isPreconditionFailure, isNotFound };
