-- 修复索引语法错误和函数嵌套问题

-- 删除有问题的索引
DROP INDEX IF EXISTS idx_match_advanced_stats_shots_total;
DROP INDEX IF EXISTS idx_match_advanced_stats_xg_total;

-- 重新创建正确的索引
CREATE INDEX idx_match_advanced_stats_shots_total ON match_advanced_stats((shots_home + shots_away));
CREATE INDEX idx_match_advanced_stats_xg_total ON match_advanced_stats((home_xg + away_xg));

-- 重新创建函数（修复嵌套聚合问题）
CREATE OR REPLACE FUNCTION extract_shot_features(match_data JSONB)
RETURNS JSONB AS $$
BEGIN
    RETURN jsonb_build_object(
        'total_shots', jsonb_array_length(match_data),
        'xg_total', COALESCE((SELECT SUM((elem->>'expectedGoals')::NUMERIC)
                               FROM jsonb_array_elements(match_data) AS elem), 0),
        'avg_xg', COALESCE((SELECT AVG((elem->>'expectedGoals')::NUMERIC)
                              FROM jsonb_array_elements(match_data) AS elem), 0),
        'high_quality_shots', COALESCE((SELECT COUNT(*)
                                           FROM jsonb_array_elements(match_data) AS elem
                                          WHERE (elem->>'expectedGoals')::NUMERIC > 0.5), 0)
    );
END;
$$ LANGUAGE plpgsql;

-- 验证函数是否正常工作
SELECT extract_shot_features('[{"expectedGoals": 0.85}, {"expectedGoals": 0.12}, {"expectedGoals": 0.45}]'::jsonb);