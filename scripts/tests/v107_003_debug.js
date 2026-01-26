const fs = require('fs');

const modalHtml = fs.readFileSync('logs/v107_hover/modal_0_1769444837677.html', 'utf-8');

// Extract current section
const currentMatch = modalHtml.match(/<div class="flex flex-row gap-3">([\s\S]*?)<\/div>/);

if (currentMatch) {
    const content = currentMatch[1];
    console.log('Content length:', content.length);
    console.log('Content:', content);
    console.log('');

    // Count occurrences of numbers
    const numberPattern = /\d+\.\d+/g;
    const numbers = content.match(numberPattern) || [];
    console.log('All decimal numbers found:', numbers);
}
