'use strict';

module.exports = {
    ...require('./contracts'),
    ...require('./identityRegistry'),
    ...require('./theOddsApiAdapter'),
    ...require('./theOddsApiClient'),
    ...require('./evidenceStore'),
    ...require('./replay'),
    ...require('./asOfView'),
};
