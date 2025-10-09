"""
数据源定义
Data Source Definitions

定义 Feast 特征存储的数据源。
"""



def get_team_data_source() -> PostgreSQLSource:
    """
    获取球队表现数据源

    Returns:
        PostgreSQLSource: 球队数据源
    """
    return PostgreSQLSource(
        name="football_postgres",
        query="""
            SELECT
                team_id,
                recent_5_wins,
                recent_5_draws,
                recent_5_losses,
                recent_5_goals_for,
                recent_5_goals_against,
                recent_5_points,
                recent_5_home_wins,
                recent_5_away_wins,
                recent_5_home_goals_for,
                recent_5_away_goals_for,
                calculation_date as event_timestamp
            FROM team_recent_performance_features
        """,
        timestamp_field="event_timestamp",
    )


def get_match_data_source() -> PostgreSQLSource:
    """
    获取比赛数据源

    Returns:
        PostgreSQLSource: 比赛数据源
    """
    return PostgreSQLSource(
        name="football_match_postgres",
        query="""
            SELECT
                match_id,
                home_team_id,
                away_team_id,
                h2h_total_matches,
                h2h_home_wins,
                h2h_away_wins,
                h2h_draws,
                h2h_home_goals_total,
                h2h_away_goals_total,
                calculation_date as event_timestamp
            FROM historical_matchup_features
        """,
        timestamp_field="event_timestamp",
    )


def get_odds_data_source() -> PostgreSQLSource:
    """
    获取赔率数据源

    Returns:
        PostgreSQLSource: 赔率数据源
    """
    return PostgreSQLSource(

        name="football_odds_postgres",
        query="""
            SELECT
                match_id,
                home_odds_avg,
                draw_odds_avg,
                away_odds_avg,
                home_implied_probability,
                draw_implied_probability,
                away_implied_probability,
                bookmaker_count,
                bookmaker_consensus,
                calculation_date as event_timestamp
            FROM odds_features
        """,
        timestamp_field="event_timestamp",
    )