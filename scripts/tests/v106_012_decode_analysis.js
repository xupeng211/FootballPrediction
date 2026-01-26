/**
 * V106.012 Decode Analysis
 * ========================
 *
 * V106.012: Analyze second decode result to determine format
 *
 * @version V106.012
 * @since 2026-01-26
 */

'use strict';

const fs = require('fs');

const filepath = 'logs/v106_diagnostic/route_raw_1769436645357.bin';
const base64Text = fs.readFileSync(filepath, 'utf-8');

// Double Base64 decode
const buf1 = Buffer.from(base64Text, 'base64');
const str1 = buf1.toString('utf-8');
const cleanStr1 = str1.replace(/[^A-Za-z0-9+/=]/g, '');
const padded = cleanStr1.padEnd(cleanStr1.length + (4 - cleanStr1.length % 4) % 4, '=');
const buf2 = Buffer.from(padded, 'base64');

console.log('[ANALYSIS] Second decode result:');
console.log('  Length:', buf2.length, 'bytes');
console.log('  Magic bytes (hex):', buf2.subarray(0, 4).toString('hex'));
console.log('');

// Check if it's valid UTF-8 text
const asUtf8 = buf2.toString('utf-8');
console.log('As UTF-8 text:');
console.log('  Length:', asUtf8.length, 'chars');
console.log('  First 100 chars:', asUtf8.substring(0, 100));
console.log('');

// Look for patterns
const hasBraces = asUtf8.includes('{') || asUtf8.includes('}');
const hasBrackets = asUtf8.includes('[') || asUtf8.includes(']');
const hasQuotes = asUtf8.includes('"');
const hasPercent = asUtf8.includes('%');

console.log('Pattern analysis:');
console.log('  Has braces:', hasBraces);
console.log('  Has brackets:', hasBrackets);
console.log('  Has quotes:', hasQuotes);
console.log('  Has percent:', hasPercent);
console.log('');

// Count different characters
let controlChars = 0;
let printableChars = 0;
for (let i = 0; i < Math.min(buf2.length, 1000); i++) {
    const b = buf2[i];
    if (b < 32 || b === 127) controlChars++;
    else if (b >= 32 && b < 127) printableChars++;
}
console.log('Character analysis (first 1000 bytes):');
console.log('  Control chars:', controlChars);
console.log('  Printable ASCII:', printableChars);
console.log('  Ratio:', (printableChars / 1000 * 100).toFixed(1) + '%');
console.log('');

// If high ratio of printable ASCII, might be text
if (printableChars > 500) {
    console.log('[HYPOTHESIS] Might be URL-encoded text, not compressed!');
    console.log('Trying URL decode...');

    let urlDecoded = asUtf8;
    let iterations = 0;
    while (urlDecoded.includes('%') && iterations < 10) {
        const newDecoded = urlDecoded.replace(/%([0-9A-Fa-f]{2})/g, (match, hex) => {
            return String.fromCharCode(parseInt(hex, 16));
        });
        if (newDecoded === urlDecoded) break;
        urlDecoded = newDecoded;
        iterations++;
    }

    console.log('After URL decode (' + iterations + ' iterations):');
    console.log('  Length:', urlDecoded.length, 'chars');
    console.log('  First 200 chars:', urlDecoded.substring(0, 200));
    console.log('');

    try {
        const json = JSON.parse(urlDecoded);
        console.log('[SUCCESS] JSON PARSE!');
        console.log('Keys:', Object.keys(json));
        if (json.d) {
            console.log('d keys:', Object.keys(json.d));
        }
        console.log('');
        console.log('Sample data:');
        console.log(JSON.stringify(json, null, 2).substring(0, 2000));
    } catch (e) {
        console.log('[FAIL] JSON parse:', e.message);
        console.log('Error:', e.stack);
    }
} else {
    console.log('[HYPOTHESIS] Likely compressed binary data');
    console.log('Magic bytes:', buf2.subarray(0, 4).toString('hex'));
    console.log('Expected for deflate: 78 01 - 78 9e');
    console.log('Expected for zlib: 78 9c');
    console.log('Expected for gzip: 1f 8b');
}
