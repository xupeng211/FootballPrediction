/**
 * V107.003 Parsing Test
 * ========================
 *
 * V107.003: Test parsing logic with captured modal HTML
 *
 * @version V107.003
 * @since 2026-01-27
 */

'use strict';

const fs = require('fs');

const modalHtml = fs.readFileSync('logs/v107_hover/modal_0_1769444837677.html', 'utf-8');

console.log('[V107.003] PARSING LOGIC TEST');
console.log('='.repeat(70));

// Test 1: Opening odds
console.log('\n=== TEST 1: OPENING ODDS ===');

// V107.003: Fixed regex - match until next div
const openingMatch = modalHtml.match(/Opening odds:<\/div>([\s\S]*?)<div class="flex border-t/);

if (openingMatch) {
    console.log('[SUCCESS] Found opening section');
    const content = openingMatch[1];
    console.log('Section content:', content);

    // Extract date and odds value using simple patterns
    const dateMatch = content.match(/(\d{2}\s[A-Za-z]{3},\s\d{2}:\d{2})/);
    const oddsMatch = content.match(/(\d+\.\d+)/);

    console.log('Date:', dateMatch ? dateMatch[0] : 'NOT FOUND');
    console.log('Odds:', oddsMatch ? oddsMatch[0] : 'NOT FOUND');

    if (dateMatch && oddsMatch) {
        const opening = {
            time: dateMatch[0],
            home: parseFloat(oddsMatch[0]) || null,
            type: 'opening'
        };
        console.log('Parsed opening:', opening);
    }
} else {
    console.log('[FAIL] Opening section not found');
}

// Test 2: Current odds
console.log('\n=== TEST 2: CURRENT ODDS ===');

const currentMatch = modalHtml.match(/<div class="flex flex-row gap-3">([\s\S]*?)<\/div>/);

if (currentMatch) {
    console.log('[SUCCESS] Found current section');
    const content = currentMatch[1];
    console.log('Content (first 200 chars):', content.substring(0, 200));

    // Extract date and odds value using simple patterns
    const dateMatch = content.match(/(\d{2}\s[A-Za-z]{3},\s\d{2}:\d{2})/);
    const oddsMatch = content.match(/(\d+\.\d+)/);

    console.log('Date:', dateMatch ? dateMatch[0] : 'NOT FOUND');
    console.log('Odds:', oddsMatch ? oddsMatch[0] : 'NOT FOUND');

    if (dateMatch && oddsMatch) {
        const current = {
            time: dateMatch[0],
            home: parseFloat(oddsMatch[0]) || null,
            type: 'current'
        };
        console.log('Parsed current:', current);
    }
} else {
    console.log('[FAIL] Current section not found');
}

// Test 3: Combined parsing
console.log('\n=== TEST 3: COMBINED PARSING ===');

const movements = [];

// Add opening
const openingSection = modalHtml.match(/Opening odds:<\/div>([\s\S]*?)<div class="flex border-t/);
if (openingSection) {
    const content = openingSection[1];
    const dateMatch = content.match(/(\d{2}\s[A-Za-z]{3},\s\d{2}:\d{2})/);
    const oddsMatch = content.match(/(\d+\.\d+)/);

    if (dateMatch && oddsMatch) {
        movements.push({
            time: dateMatch[0],
            home: parseFloat(oddsMatch[0]) || null,
            type: 'opening'
        });
    }
}

// Add current
const currentSection = modalHtml.match(/<div class="flex flex-row gap-3">([\s\S]*?)<\/div>/);
if (currentSection) {
    const content = currentSection[1];
    const dateMatch = content.match(/(\d{2}\s[A-Za-z]{3},\s\d{2}:\d{2})/);
    const oddsMatch = content.match(/(\d+\.\d+)/);

    if (dateMatch && oddsMatch) {
        const currentOdds = parseFloat(oddsMatch[0]) || null;

        // Only add if different from opening
        if (movements.length === 0 || currentOdds !== movements[0].home) {
            movements.push({
                time: dateMatch[0],
                home: currentOdds,
                type: 'current'
            });
        }
    }
}

console.log('Total movements:', movements.length);
console.log('Movements:', JSON.stringify(movements, null, 2));

// Test 4: Check if Opening != Closing
console.log('\n=== TEST 4: OPENING vs CLOSING ===');

if (movements.length >= 2) {
    const opening = movements.find(m => m.type === 'opening');
    const closing = movements.find(m => m.type === 'current');

    if (opening && closing) {
        const hasHistory = opening.home !== closing.home;
        console.log('Opening:', opening.home, 'at', opening.time);
        console.log('Closing:', closing.home, 'at', closing.time);
        console.log('Has history (Opening != Closing):', hasHistory);

        if (!hasHistory) {
            console.log('[INFO] This odds value has not changed since opening');
        }
    }
}

// Summary
console.log('\n=== SUMMARY ===');
console.log('✓ Modal HTML capture: SUCCESS');
console.log('✓ Opening odds extraction:', openingMatch ? 'SUCCESS' : 'FAILED');
console.log('✓ Current odds extraction:', currentMatch ? 'SUCCESS' : 'FAILED');
console.log('✓ Total history points:', movements.length);
console.log('✓ Has history (Opening != Closing):', movements.length >= 2 && movements[0].home !== movements[1].home);

console.log('\n[V107.003] Parsing logic verification complete!');
