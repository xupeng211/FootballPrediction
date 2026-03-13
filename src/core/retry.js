/**
 * V66.000 - Retry Mechanism
 * ===========================
 *
 * Industrial-grade retry logic with exponential backoff, jitter, and circuit breaker.
 * @module core/retry
 * @author Principal Software Architect
 * @version V66.000
 * @since 2026-01-25
 */

'use strict';

// V4.46.5 HARDENING: 使用确定性 ID 生成器（零模拟铁律）
const { generateDeterministicId } = require('./id_generator');

// ============================================================================
// CONFIGURATION
// ============================================================================

const RETRY_CONFIG = {
    // Exponential backoff settings
    baseDelay: parseInt(process.env.RETRY_BASE_DELAY) || 500,        // 500ms
    maxDelay: parseInt(process.env.RETRY_MAX_DELAY) || 10000,       // 10s
    backoffMultiplier: parseFloat(process.env.RETRY_MULTIPLIER) || 2,

    // Jitter settings (to prevent thundering herd)
    jitterEnabled: process.env.RETRY_JITTER !== 'false',
    jitterRange: 0.1,  // ±10% variation

    // Retry limits
    maxRetries: parseInt(process.env.RETRY_MAX_ATTEMPTS) || 3,

    // Circuit breaker settings
    circuitBreakerThreshold: parseInt(process.env.CIRCUIT_THRESHOLD) || 5,
    circuitBreakerTimeout: parseInt(process.env.CIRCUIT_TIMEOUT) || 60000,  // 1 minute
};

// ============================================================================
// ERROR CLASS
// ============================================================================

/**
 *
 */
class RetryError extends Error {
    /**
     *
     * @param code
     * @param message
     * @param traceId
     * @param context
     */
    constructor(code, message, traceId = null, context = {}) {
        super(message);
        this.name = 'RetryError';
        this.errorCode = code;
        this.traceId = traceId || generateTraceId();
        this.timestamp = new Date().toISOString();
        this.context = context;
    }

    /**
     *
     */
    toJSON() {
        return {
            error_code: this.errorCode,
            trace_id: this.traceId,
            timestamp: this.timestamp,
            message: this.message,
            context: this.context
        };
    }

    /**
     *
     */
    toString() {
        return JSON.stringify(this.toJSON());
    }
}

// ============================================================================
// TRACE ID GENERATOR - V4.46.5: 使用确定性生成器
// ============================================================================

// generateTraceId 已移至 src/core/id_generator.js，此处使用别名
/**
 *
 */
function generateTraceId() {
    return generateDeterministicId('trace');
}

// ============================================================================
// CIRCUIT BREAKER
// ============================================================================

/**
 * V66.000: Circuit Breaker Pattern
 *
 * Prevents cascading failures by stopping execution after repeated failures.
 */
class CircuitBreaker {
    /**
     * @param {number} threshold - Failure count threshold
     * @param {number} timeout - Reset timeout in milliseconds
     */
    constructor(threshold = RETRY_CONFIG.circuitBreakerThreshold,
                timeout = RETRY_CONFIG.circuitBreakerTimeout) {
        this.threshold = threshold;
        this.timeout = timeout;
        this.failureCount = 0;
        this.lastFailureTime = null;
        this.state = 'CLOSED';  // CLOSED, OPEN, HALF_OPEN
        this.traceId = generateTraceId();
    }

    /**
     * Check if circuit is open (blocked)
     * @returns {boolean} - True if circuit is open
     */
    isOpen() {
        const now = Date.now();

        // Auto-reset after timeout
        if (this.state === 'OPEN' && this.lastFailureTime) {
            if (now - this.lastFailureTime >= this.timeout) {
                this.state = 'HALF_OPEN';
                this._log('info', 'Circuit breaker auto-reset to HALF_OPEN');
            }
        }

        return this.state === 'OPEN';
    }

    /**
     * Record a successful attempt
     */
    recordSuccess() {
        this.failureCount = 0;
        if (this.state === 'HALF_OPEN') {
            this.state = 'CLOSED';
            this._log('info', 'Circuit breaker closed after successful attempt');
        }
    }

    /**
     * Record a failed attempt
     */
    recordFailure() {
        this.failureCount++;
        this.lastFailureTime = Date.now();

        if (this.failureCount >= this.threshold) {
            this.state = 'OPEN';
            this._log('warn', 'Circuit breaker opened', {
                failureCount: this.failureCount,
                threshold: this.threshold
            });
        }
    }

    /**
     * Reset the circuit breaker
     */
    reset() {
        this.failureCount = 0;
        this.lastFailureTime = null;
        this.state = 'CLOSED';
        this._log('info', 'Circuit breaker manually reset');
    }

    /**
     * Get current state
     * @returns {object} - State information
     */
    getState() {
        return {
            state: this.state,
            failureCount: this.failureCount,
            threshold: this.threshold,
            lastFailureTime: this.lastFailureTime
        };
    }

    /**
     * Internal logging
     * @param level
     * @param message
     * @param data
     * @private
     */
    _log(level, message, data = {}) {
        const logEntry = {
            level,
            trace_id: this.traceId,
            module: 'core/retry/circuit-breaker',
            message,
            ...data,
            timestamp: new Date().toISOString()
        };
        console.log(JSON.stringify(logEntry));
    }
}

// ============================================================================
// RETRY POLICY
// ============================================================================

/**
 * V66.000: Retry Policy with Exponential Backoff
 *
 * Implements sophisticated retry logic with jitter and configurable policies.
 */
class RetryPolicy {
    /**
     * @param {object} [config] - Configuration overrides
     */
    constructor(config = {}) {
        this.config = { ...RETRY_CONFIG, ...config };
        this.circuitBreaker = new CircuitBreaker(
            this.config.circuitBreakerThreshold,
            this.config.circuitBreakerTimeout
        );
        this.traceId = generateTraceId();
    }

    /**
     * Calculate delay with exponential backoff and jitter
     * @param {number} attempt - Current attempt number (0-based)
     * @returns {number} - Delay in milliseconds
     */
    calculateDelay(attempt) {
        // Exponential backoff: baseDelay * (multiplier ^ attempt)
        let delay = this.config.baseDelay * Math.pow(this.config.backoffMultiplier, attempt);

        // Cap at max delay
        delay = Math.min(delay, this.config.maxDelay);

        // Add jitter if enabled
        if (this.config.jitterEnabled) {
            const jitterRange = delay * this.config.jitterRange;
            const jitter = (Math.random() * 2 - 1) * jitterRange;  // ±jitterRange
            delay = delay + jitter;
        }

        return Math.max(0, Math.floor(delay));
    }

    /**
     * Execute function with retry logic
     * @template T
     * @param {function(): Promise<T>} fn - Async function to execute
     * @param {object} [options] - Execution options
     * @returns {Promise<T>} - Function result
     */
    async execute(fn, options = {}) {
        const maxRetries = options.maxRetries ?? this.config.maxRetries;
        const onRetry = options.onRetry || null;

        // Check circuit breaker
        if (this.circuitBreaker.isOpen()) {
            throw new RetryError(
                'CIRCUIT_OPEN',
                'Circuit breaker is open, refusing to execute',
                this.traceId,
                this.circuitBreaker.getState()
            );
        }

        let lastError = null;
        let attempt = 0;

        while (attempt <= maxRetries) {
            try {
                const result = await fn();

                // Record success on circuit breaker
                this.circuitBreaker.recordSuccess();

                this._log('debug', 'Execution succeeded', {
                    attempt,
                    maxRetries
                });

                return result;

            } catch (error) {
                lastError = error;

                // Check if error is retryable
                if (!this._isRetryable(error) || attempt === maxRetries) {
                    this.circuitBreaker.recordFailure();
                    throw error;
                }

                // Calculate delay
                const delay = this.calculateDelay(attempt);

                this._log('warn', 'Execution failed, retrying', {
                    attempt: attempt + 1,
                    maxRetries: maxRetries + 1,
                    delay,
                    error: error.message
                });

                // Call retry callback if provided
                if (onRetry) {
                    await onRetry(error, attempt + 1, delay);
                }

                // Wait before retry
                await this._sleep(delay);

                attempt++;
            }
        }

        // Should not reach here, but handle anyway
        this.circuitBreaker.recordFailure();
        throw lastError;
    }

    /**
     * Execute multiple functions concurrently with retry isolation
     * @template T
     * @param {Array<function(): Promise<T>>} functions - Array of async functions
     * @param {object} [options] - Execution options
     * @returns {Promise<Array<T>>} - Array of results
     */
    async executeAll(functions, options = {}) {
        const results = await Promise.allSettled(
            functions.map(fn => this.execute(fn, options))
        );

        return results.map((result, index) => {
            if (result.status === 'fulfilled') {
                return result.value;
            }
            throw new RetryError(
                'BATCH_PARTIAL_FAILURE',
                `Function at index ${index} failed`,
                this.traceId,
                { index, error: result.reason.message }
            );
        });
    }

    /**
     * Check if error is retryable
     * @private
     * @param {Error} error - Error to check
     * @returns {boolean} - True if retryable
     */
    _isRetryable(error) {
        // Non-retryable errors
        const nonRetryableErrors = [
            'CIRCUIT_OPEN',
            'VALIDATION_FAILED',
            'AUTHENTICATION_FAILED',
            'PERMISSION_DENIED'
        ];

        if (error.errorCode && nonRetryableErrors.includes(error.errorCode)) {
            return false;
        }

        // Network errors are generally retryable
        const retryablePatterns = [
            /ECONNREFUSED/i,
            /ETIMEDOUT/i,
            /ENOTFOUND/i,
            /ECONNRESET/i,
            /timeout/i,
            /network/i,
            /Temporary failure/i
        ];

        return retryablePatterns.some(pattern =>
            pattern.test(error.message) || pattern.test(error.code)
        );
    }

    /**
     * Sleep for specified milliseconds
     * @private
     * @param {number} ms - Milliseconds to sleep
     * @returns {Promise<void>}
     */
    _sleep(ms) {
        return new Promise(resolve => { setTimeout(resolve, ms); });
    }

    /**
     * Get circuit breaker state
     * @returns {object} - Circuit breaker state
     */
    getCircuitBreakerState() {
        return this.circuitBreaker.getState();
    }

    /**
     * Reset circuit breaker
     */
    resetCircuitBreaker() {
        this.circuitBreaker.reset();
    }

    /**
     * Internal logging
     * @param level
     * @param message
     * @param data
     * @private
     */
    _log(level, message, data = {}) {
        const logEntry = {
            level,
            trace_id: this.traceId,
            module: 'core/retry/policy',
            message,
            ...data,
            timestamp: new Date().toISOString()
        };
        console.log(JSON.stringify(logEntry));
    }
}

// ============================================================================
// FACTORY FUNCTION
// ============================================================================

/**
 * Create a retry policy with custom configuration
 * @param {object} [config] - Configuration overrides
 * @returns {RetryPolicy} - New retry policy instance
 */
function createRetryPolicy(config) {
    return new RetryPolicy(config);
}

/**
 * Execute function with default retry policy
 * @template T
 * @param {function(): Promise<T>} fn - Async function to execute
 * @param {object} [options] - Retry options
 * @returns {Promise<T>} - Function result
 */
async function withRetry(fn, options = {}) {
    const policy = createRetryPolicy(options);
    return policy.execute(fn, options);
}

// ============================================================================
// DECORATOR (for class methods)
// ============================================================================

/**
 * Retry decorator for class methods
 * @param {object} [options] - Retry options
 * @returns {function} - Decorator function
 */
function retryDecorator(options = {}) {
    return function(target, propertyKey, descriptor) {
        const originalMethod = descriptor.value;

        descriptor.value = async function(...args) {
            const policy = createRetryPolicy(options);
            return policy.execute(() => originalMethod.apply(this, args), options);
        };

        return descriptor;
    };
}

// ============================================================================
// EXPORTS
// ============================================================================

module.exports = {
    RetryPolicy,
    CircuitBreaker,
    RetryError,
    generateTraceId,
    createRetryPolicy,
    withRetry,
    retryDecorator,
    RETRY_CONFIG
};
