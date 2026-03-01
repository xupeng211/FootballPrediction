/**
 * 数据库模型模块入口
 * @module models
 */

'use strict';

const { MatchQueries } = require('./MatchQueries');
const { RawDataQueries } = require('./RawDataQueries');

module.exports = {
    MatchQueries,
    RawDataQueries
};
