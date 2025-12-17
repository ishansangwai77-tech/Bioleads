# BioLeads Pipeline Orchestrator
"""
Main pipeline coordinator for running the complete lead generation workflow.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd


class PipelineOrchestrator:
    """
    Orchestrates the complete lead generation pipeline.
    
    Stages:
    1. Scraping - Collect leads from multiple sources
    2. Deduplication - Merge duplicate records
    3. Enrichment - Add email, location, company data
    4. Scoring - Calculate propensity scores
    5. Export - Save results
    """
    
    def __init__(self, parallel: bool = True, max_workers: int = 4):
        """
        Initialize pipeline orchestrator.
        
        Args:
            parallel: Whether to run scrapers in parallel
            max_workers: Maximum parallel workers
        """
        self.parallel = parallel
        self.max_workers = max_workers
        self.logger = logging.getLogger('bioleads.pipeline.orchestrator')
        
        # Stage results
        self.raw_leads: List[Dict] = []
        self.deduplicated_leads: List[Dict] = []
        self.enriched_leads: List[Dict] = []
        self.scored_leads: List[Dict] = []
        
        # Stage callbacks
        self._callbacks: Dict[str, List[Callable]] = {
            'on_scrape_complete': [],
            'on_enrich_complete': [],
            'on_score_complete': [],
            'on_pipeline_complete': [],
        }
    
    def run(
        self,
        sources: Optional[List[str]] = None,
        max_results_per_source: int = 100,
        skip_enrichment: bool = False,
        output_path: Optional[Path] = None,
    ) -> List[Dict]:
        """
        Run the complete pipeline.
        
        Args:
            sources: List of sources to scrape (None = all)
            max_results_per_source: Max results from each source
            skip_enrichment: Skip enrichment stage (faster)
            output_path: Path to save results
            
        Returns:
            List of scored leads
        """
        start_time = datetime.now()
        self.logger.info("Starting pipeline...")
        
        # Stage 1: Scraping
        self.logger.info("Stage 1: Scraping sources...")
        self.raw_leads = self._run_scrapers(sources, max_results_per_source)
        self._trigger_callbacks('on_scrape_complete', self.raw_leads)
        self.logger.info(f"Collected {len(self.raw_leads)} raw leads")
        
        # Stage 2: Deduplication
        self.logger.info("Stage 2: Deduplicating leads...")
        self.deduplicated_leads = self._run_deduplication(self.raw_leads)
        self.logger.info(f"Deduplicated to {len(self.deduplicated_leads)} leads")
        
        # Stage 3: Enrichment
        if not skip_enrichment:
            self.logger.info("Stage 3: Enriching leads...")
            self.enriched_leads = self._run_enrichment(self.deduplicated_leads)
            self._trigger_callbacks('on_enrich_complete', self.enriched_leads)
        else:
            self.enriched_leads = self.deduplicated_leads
            self.logger.info("Stage 3: Skipping enrichment")
        
        # Stage 4: Scoring
        self.logger.info("Stage 4: Scoring leads...")
        self.scored_leads = self._run_scoring(self.enriched_leads)
        self._trigger_callbacks('on_score_complete', self.scored_leads)
        
        # Stage 5: Export
        if output_path:
            self.logger.info(f"Stage 5: Exporting to {output_path}")
            self.export(output_path)
        
        duration = (datetime.now() - start_time).total_seconds()
        self.logger.info(f"Pipeline complete in {duration:.1f}s. {len(self.scored_leads)} leads generated.")
        
        self._trigger_callbacks('on_pipeline_complete', self.scored_leads)
        
        return self.scored_leads
    
    def _run_scrapers(
        self,
        sources: Optional[List[str]],
        max_results: int,
    ) -> List[Dict]:
        """Run all scrapers and collect leads."""
        from ..scrapers import (
            PubMedScraper,
            NIHReporterScraper,
            OpenAlexScraper,
            ClinicalTrialsScraper,
        )
        from ..config.keywords import keywords
        
        all_leads = []
        
        # Define available scrapers
        available_scrapers = {
            'pubmed': lambda: self._run_pubmed_scraper(max_results),
            'nih': lambda: self._run_nih_scraper(max_results),
            'openalex': lambda: self._run_openalex_scraper(max_results),
            'clinicaltrials': lambda: self._run_clinicaltrials_scraper(max_results),
        }
        
        # Filter to requested sources
        if sources:
            scrapers_to_run = {k: v for k, v in available_scrapers.items() if k in sources}
        else:
            scrapers_to_run = available_scrapers
        
        if self.parallel and len(scrapers_to_run) > 1:
            # Run scrapers in parallel
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {
                    executor.submit(func): name
                    for name, func in scrapers_to_run.items()
                }
                
                for future in as_completed(futures):
                    name = futures[future]
                    try:
                        leads = future.result()
                        all_leads.extend(leads)
                        self.logger.info(f"Scraper '{name}' returned {len(leads)} leads")
                    except Exception as e:
                        self.logger.error(f"Scraper '{name}' failed: {e}")
        else:
            # Run sequentially
            for name, func in scrapers_to_run.items():
                try:
                    leads = func()
                    all_leads.extend(leads)
                    self.logger.info(f"Scraper '{name}' returned {len(leads)} leads")
                except Exception as e:
                    self.logger.error(f"Scraper '{name}' failed: {e}")
        
        return all_leads
    
    def _run_pubmed_scraper(self, max_results: int) -> List[Dict]:
        """Run PubMed scraper."""
        from ..scrapers import PubMedScraper
        from ..config.keywords import keywords
        
        scraper = PubMedScraper()
        return scraper.run(
            queries=keywords.pubmed_queries[:3],  # Top 3 queries
            max_results_per_query=max_results // 3,
        )
    
    def _run_nih_scraper(self, max_results: int) -> List[Dict]:
        """Run NIH Reporter scraper."""
        from ..scrapers import NIHReporterScraper
        
        scraper = NIHReporterScraper()
        return scraper.run_with_keywords(max_results_per_term=max_results // 5)
    
    def _run_openalex_scraper(self, max_results: int) -> List[Dict]:
        """Run OpenAlex scraper."""
        from ..scrapers import OpenAlexScraper
        
        scraper = OpenAlexScraper()
        return scraper.run_with_keywords(max_results_per_query=max_results // 5)
    
    def _run_clinicaltrials_scraper(self, max_results: int) -> List[Dict]:
        """Run ClinicalTrials.gov scraper."""
        from ..scrapers import ClinicalTrialsScraper
        
        scraper = ClinicalTrialsScraper()
        return scraper.run_with_keywords(max_results_per_query=max_results // 5)
    
    def _run_deduplication(self, leads: List[Dict]) -> List[Dict]:
        """Run deduplication."""
        from .deduplication import Deduplicator
        
        deduplicator = Deduplicator()
        return deduplicator.deduplicate(leads)
    
    def _run_enrichment(self, leads: List[Dict]) -> List[Dict]:
        """Run enrichment pipeline."""
        from ..enrichment import EmailFinder, LocationResolver, CompanyEnricher
        
        # Email enrichment
        email_finder = EmailFinder()
        leads = email_finder.batch_find_emails(leads)
        
        # Location enrichment
        location_resolver = LocationResolver()
        leads = location_resolver.batch_resolve(leads)
        
        # Company enrichment
        company_enricher = CompanyEnricher()
        leads = company_enricher.batch_enrich(leads)
        
        return leads
    
    def _run_scoring(self, leads: List[Dict]) -> List[Dict]:
        """Run scoring."""
        from ..scoring import PropensityEngine
        
        engine = PropensityEngine()
        return engine.score_batch(leads)
    
    def export(
        self,
        output_path: Path,
        format: str = 'csv',
        include_raw: bool = False,
    ) -> Path:
        """
        Export leads to file.
        
        Args:
            output_path: Output file path
            format: Export format (csv, json, excel)
            include_raw: Include raw data in export
            
        Returns:
            Path to exported file
        """
        if not self.scored_leads:
            self.logger.warning("No leads to export")
            return output_path
        
        # Prepare data for export
        export_data = []
        for lead in self.scored_leads:
            row = {
                'name': lead.get('name', ''),
                'email': lead.get('email', ''),
                'email_confidence': lead.get('email_confidence', ''),
                'title': lead.get('title', ''),
                'institution': lead.get('institution', ''),
                'department': lead.get('department', ''),
                'location': str(lead.get('location', '')),
                'score': lead.get('score', 0),
                'tier': lead.get('tier', ''),
                'sources': ', '.join(lead.get('sources', [lead.get('source', '')])),
                'research_focus': '; '.join(lead.get('research_focus', [])[:5]),
                'publications': lead.get('publications', 0),
                'grants_count': len(lead.get('grants', [])),
                'orcid': lead.get('orcid', ''),
            }
            
            if include_raw:
                row['raw_data'] = json.dumps(lead.get('raw_data', {}))
            
            export_data.append(row)
        
        df = pd.DataFrame(export_data)
        
        # Export based on format
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format == 'csv':
            filepath = output_path.with_suffix('.csv')
            df.to_csv(filepath, index=False)
        elif format == 'json':
            filepath = output_path.with_suffix('.json')
            df.to_json(filepath, orient='records', indent=2)
        elif format == 'excel':
            filepath = output_path.with_suffix('.xlsx')
            df.to_excel(filepath, index=False)
        else:
            filepath = output_path.with_suffix('.csv')
            df.to_csv(filepath, index=False)
        
        self.logger.info(f"Exported {len(export_data)} leads to {filepath}")
        return filepath
    
    def get_summary(self) -> Dict:
        """Get pipeline summary statistics."""
        if not self.scored_leads:
            return {'status': 'no_data'}
        
        tiers = {'hot': 0, 'warm': 0, 'cold': 0, 'ice': 0}
        sources = {}
        
        for lead in self.scored_leads:
            tier = lead.get('tier', 'ice')
            tiers[tier] = tiers.get(tier, 0) + 1
            
            for source in lead.get('sources', [lead.get('source', 'unknown')]):
                sources[source] = sources.get(source, 0) + 1
        
        avg_score = sum(l.get('score', 0) for l in self.scored_leads) / len(self.scored_leads)
        
        return {
            'total_leads': len(self.scored_leads),
            'raw_leads': len(self.raw_leads),
            'duplicates_removed': len(self.raw_leads) - len(self.deduplicated_leads),
            'tiers': tiers,
            'sources': sources,
            'average_score': round(avg_score, 1),
            'leads_with_email': sum(1 for l in self.scored_leads if l.get('email')),
        }
    
    def add_callback(self, event: str, callback: Callable):
        """Add a callback for pipeline events."""
        if event in self._callbacks:
            self._callbacks[event].append(callback)
    
    def _trigger_callbacks(self, event: str, data):
        """Trigger callbacks for an event."""
        for callback in self._callbacks.get(event, []):
            try:
                callback(data)
            except Exception as e:
                self.logger.error(f"Callback error for {event}: {e}")
