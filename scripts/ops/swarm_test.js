/**
 * TITAN-SWARM 蜂群实战测试
 * =========================
 *
 * 测试指令: 同时启动 3 个并发 Worker，收割意甲比赛
 * 比赛 ID: 4803312, 4803313, 4803314
 *
 * 用法:
 *   node scripts/ops/swarm_test.js
 *
 * 环境变量:
 *   SWARM_CONCURRENCY - 并发数（默认 3）
 *   SWARM_STAGGER_MS  - 错峰间隔（默认 5000ms）
 */

'use strict';

// ============================================================================
// 启动日志 - 必须在最顶部，确保任何错误发生前就有输出
// ============================================================================
console.log('🚀 Swarm Test Engine Starting...');
console.log(`📅 ${new Date().toISOString()}`);
console.log(`📂 工作目录: ${process.cwd()}`);
console.log('');

// ============================================================================
// 全局错误捕获 - 捕获所有未处理的错误
// ============================================================================
process.on('unhandledRejection', (reason, promise) => {
    console.error('');
    console.error('💥 未处理的 Promise 拒绝:');
    console.error('   原因:', reason);
    console.error('   Promise:', promise);
    console.error('');
    process.exit(1);
});

process.on('uncaughtException', (error) => {
    console.error('');
    console.error('💥 未捕获的异常:');
    console.error('   错误:', error.message);
    console.error('   堆栈:', error.stack);
    console.error('');
    process.exit(1);
});

// ============================================================================
// 模块加载阶段 - 带错误捕获
// ============================================================================
let SwarmHarvester;

try {
    console.log('📦 正在加载 SwarmHarvester 模块...');
    const module = require('../../src/infrastructure/harvesters/SwarmHarvester');
    SwarmHarvester = module.SwarmHarvester;
    console.log('✅ SwarmHarvester 模块加载成功');
    console.log('');
} catch (error) {
    console.error('');
    console.error('❌ 模块加载失败:');
    console.error(`   错误: ${error.message}`);
    console.error(`   堆栈: ${error.stack}`);
    console.error('');
    process.exit(1);
}

// ============================================================================
// 测试配置
// ============================================================================

// 意甲测试比赛 ID
const TEST_MATCH_IDS = [
    4803312,
    4803313,
    4803314
];

// 并发配置
const CONFIG = {
    concurrency: parseInt(process.env.SWARM_CONCURRENCY) || 3,
    staggerStartMs: parseInt(process.env.SWARM_STAGGER_MS) || 5000,
    verboseLogging: true
};

// ============================================================================
// 主函数
// ============================================================================

/**
 *
 */
async function main() {
    console.log('╔═══════════════════════════════════════════════════════════════╗');
    console.log('║  🧪 TITAN-SWARM 蜂群实战测试                                   ║');
    console.log('║  测试目标: 验证 3 并发 Worker + 22 代理轮询机制               ║');
    console.log('╚═══════════════════════════════════════════════════════════════╝');
    console.log('');
    console.log('📋 测试参数:');
    console.log(`   比赛 ID: ${TEST_MATCH_IDS.join(', ')}`);
    console.log(`   并发数: ${CONFIG.concurrency}`);
    console.log(`   错峰间隔: ${CONFIG.staggerStartMs}ms`);
    console.log('');

    let swarm;
    try {
        console.log('🔧 正在创建 SwarmHarvester 实例...');
        swarm = new SwarmHarvester(CONFIG);
        console.log('✅ SwarmHarvester 实例创建成功');
        console.log('');
    } catch (error) {
        console.error('');
        console.error('❌ SwarmHarvester 实例化失败:');
        console.error(`   错误: ${error.message}`);
        console.error(`   堆栈: ${error.stack}`);
        throw error;
    }

    try {
        console.log('🚀 启动蜂群收割...');
        console.log('');
        
        const result = await swarm.batchRun(TEST_MATCH_IDS, CONFIG.concurrency);

        console.log('');
        console.log('╔═══════════════════════════════════════════════════════════════╗');
        console.log('║  🎯 测试完成                                                   ║');
        console.log('╚═══════════════════════════════════════════════════════════════╝');

        // 验证结果
        const allSuccess = result.success === result.total;
        const hasDifferentPorts = result.workerDetails &&
            result.workerDetails.length >= 2 &&
            result.workerDetails[0].port !== result.workerDetails[1].port;

        console.log('');
        console.log('✅ 验证项:');
        console.log(`   ${allSuccess ? '✓' : '✗'} 所有任务完成`);
        console.log(`   ${hasDifferentPorts ? '✓' : '✗'} 不同 Worker 使用不同端口`);
        console.log(`   ${result.avgSpeed > 0 ? '✓' : '✗'} 收割速度正常`);

        if (allSuccess && hasDifferentPorts) {
            console.log('');
            console.log('🎉 蜂群测试通过！TITAN-SWARM 已就绪！');
        } else {
            console.log('');
            console.log('⚠️  部分测试项未通过，请检查日志');
        }

        // 返回结果给调用者
        return allSuccess ? 0 : 1;

    } catch (error) {
        console.error('');
        console.error('💥 测试执行失败:', error.message);
        console.error(error.stack);
        throw error;
    }
}

// ============================================================================
// 启动
// ============================================================================

// 优雅停机处理
process.on('SIGINT', () => {
    console.log('\n\n⚠️  测试被中断 (SIGINT)');
    process.exit(130);
});

process.on('SIGTERM', () => {
    console.log('\n\n⚠️  测试被终止 (SIGTERM)');
    process.exit(143);
});

// 运行测试
(async () => {
    try {
        const exitCode = await main();
        console.log('');
        console.log(`🏁 程序正常退出，退出码: ${exitCode}`);
        process.exit(exitCode);
    } catch (error) {
        console.error('');
        console.error('💥 main() 执行失败:', error.message);
        console.error(error.stack);
        process.exit(1);
    }
})();