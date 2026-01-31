/**
 * V66.000 - Configuration Validation Tests
 * ==========================================
 *
 * Unit tests for configuration loading and validation.
 * Tests provider configuration integrity.
 *
 * @file config.test.js
 * @version V66.000
 */

'use strict';

const { describe, it } = require('node:test');
const assert = require('assert');
const fs = require('fs');
const path = require('path');

// ============================================================================
// CONFIGURATION VALIDATOR
// ============================================================================

/**
 * Validate provider configuration
 * @param {Object} config - Configuration object
 * @returns {Object} - Validation result with errors
 */
function validateConfig(config) {
    const errors = [];
    const warnings = [];

    if (!config.version) {
        errors.push('Missing version field');
    }

    if (!config.providers || !Array.isArray(config.providers)) {
        errors.push('Missing or invalid providers array');
        return { valid: false, errors, warnings };
    }

    if (config.providers.length !== 5) {
        errors.push(`Expected 5 providers, found ${config.providers.length}`);
    }

    const providerIds = new Set();
    const providerNames = new Set();

    config.providers.forEach((provider, index) => {
        if (!provider.id) {
            errors.push(`Provider at index ${index}: missing id`);
        }
        if (!provider.name) {
            errors.push(`Provider at index ${index}: missing name`);
        }
        if (!provider.selector_pattern) {
            errors.push(`Provider at index ${index}: missing selector_pattern`);
        }
        if (provider.priority === undefined) {
            errors.push(`Provider at index ${index}: missing priority`);
        }
        if (provider.enabled === undefined) {
            errors.push(`Provider at index ${index}: missing enabled flag`);
        }

        if (provider.id && providerIds.has(provider.id)) {
            errors.push(`Duplicate provider id: ${provider.id}`);
        }
        if (provider.id) {
            providerIds.add(provider.id);
        }

        if (provider.name && providerNames.has(provider.name)) {
            errors.push(`Duplicate provider name: ${provider.name}`);
        }
        if (provider.name) {
            providerNames.add(provider.name);
        }

        if (provider.name && !/^Provider_[A-E]$/.test(provider.name)) {
            warnings.push(`Provider ${provider.id}: name should follow Provider_X format`);
        }
    });

    if (!config.collection_settings) {
        errors.push('Missing collection_settings');
    }

    if (!config.validation_rules) {
        errors.push('Missing validation_rules');
    }

    return {
        valid: errors.length === 0,
        errors,
        warnings
    };
}

// ============================================================================
// TEST SUITE
// ============================================================================

describe('Configuration Validation Tests', () => {

    describe('loadConfig', () => {

        it('should load configuration from file', () => {
            const configPath = path.join(__dirname, '../src/config/providers.json');
            const configData = fs.readFileSync(configPath, 'utf-8');
            const config = JSON.parse(configData);

            assert.ok(config);
            assert.ok(config.version);
            assert.ok(Array.isArray(config.providers));
        });

        it('should load exactly 5 providers', () => {
            const configPath = path.join(__dirname, '../src/config/providers.json');
            const configData = fs.readFileSync(configPath, 'utf-8');
            const config = JSON.parse(configData);

            assert.strictEqual(config.providers.length, 5);
        });

        it('should have all providers using Provider_X naming', () => {
            const configPath = path.join(__dirname, '../src/config/providers.json');
            const configData = fs.readFileSync(configPath, 'utf-8');
            const config = JSON.parse(configData);

            const expectedNames = ['Provider_A', 'Provider_B', 'Provider_C', 'Provider_D', 'Provider_E'];
            const actualNames = config.providers.map(p => p.name);

            expectedNames.forEach(name => {
                assert.ok(actualNames.includes(name), `Missing provider: ${name}`);
            });
        });
    });

    describe('validateConfig', () => {

        it('should pass validation for actual config file', () => {
            const configPath = path.join(__dirname, '../src/config/providers.json');
            const configData = fs.readFileSync(configPath, 'utf-8');
            const config = JSON.parse(configData);

            const result = validateConfig(config);
            assert.strictEqual(result.valid, true);
            assert.strictEqual(result.errors.length, 0);
        });

        it('should have unique provider IDs', () => {
            const configPath = path.join(__dirname, '../src/config/providers.json');
            const configData = fs.readFileSync(configPath, 'utf-8');
            const config = JSON.parse(configData);

            const ids = config.providers.map(p => p.id);
            const uniqueIds = new Set(ids);

            assert.strictEqual(ids.length, uniqueIds.size);
        });

        it('should have sequential priority values (1-5)', () => {
            const configPath = path.join(__dirname, '../src/config/providers.json');
            const configData = fs.readFileSync(configPath, 'utf-8');
            const config = JSON.parse(configData);

            const priorities = config.providers.map(p => p.priority).sort((a, b) => a - b);
            const expectedPriorities = [1, 2, 3, 4, 5];

            assert.deepStrictEqual(priorities, expectedPriorities);
        });

        it('should have all providers enabled', () => {
            const configPath = path.join(__dirname, '../src/config/providers.json');
            const configData = fs.readFileSync(configPath, 'utf-8');
            const config = JSON.parse(configData);

            const enabledCount = config.providers.filter(p => p.enabled).length;
            assert.strictEqual(enabledCount, 5);
        });
    });

    describe('Provider Coverage', () => {

        it('should include all 5 required providers (Provider_A through Provider_E)', () => {
            const configPath = path.join(__dirname, '../src/config/providers.json');
            const configData = fs.readFileSync(configPath, 'utf-8');
            const config = JSON.parse(configData);

            const requiredProviders = ['Provider_A', 'Provider_B', 'Provider_C', 'Provider_D', 'Provider_E'];
            const actualProviders = config.providers.map(p => p.name);

            requiredProviders.forEach(required => {
                assert.ok(actualProviders.includes(required), `Missing required provider: ${required}`);
            });
        });
    });

    describe('Collection Settings', () => {

        it('should have valid collection settings', () => {
            const configPath = path.join(__dirname, '../src/config/providers.json');
            const configData = fs.readFileSync(configPath, 'utf-8');
            const config = JSON.parse(configData);

            assert.ok(config.collection_settings);
            assert.ok(config.collection_settings.max_concurrent_providers > 0);
            assert.ok(config.collection_settings.human_delay_min >= 0);
            assert.ok(config.collection_settings.human_delay_max >= config.collection_settings.human_delay_min);
        });
    });

    describe('Validation Rules', () => {

        it('should have valid payout range', () => {
            const configPath = path.join(__dirname, '../src/config/providers.json');
            const configData = fs.readFileSync(configPath, 'utf-8');
            const config = JSON.parse(configData);

            assert.ok(config.validation_rules.min_payout >= 0.80);
            assert.ok(config.validation_rules.max_payout <= 1.0);
            assert.ok(config.validation_rules.min_payout < config.validation_rules.max_payout);
        });

        it('should have valid odd value range', () => {
            const configPath = path.join(__dirname, '../src/config/providers.json');
            const configData = fs.readFileSync(configPath, 'utf-8');
            const config = JSON.parse(configData);

            assert.ok(config.validation_rules.min_odd_value >= 1.0);
            assert.ok(config.validation_rules.max_odd_value > config.validation_rules.min_odd_value);
        });
    });
});

// ============================================================================
// EXPORTS
// ============================================================================

module.exports = {
    validateConfig
};
