# BioLeads PubMed Scraper
"""
Scraper for PubMed/NCBI using E-utilities API.
Finds researchers publishing on 3D in-vitro models for drug discovery.
Free API - register for API key for higher rate limits.
"""

import xml.etree.ElementTree as ET
from typing import Dict, List, Optional
from datetime import datetime

from .base_scraper import BaseScraper


class PubMedScraper(BaseScraper):
    """
    Scraper for PubMed database using NCBI E-utilities.
    
    Uses three E-utilities:
    - esearch: Find article IDs matching a query
    - efetch: Fetch article details
    - elink: Find related articles
    
    API Documentation: https://www.ncbi.nlm.nih.gov/books/NBK25500/
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize PubMed scraper.
        
        Args:
            api_key: Optional NCBI API key for higher rate limits
        """
        from ..config.settings import settings
        
        rate_limit = 0.34 if not api_key else 0.1  # 3 req/s without key, 10/s with
        
        super().__init__(
            name='pubmed',
            base_url=settings.api.pubmed_base_url,
            rate_limit_seconds=rate_limit,
        )
        
        self.api_key = api_key or settings.api.pubmed_api_key
        self.db = 'pubmed'
    
    def _add_api_key(self, params: Dict) -> Dict:
        """Add API key to params if available."""
        if self.api_key:
            params['api_key'] = self.api_key
        return params
    
    def search_ids(self, query: str, max_results: int = 100) -> List[str]:
        """
        Search PubMed and return article IDs.
        
        Args:
            query: PubMed search query
            max_results: Maximum number of IDs to return
            
        Returns:
            List of PubMed IDs (PMIDs)
        """
        params = self._add_api_key({
            'db': self.db,
            'term': query,
            'retmax': max_results,
            'retmode': 'json',
            'sort': 'relevance',
            'datetype': 'pdat',
            'mindate': '2019',  # Last 5 years
            'maxdate': datetime.now().strftime('%Y'),
        })
        
        response = self.fetch('esearch.fcgi', params=params)
        
        if not response:
            return []
        
        result = response.get('esearchresult', {})
        return result.get('idlist', [])
    
    def fetch_articles(self, pmids: List[str]) -> List[Dict]:
        """
        Fetch article details for given PMIDs.
        
        Args:
            pmids: List of PubMed IDs
            
        Returns:
            List of article dictionaries
        """
        if not pmids:
            return []
        
        # Fetch in batches of 100
        batch_size = 100
        all_articles = []
        
        for i in range(0, len(pmids), batch_size):
            batch = pmids[i:i + batch_size]
            
            params = self._add_api_key({
                'db': self.db,
                'id': ','.join(batch),
                'retmode': 'xml',
                'rettype': 'abstract',
            })
            
            response = self.fetch('efetch.fcgi', params=params)
            
            if response and 'raw_content' in response:
                articles = self._parse_xml_response(response['raw_content'])
                all_articles.extend(articles)
        
        return all_articles
    
    def _parse_xml_response(self, xml_content: str) -> List[Dict]:
        """Parse PubMed XML response into article dictionaries."""
        articles = []
        
        try:
            root = ET.fromstring(xml_content)
            
            for article_elem in root.findall('.//PubmedArticle'):
                article = self._parse_article(article_elem)
                if article:
                    articles.append(article)
                    
        except ET.ParseError as e:
            self.logger.error(f"XML parse error: {e}")
        
        return articles
    
    def _parse_article(self, article_elem) -> Optional[Dict]:
        """Parse a single PubmedArticle element."""
        try:
            medline = article_elem.find('.//MedlineCitation')
            if medline is None:
                return None
            
            pmid_elem = medline.find('.//PMID')
            pmid = pmid_elem.text if pmid_elem is not None else ''
            
            article = medline.find('.//Article')
            if article is None:
                return None
            
            # Title
            title_elem = article.find('.//ArticleTitle')
            title = title_elem.text if title_elem is not None else ''
            
            # Abstract
            abstract_parts = []
            for abstract_text in article.findall('.//AbstractText'):
                if abstract_text.text:
                    abstract_parts.append(abstract_text.text)
            abstract = ' '.join(abstract_parts)
            
            # Authors
            authors = []
            for author in article.findall('.//Author'):
                author_info = self._parse_author(author)
                if author_info:
                    authors.append(author_info)
            
            # Journal info
            journal = article.find('.//Journal')
            journal_title = ''
            pub_date = ''
            if journal is not None:
                journal_title_elem = journal.find('.//Title')
                journal_title = journal_title_elem.text if journal_title_elem is not None else ''
                
                pub_date_elem = journal.find('.//PubDate')
                if pub_date_elem is not None:
                    year = pub_date_elem.find('Year')
                    pub_date = year.text if year is not None else ''
            
            # Keywords/MeSH terms
            keywords = []
            for mesh in medline.findall('.//MeshHeading/DescriptorName'):
                if mesh.text:
                    keywords.append(mesh.text)
            
            return {
                'pmid': pmid,
                'title': title,
                'abstract': abstract,
                'authors': authors,
                'journal': journal_title,
                'pub_date': pub_date,
                'keywords': keywords,
            }
            
        except Exception as e:
            self.logger.error(f"Error parsing article: {e}")
            return None
    
    def _parse_author(self, author_elem) -> Optional[Dict]:
        """Parse author information from XML element."""
        try:
            last_name = author_elem.find('LastName')
            first_name = author_elem.find('ForeName')
            
            if last_name is None:
                return None
            
            author_info = {
                'last_name': last_name.text or '',
                'first_name': first_name.text if first_name is not None else '',
                'name': f"{first_name.text if first_name is not None else ''} {last_name.text}".strip(),
            }
            
            # Affiliation
            affiliation = author_elem.find('.//Affiliation')
            if affiliation is not None and affiliation.text:
                author_info['affiliation'] = affiliation.text
                
                # Try to extract email from affiliation
                email = self._extract_email(affiliation.text)
                if email:
                    author_info['email'] = email
            
            # ORCID if available
            for identifier in author_elem.findall('Identifier'):
                if identifier.get('Source') == 'ORCID':
                    author_info['orcid'] = identifier.text
            
            return author_info
            
        except Exception:
            return None
    
    def _extract_email(self, text: str) -> Optional[str]:
        """Extract email address from text."""
        import re
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        match = re.search(email_pattern, text)
        return match.group(0) if match else None
    
    def search(self, query: str, max_results: int = 100) -> List[Dict]:
        """
        Search PubMed and return article details.
        
        Args:
            query: PubMed search query
            max_results: Maximum number of results
            
        Returns:
            List of article dictionaries
        """
        self.logger.info(f"Searching PubMed: {query[:100]}...")
        
        # Step 1: Get PMIDs
        pmids = self.search_ids(query, max_results)
        self.logger.info(f"Found {len(pmids)} articles")
        
        # Step 2: Fetch article details
        articles = self.fetch_articles(pmids)
        self.logger.info(f"Fetched details for {len(articles)} articles")
        
        return articles
    
    def parse_lead(self, raw_data: Dict) -> Optional[Dict]:
        """
        Parse article data into lead format.
        
        Extracts first/corresponding author as the lead.
        """
        if not raw_data or not raw_data.get('authors'):
            return None
        
        # Use first author as primary lead
        primary_author = raw_data['authors'][0]
        
        # Try to get email from any author
        email = None
        for author in raw_data['authors']:
            if 'email' in author:
                email = author.get('email')
                break
        
        # Parse affiliation for institution
        affiliation = primary_author.get('affiliation', '')
        institution = self._parse_institution(affiliation)
        
        return {
            'source': 'pubmed',
            'source_id': raw_data.get('pmid', ''),
            'name': primary_author.get('name', ''),
            'email': email,
            'title': None,  # Not available from publications
            'institution': institution,
            'department': self._parse_department(affiliation),
            'location': self._parse_location(affiliation),
            'research_focus': raw_data.get('keywords', []),
            'publications': 1,  # This is one publication
            'grants': [],
            'orcid': primary_author.get('orcid'),
            'publication_title': raw_data.get('title', ''),
            'journal': raw_data.get('journal', ''),
            'pub_date': raw_data.get('pub_date', ''),
            'raw_data': raw_data,
        }
    
    def _parse_institution(self, affiliation: str) -> str:
        """Extract institution name from affiliation string."""
        if not affiliation:
            return ''
        
        # Common patterns: "Department, Institution, Location"
        # Try to extract institution (usually after first comma, before location)
        parts = [p.strip() for p in affiliation.split(',')]
        
        # Look for university/institute keywords
        for part in parts:
            part_lower = part.lower()
            if any(kw in part_lower for kw in ['university', 'institute', 'college', 'hospital', 'center', 'centre', 'school']):
                return part
        
        # Fallback to second part if available
        if len(parts) >= 2:
            return parts[1]
        
        return parts[0] if parts else ''
    
    def _parse_department(self, affiliation: str) -> Optional[str]:
        """Extract department from affiliation string."""
        if not affiliation:
            return None
        
        parts = [p.strip() for p in affiliation.split(',')]
        
        for part in parts:
            part_lower = part.lower()
            if any(kw in part_lower for kw in ['department', 'division', 'lab', 'laboratory', 'group', 'section']):
                return part
        
        # Often first part is department
        if len(parts) > 1:
            return parts[0]
        
        return None
    
    def _parse_location(self, affiliation: str) -> Optional[str]:
        """Extract location from affiliation string."""
        if not affiliation:
            return None
        
        parts = [p.strip() for p in affiliation.split(',')]
        
        # Location is usually last 1-2 parts
        if len(parts) >= 2:
            return ', '.join(parts[-2:])
        
        return None
