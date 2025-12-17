# BioLeads Settings Configuration
"""
Central configuration for API keys, rate limits, scoring weights, and paths.
Uses environment variables for sensitive data.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, Optional
from pathlib import Path


@dataclass
class APIConfig:
    """API configuration settings."""
    # PubMed E-utilities (free - register for API key for higher rate limits)
    # Register at: https://www.ncbi.nlm.nih.gov/account/
    pubmed_api_key: str = field(default_factory=lambda: os.getenv('PUBMED_API_KEY', ''))
    pubmed_base_url: str = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'
    pubmed_rate_limit: float = 0.34  # 3 requests/sec without API key, 10/sec with key
    
    # NIH RePORTER API (free, public API)
    nih_reporter_base_url: str = 'https://api.reporter.nih.gov/v2/'
    nih_reporter_rate_limit: float = 1.0  # 1 request per second (conservative)
    
    # OpenAlex API (free, open-source alternative to paid services)
    # No API key required, but email gives you faster access
    openalex_base_url: str = 'https://api.openalex.org/'
    openalex_email: str = field(default_factory=lambda: os.getenv('OPENALEX_EMAIL', ''))
    openalex_rate_limit: float = 0.1  # 10 requests/sec for polite pool
    
    # Crossref API (free, for publication metadata)
    crossref_base_url: str = 'https://api.crossref.org/'
    crossref_email: str = field(default_factory=lambda: os.getenv('CROSSREF_EMAIL', ''))
    crossref_rate_limit: float = 0.02  # 50 requests/sec with polite pool
    
    # ORCID Public API (free)
    orcid_base_url: str = 'https://pub.orcid.org/v3.0/'
    orcid_rate_limit: float = 0.04  # 24 requests/sec
    
    # ClinicalTrials.gov API (free)
    clinicaltrials_base_url: str = 'https://clinicaltrials.gov/api/v2/'
    clinicaltrials_rate_limit: float = 0.5


@dataclass
class StorageConfig:
    """File storage configuration."""
    base_path: Path = field(default_factory=lambda: Path(__file__).parent.parent / 'data')
    
    @property
    def raw_path(self) -> Path:
        """Path for raw scraped data."""
        path = self.base_path / 'raw'
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @property
    def processed_path(self) -> Path:
        """Path for enriched/processed data."""
        path = self.base_path / 'processed'
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @property
    def output_path(self) -> Path:
        """Path for final output files."""
        path = self.base_path / 'output'
        path.mkdir(parents=True, exist_ok=True)
        return path


@dataclass
class ScoringConfig:
    """Lead scoring weight configuration."""
    # Research Activity Weights (0-1)
    publication_weight: float = 0.20
    grant_weight: float = 0.25
    clinical_trial_weight: float = 0.15
    
    # Engagement Weights (0-1)
    conference_weight: float = 0.10
    recent_activity_weight: float = 0.15
    
    # Fit Weights (0-1)
    role_fit_weight: float = 0.10
    institution_fit_weight: float = 0.05
    
    # Thresholds
    hot_lead_threshold: float = 75.0
    warm_lead_threshold: float = 50.0
    
    def validate(self) -> bool:
        """Ensure weights sum to 1.0."""
        total = (
            self.publication_weight + 
            self.grant_weight + 
            self.clinical_trial_weight +
            self.conference_weight + 
            self.recent_activity_weight +
            self.role_fit_weight + 
            self.institution_fit_weight
        )
        return abs(total - 1.0) < 0.01


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = 'INFO'
    format: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    log_file: Optional[str] = None


@dataclass
class Settings:
    """Main settings container."""
    api: APIConfig = field(default_factory=APIConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    scoring: ScoringConfig = field(default_factory=ScoringConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    # Global settings
    max_workers: int = 4  # For parallel processing
    request_timeout: int = 30  # HTTP request timeout in seconds
    max_retries: int = 3  # Max retry attempts for failed requests
    
    @classmethod
    def from_env(cls) -> 'Settings':
        """Create settings instance with environment variable overrides."""
        settings = cls()
        
        # Override with environment variables if present
        if api_key := os.getenv('PUBMED_API_KEY'):
            settings.api.pubmed_api_key = api_key
            settings.api.pubmed_rate_limit = 0.1  # Faster with API key
        
        return settings


# Global settings instance
settings = Settings.from_env()
