'use strict';

module.exports = {
    ...require('./contracts'),
    ...require('./identityRegistry'),
    ...require('./theOddsApiAdapter'),
    ...require('./evidenceStore'),
    ...require('./replay'),
    ...require('./asOfView'),
};
