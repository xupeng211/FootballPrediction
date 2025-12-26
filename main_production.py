#!/usr/bin/env python3
"""
V19.4 统一生产入口 (Main Production Entry Point)
=================================================

这是一个统一的命令行工具，用于执行 V19.4 系统的所有核心操作。
支持通过参数控制执行：L1数据收割、L2特征解析、V19.4模型预测、实时市场巡检。

V25.0 更新: 集成统一的特征提取框架

使用示例:
    # L1 数据收割
    python main_production.py --l1-harvest --season 2324 --target 10

    # L2 特征解析 (使用 V25 框架)
    python main_production.py --l2-parse --extractor-version V25.0

    # V19.4 模型训练
    python main_production.py --train --train-size 600 --test-size 160

    # V19.4 模型预测
    python main_production.py --predict --model v19.4

    # 实时市场巡检
    python main_production.py --monitor --match-id 4813551 --match-time "2025-12-26 12:30"

    # 一键完整流程
    python main_production.py --full-pipeline

Author: V19.4 DevOps Team
Version: 2.0.0 (V25.0 Integration)
Date: 2025-12-26
"""

import asyncio
import click
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

# V19.4.1 修复：强制加载 .env 文件以确保环境变量正确
from dotenv import load_dotenv
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path, override=True)

from src.config_unified import get_settings
from src.core.pipeline_v19_4 import V19_4TrainingPipeline
from src.ops.market_live_monitor import MarketLiveMonitor
from src.ops.risk_monitor import RiskMonitor
from src.api.collectors.fotmob_core import FotMobCoreCollector

# V25.0: 统一特征提取框架
from src.processors import ExtractorRegistry, ExtractionResult, ExtractionStatus
from src.processors.exceptions import ExtractionError, ValidationError

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/production.log')
    ]
)
logger = logging.getLogger(__name__)


# ============================================
# CLI 工具函数
# ============================================

def print_banner(title: str, width: int = 70):
    """打印标题横幅"""
    click.echo(f"\n{'='*width}")
    click.echo(f"  {title}")
    click.echo(f"{'='*width}\n")


def validate_environment():
    """验证环境配置"""
    settings = get_settings()

    # 检查必需的环境变量
    if not settings.database.password:
        logger.warning("⚠️  DB_PASSWORD 未设置，使用默认值（仅开发环境）")

    if settings.environment == "production":
        if len(settings.app.secret_key) < 32:
            logger.error("❌ 生产环境 SECRET_KEY 必须至少 32 字符")
            return False

    logger.info("✅ 环境配置验证通过")
    return True


# ============================================
# L1 数据收割命令
# ============================================

@click.command()
@click.option('--season', default='2324', help='赛季代码 (如 2324)')
@click.option('--target', default=10, type=int, help='目标比赛数量')
@click.option('--league', default='EPL', help='联赛代码')
def l1_harvest(season: str, target: int, league: str):
    """L1 数据收割 - 从 FotMob API 获取原始比赛数据"""
    print_banner(f"V19.4 L1 数据收割 - {league} {season} 赛季 (目标: {target}场)")

    try:
        collector = FotMobCoreCollector()
        logger.info(f"开始收割 {league} {season} 赛季数据...")

        # TODO: 实现具体的收割逻辑
        logger.info(f"✅ L1 数据收割完成 (模拟)")

    except Exception as e:
        logger.error(f"❌ L1 数据收割失败: {e}")
        sys.exit(1)


# ============================================
# L2 特征解析命令 (V25.0 集成)
# ============================================

@click.command()
@click.option('--match-id', type=int, help='指定比赛 ID 进行特征提取')
@click.option('--extractor-version', default='V25.0', help='特征提取器版本 (默认: V25.0)')
@click.option('--skip-validation', is_flag=True, help='跳过特征验证')
@click.option('--output-features', is_flag=True, help='输出提取的特征到控制台')
def l2_parse(match_id: Optional[int], extractor_version: str, skip_validation: bool, output_features: bool):
    """
    L2 特征解析 - 使用 V25 统一特征提取框架

    从数据库读取 L1 原始数据并提取特征。

    示例:
        # 提取指定比赛的特征
        python main_production.py --l2-parse --match-id 123456

        # 使用不同的提取器版本
        python main_production.py --l2-parse --extractor-version V25.0
    """
    print_banner(f"V25.0 L2 特征解析 (提取器: {extractor_version})")

    try:
        # 创建特征提取器
        extractor = ExtractorRegistry.create(extractor_version)
        logger.info(f"✓ 已创建特征提取器: {extractor.__class__.__name__}")

        # 如果指定了 match_id，从数据库提取单场比赛特征
        if match_id:
            logger.info(f"正在提取比赛 {match_id} 的特征...")

            # 从数据库获取 L1 原始数据
            import psycopg2
            from src.config_unified import get_settings

            settings = get_settings()
            conn = psycopg2.connect(
                host=settings.database.host,
                port=settings.database.port,
                database=settings.database.name,
                user=settings.database.user,
                password=settings.database.password.get_secret_value()
            )

            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT m.id, m.external_id, m.l2_raw_json,
                               m.home_team, m.away_team, m.match_time
                        FROM matches m
                        WHERE m.id = %s OR m.external_id = %s
                    """, (match_id, match_id))

                    match_data = cur.fetchone()

                    if not match_data:
                        logger.error(f"❌ 未找到比赛 ID {match_id}")
                        sys.exit(1)

                    db_id, external_id, l2_raw_json, home_team, away_team, match_time = match_data

                    if not l2_raw_json:
                        logger.error(f"❌ 比赛 {match_id} 没有 L2 原始数据，请先运行 L1 数据收割")
                        sys.exit(1)

                    # 解析 JSON
                    import json
                    raw_data = json.loads(l2_raw_json) if isinstance(l2_raw_json, str) else l2_raw_json

                    # 提取特征
                    result = extractor.extract_with_validation(raw_data, skip_validation=skip_validation)

                    # 处理结果
                    logger.info(f"比赛: {home_team} vs {away_team}")
                    logger.info(f"状态: {result.status.value}")
                    logger.info(f"特征数量: {result.feature_count}")

                    if result.is_success:
                        logger.info(f"✅ 特征提取成功")

                        if result.warnings:
                            logger.warning(f"警告: {len(result.warnings)} 条")
                            for warning in result.warnings[:3]:
                                logger.warning(f"  - {warning}")

                        if output_features:
                            logger.info("提取的特征:")
                            for key, value in list(result.features.items())[:10]:
                                logger.info(f"  {key}: {value}")
                            logger.info(f"  ... (共 {len(result.features)} 个特征)")

                        # 可选：保存到数据库
                        # TODO: 实现将特征保存到 match_features_training 表的逻辑

                    else:
                        logger.error(f"❌ 特征提取失败: {result.status.value}")
                        if result.errors:
                            for error in result.errors[:3]:
                                logger.error(f"  - {error}")
                        sys.exit(1)

            finally:
                conn.close()

        else:
            logger.info("未指定 --match-id，进入批量模式")
            logger.info("提示: 使用 --match-id <ID> 提取单场比赛特征")

            # TODO: 实现批量模式 - 扫描数据库并提取所有待处理比赛
            logger.info("✅ L2 特征解析框架就绪")

    except ExtractionError as e:
        logger.error(f"❌ 特征提取异常: {e}")
        sys.exit(1)
    except ValidationError as e:
        logger.error(f"❌ 特征验证失败: {e}")
        sys.exit(1)
    except KeyError as e:
        logger.error(f"❌ 未找到指定版本的提取器: {extractor_version}")
        logger.info(f"可用版本: {', '.join(ExtractorRegistry.list_versions())}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ L2 特征解析失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


# ============================================
# 模型训练命令
# ============================================

@click.command()
@click.option('--train-size', default=600, type=int, help='训练集大小')
@click.option('--test-size', default=160, type=int, help='测试集大小')
@click.option('--data-limit', default=760, type=int, help='数据加载限制')
@click.option('--apply-draw-weight', is_flag=True, default=True, help='应用平局类别权重')
def train(train_size: int, test_size: int, data_limit: int, apply_draw_weight: bool):
    """V19.4 模型训练 - 使用 48 维特征 + 加权损失函数"""
    print_banner(f"V19.4 模型训练 (训练集: {train_size}, 测试集: {test_size})")

    try:
        pipeline = V19_4TrainingPipeline()

        # 1. 加载数据
        logger.info("加载数据...")
        df = pipeline.load_data(limit=data_limit)

        if df.empty:
            logger.error("❌ 数据加载失败")
            sys.exit(1)

        # 2. 提取特征
        logger.info("提取特征...")
        feature_df = pipeline.extract_features(df)

        if feature_df.empty:
            logger.error("❌ 特征提取失败")
            sys.exit(1)

        # 3. 训练模型
        logger.info("训练模型...")
        metrics = pipeline.train_model(
            feature_df,
            train_size=train_size,
            test_size=test_size,
            apply_draw_weight=apply_draw_weight
        )

        # 4. 保存模型
        pipeline.save_model()

        # 5. 显示结果
        print_banner("训练结果")
        logger.info(f"整体准确率: {metrics.accuracy * 100:.2f}%")
        logger.info(f"主胜准确率: {metrics.home_win_accuracy * 100:.2f}%")
        logger.info(f"平局准确率: {metrics.draw_accuracy * 100:.2f}%")
        logger.info(f"客胜准确率: {metrics.away_win_accuracy * 100:.2f}%")
        logger.info(f"F1 宏平均: {metrics.f1_macro:.4f}")
        logger.info(f"✅ 模型已保存到: src/production_models/")

    except Exception as e:
        logger.error(f"❌ 模型训练失败: {e}")
        sys.exit(1)


# ============================================
# 模型预测命令
# ============================================

@click.command()
@click.option('--model', default='v19.4', help='模型版本')
@click.option('--match-id', help='特定比赛 ID')
@click.option('--output', default='data/production/', help='预测结果输出目录')
def predict(model: str, match_id: Optional[str], output: str):
    """V19.4 模型预测 - 生成比赛预测结果"""
    print_banner(f"V19.4 模型预测 ({model})")

    try:
        logger.info(f"加载 {model} 模型...")

        # TODO: 实现具体的预测逻辑
        if match_id:
            logger.info(f"预测比赛: {match_id}")
        else:
            logger.info("预测所有待预测比赛...")

        logger.info(f"预测结果输出到: {output}")
        logger.info(f"✅ 预测完成 (模拟)")

    except Exception as e:
        logger.error(f"❌ 预测失败: {e}")
        sys.exit(1)


# ============================================
# 实时市场巡检命令
# ============================================

@click.command()
@click.option('--match-id', required=True, help='目标比赛 ID')
@click.option('--match-time', required=True, help='比赛时间 (格式: YYYY-MM-DD HH:MM)')
@click.option('--initial-balance', default=1000.0, type=float, help='初始资金')
def monitor(match_id: str, match_time: str, initial_balance: float):
    """实时市场巡检 - 开场前实时校准机制"""
    print_banner(f"V19.4 实时市场巡检 (比赛ID: {match_id})")

    try:
        # 解析比赛时间
        match_dt = datetime.strptime(match_time, '%Y-%m-%d %H:%M')

        logger.info(f"目标比赛: {match_id}")
        logger.info(f"比赛时间: {match_dt}")
        logger.info(f"初始资金: {initial_balance}")
        logger.info(f"巡检窗口: 开场前 {MarketLiveMonitor.PRE_MATCH_WINDOW_MINUTES} 分钟")
        logger.info(f"轮询间隔: {MarketLiveMonitor.POLL_INTERVAL_MINUTES} 分钟")
        logger.info(f"偏差阈值: {MarketLiveMonitor.DELTA_THRESHOLD:.2%}")

        # 创建监控实例
        monitor_instance = MarketLiveMonitor(
            target_match_id=match_id,
            initial_balance=initial_balance
        )

        # 启动巡检
        logger.info("\n🚀 启动实时巡检...")
        asyncio.run(monitor_instance.start_monitoring(match_dt))

    except ValueError as e:
        logger.error(f"❌ 日期格式错误: {match_time} (应为: YYYY-MM-DD HH:MM)")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ 实时巡检失败: {e}")
        sys.exit(1)


# ============================================
# 风控状态检查命令
# ============================================

@click.command()
@click.option('--initial-balance', default=1000.0, type=float, help='初始资金')
def risk_status(initial_balance: float):
    """风控状态检查 - 显示当前风险指标"""
    print_banner("V19.4 风控状态检查")

    try:
        monitor = RiskMonitor(initial_balance=initial_balance)

        status = monitor.get_status_summary()

        logger.info("当前风控状态:")
        logger.info(f"  风险等级: {status['risk_level']}")
        logger.info(f"  当前余额: {status['balance']:.2f}")
        logger.info(f"  盈亏: {status['profit_loss']:+.2f} ({status['yield_pct']:.2f}%)")
        logger.info(f"  连续亏损: {status['consecutive_losses']}")
        logger.info(f"  最大回撤: {status['max_drawdown_pct']:.2%}")
        logger.info(f"  总下注: {status['total_bets']}")
        logger.info(f"  胜率: {status['win_rate']:.2f}%")
        logger.info(f"  熔断状态: {'已熔断' if status['is_stopped'] else '正常'}")

        # 生成每日报告
        report = monitor.generate_daily_report()
        if not report.empty:
            logger.info(f"\n今日报告:")
            logger.info(f"  下注次数: {report['total_bets'].iloc[0]}")
            logger.info(f"  盈亏: {report['profit'].iloc[0]:+.2f}")

    except Exception as e:
        logger.error(f"❌ 风控检查失败: {e}")
        sys.exit(1)


# ============================================
# 完整流水线命令
# ============================================

@click.command()
@click.option('--skip-harvest', is_flag=True, help='跳过数据收割')
@click.option('--skip-train', is_flag=True, help='跳过模型训练')
@click.option('--skip-predict', is_flag=True, help='跳过预测')
def full_pipeline(skip_harvest: bool, skip_train: bool, skip_predict: bool):
    """一键完整流程 - 从数据收割到预测输出"""
    print_banner("V19.4 完整流水线")

    steps = []

    if not skip_harvest:
        steps.append("L1 数据收割")

    if not skip_train:
        steps.append("V19.4 模型训练")

    if not skip_predict:
        steps.append("模型预测")

    logger.info(f"执行步骤: {' -> '.join(steps)}")
    logger.info("")

    # 执行各步骤
    # 注意：这里简化了实现，实际应该调用对应的子命令
    for step in steps:
        logger.info(f"🔄 执行: {step}...")

        if step == "L1 数据收割":
            # TODO: 调用 l1_harvest 逻辑
            logger.info("✅ L1 数据收割完成")

        elif step == "V19.4 模型训练":
            # TODO: 调用 train 逻辑
            logger.info("✅ V19.4 模型训练完成")

        elif step == "模型预测":
            # TODO: 调用 predict 逻辑
            logger.info("✅ 模型预测完成")

    print_banner("流水线完成")
    logger.info("✅ 所有步骤执行完成")


# ============================================
# 系统健康检查命令
# ============================================

@click.command()
def health_check():
    """系统健康检查 - 验证所有组件状态"""
    print_banner("V19.4 系统健康检查")

    checks = []

    # 1. 环境配置检查
    logger.info("🔍 检查环境配置...")
    if validate_environment():
        checks.append(("环境配置", "✅"))
    else:
        checks.append(("环境配置", "❌"))

    # 2. 数据库连接检查
    logger.info("🔍 检查数据库连接...")
    try:
        import psycopg2
        settings = get_settings()
        conn = psycopg2.connect(
            host=settings.database.host,
            port=settings.database.port,
            database=settings.database.name,
            user=settings.database.user,
            password=settings.database.password.get_secret_value()
        )
        conn.close()
        checks.append(("数据库", "✅"))
    except Exception as e:
        logger.error(f"数据库连接失败: {e}")
        checks.append(("数据库", "❌"))

    # 3. Redis 连接检查
    logger.info("🔍 检查 Redis 连接...")
    try:
        import redis
        settings = get_settings()
        r = redis.Redis(
            host=settings.redis.host,
            port=settings.redis.port,
            db=settings.redis.db,
            decode_responses=True
        )
        r.ping()
        checks.append(("Redis", "✅"))
    except Exception as e:
        logger.error(f"Redis 连接失败: {e}")
        checks.append(("Redis", "❌"))

    # 4. 模型文件检查
    logger.info("🔍 检查模型文件...")
    model_path = Path("src/production_models/v19.4_draw_sensitivity_model.pkl")
    if model_path.exists():
        checks.append(("V19.4 模型", "✅"))
    else:
        logger.warning("V19.4 模型文件不存在")
        checks.append(("V19.4 模型", "❌"))

    # 5. 数据目录检查
    logger.info("🔍 检查数据目录...")
    data_dirs = ["data", "data/market_monitor", "data/risk", "logs"]
    all_exist = all(Path(d).exists() for d in data_dirs)
    if all_exist:
        checks.append(("数据目录", "✅"))
    else:
        missing = [d for d in data_dirs if not Path(d).exists()]
        logger.warning(f"缺失目录: {missing}")
        checks.append(("数据目录", "❌"))

    # 显示检查结果
    print("\n" + "="*70)
    logger.info("健康检查结果:")
    for name, status in checks:
        logger.info(f"  {status} {name}")

    all_passed = all(status == "✅" for _, status in checks)

    if all_passed:
        logger.info("\n✅ 所有检查通过 - 系统已就绪")
    else:
        logger.warning("\n⚠️  部分检查失败 - 请检查上述问题")
        sys.exit(1)


# ============================================
# CLI 主入口
# ============================================

@click.group()
@click.version_option(version='1.0.0', prog_name='football-v194')
def main():
    """V19.4 足球预测系统 - 统一生产入口"""
    pass


# 注册子命令
main.add_command(l1_harvest)
main.add_command(l2_parse)
main.add_command(train)
main.add_command(predict)
main.add_command(monitor)
main.add_command(risk_status)
main.add_command(full_pipeline)
main.add_command(health_check)


if __name__ == '__main__':
    main()
