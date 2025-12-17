# BioLeads NIH RePORTER Scraper
"""
Scraper for NIH RePORTER API.
Finds grants related to 3D in-vitro models, organoids, and drug discovery.
Free API - no API key required.
"""

from typing import Dict, List, Optional
from datetime import datetime

from .base_scraper import BaseScraper


class NIHReporterScraper(BaseScraper):
    """
    Scraper for NIH RePORTER database.
    
    Uses NIH RePORTER API v2 to find grants related to 3D in-vitro models
    and drug discovery/toxicology applications.
    
    API Documentation: https://api.reporter.nih.gov/
    """
    
    def __init__(self):
        """Initialize NIH RePORTER scraper."""
        from ..config.settings import settings
        
        super().__init__(
            name='nih_reporter',
            base_url=settings.api.nih_reporter_base_url,
            rate_limit_seconds=settings.api.nih_reporter_rate_limit,
        )
    
    def search(self, query: str, max_results: int = 100) -> List[Dict]:
        """
        Search NIH RePORTER for grants.
        
        Args:
            query: Search terms
            max_results: Maximum number of results
            
        Returns:
            List of grant dictionaries
        """
        from ..config.keywords import keywords
        
        self.logger.info(f"Searching NIH RePORTER: {query[:50]}...")
        
        all_grants = []
        offset = 0
        limit = min(500, max_results)  # API max is 500 per request
        
        while len(all_grants) < max_results:
            # Build search criteria
            criteria = {
                'criteria': {
                    'advanced_text_search': {
                        'operator': 'and',
                        'search_field': 'all',
                        'search_text': query,
                    },
                    # Focus on recent active grants
                    'fiscal_years': list(range(datetime.now().year - 3, datetime.now().year + 1)),
                    # Prioritize certain activity codes
                    'activity_codes': keywords.nih_priority_activity_codes,
                    # Exclude expired projects
                    'is_active': True,
                },
                'offset': offset,
                'limit': limit,
                'sort_field': 'project_start_date',
                'sort_order': 'desc',
            }
            
            response = self.fetch(
                'projects/search',
                method='POST',
                json_data=criteria,
            )
            
            if not response:
                break
            
            results = response.get('results', [])
            if not results:
                break
            
            all_grants.extend(results)
            offset += limit
            
            # Check if we've gotten all results
            total = response.get('meta', {}).get('total', 0)
            if offset >= total:
                break
        
        self.logger.info(f"Found {len(all_grants)} grants")
        return all_grants[:max_results]
    
    def search_by_terms(self, terms: List[str], max_results: int = 100) -> List[Dict]:
        """
        Search using multiple terms (OR logic).
        
        Args:
            terms: List of search terms
            max_results: Maximum results per term
            
        Returns:
            Combined list of unique grants
        """
        all_grants = {}  # Use dict for deduplication by project number
        
        for term in terms:
            grants = self.search(term, max_results=max_results // len(terms))
            for grant in grants:
                project_num = grant.get('project_num', '')
                if project_num and project_num not in all_grants:
                    all_grants[project_num] = grant
        
        return list(all_grants.values())
    
    def get_project_details(self, project_number: str) -> Optional[Dict]:
        """
        Get detailed information for a specific project.
        
        Args:
            project_number: NIH project number (e.g., "1R01CA123456-01A1")
            
        Returns:
            Project details dictionary
        """
        criteria = {
            'criteria': {
                'project_nums': [project_number],
            },
            'offset': 0,
            'limit': 1,
        }
        
        response = self.fetch(
            'projects/search',
            method='POST',
            json_data=criteria,
        )
        
        if response and response.get('results'):
            return response['results'][0]
        
        return None
    
    def get_publications_for_project(self, project_number: str, max_results: int = 50) -> List[Dict]:
        """
        Get publications associated with a project.
        
        Args:
            project_number: NIH project number
            max_results: Maximum publications to return
            
        Returns:
            List of publication dictionaries
        """
        criteria = {
            'criteria': {
                'core_project_nums': [project_number.split('-')[0]],  # Use core project number
            },
            'offset': 0,
            'limit': max_results,
        }
        
        response = self.fetch(
            'publications/search',
            method='POST',
            json_data=criteria,
        )
        
        if response:
            return response.get('results', [])
        
        return []
    
    def parse_lead(self, raw_data: Dict) -> Optional[Dict]:
        """
        Parse grant data into lead format.
        
        Extracts Principal Investigator as the lead.
        """
        if not raw_data:
            return None
        
        # Get PI information
        pi_list = raw_data.get('principal_investigators', [])
        if not pi_list:
            return None
        
        pi = pi_list[0]  # Primary PI
        
        # Organization info
        org = raw_data.get('organization', {})
        
        # Extract award amount
        award_amount = raw_data.get('award_amount', 0)
        
        # Research terms
        terms = raw_data.get('terms', '') or ''
        research_focus = [t.strip() for t in terms.split(';') if t.strip()]
        
        return {
            'source': 'nih_reporter',
            'source_id': raw_data.get('project_num', ''),
            'name': pi.get('full_name', ''),
            'email': pi.get('email'),
            'title': pi.get('title', 'Principal Investigator'),
            'institution': org.get('org_name', ''),
            'department': org.get('org_dept') or raw_data.get('dept_type'),
            'location': self._format_location(org),
            'research_focus': research_focus[:10],  # Limit to top 10 terms
            'publications': 0,  # Will be enriched later
            'grants': [{
                'project_number': raw_data.get('project_num', ''),
                'title': raw_data.get('project_title', ''),
                'abstract': raw_data.get('abstract_text', ''),
                'award_amount': award_amount,
                'start_date': raw_data.get('project_start_date'),
                'end_date': raw_data.get('project_end_date'),
                'activity_code': raw_data.get('activity_code'),
                'funding_mechanism': raw_data.get('funding_mechanism'),
                'nih_institute': raw_data.get('agency_ic_admin', {}).get('name', ''),
            }],
            'orcid': pi.get('orcid'),
            'raw_data': raw_data,
        }
    
    def _format_location(self, org: Dict) -> str:
        """Format organization location."""
        parts = filter(None, [
            org.get('org_city'),
            org.get('org_state'),
            org.get('org_country'),
        ])
        return ', '.join(parts)
    
    def run_with_keywords(
        self,
        max_results_per_term: int = 50,
        save_raw: bool = True,
    ) -> List[Dict]:
        """
        Run scraper using pre-configured keywords.
        
        Args:
            max_results_per_term: Max results per search term
            save_raw: Whether to save raw data
            
        Returns:
            List of parsed lead records
        """
        from ..config.keywords import keywords
        
        grants = self.search_by_terms(
            keywords.nih_grant_terms,
            max_results=max_results_per_term * len(keywords.nih_grant_terms),
        )
        
        if save_raw and grants:
            self.save_raw(grants, 'all_grants')
        
        leads = [self.parse_lead(g) for g in grants]
        return [l for l in leads if l]
