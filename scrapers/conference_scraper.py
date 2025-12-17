# BioLeads Conference Scraper
"""
Scraper for scientific conferences related to 3D in-vitro models.
Focuses on Society of Toxicology (SOT) and similar conferences.
"""

import re
from typing import Dict, List, Optional
from datetime import datetime
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper


class ConferenceScraper(BaseScraper):
    """
    Scraper for scientific conference data.
    
    Targets conferences where potential customers might present:
    - Society of Toxicology (SOT) Annual Meeting
    - ISSCR Annual Meeting
    - 3D Cell Culture conferences
    - AACR Annual Meeting
    
    Note: Many conference sites require careful scraping or
    have APIs. This implements web scraping where needed.
    """
    
    # Conference configurations
    CONFERENCES = {
        'sot': {
            'name': 'Society of Toxicology Annual Meeting',
            'base_url': 'https://www.toxicology.org',
            'sessions_path': '/annual-meeting/program',
            'keywords': ['in vitro', 'organoid', '3D', 'alternative methods', 'NAMs'],
        },
        'isscr': {
            'name': 'ISSCR Annual Meeting',
            'base_url': 'https://www.isscr.org',
            'sessions_path': '/meetings/annual-meeting',
            'keywords': ['organoid', 'stem cell', 'differentiation', 'disease model'],
        },
    }
    
    def __init__(self, conference: str = 'sot'):
        """
        Initialize conference scraper.
        
        Args:
            conference: Conference key (e.g., 'sot', 'isscr')
        """
        config = self.CONFERENCES.get(conference, self.CONFERENCES['sot'])
        
        super().__init__(
            name=f'conference_{conference}',
            base_url=config['base_url'],
            rate_limit_seconds=2.0,  # Be polite with conference sites
        )
        
        self.conference_name = config['name']
        self.sessions_path = config['sessions_path']
        self.target_keywords = config['keywords']
    
    def search(self, query: str, max_results: int = 100) -> List[Dict]:
        """
        Search conference sessions/abstracts.
        
        Args:
            query: Search query
            max_results: Maximum results
            
        Returns:
            List of session/abstract dictionaries
        """
        self.logger.info(f"Searching conference {self.conference_name}: {query}")
        
        # Try to fetch the program page
        response = self.fetch(self.sessions_path)
        
        if not response:
            self.logger.warning(f"Could not fetch conference page")
            return []
        
        if 'raw_content' in response:
            return self._parse_html_program(response['raw_content'], query)
        
        return []
    
    def _parse_html_program(self, html: str, query: str) -> List[Dict]:
        """Parse HTML conference program page."""
        soup = BeautifulSoup(html, 'lxml')
        sessions = []
        
        # Look for session/abstract containers (common patterns)
        # This needs to be adapted for each conference site
        session_elements = soup.find_all(['div', 'article'], class_=re.compile(
            r'session|abstract|presentation|talk|poster', re.I
        ))
        
        for elem in session_elements:
            session = self._extract_session(elem, query)
            if session:
                sessions.append(session)
        
        return sessions
    
    def _extract_session(self, element, query: str) -> Optional[Dict]:
        """Extract session information from HTML element."""
        try:
            # Get title
            title_elem = element.find(['h1', 'h2', 'h3', 'h4', 'a'])
            title = title_elem.get_text(strip=True) if title_elem else ''
            
            # Get description/abstract
            desc_elem = element.find(['p', 'div'], class_=re.compile(r'desc|abstract|content', re.I))
            description = desc_elem.get_text(strip=True) if desc_elem else ''
            
            # Check relevance
            text = f"{title} {description}".lower()
            if not any(kw.lower() in text for kw in self.target_keywords):
                if query.lower() not in text:
                    return None
            
            # Try to extract presenter info
            author_elem = element.find(['span', 'div', 'p'], class_=re.compile(r'author|presenter|speaker', re.I))
            presenter = author_elem.get_text(strip=True) if author_elem else ''
            
            # Try to extract affiliation
            affil_elem = element.find(['span', 'div', 'p'], class_=re.compile(r'affil|org|instit', re.I))
            affiliation = affil_elem.get_text(strip=True) if affil_elem else ''
            
            return {
                'title': title,
                'description': description,
                'presenter': presenter,
                'affiliation': affiliation,
                'conference': self.conference_name,
                'session_type': self._detect_session_type(element),
            }
            
        except Exception as e:
            self.logger.debug(f"Error extracting session: {e}")
            return None
    
    def _detect_session_type(self, element) -> str:
        """Detect whether this is a poster, talk, symposium, etc."""
        text = element.get_text().lower()
        
        if 'poster' in text:
            return 'poster'
        elif 'symposium' in text:
            return 'symposium'
        elif 'workshop' in text:
            return 'workshop'
        elif 'keynote' in text:
            return 'keynote'
        else:
            return 'presentation'
    
    def parse_lead(self, raw_data: Dict) -> Optional[Dict]:
        """
        Parse session data into lead format.
        """
        if not raw_data or not raw_data.get('presenter'):
            return None
        
        return {
            'source': f'conference_{self.conference_name}',
            'source_id': f"{self.conference_name}_{raw_data.get('title', '')[:50]}",
            'name': raw_data.get('presenter', ''),
            'email': None,
            'title': None,
            'institution': raw_data.get('affiliation', ''),
            'department': None,
            'location': None,
            'research_focus': self.target_keywords[:5],
            'publications': 0,
            'grants': [],
            'conference_presentation': {
                'conference': self.conference_name,
                'title': raw_data.get('title', ''),
                'abstract': raw_data.get('description', ''),
                'session_type': raw_data.get('session_type', ''),
            },
            'raw_data': raw_data,
        }
    
    def create_synthetic_leads_from_keywords(self) -> List[Dict]:
        """
        For conferences that are hard to scrape, create placeholder 
        entries that can be manually enriched later.
        
        This generates a template for common conference attendee profiles.
        """
        from ..config.keywords import keywords
        
        templates = []
        
        # Create templates for each conference type
        for conf_key, conf_config in self.CONFERENCES.items():
            template = {
                'source': f'conference_{conf_key}',
                'source_id': f'template_{conf_key}',
                'name': '[TO BE ENRICHED]',
                'email': None,
                'title': None,
                'institution': '[TO BE ENRICHED]',
                'department': None,
                'location': None,
                'research_focus': conf_config['keywords'],
                'publications': 0,
                'grants': [],
                'conference_info': {
                    'conference': conf_config['name'],
                    'tracks_to_target': keywords.conference_tracks,
                    'note': 'Manual enrichment needed - search conference program',
                },
                'enrichment_status': 'pending',
            }
            templates.append(template)
        
        return templates
    
    @staticmethod
    def get_manual_enrichment_guide() -> str:
        """
        Return a guide for manually finding conference attendees.
        """
        return """
        ## Conference Lead Enrichment Guide
        
        For each target conference, manually collect:
        
        1. **SOT (Society of Toxicology)**
           - Visit: https://www.toxicology.org/annual-meeting
           - Focus on sessions: "In Vitro Toxicology", "Alternative Methods", "NAMs"
           - Look for: Poster presenters, session chairs, invited speakers
           
        2. **ISSCR (Stem Cell Research)**
           - Visit: https://www.isscr.org/meetings
           - Focus on: Organoid sessions, disease modeling
           - Look for: Lab heads presenting translational work
           
        3. **AACR (Cancer Research)**
           - Visit: https://www.aacr.org/meeting/
           - Focus on: 3D tumor models, PDO (patient-derived organoids)
           - Look for: Pharma/biotech presenters
           
        4. **3D Cell Culture Conference**
           - Search for current year's event
           - All attendees are relevant targets
           
        Export as CSV with columns:
        name, email, title, institution, session_presented, research_keywords
        """
