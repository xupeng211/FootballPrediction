#!/usr/bin/env node
/**
 * V193.4 - 意甲精准熔炼
 * 鱻对指定比赛ID进行熔炼
 */

'use strict';

const path = require('path');
const { FeatureSmelter } = require('../../src/feature_engine/smelter/FeatureSmelter');
const { Logger } = require('../../src/infrastructure/utils/Logger');
const projectRoot = process.cwd();

    const logger = new Logger('smelt_serie_a');

    // 目标比赛 ID 列表 - 意甲最近 10 场已结束的意甲比赛
const targetMatchIds = [
    '55_20242025_4803308',
    '55_20242025_4803304',
    '55_20242025_4803301',
    '55_20242025_4803302',
    '55_20242025_4803307',
    '55_20242025_4803303',
    '55_20242025_4803306',
    '55_20242025_4803299',
    '55_20242025_4803313',
    '55_20242025_4803298',
    '55_20242025_4803312',
];

        console.log('═════════════════════════════════════════════════════════════════');
        console.log('🎯 目标: 意甲最近 10 场已结束比赛');
        console.log('   match_id:', targetMatchIds.join('\n  - ') });
        console.log('     - home_team vs away_team');
        console.log('     - match_date:', match.match_date);
        console.log('     - status:', match.status);
        console.log('     - league_name:', match.league_name);
        console.log('');
    }
    console.log('📊 开始熔炼...');
    console.log('═══════════════════════════════════════════════════════════════════');
        console.log('成功: ' + successCount + '/' 失, ' + 失);
        console.log(`\n🔄 恏甲数据回滚中...');
    }
    console.log(`  ========================================`);
    console.log(`  - ${targetMatchIds.join('\n' - ') `));
            return result;
        } else {
                console.log(`\n  意甲 L3 熔炼完成！`);
                return result;
            } catch (error) {
                console.error(`❌ 熔炼错误 [${matchId}]:`, error.message);
            }
        }

        // 更新最终统计
        console.log('═════════════════════════════════════════════════════════════════');
        console.log(`  成功: ${successCount} 场, 失 ${failCount} 场, 夻率: 0%`);
        console.log(`════════════════════════════════════════════════════════════════════`);
    }
    console.log('');
    process.exit(0);
})();
