# Tests for enrichment
"""Unit tests for BioLeads enrichment services."""

import pytest


class TestEmailFinder:
    """Tests for EmailFinder class."""
    
    def test_generate_email_candidates(self):
        """Test email pattern generation."""
        from bioleads.enrichment import EmailFinder
        
        finder = EmailFinder()
        candidates = finder._generate_email_candidates(
            first_name='John',
            last_name='Doe',
            domain='example.com',
        )
        
        assert len(candidates) > 0
        
        # Check expected patterns
        emails = [c['email'] for c in candidates]
        assert 'john.doe@example.com' in emails
        assert 'jdoe@example.com' in emails
    
    def test_get_institution_domain_known(self):
        """Test domain lookup for known institutions."""
        from bioleads.enrichment import EmailFinder
        
        finder = EmailFinder()
        
        assert finder._get_institution_domain('Harvard University') == 'harvard.edu'
        assert finder._get_institution_domain('MIT') == 'mit.edu'
        assert finder._get_institution_domain('Pfizer Inc') == 'pfizer.com'
    
    def test_normalize_email(self):
        """Test email pattern learning."""
        from bioleads.enrichment import EmailFinder
        
        finder = EmailFinder()
        
        # Learn pattern
        finder.learn_pattern_from_known_email(
            email='John.Doe@example.com',
            first_name='John',
            last_name='Doe',
        )
        
        # Check cache
        assert 'example.com' in finder._domain_patterns


class TestLocationResolver:
    """Tests for LocationResolver class."""
    
    def test_resolve_us_location(self):
        """Test resolving US location."""
        from bioleads.enrichment import LocationResolver
        
        resolver = LocationResolver()
        location = resolver.resolve('Boston, MA, USA')
        
        assert location.city == 'Boston'
        assert location.state == 'Massachusetts'
        assert location.country == 'United States'
        assert location.timezone == 'America/New_York'
    
    def test_resolve_uk_location(self):
        """Test resolving UK location."""
        from bioleads.enrichment import LocationResolver
        
        resolver = LocationResolver()
        location = resolver.resolve('London, UK')
        
        assert location.city == 'London'
        assert location.country == 'United Kingdom'
        assert location.timezone == 'Europe/London'
    
    def test_parse_affiliation(self):
        """Test parsing affiliation string."""
        from bioleads.enrichment import LocationResolver
        
        resolver = LocationResolver()
        result = resolver.parse_affiliation(
            'Department of Biology, Harvard University, Cambridge, MA, USA'
        )
        
        assert result['department'] == 'Department of Biology'
        assert result['institution'] == 'Harvard University'
        assert result['location'] is not None
    
    def test_normalize_country(self):
        """Test country name normalization."""
        from bioleads.enrichment import LocationResolver
        
        resolver = LocationResolver()
        
        assert resolver._normalize_country('usa') == 'United States'
        assert resolver._normalize_country('UK') == 'United Kingdom'
        assert resolver._normalize_country('Deutschland') == 'Germany'


class TestCompanyEnricher:
    """Tests for CompanyEnricher class."""
    
    def test_analyze_name_academic(self):
        """Test analyzing academic institution name."""
        from bioleads.enrichment import CompanyEnricher
        
        enricher = CompanyEnricher()
        info = enricher._analyze_name('Harvard University')
        
        assert info.type == 'academic'
        assert info.name == 'Harvard University'
    
    def test_analyze_name_pharma(self):
        """Test analyzing pharma company name."""
        from bioleads.enrichment import CompanyEnricher
        
        enricher = CompanyEnricher()
        info = enricher._analyze_name('Pfizer Pharmaceuticals')
        
        assert info.type == 'pharma'
    
    def test_analyze_name_biotech(self):
        """Test analyzing biotech company name."""
        from bioleads.enrichment import CompanyEnricher
        
        enricher = CompanyEnricher()
        info = enricher._analyze_name('Moderna Biotechnology')
        
        assert info.type == 'biotech'
    
    def test_is_ideal_customer_pharma(self):
        """Test ICP evaluation for pharma."""
        from bioleads.enrichment.company_enricher import CompanyEnricher, CompanyInfo
        
        enricher = CompanyEnricher()
        
        info = CompanyInfo(
            name='Pfizer',
            type='pharma',
            size='enterprise',
            focus_areas=['drug discovery', 'toxicology'],
        )
        
        result = enricher.is_ideal_customer(info)
        
        assert result['is_ideal'] is True
        assert result['score'] > 40
    
    def test_caching(self):
        """Test that enrichment results are cached."""
        from bioleads.enrichment import CompanyEnricher
        
        enricher = CompanyEnricher()
        
        # First call
        info1 = enricher.enrich('Harvard University')
        
        # Second call should use cache
        info2 = enricher.enrich('Harvard University')
        
        assert info1.name == info2.name
        assert 'harvard university' in enricher._cache
