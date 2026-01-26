/**
 * V106.011 Correct Decoding Test
 * ==============================
 *
 * V106.011: Implement correct JXG.decompress logic
 *
 * @version V106.011
 * @since 2026-01-26
 */

'use strict';

const fs = require('fs');
const zlib = require('zlib');

// Read captured response
const filepath = 'logs/v106_diagnostic/route_raw_1769436645357.bin';
const base64Text = fs.readFileSync(filepath, 'utf-8');

console.log('[V106.011] CORRECT DECODING TEST');
console.log('=' .repeat(70));
console.log('');

// Step 1: Base64 decode
console.log('Step 1: Base64 decode');
const buf1 = Buffer.from(base64Text, 'base64');
console.log('  Result:', buf1.length, 'bytes');
console.log('  First 20 bytes (hex):', buf1.subarray(0, 20).toString('hex'));
console.log('');

// Step 2: Unzip (zlib/gzip decompression)
console.log('Step 2: Unzip decompression');

// Try raw inflate (zlib without wrapper)
try {
    const inflated = zlib.inflateRawSync(buf1);
    console.log('  [SUCCESS] inflateRawSync:', inflated.length, 'bytes');

    // Step 3: RawUrlDecode (replace %xx with chars)
    let decoded = inflated.toString('utf-8');
    decoded = decoded.replace(/%([0-9A-Fa-f]{2})/g, (match, hex) => {
        return String.fromCharCode(parseInt(hex, 16));
    });

    console.log('  After URL decode:', decoded.length, 'chars');
    console.log('  Preview:', decoded.substring(0, 300));
    console.log('');

    // Try to parse as JSON
    try {
        const json = JSON.parse(decoded);
        console.log('[SUCCESS] JSON PARSE!');
        console.log('Keys:', Object.keys(json));
        console.log('');

        if (json.d) {
            console.log('Data keys:', Object.keys(json.d));
            if (json.d.match) {
                console.log('Match data:', JSON.stringify(json.d.match).substring(0, 500));
            }
            if (json.d.history) {
                console.log('History data:', JSON.stringify(json.d.history).substring(0, 500));
            }
        }
    } catch (e) {
        console.log('[FAIL] JSON parse:', e.message);
        console.log('Raw preview:', decoded.substring(0, 500));
    }

} catch (e) {
    console.log('  [FAIL] inflateRawSync:', e.message);
    console.log('  Trying standard zlib.inflate...');

    try {
        const inflated = zlib.inflateSync(buf1);
        console.log('  [SUCCESS] inflateSync:', inflated.length, 'bytes');

        let decoded = inflated.toString('utf-8');
        decoded = decoded.replace(/%([0-9A-Fa-f]{2})/g, (match, hex) => {
            return String.fromCharCode(parseInt(hex, 16));
        });

        console.log('  After URL decode:', decoded.length, 'chars');
        console.log('  Preview:', decoded.substring(0, 300));
        console.log('');

        try {
            const json = JSON.parse(decoded);
            console.log('[SUCCESS] JSON PARSE!');
            console.log('Keys:', Object.keys(json));
            if (json.d) console.log('d keys:', Object.keys(json.d));
        } catch (e2) {
            console.log('[FAIL] JSON parse:', e2.message);
        }

    } catch (e2) {
        console.log('  [FAIL] inflateSync:', e2.message);

        // Try gunzip
        try {
            const gunzipped = zlib.gunzipSync(buf1);
            console.log('  [SUCCESS] gunzipSync:', gunzipped.length, 'bytes');

            let decoded = gunzipped.toString('utf-8');
            decoded = decoded.replace(/%([0-9A-Fa-f]{2})/g, (match, hex) => {
                return String.fromCharCode(parseInt(hex, 16));
            });

            console.log('  After URL decode:', decoded.length, 'chars');
            console.log('  Preview:', decoded.substring(0, 300));

            try {
                const json = JSON.parse(decoded);
                console.log('[SUCCESS] JSON PARSE!');
                console.log('Keys:', Object.keys(json));
            } catch (e3) {
                console.log('[FAIL] JSON parse:', e3.message);
            }
        } catch (e3) {
            console.log('  [FAIL] gunzipSync:', e3.message);
        }
    }
}
