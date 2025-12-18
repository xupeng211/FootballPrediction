#!/usr/bin/env python3
"""
链接持久化单元测试
Chief Code Fixer: 数据管道修复验证

Purpose: 验证match_report_url从DataFrame到数据库的完整流程
"""

import pandas as pd
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestLinkPersistence:
    """链接持久化测试套件"""

    def setup_method(self):
        """测试前置设置"""
        # 创建测试数据
        self.test_data = pd.DataFrame(
            {
                "date": ["2023-08-11", "2023-08-12", "2023-08-13"],
                "home": ["Manchester City", "Arsenal", "Liverpool"],
                "away": ["Burnley", "Nottingham Forest", "Chelsea"],
                "score": ["3-0", "2-1", "1-1"],
                "xg_home": [2.1, 1.8, 1.5],
                "xg_away": [0.8, 0.9, 1.2],
                "match_report_url": [
                    "https://fbref.com/en/matches/12345678/ManCity-Burnley-August-11-2023",
                    "https://fbref.com/en/matches/87654321/Arsenal-Forest-August-12-2023",
                    "https://fbref.com/en/matches/11223344/Liverpool-Chelsea-August-13-2023",
                ],
                "attendance": [55000, 60000, 53000],
                "venue": ["Etihad", "Emirates", "Anfield"],
            }
        )

    def test_clean_schedule_data_preserves_urls(self):
        """测试数据清洗方法保留URL"""
        from src.data.collectors.fbref_collector import FBrefCollector

        collector = FBrefCollector()

        # 执行数据清洗
        cleaned_data = collector._clean_schedule_data(self.test_data)

        # 🔥 关键断言1：URL列必须存在
        assert "match_report_url" in cleaned_data.columns, "❌ match_report_url列缺失"

        # 🔥 关键断言2：URL值必须保留
        original_urls = self.test_data["match_report_url"].tolist()
        cleaned_urls = cleaned_data["match_report_url"].tolist()

        assert (
            original_urls == cleaned_urls
        ), f"❌ URL不匹配: {original_urls} vs {cleaned_urls}"

        # 🔥 关键断言3：URL数量正确
        non_null_urls = cleaned_data["match_report_url"].notna().sum()
        assert non_null_urls == 3, f"❌ URL数量不正确: {non_null_urls} != 3"

        print("✅ _clean_schedule_data URL保留测试通过")

    def test_database_saver_preserves_urls(self):
        """测试数据库保存器保留URL"""
        from scripts.fbref_database_saver import FBrefDatabaseSaver

        # 模拟数据库保存器（不连接真实数据库）
        # 只测试数据转换逻辑
        try:
            saver = FBrefDatabaseSaver()
        except Exception:
            # 如果数据库连接失败，我们只测试转换逻辑
            from scripts.fbref_database_saver import FBrefDatabaseSaver as Saver

            # 手动创建一个测试实例
            saver = Saver.__new__(Saver)

        # 转换DataFrame为比赛记录
        match_records = saver.convert_dataframe_to_match_records(
            self.test_data, "Premier League", "2023-2024"
        )

        # 🔥 关键断言1：成功转换
        assert (
            len(match_records) == 3
        ), f"❌ 比赛记录数量不正确: {len(match_records)} != 3"

        # 🔥 关键断言2：每条记录都包含URL
        for i, record in enumerate(match_records):
            stats = record["stats"]

            # 检查stats字段中的URL
            assert "match_report_url" in stats, f"❌ 记录{i}中缺少match_report_url"

            # 检查raw_data中的URL
            raw_data = stats.get("raw_data", {})
            assert "match_report_url" in raw_data, f"❌ 记录{i}的raw_data中缺少URL"

            # 验证URL值正确
            expected_url = self.test_data.iloc[i]["match_report_url"]
            actual_url = stats["match_report_url"]
            assert actual_url == expected_url, f"❌ 记录{i}的URL不匹配"

        print("✅ 数据库保存器URL保留测试通过")

    def test_end_to_end_link_flow(self):
        """端到端链接流程测试"""
        from src.data.collectors.fbref_collector import FBrefCollector

        collector = FBrefCollector()

        # 步骤1：数据清洗
        cleaned_data = collector._clean_schedule_data(self.test_data)

        # 步骤2：记录转换
        try:
            from scripts.fbref_database_saver import FBrefDatabaseSaver

            saver = FBrefDatabaseSaver()
        except Exception:
            from scripts.fbref_database_saver import FBrefDatabaseSaver as Saver

            saver = Saver.__new__(Saver)

        match_records = saver.convert_dataframe_to_match_records(
            cleaned_data, "Premier League", "2023-2024"
        )

        # 🔥 端到端验证
        for i, record in enumerate(match_records):
            # 从原始数据获取URL
            original_url = self.test_data.iloc[i]["match_report_url"]

            # 从最终记录获取URL
            stats = record["stats"]
            final_url = stats.get("match_report_url")
            raw_url = stats.get("raw_data", {}).get("match_report_url")

            # 验证URL在所有层级都存在且正确
            assert final_url == original_url, f"❌ 最终记录{i}: URL不匹配"
            assert raw_url == original_url, f"❌ 原始数据{i}: URL不匹配"

        print("✅ 端到端链接流程测试通过")


def run_quick_test():
    """快速运行测试（不在pytest环境中）"""
    print("🚀 运行链接持久化快速测试")
    print("=" * 50)

    test = TestLinkPersistence()
    test.setup_method()

    try:
        test.test_clean_schedule_data_preserves_urls()
        test.test_database_saver_preserves_urls()
        test.test_end_to_end_link_flow()

        print("=" * 50)
        print("🎉 所有测试通过！修复验证成功！")
        print("🚀 可以进入Step 3: 清空旧数据并重启任务")
        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_quick_test()
    sys.exit(0 if success else 1)
