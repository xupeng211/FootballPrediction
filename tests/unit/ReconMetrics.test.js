'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');

const { ReconMetrics } = require('../../src/infrastructure/recon/ReconMetrics');

describe('ReconMetrics', () => {
  it('应初始化所有指标并支持记录、查询与重置', async () => {
    const infoEvents = [];
    const metrics = new ReconMetrics({
      prefix: 'test_recon',
      logger: {
        info(event, payload) {
          infoEvents.push({ event, payload });
        },
        warn() {},
        error() {}
      }
    });

    metrics.recordStitchSuccess('2025/2026', 'EPL', 'fuzzy');
    metrics.recordStitchFailure('2025/2026', 'EPL', 'timeout');
    metrics.recordSelectorFallback('eventRow', 'results');
    metrics.recordFuzzyConfidence(0.91, '2025/2026', 'EPL');
    metrics.recordNavigatorLatency(2.5, 'EPL', 'results');
    metrics.recordScanDuration(25, '2025/2026', 'EPL');
    metrics.recordRetryDelay(5, 'timeout');
    metrics.recordZombieKilled('chromium');
    metrics.recordProxySwitch('banned');
    metrics.recordCircuitBreakerTrip('threshold_reached');
    metrics.setActiveLocks(3);
    metrics.setStitchingRate(0.8, '2025/2026', 'EPL');
    metrics.setCircuitBreakerState('half_open');
    metrics.setCircuitBreakerState('unexpected');
    metrics.setProxyPoolHealth(18);
    metrics.setGuardianRunning(true);

    const summary = await metrics.getSummary();
    const register = metrics.getRegistry();
    const output = await metrics.getMetrics();

    assert.deepStrictEqual(summary, {
      counters: 6,
      histograms: 4,
      gauges: 5
    });
    assert.ok(register);
    assert.ok(infoEvents.some((entry) => entry.event === 'metrics_initialized'));
    assert.match(output, /test_recon_match_stitched_total\{season="2025\/2026",league="EPL",method="fuzzy"\} 1/);
    assert.match(output, /test_recon_match_failed_total\{season="2025\/2026",league="EPL",reason="timeout"\} 1/);
    assert.match(output, /test_recon_selector_fallback_hit_total\{selector_name="eventRow",page_type="results"\} 1/);
    assert.match(output, /test_recon_zombie_killed_total\{process_name="chromium"\} 1/);
    assert.match(output, /test_recon_proxy_switches_total\{reason="banned"\} 1/);
    assert.match(output, /test_recon_circuit_breaker_trips_total\{reason="threshold_reached"\} 1/);
    assert.match(output, /test_recon_active_locks 3/);
    assert.match(output, /test_recon_stitching_rate\{season="2025\/2026",league="EPL"\} 0.8/);
    assert.match(output, /test_recon_circuit_breaker_state 0/);
    assert.match(output, /test_recon_proxy_pool_health 18/);
    assert.match(output, /test_recon_guardian_running 1/);

    metrics.reset();

    const resetOutput = await metrics.getMetrics();
    assert.ok(infoEvents.some((entry) => entry.event === 'metrics_reset'));
    assert.doesNotMatch(resetOutput, /test_recon_match_stitched_total\{season="2025\/2026"/);
  });
});
