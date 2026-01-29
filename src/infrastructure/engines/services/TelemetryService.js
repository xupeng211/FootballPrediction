/**
 * TelemetryService - V141.000 Refactored Module
 * =======================================================
 *
 * Real-time metrics dashboard and statistics tracking.
 * Extracted from QuantHarvester.js for modular architecture.
 *
 * @module services/TelemetryService
 * @version V141.000
 * @since 2026-01-27
 * @author Senior Lead Software Architect (Refactoring Specialist)
 *
 * Features:
 * - Real-time quality metrics display
 * - Success rate tracking
 * - Memory and CPU monitoring
 * - Configurable report intervals
 */

'use strict';

/**
 * TelemetryService - Manages statistics and dashboard display
 */
class TelemetryService {
    /**
     * @param {Object} config - Configuration object
     * @param {boolean} config.telemetryEnabled - Enable telemetry dashboard
     * @param {number} config.telemetryReportInterval - Report every N matches
     */
    constructor(config = {}) {
        this.config = {
            telemetryEnabled: config.telemetryEnabled || false,
            telemetryReportInterval: config.telemetryReportInterval || 20
        };

        // Statistics tracking
        this.stats = {
            totalMatches: 0,
            successfulMatches: 0,
            failedMatches: 0,
            totalTrajectoryPoints: 0,
            pixelRetrySuccesses: 0,
            overlayNodesRemoved: 0,
            goldenZoneFiltered: 0,
            avgHarvestTimeMs: 0,
            lastTelemetryReport: 0
        };
    }

    /**
     * Update harvest statistics
     * @param {Object} result - Harvest result object
     * @returns {void}
     */
    updateStats(result) {
        this.stats.totalMatches++;
        if (result.success) {
            this.stats.successfulMatches++;
        } else {
            this.stats.failedMatches++;
        }
        this.stats.totalTrajectoryPoints += result?.trajectoryPoints || 0;
    }

    /**
     * Increment specific metric counter
     * @param {string} metric - Metric name (pixelRetrySuccesses, overlayNodesRemoved, etc.)
     * @param {number} value - Value to add (default: 1)
     * @returns {void}
     */
    incrementMetric(metric, value = 1) {
        if (this.stats.hasOwnProperty(metric)) {
            this.stats[metric] += value;
        }
    }

    /**
     * Set a specific metric value
     * @param {string} metric - Metric name
     * @param {number} value - Value to set
     * @returns {void}
     */
    setMetric(metric, value) {
        if (this.stats.hasOwnProperty(metric)) {
            this.stats[metric] = value;
        }
    }

    /**
     * Get current statistics
     * @returns {Object} Current stats object
     */
    getStats() {
        return { ...this.stats };
    }

    /**
     * Reset all statistics to zero
     * @returns {void}
     */
    resetStats() {
        Object.keys(this.stats).forEach(key => {
            if (typeof this.stats[key] === 'number') {
                this.stats[key] = 0;
            }
        });
    }

    /**
     * V138.000: Display telemetry dashboard
     * Shows real-time quality metrics every N matches
     *
     * @param {boolean} force - Force display regardless of interval
     * @returns {void}
     */
    displayTelemetryDashboard(force = false) {
        if (!this.config.telemetryEnabled) {
            return;
        }

        const shouldDisplay = force ||
            (this.stats.totalMatches % this.config.telemetryReportInterval === 0);

        if (!shouldDisplay || this.stats.totalMatches === 0) {
            return;
        }

        const successRate = ((this.stats.successfulMatches / this.stats.totalMatches) * 100).toFixed(2);
        const avgPointsPerMatch = this.stats.totalMatches > 0
            ? (this.stats.totalTrajectoryPoints / this.stats.successfulMatches).toFixed(2)
            : 0;
        const cpuUsage = process.cpuUsage().user / 1000000; // Convert to seconds
        const memUsage = process.memoryUsage();
        const memUsedMb = (memUsage.heapUsed / 1024 / 1024).toFixed(2);

        console.log('');
        console.log('╔════════════════════════════════════════════════════════════════╗');
        console.log('║          V138.000 TELEMETRY DASHBOARD - REAL-TIME METRICS         ║');
        console.log('╠════════════════════════════════════════════════════════════════╣');
        console.log(`║  📊 SUCCESS RATE       : ${successRate}% (${this.stats.successfulMatches}/${this.stats.totalMatches})`);
        console.log(`║  🎯 PIXEL RETRY SUCC   : ${this.stats.pixelRetrySuccesses}`);
        console.log(`║  💾 TRAJECTORY POINTS  : ${this.stats.totalTrajectoryPoints} (avg: ${avgPointsPerMatch}/match)`);
        console.log(`║  🗑️  OVERLAYS PURGED    : ${this.stats.overlayNodesRemoved} nodes`);
        console.log(`║  🏆 GOLDEN ZONE FLT    : ${this.stats.goldenZoneFiltered} filtered`);
        console.log(`║  ⏱️  AVG HARVEST TIME   : ${this.stats.avgHarvestTimeMs.toFixed(0)}ms`);
        console.log(`║  💻 CPU/MEM           : ${cpuUsage.toFixed(2)}s / ${memUsedMb}MB`);
        console.log('╚════════════════════════════════════════════════════════════════╝');
        console.log('');
    }

    /**
     * V138.000: Calculate average harvest time
     * @param {number} totalTime - Total processing time
     * @param {number} totalProcessed - Number of matches processed
     * @returns {number} Average time in milliseconds
     */
    calculateAvgHarvestTime(totalTime, totalProcessed) {
        return totalProcessed > 0 ? (totalTime / totalProcessed) * 1000 : 0;
    }
}

module.exports = { TelemetryService };
