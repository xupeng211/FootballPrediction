'use strict';

const { extractFromHtml } = require('./NextDataParser');

class LeagueParser {
  parseFromNextData(nextData, context = {}) {
    const pageProps = nextData?.props?.pageProps || nextData?.pageProps || {};
    const content = pageProps.content || pageProps;

    return {
      leagueId: context.leagueId || content?.leagueId || content?.id || null,
      season: context.season || content?.season || pageProps?.season || null,
      name: content?.leagueName || content?.name || pageProps?.leagueName || null,
      raw: content
    };
  }

  parseFromHtml(html, context = {}) {
    const extracted = extractFromHtml(html);
    if (!extracted.success) {
      return { success: false, error: extracted.error };
    }

    return {
      success: true,
      data: this.parseFromNextData(extracted.data, context)
    };
  }
}

module.exports = { LeagueParser };
