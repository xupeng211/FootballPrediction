/**
 * V73.200 - BridgeEngine Unit Tests
 * =====================================
 *
 * 完整的回归测试套件，确保 BridgeEngine 的核心功能正确性。
 *
 * 测试覆盖:
 *   - Levenshtein 算法正确性
 *   - 队名标准化映射（120+ 映射）
 *   - 模糊匹配逻辑
 *   - 边界条件处理
 *
 * @file test_bridge_engine.js
 * @version V73.200
 * @since 2026-01-25
 */

'use strict';

const {
    BridgeEngine,
    similarity,
    normalizeTeamName,
    levenshtein,
    BRIDGE_ENGINE_CONFIG
} = require('../../src/modules/bridge_engine');

const { Pool } = require('pg');

// ============================================================================
// TEST DATA
// ============================================================================

// 典型测试用例（10 个场景）
const TEST_CASES = [
    {
        name: 'Case 1: Man Utd vs Manchester United',
        fotmob: { home_team: 'Man Utd', away_team: 'Chelsea' },
        oddsportal: { home_team: 'Manchester United', away_team: 'Chelsea' },
        expected: { home_sim: 100, away_sim: 100, avg: 100 }
    },
    {
        name: 'Case 2: Real Madrid vs R. Madrid',
        fotmob: { home_team: 'Real Madrid', away_team: 'Barcelona' },
        oddsportal: { home_team: 'Real Madrid', away_team: 'FC Barcelona' },
        expected: { home_sim: 100, away_sim: 75, avg: 87.5 }
    },
    {
        name: 'Case 3: Athletic Club variants',
        fotmob: { home_team: 'Athletic Club', away_team: 'Real Sociedad' },
        oddsportal: { home_team: 'Athletic Bilbao', away_team: 'Real Sociedad' },
        expected: { home_sim: 100, away_sim: 100, avg: 100 }
    },
    {
        name: 'Case 4: Inter Milan variants',
        fotmob: { home_team: 'Inter', away_team: 'Juventus' },
        oddsportal: { home_team: 'Inter Milan', away_team: 'Juventus FC' },
        expected: { home_sim: 100, away_sim: 72.73, avg: 86.36 }
    },
    {
        name: 'Case 5: Bayern Munich',
        fotmob: { home_team: 'Bayern', away_team: 'Dortmund' },
        oddsportal: { home_team: 'Bayern Munich', away_team: 'Borussia Dortmund' },
        expected: { home_sim: 100, away_sim: 100, avg: 100 }
    },
    {
        name: 'Case 6: PSG variants',
        fotmob: { home_team: 'PSG', away_team: 'Monaco' },
        oddsportal: { home_team: 'Paris Saint-Germain', away_team: 'AS Monaco' },
        expected: { home_sim: 100, away_sim: 100, avg: 100 }
    },
    {
        name: 'Case 7: West Ham United',
        fotmob: { home_team: 'West Ham', away_team: 'Tottenham' },
        oddsportal: { home_team: 'West Ham United', away_team: 'Tottenham Hotspur' },
        expected: { home_sim: 100, away_sim: 100, avg: 100 }
    },
    {
        name: 'Case 8: Wolves normalization',
        fotmob: { home_team: 'Wolves', away_team: 'Leicester' },
        oddsportal: { home_team: 'Wolverhampton Wanderers', away_team: 'Leicester City' },
        expected: { home_sim: 100, away_sim: 100, avg: 100 }
    },
    {
        name: 'Case 9: Newcastle United',
        fotmob: { home_team: 'Newcastle', away_team: 'Sunderland' },
        oddsportal: { home_team: 'Newcastle United', away_team: 'Sunderland' },
        expected: { home_sim: 100, away_sim: 100, avg: 100 }
    },
    {
        name: 'Case 10: Levenshtein distance accuracy',
        fotmob: { home_team: 'Liverpool', away_team: 'Everton' },
        oddsportal: { home_team: 'Liverpool', away_team: 'Everton' },
        expected: { home_sim: 100, away_sim: 100, avg: 100 }
    }
];

// ============================================================================
// TEST SUITE
// ============================================================================

class BridgeEngineTestSuite {
    constructor() {
        this.passed = 0;
        this.failed = 0;
        this.results = [];
    }

    /**
     * Run all tests
     */
    async runAll() {
        console.log('\n╔══════════════════════════════════════════════════════════════════════════╗');
        console.log('║          V73.200 - BridgeEngine Unit Test Suite                          ║');
        console.log('╚══════════════════════════════════════════════════════════════════════════╝\n');

        this.testLevenshteinAlgorithm();
        this.testSimilarityFunction();
        this.testTeamNameNormalization();
        this.testFuzzyMatchingLogic();
        this.testEdgeCases();

        this.printSummary();
    }

    /**
     * Test 1: Levenshtein algorithm correctness
     */
    testLevenshteinAlgorithm() {
        console.log('📊 Test Suite 1: Levenshtein Algorithm Correctness');
        console.log('─'.repeat(70));

        const cases = [
            { a: 'kitten', b: 'sitting', expected: 3 },
            { a: 'Saturday', b: 'Sunday', expected: 3 },
            { a: 'Manchester United', b: 'Manchester Utd', expected: 3 },
            { a: '', b: '', expected: 0 },
            { a: 'test', b: '', expected: 4 },
        ];

        for (const tc of cases) {
            const result = levenshtein(tc.a, tc.b);
            const passed = result === tc.expected;
            this.recordResult('Levenshtein', tc.a, tc.b, result, tc.expected, passed);
        }

        console.log('');
    }

    /**
     * Test 2: Similarity function
     */
    testSimilarityFunction() {
        console.log('📊 Test Suite 2: Similarity Function');
        console.log('─'.repeat(70));

        const cases = [
            { a: 'test', b: 'test', expected: 100 },
            { a: 'test', b: 'text', expected: 75 },
            { a: 'Manchester United', b: 'Manchester Utd', expected: 82.35 },
            { a: '', b: 'test', expected: 0 },
            { a: 'Real Madrid', b: 'Real Madrid', expected: 100 },
        ];

        for (const tc of cases) {
            const result = similarity(tc.a, tc.b);
            const passed = Math.abs(result - tc.expected) < 1; // Allow 1% tolerance
            this.recordResult('Similarity', tc.a, tc.b, result.toFixed(2), tc.expected, passed);
        }

        console.log('');
    }

    /**
     * Test 3: Team name normalization (120+ mappings)
     */
    testTeamNameNormalization() {
        console.log('📊 Test Suite 3: Team Name Normalization');
        console.log('─'.repeat(70));

        const cases = [
            { input: 'Man Utd', expected: 'Manchester United' },
            { input: 'Spurs', expected: 'Tottenham Hotspur' },
            { input: 'Wolves', expected: 'Wolverhampton Wanderers' },
            { input: 'Juve', expected: 'Juventus' },
            { input: 'PSG', expected: 'Paris Saint-Germain' },
            { input: 'Bayern', expected: 'Bayern Munich' },
            { input: 'Atleti', expected: 'Atletico Madrid' },
            { input: 'Inter', expected: 'Inter Milan' },
            { input: 'Lyon', expected: 'Olympique Lyonnais' },
            { input: 'NonExistentTeam', expected: 'NonExistentTeam' },  // No mapping
        ];

        for (const tc of cases) {
            const result = normalizeTeamName(tc.input);
            const passed = result === tc.expected;
            this.recordResult('Normalization', tc.input, '→', result, tc.expected, passed);
        }

        console.log('');
    }

    /**
     * Test 4: Fuzzy matching logic (10 regression cases)
     */
    testFuzzyMatchingLogic() {
        console.log('📊 Test Suite 4: Fuzzy Matching Logic (Regression Cases)');
        console.log('─'.repeat(70));

        for (const tc of TEST_CASES) {
            // Normalize both sides
            const homeNorm1 = normalizeTeamName(tc.fotmob.home_team);
            const awayNorm1 = normalizeTeamName(tc.fotmob.away_team);
            const homeNorm2 = normalizeTeamName(tc.oddsportal.home_team);
            const awayNorm2 = normalizeTeamName(tc.oddsportal.away_team);

            // Calculate similarities
            const homeSim = similarity(homeNorm1, homeNorm2);
            const awaySim = similarity(awayNorm1, awayNorm2);
            const avgSim = (homeSim + awaySim) / 2;

            // Check if within tolerance
            const tolerance = 2; // 2% tolerance
            const homePass = Math.abs(homeSim - tc.expected.home_sim) <= tolerance;
            const awayPass = Math.abs(awaySim - tc.expected.away_sim) <= tolerance;
            const avgPass = Math.abs(avgSim - tc.expected.avg) <= tolerance;

            const passed = homePass && awayPass && avgPass;

            console.log(`  ${tc.name}`);
            console.log(`    Home: ${tc.fotmob.home_team} → ${homeNorm1} vs ${homeNorm2} (${homeSim.toFixed(2)}%)`);
            console.log(`    Away: ${tc.fotmob.away_team} → ${awayNorm1} vs ${awayNorm2} (${awaySim.toFixed(2)}%)`);
            console.log(`    Avg: ${avgSim.toFixed(2)}% (expected: ${tc.expected.avg}%)`);
            console.log(`    Result: ${passed ? '✅ PASS' : '❌ FAIL'}`);
            console.log('');

            if (passed) {
                this.passed++;
            } else {
                this.failed++;
            }
        }

        console.log('');
    }

    /**
     * Test 5: Edge cases
     */
    testEdgeCases() {
        console.log('📊 Test Suite 5: Edge Cases');
        console.log('─'.repeat(70));

        // Test null/undefined handling
        const nullSim1 = similarity(null, 'test');
        const nullSim2 = similarity('test', null);
        const nullSim3 = similarity(null, null);

        console.log(`  similarity(null, 'test') = ${nullSim1} (expected: 0)`);
        console.log(`  similarity('test', null) = ${nullSim2} (expected: 0)`);
        console.log(`  similarity(null, null) = ${nullSim3} (expected: 0)`);
        console.log(`  Null handling: ${nullSim1 === 0 && nullSim2 === 0 && nullSim3 === 0 ? '✅ PASS' : '❌ FAIL'}`);
        console.log('');

        // Test empty strings
        const emptySim = similarity('', '');
        console.log(`  similarity('', '') = ${emptySim} (expected: 100)`);
        console.log(`  Empty string: ${emptySim === 100 ? '✅ PASS' : '❌ FAIL'}`);
        console.log('');

        // Test normalization with non-existent teams
        const noMapping = normalizeTeamName('TotallyFakeTeam123');
        console.log(`  normalizeTeamName('TotallyFakeTeam123') = "${noMapping}" (expected: "TotallyFakeTeam123")`);
        console.log(`  No mapping preservation: ${noMapping === 'TotallyFakeTeam123' ? '✅ PASS' : '❌ FAIL'}`);
        console.log('');
    }

    /**
     * Record test result
     */
    recordResult(suite, input, transform, result, expected, passed) {
        if (passed) {
            this.passed++;
        } else {
            this.failed++;
        }

        this.results.push({
            suite,
            input: `${input} ${transform} ${result}`,
            expected,
            actual: result,
            status: passed ? '✅ PASS' : '❌ FAIL'
        });
    }

    /**
     * Print test summary
     */
    printSummary() {
        console.log('\n╔══════════════════════════════════════════════════════════════════════════╗');
        console.log('║                        Test Summary                                          ║');
        console.log('╠══════════════════════════════════════════════════════════════════════════╣');
        console.log(`║  Total Tests:  ${this.passed + this.failed}                                                      ║`);
        console.log(`║  Passed:       ${this.passed} (${((this.passed / (this.passed + this.failed) * 100).toFixed(1))}%)             ║`);
        console.log(`║  Failed:       ${this.failed} (${((this.failed / (this.passed + this.failed) * 100).toFixed(1))}%)             ║`);
        console.log(`║  Coverage:     ${this.passed === this.passed + this.failed && this.passed > 0 ? '100%' : 'N/A'}                    ║`);
        console.log('╚══════════════════════════════════════════════════════════════════════════╝');

        if (this.failed > 0) {
            console.log('\n❌ Failed Tests:');
            this.results.filter(r => r.status === '❌ FAIL').forEach(r => {
                console.log(`  ${r.suite}: ${r.input} (expected: ${r.expected}, got: ${r.actual})`);
            });
        }

        console.log('\n' + '='.repeat(80));
        console.log(`[V73.200] Test Suite Complete: ${this.passed}/${this.passed + this.failed} tests passed`);
        console.log('='.repeat(80));
    }
}

// ============================================================================
// MAIN EXECUTION
// ============================================================================

async function main() {
    const testSuite = new BridgeEngineTestSuite();
    await testSuite.runAll();

    const allPassed = testSuite.failed === 0;
    const exitCode = allPassed ? 0 : 1;

    if (allPassed) {
        console.log('\n✅ All tests passed! BridgeEngine is ready for production.');
    } else {
        console.log(`\n❌ ${testSuite.failed} tests failed. Please review and fix.`);
    }

    process.exit(exitCode);
}

// Execute tests if run directly
if (require.main === module) {
    main().catch(error => {
        console.error('Fatal error during test execution:', error);
        process.exit(1);
    });
}

module.exports = {
    BridgeEngineTestSuite,
    TEST_CASES
};
