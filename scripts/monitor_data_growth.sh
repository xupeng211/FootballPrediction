#!/bin/bash
while true; do
    echo "--- $(date) ---"
    docker-compose exec db psql -U postgres -d football_prediction -c "
        SELECT 
            COUNT(*) as total_matches,
            COUNT(DISTINCT home_team_id) as total_teams,
            COUNT(DISTINCT league_id) as total_leagues,
            MAX(match_date) as latest_match_date
        FROM matches;
    "
    sleep 15
done

