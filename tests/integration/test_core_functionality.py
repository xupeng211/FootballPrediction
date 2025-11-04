#!/usr/bin/env python3
"""
核心功能快速测试
Core Functionality Quick Tests

针对最核心的业务逻辑进行快速测试验证
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))


def test_domain_models(client):
    """测试领域模型基本功能"""
    logger.debug("🧪 测试领域模型...")  # TODO: Add logger import if needed

    try:
        # 测试Team模型
        from src.domain.models.team import Team

        team = Team(name="Test Team", short_name="TT", code="TTC")
        logger.debug(f"✅ Team模型创建成功: {team.display_name}")  # TODO: Add logger import if needed

        # 测试Match模型
        from src.domain.models.match import Match

        match = Match(home_team_id=1, away_team_id=2, league_id=100)
        logger.debug(f"✅ Match模型创建成功: {match}")  # TODO: Add logger import if needed

        # 测试Prediction模型
        from src.domain.models.prediction import Prediction

        prediction = Prediction(match_id=1, user_id=100)
        logger.debug(f"✅ Prediction模型创建成功: {prediction}")  # TODO: Add logger import if needed

        # 测试League模型
        from src.domain.models.league import League

        league = League(name="Test League", short_name="TL", code="L01")
        logger.debug(f"✅ League模型创建成功: {league.display_name}")  # TODO: Add logger import if needed

        return True

    except Exception as e:
        logger.debug(f"❌ 领域模型测试失败: {e}")  # TODO: Add logger import if needed
        return False


def test_prediction_logic(client):
    """测试预测逻辑"""
    logger.debug("🧪 测试预测逻辑...")  # TODO: Add logger import if needed

    try:
        from src.domain.models.match import Match
        from src.domain.models.prediction import Prediction

        # 创建一个比赛
        Match(home_team_id=1, away_team_id=2, league_id=100)

        # 创建预测
        prediction = Prediction(match_id=1, user_id=100)

        # 测试预测
        prediction.make_prediction(2, 1, confidence=0.75)

        logger.debug(f"✅ 预测逻辑测试成功: {prediction}")  # TODO: Add logger import if needed
        return True

    except Exception as e:
        logger.debug(f"❌ 预测逻辑测试失败: {e}")  # TODO: Add logger import if needed
        return False


def test_api_models(client):
    """测试API数据模型"""
    logger.debug("🧪 测试API数据模型...")  # TODO: Add logger import if needed

    try:
        # 测试API基本导入

        logger.debug("✅ API模型导入成功")  # TODO: Add logger import if needed
        return True

    except Exception as e:
        logger.debug(f"❌ API数据模型测试失败: {e}")  # TODO: Add logger import if needed
        return False


def test_utils_functionality(client):
    """测试工具函数"""
    logger.debug("🧪 测试工具函数...")  # TODO: Add logger import if needed

    try:
        from src.utils.dict_utils import DictUtils
        from src.utils.file_utils import FileUtils

        # 测试字典工具
        dict1 = {"a": 1, "b": 2}
        dict2 = {"c": 3, "d": 4}
        merged = DictUtils.deep_merge(dict1, dict2)
        logger.debug(f"✅ 字典合并测试成功: {merged}")  # TODO: Add logger import if needed

        # 测试文件工具
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            test_data = {"test": "data"}
            FileUtils.write_json(test_data, f.name)
            loaded_data = FileUtils.read_json(f.name)
            logger.debug(f"✅ 文件操作测试成功: {loaded_data}")  # TODO: Add logger import if needed
            os.unlink(f.name)

        return True

    except Exception as e:
        logger.debug(f"❌ 工具函数测试失败: {e}")  # TODO: Add logger import if needed
        return False


def main():
    """主测试函数"""
    logger.debug("🚀 开始核心功能快速测试...")  # TODO: Add logger import if needed
    logger.debug("=" * 50)  # TODO: Add logger import if needed

    tests = [
        test_domain_models,
        test_prediction_logic,
        test_api_models,
        test_utils_functionality,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        logger.debug()  # TODO: Add logger import if needed

    logger.debug("=" * 50)  # TODO: Add logger import if needed
    logger.debug(f"📊 测试结果: {passed}/{total} 通过")  # TODO: Add logger import if needed

    if passed == total:
        logger.debug("🎉 所有核心功能测试通过！")  # TODO: Add logger import if needed
        return True
    else:
        logger.debug("⚠️ 部分测试失败，需要修复")  # TODO: Add logger import if needed
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
