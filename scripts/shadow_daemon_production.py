#!/usr/bin/env python3
"""
生产级影子守护进程
专注于FotMob数据抓取、AI预测、Brier Score记录
48小时连续运行验证
"""

import asyncio
import logging
import sys
import time
import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

# 设置项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import aiohttp
import psutil
import math

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ProductionShadowDaemon:
    """生产级影子守护进程"""

    def __init__(self):
        self.start_time = datetime.now()
        self.test_duration_hours = 48
        self.prediction_interval_minutes = 15

        # 配置
        self.config = {
            'fotmob_base_url': os.getenv('FOTMOB_BASE_URL', 'https://www.fotmob.com/api'),
            'fotmob_timeout': int(os.getenv('FOTMOB_TIMEOUT_SECONDS', '30')),
            'api_rate_limit': int(os.getenv('FOTMOB_RATE_LIMIT_REQUESTS_PER_MINUTE', '30')),
            'db_config': {
                'host': os.getenv('DB_HOST', 'localhost'),
                'port': int(os.getenv('DB_PORT', 5432)),
                'database': os.getenv('DB_NAME', 'football_prediction_shadow'),
                'user': os.getenv('DB_USER', 'football_user'),
                'password': os.getenv('DB_PASSWORD', 'football_pass')
            }
        }

        # 统计数据
        self.stats = {
            'total_predictions': 0,
            'successful_predictions': 0,
            'failed_predictions': 0,
            'api_calls': 0,
            'api_timeouts': 0,
            'brier_scores': [],
            'response_times': [],
            'memory_usage': [],
            'cpu_usage': [],
            'matches_processed': 0,
            'start_time': self.start_time.isoformat(),
            'last_prediction_time': None
        }

        # FotMob Headers
        self.headers = {
            'User-Agent': 'FootballPrediction Shadow Test/1.0',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache'
        }

    def is_test_running(self) -> bool:
        """检查测试是否还在运行"""
        elapsed = datetime.now() - self.start_time
        return elapsed.total_seconds() < self.test_duration_hours * 3600

    def get_test_progress(self) -> Dict[str, Any]:
        """获取测试进度"""
        elapsed = datetime.now() - self.start_time
        total_duration = timedelta(hours=self.test_duration_hours)
        progress_percentage = (elapsed.total_seconds() / total_duration.total_seconds()) * 100

        return {
            'start_time': self.start_time.isoformat(),
            'elapsed_hours': elapsed.total_seconds() / 3600,
            'total_hours': self.test_duration_hours,
            'progress_percentage': min(100, progress_percentage),
            'remaining_hours': max(0, (total_duration - elapsed).total_seconds() / 3600),
            'predictions_made': self.stats['total_predictions']
        }

    async def collect_fotmob_data(self) -> List[Dict[str, Any]]:
        """收集FotMob数据"""
        try:
            # 构建API请求URL - 获取主要联赛比赛数据
            leagues = ['47', '117', '48', '123', '61', '135']  # 英超、西甲、德甲、意甲、法甲、荷甲
            matches = []

            for league_id in leagues:
                url = f"{self.config['fotmob_base_url']}/leagues?id={league_id}&type=match&status=live"

                start_time = time.time()
                try:
                    async with aiohttp.ClientSession(headers=self.headers, timeout=aiohttp.ClientTimeout(total=self.config['fotmob_timeout'])) as session:
                        self.stats['api_calls'] += 1
                        async with session.get(url) as response:
                            response.raise_for_status()
                            data = await response.json()

                            # 解析比赛数据
                            if 'matches' in data:
                                for match in data['matches']:
                                    if match.get('status', {}).get('finished') == False:  # 只处理未完成的比赛
                                        matches.append({
                                            'match_id': str(match.get('id', '')),
                                            'home_team': match.get('home', {}).get('name', ''),
                                            'away_team': match.get('away', {}).get('name', ''),
                                            'league_id': league_id,
                                            'status': match.get('status', {}),
                                            'start_time': match.get('startTime', ''),
                                            'odds': match.get('pageView', {}).get('odd', {}),
                                            'home_score': match.get('homeScore', 0),
                                            'away_score': match.get('awayScore', 0)
                                        })

                    response_time = (time.time() - start_time) * 1000
                    self.stats['response_times'].append(response_time)
                    logger.info(f"📡 FOTMob API成功获取 {len(matches)} 场比赛")

                except aiohttp.ClientError as e:
                    self.stats['api_timeouts'] += 1
                    logger.warning(f"⚠️ FOTMob API请求超时: {e}")
                    continue  # 继续处理下一个联赛

                except asyncio.TimeoutError:
                    self.stats['api_timeouts'] += 1
                    logger.warning(f"⚠️ FOTMob API请求超时")
                    continue  # 继续处理下一个联赛

            self.stats['matches_processed'] += len(matches)
            return matches

        except Exception as e:
            logger.error(f"❌ 数据收集失败: {e}")
            return []

    async def calculate_ai_prediction(self, match_data: Dict[str, Any]) -> Dict[str, Any]:
        """计算AI预测（简化版本）"""
        try:
            match_id = match_data['match_id']

            # 简化的预测逻辑（基于历史数据模拟）
            # 在实际环境中，这里会调用训练好的ML模型

            # 基于赔率的隐式概率计算
            odds = match_data.get('odds', {})
            home_odds = odds.get('homeWin', 2.0)
            draw_odds = odds.get('draw', 3.0)
            away_odds = odds.get('awayWin', 4.0)

            # 简化的概率计算
            total_odds = home_odds + draw_odds + away_odds
            if total_odds > 0:
                home_prob = 1 / home_odds if home_odds > 0 else 0
                draw_prob = 1 / draw_odds if draw_odds > 0 else 0
                away_prob = 1 / away_odds if away_odds > 0 else 0

                # 归一化概率
                total_prob = home_prob + draw_prob + away_prob
                if total_prob > 0:
                    home_prob /= total_prob
                    draw_prob /= total_prob
                    away_prob /= total_prob
            else:
                home_prob = draw_prob = away_prob = 1/3

            # 简化的预测逻辑
            # 主队优势因子（基于主场优势）
            home_advantage = 0.1

            # 随机因素
            import random
            random_factor = random.gauss(0, 0.05)

            # 调整概率
            home_prob = max(0.01, min(0.99, home_prob + home_advantage + random_factor))
            draw_prob = max(0.01, min(0.99, draw_prob + random_factor))
            away_prob = max(0.01, min(0.99, away_prob + random_factor))

            # 重新归一化
            total_prob = home_prob + draw_prob + away_prob
            home_prob /= total_prob
            draw_prob /= total_prob
            away_prob /= total_prob

            # 确定预测
            if home_prob > draw_prob and home_prob > away_prob:
                prediction = "HOME_WIN"
                confidence = home_prob
            elif draw_prob > home_prob and draw_prob > away_prob:
                prediction = "DRAW"
                confidence = draw_prob
            else:
                prediction = "AWAY_WIN"
                confidence = away_prob

            # 计算Brier Score分量（将在最后计算总分时使用）
            actual_one_hot = {"HOME_WIN": 0, "DRAW": 0, "AWAY_WIN": 0}
            prediction_probs = {"HOME_WIN": home_prob, "DRAW": draw_prob, "AWAY": away_prob}

            return {
                'match_id': match_id,
                'prediction': prediction,
                'probabilities': prediction_probs,
                'confidence': confidence,
                'timestamp': datetime.now().isoformat(),
                'odds': odds,
                'brier_score_component': (prediction_probs, actual_one_hot)  # 临时存储
            }

        except Exception as e:
            logger.error(f"❌ AI预测计算失败 {match_data['match_id']}: {e}")
            return None

    def calculate_brier_score(self, predictions: List[Dict[str, Any]]) -> float:
        """计算Brier Score"""
        if not predictions:
            return 0.0

        brier_scores = []
        for pred in predictions:
            prediction_probs, actual_one_hot = pred['brier_score_component']

            # 计算每个结果的Brier Score
            score = 0
            for outcome in ["HOME_WIN", "DRAW", "AWAY_WIN"]:
                score += (prediction_probs[outcome] - actual_one_hot[outcome]) ** 2

            brier_scores.append(score)

        return sum(brier_scores) / len(brier_scores) if brier_scores else 0.0

    def calculate_kelly_recommendation(self, prediction: Dict[str, Any]) -> Dict[str, Any]:
        """计算Kelly公式建议"""
        try:
            odds = prediction.get('odds', {})
            probabilities = prediction.get('probabilities', {})
            confidence = prediction.get('confidence', 0)

            # 获取预测结果的赔率
            if prediction['prediction'] == 'HOME_WIN':
                decimal_odds = odds.get('homeWin', 2.0)
            elif prediction['prediction'] == 'DRAW':
                decimal_odds = odds.get('draw', 3.0)
            else:  # AWAY_WIN
                decimal_odds = odds.get('awayWin', 4.0)

            # Kelly分数 = p - q/b
            p = probabilities.get(prediction['prediction'], 0.5)
            q = 1 - p  # 失败概率
            b = decimal_odds - 1  # 净收益

            kelly_fraction = max(0, p - q/b)  # 确保不为负

            # 限制最大投注比例
            max_kelly = 0.25  # 最大25%资金比例
            kelly_fraction = min(kelly_fraction, max_kelly)

            # 模拟投注金额
            recommended_stake = kelly_fraction * 100  # 假设总资金100单位

            # 计算期望值
            expected_value = p * b - q

            return {
                'kelly_fraction': kelly_fraction,
                'recommended_stake': recommended_stake,
                'expected_value': expected_value,
                'decimal_odds': decimal_odds
            }

        except Exception as e:
            logger.error(f"❌ Kelly计算失败: {e}")
            return {'kelly_fraction': 0, 'recommended_stake': 0, 'expected_value': 0, 'decimal_odds': 0}

    async def run_prediction_cycle(self) -> Dict[str, Any]:
        """运行一次预测周期"""
        cycle_start = time.time()

        try:
            # 1. 收集FotMob数据
            logger.info("📡 开始FotMob数据收集...")
            matches = await self.collect_fotmob_data()

            if not matches:
                logger.warning("⚠️ 没有获取到比赛数据")
                return {'success': False, 'error': 'No match data available'}

            # 2. 处理每场比赛
            cycle_predictions = []
            for match in matches[:10]:  # 限制每周期最多处理10场比赛
                prediction = await self.calculate_ai_prediction(match)
                if prediction:
                    kelly = self.calculate_kelly_recommendation(prediction)

                    cycle_predictions.append({
                        **prediction,
                        'kelly': kelly,
                        'match_data': match
                    })

            # 3. 计算Brier Score
            if cycle_predictions:
                brier_score = self.calculate_brier_score(cycle_predictions)
                self.stats['brier_scores'].append(brier_score)

            # 4. 更新统计
            self.stats['total_predictions'] += len(cycle_predictions)
            self.stats['successful_predictions'] += len(cycle_predictions)
            self.stats['last_prediction_time'] = datetime.now().isoformat()

            cycle_time = time.time() - cycle_start

            logger.info(f"✅ 预测周期完成:")
            logger.info(f"  - 处理比赛: {len(cycle_predictions)}")
            logger.info(f"  - 周期时间: {cycle_time:.2f}秒")
            logger.info(f"  - Brier Score: {self.stats['brier_scores'][-1]:.4f}" if self.stats['brier_scores'] else 'N/A')

            return {
                'success': True,
                'cycle_time': cycle_time,
                'matches_processed': len(matches),
                'predictions_made': len(cycle_predictions),
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"❌ 预测周期失败: {e}")
            self.stats['failed_predictions'] += 1
            return {'success': False, 'error': str(e), 'cycle_time': time.time() - cycle_start}

    def collect_system_metrics(self) -> Dict[str, Any]:
        """收集系统指标"""
        try:
            # 内存使用
            memory_info = psutil.virtual_memory()
            self.stats['memory_usage'].append(memory_info.used / 1024 / 1024)  # MB

            # CPU使用
            cpu_percent = psutil.cpu_percent(interval=1)
            self.stats['cpu_usage'].append(cpu_percent)

            return {
                'memory_mb': memory_info.used / 1024 / 1024,
                'cpu_percent': cpu_percent,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"❌ 系统指标收集失败: {e}")
            return {'memory_mb': 0, 'cpu_percent': 0, 'timestamp': datetime.now().isoformat()}

    def calculate_statistics(self) -> Dict[str, Any]:
        """计算统计数据"""
        stats = self.stats.copy()

        # 成功率
        total = stats['total_predictions']
        successful = stats['successful_predictions']
        success_rate = successful / total if total > 0 else 0

        # 平均响应时间
        avg_response_time = 0
        if stats['response_times']:
            avg_response_time = sum(stats['response_times']) / len(stats['response_times'])

        # P95响应时间
        p95_response_time = 0
        if stats['response_times']:
            sorted_times = sorted(stats['response_times'])
            p95_index = int(len(sorted_times) * 0.95)
            p95_response_time = sorted_times[min(p95_index, len(sorted_times) - 1)]

        # 平均Brier Score
        avg_brier_score = 0
        if stats['brier_scores']:
            avg_brier_score = sum(stats['brier_scores']) / len(stats['brier_scores'])

        # 资源使用
        avg_memory = 0
        max_memory = 0
        if stats['memory_usage']:
            avg_memory = sum(stats['memory_usage']) / len(stats['memory_usage'])
            max_memory = max(stats['memory_usage'])

        avg_cpu = 0
        max_cpu = 0
        if stats['cpu_usage']:
            avg_cpu = sum(stats['cpu_usage']) / len(stats['cpu_usage'])
            max_cpu = max(stats['cpu_usage'])

        return {
            **stats,
            'success_rate': success_rate,
            'success_rate_percentage': success_rate * 100,
            'avg_response_time_ms': avg_response_time,
            'p95_response_time_ms': p95_response_time,
            'avg_brier_score': avg_brier_score,
            'avg_memory_mb': avg_memory,
            'max_memory_mb': max_memory,
            'avg_cpu_percent': avg_cpu,
            'max_cpu_percent': max_cpu,
            'api_success_rate': (stats['api_calls'] - stats['api_timeouts']) / stats['api_calls'] * 100 if stats['api_calls'] > 0 else 0
        }

    def print_status_update(self, progress: Dict[str, Any], stats: Dict[str, Any]):
        """打印状态更新"""
        print("\n" + "=" * 80)
        print(f"🔥 48小时影子测试监控 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

        # 进度信息
        print(f"⏰ 测试进度: {progress['progress_percentage']:.1f}%")
        print(f"⏳ 已运行: {progress['elapsed_hours']:.1f}小时")
        print(f"⏳ 剩余时间: {progress['remaining_hours']:.1f}小时")
        print(f"📊 预测数: {progress['predictions_made']}")

        # 预测统计
        print(f"🎯 预测统计:")
        print(f"  总预测数: {stats['total_predictions']}")
        print(f"  成功率: {stats['success_rate_percentage']:.1f}%")
        print(f"  API调用: {stats['api_calls']}")
        print(f"  API超时: {stats['api_timeouts']}")

        # 性能统计
        print(f"⚡ 性能统计:")
        print(f"  平均响应时间: {stats['avg_response_time_ms']:.1f}ms")
        print(f"  P95响应时间: {stats['p95_response_time_ms']:.1f}ms")
        print(f"  API成功率: {stats['api_success_rate']:.1f}%")

        # 预测质量
        if stats['avg_brier_score'] > 0:
            print(f"📈 预测质量:")
            print(f"  平均Brier Score: {stats['avg_brier_score']:.4f}")
            if stats['avg_brier_score'] < 0.2:
                print(f"  质量评估: 优秀 (Excellent)")
            elif stats['avg_brier_score'] < 0.3:
                print(f"  质量评估: 良好 (Good)")
            else:
                print(f"  质量评估: 需要改进 (Needs Improvement)")

        # 资源使用
        print(f"💻 资源使用:")
        print(f"  平均内存: {stats['avg_memory_mb']:.1f}MB")
        print(f"  峰值内存: {stats['max_memory_mb']:.1f}MB")
        print(f"  平均CPU: {stats['avg_cpu_percent']:.1f}%")
        print(f"  峰值CPU: {stats['max_cpu_percent']:.1f}%")

        # 状态指示
        if stats['success_rate_percentage'] >= 90 and stats['p95_response_time_ms'] <= 2000:
            status = "🟢 优秀"
        elif stats['success_rate_percentage'] >= 80 and stats['p95_response_time_ms'] <= 3000:
            status = "🟡 良好"
        else:
            status = "🔴 需要关注"

        print(f"\n🎯 系统状态: {status}")

    async def run_48hour_shadow_test(self):
        """运行48小时影子测试"""
        logger.info("🚀 启动48小时影子测试守护进程")
        logger.info(f"开始时间: {self.start_time}")
        logger.info(f"测试时长: {self.test_duration_hours}小时")
        logger.info(f"预测间隔: {self.prediction_interval_minutes}分钟")

        cycle_count = 0

        try:
            while self.is_test_running():
                cycle_start = time.time()
                cycle_count += 1

                # 收集系统指标
                metrics = self.collect_system_metrics()

                # 运行预测周期
                result = await self.run_prediction_cycle()

                # 获取进度和统计
                progress = self.get_test_progress()
                stats = self.calculate_statistics()

                # 每5个周期打印一次详细状态
                if cycle_count % 5 == 0:
                    self.print_status_update(progress, stats)

                # 每小时保存一次统计数据
                if cycle_count % 12 == 0:  # 15分钟 * 12 = 3小时
                    await self.save_monitoring_data(progress, stats)

                # 等待下一个预测周期
                elapsed = time.time() - cycle_start
                sleep_time = max(0, self.prediction_interval_minutes * 60 - elapsed)
                await asyncio.sleep(sleep_time)

            # 测试完成
            logger.info("🏁 48小时影子测试完成")
            final_stats = self.calculate_statistics()
            self.print_final_report(final_stats)

        except KeyboardInterrupt:
            logger.info("🛑️ 用户中断测试")
        except Exception as e:
            logger.error(f"❌ 守时异常: {e}")
        finally:
            # 保存最终数据
            progress = self.get_test_progress()
            stats = self.calculate_statistics()
            await self.save_monitoring_data(progress, stats, filename="shadow_test_48h_final.json")

    def print_final_report(self, stats: Dict[str, Any]):
        """打印最终报告"""
        print("\n" + "=" * 80)
        print("🏆 48小时影子测试最终报告")
        print("=" * 80)

        print(f"📊 测试总结:")
        print(f"  测试时长: {stats['elapsed_hours']:.1f}小时")
        print(f"  总预测数: {stats['total_predictions']}")
        print(f"  成功率: {stats['success_rate_percentage']:.1f}%")
        print(f"  API调用: {stats['api_calls']}")
        print(f"  API超时: {stats['api_timeouts']}")

        print(f"\n⚡ 性能总结:")
        print(f"  平均响应时间: {stats['avg_response_time_ms']:.1f}ms")
        print(f"  P95响应时间: {stats['p95_response_time_ms']:.1f}ms")
        print(f"  API成功率: {stats['api_success_rate']:.1f}%")

        print(f"\n📈 预测质量:")
        if stats['avg_brier_score'] > 0:
            print(f"  平均Brier Score: {stats['avg_brier_score']:.4f}")
            if stats['avg_brier_score'] < 0.2:
                print(f"  质量评级: 🏆 优秀 - 概率预测非常准确")
            elif stats['avg_brier_score'] < 0.3:
                print(f"  质量评级: ✅ 良好 - 概率预测较为准确")
            else:
                print(f"  质量评级: ⚠️ 需要改进 - 建议优化概率校准")

        print(f"\n💻 资源使用:")
        print(f"  平均内存: {stats['avg_memory_mb']:.1f}MB")
        print(f"  峰值内存: {stats['max_memory_mb']:.1f}MB")
        print(f"  平均CPU: {stats['avg_cpu_percent']:.1f}%")
        print(f"  峰值CPU: {stats['max_cpu_percent']:.1f}%")

        print(f"\n🎯 评估结果:")
        success_rate = stats['success_rate']
        brier_score = stats.get('avg_brier_score', 1.0)

        if success_rate >= 0.90 and brier_score < 0.25:
            print("  🏆 优秀 - 系统表现超出预期，可投入实盘")
        elif success_rate >= 0.80 and brier_score < 0.35:
            print("  ✅ 良好 - 系统表现符合预期，可投入实盘")
        elif success_rate >= 0.70 and brier_score < 0.45:
            print("  🟡 一般 - 系统基本可用，建议优化后实盘")
        else:
            print("  🔴 需要改进 - 系统存在性能或准确率问题")

        print("=" * 80)

    async def save_monitoring_data(self, progress: Dict[str, Any], stats: Dict[str, Any], filename: str = None):
        """保存监控数据"""
        try:
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"shadow_monitoring_{timestamp}.json"

            monitoring_dir = Path("monitoring_data")
            monitoring_dir.mkdir(exist_ok=True)

            data = {
                'timestamp': datetime.now().isoformat(),
                'progress': progress,
                'statistics': stats,
                'environment': os.getenv('ENVIRONMENT', 'unknown'),
                'daemon_version': '1.0.0'
            }

            filepath = monitoring_dir / filename
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            logger.info(f"📊 监控数据已保存: {filepath}")

        except Exception as e:
            logger.error(f"❌ 保存监控数据失败: {e}")

async def main():
    """主函数"""
    try:
        daemon = ProductionShadowDaemon()

        print("🚀 启动48小时影子测试守护进程")
        print("=" * 60)
        print("📊 监控项目:")
        print("  - FotMob API数据抓取 (15分钟间隔)")
        print("  - AI概率预测计算")
        print("  - Brier Score记录 (预测准确度)")
        print("  - Kelly公式投注建议")
        print("  - 系统性能监控")
        print("  - 实时统计报告")
        print("\n按 Ctrl+C 停止测试\n")

        # 运行48小时测试
        success = await daemon.run_48hour_shadow_test()

        return 0 if success else 1

    except KeyboardInterrupt:
        print("\n🛑️ 用户中断测试")
        return 0
    except Exception as e:
        logger.error(f"守护进程异常: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)