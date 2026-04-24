/* eslint-disable complexity, max-lines */
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const PROXY_POOL_PATH = path.resolve(__dirname, 'proxy_pool.json');
const PROXY_POOLS_PATH = path.resolve(__dirname, 'proxy_pools.json');
const DEFAULT_PROTOCOL = 'socks5';
const DEFAULT_PREFERRED_HOST = '127.0.0.1';
const DEFAULT_HOST = DEFAULT_PREFERRED_HOST;
const DEFAULT_POOL_NAME = 'default';

function normalizeHost(value) {
    return typeof value === 'string' && value.trim() !== ''
        ? value.trim()
        : '';
}

function normalizeProxyProtocol(value) {
    const protocol = String(value || '').trim().toLowerCase();
    if (protocol === 'socks5h') {
        return 'socks5';
    }

    return protocol || DEFAULT_PROTOCOL;
}

function isLegacyBridgeHost(value) {
    const host = normalizeHost(value);
    if (!host) {
        return false;
    }

    const parts = host.split('.').map(part => Number(part));
    return parts.length === 4
        && parts.every(part => Number.isInteger(part) && part >= 0 && part <= 255)
        && parts[0] === 172
        && parts[1] === 25
        && parts[2] === 16
        && parts[3] === 1;
}

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
    const match = String(serverTemplate).match(/^(?:https?|socks5h?):\/\/([^/:]+)/i);
    return match?.[1] || null;
}

function parsePositiveNumber(value) {
    const parsed = Number(value);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : undefined;
}

function normalizePoolName(value) {
    return typeof value === 'string' && value.trim() !== ''
        ? value.trim()
        : DEFAULT_POOL_NAME;
}

function readJsonFile(filePath) {
    try {
        const raw = fs.readFileSync(filePath, 'utf8');
        const data = JSON.parse(raw);
        if (!data || typeof data !== 'object' || Array.isArray(data)) {
            return {};
        }
        return data;
    } catch {
        return {};
    }
}

function selectPoolConfig(rawConfig, poolName) {
    if (!rawConfig || typeof rawConfig !== 'object' || Array.isArray(rawConfig)) {
        return null;
    }

    if (Array.isArray(rawConfig.active_ports) || Array.isArray(rawConfig.ports)) {
        return rawConfig;
    }

    const normalizedPoolName = normalizePoolName(poolName);
    const selected = rawConfig[normalizedPoolName] || rawConfig[DEFAULT_POOL_NAME] || null;
    return selected && typeof selected === 'object' && !Array.isArray(selected)
        ? selected
        : null;
}

function readProxyPoolFile(poolName = DEFAULT_POOL_NAME) {
    const normalizedPoolName = normalizePoolName(poolName);
    const multiPoolConfig = selectPoolConfig(readJsonFile(PROXY_POOLS_PATH), normalizedPoolName);
    if (multiPoolConfig) {
        return {
            ...multiPoolConfig,
            poolName: normalizedPoolName,
            configPath: PROXY_POOLS_PATH
        };
    }

    return {
        ...readJsonFile(PROXY_POOL_PATH),
        poolName: normalizedPoolName,
        configPath: PROXY_POOL_PATH
    };
}

function resolveProxyPoolConfig(env = process.env, options = {}) {
    const normalizedOptions = typeof options === 'string'
        ? { poolName: options }
        : (options || {});
    const poolName = normalizePoolName(
        normalizedOptions.poolName
        || env.PROXY_POOL_NAME
        || DEFAULT_POOL_NAME
    );
    const radarMode = String(env.PROXY_RADAR_MODE || '').toLowerCase() === 'true';
    const fileConfig = readProxyPoolFile(poolName);
    const protocol = normalizeProxyProtocol(env.PROXY_PROTOCOL || fileConfig.protocol || DEFAULT_PROTOCOL);
    const explicitServerTemplate = typeof env.PROXY_SERVER === 'string' && env.PROXY_SERVER.trim() !== ''
        ? env.PROXY_SERVER.trim()
        : '';

    const envPorts = parseProxyPorts(env.PROXY_PORTS);
    const rangePorts = envPorts.length === 0
        ? expandPortRange(env.PROXY_PORT_START, env.PROXY_PORT_END)
        : [];

    const hardcodedPorts = Array.from({ length: 40 }, (_, i) => 10001 + i);

    const fileActivePorts = parseProxyPorts(fileConfig.active_ports);
    const filePorts = fileActivePorts.length > 0
        ? fileActivePorts
        : parseProxyPorts(fileConfig.ports);
    const candidatePorts = radarMode
        ? []
        : (envPorts.length > 0
            ? envPorts
            : (rangePorts.length > 0 ? rangePorts : (filePorts.length > 0 ? filePorts : hardcodedPorts)));

    const fileServerTemplate = typeof fileConfig.serverTemplate === 'string'
        ? fileConfig.serverTemplate
        : '';
    const configuredServerTemplate = explicitServerTemplate || fileServerTemplate;
    const fileHost = normalizeHost(fileConfig.host);
    const host = normalizeHost(env.PROXY_HOST)
        || normalizeHost(extractHost(explicitServerTemplate))
        || (isLegacyBridgeHost(fileHost) ? '' : fileHost)
        || DEFAULT_PREFERRED_HOST
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
    const hasExplicitHost = normalizeHost(env.PROXY_HOST);
    const serverTemplate = configuredServerTemplate && !hasExplicitHost
        ? configuredServerTemplate
        : `${protocol}://${host}:{port}`;

    return {
        poolName,
        protocol,
        host,
        ports,
        activePorts: ports,
        defaultPort: defaultPort || ports[0] || 0,
        serverTemplate,
        configPath: fileConfig.configPath || PROXY_POOL_PATH,
        radarMode,
        healthCheckIntervalMs: parsePositiveNumber(fileConfig.healthCheckIntervalMs),
        failureThreshold: parsePositiveNumber(fileConfig.failureThreshold),
        failureCooldownMs: parsePositiveNumber(fileConfig.failureCooldownMs),
        http503ObservationThreshold: parsePositiveNumber(fileConfig.http503ObservationThreshold),
        http503CooldownMs: parsePositiveNumber(fileConfig.http503CooldownMs),
        heartbeatFailureCooldownMs: parsePositiveNumber(fileConfig.heartbeatFailureCooldownMs),
        criticalErrorCooldownMs: parsePositiveNumber(fileConfig.criticalErrorCooldownMs),
        rateLimitIsolationMs: parsePositiveNumber(fileConfig.rateLimitIsolationMs),
        minHealthScore: parsePositiveNumber(fileConfig.minHealthScore),
        healthProbeMode: typeof fileConfig.healthProbeMode === 'string'
            ? fileConfig.healthProbeMode
            : undefined
    };
}

function buildProxyServer(port, options = {}) {
    const config = options.config || resolveProxyPoolConfig(options.env, { poolName: options.poolName });
    const hasExplicitHost = Object.prototype.hasOwnProperty.call(options, 'host');
    const hasExplicitProtocol = Object.prototype.hasOwnProperty.call(options, 'protocol');
    const serverTemplate = options.serverTemplate
        || (!hasExplicitHost && !hasExplicitProtocol ? config.serverTemplate : '');
    if (serverTemplate && serverTemplate.includes('{port}')) {
        return serverTemplate.replace('{port}', String(Number(port)));
    }

    const protocol = normalizeProxyProtocol(options.protocol || config.protocol || DEFAULT_PROTOCOL);
    const host = options.host || config.host || DEFAULT_HOST;
    return `${protocol}://${host}:${Number(port)}`;
}

module.exports = {
    PROXY_POOL_PATH,
    PROXY_POOLS_PATH,
    buildProxyServer,
    extractHost,
    isLegacyBridgeHost,
    normalizeProxyProtocol,
    normalizePoolName,
    parseProxyPorts,
    readProxyPoolFile,
    resolveProxyPoolConfig
};
