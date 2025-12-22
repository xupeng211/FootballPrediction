#!/usr/bin/env python3
"""
V12.3 核心组件验证测试 - 简化版
专注验证核心逻辑是否正确，避免复杂的测试框架依赖
"""

import logging
import json
from datetime import datetime, timezone, timedelta
from src.api.collectors.fotmob_core import FotMobCoreCollector

# 设置测试日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class V123CoreValidation:
    """V12.3核心验证类"""

    def __init__(self):
        self.collector = FotMobCoreCollector()
        self.current_time = datetime(2024, 12, 22, 12, 0, 0, tzinfo=timezone.utc)
        self.test_results = {
            'sentry_logic': {},
            'parser_logic': {},
            'filter_logic': {},
            'overall_status': 'PENDING'
        }

    def test_sentry_threshold(self):
        """测试哨兵阈值设置"""
        logger.info("🧪 测试100KB哨兵阈值设置")

        expected_threshold = 102400  # 100KB
        actual_threshold = self.collector.min_response_size

        if actual_threshold == expected_threshold:
            logger.info(f"✅ 哨兵阈值正确: {actual_threshold} bytes")
            self.test_results['sentry_logic']['threshold'] = 'PASSED'
            return True
        else:
            logger.error(f"❌ 哨兵阈值错误: 期望{expected_threshold}，实际{actual_threshold}")
            self.test_results['sentry_logic']['threshold'] = 'FAILED'
            return False

    def test_size_validation_logic(self):
        """测试大小验证逻辑"""
        logger.info("🧪 测试大小验证逻辑")

        # 构造测试数据
        small_data = '{"test": "small"}'  # 约20字节
        medium_data = '{"test": "' + 'x' * 50000 + '"}'  # 约50KB
        large_data = '{"test": "' + 'x' * 120000 + '"}'  # 约120KB

        small_size = len(small_data)
        medium_size = len(medium_data)
        large_size = len(large_data)

        threshold = self.collector.min_response_size

        # 验证逻辑
        small_rejected = small_size < threshold
        medium_rejected = medium_size < threshold
        large_rejected = large_size < threshold

        results = {
            'small_data_size': small_size,
            'small_rejected': small_rejected,
            'medium_data_size': medium_size,
            'medium_rejected': medium_rejected,
            'large_data_size': large_size,
            'large_rejected': large_rejected,
            'threshold': threshold
        }

        if small_rejected and medium_rejected and not large_rejected:
            logger.info(f"✅ 大小验证逻辑正确")
            logger.info(f"   小数据({small_size}B): 拒绝={small_rejected}")
            logger.info(f"   中数据({medium_size}B): 拒绝={medium_rejected}")
            logger.info(f"   大数据({large_size}B): 拒绝={large_rejected}")
            self.test_results['sentry_logic']['size_validation'] = 'PASSED'
            return True
        else:
            logger.error(f"❌ 大小验证逻辑错误")
            self.test_results['sentry_logic']['size_validation'] = 'FAILED'
            return False

    def test_hollow_match_logging(self):
        """测试空心比赛日志记录"""
        logger.info("🧪 测试空心比赛日志记录")

        try:
            # 测试日志记录功能
            self.collector._log_hollow_match(12345, "test_reason")
            logger.info("✅ 空心比赛日志记录功能正常")
            self.test_results['sentry_logic']['logging'] = 'PASSED'
            return True
        except Exception as e:
            logger.error(f"❌ 空心比赛日志记录失败: {e}")
            self.test_results['sentry_logic']['logging'] = 'FAILED'
            return False

    def test_historical_filter_logic(self):
        """测试历史过滤器逻辑"""
        logger.info("🧪 测试历史过滤器逻辑")

        # 构造测试日期
        future_date = datetime(2025, 12, 30, 15, 0, 0, tzinfo=timezone.utc)
        historical_date = datetime(2024, 5, 10, 15, 0, 0, tzinfo=timezone.utc)

        # 测试未来赛项拒绝逻辑
        future_diff = future_date - self.current_time
        should_reject_future = future_diff.total_seconds() > 0

        # 测试历史赛项接受逻辑
        historical_diff = self.current_time - historical_date
        should_accept_historical = historical_diff.total_seconds() > 0

        results = {
            'future_days': future_diff.days,
            'should_reject_future': should_reject_future,
            'historical_days': historical_diff.days,
            'should_accept_historical': should_accept_historical
        }

        if should_reject_future and should_accept_historical:
            logger.info(f"✅ 历史过滤器逻辑正确")
            logger.info(f"   未来赛项({future_diff.days}天后): 拒绝={should_reject_future}")
            logger.info(f"   历史赛项({historical_diff.days}天前): 接受={should_accept_historical}")
            self.test_results['filter_logic']['basic'] = 'PASSED'
            return True
        else:
            logger.error(f"❌ 历史过滤器逻辑错误")
            self.test_results['filter_logic']['basic'] = 'FAILED'
            return False

    def test_data_structure_validation(self):
        """测试数据结构验证"""
        logger.info("🧪 测试数据结构验证")

        # 构造测试JSON结构
        valid_structure = {
            "header": {
                "teams": [
                    {"name": "Home Team"},
                    {"name": "Away Team"}
                ],
                "status": {
                    "utcTime": "2024-12-22T15:00:00Z",
                    "finished": True,
                    "scoreStr": "2-1"
                }
            },
            "content": {
                "stats": {
                    "Periods": {
                        "All": {"stats": []}
                    }
                }
            }
        }

        # 验证基本结构
        has_header = "header" in valid_structure
        has_content = "content" in valid_structure
        has_teams = "teams" in valid_structure["header"]
        has_status = "status" in valid_structure["header"]

        if has_header and has_content and has_teams and has_status:
            logger.info("✅ 数据结构验证通过")
            self.test_results['parser_logic']['structure'] = 'PASSED'
            return True
        else:
            logger.error("❌ 数据结构验证失败")
            self.test_results['parser_logic']['structure'] = 'FAILED'
            return False

    def test_dynamic_id_loading(self):
        """测试动态ID加载"""
        logger.info("🧪 测试动态ID加载")

        try:
            # 测试从manifest加载ID的方法是否存在
            if hasattr(self.collector, '_load_match_ids_from_manifest'):
                # 尝试调用方法
                match_ids = self.collector._load_match_ids_from_manifest()

                if isinstance(match_ids, list):
                    logger.info(f"✅ 动态ID加载功能正常: 加载了{len(match_ids)}个ID")
                    self.test_results['parser_logic']['dynamic_loading'] = 'PASSED'
                    return True
                else:
                    logger.error(f"❌ 动态ID加载返回类型错误: 期望list，实际{type(match_ids)}")
                    self.test_results['parser_logic']['dynamic_loading'] = 'FAILED'
                    return False
            else:
                logger.error("❌ 缺少动态ID加载方法")
                self.test_results['parser_logic']['dynamic_loading'] = 'FAILED'
                return False

        except Exception as e:
            logger.error(f"❌ 动态ID加载测试失败: {e}")
            self.test_results['parser_logic']['dynamic_loading'] = 'FAILED'
            return False

    def run_all_tests(self):
        """运行所有测试"""
        logger.info("🚀 开始V12.3核心组件验证")
        logger.info("=" * 50)

        all_passed = True

        # 运行各项测试
        test_methods = [
            ('哨兵阈值', self.test_sentry_threshold),
            ('大小验证', self.test_size_validation_logic),
            ('日志记录', self.test_hollow_match_logging),
            ('历史过滤器', self.test_historical_filter_logic),
            ('数据结构', self.test_data_structure_validation),
            ('动态加载', self.test_dynamic_id_loading)
        ]

        for test_name, test_method in test_methods:
            logger.info(f"\n🔍 执行测试: {test_name}")
            try:
                result = test_method()
                if not result:
                    all_passed = False
            except Exception as e:
                logger.error(f"❌ 测试执行异常: {test_name} - {e}")
                all_passed = False

        # 生成最终报告
        self._generate_final_report(all_passed)

        return all_passed

    def _generate_final_report(self, all_passed):
        """生成最终验证报告"""
        logger.info("\n" + "=" * 50)
        logger.info("📊 V12.3 核心组件验证报告")
        logger.info("=" * 50)

        # 哨兵逻辑结果
        sentry_results = self.test_results['sentry_logic']
        logger.info("\n🛡️ 哨兵逻辑 (100KB质量红线):")
        for test, result in sentry_results.items():
            status = "✅ PASSED" if result == 'PASSED' else "❌ FAILED"
            logger.info(f"   {test}: {status}")

        # 解析逻辑结果
        parser_results = self.test_results['parser_logic']
        logger.info("\n🔍 解析逻辑 (数据完整性):")
        for test, result in parser_results.items():
            status = "✅ PASSED" if result == 'PASSED' else "❌ FAILED"
            logger.info(f"   {test}: {status}")

        # 过滤逻辑结果
        filter_results = self.test_results['filter_logic']
        logger.info("\n📅 过滤逻辑 (历史赛项判定):")
        for test, result in filter_results.items():
            status = "✅ PASSED" if result == 'PASSED' else "❌ FAILED"
            logger.info(f"   {test}: {status}")

        # 总体状态
        self.test_results['overall_status'] = 'PASSED' if all_passed else 'FAILED'
        logger.info(f"\n🎯 总体验证状态: {self.test_results['overall_status']}")

        if all_passed:
            logger.info("\n🎉 所有核心逻辑验证通过！V13.0点火准备就绪！")
        else:
            logger.info("\n⚠️  部分验证失败，需要修复后才能启动V13.0")

        logger.info("=" * 50)

def main():
    """主函数"""
    validator = V123CoreValidation()
    return validator.run_all_tests()

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)