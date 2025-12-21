#!/usr/bin/env python3
"""
V4.2: 真实赔率CSV处理器
Real Odds CSV Processor - Football-Data.co.uk Integration

目的:
1. 扫描 data/external/ 目录中的 Football-Data.co.uk CSV 文件
2. 解析真实历史赔率数据
3. 物理合并到我们的 517 场训练集中
4. 替换所有模拟赔率为真实市场数据
"""

import pandas as pd
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import re

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class RealOddsCSVProcessor:
    """真实赔率CSV处理器"""

    def __init__(self):
        logger.info("🏆 V4.2 真实赔率CSV处理器启动")
        logger.info("🎯 目标: 对接Football-Data.co.uk真实历史赔率数据")

        self.db_config = {
            "host": "localhost",
            "port": 5432,
            "database": "football_prediction_dev",
            "user": "football_user",
            "password": "football_pass",
        }

        # Football-Data.co.uk 标准列映射
        self.football_data_columns = {
            'Date': 'match_date',
            'HomeTeam': 'home_team',
            'AwayTeam': 'away_team',
            'FTHG': 'home_score',      # Full Time Home Goals
            'FTAG': 'away_score',      # Full Time Away Goals
            'FTR': 'result',          # Full Time Result (H/D/A)

            # 赔率相关列 (不同赛季可能有不同的列名)
            'B365H': 'bet365_home_odds',     # Bet365 home odds
            'B365D': 'bet365_draw_odds',     # Bet365 draw odds
            'B365A': 'bet365_away_odds',     # Bet365 away odds
            'BWH': 'betway_home_odds',       # Betway home odds
            'BWD': 'betway_draw_odds',       # Betway draw odds
            'BWA': 'betway_away_odds',       # Betway away odds
            'IWH': 'interwetten_home_odds',  # Interwetten home odds
            'IWD': 'interwetten_draw_odds',  # Interwetten draw odds
            'IWA': 'interwetten_away_odds',  # Interwetten away odds
            'WHH': 'william_hill_home_odds', # William Hill home odds
            'WHD': 'william_hill_draw_odds', # William Hill draw odds
            'WHA': 'william_hill_away_odds', # William Hill away odds

            # 其他重要列
            'Div': 'division',
            'Season': 'season',
        }

    def scan_external_directory(self) -> List[Path]:
        """扫描external目录中的CSV文件"""
        logger.info("🔍 扫描 data/external/ 目录...")

        external_dir = Path("data/external")
        if not external_dir.exists():
            external_dir.mkdir(parents=True, exist_ok=True)
            logger.warning("📁 创建 external 目录: data/external/")
            return []

        csv_files = list(external_dir.glob("*.csv"))
        logger.info(f"📁 找到 {len(csv_files)} 个CSV文件:")
        for csv_file in csv_files:
            logger.info(f"   📄 {csv_file.name} ({csv_file.stat().st_size / 1024:.1f} KB)")

        return csv_files

    def analyze_csv_structure(self, csv_path: Path) -> Dict[str, any]:
        """分析CSV文件结构"""
        logger.info(f"📊 分析CSV文件结构: {csv_path.name}")

        try:
            # 读取前几行分析结构
            df_sample = pd.read_csv(csv_path, nrows=5)

            analysis = {
                'file_name': csv_path.name,
                'total_columns': len(df_sample.columns),
                'sample_rows': len(df_sample),
                'columns': list(df_sample.columns),
                'odds_columns': self._identify_odds_columns(df_sample.columns),
                'data_quality': self._assess_data_quality(df_sample),
            }

            logger.info(f"   📋 总列数: {analysis['total_columns']}")
            logger.info(f"   💰 赔率列数: {len(analysis['odds_columns'])}")
            logger.info(f"   ✅ 数据质量: {analysis['data_quality']}")

            return analysis

        except Exception as e:
            logger.error(f"❌ CSV结构分析失败 {csv_path.name}: {e}")
            return {'error': str(e)}

    def _identify_odds_columns(self, columns: List[str]) -> List[str]:
        """识别赔率相关列"""
        odds_patterns = [
            'B365', 'BW', 'IW', 'WH',  # 博彩公司前缀
            'H', 'D', 'A',            # Home, Draw, Away 后缀
            'Avg', 'Max', 'Min'        # 平均值、最大值、最小值
        ]

        odds_columns = []
        for col in columns:
            col_upper = col.upper()
            if any(pattern in col_upper for pattern in odds_patterns):
                odds_columns.append(col)

        return odds_columns

    def _assess_data_quality(self, df_sample: pd.DataFrame) -> str:
        """评估数据质量"""
        # 简单的数据质量评估
        if len(df_sample) == 0:
            return "EMPTY"

        non_empty_ratio = (df_sample.count().sum() / (len(df_sample) * len(df_sample.columns))) * 100

        if non_empty_ratio > 80:
            return "EXCELLENT"
        elif non_empty_ratio > 60:
            return "GOOD"
        elif non_empty_ratio > 40:
            return "FAIR"
        else:
            return "POOR"

    def process_csv_file(self, csv_path: Path) -> Dict[str, any]:
        """处理单个CSV文件"""
        logger.info(f"🔄 处理CSV文件: {csv_path.name}")

        try:
            # 读取完整CSV文件
            df = pd.read_csv(csv_path)
            logger.info(f"   📊 总行数: {len(df)}")

            # 清理和标准化列名
            df = self._standardize_columns(df)

            # 数据清理
            df = self._clean_data(df)

            # 提取赔率统计
            odds_stats = self._extract_odds_statistics(df)

            return {
                'file_name': csv_path.name,
                'total_matches': len(df),
                'odds_stats': odds_stats,
                'sample_data': df.head(3).to_dict('records'),
                'status': 'SUCCESS'
            }

        except Exception as e:
            logger.error(f"❌ CSV处理失败 {csv_path.name}: {e}")
            return {'file_name': csv_path.name, 'error': str(e), 'status': 'FAILED'}

    def _standardize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化列名"""
        # 创建列名映射
        column_mapping = {}

        for col in df.columns:
            # 寻找Football-Data.co.uk标准列
            for standard_col, mapped_name in self.football_data_columns.items():
                if standard_col.lower() in col.lower() or col.lower() in standard_col.lower():
                    column_mapping[col] = mapped_name
                    break

        # 应用列名映射
        df = df.rename(columns=column_mapping)

        logger.info(f"   🏷️ 标准化了 {len(column_mapping)} 个列名")
        return df

    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """清理数据"""
        original_rows = len(df)

        # 移除空行
        df = df.dropna(subset=['home_team', 'away_team'], how='any')

        # 清理日期格式
        if 'match_date' in df.columns:
            df['match_date'] = pd.to_datetime(df['match_date'], errors='coerce')
            df = df.dropna(subset=['match_date'])

        # 移除没有赔率数据的行
        odds_columns = [col for col in df.columns if 'odds' in col.lower()]
        if odds_columns:
            df = df.dropna(subset=odds_columns, how='all')

        logger.info(f"   🧹 数据清理: {original_rows} → {len(df)} 行 (保留 {(len(df)/original_rows)*100:.1f}%)")
        return df

    def _extract_odds_statistics(self, df: pd.DataFrame) -> Dict[str, any]:
        """提取赔率统计信息"""
        odds_stats = {
            'total_matches_with_odds': 0,
            'odds_sources': {},
            'odds_ranges': {}
        }

        # 统计各博彩公司的数据覆盖率
        odds_columns = [col for col in df.columns if 'odds' in col.lower()]

        for col in odds_columns:
            non_null_count = df[col].count()
            coverage = (non_null_count / len(df)) * 100

            odds_stats['odds_sources'][col] = {
                'coverage': coverage,
                'valid_values': non_null_count,
                'avg_odds': df[col].mean() if non_null_count > 0 else None
            }

        odds_stats['total_matches_with_odds'] = len(df.dropna(subset=odds_columns, how='all'))

        return odds_stats

    def merge_with_training_data(self, csv_data: Dict[str, any]) -> Dict[str, any]:
        """将真实赔率数据合并到训练集"""
        logger.info("🔗 开始合并真实赔率数据到训练集...")

        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # 获取当前训练集统计
            cursor.execute("SELECT COUNT(*) as total FROM match_features_training")
            total_training = cursor.fetchone()['total']
            logger.info(f"   📊 当前训练集大小: {total_training} 场")

            # 这里应该实现具体的合并逻辑
            # 由于CSV格式可能不同，需要根据实际情况调整

            merge_stats = {
                'csv_matches': csv_data.get('total_matches', 0),
                'training_matches': total_training,
                'potential_matches': min(csv_data.get('total_matches', 0), total_training),
                'merge_status': 'READY_FOR_IMPLEMENTATION'
            }

            conn.close()
            return merge_stats

        except Exception as e:
            logger.error(f"❌ 数据合并失败: {e}")
            return {'error': str(e), 'merge_status': 'FAILED'}

    def generate_processing_report(self, csv_files: List[Path], results: List[Dict[str, any]]) -> Dict[str, any]:
        """生成处理报告"""
        logger.info("📋 生成真实赔率数据处理报告")

        report = {
            'processing_version': 'V4.2',
            'processing_date': datetime.now().isoformat(),
            'summary': {
                'total_csv_files': len(csv_files),
                'successful_processing': len([r for r in results if r.get('status') == 'SUCCESS']),
                'failed_processing': len([r for r in results if r.get('status') == 'FAILED']),
                'total_odds_matches': sum(r.get('total_matches', 0) for r in results),
                'odds_sources_identified': set()
            },
            'detailed_results': results,
            'merge_recommendations': [],
            'next_steps': []
        }

        # 收集所有赔率来源
        for result in results:
            if 'odds_stats' in result and 'odds_sources' in result['odds_stats']:
                report['summary']['odds_sources_identified'].update(result['odds_stats']['odds_sources'].keys())

        # 生成合并建议
        if report['summary']['total_odds_matches'] > 0:
            report['merge_recommendations'] = [
                "✅ 发现真实赔率数据，建议立即合并到训练集",
                f"🎯 可更新 {min(report['summary']['total_odds_matches'], 517)} 场比赛的赔率数据",
                "💡 建议使用平均赔率避免单一博彩公司偏差",
                "⚠️ 需要验证日期和球队名称匹配逻辑"
            ]

        # 下一步行动
        report['next_steps'] = [
            "🔄 实现比赛匹配算法 (日期 + 球队名称)",
            "📊 批量更新数据库中的赔率字段",
            "🏷️ 将 has_real_odds 标记为 TRUE",
            "🎯 使用真实赔率重新训练V4.2模型"
        ]

        return report


def main():
    """主程序"""
    logger.info("🚀 V4.2 真实赔率CSV处理器启动")

    try:
        processor = RealOddsCSVProcessor()

        # 1. 扫描external目录
        csv_files = processor.scan_external_directory()

        if not csv_files:
            logger.warning("⚠️ 未找到CSV文件，请在 data/external/ 目录放置Football-Data.co.uk数据")
            logger.info("💡 下载地址: https://www.football-data.co.uk/data.php")
            return

        # 2. 分析和处理CSV文件
        results = []
        for csv_file in csv_files:
            logger.info(f"\n{'='*60}")

            # 分析结构
            structure = processor.analyze_csv_structure(csv_file)
            if 'error' in structure:
                results.append(structure)
                continue

            # 处理数据
            processed = processor.process_csv_file(csv_file)
            results.append(processed)

        # 3. 生成处理报告
        report = processor.generate_processing_report(csv_files, results)

        # 4. 保存报告
        report_file = f"reports/v4_2_real_odds_processing_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        import json
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"\n🎉 V4.2 真实赔率处理完成!")
        logger.info(f"📄 详细报告: {report_file}")
        logger.info(f"📊 处理统计: {report['summary']['successful_processing']}/{report['summary']['total_csv_files']} 成功")
        logger.info(f"💰 发现赔率来源: {len(report['summary']['odds_sources_identified'])} 个")

        # 5. 展示关键发现
        logger.info(f"\n🔍 关键发现:")
        for rec in report['merge_recommendations']:
            logger.info(f"   {rec}")

        logger.info(f"\n📋 下一步行动:")
        for step in report['next_steps']:
            logger.info(f"   {step}")

    except Exception as e:
        logger.error(f"❌ V4.2 真实赔率处理失败: {e}")
        raise


if __name__ == "__main__":
    main()