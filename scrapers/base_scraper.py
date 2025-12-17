# BioLeads Base Scraper
"""
Abstract base class for all scrapers with common functionality.
"""

import json
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Dict, List, Optional, Generator

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def rate_limit(min_interval: float):
    """Decorator to enforce rate limiting between API calls."""
    last_call = [0.0]
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_call[0]
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
            result = func(*args, **kwargs)
            last_call[0] = time.time()
            return result
        return wrapper
    return decorator


class BaseScraper(ABC):
    """
    Abstract base class for all data scrapers.
    
    Provides common functionality for:
    - HTTP requests with retry logic
    - Rate limiting
    - Data persistence
    - Logging
    """
    
    def __init__(
        self,
        name: str,
        base_url: str,
        rate_limit_seconds: float = 1.0,
        timeout: int = 30,
        max_retries: int = 3,
        storage_path: Optional[Path] = None,
    ):
        """
        Initialize the scraper.
        
        Args:
            name: Identifier for this scraper
            base_url: Base URL for API requests
            rate_limit_seconds: Minimum seconds between requests
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts for failed requests
            storage_path: Path to save raw data (uses default if not provided)
        """
        self.name = name
        self.base_url = base_url.rstrip('/')
        self.rate_limit_seconds = rate_limit_seconds
        self.timeout = timeout
        self.max_retries = max_retries
        self.logger = logging.getLogger(f"bioleads.scrapers.{name}")
        
        # Set up storage path
        if storage_path is None:
            from ..config.settings import settings
            storage_path = settings.storage.raw_path
        self.storage_path = storage_path / name
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Track last request time for rate limiting
        self._last_request_time = 0.0
        
        # Set up session with retry logic
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Create a requests session with retry configuration."""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set default headers
        session.headers.update({
            'User-Agent': 'BioLeads/1.0 (Research Lead Generation; Contact: your-email@example.com)',
            'Accept': 'application/json',
        })
        
        return session
    
    def _rate_limit_wait(self):
        """Wait if needed to respect rate limits."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit_seconds:
            sleep_time = self.rate_limit_seconds - elapsed
            self.logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)
    
    def fetch(
        self,
        endpoint: str = '',
        method: str = 'GET',
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
    ) -> Optional[Dict]:
        """
        Make an HTTP request with rate limiting and error handling.
        
        Args:
            endpoint: API endpoint (appended to base_url)
            method: HTTP method (GET, POST)
            params: Query parameters
            data: Form data for POST
            json_data: JSON body for POST
            headers: Additional headers
            
        Returns:
            JSON response as dict, or None if request failed
        """
        self._rate_limit_wait()
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}" if endpoint else self.base_url
        
        try:
            self.logger.info(f"Fetching: {url}")
            
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                data=data,
                json=json_data,
                headers=headers,
                timeout=self.timeout,
            )
            
            self._last_request_time = time.time()
            
            response.raise_for_status()
            
            # Try to parse JSON, return raw text if not JSON
            try:
                return response.json()
            except json.JSONDecodeError:
                return {'raw_content': response.text}
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed for {url}: {e}")
            return None
    
    def fetch_all(
        self,
        endpoint: str,
        params: Dict,
        page_param: str = 'offset',
        page_size: int = 100,
        total_key: str = 'total',
        results_key: str = 'results',
        max_results: Optional[int] = None,
    ) -> Generator[Dict, None, None]:
        """
        Fetch all pages of results from a paginated API.
        
        Args:
            endpoint: API endpoint
            params: Base query parameters
            page_param: Parameter name for pagination offset
            page_size: Number of results per page
            total_key: Key in response containing total count
            results_key: Key in response containing results array
            max_results: Maximum total results to fetch (None for all)
            
        Yields:
            Individual result items
        """
        offset = 0
        total_fetched = 0
        
        while True:
            page_params = {**params, page_param: offset, 'limit': page_size}
            response = self.fetch(endpoint, params=page_params)
            
            if not response:
                break
            
            results = response.get(results_key, [])
            if not results:
                break
            
            for item in results:
                yield item
                total_fetched += 1
                
                if max_results and total_fetched >= max_results:
                    return
            
            total = response.get(total_key, 0)
            offset += page_size
            
            if offset >= total:
                break
    
    def save_raw(self, data: Any, filename: str, timestamp: bool = True) -> Path:
        """
        Save raw data to storage.
        
        Args:
            data: Data to save (will be JSON serialized)
            filename: Base filename (without extension)
            timestamp: Whether to append timestamp to filename
            
        Returns:
            Path to saved file
        """
        if timestamp:
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{filename}_{ts}"
        
        filepath = self.storage_path / f"{filename}.json"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        
        self.logger.info(f"Saved raw data to {filepath}")
        return filepath
    
    @abstractmethod
    def search(self, query: str, max_results: int = 100) -> List[Dict]:
        """
        Search for leads matching the query.
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            
        Returns:
            List of lead records
        """
        pass
    
    @abstractmethod
    def parse_lead(self, raw_data: Dict) -> Dict:
        """
        Parse raw API response into standardized lead format.
        
        Args:
            raw_data: Raw data from API
            
        Returns:
            Standardized lead record with fields:
            - source: str
            - source_id: str
            - name: str
            - email: Optional[str]
            - title: Optional[str]
            - institution: str
            - department: Optional[str]
            - location: Optional[str]
            - research_focus: List[str]
            - publications: int
            - grants: List[Dict]
            - raw_data: Dict
        """
        pass
    
    def run(
        self,
        queries: List[str],
        max_results_per_query: int = 100,
        save_raw: bool = True,
    ) -> List[Dict]:
        """
        Run the scraper for multiple queries.
        
        Args:
            queries: List of search queries
            max_results_per_query: Maximum results per query
            save_raw: Whether to save raw data
            
        Returns:
            List of all parsed lead records
        """
        all_leads = []
        
        for i, query in enumerate(queries):
            self.logger.info(f"Processing query {i+1}/{len(queries)}: {query[:50]}...")
            
            try:
                results = self.search(query, max_results=max_results_per_query)
                
                if save_raw and results:
                    self.save_raw(results, f"search_{i+1}")
                
                leads = [self.parse_lead(r) for r in results if r]
                all_leads.extend([l for l in leads if l])
                
                self.logger.info(f"Found {len(leads)} leads from query")
                
            except Exception as e:
                self.logger.error(f"Error processing query '{query}': {e}")
        
        self.logger.info(f"Total leads found: {len(all_leads)}")
        return all_leads
