#!/usr/bin/env python3
"""
V51.0 数据健康检查脚本
=======================

用途:
    1. 统计 matches 表中已激活 (finished) 比赛总数
    2. 随机抽取 10 场比赛，尝试提取 V51 特征
    3. 检查输出特征向量的异常极值和 NaN
    4. 输出"数据就绪度报告"

使用方法:
    python scripts/maintenance/check_v51_data_health.py
    python scripts/maintenance/check_v51_data_health.py --sample-size 20
    python scripts/maintenance/check_v51_data_health.py --verbose

Author: ML Engineering Team
Version: V51.0
Date: 2025-12-31
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config_unified import get_settings
from src.processors.v51_feature_refiner import V51FeatureRefiner

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)8s] %(message)s")
logger = logging.getLogger(__name__)


# ============================================================================
# 数据库查询
# ============================================================================


def get_finished_matches_stats(conn) -> dict:
    """获取 finished 比赛统计信息"""
    cur = conn.cursor()

    # 总 finished 比赛数
    cur.execute("""
        SELECT COUNT(*)
        FROM matches
        WHERE status = 'finished'
          AND home_score IS NOT NULL
          AND away_score IS NOT NULL
    """)
    total_finished = cur.fetchone()[0]

    # 有 raw_data 的比赛数
    cur.execute("""
        SELECT COUNT(*)
        FROM matches m
        INNER JOIN raw_match_data r ON m.match_id = r.match_id
        WHERE m.status = 'finished'
          AND m.home_score IS NOT NULL
          AND m.away_score IS NOT NULL
    """)
    with_raw_data = cur.fetchone()[0]

    # 按赛季分布
    cur.execute("""
        SELECT season, COUNT(*) as count
        FROM matches
        WHERE status = 'finished'
          AND home_score IS NOT NULL
          AND away_score IS NOT NULL
        GROUP BY season
        ORDER BY season DESC
    """)
    season_distribution = cur.fetchall()

    # 按联赛分布
    cur.execute("""
        SELECT league_name, COUNT(*) as count
        FROM matches
        WHERE status = 'finished'
          AND home_score IS NOT NULL
          AND away_score IS NOT NULL
        GROUP BY league_name
        ORDER BY count DESC
        LIMIT 10
    """)
    league_distribution = cur.fetchall()

    # 最近比赛日期
    cur.execute("""
        SELECT MAX(match_date), MIN(match_date)
        FROM matches
        WHERE status = 'finished'
          AND home_score IS NOT NULL
          AND away_score IS NOT NULL
    """)
    max_date, min_date = cur.fetchone()

    cur.close()

    return {
        "total_finished": total_finished,
        "with_raw_data": with_raw_data,
        "season_distribution": season_distribution,
        "league_distribution": league_distribution,
        "date_range": (min_date, max_date),
    }


def get_random_matches(conn, limit: int = 10) -> list[tuple[str, dict]]:
    """随机抽取 N 场比赛及其 raw_data"""
    cur = conn.cursor()

    # 获取所有比赛 ID
    cur.execute(
        """
        SELECT m.match_id, r.raw_data
        FROM matches m
        INNER JOIN raw_match_data r ON m.match_id = r.match_id
        WHERE m.status = 'finished'
          AND m.home_score IS NOT NULL
          AND m.away_score IS NOT NULL
        ORDER BY RANDOM()
        LIMIT %s
    """,
        (limit,),
    )

    rows = cur.fetchall()
    cur.close()

    return rows


# ============================================================================
# 健康检查
# ============================================================================


def check_nan_values(df: pd.DataFrame) -> dict:
    """检查 NaN 值"""
    nan_count = df.isna().sum().sum()
    nan_percentage = 100 * nan_count / (df.shape[0] * df.shape[1]) if df.size > 0 else 0

    nan_by_column = df.isna().sum()
    nan_columns = nan_by_column[nan_by_column > 0].to_dict()

    return {
        "total_nan": nan_count,
        "nan_percentage": nan_percentage,
        "nan_columns": nan_columns,
    }


def check_outliers(df: pd.DataFrame, threshold: float = 5.0) -> dict:
    """检查异常极值 (使用 Z-score 方法)"""
    outliers = {}

    for col in df.columns:
        if col == "match_id":
            continue

        # 跳过非数值列
        if not pd.api.types.is_numeric_dtype(df[col]):
            continue

        # 计算 Z-score
        mean = df[col].mean()
        std = df[col].std()

        if std == 0 or np.isnan(std):
            continue

        z_scores = np.abs((df[col] - mean) / std)
        outlier_mask = z_scores > threshold
        outlier_count = outlier_mask.sum()

        if outlier_count > 0:
            outliers[col] = {
                "count": int(outlier_count),
                "percentage": 100 * outlier_count / len(df),
                "min": float(df[col].min()),
                "max": float(df[col].max()),
                "mean": float(mean),
                "std": float(std),
            }

    return outliers


def check_feature_consistency(df: pd.DataFrame) -> dict:
    """检查特征一致性"""
    issues = []

    # 检查维度
    if len(df.columns) > 600:
        issues.append(
            {
                "type": "维度过高",
                "severity": "warning",
                "message": f"特征数 {len(df.columns)} 超过建议值 500",
            }
        )

    # 检查是否有 ID 字段泄露
    id_columns = [col for col in df.columns if col.endswith("Id") or col.endswith("_id")]
    if "match_id" in id_columns:
        id_columns.remove("match_id")  # match_id 是允许的

    if id_columns:
        issues.append(
            {
                "type": "ID 字段泄露",
                "severity": "warning",
                "message": f"发现 ID 字段: {', '.join(id_columns[:5])}",
            }
        )

    # 检查是否有全零列
    zero_columns = []
    for col in df.columns:
        if col == "match_id":
            continue
        if df[col].dtype in [np.float64, np.int64, float, int]:
            if (df[col] == 0).all():
                zero_columns.append(col)

    if zero_columns:
        issues.append(
            {
                "type": "全零特征",
                "severity": "info",
                "message": f"发现 {len(zero_columns)} 个全零特征",
            }
        )

    return {
        "total_issues": len(issues),
        "issues": issues,
    }


def extract_and_check_sample(raw_data_list: list[tuple[str, dict]]) -> dict:
    """抽取样本并检查质量"""
    refiner = V51FeatureRefiner(max_features=500)

    # 提取特征
    df = refiner.extract_batch(raw_data_list, show_progress=False)

    # 各项检查
    nan_check = check_nan_values(df)
    outlier_check = check_outliers(df)
    consistency_check = check_feature_consistency(df)

    # 基础统计
    basic_stats = {
        "sample_count": len(df),
        "feature_count": len(df.columns),
        "extraction_time_ms": refiner.stats.extraction_time_ms,
        "avg_time_per_match_ms": refiner.stats.extraction_time_ms / len(df) if df.size > 0 else 0,
    }

    return {
        "df": df,
        "basic_stats": basic_stats,
        "nan_check": nan_check,
        "outlier_check": outlier_check,
        "consistency_check": consistency_check,
    }


# ============================================================================
# 报告生成
# ============================================================================


def print_health_report(db_stats: dict, sample_check: dict, verbose: bool = False):
    """打印数据就绪度报告"""
    print("\n" + "=" * 70)
    print("V51.0 数据健康检查报告")
    print("=" * 70)
    print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 1. 数据库统计
    print("\n" + "─" * 70)
    print("📊 数据库统计")
    print("─" * 70)

    print(f"  Finished 比赛总数: {db_stats['total_finished']:,} 场")
    print(f"  有 raw_data 的比赛: {db_stats['with_raw_data']:,} 场")
    print(f"  数据覆盖率: {100 * db_stats['with_raw_data'] / max(db_stats['total_finished'], 1):.1f}%")

    min_date, max_date = db_stats["date_range"]
    print(f"  数据时间范围: {min_date} ~ {max_date}")

    # 赛季分布
    print("\n  赛季分布:")
    for season, count in db_stats["season_distribution"][:5]:
        print(f"    {season}: {count:,} 场")

    # 联赛分布
    print("\n  联赛分布 (Top 5):")
    for league, count in db_stats["league_distribution"][:5]:
        print(f"    {league}: {count:,} 场")

    # 2. 样本提取结果
    print("\n" + "─" * 70)
    print("🔬 样本提取结果")
    print("─" * 70)

    basic = sample_check["basic_stats"]
    print(f"  提取样本数: {basic['sample_count']} 场")
    print(f"  特征维度: {basic['feature_count']} 维")
    print(f"  提取耗时: {basic['extraction_time_ms']:.0f} ms")
    print(f"  平均耗时: {basic['avg_time_per_match_ms']:.1f} ms/场")

    # 3. NaN 检查
    print("\n" + "─" * 70)
    print("🔍 NaN 检查")
    print("─" * 70)

    nan_info = sample_check["nan_check"]
    if nan_info["total_nan"] == 0:
        print("  ✅ 未发现 NaN 值 - fillna 工作正常")
    else:
        print(f"  ⚠️  发现 {nan_info['total_nan']} 个 NaN 值 ({nan_info['nan_percentage']:.2f}%)")
        if verbose and nan_info["nan_columns"]:
            print("\n  NaN 分布:")
            for col, count in list(nan_info["nan_columns"].items())[:10]:
                print(f"    {col}: {count} 个")

    # 4. 异常值检查
    print("\n" + "─" * 70)
    print("⚠️  异常值检查")
    print("─" * 70)

    outliers = sample_check["outlier_check"]
    if not outliers:
        print("  ✅ 未发现显著异常值 (Z-score > 5)")
    else:
        print(f"  ⚠️  发现 {len(outliers)} 个特征存在异常值:")
        for col, info in list(outliers.items())[:5]:
            print(f"    {col}:")
            print(f"      异常数量: {info['count']} ({info['percentage']:.1f}%)")
            print(f"      范围: [{info['min']:.2f}, {info['max']:.2f}]")
            print(f"      均值±标准差: {info['mean']:.2f} ± {info['std']:.2f}")

    # 5. 特征一致性检查
    print("\n" + "─" * 70)
    print("🔧 特征一致性检查")
    print("─" * 70)

    consistency = sample_check["consistency_check"]
    if consistency["total_issues"] == 0:
        print("  ✅ 未发现一致性问题")
    else:
        print(f"  ⚠️  发现 {consistency['total_issues']} 个问题:")
        for issue in consistency["issues"]:
            icon = {"error": "❌", "warning": "⚠️ ", "info": "ℹ️  "}.get(issue["severity"], "•")
            print(f"    {icon} [{issue['type']}] {issue['message']}")

    # 6. 数据就绪度评分
    print("\n" + "─" * 70)
    print("📈 数据就绪度评分")
    print("─" * 70)

    score = 100
    reasons = []

    # 数据覆盖率 (40分)
    coverage = 100 * db_stats["with_raw_data"] / max(db_stats["total_finished"], 1)
    if coverage >= 95:
        score -= 0
    elif coverage >= 90:
        score -= 5
        reasons.append("数据覆盖率 < 95%")
    elif coverage >= 80:
        score -= 10
        reasons.append("数据覆盖率 < 90%")
    else:
        score -= 20
        reasons.append("数据覆盖率 < 80%")

    # 数据量 (20分)
    if db_stats["with_raw_data"] >= 8000:
        score -= 0
    elif db_stats["with_raw_data"] >= 5000:
        score -= 5
        reasons.append("数据量 < 8000")
    elif db_stats["with_raw_data"] >= 2000:
        score -= 10
        reasons.append("数据量 < 5000")
    else:
        score -= 20
        reasons.append("数据量不足")

    # NaN 检查 (20分)
    if nan_info["total_nan"] == 0:
        score -= 0
    elif nan_info["nan_percentage"] < 1:
        score -= 5
        reasons.append("存在少量 NaN")
    elif nan_info["nan_percentage"] < 5:
        score -= 10
        reasons.append("存在较多 NaN")
    else:
        score -= 20
        reasons.append("NaN 过多")

    # 异常值检查 (10分)
    if len(outliers) == 0:
        score -= 0
    elif len(outliers) < 5:
        score -= 3
        reasons.append("存在少量异常值")
    elif len(outliers) < 10:
        score -= 6
        reasons.append("存在中等异常值")
    else:
        score -= 10
        reasons.append("异常值过多")

    # 特征一致性 (10分)
    if consistency["total_issues"] == 0:
        score -= 0
    elif consistency["total_issues"] < 3:
        score -= 3
        reasons.append("存在少量一致性问题")
    else:
        score -= 10
        reasons.append("一致性问题较多")

    # 输出评分
    grade = "A" if score >= 90 else "B" if score >= 80 else "C" if score >= 70 else "D" if score >= 60 else "F"
    grade_color = {"A": "🟢", "B": "🟡", "C": "🟠", "D": "🔴", "F": "⛔"}[grade]

    print(f"  综合评分: {score}/100")
    print(f"  数据等级: {grade_color} {grade}")

    if reasons:
        print("\n  扣分原因:")
        for reason in reasons:
            print(f"    - {reason}")

    # 7. 结论
    print("\n" + "=" * 70)
    print("结论")
    print("=" * 70)

    if score >= 90:
        print("✅ 数据质量优秀，可以开始模型训练！")
    elif score >= 80:
        print("⚠️  数据质量良好，建议修复警告后开始训练。")
    elif score >= 70:
        print("⚠️  数据质量一般，存在一些问题需要修复。")
    else:
        print("❌ 数据质量不足，建议先解决数据问题。")

    print("=" * 70 + "\n")

    return score


# ============================================================================
# 主函数
# ============================================================================


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="V51.0 数据健康检查脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python scripts/maintenance/check_v51_data_health.py
  python scripts/maintenance/check_v51_data_health.py --sample-size 20
  python scripts/maintenance/check_v51_data_health.py --verbose
        """,
    )
    parser.add_argument("--sample-size", type=int, default=10, help="样本抽取数量 (默认: 10)")
    parser.add_argument("--verbose", action="store_true", help="详细输出")
    parser.add_argument("--outlier-threshold", type=float, default=5.0, help="异常值 Z-score 阈值 (默认: 5.0)")

    args = parser.parse_args()

    # 连接数据库
    settings = get_settings()
    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
    )

    try:
        # 1. 获取数据库统计
        logger.info("正在获取数据库统计...")
        db_stats = get_finished_matches_stats(conn)

        # 2. 随机抽取样本
        logger.info(f"正在随机抽取 {args.sample_size} 场比赛...")
        raw_data_list = get_random_matches(conn, limit=args.sample_size)

        if not raw_data_list:
            logger.error("未找到任何可用的比赛数据！")
            return 1

        # 3. 提取并检查特征
        logger.info("正在提取 V51 特征并检查质量...")
        sample_check = extract_and_check_sample(raw_data_list)

        # 4. 打印报告
        score = print_health_report(db_stats, sample_check, verbose=args.verbose)

        # 5. 返回退出码
        return 0 if score >= 80 else 1

    except Exception as e:
        logger.error(f"检查失败: {e}")
        import traceback

        traceback.print_exc()
        return 1

    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
