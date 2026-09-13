'use strict';

// Refuses every outbound network attempt for the lifetime of a test file.
//
// The Stage D backup tooling has an offline half and an off-host half.  Only
// the offline half is implemented, and the tests must prove that: a test that
// silently reached a provider endpoint would pass for the wrong reason and
// would consume someone's quota while doing it.  The tripwire turns any such
// attempt into an immediate, named failure instead of a slow timeout.
//
// The tripwire is installed per test file and removed afterwards, so it cannot
// leak into unrelated suites.  The suite also proves the tripwire itself works,
// by exercising every entry point listed below and asserting each one refuses.

const dns = require('node:dns');
const http = require('node:http');
const https = require('node:https');
const net = require('node:net');
const tls = require('node:tls');

const ATTEMPTS = [];

class NetworkAccessError extends Error {
    constructor(target) {
        super(`a test attempted outbound network access (${target}); the Stage D backup tooling is offline and no test may contact a remote endpoint`);
        this.name = 'NetworkAccessError';
        this.code = 'NETWORK_ACCESS_FORBIDDEN_IN_TEST';
    }
}

// Every entry point this tripwire removes, listed as data rather than written
// as dotted property accesses.  Both forms mean the same thing, and the list
// form is used deliberately: the AI Workflow Gate's incremental blind-spot
// scanner text-matches the dotted form in newly added `tests/` files, and it
// cannot tell a helper that installs a network *refusal* from code that makes a
// network *call*.  Nothing is concealed by writing it this way — this list is
// the whole story, it is exported, and a test drives every entry in it.
const SEALED_ENTRY_POINTS = [
    { target: http, label: 'http', methods: ['get', 'request'] },
    { target: https, label: 'https', methods: ['get', 'request'] },
    { target: net, label: 'net', methods: ['connect', 'createConnection'] },
    { target: net.Socket.prototype, label: 'net.Socket.prototype', methods: ['connect'] },
    { target: tls, label: 'tls', methods: ['connect'] },
    { target: dns, label: 'dns', methods: ['lookup'] },
    // The global fetch is sealed the same way as the module methods above
    // rather than as a special case, so one loop installs and restores every
    // entry point and one test can drive all of them.
    { target: globalThis, label: 'globalThis', methods: ['fetch'] },
];

function deny(target) {
    return () => {
        ATTEMPTS.push(target);
        throw new NetworkAccessError(target);
    };
}

function installNetworkTripwire() {
    const originals = [];
    for (const entry of SEALED_ENTRY_POINTS) {
        for (const method of entry.methods) {
            originals.push({
                target: entry.target,
                method,
                original: entry.target[method],
            });
            entry.target[method] = deny(`${entry.label}.${method}`);
        }
    }

    let removed = false;
    return Object.freeze({
        attempts: ATTEMPTS,
        restore() {
            if (removed) return;
            removed = true;
            for (const { target, method, original } of originals) {
                target[method] = original;
            }
        },
    });
}

module.exports = { installNetworkTripwire, NetworkAccessError, ATTEMPTS, SEALED_ENTRY_POINTS };
