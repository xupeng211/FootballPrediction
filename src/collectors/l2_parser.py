#!/usr/bin/env python3
"""
完整版L2数据解析器 - 79字段全覆盖版本
基于真实FotMob API数据结构优化，支持80个高价值统计指标的完整提取和存储
"""

import json
import logging
from typing import Dict, Any, Optional, List, Tuple, Union
from dataclasses import dataclass
import re

logger = logging.getLogger(__name__)


@dataclass
class L2MatchStats:
    """L2统计数据结构 - 完整80字段版本（79个统计字段 + 原始数据）"""

    # 基础比赛信息
    home_score: Optional[int] = None
    away_score: Optional[int] = None

    # 控球统计 (2个字段)
    home_possession: Optional[int] = None
    away_possession: Optional[int] = None

    # 期望进球相关 (10个字段)
    home_expected_goals: Optional[float] = None
    away_expected_goals: Optional[float] = None
    home_expected_goals_open_play: Optional[float] = None
    away_expected_goals_open_play: Optional[float] = None
    home_expected_goals_set_play: Optional[float] = None
    away_expected_goals_set_play: Optional[float] = None
    home_expected_goals_non_penalty: Optional[float] = None
    away_expected_goals_non_penalty: Optional[float] = None
    home_expected_goals_on_target: Optional[float] = None
    away_expected_goals_on_target: Optional[float] = None

    # 射门统计 (12个字段)
    home_total_shots: Optional[int] = None
    away_total_shots: Optional[int] = None
    home_shots_on_target: Optional[int] = None
    away_shots_on_target: Optional[int] = None
    home_shots_off_target: Optional[int] = None
    away_shots_off_target: Optional[int] = None
    home_blocked_shots: Optional[int] = None
    away_blocked_shots: Optional[int] = None
    home_shots_inside_box: Optional[int] = None
    away_shots_inside_box: Optional[int] = None
    home_shots_outside_box: Optional[int] = None
    away_shots_outside_box: Optional[int] = None
    home_shots_woodwork: Optional[int] = None
    away_shots_woodwork: Optional[int] = None

    # 绝佳机会 (4个字段)
    home_big_chances_created: Optional[int] = None
    away_big_chances_created: Optional[int] = None
    home_big_chances_missed: Optional[int] = None
    away_big_chances_missed: Optional[int] = None

    # 传球统计 (16个字段)
    home_total_passes: Optional[int] = None
    away_total_passes: Optional[int] = None
    home_accurate_passes: Optional[int] = None
    away_accurate_passes: Optional[int] = None
    home_accurate_passes_pct: Optional[str] = None
    away_accurate_passes_pct: Optional[str] = None
    home_long_balls: Optional[int] = None
    away_long_balls: Optional[int] = None
    home_accurate_long_balls: Optional[int] = None
    away_accurate_long_balls: Optional[int] = None
    home_long_balls_pct: Optional[str] = None
    away_long_balls_pct: Optional[str] = None
    home_crosses: Optional[int] = None
    away_crosses: Optional[int] = None
    home_accurate_crosses: Optional[int] = None
    away_accurate_crosses: Optional[int] = None
    home_crosses_pct: Optional[str] = None
    away_crosses_pct: Optional[str] = None
    home_own_half_passes: Optional[int] = None
    away_own_half_passes: Optional[int] = None
    home_opposition_half_passes: Optional[int] = None
    away_opposition_half_passes: Optional[int] = None
    home_player_throws: Optional[int] = None
    away_player_throws: Optional[int] = None

    # 防守统计 (8个字段)
    home_tackles: Optional[int] = None
    away_tackles: Optional[int] = None
    home_interceptions: Optional[int] = None
    away_interceptions: Optional[int] = None
    home_blocks: Optional[int] = None
    away_blocks: Optional[int] = None
    home_clearances: Optional[int] = None
    away_clearances: Optional[int] = None
    home_keeper_saves: Optional[int] = None
    away_keeper_saves: Optional[int] = None

    # 身体对抗 (8个字段)
    home_duels_won: Optional[int] = None
    away_duels_won: Optional[int] = None
    home_duels_total: Optional[int] = None
    away_duels_total: Optional[int] = None
    home_ground_duels_won: Optional[int] = None
    away_ground_duels_won: Optional[int] = None
    home_ground_duels_won_pct: Optional[str] = None
    away_ground_duels_won_pct: Optional[str] = None
    home_aerial_duels_won: Optional[int] = None
    away_aerial_duels_won: Optional[int] = None
    home_aerial_duels_won_pct: Optional[str] = None
    away_aerial_duels_won_pct: Optional[str] = None
    home_successful_dribbles: Optional[int] = None
    away_successful_dribbles: Optional[int] = None
    home_successful_dribbles_pct: Optional[str] = None
    away_successful_dribbles_pct: Optional[str] = None

    # 定位球和比赛控制 (8个字段)
    home_corners: Optional[int] = None
    away_corners: Optional[int] = None
    home_fouls_committed: Optional[int] = None
    away_fouls_committed: Optional[int] = None
    home_offsides: Optional[int] = None
    away_offsides: Optional[int] = None
    home_touches: Optional[int] = None
    away_touches: Optional[int] = None
    home_touches_opp_box: Optional[int] = None
    away_touches_opp_box: Optional[int] = None

    # 纪律统计 (4个字段)
    home_yellow_cards: Optional[int] = None
    away_yellow_cards: Optional[int] = None
    home_red_cards: Optional[int] = None
    away_red_cards: Optional[int] = None

    # 原始数据存储 (1个字段)
    l2_stats_raw: Optional[Dict] = None


class CompleteL2Parser:
    """完整版L2数据解析器 - 79字段全覆盖"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # 完整的字段映射表 - 基于真实FotMob API数据结构
        # 40个唯一键值，扩展为80个数据库字段（主客队各一）
        self.field_mapping = {
            # 基础统计
            "BallPossesion": ("home_possession", "away_possession"),

            # 期望进球相关 (10个字段)
            "expected_goals": ("home_expected_goals", "away_expected_goals"),
            "expected_goals_open_play": ("home_expected_goals_open_play", "away_expected_goals_open_play"),
            "expected_goals_set_play": ("home_expected_goals_set_play", "away_expected_goals_set_play"),
            "expected_goals_non_penalty": ("home_expected_goals_non_penalty", "away_expected_goals_non_penalty"),
            "expected_goals_on_target": ("home_expected_goals_on_target", "away_expected_goals_on_target"),

            # 射门统计 (12个字段)
            "total_shots": ("home_total_shots", "away_total_shots"),
            "ShotsOnTarget": ("home_shots_on_target", "away_shots_on_target"),
            "ShotsOffTarget": ("home_shots_off_target", "away_shots_off_target"),
            "blocked_shots": ("home_blocked_shots", "away_blocked_shots"),
            "shots_inside_box": ("home_shots_inside_box", "away_shots_inside_box"),
            "shots_outside_box": ("home_shots_outside_box", "away_shots_outside_box"),
            "shots_woodwork": ("home_shots_woodwork", "away_shots_woodwork"),

            # 绝佳机会 (4个字段)
            "big_chance": ("home_big_chances_created", "away_big_chances_created"),
            "big_chance_missed_title": ("home_big_chances_missed", "away_big_chances_missed"),

            # 传球统计 (16个字段)
            "passes": ("home_total_passes", "away_total_passes"),
            "accurate_passes": ("home_accurate_passes", "away_accurate_passes"),
            "long_balls_total": ("home_long_balls", "away_long_balls"),
            "long_balls_accurate": ("home_accurate_long_balls", "away_accurate_long_balls"),
            "accurate_crosses": ("home_accurate_crosses", "away_accurate_crosses"),
            "crosses_total": ("home_crosses", "away_crosses"),
            "own_half_passes": ("home_own_half_passes", "away_own_half_passes"),
            "opposition_half_passes": ("home_opposition_half_passes", "away_opposition_half_passes"),
            "player_throws": ("home_player_throws", "away_player_throws"),
            "Offsides": ("home_offsides", "away_offsides"),

            # 防守统计 (8个字段)
            "matchstats.headers.tackles": ("home_tackles", "away_tackles"),
            "interceptions": ("home_interceptions", "away_interceptions"),
            "shot_blocks": ("home_blocks", "away_blocks"),
            "clearances": ("home_clearances", "away_clearances"),
            "keeper_saves": ("home_keeper_saves", "away_keeper_saves"),

            # 身体对抗 (8个字段)
            "duel_won": ("home_duels_won", "away_duels_won"),
            "duel_total": ("home_duels_total", "away_duels_total"),
            "ground_duels_won": ("home_ground_duels_won", "away_ground_duels_won"),
            "aerials_won": ("home_aerial_duels_won", "away_aerial_duels_won"),
            "dribbles_succeeded": ("home_successful_dribbles", "away_successful_dribbles"),

            # 定位球和比赛控制 (8个字段)
            "corners": ("home_corners", "away_corners"),
            "fouls": ("home_fouls_committed", "away_fouls_committed"),
            "touches": ("home_touches", "away_touches"),
            "touches_opp_box": ("home_touches_opp_box", "away_touches_opp_box"),

            # 纪律统计 (4个字段)
            "yellow_cards": ("home_yellow_cards", "away_yellow_cards"),
            "red_cards": ("home_red_cards", "away_red_cards"),
        }

        # 百分比解析模式
        self.percentage_patterns = [
            re.compile(r'(\d+)\s*\((\d+)%\)'),  # 数字 (百分比%) -> 数字, 百分比
        ]

    def parse_api_response(self, api_data: Dict[str, Any]) -> L2MatchStats:
        """解析FotMob API响应数据"""
        try:
            # 提取统计数据
            content = api_data.get('content', {})
            stats = content.get('stats', {})
            periods = stats.get('Periods', {})
            all_stats = periods.get('All', {})

            # 根据真实API结构：stats是一个包含7个元素的列表
            stats_data = all_stats.get('stats', [])
            if not stats_data:
                self.logger.warning("⚠️ 未找到统计数据结构")
                return L2MatchStats()

            # 创建统计数据对象
            l2_stats = L2MatchStats()

            # 存储原始数据
            l2_stats.l2_stats_raw = all_stats

            # 解析比分
            general = content.get('general', {})
            if general:
                home_team_info = general.get('homeTeam', {})
                away_team_info = general.get('awayTeam', {})

                l2_stats.home_score = home_team_info.get('score')
                l2_stats.away_score = away_team_info.get('score')

            # 遍历所有统计类别（7个类别）
            for category in stats_data:
                if isinstance(category, dict) and 'stats' in category:
                    category_stats = category['stats']
                    for field in category_stats:
                        if isinstance(field, dict) and 'key' in field and 'stats' in field:
                            key = field['key']
                            values = field['stats']

                            # 跳过空值或无效值
                            if not values or len(values) < 2:
                                continue

                            # 处理数据值
                            home_value, away_value = self._process_stat_values(values)

                            # 查找映射
                            if key in self.field_mapping:
                                home_attr, away_attr = self.field_mapping[key]
                                setattr(l2_stats, home_attr, home_value)
                                setattr(l2_stats, away_attr, away_value)

                                # 特殊处理百分比和复杂字段
                                if key == "accurate_passes":
                                    self._parse_percentage_fields(l2_stats, home_value, away_value, 'accurate_passes')
                                elif key == "long_balls_accurate":
                                    self._parse_percentage_fields(l2_stats, home_value, away_value, 'accurate_long_balls')
                                    # 同时处理总长传数
                                    self._parse_total_fields(l2_stats, home_value, away_value, 'long_balls')
                                elif key == "accurate_crosses":
                                    self._parse_percentage_fields(l2_stats, home_value, away_value, 'accurate_crosses')
                                    # 同时处理总传中数
                                    self._parse_total_fields(l2_stats, home_value, away_value, 'crosses')
                                elif key == "ground_duels_won":
                                    self._parse_percentage_fields(l2_stats, home_value, away_value, 'ground_duels_won')
                                elif key == "aerials_won":
                                    self._parse_percentage_fields(l2_stats, home_value, away_value, 'aerial_duels_won')
                                elif key == "dribbles_succeeded":
                                    self._parse_percentage_fields(l2_stats, home_value, away_value, 'successful_dribbles')

                            else:
                                # 记录未映射的键（用于调试）
                                self.logger.debug(f"未映射的键: {key}")

            filled_fields = self._count_filled_fields(l2_stats)
            self.logger.info(f"✅ L2统计数据解析完成，成功提取 {filled_fields} 个指标")

            if filled_fields < 60:
                self.logger.warning(f"⚠️ 字段填充数量较少: {filled_fields}，可能存在问题")

            return l2_stats

        except Exception as e:
            self.logger.error(f"❌ L2数据解析失败: {e}")
            import traceback
            traceback.print_exc()
            return L2MatchStats()

    def _process_stat_values(self, values: List[Union[str, int, float, None]]) -> Tuple[Optional[Union[int, float]], Optional[Union[int, float]]]:
        """处理统计数据值"""
        try:
            home_val = values[0] if len(values) > 0 else None
            away_val = values[1] if len(values) > 1 else None

            # 处理字符串数值
            if isinstance(home_val, str):
                if home_val.isdigit():
                    home_val = int(home_val)
                elif home_val.replace('.', '').replace('-', '').isdigit():
                    home_val = float(home_val)
                elif home_val == 'None':
                    home_val = None

            if isinstance(away_val, str):
                if away_val.isdigit():
                    away_val = int(away_val)
                elif away_val.replace('.', '').replace('-', '').isdigit():
                    away_val = float(away_val)
                elif away_val == 'None':
                    away_val = None

            return home_val, away_val

        except Exception:
            return None, None

    def _parse_percentage_fields(self, l2_stats: L2MatchStats, home_value: Optional[Union[int, float]], away_value: Optional[Union[int, float]], base_field: str) -> None:
        """解析百分比字段并设置相关属性"""
        try:
            # 解析主队数据
            if isinstance(home_value, str) and home_value:
                # 匹配格式: "254 (81%)" 或 "254 81%"
                match = re.search(r'(\d+)', home_value)
                if match:
                    count_val = int(match.group(1))
                    setattr(l2_stats, f'home_{base_field}', count_val)

                    # 设置百分比字段
                    pct_match = re.search(r'(\d+)%', home_value)
                    if pct_match:
                        pct_val = int(pct_match.group(1))
                        setattr(l2_stats, f'home_{base_field}_pct', f'{pct_val}%')

            # 解析客队数据
            if isinstance(away_value, str) and away_value:
                match = re.search(r'(\d+)', away_value)
                if match:
                    count_val = int(match.group(1))
                    setattr(l2_stats, f'away_{base_field}', count_val)

                    # 设置百分比字段
                    pct_match = re.search(r'(\d+)%', away_value)
                    if pct_match:
                        pct_val = int(pct_match.group(1))
                        setattr(l2_stats, f'away_{base_field}_pct', f'{pct_val}%')

        except Exception as e:
            self.logger.warning(f"⚠️ 百分比字段解析失败 {base_field}: {e}")

    def _parse_total_fields(self, l2_stats: L2MatchStats, home_value: Optional[Union[int, float]], away_value: Optional[Union[int, float]], total_field: str) -> None:
        """解析总数字段（用于传中、长传等）"""
        try:
            # 如果当前值已经是总数，直接设置
            if isinstance(home_value, (int, float)) and not isinstance(home_value, str):
                setattr(l2_stats, f'home_{total_field}', int(home_value))
            elif isinstance(home_value, str):
                # 从字符串中提取总数
                numbers = re.findall(r'\d+', home_value)
                if numbers:
                    setattr(l2_stats, f'home_{total_field}', int(numbers[0]))

            if isinstance(away_value, (int, float)) and not isinstance(away_value, str):
                setattr(l2_stats, f'away_{total_field}', int(away_value))
            elif isinstance(away_value, str):
                numbers = re.findall(r'\d+', away_value)
                if numbers:
                    setattr(l2_stats, f'away_{total_field}', int(numbers[0]))

        except Exception as e:
            self.logger.warning(f"⚠️ 总数字段解析失败 {total_field}: {e}")

    def _count_filled_fields(self, l2_stats: L2MatchStats) -> int:
        """计算已填充的字段数量（排除原始数据字段）"""
        count = 0
        for attr_name in dir(l2_stats):
            if not attr_name.startswith('_') and not attr_name.startswith('l2_') and hasattr(l2_stats, attr_name):
                value = getattr(l2_stats, attr_name)
                if value is not None:
                    count += 1
        return count

    def parse_from_json_file(self, json_file_path: str) -> L2MatchStats:
        """从JSON文件解析数据"""
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return self.parse_api_response(data)
        except Exception as e:
            self.logger.error(f"❌ 从JSON文件解析失败: {e}")
            return L2MatchStats()

    def get_field_summary(self) -> Dict[str, int]:
        """获取字段映射摘要"""
        return {
            'total_unique_keys': len(self.field_mapping),
            'potential_database_fields': len(self.field_mapping) * 2,
            'percentage_fields_with_pct': 6,  # 有对应百分比字段的数量
            'defined_dataclass_fields': len([field for field in dir(L2MatchStats) if not field.startswith('_')]) - 1,  # 减去l2_stats_raw
        }

    def validate_data_quality(self, l2_stats: L2MatchStats) -> Dict[str, Any]:
        """验证数据质量"""
        validation_results = {
            'total_fields': 0,
            'critical_fields_filled': 0,
            'advanced_fields_filled': 0,
            'data_quality_score': 0.0,
            'warnings': []
        }

        # 核心高价值字段
        critical_fields = [
            'home_possession', 'away_possession',
            'home_expected_goals', 'away_expected_goals',
            'home_total_shots', 'away_total_shots',
            'home_shots_on_target', 'away_shots_on_target',
            'home_big_chances_created', 'away_big_chances_created',
            'home_corners', 'away_corners',
            'home_yellow_cards', 'away_yellow_cards'
        ]

        # 进阶字段
        advanced_fields = [
            'home_expected_goals_on_target', 'away_expected_goals_on_target',
            'home_shots_inside_box', 'away_shots_inside_box',
            'home_accurate_passes', 'away_accurate_passes',
            'home_accurate_crosses', 'away_accurate_crosses',
            'home_tackles', 'away_tackles',
            'home_aerial_duels_won', 'away_aerial_duels_won'
        ]

        for field in critical_fields:
            if getattr(l2_stats, field) is not None:
                validation_results['critical_fields_filled'] += 1

        for field in advanced_fields:
            if getattr(l2_stats, field) is not None:
                validation_results['advanced_fields_filled'] += 1

        validation_results['total_fields'] = self._count_filled_fields(l2_stats)

        # 计算质量分数
        critical_score = (validation_results['critical_fields_filled'] / len(critical_fields)) * 50
        advanced_score = (validation_results['advanced_fields_filled'] / len(advanced_fields)) * 30
        coverage_score = min((validation_results['total_fields'] / 70) * 20, 20)  # 假设最多70个字段

        validation_results['data_quality_score'] = critical_score + advanced_score + coverage_score

        # 生成警告
        if validation_results['critical_fields_filled'] < len(critical_fields) * 0.8:
            validation_results['warnings'].append("核心字段填充不足")
        if validation_results['total_fields'] < 50:
            validation_results['warnings'].append("总字段填充数量过低")

        return validation_results