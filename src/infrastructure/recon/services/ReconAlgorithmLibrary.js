'use strict';

const reconAlgorithmLibrary = {
  _extractFromBundle(bundleSource) {
    const text = String(bundleSource || '');
    if (!text) {
      return [];
    }

    const exportMap = this._parseBundleExportMap(text);
    if (exportMap.size === 0) {
      return [];
    }

    const candidates = [];
    for (const [alias, original] of exportMap.entries()) {
      const snippet = this._findBundleSnippet(text, original);
      const score = this._scoreBundleSnippet(alias, snippet);
      if (score > 0) {
        candidates.push({ alias, score });
      }
    }

    return candidates
      .sort((left, right) => right.score - left.score)
      .map((candidate) => candidate.alias);
  },

  _parseBundleExportMap(bundleSource) {
    const text = String(bundleSource || '');
    const exportBlock = text.match(/export\{([\s\S]+)\};\s*$/);
    if (!exportBlock) {
      return new Map();
    }

    const entries = exportBlock[1]
      .split(',')
      .map((entry) => entry.trim())
      .filter(Boolean);

    const exportMap = new Map();
    for (const entry of entries) {
      const match = entry.match(/^(\S+)\s+as\s+(\S+)$/);
      if (!match) {
        continue;
      }
      exportMap.set(match[2], match[1]);
    }

    return exportMap;
  },

  _findBundleSnippet(bundleSource, symbolName) {
    if (!bundleSource || !symbolName) {
      return '';
    }

    const markers = [
      `function ${symbolName}`,
      `const ${symbolName}=`,
      `const ${symbolName} =`,
      `let ${symbolName}=`,
      `let ${symbolName} =`
    ];

    for (const marker of markers) {
      const index = bundleSource.indexOf(marker);
      if (index >= 0) {
        return bundleSource.slice(index, index + 1600);
      }
    }

    return '';
  },

  _scoreBundleSnippet(alias, snippet) {
    const text = String(snippet || '');
    if (!text) {
      return 0;
    }

    let score = 0;
    if (/^ai$/i.test(alias)) score += 3;
    if (/atob\(/.test(text)) score += 5;
    if (/crypto/.test(text)) score += 5;
    if (/TextDecoder/.test(text)) score += 4;
    if (/TextEncoder/.test(text)) score += 2;
    if (/Uint8Array/.test(text)) score += 2;
    if (/importKey|deriveKey|decrypt/.test(text)) score += 6;
    if (/PBKDF2|AES-CBC|AES-GCM/.test(text)) score += 4;

    return score >= 8 ? score : 0;
  },

  _cleanPayload(rawData) {
    if (!rawData || typeof rawData !== 'string') {
      return rawData;
    }

    let cleaned = rawData
      .replace(/^"|"$/g, '')
      .replace(/\\"/g, '"')
      .replace(/\\n/g, '')
      .replace(/\\r/g, '')
      .replace(/\\t/g, '')
      .replace(/\\/g, '')
      .trim();

    if (cleaned.startsWith('"') && cleaned.endsWith('"')) {
      try {
        cleaned = JSON.parse(cleaned);
      } catch {
        // ignore malformed quoted payloads
      }
    }

    const base64Pattern = /^[A-Za-z0-9+/=]+$/;
    if (!base64Pattern.test(cleaned)) {
      const base64Match = cleaned.match(/([A-Za-z0-9+/]{100,}={0,2})/);
      if (base64Match) {
        cleaned = base64Match[1];
      }
    }

    return cleaned;
  },

  _probeEncryptedPayload(cleanedData) {
    if (!cleanedData || typeof cleanedData !== 'string') {
      return {
        valid: false,
        reason: 'INVALID_ENCRYPTED_PAYLOAD',
        preview: ''
      };
    }

    const preview = cleanedData.slice(0, 120);
    if (/^URL:|^Status:|<html|<!doctype|not found|forbidden/i.test(cleanedData)) {
      return {
        valid: false,
        reason: 'INVALID_ENCRYPTED_PAYLOAD',
        preview
      };
    }

    try {
      const decoded = Buffer.from(cleanedData, 'base64').toString('utf8');
      const separatorIndex = decoded.indexOf(':');
      if (separatorIndex <= 0 || separatorIndex >= decoded.length - 1) {
        return {
          valid: false,
          reason: 'INVALID_ENCRYPTED_PAYLOAD',
          preview
        };
      }

      const ivSegment = decoded.slice(separatorIndex + 1).trim();
      if (!/^[a-f0-9]+$/i.test(ivSegment) || ivSegment.length % 2 !== 0) {
        return {
          valid: false,
          reason: 'INVALID_ENCRYPTED_PAYLOAD',
          preview
        };
      }

      return {
        valid: true,
        reason: null,
        preview
      };
    } catch {
      return {
        valid: false,
        reason: 'INVALID_ENCRYPTED_PAYLOAD',
        preview
      };
    }
  }
};

module.exports = { reconAlgorithmLibrary };
