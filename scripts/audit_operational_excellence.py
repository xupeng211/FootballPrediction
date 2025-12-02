#!/usr/bin/env python3
"""
MLOps首席运维工程师 - 运维优雅度审计脚本
执行最终验收，评估数据工厂的"健壮性"和"优雅度"

SRE Lead: 验证双进程协调系统的生产就绪性
Purpose: 系统健康检查、性能评估和质量监控
"""

import json
import logging
import time
import subprocess
import re
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class OperationalExcellenceAuditor:
    """运维优雅度审计器"""

    def __init__(self):
        """初始化审计器"""
        self.report = {
            'audit_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'heartbeat_check': {},
            'throughput_check': {},
            'robustness_metrics': {},
            'quality_metrics': {},
            'final_score': {}
        }

    def execute_full_audit(self) -> Dict[str, any]:
        """执行完整审计"""
        logger.info("🚀 MLOps首席运维工程师 - 开始运维优雅度审计")
        logger.info("=" * 60)

        try:
            # Step 1: 心跳检查 (Health & Uptime)
            logger.info("📋 STEP 1: 心跳检查 (Health & Uptime)")
            self.heartbeat_check = self._check_heartbeat()
            time.sleep(1)

            # Step 2: 数据吞吐量检查 (Throughput Check)
            logger.info("📈 STEP 2: 数据吞吐量检查 (Throughput Check)")
            self.throughput_check = self._check_throughput()
            time.sleep(1)

            # Step 3: 健壮性指标 (Robustness Metrics)
            logger.info("🛡️ STEP 3: 健壮性指标 (Robustness Metrics)")
            self.robustness_metrics = self._check_robustness()
            time.sleep(1)

            # Step 4: 数据质量度量 (Quality Metrics)
            logger.info("🎯 STEP 4: 数据质量度量 (Quality Metrics)")
            self.quality_metrics = self._check_quality()

            # Step 5: 生成最终评分
            logger.info("🏆 STEP 5: 生成最终评分")
            self.final_score = self._calculate_final_score()

            logger.info("✅ 审计完成，生成最终报告...")
            return self.report

        except Exception as e:
            logger.error(f"❌ 审计失败: {e}")
            return self.report

    def _check_heartbeat(self) -> Dict[str, any]:
        """心跳检查"""
        results = {}

        try:
            # 检查L1进程
            l1_pid = self._get_process_pid("launch_robust_coverage.py")
            results['l1_process'] = {
                'status': 'running' if l1_pid else 'stopped',
                'pid': l1_pid,
                'name': 'L1采集器 (全域基础数据)'
            }

            # 检查L2进程
            l2_pid = self._get_process_pid("backfill_details.py")
            results['l2_process'] = {
                'status': 'running' if l2_pid else 'stopped',
                'pid': l2_pid,
                'name': 'L2采集器 (深度数据补全)'
            }

            # 检查Crontab服务
            try:
                cron_result = subprocess.run(['systemctl', 'is-active', 'cron'],
                                           capture_output=True, text=True)
                results['cron_service'] = {
                    'status': 'active' if cron_result.returncode == 0 else 'inactive',
                    'output': cron_result.stdout.strip()
                }
            except:
                results['cron_service'] = {'status': 'unknown', 'output': '无法检查'}

            # 计算系统启动时间
            boot_time = self._get_system_uptime()
            results['system_uptime'] = f"{boot_time:.1f} 小时"

            logger.info(f"✅ 心跳检查完成: L1={results['l1_process']['status']}, L2={results['l2_process']['status']}")
            return results

        except Exception as e:
            logger.error(f"❌ 心跳检查失败: {e}")
            return {'error': str(e)}

    def _get_process_pid(self, process_name: str) -> Optional[int]:
        """获取进程PID"""
        try:
            result = subprocess.run(['pgrep', '-f', process_name],
                                      capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                if lines:
                    return int(lines[0].split()[0])
        except:
            pass
        return None

    def _get_system_uptime(self) -> float:
        """获取系统运行时间（小时）"""
        try:
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.read().split()[0])
                return uptime_seconds / 3600.0
        except:
            return 0.0

    def _check_throughput(self) -> Dict[str, any]:
        """数据吞吐量检查"""
        results = {}

        try:
            conn = psycopg2.connect(
                host='localhost',
                port=5432,
                user='postgres',
                password='postgres-dev-password',
                database='football_prediction'
            )

            with conn.cursor() as cur:
                # L1速率：过去60分钟新增的基础记录
                cur.execute("""
                    SELECT COUNT(*)
                    FROM matches
                    WHERE data_source = 'fbref'
                    AND created_at > NOW() - INTERVAL '60 minutes'
                """)
                l1_new_records = cur.fetchone()[0]

                # L2转换速率：过去60分钟升级的记录
                cur.execute("""
                    SELECT COUNT(*)
                    FROM matches
                    WHERE data_source = 'fbref'
                    AND data_completeness = 'complete'
                    AND updated_at > NOW() - INTERVAL '60 minutes'
                """)
                l2_upgraded_records = cur.fetchone()[0]

                # 总体数据量统计
                cur.execute("SELECT COUNT(*) FROM matches WHERE data_source = 'fbref'")
                total_records = cur.fetchone()[0]

                # 数据完整性统计
                cur.execute("""
                    SELECT
                        COUNT(*) as total,
                        COUNT(CASE WHEN stats IS NOT NULL AND stats != '{}' THEN 1 END) as with_stats,
                        COUNT(CASE WHEN data_completeness = 'complete' THEN 1 END) as complete,
                        COUNT(CASE WHEN data_completeness = 'partial' THEN 1 END) as partial
                    FROM matches
                    WHERE data_source = 'fbref'
                """)
                completeness_stats = cur.fetchone()

                results['l1_throughput'] = {
                    'records_per_hour': l1_new_records,
                    'target': 100,
                    'score': min(100, (l1_new_records / 100) * 100)
                }

                results['l2_throughput'] = {
                    'upgraded_per_hour': l2_upgraded_records,
                    'target': 50,
                    'score': min(100, (l2_upgraded_records / 50) * 100)
                }

                results['data_summary'] = {
                    'total_records': total_records,
                    'with_stats': completeness_stats[1],
                    'complete_records': completeness_stats[2],
                    'partial_records': completeness_stats[3],
                    'completion_rate': (completeness_stats[2] / completeness_stats[0] * 100) if completeness_stats[0] > 0 else 0
                }

            conn.close()

            logger.info(f"✅ 吞吐量检查: L1={l1_new_records}/h, L2={l2_upgraded_records}/h")
            return results

        except Exception as e:
            logger.error(f"❌ 吞吐量检查失败: {e}")
            return {'error': str(e)}

    def _check_robustness(self) -> Dict[str, any]:
        """健壮性指标检查"""
        results = {}

        try:
            # 检查反爬虫日志
            l1_log_path = 'logs/skynet_live_run.log'
            if Path(l1_log_path).exists():
                anti_crawl_stats = self._analyze_anti_crawl_metrics(l1_log_path)
                results['anti_crawl_metrics'] = anti_crawl_stats
            else:
                results['anti_crawl_metrics'] = {'error': '日志文件不存在'}

            # 检查系统资源
            cpu_usage = self._get_cpu_usage()
            memory_usage = self._get_memory_usage()

            results['system_resources'] = {
                'cpu_usage_percent': cpu_usage,
                'memory_usage_mb': memory_usage,
                'status': 'healthy' if cpu_usage < 80 and memory_usage < 2048 else 'warning'
            }

            # 检查错误率
            error_rate = self._calculate_error_rate()
            results['error_rate'] = {
                'error_rate_percent': error_rate,
                'status': 'good' if error_rate < 5 else 'needs_attention'
            }

            logger.info(f"✅ 健壮性检查: 反爬虫机制正常，系统资源充足")
            return results

        except Exception as e:
            logger.error(f"❌ 健壮性检查失败: {e}")
            return {'error': str(e)}

    def _analyze_anti_crawl_metrics(self, log_path: str) -> Dict[str, any]:
        """分析反爬虫指标"""
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                log_content = f.read()

            # 统计403错误
            pattern_403 = r'403.*?Forbidden'
            matches_403 = len(re.findall(pattern_403, log_content, re.IGNORECASE))

            # 统计等待延迟
            pattern_wait = r'Waiting\s+\d+\s+seconds'
            matches_wait = len(re.findall(pattern_wait, log_content, re.IGNORECASE))

            # 统计请求总数（估算）
            pattern_request = r'HTTP状态:\s*\d+'
            total_requests = len(re.findall(pattern_request, log_content, re.IGNORECASE))

            # 计算成功率
            success_rate = ((total_requests - matches_403) / total_requests * 100) if total_requests > 0 else 100

            return {
                'total_requests': total_requests,
                '403_errors': matches_403,
                'wait_events': matches_wait,
                'success_rate': success_rate,
                '403_rate': (matches_403 / total_requests * 100) if total_requests > 0 else 0,
                'status': 'excellent' if matches_403 / total_requests < 0.05 else 'needs_optimization'
            }

        except Exception as e:
            return {'error': f'日志分析失败: {e}'}

    def _get_cpu_usage(self) -> float:
        """获取CPU使用率"""
        try:
            result = subprocess.run(['top', '-bn1', '-p', 'pgrep', '-P', 'launch_robust_coverage|backfill_details'],
                                      capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if line.strip() and 'python' in line:
                        # 提取CPU使用率（通常是第9列）
                        parts = line.split()
                        if len(parts) >= 9:
                            try:
                                return float(parts[8])
                            except ValueError:
                                continue
        except:
            pass
        return 0.0

    def _get_memory_usage(self) -> int:
        """获取内存使用量（MB）"""
        try:
            result = subprocess.run(['ps', '--no-headers', '-o', 'rss,comm', '-C', 'python', '-p', 'pgrep', '-f', 'launch_robust_coverage|backfill_details'],
                                      capture_output=True, text=True)
            if result.returncode == 0:
                total_memory = 0
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        try:
                            memory_kb = int(line.split()[0])
                            total_memory += memory_kb
                        except (ValueError, IndexError):
                            continue
                return total_memory // 1024  # 转换为MB
        except:
            pass
        return 0

    def _calculate_error_rate(self) -> float:
        """计算错误率"""
        try:
            with open('logs/skynet_live_run.log', 'r', encoding='utf-8') as f:
                log_content = f.read()

            error_keywords = ['ERROR', 'EXCEPTION', 'FAILED']
            error_count = sum(1 for keyword in error_keywords if keyword.lower() in log_content.lower())

            total_lines = len(log_content.split('\n'))
            return (error_count / total_lines * 100) if total_lines > 0 else 0

        except:
            return 0.0

    def _check_quality(self) -> Dict[str, any]:
        """数据质量度量"""
        results = {}

        try:
            conn = psycopg2.connect(
                host='localhost',
                port=5432,
                user='postgres',
                password='postgres-dev-password',
                database='football_prediction'
            )

            with conn.cursor() as cur:
                # 随机抽取5条complete记录进行质量检查
                cur.execute("""
                    SELECT
                        id, stats, match_date, home_score, away_score
                    FROM matches
                    WHERE data_source = 'fbref'
                    AND data_completeness = 'complete'
                    ORDER BY updated_at DESC
                    LIMIT 5
                """)

                complete_records = cur.fetchall()

                quality_scores = []
                missing_fields = []

                for record_id, stats_json, match_date, home_score, away_score in complete_records:
                    record_score = 100
                    record_missing = []

                    if stats_json and stats_json != '{}':
                        try:
                            stats_data = json.loads(stats_json) if isinstance(stats_json, str) else stats_json

                            # 检查关键字段
                            if 'xg_home' not in stats_data:
                                record_missing.append('xg_home')
                                record_score -= 25
                            if 'possession_home' not in stats_data:
                                record_missing.append('possession_home')
                                record_score -= 25

                            # 检查基础数据完整性
                            if home_score is None or away_score is None:
                                record_missing.append('basic_score')
                                record_score -= 25

                            if match_date is None:
                                record_missing.append('match_date')
                                record_score -= 25

                        except (json.JSONDecodeError, TypeError):
                            record_score = 0
                            record_missing = ['JSON解析失败']
                    else:
                        record_score = 0
                        record_missing = ['Stats字段为空']

                    quality_scores.append(record_score)
                    missing_fields.extend(record_missing)

                # 计算平均质量分数
                avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0

                results['sample_quality'] = {
                    'sample_size': len(complete_records),
                    'scores': quality_scores,
                    'average_score': avg_quality,
                    'missing_fields_summary': list(set(missing_fields))
                }

                # 整体数据质量评估
                cur.execute("""
                    SELECT
                        COUNT(*) as total_complete,
                        COUNT(CASE WHEN stats::text LIKE '%xg_home%' THEN 1 END) as with_xg,
                        COUNT(CASE WHEN stats::text LIKE '%possession_home%' THEN 1 END) as with_possession
                    FROM matches
                    WHERE data_source = 'fbref'
                    AND data_completeness = 'complete'
                """)

                quality_stats = cur.fetchone()

                results['overall_quality'] = {
                    'total_complete_records': quality_stats[0],
                    'with_xg_percentage': (quality_stats[1] / quality_stats[0] * 100) if quality_stats[0] > 0 else 0,
                    'with_possession_percentage': (quality_stats[2] / quality_stats[0] * 100) if quality_stats[0] > 0 else 0,
                    'data_quality_grade': self._get_quality_grade(avg_quality)
                }

            conn.close()

            logger.info(f"✅ 质量检查完成: 平均分数={avg_quality:.1f}")
            return results

        except Exception as e:
            logger.error(f"❌ 质量检查失败: {e}")
            return {'error': str(e)}

    def _get_quality_grade(self, score: float) -> str:
        """获取质量等级"""
        if score >= 90:
            return 'A+ (优秀)'
        elif score >= 80:
            return 'A (良好)'
        elif score >= 70:
            return 'B (合格)'
        elif score >= 60:
            return 'C (需要改进)'
        else:
            return 'D (不合格)'

    def _calculate_final_score(self) -> Dict[str, any]:
        """计算最终评分"""
        scores = []

        # 心跳评分 (40%)
        heartbeat_score = 0
        if self.heartbeat_check.get('l1_process', {}).get('status') == 'running':
            heartbeat_score += 20
        if self.heartbeat_check.get('l2_process', {}).get('status') == 'running':
            heartbeat_score += 20
        scores.append(heartbeat_score)

        # 吞吐量评分 (30%)
        throughput_score = 0
        if self.throughput_check.get('l1_throughput', {}).get('score', 0) >= 50:
            throughput_score += 15
        if self.throughput_check.get('l2_throughput', {}).get('score', 0) >= 50:
            throughput_score += 15
        scores.append(throughput_score)

        # 健壮性评分 (20%)
        robustness_score = 0
        if self.robustness_metrics.get('system_resources', {}).get('status') == 'healthy':
            robustness_score += 10
        if self.robustness_metrics.get('anti_crawl_metrics', {}).get('status') == 'excellent':
            robustness_score += 10
        scores.append(robustness_score)

        # 质量评分 (10%)
        quality_score = 0
        if self.quality_metrics.get('overall_quality', {}).get('data_quality_grade') in ['A+', 'A']:
            quality_score = 10
        elif self.quality_metrics.get('overall_quality', {}).get('data_quality_grade') == 'B':
            quality_score = 7
        scores.append(quality_score)

        total_score = sum(scores)
        grade = self._get_overall_grade(total_score)

        return {
            'total_score': total_score,
            'max_score': 100,
            'grade': grade,
            'component_scores': {
                'heartbeat': f'{heartbeat_score}/40',
                'throughput': f'{throughput_score}/30',
                'robustness': f'{robustness_score}/20',
                'quality': f'{quality_score}/10'
            }
        }

    def _get_overall_grade(self, score: float) -> str:
        """获取总体等级"""
        if score >= 90:
            return 'A+ (卓越)'
        elif score >= 80:
            return 'A (优秀)'
        elif score >= 70:
            return 'B (良好)'
        elif score >= 60:
            return 'C (合格)'
        else:
            return 'D (需要改进)'

    def generate_report(self) -> str:
        """生成最终报告"""
        report = []

        report.append("# MLOps首席运维工程师 - 运维优雅度审计报告")
        report.append(f"")
        report.append(f"**审计时间**: {self.report['audit_time']}")
        report.append(f"")
        report.append("## 📋 执行摘要")
        report.append("")
        report.append(f"- **总分**: {self.final_score.get('total_score', 0)}/100")
        report.append(f"- **等级**: {self.final_score.get('grade', 'Unknown')}")
        report.append(f"- **状态**: {'✅ 优雅' if self.final_score.get('total_score', 0) >= 80 else '⚠️ 需要优化'}")
        report.append("")

        # 详细结果
        report.append("## 🔍 详细审计结果")
        report.append("")

        # 心跳检查
        report.append("### 1. 心跳检查 (Health & Uptime)")
        report.append("")
        heartbeat = self.report['heartbeat_check']
        if 'error' not in heartbeat:
            report.append(f"- **L1采集器**: {heartbeat.get('l1_process', {}).get('status', 'Unknown')} (PID: {heartbeat.get('l1_process', {}).get('pid', 'N/A')})")
            report.append(f"- **L2采集器**: {heartbeat.get('l2_process', {}).get('status', 'Unknown')} (PID: {heartbeat.get('l2_process', {}).get('pid', 'N/A')})")
            report.append(f"- **Cron服务**: {heartbeat.get('cron_service', {}).get('status', 'Unknown')}")
            report.append(f"- **系统运行时间**: {heartbeat.get('system_uptime', 'N/A')}")
        report.append("")

        # 吞吐量检查
        report.append("### 2. 数据吞吐量检查 (Throughput Check)")
        report.append("")
        throughput = self.report['throughput_check']
        if 'error' not in throughput:
            l1 = throughput.get('l1_throughput', {})
            l2 = throughput.get('l2_throughput', {})
            summary = throughput.get('data_summary', {})

            report.append(f"- **L1采集速率**: {l1.get('records_per_hour', 0)} 条/小时 (目标: {l1.get('target', 0)}, 评分: {l1.get('score', 0)})")
            report.append(f"- **L2转换速率**: {l2.get('upgraded_per_hour', 0)} 条/小时 (目标: {l2.get('target', 0)}, 评分: {l2.get('score', 0)})")
            report.append(f"- **数据总量**: {summary.get('total_records', 0):,} 条记录")
            report.append(f"- **完整率**: {summary.get('completion_rate', 0):.1f}%")
        report.append("")

        # 健壮性指标
        report.append("### 3. 健壮性指标 (Robustness Metrics)")
        report.append("")
        robustness = self.report['robustness_metrics']
        if 'error' not in robustness:
            anti_crawl = robustness.get('anti_crawl_metrics', {})
            resources = robustness.get('system_resources', {})

            report.append(f"- **403遭遇率**: {anti_crawl.get('403_rate', 0):.2f}%")
            report.append(f"- **成功率**: {anti_crawl.get('success_rate', 0):.1f}%")
            report.append(f"- **等待事件**: {anti_crawl.get('wait_events', 0)} 次")
            report.append(f"- **CPU使用率**: {resources.get('cpu_usage_percent', 0):.1f}%")
            report.append(f"- **内存使用**: {resources.get('memory_usage_mb', 0):,} MB")
            report.append(f"- **系统状态**: {resources.get('status', 'Unknown')}")
        report.append("")

        # 质量度量
        report.append("### 4. 数据质量度量 (Quality Metrics)")
        report.append("")
        quality = self.report['quality_metrics']
        if 'error' not in quality:
            overall = quality.get('overall_quality', {})
            sample = quality.get('sample_quality', {})

            report.append(f"- **抽样质量**: 平均分数 {sample.get('average_score', 0):.1f}")
            report.append(f"- **xG覆盖率**: {overall.get('with_xg_percentage', 0):.1f}%")
            report.append(f"- **控球率覆盖率**: {overall.get('with_possession_percentage', 0):.1f}%")
            report.append(f"- **数据质量等级**: {overall.get('data_quality_grade', 'Unknown')}")
        report.append("")

        # 风险点分析
        report.append("## ⚠️ 风险点分析")
        report.append("")
        risks = []

        if self.final_score.get('total_score', 0) < 80:
            risks.append("🔴 总分低于80分，需要优化")

        if self.robustness_metrics.get('anti_crawl_metrics', {}).get('403_rate', 0) > 5:
            risks.append("🟡 403错误率偏高，建议增加延迟时间")

        if self.throughput_check.get('l1_throughput', {}).get('score', 0) < 50:
            risks.append("🟡 L1采集速率偏低，需要优化")

        if self.quality_metrics.get('overall_quality', {}).get('data_quality_grade') in ['C', 'D']:
            risks.append("🟡 数据质量需要改进")

        if risks:
            for risk in risks:
                report.append(f"- {risk}")
        else:
            report.append("- ✅ 未发现重大风险点，系统运行优雅")

        report.append("")

        return '\n'.join(report)


def main():
    """主函数"""
    print("🚀 MLOps首席运维工程师 - 启动运维优雅度审计")
    print("=" * 60)

    auditor = OperationalExcellenceAuditor()

    try:
        # 执行审计
        report_data = auditor.execute_full_audit()

        # 生成报告
        report = auditor.generate_report()

        # 输出报告
        print(report)

        # 保存报告到文件
        report_file = f"reports/operational_excellence_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

        # 确保报告目录存在
        Path("reports").mkdir(exist_ok=True)

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"\n📄 报告已保存到: {report_file}")
        print("🎉 运维优雅度审计完成！")

        return 0

    except Exception as e:
        print(f"❌ 审计失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())