from app.services.scraper.html_scraper import HtmlScraper
from app.services.scraper.js_scraper import JsRenderedScraper
from app.services.scraper.multi_scraper import MultiScraper
from app.services.scraper.smart_extractor import SmartDataExtractor
from app.services.scraper.export_service import ExportService
from app.services.scraper.data_transformer import DataTransformer
from app.services.scraper.deduplicator import CrossPageDeduplicator
from app.services.scraper.templates import TemplateManager
from app.services.scraper.shared import USER_AGENTS, get_user_id, make_json_safe
try:
    from app.services.scraper.playwright_scraper import PlaywrightScraper
except ImportError:
    PlaywrightScraper = None
try:
    from app.services.scraper.scheduler import ScrapeScheduler
except (ImportError, TypeError):
    ScrapeScheduler = None
from app.services.scraper.auth_scraper import AuthenticatedScraper, AuthConfig
from app.services.scraper.captcha_solver import CaptchaSolver
from app.services.scraper.rate_limiter import RateLimiter
from app.services.scraper.fingerprint import FingerprintGenerator
from app.services.scraper.webhook_notifier import WebhookNotifier
from app.services.scraper.scrape_diff import ScrapeDiff
from app.services.scraper.distributed_scraper import DistributedScraper
from app.services.scraper.data_validator import DataValidator
from app.services.scraper.automl import AutoMLRecommender
from app.services.scraper.anomaly_detector import AnomalyDetector
from app.services.scraper.forecaster import Forecaster
from app.services.scraper.clusterer import AutoClusterer
from app.services.scraper.dim_reducer import DimReducer
from app.services.scraper.feature_engineer import FeatureEngineer
from app.services.scraper.data_enricher import DataEnricher
from app.services.scraper.target_scrapers import (
    EcommerceScraper, NewsScraper, FinancialScraper,
    AcademicScraper, JobScraper, RealEstateScraper,
)

__all__ = [
    "HtmlScraper",
    "JsRenderedScraper",
    "MultiScraper",
    "SmartDataExtractor",
    "ExportService",
    "DataTransformer",
    "CrossPageDeduplicator",
    "TemplateManager",
    "PlaywrightScraper",
    "ScrapeScheduler",
    "AuthenticatedScraper",
    "AuthConfig",
    "CaptchaSolver",
    "RateLimiter",
    "FingerprintGenerator",
    "WebhookNotifier",
    "ScrapeDiff",
    "DistributedScraper",
    "DataValidator",
    "AutoMLRecommender",
    "AnomalyDetector",
    "Forecaster",
    "AutoClusterer",
    "DimReducer",
    "FeatureEngineer",
    "DataEnricher",
    "EcommerceScraper",
    "NewsScraper",
    "FinancialScraper",
    "AcademicScraper",
    "JobScraper",
    "RealEstateScraper",
    "USER_AGENTS",
    "get_user_id",
    "make_json_safe",
]
