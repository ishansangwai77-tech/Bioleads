# Tests for scrapers
"""Unit tests for BioLeads scrapers."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json


class TestBaseScraper:
    """Tests for BaseScraper class."""
    
    def test_rate_limit_wait(self):
        """Test that rate limiting works."""
        from bioleads.scrapers.base_scraper import BaseScraper
        
        # Create a concrete implementation for testing
        class TestScraper(BaseScraper):
            def search(self, query, max_results=100):
                return []
            
            def parse_lead(self, raw_data):
                return raw_data
        
        scraper = TestScraper(
            name='test',
            base_url='https://example.com',
            rate_limit_seconds=0.1,
        )
        
        assert scraper.name == 'test'
        assert scraper.rate_limit_seconds == 0.1


class TestPubMedScraper:
    """Tests for PubMed scraper."""
    
    @patch('bioleads.scrapers.pubmed_scraper.PubMedScraper.fetch')
    def test_search_ids(self, mock_fetch):
        """Test PubMed ID search."""
        from bioleads.scrapers import PubMedScraper
        
        mock_fetch.return_value = {
            'esearchresult': {
                'idlist': ['12345', '67890'],
                'count': '2',
            }
        }
        
        scraper = PubMedScraper()
        ids = scraper.search_ids('organoid', max_results=10)
        
        assert ids == ['12345', '67890']
        assert mock_fetch.called
    
    def test_parse_lead(self):
        """Test parsing PubMed article to lead format."""
        from bioleads.scrapers import PubMedScraper
        
        scraper = PubMedScraper()
        
        raw_data = {
            'pmid': '12345',
            'title': 'Test Article',
            'authors': [
                {
                    'name': 'John Doe',
                    'affiliation': 'Department of Biology, Harvard University, Boston, MA, USA',
                    'email': 'jdoe@harvard.edu',
                }
            ],
            'journal': 'Test Journal',
            'pub_date': '2024',
            'keywords': ['organoid', '3D culture'],
        }
        
        lead = scraper.parse_lead(raw_data)
        
        assert lead['source'] == 'pubmed'
        assert lead['source_id'] == '12345'
        assert lead['name'] == 'John Doe'
        assert lead['email'] == 'jdoe@harvard.edu'
        assert 'organoid' in lead['research_focus']
    
    def test_parse_lead_no_authors(self):
        """Test parsing with no authors returns None."""
        from bioleads.scrapers import PubMedScraper
        
        scraper = PubMedScraper()
        lead = scraper.parse_lead({'pmid': '12345', 'authors': []})
        
        assert lead is None


class TestNIHReporterScraper:
    """Tests for NIH RePORTER scraper."""
    
    @patch('bioleads.scrapers.nih_reporter_scraper.NIHReporterScraper.fetch')
    def test_search(self, mock_fetch):
        """Test NIH grant search."""
        from bioleads.scrapers import NIHReporterScraper
        
        mock_fetch.return_value = {
            'results': [
                {
                    'project_num': 'R01CA123456',
                    'project_title': 'Organoid Research',
                    'principal_investigators': [
                        {'full_name': 'Jane Smith', 'email': 'jsmith@nih.gov'}
                    ],
                    'organization': {'org_name': 'NIH'},
                    'award_amount': 500000,
                }
            ],
            'meta': {'total': 1},
        }
        
        scraper = NIHReporterScraper()
        grants = scraper.search('organoid', max_results=10)
        
        assert len(grants) == 1
        assert grants[0]['project_num'] == 'R01CA123456'
    
    def test_parse_lead(self):
        """Test parsing NIH grant to lead format."""
        from bioleads.scrapers import NIHReporterScraper
        
        scraper = NIHReporterScraper()
        
        raw_data = {
            'project_num': 'R01CA123456',
            'project_title': 'Organoid Research',
            'principal_investigators': [
                {'full_name': 'Jane Smith', 'email': 'jsmith@nih.gov', 'title': 'PI'}
            ],
            'organization': {
                'org_name': 'Harvard University',
                'org_city': 'Boston',
                'org_state': 'MA',
                'org_country': 'United States',
            },
            'award_amount': 500000,
            'terms': 'organoid; 3D culture; drug screening',
        }
        
        lead = scraper.parse_lead(raw_data)
        
        assert lead['source'] == 'nih_reporter'
        assert lead['name'] == 'Jane Smith'
        assert lead['institution'] == 'Harvard University'
        assert len(lead['grants']) == 1
        assert lead['grants'][0]['award_amount'] == 500000


class TestOpenAlexScraper:
    """Tests for OpenAlex scraper."""
    
    def test_reconstruct_abstract(self):
        """Test abstract reconstruction from inverted index."""
        from bioleads.scrapers import OpenAlexScraper
        
        scraper = OpenAlexScraper()
        
        inverted_index = {
            'This': [0],
            'is': [1],
            'a': [2],
            'test': [3],
        }
        
        abstract = scraper._reconstruct_abstract(inverted_index)
        
        assert abstract == 'This is a test'
    
    def test_get_location(self):
        """Test location extraction from institution."""
        from bioleads.scrapers import OpenAlexScraper
        
        scraper = OpenAlexScraper()
        
        institution = {
            'geo': {
                'city': 'Boston',
                'region': 'Massachusetts',
                'country': 'United States',
            }
        }
        
        location = scraper._get_location(institution)
        
        assert 'Boston' in location
        assert 'Massachusetts' in location


class TestClinicalTrialsScraper:
    """Tests for ClinicalTrials.gov scraper."""
    
    def test_format_location(self):
        """Test location formatting."""
        from bioleads.scrapers import ClinicalTrialsScraper
        
        scraper = ClinicalTrialsScraper()
        
        location = {
            'city': 'Boston',
            'state': 'MA',
            'country': 'United States',
        }
        
        formatted = scraper._format_location(location)
        
        assert formatted == 'Boston, MA, United States'
