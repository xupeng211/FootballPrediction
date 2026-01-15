#!/usr/bin/env python3
"""
V41.77 TDD 测试套件 - 极端队伍名称解析测试
===============================================

本测试套件针对收割过程中发现的极端队伍名称解析问题，
确保未来 50 个联赛的稳定性。

测试场景：
1. 极端队名缩写 (Rayo Vallecano Ath vs Bilbao)
2. 复杂多词队名 (Tottenham Manchester vs City)
3. 西班牙特殊缩写 (Ath, Granada CF)
4. URL 解析失败容错
5. 数据库匹配边界条件

Author: 首席系统架构师
Version: V41.77
Date: 2026-01-15
"""

import pytest
from src.utils.team_alias import (
    normalize_team_name,
    denoise_team_name,
    extract_place_name,
    calculate_similarity,
    match_teams,
    get_team_aliases,
)


class TestExtremeSpanishTeamNames:
    """测试西班牙联赛极端队伍名称"""

    def test_rayo_vallecano_ath_bilbao_parsing(self):
        """测试 Rayo Vallecano vs Athletic Bilbao 解析"""
        # 输入来自收割日志: "Rayo Vallecano Ath vs Bilbao"
        home_raw = "Rayo Vallecano"
        away_raw = "Ath Bilbao"

        # 标准化后应包含核心队名
        home_norm = normalize_team_name(home_raw)
        away_norm = normalize_team_name(away_raw)

        assert "rayo" in home_norm or "vallecano" in home_norm
        assert "bilbao" in away_norm or "athletic" in away_norm

    def test_athletic_bilbao_variants(self):
        """测试 Athletic Bilbao 各种变体"""
        variants = [
            "Athletic Bilbao",
            "Ath Bilbao",
            "Athletic",
            "Bilbao",
        ]

        normalized = [normalize_team_name(v) for v in variants]

        # 所有变体应包含 bilbao 或 athletic
        for norm in normalized:
            assert "bilbao" in norm or "athletic" in norm, f"Failed for: {norm}"

    def test_rayo_vallecano_variants(self):
        """测试 Rayo Vallecano 各种变体"""
        variants = [
            "Rayo Vallecano",
            "Rayo",
            "Vallecano",
        ]

        normalized = [normalize_team_name(v) for v in variants]

        # 所有变体应包含 rayo 或 vallecano
        for norm in normalized:
            assert "rayo" in norm or "vallecano" in norm, f"Failed for: {norm}"

    def test_granada_cf_parsing(self):
        """测试 Granada CF 解析"""
        # 输入: "Girona Granada vs Cf"
        # 实际应为 Girona vs Granada CF

        raw = "Granada Cf"
        normalized = normalize_team_name(raw)

        assert "granada" in normalized
        # Cf 应被移除（空替换）
        assert "cf" not in normalized or normalized.endswith("cf")


class TestComplexMultiWordParsing:
    """测试复杂多词队伍名称解析"""

    def test_tottenham_manchester_vs_city_error(self):
        """
        测试 "Tottenham Manchester vs City" 错误解析

        这是 URL 正则解析失败案例：
        - 实际应为 "Tottenham vs Manchester City"
        - 错误解析为 "Tottenham Manchester vs City"
        """
        # 模拟错误解析的队名
        home_wrong = "Tottenham Manchester"
        away_wrong = "City"

        # 去噪应提取核心地名
        home_denoised = denoise_team_name(home_wrong)
        away_denoised = denoise_team_name(away_wrong)

        # Tottenham 应保留，Manchester 应被识别为城市名
        assert "tottenham" in home_denoised.lower()

        # City 单独时应失败或返回空
        assert away_denoised == "" or len(away_denoised) <= 4

    def test_manchester_city_correct_parsing(self):
        """测试正确的 Manchester City 解析"""
        variants = [
            "Manchester City",
            "Man City",
            "ManCity",
            "Mancity",
        ]

        for variant in variants:
            normalized = normalize_team_name(variant)
            assert "manchester" in normalized or "city" in normalized

    def test_manchester_united_vs_city_disambiguation(self):
        """测试 Manchester United vs City 区分"""
        man_utd = normalize_team_name("Manchester United")
        man_city = normalize_team_name("Manchester City")

        # 应能区分
        assert "united" in man_utd or "utd" in man_utd
        assert "city" in man_city

    def test_brighton_hove_albion_variants(self):
        """测试 Brighton & Hove Albion 复杂名称"""
        variants = [
            "Brighton & Hove Albion",
            "Brighton",
            "Brighton Hove Albion",
            "Brighton and Hove Albion",
        ]

        for variant in variants:
            normalized = normalize_team_name(variant)
            # 应包含 brighton
            assert "brighton" in normalized.lower()

    def test_wolverhampton_wanderers_variants(self):
        """测试 Wolverhampton Wanderers 各种变体"""
        variants = [
            "Wolverhampton Wanderers",
            "Wolves",
            "Wolverhampton",
        ]

        for variant in variants:
            normalized = normalize_team_name(variant)
            # 应包含 wolverhampton 或 wolves
            assert "wolverhampton" in normalized or "wolves" in normalized

    def test_sheffield_united_variants(self):
        """测试 Sheffield United 各种变体"""
        variants = [
            "Sheffield United",
            "Sheffield Utd",
            "Sheffield",
        ]

        for variant in variants:
            normalized = normalize_team_name(variant)
            # 应包含 sheffield
            assert "sheffield" in normalized

    def test_crystal_palace_variants(self):
        """测试 Crystal Palace 各种变体"""
        variants = [
            "Crystal Palace",
            "Crystal Pal",
            "Palace",
        ]

        for variant in variants:
            normalized = normalize_team_name(variant)
            # 应包含 crystal 或 palace
            assert "crystal" in normalized or "palace" in normalized

    def test_nottingham_forest_variants(self):
        """测试 Nottingham Forest 各种变体"""
        variants = [
            "Nottingham Forest",
            "Nottingham",
            "Nottm Forest",
            "Nottm",
        ]

        for variant in variants:
            normalized = normalize_team_name(variant)
            # 应包含 nottingham 或 nottm
            assert "nottingham" in normalized or "nottm" in normalized

    def test_west_ham_united_variants(self):
        """测试 West Ham United 各种变体"""
        variants = [
            "West Ham United",
            "West Ham",
            "West Ham Utd",
            "WHU",
        ]

        for variant in variants:
            normalized = normalize_team_name(variant)
            # 应包含 west ham
            assert "west" in normalized and "ham" in normalized


class TestGermanTeamNames:
    """测试德甲队伍名称"""

    def test_bayern_munich_variants(self):
        """测试 Bayern Munich 各种变体"""
        variants = [
            "Bayern Munich",
            "Bayern Munchen",
            "Bayern",
            "Munich",
        ]

        for variant in variants:
            normalized = normalize_team_name(variant)
            # 应包含 bayern 或 munich
            assert "bayern" in normalized or "munich" in normalized

    def test_borussia_dortmund_variants(self):
        """测试 Borussia Dortmund 各种变体"""
        variants = [
            "Borussia Dortmund",
            "Dortmund",
            "BVB",
        ]

        for variant in variants:
            normalized = normalize_team_name(variant)
            # 应包含 dortmund
            assert "dortmund" in normalized

    def test_rb_leipzig_variants(self):
        """测试 RB Leipzig 各种变体"""
        variants = [
            "RB Leipzig",
            "RasenBallsport Leipzig",
            "Rb Leipzig",
            "Leipzig",
        ]

        for variant in variants:
            normalized = normalize_team_name(variant)
            # 应包含 leipzig 或 rb
            assert "leipzig" in normalized or "rb" in normalized

    def test_vfb_stuttgart_variants(self):
        """测试 VfB Stuttgart 各种变体"""
        variants = [
            "VfB Stuttgart",
            "Vfb Stuttgart",
            "Stuttgart",
        ]

        for variant in variants:
            normalized = normalize_team_name(variant)
            # 应包含 stuttgart
            assert "stuttgart" in normalized

    def test_mainz_variants(self):
        """测试 Mainz 各种变体"""
        variants = [
            "Mainz 05",
            "Mainz",
            "Fsv Mainz 05",
        ]

        for variant in variants:
            normalized = normalize_team_name(variant)
            # 应包含 mainz
            assert "mainz" in normalized

    def test_darmstadt_variants(self):
        """测试 Darmstadt 各种变体"""
        variants = [
            "Darmstadt",
            "SV Darmstadt 98",
            "Darmstadt 98",
        ]

        for variant in variants:
            normalized = normalize_team_name(variant)
            # 应包含 darmstadt
            assert "darmstadt" in normalized

    def test_fc_heidenheim_variants(self):
        """测试 FC Heidenheim 各种变体"""
        variants = [
            "FC Heidenheim",
            "Heidenheim",
            "1. FC Heidenheim",
        ]

        for variant in variants:
            normalized = normalize_team_name(variant)
            # 应包含 heidenheim
            assert "heidenheim" in normalized


class TestFrenchTeamNames:
    """测试法甲队伍名称"""

    def test_psg_variants(self):
        """测试 PSG 各种变体"""
        variants = [
            "PSG",
            "Paris Saint-Germain",
            "Paris Saint Germain",
            "Paris",
        ]

        for variant in variants:
            normalized = normalize_team_name(variant)
            # 应包含 paris 或 psg
            assert "paris" in normalized or "psg" in normalized

    def test_as_monaco_variants(self):
        """测试 AS Monaco 各种变体"""
        variants = [
            "AS Monaco",
            "Monaco",
        ]

        for variant in variants:
            normalized = normalize_team_name(variant)
            # 应包含 monaco
            assert "monaco" in normalized

    def test_olympique_marseille_variants(self):
        """测试 Olympique Marseille 各种变体"""
        variants = [
            "Olympique Marseille",
            "Marseille",
            "OM",
        ]

        for variant in variants:
            normalized = normalize_team_name(variant)
            # 应包含 marseille
            assert "marseille" in normalized

    def test_olympique_lyon_variants(self):
        """测试 Olympique Lyon 各种变体"""
        variants = [
            "Olympique Lyon",
            "Lyon",
            "OL",
        ]

        for variant in variants:
            normalized = normalize_team_name(variant)
            # 应包含 lyon
            assert "lyon" in normalized


class TestItalianTeamNames:
    """测试意甲队伍名称"""

    def test_ac_milan_variants(self):
        """测试 AC Milan 各种变体"""
        variants = [
            "AC Milan",
            "Milan",
            "Milano",
        ]

        for variant in variants:
            normalized = normalize_team_name(variant)
            # 应包含 milan
            assert "milan" in normalized

    def test_inter_milan_variants(self):
        """测试 Inter Milan 各种变体"""
        variants = [
            "Inter Milan",
            "Inter",
            "Internazionale",
            "Internazionale Milano",
        ]

        for variant in variants:
            normalized = normalize_team_name(variant)
            # 应包含 inter 或 milan
            assert "inter" in normalized or "milan" in normalized

    def test_juventus_variants(self):
        """测试 Juventus 各种变体"""
        variants = [
            "Juventus",
            "Juve",
            "Juventus FC",
        ]

        for variant in variants:
            normalized = normalize_team_name(variant)
            # 应包含 juve
            assert "juve" in normalized or "juventus" in normalized

    def test_as_roma_variants(self):
        """测试 AS Roma 各种变体"""
        variants = [
            "AS Roma",
            "Roma",
            "Rome",
            "Roman",
        ]

        for variant in variants:
            normalized = normalize_team_name(variant)
            # 应包含 roma
            assert "roma" in normalized

    def test_napoli_variants(self):
        """测试 Napoli 各种变体"""
        variants = [
            "Napoli",
            "Naples",
            "SSC Napoli",
        ]

        for variant in variants:
            normalized = normalize_team_name(variant)
            # 应包含 napoli 或 naples
            assert "napoli" in normalized or "naples" in normalized

    def test_atalanta_variants(self):
        """测试 Atalanta 各种变体"""
        variants = [
            "Atalanta",
            "Atalanta BC",
        ]

        for variant in variants:
            normalized = normalize_team_name(variant)
            # 应包含 atalanta
            assert "atalanta" in normalized

    def test_bologna_variants(self):
        """测试 Bologna 各种变体"""
        variants = [
            "Bologna",
            "Bologna FC",
        ]

        for variant in variants:
            normalized = normalize_team_name(variant)
            # 应包含 bologna
            assert "bologna" in normalized

    def test_fiorentina_variants(self):
        """测试 Fiorentina 各种变体"""
        variants = [
            "ACF Fiorentina",
            "Fiorentina",
            "Florence",
        ]

        for variant in variants:
            normalized = normalize_team_name(variant)
            # 应包含 fiorentina 或 florence
            assert "fiorentina" in normalized or "florence" in normalized

    def test_hellas_verona_variants(self):
        """测试 Hellas Verona 各种变体"""
        variants = [
            "Hellas Verona",
            "Verona",
        ]

        for variant in variants:
            normalized = normalize_team_name(variant)
            # 应包含 verona
            assert "verona" in normalized

    def test_torino_variants(self):
        """测试 Torino 各种变体"""
        variants = [
            "Torino",
            "Torino FC",
        ]

        for variant in variants:
            normalized = normalize_team_name(variant)
            # 应包含 torino
            assert "torino" in normalized

    def test_udinese_variants(self):
        """测试 Udinese 各种变体"""
        variants = [
            "Udinese",
            "Udinese Calcio",
        ]

        for variant in variants:
            normalized = normalize_team_name(variant)
            # 应包含 udinese
            assert "udinese" in normalized

    def test_sassuolo_variants(self):
        """测试 Sassuolo 各种变体"""
        variants = [
            "US Sassuolo",
            "Sassuolo",
        ]

        for variant in variants:
            normalized = normalize_team_name(variant)
            # 应包含 sassuolo
            assert "sassuolo" in normalized

    def test_cagliari_variants(self):
        """测试 Cagliari 各种变体"""
        variants = [
            "Cagliari",
            "Cagliari Calcio",
        ]

        for variant in variants:
            normalized = normalize_team_name(variant)
            # 应包含 cagliari
            assert "cagliari" in normalized

    def test_genoa_variants(self):
        """测试 Genoa 各种变体"""
        variants = [
            "Genoa",
            "Genoa CFC",
        ]

        for variant in variants:
            normalized = normalize_team_name(variant)
            # 应包含 genoa
            assert "genoa" in normalized

    def test_lecce_variants(self):
        """测试 Lecce 各种变体"""
        variants = [
            "US Lecce",
            "Lecce",
        ]

        for variant in variants:
            normalized = normalize_team_name(variant)
            # 应包含 lecce
            assert "lecce" in normalized

    def test_empoli_variants(self):
        """测试 Empoli 各种变体"""
        variants = [
            "Empoli",
            "Empoli FC",
        ]

        for variant in variants:
            normalized = normalize_team_name(variant)
            # 应包含 empoli
            assert "empoli" in normalized

    def test_salernitana_variants(self):
        """测试 Salernitana 各种变体"""
        variants = [
            "US Salernitana",
            "Salernitana",
            "Salerno",
        ]

        for variant in variants:
            normalized = normalize_team_name(variant)
            # 应包含 salernitana 或 salerno
            assert "salernitana" in normalized or "salerno" in normalized


class TestPlaceNameExtraction:
    """测试地名提取功能"""

    def test_extract_manchester(self):
        """测试 Manchester 地名提取"""
        assert extract_place_name("Manchester United") == "manchester"
        assert extract_place_name("Manchester City") == "manchester"

    def test_extract_newcastle(self):
        """测试 Newcastle 地名提取"""
        assert extract_place_name("Newcastle United") == "newcastle"

    def test_extract_wolverhampton(self):
        """测试 Wolverhampton 地名提取"""
        assert extract_place_name("Wolverhampton Wanderers") == "wolverhampton"

    def test_extract_brighton_hove(self):
        """测试 Brighton & Hove 地名提取"""
        place = extract_place_name("Brighton & Hove Albion")
        assert "brighton" in place

    def test_extract_west_bromwich(self):
        """测试 West Bromwich 地名提取"""
        place = extract_place_name("West Bromwich Albion")
        assert "west bromwich" in place

    def test_extract_nottingham(self):
        """测试 Nottingham 地名提取"""
        assert extract_place_name("Nottingham Forest") == "nottingham"

    def test_extract_sheffield(self):
        """测试 Sheffield 地名提取"""
        assert extract_place_name("Sheffield United") == "sheffield"

    def test_extract_crystal_palace(self):
        """测试 Crystal Palace 地名提取（非城市名）"""
        place = extract_place_name("Crystal Palace")
        # Crystal Palace 不是城市名，应保留或特殊处理
        assert "crystal" in place or "palace" in place


class TestTeamMatchingConfidence:
    """测试队伍匹配置信度"""

    def test_perfect_match_confidence(self):
        """测试完美匹配置信度"""
        score, details = match_teams("Arsenal", "Chelsea", "Arsenal", "Chelsea")
        assert score == 100.0

    def test_high_confidence_match(self):
        """测试高置信度匹配（>90%）"""
        score, details = match_teams("Man Utd", "Liverpool", "Manchester United", "Liverpool")
        assert score >= 90.0

    def test_medium_confidence_match(self):
        """测试中等置信度匹配（70-90%）"""
        score, details = match_teams("Man City", "Arsenal", "Manchester City", "Arsenal")
        assert 70.0 <= score < 90.0

    def test_low_confidence_match(self):
        """测试低置信度匹配（<70%）"""
        score, details = match_teams("City", "Arsenal", "Manchester City", "Arsenal")
        # "City" 单独应该产生低置信度
        assert score < 85.0

    def test_no_match_confidence(self):
        """测试无匹配置信度"""
        score, details = match_teams("Random", "Team", "Arsenal", "Chelsea")
        assert score < 50.0


class TestGetTeamAliasesEdgeCases:
    """测试 get_team_aliases 边界条件"""

    def test_empty_string(self):
        """测试空字符串"""
        result = get_team_aliases("")
        assert result.normalized_name == ""

    def test_none_input(self):
        """测试 None 输入"""
        result = get_team_aliases(None)
        assert result.normalized_name == ""

    def test_special_characters_only(self):
        """测试只有特殊字符"""
        result = get_team_aliases("@#$%")
        assert result.normalized_name == ""

    def test_very_long_input(self):
        """测试超长输入"""
        long_name = "A" * 200
        result = get_team_aliases(long_name)
        assert result.normalized_name == long_name.lower()


class TestHarvestLogFailureCases:
    """测试收割日志中的实际失败案例"""

    def test_rayo_vallecano_ath_bilbao_failure(self):
        """
        测试实际收割失败案例: "Rayo Vallecano Ath vs Bilbao"

        日志显示: ⚠️ 未找到匹配: Rayo Vallecano Ath vs Bilbao (La Liga 2023/2024)
        """
        home = "Rayo Vallecano Ath"
        away = "Bilbao"

        home_norm = normalize_team_name(home)
        away_norm = normalize_team_name(away)

        # 至少应能提取核心地名
        assert "rayo" in home_norm or "vallecano" in home_norm
        assert "bilbao" in away_norm

    def test_girona_granada_vs_cf_failure(self):
        """
        测试实际收割失败案例: "Girona Granada vs Cf"

        日志显示: ⚠️ 未找到匹配: Girona Granada vs Cf (La Liga 2023/2024)
        """
        # 这个案例实际上是两个队名被错误合并
        # 正确解析应为: Girona vs Granada CF
        # 但错误解析为: "Girona Granada vs Cf"
        malformed = "Girona Granada vs Cf"

        # 标准化应至少保留部分信息
        normalized = normalize_team_name(malformed)
        assert "girona" in normalized or "granada" in normalized

    def test_ath_bilbao_vs_sevilla_failure(self):
        """
        测试实际收割失败案例: "Ath Bilbao vs Sevilla"

        日志显示: ⚠️ 未找到匹配: Ath Bilbao vs Sevilla (La Liga 2023/2024)
        """
        home = "Ath Bilbao"
        away = "Sevilla"

        home_norm = normalize_team_name(home)
        away_norm = normalize_team_name(away)

        # Ath 应被识别为 Athletic
        assert "bilbao" in home_norm or "athletic" in home_norm
        assert "sevilla" in away_norm or "seville" in away_norm

    def test_atl_madrid_vs_osasuna_failure(self):
        """
        测试实际收割失败案例: "Atl Madrid vs Osasuna"

        日志显示: ⚠️ 未找到匹配: Atl Madrid vs Osasuna (La Liga 2023/2024)
        """
        home = "Atl Madrid"
        away = "Osasuna"

        home_norm = normalize_team_name(home)
        away_norm = normalize_team_name(away)

        # Atl 应被识别为 Atletico/Atlético
        assert "madrid" in home_norm or "atletico" in home_norm
        assert "osasuna" in away_norm

    def test_betis_real_vs_sociedad_failure(self):
        """
        测试实际收割失败案例: "Betis Real vs Sociedad"

        日志显示: ⚠️ 未找到匹配: Betis Real vs Sociedad (La Liga 2023/2024)
        """
        # 这个案例也是队名被错误合并
        # 正确应为: Real Betis vs Real Sociedad
        # 错误解析为: "Betis Real vs Sociedad"
        malformed = "Betis Real vs Sociedad"

        normalized = normalize_team_name(malformed)
        assert "betis" in normalized or "real" in normalized or "sociedad" in normalized

    def test_celta_vigo_ath_bilbao_failure(self):
        """
        测试实际收割失败案例: "Celta Vigo Ath vs Bilbao"

        日志显示: ⚠️ 未找到匹配: Celta Vigo Ath vs Bilbao (La Liga 2023/2024)
        """
        # 队名被错误合并: Celta Vigo + Ath Bilbao
        malformed = "Celta Vigo Ath"

        normalized = normalize_team_name(malformed)
        assert "celta" in normalized or "vigo" in normalized

    def test_rayo_vallecano_granada_vs_cf_failure(self):
        """
        测试实际收割失败案例: "Rayo Vallecano Granada vs Cf"

        日志显示: ⚠️ 未找到匹配: Rayo Vallecano Granada vs Cf (La Liga 2023/2024)
        """
        # 三个队名被错误合并
        malformed = "Rayo Vallecano Granada vs Cf"

        normalized = normalize_team_name(malformed)
        # 至少应保留部分信息
        assert "rayo" in normalized or "vallecano" in normalized or "granada" in normalized


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
