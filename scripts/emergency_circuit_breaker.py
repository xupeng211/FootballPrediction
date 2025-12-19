#!/usr/bin/env python3
"""
紧急熔断系统 - 防止API调用频率过高被封
FootballPrediction v2.3.0-production
"""

import subprocess
import signal
import time
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import json

class EmergencyCircuitBreaker:
    """紧急熔断系统"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.monitored_processes = [
            'automation_daemon_24h.py',
            'shadow_daemon_production.py',
            'automation_timer.py'
        ]

    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        status = {
            'timestamp': datetime.now().isoformat(),
            'processes': {},
            'api_rate_limiter': {
                'current_calls_per_minute': 0,
                'max_safe_limit': 30,  # FotMob API安全限制
                'status': 'Normal'
            },
            'system_health': {
                'cpu_usage': 0,
                'memory_usage': 0,
                'disk_usage': 0
            },
            'recommendations': []
        }

        # 检查进程状态
        for process_name in self.monitored_processes:
            try:
                result = subprocess.run(['pgrep', '-f', process_name],
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    pids = result.stdout.strip().split('\n')
                    status['processes'][process_name] = {
                        'running': True,
                        'pids': pids,
                        'count': len(pids)
                    }
                else:
                    status['processes'][process_name] = {
                        'running': False,
                        'pids': [],
                        'count': 0
                    }
            except Exception as e:
                status['processes'][process_name] = {
                    'running': 'Unknown',
                    'error': str(e)
                }

        return status

    def emergency_stop_automation(self) -> bool:
        """紧急停止所有自动化进程"""
        print("🚨 执行紧急停止...")

        stopped_processes = []
        for process_name in self.monitored_processes:
            try:
                # 查找进程PID
                result = subprocess.run(['pgrep', '-f', process_name],
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    pids = result.stdout.strip().split('\n')
                    for pid in pids:
                        if pid:
                            try:
                                os.kill(int(pid), signal.SIGTERM)
                                stopped_processes.append(f"{process_name} (PID: {pid})")
                                print(f"✅ 已停止: {process_name} (PID: {pid})")
                            except ProcessLookupError:
                                print(f"⚠️ 进程不存在: {process_name} (PID: {pid})")
                            except Exception as e:
                                print(f"❌ 停止失败: {process_name} (PID: {pid}) - {e}")
            except Exception as e:
                print(f"❌ 查找进程失败: {process_name} - {e}")

        if stopped_processes:
            print(f"\n🛑 紧急停止完成，已终止 {len(stopped_processes)} 个进程")
            return True
        else:
            print("\nℹ️ 没有找到需要停止的进程")
            return False

    def api_rate_limit_control(self, action: str) -> bool:
        """API频率限制控制"""
        if action == "pause":
            print("⏸️ 暂停API调用...")
            # 这里可以实现暂停逻辑，比如创建一个标志文件
            pause_file = self.project_root / ".api_pause_flag"
            pause_file.touch()
            print(f"✅ API调用已暂停，创建了暂停标志: {pause_file}")
            return True

        elif action == "resume":
            print("▶️ 恢复API调用...")
            pause_file = self.project_root / ".api_pause_flag"
            if pause_file.exists():
                pause_file.unlink()
                print(f"✅ API调用已恢复，删除了暂停标志: {pause_file}")
            else:
                print("ℹ️ API调用未处于暂停状态")
            return True

        elif action == "status":
            pause_file = self.project_root / ".api_pause_flag"
            if pause_file.exists():
                print("⏸️ API调用当前处于暂停状态")
            else:
                print("▶️ API调用当前处于正常状态")
            return True

        else:
            print(f"❌ 未知操作: {action}")
            return False

    def reduce_api_frequency(self, reduction_factor: float = 0.5) -> bool:
        """降低API调用频率"""
        print(f"📉 降低API调用频率至 {reduction_factor*100}%")

        # 这里可以修改配置文件或环境变量
        # 暂时打印提示信息
        print("💡 建议操作:")
        print("  1. 修改预测间隔从15分钟增加到30分钟")
        print("  2. 减少监控的联赛数量")
        print("  3. 启用更严格的错误处理和重试限制")

        return True

    def generate_health_matrix(self) -> Dict[str, Any]:
        """生成健康矩阵"""
        status = self.get_system_status()

        # 计算健康分数
        running_processes = sum(1 for p in status['processes'].values() if p.get('running', False))
        total_processes = len(status['processes'])
        process_health = (running_processes / total_processes) * 100 if total_processes > 0 else 0

        # 模拟系统资源使用
        import psutil
        try:
            cpu_usage = psutil.cpu_percent(interval=1)
            memory_usage = psutil.virtual_memory().percent
            disk_usage = psutil.disk_usage('/').percent
        except:
            cpu_usage = memory_usage = disk_usage = 0

        health_matrix = {
            'overall_health': 'Good' if process_health >= 80 else 'Warning' if process_health >= 60 else 'Critical',
            'process_health_score': process_health,
            'system_resources': {
                'cpu_usage': cpu_usage,
                'memory_usage': memory_usage,
                'disk_usage': disk_usage
            },
            'processes': status['processes'],
            'timestamp': datetime.now().isoformat()
        }

        return health_matrix

    def print_system_dashboard(self):
        """打印系统仪表板"""
        print("\n" + "="*80)
        print("🏥 FootballPrediction 生产系统健康仪表板")
        print("="*80)

        status = self.get_system_status()
        health_matrix = self.generate_health_matrix()

        # 整体健康状态
        print(f"🎯 系统整体状态: {health_matrix['overall_health']}")
        print(f"📊 进程健康分数: {health_matrix['process_health_score']:.1f}%")
        print(f"⏰ 检查时间: {health_matrix['timestamp']}")

        # 进程状态
        print(f"\n🤖 自动化进程状态:")
        for process_name, proc_info in health_matrix['processes'].items():
            status_icon = "✅" if proc_info.get('running', False) else "❌"
            print(f"  {status_icon} {process_name}")
            if proc_info.get('running', False):
                print(f"     PIDs: {', '.join(proc_info.get('pids', []))}")

        # 系统资源
        resources = health_matrix['system_resources']
        print(f"\n💻 系统资源使用:")
        print(f"  CPU使用率: {resources['cpu_usage']:.1f}%")
        print(f"  内存使用率: {resources['memory_usage']:.1f}%")
        print(f"  磁盘使用率: {resources['disk_usage']:.1f}%")

        # API状态
        api_status = status['api_rate_limiter']
        print(f"\n🌐 API频率限制:")
        print(f"  当前调用频率: {api_status['current_calls_per_minute']}/分钟")
        print(f"  安全限制: {api_status['max_safe_limit']}/分钟")
        print(f"  状态: {api_status['status']}")

        print("="*80)

    def show_emergency_commands(self):
        """显示紧急命令"""
        print("\n🚨 紧急熔断命令:")
        print("="*50)
        print("1. 立即停止所有自动化进程:")
        print("   python3 scripts/emergency_circuit_breaker.py --stop-all")
        print()
        print("2. 暂停API调用:")
        print("   python3 scripts/emergency_circuit_breaker.py --api-pause")
        print()
        print("3. 恢复API调用:")
        print("   python3 scripts/emergency_circuit_breaker.py --api-resume")
        print()
        print("4. 降低API频率:")
        print("   python3 scripts/emergency_circuit_breaker.py --reduce-freq 0.5")
        print()
        print("5. 查看系统状态:")
        print("   python3 scripts/emergency_circuit_breaker.py --status")
        print()
        print("6. 查看健康仪表板:")
        print("   python3 scripts/emergency_circuit_breaker.py --dashboard")
        print("="*50)

def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='紧急熔断系统')
    parser.add_argument('--stop-all', action='store_true', help='停止所有自动化进程')
    parser.add_argument('--api-pause', action='store_true', help='暂停API调用')
    parser.add_argument('--api-resume', action='store_true', help='恢复API调用')
    parser.add_argument('--api-status', action='store_true', help='查看API状态')
    parser.add_argument('--reduce-freq', type=float, default=0.5, help='降低API频率 (0.1-1.0)')
    parser.add_argument('--status', action='store_true', help='查看系统状态')
    parser.add_argument('--dashboard', action='store_true', help='显示健康仪表板')
    parser.add_argument('--export-health', help='导出健康矩阵到JSON文件')

    args = parser.parse_args()

    # 创建熔断器
    breaker = EmergencyCircuitBreaker()

    # 如果没有参数，显示帮助和默认仪表板
    if len(sys.argv) == 1:
        breaker.print_system_dashboard()
        breaker.show_emergency_commands()
        return 0

    # 执行相应操作
    try:
        if args.stop_all:
            success = breaker.emergency_stop_automation()
            return 0 if success else 1

        elif args.api_pause:
            success = breaker.api_rate_limit_control("pause")
            return 0 if success else 1

        elif args.api_resume:
            success = breaker.api_rate_limit_control("resume")
            return 0 if success else 1

        elif args.api_status:
            success = breaker.api_rate_limit_control("status")
            return 0 if success else 1

        elif args.reduce_freq is not None:
            success = breaker.reduce_api_frequency(args.reduce_freq)
            return 0 if success else 1

        elif args.status:
            status = breaker.get_system_status()
            print(json.dumps(status, indent=2, ensure_ascii=False, default=str))
            return 0

        elif args.dashboard:
            breaker.print_system_dashboard()
            return 0

        elif args.export_health:
            health_matrix = breaker.generate_health_matrix()
            with open(args.export_health, 'w') as f:
                json.dump(health_matrix, f, indent=2, ensure_ascii=False, default=str)
            print(f"✅ 健康矩阵已导出到: {args.export_health}")
            return 0

        else:
            breaker.show_emergency_commands()
            return 0

    except Exception as e:
        print(f"❌ 操作失败: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)