/**
 * V66.000 - Browser Pool Management
 * =================================
 *
 * Core browser lifecycle management with defensive programming and resource cleanup.
 *
 * @module core/browser
 * @author Principal Software Architect
 * @version V66.000
 * @since 2026-01-25
 */

'use strict';

const { chromium } = require('playwright');
const v8 = require('v8');

// ============================================================================
// CONFIGURATION
// ============================================================================

const BROWSER_CONFIG = {
    // Pool settings
    maxPoolSize: parseInt(process.env.BROWSER_POOL_MAX) || 5,
    minPoolSize: parseInt(process.env.BROWSER_POOL_MIN) || 1,

    // Context settings
    headless: process.env.HEADLESS !== 'false',
    viewport: { width: 1920, height: 1080 },
    userAgent: process.env.USER_AGENT || 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',

    // Timeout settings
    defaultTimeout: parseInt(process.env.BROWSER_TIMEOUT) || 30000,
    navigationTimeout: parseInt(process.env.NAVIGATION_TIMEOUT) || 60000,

    // Resource cleanup
    cleanupOnExit: true,
    gracefulShutdownTimeout: 10000
};

// ============================================================================
// ERROR CLASS
// ============================================================================

class BrowserError extends Error {
    constructor(code, message, traceId = null, context = {}) {
        super(message);
        this.name = 'BrowserError';
        this.errorCode = code;
        this.traceId = traceId || generateTraceId();
        this.timestamp = new Date().toISOString();
        this.context = context;
    }

    toJSON() {
        return {
            error_code: this.errorCode,
            trace_id: this.traceId,
            timestamp: this.timestamp,
            message: this.message,
            context: this.context
        };
    }

    toString() {
        return JSON.stringify(this.toJSON());
    }
}

// ============================================================================
// TRACE ID GENERATOR
// ============================================================================

function generateTraceId() {
    return `trace_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
}

// ============================================================================
// BROWSER POOL CLASS
// ============================================================================

/**
 * V66.000: Browser Pool Manager
 *
 * Manages a pool of browser contexts with automatic resource cleanup.
 * Ensures all resources are properly released on shutdown.
 */
class BrowserPool {
    /**
     * @param {Object} [config={}] - Configuration overrides
     */
    constructor(config = {}) {
        this.config = { ...BROWSER_CONFIG, ...config };
        this.browser = null;
        this.contexts = new Map();
        this.isInitialized = false;
        this.isShuttingDown = false;
        this.traceId = generateTraceId();

        // Register shutdown handlers
        this._registerShutdownHandlers();
    }

    /**
     * Initialize the browser pool
     * @returns {Promise<void>}
     */
    async initialize() {
        if (this.isInitialized) {
            return;
        }

        try {
            this.browser = await chromium.launch({
                headless: this.config.headless,
                timeout: this.config.defaultTimeout
            });

            this.isInitialized = true;

            this._log('info', 'Browser pool initialized', {
                headless: this.config.headless,
                maxPoolSize: this.config.maxPoolSize
            });

        } catch (error) {
            throw new BrowserError(
                'BROWSER_INIT_FAILED',
                `Failed to initialize browser: ${error.message}`,
                this.traceId,
                { originalError: error.message }
            );
        }
    }

    /**
     * Acquire a browser context from the pool
     * @param {Object} [options={}] - Context options
     * @returns {Promise<import('@playwright/test').BrowserContext>}
     */
    async acquireContext(options = {}) {
        if (!this.isInitialized) {
            await this.initialize();
        }

        if (this.isShuttingDown) {
            throw new BrowserError(
                'POOL_SHUTTING_DOWN',
                'Cannot acquire context during shutdown',
                this.traceId
            );
        }

        // Check pool size limit
        if (this.contexts.size >= this.config.maxPoolSize) {
            throw new BrowserError(
                'POOL_EXHAUSTED',
                `Maximum pool size (${this.config.maxPoolSize}) reached`,
                this.traceId,
                { currentSize: this.contexts.size }
            );
        }

        try {
            const context = await this.browser.newContext({
                viewport: this.config.viewport,
                userAgent: this.config.userAgent,
                ...options
            });

            // Set default timeout
            context.setDefaultTimeout(this.config.defaultTimeout);

            // Track context
            const contextId = generateTraceId();
            this.contexts.set(contextId, context);

            this._log('info', 'Context acquired', {
                contextId,
                poolSize: this.contexts.size
            });

            // Attach cleanup handler to context
            context.on('close', () => {
                this.contexts.delete(contextId);
                this._log('debug', 'Context released', {
                    contextId,
                    poolSize: this.contexts.size
                });
            });

            return context;

        } catch (error) {
            throw new BrowserError(
                'CONTEXT_ACQUIRE_FAILED',
                `Failed to acquire context: ${error.message}`,
                this.traceId,
                { originalError: error.message }
            );
        }
    }

    /**
     * Get current pool statistics
     * @returns {Object} Pool statistics
     */
    getStats() {
        return {
            isInitialized: this.isInitialized,
            isShuttingDown: this.isShuttingDown,
            activeContexts: this.contexts.size,
            maxPoolSize: this.config.maxPoolSize,
            utilization: this.contexts.size / this.config.maxPoolSize
        };
    }

    /**
     * Graceful shutdown - closes all contexts and browser
     * @returns {Promise<void>}
     */
    async shutdown() {
        if (this.isShuttingDown) {
            return;
        }

        this.isShuttingDown = true;
        this._log('info', 'Starting graceful shutdown', {
            activeContexts: this.contexts.size
        });

        const startTime = Date.now();

        try {
            // Close all contexts with timeout
            const closePromises = Array.from(this.contexts.values()).map(context =>
                Promise.race([
                    context.close(),
                    new Promise(resolve => setTimeout(resolve, this.config.gracefulShutdownTimeout))
                ])
            );

            await Promise.allSettled(closePromises);
            this.contexts.clear();

            // Close browser
            if (this.browser) {
                await this.browser.close();
                this.browser = null;
            }

            this.isInitialized = false;

            const duration = Date.now() - startTime;
            this._log('info', 'Shutdown complete', { duration });

        } catch (error) {
            this._log('error', 'Shutdown error', {
                error: error.message
            });
        } finally {
            this.isShuttingDown = false;
        }
    }

    /**
     * Force immediate shutdown (emergency)
     * @returns {Promise<void>}
     */
    async forceShutdown() {
        this._log('warn', 'Force shutdown initiated');

        try {
            // Clear all context references
            this.contexts.clear();

            // Force close browser
            if (this.browser) {
                await this.browser.close();
                this.browser = null;
            }

            this.isInitialized = false;
            this.isShuttingDown = false;

        } catch (error) {
            // Ignore errors during force shutdown
        }
    }

    /**
     * Register process shutdown handlers
     * @private
     */
    _registerShutdownHandlers() {
        const shutdownHandler = async () => {
            if (this.config.cleanupOnExit) {
                await this.shutdown();
            }
        };

        process.on('SIGINT', shutdownHandler);
        process.on('SIGTERM', shutdownHandler);
        process.on('beforeExit', shutdownHandler);
    }

    /**
     * Internal logging with structured output
     * @private
     */
    _log(level, message, data = {}) {
        const logEntry = {
            level,
            trace_id: this.traceId,
            module: 'core/browser',
            message,
            ...data,
            timestamp: new Date().toISOString()
        };

        // In production, send to proper logger
        // For now, use console with structured format
        const logLine = JSON.stringify(logEntry);

        switch (level) {
            case 'error':
                console.error(logLine);
                break;
            case 'warn':
                console.warn(logLine);
                break;
            case 'info':
                console.info(logLine);
                break;
            default:
                console.log(logLine);
        }
    }
}

// ============================================================================
// SINGLETON INSTANCE
// ============================================================================

let globalPool = null;

/**
 * Get global browser pool singleton
 * @param {Object} [config] - Configuration for first initialization
 * @returns {BrowserPool} - Global pool instance
 */
function getGlobalPool(config) {
    if (!globalPool) {
        globalPool = new BrowserPool(config);
    }
    return globalPool;
}

/**
 * Cleanup global pool
 * @returns {Promise<void>}
 */
async function cleanupGlobalPool() {
    if (globalPool) {
        await globalPool.shutdown();
        globalPool = null;
    }
}

// ============================================================================
// EXPORTS
// ============================================================================

module.exports = {
    BrowserPool,
    BrowserError,
    generateTraceId,
    getGlobalPool,
    cleanupGlobalPool,
    BROWSER_CONFIG
};
