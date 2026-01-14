#!/usr/bin/env python3
"""
V36.3 TDD Guardian - 生产环境测试守护程序

职责：
1. 实时监控 logs/failed_features.json
2. 检测到新失败时自动生成测试 Case
3. 验证测试通过后才能修复数据
4. 每日晨报前运行全量单元测试

准入红线：
- 禁止在测试未通过的情况下手动改库
- 每个失败记录必须有对应的测试 Case
- 新测试必须先失败（Red Phase）再修复（Green Phase）

Author: SRE Team
Version: V36.3
Date: 2026-01-12
"""

import sys
import json
import logging
import time
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List
import hashlib

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class TDDGuardian:
    """TDD 守护程序"""

    def __init__(self):
        self.failed_features_log = Path("logs/failed_features.json")
        self.test_file = Path("tests/unit/test_feature_extraction_v1.py")
        self.known_failures = set()  # 已知失败记录的 hash 集合
        self.last_check_time = None

    def get_file_hash(self, record: Dict[str, Any]) -> str:
        """计算失败记录的唯一哈希"""
        # 使用 match_id + format_type + reason 生成唯一标识
        key = f"{record.get('match_id', '')}_{record.get('format_type', '')}_{record.get('reason', '')}"
        return hashlib.md5(key.encode()).hexdigest()

    def load_known_failures(self) -> None:
        """加载已知失败记录"""
        if self.failed_features_log.exists():
            with open(self.failed_features_log, 'r') as f:
                records = json.load(f)
                for record in records:
                    self.known_failures.add(self.get_file_hash(record))

        logger.info(f"📚 已加载 {len(self.known_failures)} 条已知失败记录")

    def check_new_failures(self) -> List[Dict[str, Any]]:
        """检查新的失败记录"""
        if not self.failed_features_log.exists():
            return []

        with open(self.failed_features_log, 'r') as f:
            all_records = json.load(f)

        new_failures = []
        for record in all_records:
            record_hash = self.get_file_hash(record)
            if record_hash not in self.known_failures:
                new_failures.append(record)
                self.known_failures.add(record_hash)

        return new_failures

    def generate_test_case(self, failure_record: Dict[str, Any]) -> str:
        """基于失败记录生成测试 Case"""
        match_id = failure_record.get('match_id', 'unknown')
        format_type = failure_record.get('format_type', 'unknown')
        reason = failure_record.get('reason', 'unknown')
        raw_data = failure_record.get('raw_data_sample', '{}')

        # 生成测试方法名
        test_method_name = f"test_failure_{match_id}_{format_type.replace(' ', '_').replace('-', '_')}"

        # 生成测试代码
        test_case = f'''

    def {test_method_name}(self):
        """TDD 自动生成: {reason}

        失败记录: {match_id}
        格式类型: {format_type}
        生成时间: {datetime.now().isoformat()}

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {raw_data}

        # 构造测试数据
        test_data = {{
            "match_id": "{match_id}",
            "l3_odds_data": raw_data
        }}

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: {reason}
'''

        return test_case

    def append_test_to_file(self, test_case: str) -> bool:
        """将测试追加到测试文件"""
        try:
            with open(self.test_file, 'a') as f:
                f.write(test_case)

            logger.info(f"✅ 测试 Case 已追加到 {self.test_file}")
            return True
        except Exception as e:
            logger.error(f"❌ 追加测试失败: {e}")
            return False

    def run_single_test(self, test_method_name: str) -> bool:
        """运行单个测试"""
        try:
            result = subprocess.run(
                ['python', '-m', 'pytest', str(self.test_file),
                 f'-k', f'{test_method_name}', '-v'],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                logger.info(f"✅ 测试 {test_method_name} 通过")
                return True
            else:
                logger.warning(f"⚠️  测试 {test_method_name} 失败 (符合预期 - Red Phase)")
                logger.warning(result.stdout)
                return False

        except Exception as e:
            logger.error(f"❌ 运行测试异常: {e}")
            return False

    def run_full_unit_tests(self) -> bool:
        """运行全量单元测试"""
        logger.info("=" * 60)
        logger.info("🧪 运行全量单元测试 (tests/unit/)")
        logger.info("=" * 60)

        try:
            result = subprocess.run(
                ['python', '-m', 'pytest', 'tests/unit/', '-v', '--tb=short'],
                capture_output=True,
                text=True,
                timeout=300  # 5 分钟超时
            )

            # 显示测试结果摘要
            lines = result.stdout.split('\n')
            for line in lines[-20:]:  # 显示最后 20 行
                if line.strip():
                    logger.info(line)

            if result.returncode == 0:
                logger.info("✅ 全量单元测试通过")
                return True
            else:
                logger.error("❌ 全量单元测试失败")
                logger.error(result.stderr)
                return False

        except Exception as e:
            logger.error(f"❌ 运行全量测试异常: {e}")
            return False

    def handle_new_failure(self, failure_record: Dict[str, Any]) -> None:
        """处理新的失败记录"""
        logger.warning("=" * 60)
        logger.warning("⚠️  检测到新的失败记录！")
        logger.warning("=" * 60)
        logger.warning(f"Match ID: {failure_record.get('match_id')}")
        logger.warning(f"Format Type: {failure_record.get('format_type')}")
        logger.warning(f"Reason: {failure_record.get('reason')}")
        logger.warning(f"Timestamp: {failure_record.get('timestamp')}")

        # 生成测试 Case
        logger.info("📝 正在生成测试 Case...")
        test_case = self.generate_test_case(failure_record)

        # 追加到测试文件
        if self.append_test_to_file(test_case):
            # 提取测试方法名
            test_method_name = test_case.split('def ')[1].split('(')[0]

            logger.info(f"🧪 运行新生成的测试: {test_method_name}")

            # 运行测试（预期失败 - Red Phase）
            test_passed = self.run_single_test(test_method_name)

            if not test_passed:
                logger.info("✅ Red Phase 完成 - 测试失败符合预期")
                logger.info("🔧 下一步：修复代码使测试通过 (Green Phase)")
            else:
                logger.warning("⚠️  测试意外通过 - 可能已存在相应功能")

    def monitor_loop(self, check_interval: int = 60) -> None:
        """监控循环"""
        logger.info("=" * 60)
        logger.info("🛡️  V36.3 TDD Guardian 启动")
        logger.info("=" * 60)
        logger.info(f"监控文件: {self.failed_features_log}")
        logger.info(f"检查间隔: {check_interval} 秒")
        logger.info(f"测试文件: {self.test_file}")
        logger.info("=" * 60)

        # 初始化已知失败记录
        self.load_known_failures()

        logger.info("👀 开始监控...")
        logger.info("💡 按 Ctrl+C 停止监控")

        try:
            while True:
                # 检查新失败
                new_failures = self.check_new_failures()

                if new_failures:
                    logger.info(f"🔔 检测到 {len(new_failures)} 条新失败记录")

                    for failure in new_failures:
                        self.handle_new_failure(failure)
                        logger.info("")

                # 等待下次检查
                time.sleep(check_interval)

        except KeyboardInterrupt:
            logger.info("\n🛑 收到停止信号，TDD Guardian 正在退出...")
            logger.info("👋 监控已停止")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="V36.3 TDD Guardian")
    parser.add_argument(
        '--check-interval',
        type=int,
        default=60,
        help='检查间隔（秒），默认 60'
    )
    parser.add_argument(
        '--run-tests',
        action='store_true',
        help='运行全量单元测试然后退出'
    )
    parser.add_argument(
        '--once',
        action='store_true',
        help='只检查一次然后退出'
    )

    args = parser.parse_args()

    guardian = TDDGuardian()

    # 运行全量测试模式
    if args.run_tests:
        success = guardian.run_full_unit_tests()
        sys.exit(0 if success else 1)

    # 单次检查模式
    if args.once:
        guardian.load_known_failures()
        new_failures = guardian.check_new_failures()

        if new_failures:
            logger.info(f"🔔 检测到 {len(new_failures)} 条新失败记录")
            for failure in new_failures:
                guardian.handle_new_failure(failure)
        else:
            logger.info("✅ 没有新失败记录")

        sys.exit(0)

    # 默认：持续监控模式
    guardian.monitor_loop(check_interval=args.check_interval)


if __name__ == "__main__":
    main()
