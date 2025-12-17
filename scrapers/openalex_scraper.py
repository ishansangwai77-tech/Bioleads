# BioLeads OpenAlex Scraper
"""
Scraper for OpenAlex API.
Free, open-source alternative to paid academic databases.
Provides author, institution, and publication data.
"""

from typing import Dict, List, Optional
from datetime import datetime
import urllib.parse

from .base_scraper import BaseScraper


class OpenAlexScraper(BaseScraper):
    """
    Scraper for OpenAlex - open catalog of scholarly works.
    
    OpenAlex is a free, open alternative to proprietary databases.
    It indexes over 200M works, 50M authors, and 100K institutions.
    
    API Documentation: https://docs.openalex.org/
    """
    
    def __init__(self, email: Optional[str] = None):
        """
        Initialize OpenAlex scraper.
        
        Args:
            email: Email for polite pool (faster rate limits)
        """
        from ..config.settings import settings
        
        super().__init__(
            name='openalex',
            base_url=settings.api.openalex_base_url,
            rate_limit_seconds=settings.api.openalex_rate_limit,
        )
        
        self.email = email or settings.api.openalex_email
        
        # Add email to session headers for polite pool
        if self.email:
            self.session.headers['User-Agent'] = f'BioLeads/1.0 (mailto:{self.email})'
    
    def search(self, query: str, max_results: int = 100) -> List[Dict]:
        """
        Search for works in OpenAlex.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            List of work dictionaries
        """
        self.logger.info(f"Searching OpenAlex works: {query[:50]}...")
        
        all_works = []
        cursor = '*'  # OpenAlex uses cursor pagination
        per_page = min(200, max_results)  # Max 200 per request
        
        while len(all_works) < max_results:
            params = {
                'search': query,
                'per_page': per_page,
                'cursor': cursor,
                'filter': f'from_publication_date:2020-01-01',  # Recent works
                'select': 'id,doi,title,publication_date,authorships,concepts,cited_by_count,abstract_inverted_index',
            }
            
            if self.email:
                params['mailto'] = self.email
            
            response = self.fetch('works', params=params)
            
            if not response:
                break
            
            results = response.get('results', [])
            if not results:
                break
            
            all_works.extend(results)
            
            # Get next cursor
            cursor = response.get('meta', {}).get('next_cursor')
            if not cursor:
                break
        
        self.logger.info(f"Found {len(all_works)} works")
        return all_works[:max_results]
    
    def search_authors(self, query: str, max_results: int = 100) -> List[Dict]:
        """
        Search for authors/researchers.
        
        Args:
            query: Search query (name or topic)
            max_results: Maximum number of results
            
        Returns:
            List of author dictionaries
        """
        self.logger.info(f"Searching OpenAlex authors: {query[:50]}...")
        
        all_authors = []
        cursor = '*'
        per_page = min(200, max_results)
        
        while len(all_authors) < max_results:
            params = {
                'search': query,
                'per_page': per_page,
                'cursor': cursor,
                'filter': 'works_count:>5',  # Active researchers
                'select': 'id,orcid,display_name,works_count,cited_by_count,affiliations,last_known_institutions,x_concepts',
            }
            
            if self.email:
                params['mailto'] = self.email
            
            response = self.fetch('authors', params=params)
            
            if not response:
                break
            
            results = response.get('results', [])
            if not results:
                break
            
            all_authors.extend(results)
            
            cursor = response.get('meta', {}).get('next_cursor')
            if not cursor:
                break
        
        self.logger.info(f"Found {len(all_authors)} authors")
        return all_authors[:max_results]
    
    def search_by_concepts(self, concept_ids: List[str], max_results: int = 100) -> List[Dict]:
        """
        Search works by OpenAlex concept IDs.
        
        Args:
            concept_ids: List of OpenAlex concept IDs (e.g., 'C203014093' for Organoid)
            max_results: Maximum results per concept
            
        Returns:
            List of work dictionaries
        """
        all_works = {}
        
        for concept_id in concept_ids:
            params = {
                'filter': f'concepts.id:{concept_id},from_publication_date:2020-01-01',
                'per_page': min(200, max_results),
                'select': 'id,doi,title,publication_date,authorships,concepts,cited_by_count',
                'sort': 'cited_by_count:desc',
            }
            
            if self.email:
                params['mailto'] = self.email
            
            response = self.fetch('works', params=params)
            
            if response:
                for work in response.get('results', []):
                    work_id = work.get('id', '')
                    if work_id not in all_works:
                        all_works[work_id] = work
        
        return list(all_works.values())
    
    def get_author_details(self, author_id: str) -> Optional[Dict]:
        """
        Get detailed author information.
        
        Args:
            author_id: OpenAlex author ID (e.g., 'A1234567890')
            
        Returns:
            Author details dictionary
        """
        params = {}
        if self.email:
            params['mailto'] = self.email
        
        # Extract just the ID if full URL given
        if author_id.startswith('https://'):
            author_id = author_id.split('/')[-1]
        
        response = self.fetch(f'authors/{author_id}', params=params)
        return response
    
    def get_institution_details(self, institution_id: str) -> Optional[Dict]:
        """
        Get detailed institution information.
        
        Args:
            institution_id: OpenAlex institution ID
            
        Returns:
            Institution details dictionary
        """
        params = {}
        if self.email:
            params['mailto'] = self.email
        
        if institution_id.startswith('https://'):
            institution_id = institution_id.split('/')[-1]
        
        response = self.fetch(f'institutions/{institution_id}', params=params)
        return response
    
    def parse_lead(self, raw_data: Dict) -> Optional[Dict]:
        """
        Parse work data into lead format.
        
        Extracts first author as primary lead.
        """
        if not raw_data:
            return None
        
        authorships = raw_data.get('authorships', [])
        if not authorships:
            return None
        
        # Get first/corresponding author
        primary_auth = authorships[0]
        author_info = primary_auth.get('author', {})
        
        # Get institution
        institutions = primary_auth.get('institutions', [])
        institution = institutions[0] if institutions else {}
        
        # Get research concepts
        concepts = raw_data.get('concepts', [])
        research_focus = [c.get('display_name', '') for c in concepts[:10]]
        
        # Reconstruct abstract if inverted index available
        abstract = self._reconstruct_abstract(raw_data.get('abstract_inverted_index'))
        
        return {
            'source': 'openalex',
            'source_id': raw_data.get('id', ''),
            'name': author_info.get('display_name', ''),
            'email': None,  # OpenAlex doesn't provide emails
            'title': None,
            'institution': institution.get('display_name', ''),
            'department': None,
            'location': self._get_location(institution),
            'research_focus': research_focus,
            'publications': 1,
            'grants': [],
            'orcid': author_info.get('orcid'),
            'openalex_author_id': author_info.get('id'),
            'cited_by_count': raw_data.get('cited_by_count', 0),
            'publication_title': raw_data.get('title', ''),
            'doi': raw_data.get('doi'),
            'publication_date': raw_data.get('publication_date'),
            'raw_data': raw_data,
        }
    
    def parse_author_lead(self, raw_data: Dict) -> Optional[Dict]:
        """
        Parse author data into lead format.
        """
        if not raw_data:
            return None
        
        # Get current institution
        last_institutions = raw_data.get('last_known_institutions', [])
        institution = last_institutions[0] if last_institutions else {}
        
        # Get research concepts
        concepts = raw_data.get('x_concepts', [])
        research_focus = [c.get('display_name', '') for c in concepts[:10]]
        
        return {
            'source': 'openalex',
            'source_id': raw_data.get('id', ''),
            'name': raw_data.get('display_name', ''),
            'email': None,
            'title': None,
            'institution': institution.get('display_name', ''),
            'department': None,
            'location': self._get_location(institution),
            'research_focus': research_focus,
            'publications': raw_data.get('works_count', 0),
            'grants': [],
            'orcid': raw_data.get('orcid'),
            'openalex_author_id': raw_data.get('id'),
            'cited_by_count': raw_data.get('cited_by_count', 0),
            'raw_data': raw_data,
        }
    
    def _get_location(self, institution: Dict) -> Optional[str]:
        """Extract location from institution data."""
        geo = institution.get('geo', {})
        parts = filter(None, [
            geo.get('city'),
            geo.get('region'),
            geo.get('country'),
        ])
        return ', '.join(parts) or institution.get('country_code')
    
    def _reconstruct_abstract(self, inverted_index: Optional[Dict]) -> str:
        """Reconstruct abstract from OpenAlex inverted index format."""
        if not inverted_index:
            return ''
        
        try:
            # Build word position mapping
            word_positions = []
            for word, positions in inverted_index.items():
                for pos in positions:
                    word_positions.append((pos, word))
            
            # Sort by position and join
            word_positions.sort(key=lambda x: x[0])
            return ' '.join(word for _, word in word_positions)
        except Exception:
            return ''
    
    def run_with_keywords(
        self,
        max_results_per_query: int = 50,
        save_raw: bool = True,
    ) -> List[Dict]:
        """
        Run scraper using pre-configured keywords and concepts.
        
        Args:
            max_results_per_query: Max results per query
            save_raw: Whether to save raw data
            
        Returns:
            List of parsed lead records
        """
        from ..config.keywords import keywords
        
        all_leads = []
        
        # Search by concepts
        self.logger.info("Searching by OpenAlex concepts...")
        concept_works = self.search_by_concepts(
            keywords.openalex_concepts,
            max_results=max_results_per_query,
        )
        
        if save_raw and concept_works:
            self.save_raw(concept_works, 'concept_works')
        
        for work in concept_works:
            lead = self.parse_lead(work)
            if lead:
                all_leads.append(lead)
        
        # Also search for authors directly
        self.logger.info("Searching for authors by topic...")
        for term in keywords.core_terms[:5]:  # Top 5 core terms
            authors = self.search_authors(term, max_results=20)
            
            for author in authors:
                lead = self.parse_author_lead(author)
                if lead:
                    all_leads.append(lead)
        
        return all_leads
