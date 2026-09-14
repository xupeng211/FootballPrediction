'use strict';

// Public surface of the Stage D independent backup tooling.
//
// The tooling is deliberately offline-first: nothing here reads the network,
// discovers credentials or knows a production path.  Callers supply the roots,
// the transport and the identity of the generation they mean.
//
// This module exists so the rest of the repository never has to reach into the
// individual files.  It is intentionally the only entry point imported by the
// ops CLIs, so a future change to the internal layout cannot leak outward.

const transport = require('./transport');
const localTransport = require('./localTransport');
const snapshotInputs = require('./snapshotInputs');
const snapshotManifest = require('./snapshotManifest');
const snapshotWriter = require('./snapshotWriter');
const snapshotVerifier = require('./snapshotVerifier');
const liveTargetIdentity = require('./liveTargetIdentity');
const liveCredentialLoader = require('./liveCredentialLoader');

module.exports = Object.freeze({
    ...transport,
    ...snapshotInputs,
    ...snapshotManifest,
    ...snapshotWriter,
    ...snapshotVerifier,
    ...liveTargetIdentity,
    ...liveCredentialLoader,
    createLocalTransport: localTransport.createLocalTransport,
    canonicalizeKey: localTransport.canonicalizeKey,
    sha256OfBytes: localTransport.sha256OfBytes,
    isGovernedProductionPath: localTransport.isGovernedProductionPath,
    assertNotGovernedProductionPath: localTransport.assertNotGovernedProductionPath,
    PRODUCTION_MARKERS: localTransport.PRODUCTION_MARKERS,
    // The R2 transport is loaded on demand rather than re-exported.  Requiring
    // it eagerly would pull @aws-sdk/client-s3 into every process that touches
    // this barrel, including the offline ops CLIs and the unit tests, and a
    // backup tool that links the network client it does not use is a larger
    // attack surface than the job needs.  Nothing in this mission wires it to a
    // CLI; it is reachable only by a caller that asks for it by name.
    //
    // The two live loaders above are exported eagerly by contrast, and the
    // distinction is the whole reason: they read a local file and validate it.
    // Neither links a network client, opens a socket or resolves a name, so
    // pulling them into every process that touches this barrel adds no
    // capability to the offline CLIs -- those still have no flag that can reach
    // them, and the offline CLI test asserts exactly that.
    loadR2Transport: () => require('./r2Transport'),
});
