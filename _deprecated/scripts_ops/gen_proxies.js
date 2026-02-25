/**
 * V86.100 Proxy Generator - Convert proxy list to JSON format
 * =============================================================
 *
 * Purpose: Convert raw proxy list to proxies.json format for Turbo Pipeline
 *
 * Input formats supported:
 *   - Comma-separated: "http://proxy1:port,http://proxy2:port"
 *   - Newline-separated (file)
 *   - Array format: [["host", "port", "user", "pass"], ...]
 *
 * Output: proxies.json with structured format
 *
 * @usage: node scripts/ops/gen_proxies.js
 * @author High-Performance Systems Architect
 * @version V86.100
 * @since 2026-01-26
 */

'use strict';

const fs = require('fs');
const path = require('path');

// ============================================================================
// CONFIGURATION
// ============================================================================

const CONFIG = {
    // Output file path
    outputPath: path.join(__dirname, 'proxies.json'),

    // Sample proxy list (replace with your actual proxies)
    sampleProxies: [
        // Format 1: HTTP proxy without auth
        'http://proxy1.example.com:8080',
        'http://proxy2.example.com:8080',
        'http://proxy3.example.com:8080',

        // Format 2: HTTP proxy with auth
        'http://user:pass@proxy4.example.com:8080',
        'http://user:pass@proxy5.example.com:8080',

        // Format 3: SOCKS5 proxy
        'socks5://proxy6.example.com:1080',

        // Format 4: IP:Port format
        '192.168.1.100:8080',
        '192.168.1.101:8080',
    ]
};

// ============================================================================
// PROXY PARSER
// ============================================================================

/**
 * Parse various proxy formats into structured object
 * @param {string} proxyStr - Proxy string
 * @returns {Object|null} - Structured proxy object
 */
function parseProxyString(proxyStr) {
    const trimmed = proxyStr.trim();

    if (!trimmed) return null;

    // Format: IP:Port (no protocol)
    const ipPortMatch = trimmed.match(/^(\d+\.\d+\.\d+\.\d+):(\d+)$/);
    if (ipPortMatch) {
        return {
            server: `http://${trimmed}`,
            host: ipPortMatch[1],
            port: parseInt(ipPortMatch[2]),
            protocol: 'http',
            username: undefined,
            password: undefined
        };
    }

    // Format: protocol://host:port or protocol://user:pass@host:port
    try {
        const url = new URL(trimmed);

        return {
            server: trimmed,
            host: url.hostname,
            port: parseInt(url.port) || (url.protocol === 'https:' ? 443 : 80),
            protocol: url.protocol.replace(':', ''),
            username: url.username || undefined,
            password: url.password || undefined
        };
    } catch (e) {
        console.warn(`[WARN] Invalid proxy format: ${trimmed}`);
        return null;
    }
}

/**
 * Parse array format: [["host", "port", "user", "pass"], ...]
 * @param {Array} proxyArray - Array of proxy arrays
 * @returns {Array} - Array of structured proxy objects
 */
function parseProxyArray(proxyArray) {
    const result = [];

    for (const item of proxyArray) {
        if (!Array.isArray(item)) continue;

        const [host, port, username, password] = item;

        if (!host || !port) continue;

        const proxyStr = username
            ? `http://${username}:${password}@${host}:${port}`
            : `http://${host}:${port}`;

        const parsed = parseProxyString(proxyStr);
        if (parsed) result.push(parsed);
    }

    return result;
}

// ============================================================================
// MAIN GENERATOR
// ============================================================================

/**
 * Generate proxies.json from various input sources
 */
function generateProxyConfig() {
    console.log('=== V86.100 Proxy Generator ===\n');

    // Get input from various sources
    let proxies = [];

    // 1. Check environment variable
    if (process.env.PROXY_LIST) {
        console.log('[Source] Environment variable PROXY_LIST');
        const envProxies = process.env.PROXY_LIST.split(',').map(p => parseProxyString(p)).filter(p => p);
        proxies.push(...envProxies);
    }

    // 2. Check command line arguments
    if (process.argv.length > 2) {
        console.log('[Source] Command line arguments');
        const cliProxies = process.argv.slice(2).map(p => parseProxyString(p)).filter(p => p);
        proxies.push(...cliProxies);
    }

    // 3. Check for proxy list file
    const proxyListPath = path.join(__dirname, 'proxy_list.txt');
    if (fs.existsSync(proxyListPath)) {
        console.log('[Source] proxy_list.txt file');
        const fileContent = fs.readFileSync(proxyListPath, 'utf-8');
        const lines = fileContent.split('\n').map(line => line.trim()).filter(line => line && !line.startsWith('#'));
        const fileProxies = lines.map(p => parseProxyString(p)).filter(p => p);
        proxies.push(...fileProxies);
    }

    // 4. Use sample proxies if no input provided
    if (proxies.length === 0) {
        console.log('[Source] Built-in sample proxies (replace with your actual proxies)');
        proxies = CONFIG.sampleProxies.map(p => parseProxyString(p)).filter(p => p);
    }

    // Deduplicate by server URL
    const uniqueProxies = [];
    const seenServers = new Set();

    for (const proxy of proxies) {
        if (!seenServers.has(proxy.server)) {
            seenServers.add(proxy.server);
            uniqueProxies.push(proxy);
        }
    }

    // Validate minimum requirement
    const minProxies = 20;
    if (uniqueProxies.length < minProxies) {
        console.warn(`\n[WARN] Only ${uniqueProxies.length} proxies found. Minimum recommended: ${minProxies}`);
        console.warn('[WARN] Please add more proxies to achieve optimal performance.\n');
    }

    // Generate output structure
    const output = {
        version: 'V86.100',
        generatedAt: new Date().toISOString(),
        count: uniqueProxies.length,
        proxies: uniqueProxies.map((p, idx) => ({
            id: `proxy_${idx + 1}`,
            ...p
        }))
    };

    // Write to file
    fs.writeFileSync(CONFIG.outputPath, JSON.stringify(output, null, 2));

    console.log(`\n[Output] Generated ${CONFIG.outputPath}`);
    console.log(`[Status] ${output.count} proxies validated and saved\n`);

    // Display proxy list
    console.log('='.repeat(60));
    console.log('Proxy List:');
    console.log('='.repeat(60));

    output.proxies.forEach((p, idx) => {
        const auth = p.username ? ` (${p.username}:****)` : '';
        console.log(`${(idx + 1).toString().padStart(2)}. ${p.server}${auth}`);
    });

    console.log('='.repeat(60));
    console.log(`\n[INFO] Turbo Pipeline will use ${Math.min(output.count, 20)} workers`);
    console.log('[INFO] Workers will be assigned proxies in round-robin fashion\n');

    return output;
}

// ============================================================================
// TEMPLATE GENERATOR
// ============================================================================

/**
 * Generate a template proxy_list.txt file for user to fill in
 */
function generateTemplate() {
    const templatePath = path.join(__dirname, 'proxy_list_template.txt');

    const template = `# V86.100 Turbo Pipeline - Proxy List Template
# ================================================
#
# Add your proxies here (one per line)
#
# Supported formats:
#   http://proxy.example.com:8080
#   http://username:password@proxy.example.com:8080
#   socks5://proxy.example.com:1080
#   192.168.1.100:8080
#
# Lines starting with # are comments
#

# HTTP Proxies (without authentication)
http://proxy1.example.com:8080
http://proxy2.example.com:8080
http://proxy3.example.com:8080

# HTTP Proxies (with authentication)
http://user:pass@proxy4.example.com:8080
http://user:pass@proxy5.example.com:8080

# SOCKS5 Proxies
socks5://proxy6.example.com:1080

# IP:Port format
192.168.1.100:8080
192.168.1.101:8080

# Add more proxies below to reach 20+ for optimal performance
`;

    if (!fs.existsSync(templatePath)) {
        fs.writeFileSync(templatePath, template);
        console.log(`\n[INFO] Template file created: ${templatePath}`);
        console.log('[INFO] Edit this file and run: node gen_proxies.js\n');
    }
}

// ============================================================================
// MAIN ENTRY
// ============================================================================

(async () => {
    try {
        // Generate template if it doesn't exist
        generateTemplate();

        // Generate proxy configuration
        generateProxyConfig();

        process.exit(0);
    } catch (error) {
        console.error(`[ERROR] ${error.message}`);
        process.exit(1);
    }
})();
