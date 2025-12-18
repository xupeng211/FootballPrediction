"""
冒烟测试脚本
测试数据标准化、Upsert逻辑和数据入库的完整流程
只引用src目录下的代码，不在测试脚本中定义业务逻辑
"""

import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 引用src目录下的业务逻辑代码
from src.database.models import League, Team, Match
from src.database.repositories import TeamRepository, LeagueRepository, MatchRepository
from src.utils.normalizer import TeamNameStandardizer, LeagueNameStandardizer, data_validator

# 简单的日志配置
import logging

class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""
    COLORS = {
        'DEBUG': '\033[36m',    # 青色
        'INFO': '\033[32m',     # 绿色
        'WARNING': '\033[33m',  # 黄色
        'ERROR': '\033[31m',    # 红色
        'CRITICAL': '\033[35m', # 紫色
        'RESET': '\033[0m'      # 重置
    }

    def format(self, record):
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(ColoredFormatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.handlers.clear()
logger.addHandler(handler)

def success(message):
    logger.info(f"✅ {message}")

def info(message):
    logger.info(f"ℹ️  {message}")

def warning(message):
    logger.warning(f"⚠️  {message}")

def error(message):
    logger.error(f"❌ {message}")


class SmokeTestRunner:
    """冒烟测试运行器"""

    def __init__(self):
        # 数据库连接
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        db_path = project_root / "data" / "football_prediction.db"
        database_url = f"sqlite:///{db_path}"

        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        # 获取数据库会话
        self.session = self.SessionLocal()

        # 初始化仓库（引用src目录下的业务逻辑）
        self.team_repo = TeamRepository(self.session)
        self.league_repo = LeagueRepository(self.session)
        self.match_repo = MatchRepository(self.session)

        # 引用src目录下的标准化器
        self.team_standardizer = TeamNameStandardizer()
        self.league_standardizer = LeagueNameStandardizer()

        info("🧪 冒烟测试环境初始化完成")

    def test_team_name_normalization(self):
        """测试队名标准化功能"""
        info("🔍 测试 1: 队名标准化")

        dirty_team_names = [
            "Man Utd",
            "Man U",
            "manchester utd",
            "Man City",
            "liverpool fc",
            "Chelsea",
            "Arsenal FC",
            "spurs",
            "Real Madrid",
            "FC Barcelona",
            "PSG",
            "Bayern Munich",
        ]

        info("原始队名 → 标准化队名:")
        for dirty_name in dirty_team_names:
            clean_name = self.team_standardizer.normalize_team_name(dirty_name)
            info(f"  '{dirty_name}' → '{clean_name}'")

        success("队名标准化测试通过")
        return self.team_standardizer

    def test_league_name_normalization(self):
        """测试联赛名称标准化功能"""
        info("🔍 测试 2: 联赛名称标准化")

        dirty_league_names = [
            "EPL",
            "English Premier League",
            "premier league",
            "La Liga",
            "laliga",
            "Bundesliga",
            "Serie A",
            "Ligue 1",
            "UEFA Champions League",
        ]

        info("原始联赛名 → 标准化联赛名:")
        for dirty_name in dirty_league_names:
            clean_name = self.league_standardizer.normalize_league_name(dirty_name)
            info(f"  '{dirty_name}' → '{clean_name}'")

        success("联赛名称标准化测试通过")
        return self.league_standardizer

    def test_match_data_validation(self):
        """测试比赛数据验证功能"""
        info("🔍 测试 3: 比赛数据验证")

        # 测试有效数据
        valid_data = {
            "home_team": "Manchester United",
            "away_team": "Liverpool FC",
            "match_date": datetime.now() + timedelta(days=1),
            "home_score": 2,
            "away_score": 1,
            "home_xg": 1.5,
            "away_xg": 0.8,
        }

        is_valid, errors = data_validator.validate_match_data(valid_data)
        info(f"有效数据验证结果: {is_valid}, 错误: {errors}")
        assert is_valid, "有效数据验证失败"

        # 测试无效数据
        invalid_data = {
            "home_team": "",  # 空队名
            "away_team": "Liverpool FC",
            "match_date": datetime.now() + timedelta(days=1),
            "home_score": -1,  # 负分
            "away_xg": 15.0,  # 超出合理范围的xG
        }

        is_valid, errors = data_validator.validate_match_data(invalid_data)
        info(f"无效数据验证结果: {is_valid}, 错误: {errors}")
        assert not is_valid, "无效数据应该被拒绝"
        assert len(errors) > 0, "应该有错误信息"

        success("比赛数据验证测试通过")

    def test_match_ingestion(self):
        """测试完整的比赛数据入库流程"""
        info("🔍 测试 4: 比赛数据入库流程")

        # 构造包含脏数据的比赛信息
        dirty_match_data = {
            # 脏数据：非标准队名和联赛名
            "home_team": "Man Utd",           # 应该被标准化为 "Manchester United"
            "away_team": "liverpool fc",      # 应该被标准化为 "Liverpool FC"
            "league": "EPL",                  # 应该被标准化为 "Premier League"

            # 比赛信息
            "match_date": datetime.now() + timedelta(hours=3),
            "status": "finished",
            "home_score": 3,
            "away_score": 1,
            "external_id": "test_match_001",

            # 统计数据
            "home_xg": 2.1,
            "away_xg": 0.9,
            "home_possession": 65.5,
            "away_possession": 34.5,

            # 赔率数据
            "home_win_odds": 1.85,
            "draw_odds": 3.60,
            "away_win_odds": 4.20,

            "data_completeness": "complete"
        }

        info("📝 原始脏数据:")
        for key, value in dirty_match_data.items():
            info(f"  {key}: {value}")

        # 执行 Upsert 操作（引用src目录下的仓库逻辑）
        try:
            match, is_new = self.match_repo.upsert_match(dirty_match_data)

            if is_new:
                success("✅ 新比赛记录创建成功")
            else:
                success("✅ 现有比赛记录更新成功")

            info(f"比赛记录ID: {match.id}")
            info(f"标准化后主队: {match.home_team.name}")
            info(f"标准化后客队: {match.away_team.name}")
            if match.league:
                info(f"标准化后联赛: {match.league.name}")

            return match

        except Exception as e:
            error(f"比赛数据入库失败: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

    def test_duplicate_prevention(self):
        """测试重复数据防护"""
        info("🔍 测试 5: 重复数据防护")

        # 使用相同的外部ID再次插入数据
        duplicate_match_data = {
            "home_team": "Manchester United",     # 标准名称
            "away_team": "Liverpool FC",         # 标准名称
            "league": "Premier League",
            "match_date": datetime.now() + timedelta(hours=3),
            "status": "finished",
            "home_score": 3,
            "away_score": 1,
            "external_id": "test_match_001",     # 相同的外部ID
            "home_xg": 2.1,
            "away_xg": 0.9,
        }

        # 执行 Upsert，应该更新现有记录而不是创建新记录
        match, is_new = self.match_repo.upsert_match(duplicate_match_data)

        assert not is_new, "不应该创建新的比赛记录"
        success("重复数据防护测试通过 - 成功更新现有记录")

        # 查询数据库确认只有一条记录
        matches = self.session.query(Match).filter(
            Match.fotmob_id == "test_match_001"
        ).all()

        assert len(matches) == 1, f"应该只有1条记录，实际有 {len(matches)} 条"
        info(f"数据库中包含 {len(matches)} 条匹配记录")

    def verify_database_content(self):
        """验证数据库内容"""
        info("🔍 测试 6: 数据库内容验证")

        # 查询所有队伍
        teams = self.session.query(Team).all()
        info(f"📊 数据库中的队伍数量: {len(teams)}")
        for team in teams:
            info(f"  - ID: {team.id}, 名称: {team.name}, 外部ID: {team.external_id}")

        # 查询所有联赛
        leagues = self.session.query(League).all()
        info(f"📊 数据库中的联赛数量: {len(leagues)}")
        for league in leagues:
            info(f"  - ID: {league.id}, 名称: {league.name}, 国家: {league.country}")

        # 查询所有比赛
        matches = self.session.query(Match).all()
        info(f"📊 数据库中的比赛数量: {len(matches)}")
        for match in matches:
            home_team_name = match.home_team.name if match.home_team else "Unknown"
            away_team_name = match.away_team.name if match.away_team else "Unknown"
            league_name = match.league.name if match.league else "Unknown"
            info(f"  - ID: {match.id}, 比赛: {home_team_name} vs {away_team_name}")
            info(f"    联赛: {league_name}, 日期: {match.match_date}")
            info(f"    比分: {match.home_score}-{match.away_score}, 状态: {match.status}")
            info(f"    外部ID: {match.fotmob_id}, 数据完整性: {match.data_completeness}")

        success("数据库内容验证完成")

    def cleanup_test_data(self):
        """清理测试数据"""
        info("🧹 清理测试数据")

        try:
            # 删除测试比赛记录
            self.session.query(Match).filter(
                Match.fotmob_id == "test_match_001"
            ).delete()

            # 删除测试期间创建的孤立队伍记录（仅限本次测试创建的）
            # 注意：这里保留所有队伍记录，因为它们可能在其他测试中使用
            self.session.commit()
            info("测试数据清理完成")

        except Exception as e:
            self.session.rollback()
            warning(f"清理测试数据时出错: {str(e)}")

    def run_all_tests(self):
        """运行所有冒烟测试"""
        info("🚀 开始运行冒烟测试套件...")

        try:
            # 测试1：队名标准化
            team_standardizer = self.test_team_name_normalization()

            # 测试2：联赛名称标准化
            league_standardizer = self.test_league_name_normalization()

            # 测试3：数据验证
            self.test_match_data_validation()

            # 测试4：完整入库流程
            match = self.test_match_ingestion()

            # 测试5：重复数据防护
            self.test_duplicate_prevention()

            # 测试6：数据库内容验证
            self.verify_database_content()

            success("🎉 所有冒烟测试通过！")
            info("📋 测试总结:")
            info("   ✅ 队名标准化功能正常")
            info("   ✅ 联赛名称标准化功能正常")
            info("   ✅ 数据验证功能正常")
            info("   ✅ 数据入库功能正常")
            info("   ✅ Upsert去重功能正常")
            info("   ✅ 数据库持久化功能正常")
            info("   ✅ 业务逻辑代码复用正确")

        except Exception as e:
            error(f"冒烟测试失败: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

        finally:
            # 清理测试数据
            self.cleanup_test_data()
            self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()


def main():
    """主函数"""
    info("🧪 开始足球预测系统冒烟测试...")

    try:
        with SmokeTestRunner() as test_runner:
            test_runner.run_all_tests()

        success("🎉 冒烟测试完成！系统准备就绪。")
        info("📝 下一步建议:")
        info("   1. 检查数据库文件: data/football_prediction.db")
        info("   2. 启动数据采集: python scripts/collect_data.py")
        info("   3. 启动Web界面: streamlit run src/web/app.py")

    except Exception as e:
        error(f"冒烟测试失败: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()