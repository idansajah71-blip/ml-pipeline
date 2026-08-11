from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ScrapeRequest(BaseModel):
    url: str = Field(..., min_length=5, max_length=1000, description="URL to scrape")
    extract_tables: bool = Field(default=True)
    extract_lists: bool = Field(default=True)

    model_config = {"extra": "ignore"}


class UniversalScrapeRequest(BaseModel):
    url: str = Field(..., min_length=5, max_length=2000, description="URL to scrape universal")
    extract_tables: bool = Field(default=True)
    extract_lists: bool = Field(default=True)
    use_js: bool = Field(default=False, description="Force JS rendering")
    use_selenium: bool = Field(default=False, description="Use Selenium for JS rendering")
    wait_seconds: int = Field(default=3, ge=1, le=30, description="Wait time for JS rendering")

    model_config = {"extra": "ignore"}


class UniversalScrapeResponse(BaseModel):
    url: str
    title: str
    html: Optional[str] = None
    tables: list = []
    text_blocks: list = []
    metadata: dict = {}
    row_count: int = 0
    column_count: int = 0
    content_hash: str = ""
    links: list = []
    images: list = []
    json_ld: list = []
    feeds: list = []
    api_endpoints: list = []
    open_graph: dict = {}
    keywords: list = []
    language: str = ""
    word_count: int = 0
    reading_time_minutes: float = 0.0
    scrape_strategy: str = ""
    scrape_duration_ms: int = 0
    status_code: int = 0


class ScrapeAndProcessRequest(BaseModel):
    url: str = Field(..., min_length=5, max_length=1000)
    auto_rename: bool = Field(default=True)
    deduplicate: bool = Field(default=True)
    detect_types: bool = Field(default=True)
    cluster_text: bool = Field(default=False)
    export_as_dataset: bool = Field(default=False)
    dataset_name: Optional[str] = None
    run_advanced_analysis: bool = Field(default=True)
    run_sentiment: bool = Field(default=True)
    run_patterns: bool = Field(default=True)
    use_selenium: bool = Field(default=False)

    model_config = {"extra": "ignore"}


class BatchScrapeRequest(BaseModel):
    urls: List[str] = Field(..., min_length=1, max_length=20, description="List of URLs to scrape")
    extract_tables: bool = Field(default=True)
    extract_lists: bool = Field(default=True)
    run_advanced_analysis: bool = Field(default=True)
    run_sentiment: bool = Field(default=True)
    run_patterns: bool = Field(default=True)
    max_concurrent: int = Field(default=5, ge=1, le=10)
    max_retries: int = Field(default=3, ge=0, le=5)
    use_selenium: bool = Field(default=False)

    model_config = {"extra": "ignore"}


class RecursiveScrapeRequest(BaseModel):
    url: str = Field(..., min_length=5, max_length=1000)
    max_depth: int = Field(default=2, ge=1, le=5)
    max_pages: int = Field(default=10, ge=1, le=50)
    run_advanced_analysis: bool = Field(default=True)
    use_selenium: bool = Field(default=False)

    model_config = {"extra": "ignore"}


class SitemapScrapeRequest(BaseModel):
    sitemap_url: str = Field(..., min_length=5, max_length=1000)
    limit: int = Field(default=50, ge=1, le=200)
    run_advanced_analysis: bool = Field(default=True)

    model_config = {"extra": "ignore"}


class DiscoverScrapeRequest(BaseModel):
    url: str = Field(..., min_length=5, max_length=1000)
    max_pages: int = Field(default=20, ge=1, le=50)
    run_advanced_analysis: bool = Field(default=True)

    model_config = {"extra": "ignore"}


class ScrapeJobResponse(BaseModel):
    id: str
    url: str
    title: Optional[str] = None
    status: str
    scrape_type: str = "single"
    raw_row_count: int = 0
    clean_row_count: int = 0
    column_count: int = 0
    duplicates_removed: int = 0
    tables_data: list = []
    columns_typed: dict = {}
    columns_renamed: dict = {}
    quality_score: float = 0.0
    quality_issues: list = []
    clusters: dict = {}
    ml_processing_applied: list = []
    advanced_analysis: Optional[dict] = None
    sentiment_analysis: Optional[dict] = None
    pattern_analysis: Optional[dict] = None
    scrape_metadata: Optional[dict] = None
    batch_results: Optional[list] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    scraped_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None


class ScrapePreviewResponse(BaseModel):
    title: str
    tables: list[dict] = []
    lists: list[list[str]] = []
    metadata: dict = {}
    row_count: int = 0
    column_count: int = 0
    content_hash: str = ""
    links: list[str] = []
    images: list[dict] = []
    json_ld: list[dict] = []
    feeds: list[str] = []
    api_endpoints: list[dict] = []
    open_graph: dict = {}
    keywords: list[str] = []
    language: str = ""
    word_count: int = 0
    reading_time_minutes: float = 0.0
    scrape_duration_ms: int = 0


class ImportScrapeRequest(BaseModel):
    job_id: str
    dataset_name: Optional[str] = None
    description: Optional[str] = None
    target_column: Optional[str] = None
    tags: Optional[List[str]] = None

    model_config = {"extra": "ignore"}


class ImportScrapeResponse(BaseModel):
    dataset_id: str
    name: str
    row_count: int
    column_count: int
    message: str = "Dataset berhasil dibuat dari data scraping"
