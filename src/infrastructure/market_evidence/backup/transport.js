'use strict';

// Transport contract for the Stage D independent backup.
//
// The contract is deliberately five capabilities wide.  It has no deletion
// verb, no bucket administration and no overwrite path: an accepted snapshot
// generation can only ever be added to.  Refusing overwrite is not a
// convention here, it is the only write verb the contract offers.
//
// This module must not depend on any provider account API.  A transport knows
// how to store and read bytes under a key.  It does not know what a bucket
// policy is, and it cannot be asked to change one.

const REQUIRED_TRANSPORT_METHODS = Object.freeze([
    'putObjectCreateOnly',
    'getObject',
    'headObject',
    'listObjects',
    'describe',
]);

// Presence of any of these on a transport object is a contract violation, not
// a warning.  A transport that can delete cannot be used for an immutable
// backup generation, because a bug in the writer would then be able to destroy
// the evidence the writer exists to protect.
const FORBIDDEN_TRANSPORT_METHODS = Object.freeze([
    'deleteObject',
    'deleteObjects',
    'deletePrefix',
    'deleteGeneration',
    'emptyBucket',
    'removeObject',
    'overwriteAcceptedSnapshot',
    'putObjectOverwrite',
    'createBucket',
    'deleteBucket',
    'configureBucket',
    'putBucketLock',
    'putBucketLifecycle',
    'putBucketPolicy',
]);

class TransportContractError extends Error {
    constructor(message) {
        super(message);
        this.name = 'TransportContractError';
        this.code = 'TRANSPORT_CONTRACT_VIOLATION';
    }
}

// Raised when a create-only write loses: the key already exists.  This is a
// first-class outcome rather than a generic failure, because "the generation
// already exists" and "the write broke" require different responses.
class ObjectAlreadyExistsError extends Error {
    constructor(key) {
        super(`object already exists and create-only writes never overwrite: ${key}`);
        this.name = 'ObjectAlreadyExistsError';
        this.code = 'OBJECT_ALREADY_EXISTS';
        this.key = key;
    }
}

class SnapshotIntegrityError extends Error {
    constructor(message) {
        super(message);
        this.name = 'SnapshotIntegrityError';
        this.code = 'SNAPSHOT_INTEGRITY_VIOLATION';
    }
}

function assertTransportContract(transport) {
    if (transport === null || typeof transport !== 'object') throw new TransportContractError('transport must be an object');
    for (const method of REQUIRED_TRANSPORT_METHODS) {
        if (typeof transport[method] !== 'function') throw new TransportContractError(`transport is missing required capability: ${method}`);
    }
    for (const method of FORBIDDEN_TRANSPORT_METHODS) {
        if (typeof transport[method] === 'function') throw new TransportContractError(`transport exposes a forbidden capability: ${method}`);
    }
    const described = transport.describe();
    if (described === null || typeof described !== 'object') throw new TransportContractError('transport.describe() must return an object');
    if (described.create_only !== true) throw new TransportContractError('transport must declare create_only: true');
    if (described.delete_exposed !== false) throw new TransportContractError('transport must declare delete_exposed: false');
    return transport;
}

module.exports = {
    REQUIRED_TRANSPORT_METHODS,
    FORBIDDEN_TRANSPORT_METHODS,
    TransportContractError,
    ObjectAlreadyExistsError,
    SnapshotIntegrityError,
    assertTransportContract,
};
