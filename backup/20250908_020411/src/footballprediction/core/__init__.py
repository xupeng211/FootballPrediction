"""核心功能模块"""


class ProjectCore:
    """项目核心类"""

    def __init__(self):
        self.name = "FootballPrediction"
        self.version = "0.1.0"

    def get_info(self) -> dict:
        """获取项目信息"""
        return {
            "name": self.name,
            "version": self.version,
            "description": "基于机器学习的足球比赛结果预测系统，覆盖全球主要赛事",
        }
