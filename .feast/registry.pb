
o
O
team*ÁêÉÈòüÂÆû‰ΩìÔºåÁî®‰∫éÁêÉÈòüÁ∫ßÂà´ÁöÑÁâπÂæÅ"teamJfootball_prediction
ª‡é∆«≠áÁ‡é∆∏Õ¥π
q
Q
match*ÊØîËµõÂÆû‰ΩìÔºåÁî®‰∫éÊØîËµõÁ∫ßÂà´ÁöÑÁâπÂæÅ"matchJfootball_prediction
ª‡é∆¯Å¯àÁ‡é∆–∫àª
J
*
__dummy"
__dummy_idJfootball_prediction
ª‡é∆¸≈áÁ‡é∆êˆÉΩ1"$8a038520-ef00-4a8d-9f81-519482b35b98*Á‡é∆à√áΩ2ä

È	
team_recent_performancefootball_predictionteam"
recent_5_wins"
recent_5_draws"
recent_5_losses"
recent_5_goals_for"
recent_5_goals_against"
recent_5_points"
recent_5_home_wins"
recent_5_away_wins"
recent_5_home_goals_for"
recent_5_away_goals_for2Äı$:Åevent_timestampÇ‘
—{"name": "team_performance_source", "query": "\n                SELECT \n                    team_id,\n                    recent_5_wins,\n                    recent_5_draws, \n                    recent_5_losses,\n                    recent_5_goals_for,\n                    recent_5_goals_against,\n                    recent_5_points,\n                    recent_5_home_wins,\n                    recent_5_away_wins,\n                    recent_5_home_goals_for,\n                    recent_5_away_goals_for,\n                    calculation_date as event_timestamp\n                FROM team_recent_performance_features\n                WHERE calculation_date >= NOW() - INTERVAL '1 year'\n            ", "table": ""}äZfeast.infra.offline_stores.contrib.postgres_offline_store.postgres_source.PostgreSQLSource¢team_performance_sourceíÁ‡é∆»≥ßª"Á‡é∆®∏òº@R.ÁêÉÈòüËøëÊúüË°®Áé∞ÁâπÂæÅÔºàÊúÄËøë5Âú∫ÊØîËµõÔºâb
team
Á‡é∆¿ï°ºÁ‡é∆¿ï°º2ª
ö
historical_matchupfootball_predictionmatch"
home_team_id"
away_team_id"
h2h_total_matches"
h2h_home_wins"
h2h_away_wins"
	h2h_draws"
h2h_home_goals_total"
h2h_away_goals_total2Äöû:ïevent_timestampÇÊ
„{"name": "historical_matchup_source", "query": "\n                SELECT\n                    match_id,\n                    home_team_id,\n                    away_team_id, \n                    h2h_total_matches,\n                    h2h_home_wins,\n                    h2h_away_wins,\n                    h2h_draws,\n                    h2h_home_goals_total,\n                    h2h_away_goals_total,\n                    calculation_date as event_timestamp\n                FROM historical_matchup_features  \n                WHERE calculation_date >= NOW() - INTERVAL '1 year'\n            ", "table": ""}äZfeast.infra.offline_stores.contrib.postgres_offline_store.postgres_source.PostgreSQLSource¢historical_matchup_sourceíÁ‡é∆ÿ¯™ª"Á‡é∆–Î»º@RÁêÉÈòüÂéÜÂè≤ÂØπÊàòÁâπÂæÅb	
match
Á‡é∆‡≠ÕºÁ‡é∆‡≠Õº2æ
ù
odds_featuresfootball_predictionmatch"
home_odds_avg"
draw_odds_avg"
away_odds_avg"
home_implied_probability"
draw_implied_probability"
away_implied_probability"
bookmaker_count"
bookmaker_consensus2‡®:áevent_timestampÇÊ
„{"name": "odds_source", "query": "\n                SELECT\n                    match_id,\n                    home_odds_avg,\n                    draw_odds_avg,\n                    away_odds_avg,\n                    home_implied_probability,\n                    draw_implied_probability,  \n                    away_implied_probability,\n                    bookmaker_count,\n                    bookmaker_consensus,\n                    calculation_date as event_timestamp\n                FROM odds_features\n                WHERE calculation_date >= NOW() - INTERVAL '1 year'\n            ", "table": ""}äZfeast.infra.offline_stores.contrib.postgres_offline_store.postgres_source.PostgreSQLSource¢odds_sourceíÁ‡é∆Ä∂Æª"Á‡é∆–€˜º@RËµîÁéáË°çÁîüÁâπÂæÅb	
match
Á‡é∆ÿˆ˚ºÁ‡é∆ÿˆ˚ºbóevent_timestampÇ‘
—{"name": "team_performance_source", "query": "\n                SELECT \n                    team_id,\n                    recent_5_wins,\n                    recent_5_draws, \n                    recent_5_losses,\n                    recent_5_goals_for,\n                    recent_5_goals_against,\n                    recent_5_points,\n                    recent_5_home_wins,\n                    recent_5_away_wins,\n                    recent_5_home_goals_for,\n                    recent_5_away_goals_for,\n                    calculation_date as event_timestamp\n                FROM team_recent_performance_features\n                WHERE calculation_date >= NOW() - INTERVAL '1 year'\n            ", "table": ""}äZfeast.infra.offline_stores.contrib.postgres_offline_store.postgres_source.PostgreSQLSource¢team_performance_source™football_predictioníÁ‡é∆»≥ßª"Á‡é∆®∏òºb´event_timestampÇÊ
„{"name": "historical_matchup_source", "query": "\n                SELECT\n                    match_id,\n                    home_team_id,\n                    away_team_id, \n                    h2h_total_matches,\n                    h2h_home_wins,\n                    h2h_away_wins,\n                    h2h_draws,\n                    h2h_home_goals_total,\n                    h2h_away_goals_total,\n                    calculation_date as event_timestamp\n                FROM historical_matchup_features  \n                WHERE calculation_date >= NOW() - INTERVAL '1 year'\n            ", "table": ""}äZfeast.infra.offline_stores.contrib.postgres_offline_store.postgres_source.PostgreSQLSource¢historical_matchup_source™football_predictioníÁ‡é∆ÿ¯™ª"Á‡é∆–Î»ºbùevent_timestampÇÊ
„{"name": "odds_source", "query": "\n                SELECT\n                    match_id,\n                    home_odds_avg,\n                    draw_odds_avg,\n                    away_odds_avg,\n                    home_implied_probability,\n                    draw_implied_probability,  \n                    away_implied_probability,\n                    bookmaker_count,\n                    bookmaker_consensus,\n                    calculation_date as event_timestamp\n                FROM odds_features\n                WHERE calculation_date >= NOW() - INTERVAL '1 year'\n            ", "table": ""}äZfeast.infra.offline_stores.contrib.postgres_offline_store.postgres_source.PostgreSQLSource¢odds_source™football_predictioníÁ‡é∆Ä∂Æª"Á‡é∆–€˜ºz;
football_prediction$843d457c-b965-4abb-837f-89dd5981caf3ä5

football_prediction
ª‡é∆–ç∂áª‡é∆–ç∂á