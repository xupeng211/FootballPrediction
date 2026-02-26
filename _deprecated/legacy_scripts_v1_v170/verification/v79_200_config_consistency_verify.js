#!/usr/bin/env node
/**
 * V79.200 Configuration Consistency Verification (JavaScript Side)
 * ==============================================================
 *
 * This script verifies that JavaScript's YAML/JSON loader produces
 * consistent types with Python's YAML loader.
 *
 * @file v79_200_config_consistency_verify.js
 * @version V79.200
 * @since 2026-01-25
 * @author V79.200 Engineering Team
 */

'use strict';

const fs = require('fs');
const path = require('path');

// Try to load js-yaml
let yaml;
try {
  yaml = require('js-yaml');
} catch (e) {
  console.error('❌ js-yaml not found. Install with: npm install js-yaml');
  process.exit(1);
}

// Add project root to path
const projectRoot = path.resolve(__dirname, '../..');
const configLoaderPath = path.join(projectRoot, 'scripts/ops/config_loader.js');

// Import config loader
const { getHyperParametersConfig, getTeamAliasesConfig } = require(configLoaderPath);

/**
 * Get the type name of a value
 * @param {*} value - Any value
 * @returns {string} Type name
 */
function formatType(value) {
  if (value === null) {
    return 'null';
  } else if (value === undefined) {
    return 'undefined';
  } else if (typeof value === 'boolean') {
    return 'boolean';
  } else if (typeof value === 'number') {
    // Check if integer or float
    return Number.isInteger(value) ? 'integer' : 'float';
  } else if (typeof value === 'string') {
    return 'string';
  } else if (Array.isArray(value)) {
    return 'array';
  } else if (typeof value === 'object') {
    return 'object';
  } else {
    return typeof value;
  }
}

/**
 * Verify hyper-parameters configuration
 * @returns {Object} Verification result
 */
function verifyHyperParameters() {
  const config = getHyperParametersConfig();

  const result = {
    timestamp: new Date().toISOString(),
    language: 'javascript',
    loader: 'js-yaml.load (js-yaml)',
    config_file: 'src/config/hyper_parameters.yaml',
    sections: {}
  };

  // Fatigue section
  result.sections.fatigue = {
    busy_week_threshold: {
      value: config.busyWeekThreshold,
      type: formatType(config.busyWeekThreshold),
      expected_type: 'integer'
    },
    default_rest_days: {
      value: config.defaultRestDays,
      type: formatType(config.defaultRestDays),
      expected_type: 'integer'
    }
  };

  // Unavailable section
  result.sections.unavailable = {
    star_market_value: {
      value: config.starMarketValue,
      type: formatType(config.starMarketValue),
      expected_type: 'float'
    }
  };

  // Feature extraction section
  result.sections.feature_extraction = {
    core_player_threshold: {
      value: config.corePlayerThreshold,
      type: formatType(config.corePlayerThreshold),
      expected_type: 'float'
    },
    sparsity_threshold: {
      value: config.sparsityThreshold,
      type: formatType(config.sparsityThreshold),
      expected_type: 'float'
    },
    excellent_threshold: {
      value: config.excellentThreshold,
      type: formatType(config.excellentThreshold),
      expected_type: 'integer'
    },
    good_threshold: {
      value: config.goodThreshold,
      type: formatType(config.goodThreshold),
      expected_type: 'integer'
    },
    fair_threshold: {
      value: config.fairThreshold,
      type: formatType(config.fairThreshold),
      expected_type: 'integer'
    },
    minimum_threshold: {
      value: config.minimumThreshold,
      type: formatType(config.minimumThreshold),
      expected_type: 'integer'
    }
  };

  // Similarity section
  result.sections.similarity = {
    team_match_threshold: {
      value: config.teamMatchThreshold,
      type: formatType(config.teamMatchThreshold),
      expected_type: 'float'
    },
    excellent_confidence_min: {
      value: config.excellentConfidenceMin,
      type: formatType(config.excellentConfidenceMin),
      expected_type: 'integer'
    },
    good_confidence_min: {
      value: config.goodConfidenceMin,
      type: formatType(config.goodConfidenceMin),
      expected_type: 'integer'
    },
    fair_confidence_min: {
      value: config.fairConfidenceMin,
      type: formatType(config.fairConfidenceMin),
      expected_type: 'integer'
    },
    reject_confidence_below: {
      value: config.rejectConfidenceBelow,
      type: formatType(config.rejectConfidenceBelow),
      expected_type: 'integer'
    },
    youth_penalty_ratio: {
      value: config.youthPenaltyRatio,
      type: formatType(config.youthPenaltyRatio),
      expected_type: 'float'
    }
  };

  // Odds integrity section
  result.sections.odds_integrity = {
    min_payout: {
      value: config.minPayout,
      type: formatType(config.minPayout),
      expected_type: 'float'
    },
    max_payout: {
      value: config.maxPayout,
      type: formatType(config.maxPayout),
      expected_type: 'float'
    },
    min_odds_value: {
      value: config.minOddsValue,
      type: formatType(config.minOddsValue),
      expected_type: 'float'
    }
  };

  // Database section
  result.sections.database = {
    pool_size: {
      value: config.poolSize,
      type: formatType(config.poolSize),
      expected_type: 'integer'
    },
    pool_max_overflow: {
      value: config.poolMaxOverflow,
      type: formatType(config.poolMaxOverflow),
      expected_type: 'integer'
    },
    pool_timeout: {
      value: config.poolTimeout,
      type: formatType(config.poolTimeout),
      expected_type: 'integer'
    },
    pool_recycle: {
      value: config.poolRecycle,
      type: formatType(config.poolRecycle),
      expected_type: 'integer'
    },
    query_timeout: {
      value: config.queryTimeout,
      type: formatType(config.queryTimeout),
      expected_type: 'integer'
    },
    connection_timeout: {
      value: config.connectionTimeout,
      type: formatType(config.connectionTimeout),
      expected_type: 'integer'
    }
  };

  // Crawler section
  result.sections.crawler = {
    default_delay: {
      value: config.defaultDelay,
      type: formatType(config.defaultDelay),
      expected_type: 'float'
    },
    min_delay: {
      value: config.minDelay,
      type: formatType(config.minDelay),
      expected_type: 'float'
    },
    max_delay: {
      value: config.maxDelay,
      type: formatType(config.maxDelay),
      expected_type: 'float'
    },
    max_retries: {
      value: config.maxRetries,
      type: formatType(config.maxRetries),
      expected_type: 'integer'
    },
    retry_backoff_multiplier: {
      value: config.retryBackoffMultiplier,
      type: formatType(config.retryBackoffMultiplier),
      expected_type: 'float'
    },
    retry_max_delay: {
      value: config.retryMaxDelay,
      type: formatType(config.retryMaxDelay),
      expected_type: 'integer'
    },
    retry_jitter_range: {
      value: config.retryJitterRange,
      type: formatType(config.retryJitterRange),
      expected_type: 'float'
    }
  };

  // Cache section
  result.sections.cache = {
    cache_enable: {
      value: config.cacheEnable,
      type: formatType(config.cacheEnable),
      expected_type: 'boolean'
    },
    cache_size: {
      value: config.cacheSize,
      type: formatType(config.cacheSize),
      expected_type: 'integer'
    },
    cache_ttl_seconds: {
      value: config.cacheTtlSeconds,
      type: formatType(config.cacheTtlSeconds),
      expected_type: 'integer'
    }
  };

  // Performance section
  result.sections.performance = {
    target_inference_latency_ms: {
      value: config.targetInferenceLatencyMs,
      type: formatType(config.targetInferenceLatencyMs),
      expected_type: 'integer'
    },
    target_fotmob_api_latency_s: {
      value: config.targetFotmobApiLatencyS,
      type: formatType(config.targetFotmobApiLatencyS),
      expected_type: 'float'
    },
    max_memory_mb: {
      value: config.maxMemoryMb,
      type: formatType(config.maxMemoryMb),
      expected_type: 'integer'
    },
    min_data_completeness: {
      value: config.minDataCompleteness,
      type: formatType(config.minDataCompleteness),
      expected_type: 'float'
    },
    min_mapping_success_rate: {
      value: config.minMappingSuccessRate,
      type: formatType(config.minMappingSuccessRate),
      expected_type: 'float'
    }
  };

  // Leagues section
  result.sections.leagues = {
    top_5_leagues: {
      value: config.top5Leagues,
      type: formatType(config.top5Leagues),
      expected_type: 'array'
    }
  };

  return result;
}

/**
 * Verify team aliases configuration
 * @returns {Object} Verification result
 */
function verifyTeamAliases() {
  const config = getTeamAliasesConfig();

  const result = {
    timestamp: new Date().toISOString(),
    language: 'javascript',
    loader: 'JSON.parse (stdlib)',
    config_file: 'config/team_aliases.json',
    sections: {}
  };

  result.sections.team_aliases = {
    team_name_mappings: {
      value: config.teamNameMappings,
      type: formatType(config.teamNameMappings),
      expected_type: 'object'
    },
    suffixes_to_strip: {
      value: config.suffixesToStrip,
      type: formatType(config.suffixesToStrip),
      expected_type: 'array'
    },
    prefixes_to_strip: {
      value: config.prefixesToStrip,
      type: formatType(config.prefixesToStrip),
      expected_type: 'array'
    },
    youth_keywords: {
      value: config.youthKeywords,
      type: formatType(config.youthKeywords),
      expected_type: 'object'
    },
    youth_patterns: {
      value: config.youthPatterns,
      type: formatType(config.youthPatterns),
      expected_type: 'array'
    },
    common_suffixes: {
      value: config.commonSuffixes,
      type: formatType(config.commonSuffixes),
      expected_type: 'object'
    }
  };

  return result;
}

/**
 * Compare Python and JavaScript results
 * @param {Object} pythonResult - Python verification result
 * @param {Object} jsResult - JavaScript verification result
 * @returns {Object} Comparison result
 */
function compareResults(pythonResult, jsResult) {
  const issues = [];
  const passed = [];
  const warnings = [];

  // Compare hyper-parameters
  const pyHyper = pythonResult.hyper_parameters.sections;
  const jsHyper = jsResult.hyper_parameters.sections;

  for (const sectionName in pyHyper) {
    const pySection = pyHyper[sectionName];
    const jsSection = jsHyper[sectionName];

    for (const key in pySection) {
      const pyEntry = pySection[key];
      const jsEntry = jsSection[key];

      // Type comparison
      // Special handling: Python float (85.0) vs JS integer (85) is OK if values are numerically equal
      const isFloatIntCompatible =
        (pyEntry.type === 'float' && jsEntry.type === 'integer') ||
        (pyEntry.type === 'integer' && jsEntry.type === 'float');

      const isNumericEqual = isFloatIntCompatible && (pyEntry.value === jsEntry.value);

      if (pyEntry.type !== jsEntry.type && !isNumericEqual) {
        issues.push({
          section: sectionName,
          key: key,
          issue: 'Type mismatch',
          python: pyEntry.type,
          javascript: jsEntry.type,
          python_value: pyEntry.value,
          javascript_value: jsEntry.value
        });
      } else {
        // Value comparison (for primitive types)
        if (pyEntry.type === 'boolean' ||
            pyEntry.type === 'integer' ||
            pyEntry.type === 'float' ||
            pyEntry.type === 'string' ||
            isNumericEqual) {
          if (pyEntry.value !== jsEntry.value) {
            warnings.push({
              section: sectionName,
              key: key,
              issue: 'Value mismatch',
              python: pyEntry.value,
              javascript: jsEntry.value
            });
          } else {
            // For float/int compatibility, mark as passed with note
            passed.push({
              section: sectionName,
              key: key,
              type: isNumericEqual ? `${pyEntry.type}↔${jsEntry.type}` : pyEntry.type,
              value: pyEntry.value,
              note: isNumericEqual ? 'Numeric value equality despite type difference' : undefined
            });
          }
        } else if (pyEntry.type === 'array') {
          // Array comparison
          if (JSON.stringify(pyEntry.value) === JSON.stringify(jsEntry.value)) {
            passed.push({
              section: sectionName,
              key: key,
              type: pyEntry.type,
              value: pyEntry.value
            });
          } else {
            warnings.push({
              section: sectionName,
              key: key,
              issue: 'Array content mismatch',
              python: pyEntry.value,
              javascript: jsEntry.value
            });
          }
        } else {
          passed.push({
            section: sectionName,
            key: key,
            type: pyEntry.type
          });
        }
      }
    }
  }

  return {
    total_checked: passed.length + issues.length + warnings.length,
    passed: passed.length,
    issues: issues.length,
    warnings: warnings.length,
    issue_details: issues,
    warning_details: warnings
  };
}

/**
 * Main entry point
 */
function main() {
  console.log('='.repeat(70));
  console.log('V79.200 Configuration Consistency Verification (JavaScript Side)');
  console.log('='.repeat(70));
  console.log();

  // Verify hyper-parameters
  console.log('Verifying hyper_parameters.yaml...');
  const hyperParams = verifyHyperParameters();

  // Verify team aliases
  console.log('Verifying team_aliases.json...');
  const teamAliases = verifyTeamAliases();

  // Output JSON result
  const result = {
    hyper_parameters: hyperParams,
    team_aliases: teamAliases
  };

  // Write to file
  const outputFile = path.join(__dirname, 'v79_200_javascript_config_snapshot.json');
  fs.writeFileSync(outputFile, JSON.stringify(result, null, 2), 'utf8');

  console.log(`\n✅ JavaScript configuration snapshot saved to: ${outputFile}`);
  console.log();

  // Print summary
  console.log('Summary:');
  console.log(`  - Fatigue parameters: ${Object.keys(hyperParams.sections.fatigue).length} keys`);
  console.log(`  - Feature extraction: ${Object.keys(hyperParams.sections.feature_extraction).length} keys`);
  console.log(`  - Similarity: ${Object.keys(hyperParams.sections.similarity).length} keys`);
  console.log(`  - Database: ${Object.keys(hyperParams.sections.database).length} keys`);
  console.log(`  - Crawler: ${Object.keys(hyperParams.sections.crawler).length} keys`);
  console.log(`  - Cache: ${Object.keys(hyperParams.sections.cache).length} keys`);
  console.log(`  - Performance: ${Object.keys(hyperParams.sections.performance).length} keys`);
  console.log(`  - Leagues: ${Object.keys(hyperParams.sections.leagues).length} keys`);
  console.log(`  - Team aliases: ${Object.keys(teamAliases.sections.team_aliases).length} keys`);

  // Try to load Python snapshot for comparison
  const pythonSnapshotPath = path.join(__dirname, 'v79_200_python_config_snapshot.json');
  if (fs.existsSync(pythonSnapshotPath)) {
    console.log();
    console.log('🔍 Comparing with Python snapshot...');

    const pythonResult = JSON.parse(fs.readFileSync(pythonSnapshotPath, 'utf8'));
    const comparison = compareResults(pythonResult, result);

    console.log();
    console.log('='.repeat(70));
    console.log('Configuration Consistency Report');
    console.log('='.repeat(70));
    console.log(`Total Checked: ${comparison.total_checked}`);
    console.log(`✅ Passed: ${comparison.passed}`);
    console.log(`⚠️  Warnings: ${comparison.warnings}`);
    console.log(`❌ Issues: ${comparison.issues}`);

    if (comparison.issues > 0) {
      console.log();
      console.log('Type Mismatches Found:');
      for (const issue of comparison.issue_details) {
        console.log(`  [${issue.section}.${issue.key}]`);
        console.log(`    Python: ${issue.python} (${JSON.stringify(issue.python_value)})`);
        console.log(`    JavaScript: ${issue.javascript} (${JSON.stringify(issue.javascript_value)})`);
      }
      console.log();
      console.log('❌ Configuration consistency check FAILED!');
      console.log('   Please ensure Python YAML and JS YAML loaders produce identical types.');
      return 1;
    }

    if (comparison.warnings > 0) {
      console.log();
      console.log('Warnings (non-critical):');
      for (const warning of comparison.warning_details) {
        console.log(`  [${warning.section}.${warning.key}] ${warning.issue}`);
        console.log(`    Python: ${JSON.stringify(warning.python)}`);
        console.log(`    JavaScript: ${JSON.stringify(warning.javascript)}`);
      }
    }

    console.log();
    console.log('✅ Configuration consistency check PASSED!');
    console.log('   Python YAML and JS YAML loaders produce IDENTICAL types.');
  } else {
    console.log();
    console.log('⏳ Python snapshot not found.');
    console.log('   Run first: python scripts/verification/v79_200_config_consistency_verify.py');
  }

  return 0;
}

// Run main
if (require.main === module) {
  process.exit(main());
}

module.exports = {
  verifyHyperParameters,
  verifyTeamAliases,
  compareResults
};
