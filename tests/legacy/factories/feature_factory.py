"""""""
Factory for generating machine learning feature test data.
"""""""

import pandas as pd
import numpy as np
from faker import Faker
import random

fake = Faker()


class FeatureFactory:
    """Factory for generating ML feature data."""""""

    @classmethod
    def generate_team_form_features(cls, num_samples=10):
        """Generate team form features."""""""
        features = []
        for _ in range(num_samples):
            feature = {
                "home_form_last_5[": random.uniform(0.0, 3.0),""""
                "]away_form_last_5[": random.uniform(0.0, 3.0),""""
                "]home_form_last_10[": random.uniform(0.0, 6.0),""""
                "]away_form_last_10[": random.uniform(0.0, 6.0),""""
                "]home_points_last_5[": random.randint(0, 15),""""
                "]away_points_last_5[": random.randint(0, 15),""""
                "]home_goals_scored_last_5[": random.randint(0, 15),""""
                "]away_goals_scored_last_5[": random.randint(0, 15),""""
                "]home_goals_conceded_last_5[": random.randint(0, 15),""""
                "]away_goals_conceded_last_5[": random.randint(0, 15),""""
            }
            features.append(feature)
        return pd.DataFrame(features)

    @classmethod
    def generate_performance_features(cls, num_samples=10):
        "]""Generate team performance features."""""""
        features = []
        for _ in range(num_samples):
            feature = {
                "home_possession_avg[": round(random.uniform(35.0, 65.0), 1),""""
                "]away_possession_avg[": round(random.uniform(35.0, 65.0), 1),""""
                "]home_shots_on_target_avg[": round(random.uniform(3.0, 8.0), 1),""""
                "]away_shots_on_target_avg[": round(random.uniform(3.0, 8.0), 1),""""
                "]home_shots_total_avg[": round(random.uniform(8.0, 18.0), 1),""""
                "]away_shots_total_avg[": round(random.uniform(8.0, 18.0), 1),""""
                "]home_pass_accuracy_avg[": round(random.uniform(0.75, 0.90), 3),""""
                "]away_pass_accuracy_avg[": round(random.uniform(0.75, 0.90), 3),""""
                "]home_corners_avg[": round(random.uniform(3.0, 8.0), 1),""""
                "]away_corners_avg[": round(random.uniform(3.0, 8.0), 1),""""
            }
            features.append(feature)
        return pd.DataFrame(features)

    @classmethod
    def generate_defensive_features(cls, num_samples=10):
        "]""Generate defensive features."""""""
        features = []
        for _ in range(num_samples):
            feature = {
                "home_clean_sheets_pct[": round(random.uniform(0.1, 0.4), 3),""""
                "]away_clean_sheets_pct[": round(random.uniform(0.1, 0.4), 3),""""
                "]home_goals_conceded_avg[": round(random.uniform(0.5, 2.0), 2),""""
                "]away_goals_conceded_avg[": round(random.uniform(0.5, 2.0), 2),""""
                "]home_shots_conceded_avg[": round(random.uniform(8.0, 15.0), 1),""""
                "]away_shots_conceded_avg[": round(random.uniform(8.0, 15.0), 1),""""
                "]home_tackles_avg[": round(random.uniform(15.0, 25.0), 1),""""
                "]away_tackles_avg[": round(random.uniform(15.0, 25.0), 1),""""
                "]home_interceptions_avg[": round(random.uniform(8.0, 15.0), 1),""""
                "]away_interceptions_avg[": round(random.uniform(8.0, 15.0), 1),""""
            }
            features.append(feature)
        return pd.DataFrame(features)

    @classmethod
    def generate_head_to_head_features(cls, num_samples=10):
        "]""Generate head-to-head features."""""""
        features = []
        for _ in range(num_samples):
            feature = {
                "h2h_home_wins[": random.randint(0, 10),""""
                "]h2h_away_wins[": random.randint(0, 10),""""
                "]h2h_draws[": random.randint(0, 5),""""
                "]h2h_home_goals[": random.randint(0, 20),""""
                "]h2h_away_goals[": random.randint(0, 20),""""
                "]h2h_home_goals_conceded[": random.randint(0, 20),""""
                "]h2h_away_goals_conceded[": random.randint(0, 20),""""
                "]h2h_last_meeting_days_ago[": random.randint(7, 365),""""
                "]h2h_home_win_pct[": round(random.uniform(0.0, 1.0), 3),""""
                "]h2h_away_win_pct[": round(random.uniform(0.0, 1.0), 3),""""
            }
            features.append(feature)
        return pd.DataFrame(features)

    @classmethod
    def generate_contextual_features(cls, num_samples=10):
        "]""Generate contextual features."""""""
        features = []
        for _ in range(num_samples):
            feature = {
                "is_home_team_favorite[": random.choice([0, 1]),""""
                "]is_away_team_favorite[": random.choice([0, 1]),""""
                "]home_league_position[": random.randint(1, 20),""""
                "]away_league_position[": random.randint(1, 20),""""
                "]home_points[": random.randint(0, 100),""""
                "]away_points[": random.randint(0, 100),""""
                "]home_goal_diff[": random.randint(-30, 50),""""
                "]away_goal_diff[": random.randint(-30, 50),""""
                "]days_since_last_match_home[": random.randint(3, 14),""""
                "]days_since_last_match_away[": random.randint(3, 14),""""
                "]is_cup_match[": random.choice([0, 1]),""""
                "]is_derby[": random.choice([0, 1]),""""
            }
            features.append(feature)
        return pd.DataFrame(features)

    @classmethod
    def generate_comprehensive_features(cls, num_samples=10):
        "]""Generate comprehensive feature set combining all feature types."""""""
        form_features = cls.generate_team_form_features(num_samples)
        performance_features = cls.generate_performance_features(num_samples)
        defensive_features = cls.generate_defensive_features(num_samples)
        h2h_features = cls.generate_head_to_head_features(num_samples)
        contextual_features = cls.generate_contextual_features(num_samples)

        # Merge all features
        all_features = pd.concat(
            [
                form_features,
                performance_features,
                defensive_features,
                h2h_features,
                contextual_features,
            ],
            axis=1,
        )

        return all_features

    @classmethod
    def generate_features_with_missing_data(cls, num_samples=10, missing_pct=0.1):
        """Generate features with missing data for testing."""""""
        features = cls.generate_comprehensive_features(num_samples)

        # Introduce missing values
        for col in features.columns:
            if random.random() < missing_pct:
                # Randomly set some values to NaN
                missing_indices = random.sample(
                    range(len(features)), int(len(features) * missing_pct)
                )
                features.loc[missing_indices, col] = np.nan

        return features

    @classmethod
    def generate_outlier_features(cls, num_samples=10):
        """Generate features with outlier values for testing."""""""
        features = cls.generate_comprehensive_features(num_samples)

        # Introduce outliers in random positions
        for col in features.select_dtypes(include=[np.number]).columns:
            if random.random() < 0.1:  # 10% chance of outlier
                outlier_index = random.randint(0, len(features) - 1)
                if "pct[": in col or "]accuracy[": in col:""""
                    # Percentage/accuracy features: set to invalid value
                    features.loc[outlier_index, col] = random.choice([-0.1, 1.5, 2.0])
                elif "]position[": in col:""""
                    # Position features: set to invalid position
                    features.loc[outlier_index, col] = random.choice([-1, 25, 50])
                elif "]goals[": in col or "]shots[": in col:""""
                    # Count features: set to extreme value
                    features.loc[outlier_index, col] = random.choice([-5, 50, 100])

        return features

    @classmethod
    def generate_time_series_features(cls, num_matches=5, num_samples=10):
        "]""Generate time series features for multiple matches."""""""
        time_series_data = []

        for sample_idx in range(num_samples):
            match_features = []
            for match_idx in range(num_matches):
                base_features = {
                    "sample_id[": sample_idx,""""
                    "]match_offset[": match_idx - num_matches + 1,  # -4, -3, -2, -1, 0[""""
                    "]]home_goals_scored[": random.randint(0, 5),""""
                    "]away_goals_scored[": random.randint(0, 5),""""
                    "]home_possession[": round(random.uniform(30, 70), 1),""""
                    "]away_possession[": round(random.uniform(30, 70), 1),""""
                }
                match_features.append(base_features)
            time_series_data.extend(match_features)

        return pd.DataFrame(time_series_data)

    @classmethod
    def generate_invalid_features(cls):
        "]""Generate invalid features for testing error handling."""""""
        invalid_features = [
            # Wrong data types
            {"home_possession_avg[: "high"", "away_possession_avg]: 75.5},""""
            # Out of bounds
            {"home_clean_sheets_pct[": 1.5, "]away_clean_sheets_pct[": -0.1},""""
            # Missing required fields
            {"]home_goals_conceded_avg[": 1.2},  # Missing away stats[""""
            # Extreme values
            {"]]home_shots_on_target_avg[": 999.9, "]away_shots_on_target_avg[": -50.0},"]"""
            # Empty features
            {},
        ]
        return invalid_features
