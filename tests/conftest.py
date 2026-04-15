"""
Pytest configuration and fixtures
"""

import pytest
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def sample_article_data():
    """Sample article data for testing"""
    from src.scrapers.base import ArticleData
    
    return ArticleData(
        title="OpenAI releases GPT-5 with improved reasoning",
        url="https://openai.com/blog/gpt-5",
        summary="OpenAI announced GPT-5 today with significant improvements in reasoning and safety.",
        published_at=None,
        tags=["AI", "GPT-5", "OpenAI"]
    )


@pytest.fixture
def sample_config():
    """Sample configuration for testing"""
    from src.core.config import Settings, AppConfig, DatabaseConfig, RedisConfig, TelegramConfig
    
    return Settings(
        app=AppConfig(name="test", version="1.0.0"),
        database=DatabaseConfig(host="localhost", port=5432, name="test_db"),
        redis=RedisConfig(host="localhost", port=6379),
        telegram=TelegramConfig(bot_token="test_token"),
    )
