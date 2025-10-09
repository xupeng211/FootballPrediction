from src.data.processing.football_data_cleaner_mod import FootballDataCleaner


def test_data_cleaner():
    cleaner = FootballDataCleaner()
    assert cleaner is not None


def test_cleaning_methods():
    cleaner = FootballDataCleaner()
    assert hasattr(cleaner, "clean_data")
    assert hasattr(cleaner, "remove_duplicates")
