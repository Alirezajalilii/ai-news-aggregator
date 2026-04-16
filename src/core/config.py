"""
AI News Aggregator - Core Configuration Module
Production-ready configuration management using YAML and Pydantic

Supports environment variable overrides for Docker/12-factor deployments.
Priority: Environment variables > config.yaml > defaults
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

    @classmethod
    def from_env(cls, base: "DatabaseConfig") -> "DatabaseConfig":
        """Override fields from environment variables (DB_HOST, DB_PORT, etc.)"""
        return cls(
            host=os.getenv("DB_HOST", base.host),
            port=int(os.getenv("DB_PORT", str(base.port))),
            name=os.getenv("DB_NAME", base.name),
            username=os.getenv("DB_USERNAME", base.username),
            password=os.getenv("DB_PASSWORD", base.password),
            pool_size=base.pool_size,
            max_overflow=base.max_overflow,
            echo=base.echo,
        )


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

    @classmethod
    def from_env(cls, base: "RedisConfig") -> "RedisConfig":
        """Override fields from environment variables (REDIS_HOST, REDIS_PORT, etc.)"""
        redis_password = os.getenv("REDIS_PASSWORD")
        return cls(
            host=os.getenv("REDIS_HOST", base.host),
            port=int(os.getenv("REDIS_PORT", str(base.port))),
            db=base.db,
            password=redis_password if redis_password else base.password,
            socket_timeout=base.socket_timeout,
            max_connections=base.max_connections,
        )


class TelegramConfig(BaseModel):
    bot_token: str
    allowed_users: List[int] = []
    admin_users: List[int] = []
    channels: List[str] = []
    parse_mode: str = "HTML"
    message_template: str = "html"

    @classmethod
    def from_env(cls, base: "TelegramConfig") -> "TelegramConfig":
        """Override bot_token from TELEGRAM_BOT_TOKEN env var"""
        env_token = os.getenv("TELEGRAM_BOT_TOKEN")
        return cls(
            bot_token=env_token if env_token else base.bot_token,
            allowed_users=base.allowed_users,
            admin_users=base.admin_users,
            channels=base.channels,
            parse_mode=base.parse_mode,
            message_template=base.message_template,
        )


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
    ollama_base_url: str = "http://localhost:11434"
    max_summary_length: int = 900
    min_summary_length: int = 400
    prompt_template: str = "این خبر رو به صورت خلاصه و جذاب برای کانال تلگرام فارسی بنویس. طول خلاصه: بین {min_len} تا {max_len} کاراکتر. - خلاصه باید تمام اطلاعات مهم رو حفظ کنه - در انتها یک دعوت به اقدام بذار: \"🔗 ادامه خبر در لینک\" - بدون تیتر، فقط متن خلاصه. خبر: {content}"

    @classmethod
    def from_env(cls, base: "SummarizationConfig") -> "SummarizationConfig":
        """Override ollama_base_url from OLLAMA_BASE_URL env var"""
        return cls(
            enabled=base.enabled,
            model=base.model,
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", base.ollama_base_url),
            max_summary_length=base.max_summary_length,
            min_summary_length=base.min_summary_length,
            prompt_template=base.prompt_template,
        )


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

    @classmethod
    def from_env(cls, base: "LoggingConfig") -> "LoggingConfig":
        """Override level from LOG_LEVEL env var"""
        return cls(
            level=os.getenv("LOG_LEVEL", base.level),
            format=base.format,
            file=base.file,
            max_bytes=base.max_bytes,
            backup_count=base.backup_count,
            sentry_dsn=base.sentry_dsn,
        )


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
    Load configuration from YAML file with environment variable overrides.
    
    Priority: Environment variables > config.yaml > defaults
    
    Supported env vars:
        DB_HOST, DB_PORT, DB_NAME, DB_USERNAME, DB_PASSWORD
        REDIS_HOST, REDIS_PORT, REDIS_PASSWORD
        TELEGRAM_BOT_TOKEN
        OLLAMA_BASE_URL
        LOG_LEVEL
        APP_ENV
    
    Args:
        config_path: Path to config file. Defaults to CONFIG_PATH env var or config.yaml.
        
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
    
    settings = Settings(**config_data)
    
    # Apply environment variable overrides (for Docker / 12-factor)
    settings.database = DatabaseConfig.from_env(settings.database)
    settings.redis = RedisConfig.from_env(settings.redis)
    settings.telegram = TelegramConfig.from_env(settings.telegram)
    settings.news.summarization = SummarizationConfig.from_env(settings.news.summarization)
    settings.logging = LoggingConfig.from_env(settings.logging)
    
    # Override app environment if set
    app_env = os.getenv("APP_ENV")
    if app_env:
        settings.app.environment = app_env
    
    return settings


def get_config() -> Settings:
    """Get singleton configuration instance"""
    global _config_instance
    
    if _config_instance is None:
        _config_instance = load_config()
    
    return _config_instance


# Global configuration instance
_config_instance: Optional[Settings] = None
