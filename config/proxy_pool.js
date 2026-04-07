'use strict';

const fs = require('node:fs');
const path = require('node:path');

const PROXY_POOL_PATH = path.resolve(__dirname, 'proxy_pool.json');
const DEFAULT_PROTOCOL = 'http';
const DEFAULT_HOST = '127.0.0.1';

function parseProxyPorts(value) {
    if (Array.isArray(value)) {
        return value
            .map(port => Number(port))
            .filter(port => Number.isInteger(port) && port > 0);
    }

    if (typeof value !== 'string' || value.trim() === '') {
        return [];
    }

    return value
        .split(',')
        .map(port => Number(port.trim()))
        .filter(port => Number.isInteger(port) && port > 0);
}

function expandPortRange(start, end) {
    const rangeStart = Number(start);
    const rangeEnd = Number(end);

    if (!Number.isInteger(rangeStart) || !Number.isInteger(rangeEnd) || rangeEnd < rangeStart) {
        return [];
    }

    return Array.from({ length: (rangeEnd - rangeStart) + 1 }, (_, index) => rangeStart + index);
}

function extractHost(serverTemplate = '') {
    const match = String(serverTemplate).match(/^https?:\/\/([^/:]+)/i);
    return match?.[1] || null;
}

function readProxyPoolFile() {
    try {
        const raw = fs.readFileSync(PROXY_POOL_PATH, 'utf8');
        const data = JSON.parse(raw);
        if (!data || typeof data !== 'object' || Array.isArray(data)) {
            return {};
        }
        return data;
    } catch {
        return {};
    }
}

function resolveProxyPoolConfig(env = process.env) {
    const fileConfig = readProxyPoolFile();
    const protocol = env.PROXY_PROTOCOL || fileConfig.protocol || DEFAULT_PROTOCOL;

    const envPorts = parseProxyPorts(env.PROXY_PORTS);
    const rangePorts = envPorts.length === 0
        ? expandPortRange(env.PROXY_PORT_START, env.PROXY_PORT_END)
        : [];
    const filePorts = parseProxyPorts(fileConfig.ports);
    const candidatePorts = envPorts.length > 0
        ? envPorts
        : (rangePorts.length > 0 ? rangePorts : filePorts);

    const fileServerTemplate = typeof fileConfig.serverTemplate === 'string'
        ? fileConfig.serverTemplate
        : '';
    const configuredServerTemplate = env.PROXY_SERVER || fileServerTemplate;
    const host = env.WSL2_PROXY_HOST
        || env.PROXY_HOST
        || extractHost(configuredServerTemplate)
        || fileConfig.host
        || DEFAULT_HOST;

    const defaultPortCandidate = Number(
        env.PROXY_PORT
        || fileConfig.defaultPort
        || candidatePorts[0]
        || 0
    );
    const defaultPort = Number.isInteger(defaultPortCandidate) && defaultPortCandidate > 0
        ? defaultPortCandidate
        : 0;
    const ports = candidatePorts.length > 0
        ? [...candidatePorts]
        : (defaultPort > 0 ? [defaultPort] : []);
    const serverTemplate = configuredServerTemplate || `${protocol}://${host}:{port}`;

    return {
        protocol,
        host,
        ports,
        defaultPort: defaultPort || ports[0] || 0,
        serverTemplate,
        configPath: PROXY_POOL_PATH
    };
}

function buildProxyServer(port, options = {}) {
    const config = options.config || resolveProxyPoolConfig(options.env);
    const hasExplicitHost = Object.prototype.hasOwnProperty.call(options, 'host');
    const hasExplicitProtocol = Object.prototype.hasOwnProperty.call(options, 'protocol');
    const serverTemplate = options.serverTemplate
        || (!hasExplicitHost && !hasExplicitProtocol ? config.serverTemplate : '');
    if (serverTemplate && serverTemplate.includes('{port}')) {
        return serverTemplate.replace('{port}', String(Number(port)));
    }

    const protocol = options.protocol || config.protocol || DEFAULT_PROTOCOL;
    const host = options.host || config.host || DEFAULT_HOST;
    return `${protocol}://${host}:${Number(port)}`;
}

module.exports = {
    PROXY_POOL_PATH,
    buildProxyServer,
    extractHost,
    parseProxyPorts,
    readProxyPoolFile,
    resolveProxyPoolConfig
};
