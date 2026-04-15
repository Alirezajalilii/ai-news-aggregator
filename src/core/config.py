"""
AI News Aggregator - Core Configuration Module
Production-ready configuration management using YAML and Pydantic
"""

import os
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
import yaml


# ============== Configuration Models ==============

class AppConfig(BaseModel):
    name: str = "AI News Aggregator"
    version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000


class DatabaseConfig(BaseModel):
    host: str = "localhost"
    port: int = 5432
    name: str = "ai_news"
    username: str = "postgres"
    password: str = "postgres"
    pool_size: int = 10
    max_overflow: int = 20
    echo: bool = False

    @property
    def url(self) -> str:
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.name}"


class RedisConfig(BaseModel):
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    socket_timeout: int = 5
    max_connections: int = 50

    @property
    def url(self) -> str:
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"


class TelegramConfig(BaseModel):
    bot_token: str
    allowed_users: List[int] = []
    admin_users: List[int] = []
    channels: List[str] = []
    parse_mode: str = "HTML"
    message_template: str = "html"


class ScraperSource(BaseModel):
    name: str
    url: str
    enabled: bool = True
    priority: int = 1
    category: str = "general"
    custom_headers: Optional[dict] = None
    fetch_strategy: str = "httpx"  # httpx, curl, ollama, brave


class ScraperConfig(BaseModel):
    user_agent: str = "AI-News-Aggregator/1.0"
    request_timeout: int = 30
    max_retries: int = 3
    retry_delay: int = 5
    batch_size: int = 5
    concurrency: int = 3
    default_fetch_strategy: str = "httpx"
    sources: List[ScraperSource] = []


class CategoryConfig(BaseModel):
    id: str
    name: str
    emoji: str = "📰"


class DeduplicationConfig(BaseModel):
    enabled: bool = True
    similarity_threshold: float = 0.75
    title_similarity_weight: float = 0.4
    entity_similarity_weight: float = 0.4
    content_similarity_weight: float = 0.2
    max_age_hours: int = 48
    store_hash: bool = True


class SummarizationConfig(BaseModel):
    enabled: bool = True
    model: str = "minimax-m2.7:cloud"
    max_summary_length: int = 900
    min_summary_length: int = 400
    prompt_template: str = "این خبر رو به صورت خلاصه و جذاب برای کانال تلگرام فارسی بنویس. طول خلاصه: بین {min_len} تا {max_len} کاراکتر. - خلاصه باید تمام اطلاعات مهم رو حفظ کنه - در انتها یک دعوت به اقدام بذار: \"🔗 ادامه خبر در لینک\" - بدون تیتر، فقط متن خلاصه. خبر: {content}"


class NewsConfig(BaseModel):
    summarization: SummarizationConfig = Field(default_factory=SummarizationConfig)
    deduplication: DeduplicationConfig = Field(default_factory=DeduplicationConfig)
    categories: List[CategoryConfig] = []


class SchedulerJob(BaseModel):
    name: str
    schedule: str
    description: str = ""
    enabled: bool = True


class SchedulerConfig(BaseModel):
    enabled: bool = True
    timezone: str = "Asia/Tehran"
    jobs: List[SchedulerJob] = []


class TelegramBotCommand(BaseModel):
    command: str
    description: str = ""


class TelegramBotFilters(BaseModel):
    min_summary_length: int = 400
    max_summary_length: int = 900


class TelegramBotFormatting(BaseModel):
    max_articles_per_message: int = 10
    include_source: bool = True
    include_timestamp: bool = True
    include_categories: bool = True
    link_preview: bool = False


class TelegramBotConfig(BaseModel):
    commands: List[TelegramBotCommand] = []
    filters: TelegramBotFilters = Field(default_factory=TelegramBotFilters)
    formatting: TelegramBotFormatting = Field(default_factory=TelegramBotFormatting)


class LoggingConfig(BaseModel):
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: str = "logs/app.log"
    max_bytes: int = 10 * 1024 * 1024
    backup_count: int = 5
    sentry_dsn: Optional[str] = None


class MonitoringConfig(BaseModel):
    enabled: bool = True
    health_check_interval: int = 60
    metrics_port: int = 9090
    prometheus_enabled: bool = False


# ============== Main Configuration ==============

class Settings(BaseModel):
    app: AppConfig = Field(default_factory=AppConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    telegram: TelegramConfig
    scraper: ScraperConfig = Field(default_factory=ScraperConfig)
    news: NewsConfig = Field(default_factory=NewsConfig)
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    telegram_bot: TelegramBotConfig = Field(default_factory=TelegramBotConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)


# ============== Configuration Loader ==============

def load_config(config_path: Optional[str] = None) -> Settings:
    """
    Load configuration from YAML file
    
    Args:
        config_path: Path to config file. Defaults to config.yaml in project root.
        
    Returns:
        Settings object with all configuration
    """
    if config_path is None:
        config_path = os.getenv("CONFIG_PATH", "config.yaml")
    
    config_file = Path(config_path)
    
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_file, "r", encoding="utf-8") as f:
        config_data = yaml.safe_load(f)
    
    return Settings(**config_data)


def get_config() -> Settings:
    """Get singleton configuration instance"""
    global _config_instance
    
    if _config_instance is None:
        _config_instance = load_config()
    
    return _config_instance


# Global configuration instance
_config_instance: Optional[Settings] = None
