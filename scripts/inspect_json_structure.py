#!/usr/bin/env python3
"""
FotMob JSON 结构分析器
深度解析137KB响应中的隐藏数据
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Set


class JSONPathAnalyzer:
    def __init__(self):
        self.match_paths: list[str] = []
        self.team_paths: list[str] = []
        self.score_paths: list[str] = []
        self.interesting_paths: list[str] = []
        self.visited_paths: set[str] = set()

    def analyze_json_structure(self, json_file: Path):
        """分析JSON文件结构"""
        print("🔍 FotMob JSON 结构深度分析器")
        print("=" * 60)

        # 加载JSON数据
        with open(json_file, encoding="utf-8") as f:
            data = json.load(f)

        print(f"📁 分析文件: {json_file}")
        print(f"📊 文件大小: {json_file.stat().st_size:,} 字节")

        # 显示顶级结构
        self.analyze_top_level(data)

        # 深度分析pageProps
        if "pageProps" in data:
            print("\n🎯 深度分析 pageProps:")
            self.recursive_analyze(data["pageProps"], "pageProps")

        # 深度分析translations (可能包含比赛数据)
        if "translations" in data:
            print("\n🌐 深度分析 translations:")
            self.recursive_analyze(data["translations"], "translations")

        # 显示找到的路径
        self.display_findings()

    def analyze_top_level(self, data: dict[str, Any]):
        """分析顶级结构"""
        print(f"\n📋 顶级键 (共 {len(data)} 个):")
        for i, (key, value) in enumerate(data.items(), 1):
            value_type = type(value).__name__
            size_info = ""

            if isinstance(value, dict):
                size_info = f" ({len(value)} 键)"
            elif isinstance(value, list):
                size_info = f" ({len(value)} 元素)"
            elif isinstance(value, str):
                size_info = f" ({len(value)} 字符)"

            print(f"  {i:2d}. {key}: {value_type}{size_info}")

    def recursive_analyze(
        self, obj: Any, path: str, depth: int = 0, max_depth: int = 6
    ):
        """递归分析JSON对象"""
        if depth > max_depth or path in self.visited_paths:
            return

        self.visited_paths.add(path)

        # 显示当前路径
        indent = "  " * depth
        type(obj).__name__

        if isinstance(obj, dict):
            print(f"{indent}📁 {path} [dict, {len(obj)} 键]")

            # 检查是否包含关键词
            self.check_for_keywords(obj, path)

            # 只显示有意义的键
            important_keys = []
            for key, value in obj.items():
                if self.is_important_key(key, value):
                    important_keys.append(key)

            if important_keys:
                print(f"{indent}   重要键: {important_keys}")

            # 递归分析重要内容
            for key, value in obj.items():
                if self.should_recurse(key, value, depth):
                    new_path = f"{path} -> {key}"
                    self.recursive_analyze(value, new_path, depth + 1, max_depth)

        elif isinstance(obj, list):
            print(f"{indent}📋 {path} [list, {len(obj)} 元素]")

            # 检查列表元素
            if obj and len(obj) > 0:
                first_element = obj[0]
                first_type = type(first_element).__name__
                print(f"{indent}   首元素类型: {first_type}")

                # 如果列表包含重要数据，递归分析前几个元素
                if self.important_list_content(obj):
                    for i, element in enumerate(obj[:3]):  # 只分析前3个
                        new_path = f"{path}[{i}]"
                        self.recursive_analyze(element, new_path, depth + 1, max_depth)

        elif isinstance(obj, str):
            # 检查字符串是否包含比赛相关信息
            if self.contains_match_info(obj):
                print(
                    f"{indent}📄 {path} [string, {len(obj)} 字符] 🎯 可能包含比赛数据!"
                )
                self.interesting_paths.append(path)

    def check_for_keywords(self, obj: dict[str, Any], path: str):
        """检查字典是否包含关键词"""
        obj_str = json.dumps(obj, ensure_ascii=False).lower()
        keywords = [
            "match",
            "team",
            "home",
            "away",
            "score",
            "goal",
            "league",
            "tournament",
        ]

        found_keywords = [kw for kw in keywords if kw in obj_str]

        if found_keywords:
            print(f"  🔍 找到关键词: {found_keywords}")

            # 记录路径
            if "match" in obj_str:
                self.match_paths.append(path)
            if any(kw in obj_str for kw in ["home", "away", "team"]):
                self.team_paths.append(path)
            if "score" in obj_str:
                self.score_paths.append(path)

    def is_important_key(self, key: str, value: Any) -> bool:
        """判断是否为重要键"""
        key_lower = key.lower()
        important_patterns = [
            "match",
            "team",
            "home",
            "away",
            "score",
            "goal",
            "league",
            "tournament",
            "fixture",
            "game",
            "player",
            "club",
            "venue",
            "status",
            "result",
        ]

        # 检查键名
        if any(pattern in key_lower for pattern in important_patterns):
            return True

        # 检查值的特征
        if isinstance(value, (dict, list)) and len(str(value)) > 1000:
            return True

        return False

    def should_recurse(self, key: str, value: Any, depth: int) -> bool:
        """判断是否应该递归分析"""
        # 限制深度
        if depth >= 4:
            return False

        # 重要键总是递归
        if self.is_important_key(key, value):
            return True

        # 小数据结构不递归
        if isinstance(value, (dict, list)) and len(str(value)) < 500:
            return False

        return True

    def important_list_content(self, lst: list[Any]) -> bool:
        """检查列表是否包含重要内容"""
        if not lst:
            return False

        first_element = lst[0]

        # 检查是否包含字典且有比赛相关键
        if isinstance(first_element, dict):
            element_str = json.dumps(first_element, ensure_ascii=False).lower()
            return any(
                keyword in element_str for keyword in ["match", "team", "home", "away"]
            )

        return False

    def contains_match_info(self, text: str) -> bool:
        """检查字符串是否包含比赛信息"""
        text_lower = text.lower()
        match_indicators = [
            "vs",
            "versus",
            "v ",
            " - ",
            ":",
            "score",
            "goal",
            "win",
            "lose",
            "draw",
            "premier league",
            "la liga",
            "serie a",
            "bundesliga",
            "ligue 1",
        ]

        # 需要包含多个指示词才认为可能包含比赛数据
        found_count = sum(
            1 for indicator in match_indicators if indicator in text_lower
        )
        return found_count >= 2

    def display_findings(self):
        """显示分析发现"""
        print("\n" + "=" * 60)
        print("🔍 分析发现总结")
        print("=" * 60)

        if self.match_paths:
            print(f"\n🎯 找到可能包含比赛数据的路径 ({len(self.match_paths)} 个):")
            for path in self.match_paths:
                print(f"  • {path}")

        if self.team_paths:
            print(f"\n👥 找到可能包含球队数据的路径 ({len(self.team_paths)} 个):")
            for path in self.team_paths[:5]:  # 只显示前5个
                print(f"  • {path}")
            if len(self.team_paths) > 5:
                print(f"  ... 还有 {len(self.team_paths) - 5} 个路径")

        if self.score_paths:
            print(f"\n⚽ 找到可能包含比分数据的路径 ({len(self.score_paths)} 个):")
            for path in self.score_paths:
                print(f"  • {path}")

        if self.interesting_paths:
            print(f"\n🌟 有趣的数据路径 ({len(self.interesting_paths)} 个):")
            for path in self.interesting_paths:
                print(f"  • {path}")

        # 提供具体的数据提取建议
        print("\n💡 数据提取建议:")
        if self.match_paths:
            print(f"  • 优先检查: {self.match_paths[0]}")
        if self.team_paths:
            print(f"  • 球队数据可能在: {self.team_paths[0]}")

    def extract_sample_data(self, json_file: Path):
        """提取示例数据"""
        print("\n🔬 提取示例数据:")
        print("-" * 40)

        with open(json_file, encoding="utf-8") as f:
            data = json.load(f)

        # 尝试从不同路径提取数据
        if "translations" in data:
            translations = data["translations"]
            print(f"translations类型: {type(translations)}")

            if isinstance(translations, dict):
                print(f"translations键数量: {len(translations)}")

                # 查找可能包含比赛数据的键
                match_keys = [
                    k
                    for k in translations.keys()
                    if any(
                        keyword in k.lower()
                        for keyword in ["match", "team", "league", "fixture"]
                    )
                ]
                print(f"可能的比赛相关键: {match_keys[:10]}")  # 显示前10个

                # 显示一个示例
                if match_keys:
                    sample_key = match_keys[0]
                    sample_value = translations[sample_key]
                    print(f"\n示例键: {sample_key}")
                    print(f"示例值类型: {type(sample_value)}")
                    print(f"示例值: {str(sample_value)[:200]}...")

        # 分析pageProps.fallback
        if "pageProps" in data and "fallback" in data["pageProps"]:
            fallback = data["pageProps"]["fallback"]
            print("\nfallback结构:")
            for key, value in fallback.items():
                value_size = len(json.dumps(value, ensure_ascii=False))
                print(f"  {key}: {type(value).__name__} ({value_size:,} 字节)")


def main():
    """主函数"""
    json_file = Path(__file__).parent.parent / "debug_fotmob_full_response.json"

    if not json_file.exists():
        print(f"❌ 找不到文件: {json_file}")
        print("请先运行: python scripts/dump_fotmob_json.py")
        return

    analyzer = JSONPathAnalyzer()
    analyzer.analyze_json_structure(json_file)
    analyzer.extract_sample_data(json_file)


if __name__ == "__main__":
    main()
