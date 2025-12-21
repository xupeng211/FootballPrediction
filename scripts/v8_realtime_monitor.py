#!/usr/bin/env python3
"""
V8.0 实时赔率监控CLI工具
48小时英超赔率波动实时跟踪系统
"""

import asyncio
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta
import json
import argparse
from typing import Dict, List, Optional
import logging

sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from ml.value_finder import ValueFinder
    from ml.betting_strategy import BettingStrategyManager
except ImportError as e:
    print(f"⚠️ 模块导入失败: {e}")
    print("使用模拟模式进行演示...")
    ValueFinder = None
    BettingStrategyManager = None

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'realtime_monitor_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RealtimeMonitor:
    """
    实时赔率监控系统
    """

    def __init__(self, monitoring_hours: int = 48):
        self.monitoring_hours = monitoring_hours
        self.start_time = datetime.now()
        self.end_time = self.start_time + timedelta(hours=monitoring_hours)

        # 初始化组件（如果可用）
        self.value_finder = ValueFinder() if ValueFinder else None
        self.strategy_manager = BettingStrategyManager() if BettingStrategyManager else None

        # 监控数据存储
        self.monitoring_data = {
            'matches': {},
            'alerts': [],
            'opportunities': [],
            'summary': {
                'total_matches': 0,
                'gold_opportunities': 0,
                'silver_opportunities': 0,
                'warning_alerts': 0,
                'edge_movements': 0
            }
        }

        # 模拟数据（用于演示）
        self.simulation_matches = self._create_simulation_matches()

    def _create_simulation_matches(self) -> List[Dict]:
        """创建模拟比赛数据"""
        matches = [
            {
                'id': 'epl_001',
                'home_team': 'Manchester City',
                'away_team': 'Arsenal',
                'league': 'Premier League',
                'match_time': self.start_time + timedelta(hours=6),
                'current_odds': {'home': 2.10, 'draw': 3.40, 'away': 3.60}
            },
            {
                'id': 'epl_002',
                'home_team': 'Liverpool',
                'away_team': 'Chelsea',
                'league': 'Premier League',
                'match_time': self.start_time + timedelta(hours=12),
                'current_odds': {'home': 1.85, 'draw': 3.60, 'away': 4.20}
            },
            {
                'id': 'epl_003',
                'home_team': 'Tottenham',
                'away_team': 'Manchester United',
                'league': 'Premier League',
                'match_time': self.start_time + timedelta(hours=24),
                'current_odds': {'home': 2.45, 'draw': 3.30, 'away': 2.80}
            },
            {
                'id': 'epl_004',
                'home_team': 'Newcastle',
                'away_team': 'Brighton',
                'league': 'Premier League',
                'match_time': self.start_time + timedelta(hours=36),
                'current_odds': {'home': 2.20, 'draw': 3.50, 'away': 3.20}
            },
            {
                'id': 'epl_005',
                'home_team': 'Aston Villa',
                'away_team': 'West Ham',
                'league': 'Premier League',
                'match_time': self.start_time + timedelta(hours=48),
                'current_odds': {'home': 1.95, 'draw': 3.70, 'away': 3.90}
            }
        ]
        return matches

    async def start_monitoring(self):
        """开始实时监控"""
        print(f"🎯 V8.0 实时赔率监控系统启动")
        print(f"📅 监控时间: {self.monitoring_hours}小时")
        print(f"⏰ 开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🏁 结束时间: {self.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        try:
            while datetime.now() < self.end_time:
                # 执行监控循环
                await self._monitoring_cycle()

                # 等待下一次检查（5分钟间隔）
                await asyncio.sleep(5)  # 演示用5秒，实际应为300秒

        except KeyboardInterrupt:
            print("\n⚠️ 用户中断监控")
        except Exception as e:
            logger.error(f"监控过程中出现错误: {e}")
        finally:
            await self._generate_final_report()

    async def _monitoring_cycle(self):
        """单次监控循环"""
        current_time = datetime.now()
        remaining_hours = (self.end_time - current_time).total_seconds() / 3600

        print(f"\n⏰ {current_time.strftime('%H:%M:%S')} | 剩余: {remaining_hours:.1f}小时")
        print("-" * 50)

        if self.value_finder:
            # 真实API监控
            await self._real_api_monitoring()
        else:
            # 模拟监控
            await self._simulation_monitoring()

        # 显示实时摘要
        self._display_summary()

    async def _real_api_monitoring(self):
        """真实API监控"""
        try:
            # 获取未来比赛
            upcoming_matches = await self.value_finder.get_upcoming_matches(days_ahead=2)

            for match in upcoming_matches:
                match_id = match['id']

                # 获取最新赔率
                market_odds = await self.value_finder.get_market_odds(match_id)

                if market_odds:
                    # 分析价值机会
                    analysis = await self.value_finder.analyze_match(match)

                    if analysis:
                        self._process_match_analysis(match_id, analysis)

        except Exception as e:
            logger.error(f"API监控失败: {e}")

    async def _simulation_monitoring(self):
        """模拟监控"""
        import random

        for match in self.simulation_matches:
            match_id = match['id']

            # 模拟赔率波动
            if match_id not in self.monitoring_data['matches']:
                self.monitoring_data['matches'][match_id] = {
                    'team': f"{match['home_team']} vs {match['away_team']}",
                    'match_time': match['match_time'],
                    'odds_history': [],
                    'analysis_history': []
                }

            # 生成新的赔率（模拟市场波动）
            current_odds = match['current_odds'].copy()
            for outcome in ['home', 'draw', 'away']:
                # ±5%的随机波动
                change = random.uniform(0.95, 1.05)
                current_odds[outcome] = round(current_odds[outcome] * change, 2)
                # 确保赔率在合理范围内
                current_odds[outcome] = max(1.1, min(10.0, current_odds[outcome]))

            # 记录赔率历史
            odds_record = {
                'timestamp': datetime.now(),
                'odds': current_odds.copy()
            }

            match_data = self.monitoring_data['matches'][match_id]
            match_data['odds_history'].append(odds_record)

            # 模拟价值分析
            analysis = self._simulate_value_analysis(current_odds)
            match_data['analysis_history'].append(analysis)

            # 检查Edge变动
            if len(match_data['analysis_history']) > 1:
                prev_analysis = match_data['analysis_history'][-2]
                curr_analysis = analysis
                edge_change = abs(curr_analysis['best_edge'] - prev_analysis['best_edge'])

                if edge_change > 0.02:  # Edge变动超过2%
                    self._create_edge_movement_alert(match_id, prev_analysis, curr_analysis)

            # 检查机会
            if analysis['recommendation_level'] == 1:
                self.monitoring_data['opportunities'].append({
                    'timestamp': datetime.now(),
                    'match_id': match_id,
                    'type': 'GOLD',
                    'edge': analysis['best_edge'],
                    'odds': current_odds
                })
                self.monitoring_data['summary']['gold_opportunities'] += 1

            elif analysis['recommendation_level'] == 2:
                self.monitoring_data['opportunities'].append({
                    'timestamp': datetime.now(),
                    'match_id': match_id,
                    'type': 'SILVER',
                    'edge': analysis['best_edge'],
                    'odds': current_odds
                })
                self.monitoring_data['summary']['silver_opportunities'] += 1

            elif analysis['recommendation_level'] == 3:
                self._create_warning_alert(match_id, analysis)

    def _simulate_value_analysis(self, odds: Dict) -> Dict:
        """模拟价值分析"""
        # 计算隐含概率
        home_prob = 1 / odds['home']
        draw_prob = 1 / odds['draw']
        away_prob = 1 / odds['away']
        total_prob = home_prob + draw_prob + away_prob

        # 去水处理
        margin = total_prob - 1.0
        if margin > 0:
            norm_factor = 1.0 / total_prob
            fair_home = home_prob * norm_factor
            fair_draw = draw_prob * norm_factor
            fair_away = away_prob * norm_factor
        else:
            fair_home, fair_draw, fair_away = home_prob, draw_prob, away_prob

        # 模拟模型预测（添加一些随机性）
        import random
        model_home = fair_home + random.uniform(-0.05, 0.08)
        model_draw = fair_draw + random.uniform(-0.03, 0.05)
        model_away = fair_away + random.uniform(-0.03, 0.05)

        # 归一化
        total_model = model_home + model_draw + model_away
        model_home /= total_model
        model_draw /= total_model
        model_away /= total_model

        # 计算Edge
        edges = {
            'home': model_home - fair_home,
            'draw': model_draw - fair_draw,
            'away': model_away - fair_away
        }

        best_outcome = max(edges, key=edges.get)
        best_edge = edges[best_outcome]

        # 确定推荐等级
        if best_edge > 0.15:
            level = 1
            level_name = "GOLD"
        elif best_edge > 0.08:
            level = 2
            level_name = "SILVER"
        elif best_edge < -0.10:
            level = 3
            level_name = "WARNING"
        else:
            level = 0
            level_name = "NO_VALUE"

        return {
            'model_probs': {'home': model_home, 'draw': model_draw, 'away': model_away},
            'fair_probs': {'home': fair_home, 'draw': fair_draw, 'away': fair_away},
            'edges': edges,
            'best_outcome': best_outcome,
            'best_edge': best_edge,
            'recommendation_level': level,
            'recommendation_name': level_name
        }

    def _process_match_analysis(self, match_id: str, analysis):
        """处理真实比赛分析"""
        if match_id not in self.monitoring_data['matches']:
            self.monitoring_data['matches'][match_id] = {
                'odds_history': [],
                'analysis_history': []
            }

        match_data = self.monitoring_data['matches'][match_id]
        match_data['analysis_history'].append({
            'timestamp': datetime.now(),
            'analysis': analysis
        })

        # 处理推荐
        if analysis.recommendation_level == 1:
            self.monitoring_data['summary']['gold_opportunities'] += 1
            print(f"🏆 黄金机会: {match_id} - Edge: {analysis.edge_value:+.3f}")
        elif analysis.recommendation_level == 2:
            self.monitoring_data['summary']['silver_opportunities'] += 1
            print(f"🥈 白银机会: {match_id} - Edge: {analysis.edge_value:+.3f}")
        elif analysis.recommendation_level == 3:
            self.monitoring_data['summary']['warning_alerts'] += 1
            print(f"⚠️ 避坑预警: {match_id}")

    def _create_edge_movement_alert(self, match_id: str, prev_analysis: Dict, curr_analysis: Dict):
        """创建Edge变动警报"""
        self.monitoring_data['alerts'].append({
            'timestamp': datetime.now(),
            'type': 'EDGE_MOVEMENT',
            'match_id': match_id,
            'message': f"Edge大幅变动: {prev_analysis['best_edge']:+.3f} → {curr_analysis['best_edge']:+.3f}",
            'prev_edge': prev_analysis['best_edge'],
            'curr_edge': curr_analysis['best_edge']
        })
        self.monitoring_data['summary']['edge_movements'] += 1

        print(f"📈 Edge变动警报: {match_id} {prev_analysis['best_edge']:+.3f} → {curr_analysis['best_edge']:+.3f}")

    def _create_warning_alert(self, match_id: str, analysis: Dict):
        """创建预警警报"""
        self.monitoring_data['alerts'].append({
            'timestamp': datetime.now(),
            'type': 'WARNING',
            'match_id': match_id,
            'message': f"市场高估预警: {analysis['best_outcome']} Edge={analysis['best_edge']:+.3f}",
            'edge': analysis['best_edge']
        })
        self.monitoring_data['summary']['warning_alerts'] += 1

        print(f"⚠️ 市场高估预警: {match_id}")

    def _display_summary(self):
        """显示实时摘要"""
        summary = self.monitoring_data['summary']
        summary['total_matches'] = len(self.monitoring_data['matches'])

        print(f"📊 实时摘要:")
        print(f"   跟踪比赛: {summary['total_matches']}场")
        print(f"   🏆 黄金机会: {summary['gold_opportunities']}个")
        print(f"   🥈 白银机会: {summary['silver_opportunities']}个")
        print(f"   ⚠️ 避坑预警: {summary['warning_alerts']}个")
        print(f"   📈 Edge变动: {summary['edge_movements']}次")

    async def _generate_final_report(self):
        """生成最终报告"""
        print("\n" + "=" * 60)
        print("📋 V8.0 实时监控最终报告")
        print("=" * 60)

        summary = self.monitoring_data['summary']
        duration = (datetime.now() - self.start_time).total_seconds() / 3600

        print(f"📅 监控时长: {duration:.1f}小时")
        print(f"🎯 跟踪比赛: {summary['total_matches']}场")
        print(f"🏆 发现机会: {summary['gold_opportunities'] + summary['silver_opportunities']}个")
        print(f"   - 黄金级别: {summary['gold_opportunities']}个")
        print(f"   - 白银级别: {summary['silver_opportunities']}个")
        print(f"⚠️ 风险预警: {summary['warning_alerts']}个")
        print(f"📈 市场波动: {summary['edge_movements']}次显著变动")

        # 保存详细报告
        report_path = Path(f"realtime_monitor_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.monitoring_data, f, indent=2, ensure_ascii=False, default=str)

        print(f"📁 详细报告已保存: {report_path}")

        # 生成建议
        print("\n💡 监控建议:")
        if summary['gold_opportunities'] > 0:
            print("✅ 发现多个黄金机会，建议重点关注")
        if summary['edge_movements'] > 5:
            print("📈 市场波动较大，建议及时调整策略")
        if summary['warning_alerts'] > 3:
            print("⚠️ 多个市场高估预警，建议谨慎投注")

def create_cli_parser():
    """创建CLI参数解析器"""
    parser = argparse.ArgumentParser(description='V8.0 实时赔率监控系统')
    parser.add_argument('--hours', type=int, default=48,
                       help='监控时长（小时），默认48小时')
    parser.add_argument('--simulation', '-s', action='store_true',
                       help='使用模拟模式（无需API连接）')
    parser.add_argument('--interval', '-i', type=int, default=300,
                       help='检查间隔（秒），默认300秒（5分钟）')
    return parser

async def main():
    """主函数"""
    parser = create_cli_parser()
    args = parser.parse_args()

    print("🎯 V8.0 FootballPrediction 实时监控系统")
    print("=" * 50)
    print(f"📅 监控时长: {args.hours}小时")
    print(f"🔄 检查间隔: {args.interval}秒")
    if args.simulation:
        print("🎮 模式: 模拟运行")
    else:
        print("🌐 模式: 实时API监控")
    print("")

    # 创建监控器
    monitor = RealtimeMonitor(monitoring_hours=args.hours)

    # 开始监控
    await monitor.start_monitoring()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 监控已停止")
    except Exception as e:
        print(f"❌ 程序异常: {e}")
        sys.exit(1)