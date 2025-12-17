# Tests for scoring
"""Unit tests for BioLeads scoring engine."""

import pytest


class TestScoringWeights:
    """Tests for ScoringWeights configuration."""
    
    def test_default_weights_validate(self):
        """Test that default weights sum to 100."""
        from bioleads.scoring import ScoringWeights
        
        weights = ScoringWeights()
        
        # Should validate (sum to 100)
        assert weights.validate()
    
    def test_get_role_score(self):
        """Test role scoring."""
        from bioleads.scoring import ScoringWeights
        
        weights = ScoringWeights()
        
        # High priority roles
        assert weights.get_role_score('Chief Scientific Officer') > 5
        assert weights.get_role_score('Principal Investigator') > 5
        assert weights.get_role_score('Director of Research') > 5
        
        # Lower priority / unknown
        assert weights.get_role_score('Research Assistant') < 5
        assert weights.get_role_score('Unknown Role') == 0
    
    def test_get_topic_relevance_score(self):
        """Test topic relevance scoring."""
        from bioleads.scoring import ScoringWeights
        
        weights = ScoringWeights()
        
        # Highly relevant topics
        high_score = weights.get_topic_relevance_score(['organoid', '3D cell culture'])
        
        # Less relevant topics
        low_score = weights.get_topic_relevance_score(['general biology'])
        
        assert high_score > low_score
    
    def test_to_dict_from_dict(self):
        """Test serialization/deserialization."""
        from bioleads.scoring import ScoringWeights
        
        original = ScoringWeights(publication_weight=20.0)
        data = original.to_dict()
        restored = ScoringWeights.from_dict(data)
        
        assert restored.publication_weight == 20.0


class TestPropensityEngine:
    """Tests for PropensityEngine scoring."""
    
    def test_score_lead_basic(self):
        """Test basic lead scoring."""
        from bioleads.scoring import PropensityEngine
        
        engine = PropensityEngine()
        
        lead = {
            'name': 'Dr. Jane Smith',
            'title': 'Principal Investigator',
            'institution': 'Harvard University',
            'publications': 20,
            'grants': [{'award_amount': 500000}],
            'research_focus': ['organoid', '3D cell culture', 'drug screening'],
            'pub_date': '2024',
        }
        
        score = engine.score_lead(lead)
        
        assert score.total_score > 0
        assert score.tier in ['hot', 'warm', 'cold', 'ice']
        assert len(score.factors) > 0
    
    def test_score_lead_empty(self):
        """Test scoring empty lead."""
        from bioleads.scoring import PropensityEngine
        
        engine = PropensityEngine()
        
        lead = {'name': 'Unknown', 'institution': 'Unknown'}
        score = engine.score_lead(lead)
        
        assert score.total_score >= 0
        assert score.tier in ['ice', 'cold']
    
    def test_score_lead_hot(self):
        """Test that highly qualified leads score as hot."""
        from bioleads.scoring import PropensityEngine
        
        engine = PropensityEngine()
        
        lead = {
            'name': 'Dr. Jane Smith',
            'title': 'Chief Scientific Officer',
            'institution': 'Pfizer',
            'publications': 50,
            'cited_by_count': 2000,
            'grants': [
                {'award_amount': 1000000, 'end_date': '2026-12-31'},
                {'award_amount': 500000, 'end_date': '2025-12-31'},
            ],
            'research_focus': ['organoid', '3D cell culture', 'drug screening', 'toxicology'],
            'pub_date': '2024',
            'company_info': {'type': 'pharma'},
            'icp_score': 60,
        }
        
        score = engine.score_lead(lead)
        
        assert score.tier == 'hot'
        assert score.total_score >= 75
    
    def test_determine_tier(self):
        """Test tier determination."""
        from bioleads.scoring import PropensityEngine
        
        engine = PropensityEngine()
        
        assert engine._determine_tier(80) == 'hot'
        assert engine._determine_tier(60) == 'warm'
        assert engine._determine_tier(40) == 'cold'
        assert engine._determine_tier(10) == 'ice'
    
    def test_score_batch(self):
        """Test batch scoring."""
        from bioleads.scoring import PropensityEngine
        
        engine = PropensityEngine()
        
        leads = [
            {'name': 'Lead 1', 'publications': 10, 'research_focus': ['organoid']},
            {'name': 'Lead 2', 'publications': 5, 'research_focus': ['other']},
            {'name': 'Lead 3', 'publications': 20, 'title': 'Director', 'research_focus': ['3D culture']},
        ]
        
        scored = engine.score_batch(leads)
        
        # Should be sorted by score (descending)
        assert scored[0]['score'] >= scored[1]['score']
        assert scored[1]['score'] >= scored[2]['score']
        
        # All should have score and tier
        for lead in scored:
            assert 'score' in lead
            assert 'tier' in lead
    
    def test_get_tier_summary(self):
        """Test tier summary statistics."""
        from bioleads.scoring import PropensityEngine
        
        engine = PropensityEngine()
        
        leads = [
            {'tier': 'hot', 'score': 85},
            {'tier': 'hot', 'score': 80},
            {'tier': 'warm', 'score': 60},
            {'tier': 'cold', 'score': 30},
        ]
        
        summary = engine.get_tier_summary(leads)
        
        assert summary['total'] == 4
        assert summary['by_tier']['hot'] == 2
        assert summary['by_tier']['warm'] == 1
        assert summary['by_tier']['cold'] == 1


class TestDeduplicator:
    """Tests for lead deduplication."""
    
    def test_deduplicate_by_email(self):
        """Test deduplication by email match."""
        from bioleads.pipeline import Deduplicator
        
        dedup = Deduplicator()
        
        leads = [
            {'name': 'John Doe', 'email': 'jdoe@example.com', 'source': 'pubmed'},
            {'name': 'John D.', 'email': 'jdoe@example.com', 'source': 'nih'},
        ]
        
        result = dedup.deduplicate(leads)
        
        assert len(result) == 1
        assert 'pubmed' in result[0]['sources']
        assert 'nih' in result[0]['sources']
    
    def test_deduplicate_by_orcid(self):
        """Test deduplication by ORCID match."""
        from bioleads.pipeline import Deduplicator
        
        dedup = Deduplicator()
        
        leads = [
            {'name': 'John Doe', 'orcid': '0000-0001-2345-6789', 'source': 'pubmed'},
            {'name': 'J. Doe', 'orcid': '0000-0001-2345-6789', 'source': 'openalex'},
        ]
        
        result = dedup.deduplicate(leads)
        
        assert len(result) == 1
    
    def test_normalize_name(self):
        """Test name normalization."""
        from bioleads.pipeline import Deduplicator
        
        dedup = Deduplicator()
        
        # Should remove titles and normalize
        assert dedup._normalize_name('Dr. John Doe') == 'john doe'
        assert dedup._normalize_name('Prof. Jane Smith PhD') == 'jane smith'
        assert dedup._normalize_name('John   Doe') == 'john doe'
    
    def test_merge_leads(self):
        """Test lead merging."""
        from bioleads.pipeline import Deduplicator
        
        dedup = Deduplicator()
        
        leads = [
            {'name': 'John Doe', 'email': 'jdoe@example.com', 'publications': 5, 'source': 'pubmed'},
            {'name': 'John Doe', 'title': 'PI', 'publications': 3, 'source': 'nih'},
        ]
        
        merged = dedup._merge_leads(leads)
        
        assert merged['email'] == 'jdoe@example.com'
        assert merged['title'] == 'PI'
        assert merged['publications'] == 8  # Sum
        assert len(merged['sources']) == 2
