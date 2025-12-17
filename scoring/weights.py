# BioLeads Scoring Weights
"""
Configurable weight system for lead scoring.
"""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class ScoringWeights:
    """
    Configurable weights for lead scoring.
    
    All weights should be 0-100 and represent the maximum
    contribution of each factor to the total score.
    Total maximum score is 100.
    """
    
    # Research Activity Weights (max contribution to score)
    publication_weight: float = 15.0  # Recent publications in relevant topics
    grant_weight: float = 20.0  # Active grant funding
    clinical_trial_weight: float = 10.0  # Clinical trial involvement
    citation_weight: float = 5.0  # Citation impact
    
    # Engagement Signals
    conference_weight: float = 10.0  # Conference presentations
    recent_activity_weight: float = 10.0  # Activity in last 2 years
    
    # Fit/Match Weights
    role_fit_weight: float = 10.0  # Job title match
    institution_fit_weight: float = 10.0  # ICP match
    research_focus_weight: float = 10.0  # Topic relevance
    
    # Scoring parameters
    publication_recency_years: int = 3  # Publications within X years
    grant_min_amount: float = 100000  # Minimum grant amount to score
    
    # Tier thresholds
    hot_threshold: float = 75.0
    warm_threshold: float = 50.0
    cold_threshold: float = 25.0
    
    # Publication scoring parameters
    pub_score_thresholds: Dict[str, int] = field(default_factory=lambda: {
        'excellent': 10,  # 10+ publications = max score
        'good': 5,       # 5-9 publications
        'moderate': 2,   # 2-4 publications
        'minimal': 1,    # 1 publication
    })
    
    # Grant scoring parameters
    grant_amount_thresholds: Dict[str, float] = field(default_factory=lambda: {
        'major': 1000000,    # $1M+ 
        'significant': 500000,  # $500K-1M
        'moderate': 250000,   # $250K-500K
        'seed': 100000,       # $100K-250K
    })
    
    # Target job titles (for role fit)
    target_titles_priority: Dict[str, int] = field(default_factory=lambda: {
        # Decision makers (highest priority)
        'chief scientific officer': 100,
        'cso': 100,
        'vp research': 95,
        'vice president': 90,
        'director': 85,
        'head of': 85,
        
        # Research leads
        'principal investigator': 80,
        'pi': 80,
        'group leader': 75,
        'lab director': 75,
        
        # Senior researchers
        'senior scientist': 70,
        'staff scientist': 65,
        'research scientist': 60,
        'associate director': 70,
        
        # Specialists
        'toxicologist': 65,
        'pharmacologist': 65,
        'cell biologist': 60,
        
        # Operations
        'lab manager': 55,
        'procurement': 50,
    })
    
    # Research topic relevance scores
    topic_relevance: Dict[str, int] = field(default_factory=lambda: {
        # Highly relevant (100%)
        '3d cell culture': 100,
        'organoid': 100,
        'spheroid': 100,
        'organ-on-chip': 100,
        'microphysiological': 100,
        
        # Very relevant (80%)
        'in vitro toxicology': 80,
        'drug screening': 80,
        'hepatotoxicity': 80,
        'dili': 80,
        'tissue engineering': 80,
        
        # Relevant (60%)
        'drug discovery': 60,
        'pharmacology': 60,
        'toxicology': 60,
        'cell culture': 60,
        'high-throughput': 60,
        
        # Somewhat relevant (40%)
        'cancer research': 40,
        'stem cell': 40,
        'regenerative medicine': 40,
        'biomarker': 40,
    })
    
    def validate(self) -> bool:
        """Validate that all weights sum appropriately."""
        total = (
            self.publication_weight +
            self.grant_weight +
            self.clinical_trial_weight +
            self.citation_weight +
            self.conference_weight +
            self.recent_activity_weight +
            self.role_fit_weight +
            self.institution_fit_weight +
            self.research_focus_weight
        )
        return abs(total - 100.0) < 0.01
    
    def get_role_score(self, title: str) -> float:
        """Get role fit score for a job title."""
        if not title:
            return 0.0
        
        title_lower = title.lower()
        
        # Check for exact or partial matches
        best_score = 0
        for target, score in self.target_titles_priority.items():
            if target in title_lower:
                best_score = max(best_score, score)
        
        # Normalize to weight
        return (best_score / 100) * self.role_fit_weight
    
    def get_topic_relevance_score(self, topics: List[str]) -> float:
        """Get research focus score based on topic relevance."""
        if not topics:
            return 0.0
        
        total_relevance = 0
        for topic in topics:
            topic_lower = topic.lower()
            for keyword, score in self.topic_relevance.items():
                if keyword in topic_lower or topic_lower in keyword:
                    total_relevance += score
                    break
        
        # Normalize: average relevance capped at max weight
        avg_relevance = total_relevance / len(topics) if topics else 0
        return min((avg_relevance / 100) * self.research_focus_weight, self.research_focus_weight)
    
    def to_dict(self) -> Dict:
        """Convert weights to dictionary."""
        return {
            'publication_weight': self.publication_weight,
            'grant_weight': self.grant_weight,
            'clinical_trial_weight': self.clinical_trial_weight,
            'citation_weight': self.citation_weight,
            'conference_weight': self.conference_weight,
            'recent_activity_weight': self.recent_activity_weight,
            'role_fit_weight': self.role_fit_weight,
            'institution_fit_weight': self.institution_fit_weight,
            'research_focus_weight': self.research_focus_weight,
            'hot_threshold': self.hot_threshold,
            'warm_threshold': self.warm_threshold,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ScoringWeights':
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})


# Default weights instance
default_weights = ScoringWeights()
