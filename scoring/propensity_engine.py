# BioLeads Propensity Engine
"""
Main scoring algorithm for lead propensity-to-buy calculation.
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

from .weights import ScoringWeights, default_weights


@dataclass
class ScoreBreakdown:
    """Detailed breakdown of a lead's score."""
    total_score: float
    tier: str  # hot, warm, cold
    publication_score: float
    grant_score: float
    clinical_trial_score: float
    citation_score: float
    conference_score: float
    recency_score: float
    role_score: float
    institution_score: float
    topic_score: float
    factors: List[str]  # Key scoring factors
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'total_score': round(self.total_score, 1),
            'tier': self.tier,
            'breakdown': {
                'publication': round(self.publication_score, 2),
                'grant': round(self.grant_score, 2),
                'clinical_trial': round(self.clinical_trial_score, 2),
                'citation': round(self.citation_score, 2),
                'conference': round(self.conference_score, 2),
                'recency': round(self.recency_score, 2),
                'role_fit': round(self.role_score, 2),
                'institution_fit': round(self.institution_score, 2),
                'topic_relevance': round(self.topic_score, 2),
            },
            'key_factors': self.factors,
        }


class PropensityEngine:
    """
    Lead scoring engine that calculates propensity-to-buy scores.
    
    Scoring factors:
    - Research Activity: publications, grants, clinical trials, citations
    - Engagement: conference presence, recent activity
    - Fit: role match, institution type, research focus
    """
    
    def __init__(self, weights: Optional[ScoringWeights] = None):
        """
        Initialize propensity engine.
        
        Args:
            weights: Custom scoring weights (uses defaults if not provided)
        """
        self.weights = weights or default_weights
        self.logger = logging.getLogger('bioleads.scoring.propensity')
    
    def score_lead(self, lead: Dict) -> ScoreBreakdown:
        """
        Calculate propensity score for a single lead.
        
        Args:
            lead: Lead dictionary with enriched data
            
        Returns:
            ScoreBreakdown with detailed scoring
        """
        factors = []
        
        # 1. Publication Score
        pub_score, pub_factors = self._score_publications(lead)
        factors.extend(pub_factors)
        
        # 2. Grant Score
        grant_score, grant_factors = self._score_grants(lead)
        factors.extend(grant_factors)
        
        # 3. Clinical Trial Score
        trial_score, trial_factors = self._score_clinical_trials(lead)
        factors.extend(trial_factors)
        
        # 4. Citation Score
        citation_score = self._score_citations(lead)
        
        # 5. Conference Score
        conf_score, conf_factors = self._score_conference(lead)
        factors.extend(conf_factors)
        
        # 6. Recency Score
        recency_score = self._score_recency(lead)
        if recency_score > 5:
            factors.append("Recent research activity")
        
        # 7. Role Fit Score
        role_score = self.weights.get_role_score(lead.get('title', ''))
        if role_score > 5:
            factors.append(f"Decision-maker role: {lead.get('title')}")
        
        # 8. Institution Fit Score
        inst_score = self._score_institution(lead)
        if inst_score > 5:
            factors.append(f"Strong institution fit: {lead.get('institution')}")
        
        # 9. Topic Relevance Score
        topic_score = self.weights.get_topic_relevance_score(
            lead.get('research_focus', [])
        )
        if topic_score > 5:
            factors.append("Highly relevant research focus")
        
        # Calculate total
        total_score = (
            pub_score +
            grant_score +
            trial_score +
            citation_score +
            conf_score +
            recency_score +
            role_score +
            inst_score +
            topic_score
        )
        
        # Determine tier
        tier = self._determine_tier(total_score)
        
        return ScoreBreakdown(
            total_score=min(100, total_score),  # Cap at 100
            tier=tier,
            publication_score=pub_score,
            grant_score=grant_score,
            clinical_trial_score=trial_score,
            citation_score=citation_score,
            conference_score=conf_score,
            recency_score=recency_score,
            role_score=role_score,
            institution_score=inst_score,
            topic_score=topic_score,
            factors=factors[:5],  # Top 5 factors
        )
    
    def _score_publications(self, lead: Dict) -> Tuple[float, List[str]]:
        """Score based on publication activity."""
        factors = []
        pub_count = lead.get('publications', 0)
        
        # Get thresholds from weights
        thresholds = self.weights.pub_score_thresholds
        
        # Calculate score as percentage of weight
        if pub_count >= thresholds['excellent']:
            score_pct = 1.0
            factors.append(f"Highly active researcher ({pub_count}+ publications)")
        elif pub_count >= thresholds['good']:
            score_pct = 0.75
            factors.append(f"Active researcher ({pub_count} publications)")
        elif pub_count >= thresholds['moderate']:
            score_pct = 0.5
        elif pub_count >= thresholds['minimal']:
            score_pct = 0.25
        else:
            score_pct = 0
        
        score = score_pct * self.weights.publication_weight
        
        return score, factors
    
    def _score_grants(self, lead: Dict) -> Tuple[float, List[str]]:
        """Score based on grant funding."""
        factors = []
        grants = lead.get('grants', [])
        
        if not grants:
            return 0, factors
        
        total_amount = sum(g.get('award_amount', 0) for g in grants)
        thresholds = self.weights.grant_amount_thresholds
        
        # Score based on total funding
        if total_amount >= thresholds['major']:
            score_pct = 1.0
            factors.append(f"Major funding: ${total_amount:,.0f}")
        elif total_amount >= thresholds['significant']:
            score_pct = 0.75
            factors.append(f"Significant funding: ${total_amount:,.0f}")
        elif total_amount >= thresholds['moderate']:
            score_pct = 0.5
        elif total_amount >= thresholds['seed']:
            score_pct = 0.25
        else:
            score_pct = 0.1
        
        score = score_pct * self.weights.grant_weight
        
        # Bonus for active grants
        active_grants = [g for g in grants if self._is_grant_active(g)]
        if len(active_grants) >= 2:
            score = min(score * 1.2, self.weights.grant_weight)
            factors.append(f"{len(active_grants)} active grants")
        
        return score, factors
    
    def _is_grant_active(self, grant: Dict) -> bool:
        """Check if a grant is currently active."""
        end_date = grant.get('end_date')
        if not end_date:
            return True  # Assume active if no end date
        
        try:
            if isinstance(end_date, str):
                # Parse various date formats
                for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%Y']:
                    try:
                        end_dt = datetime.strptime(end_date[:10], fmt)
                        return end_dt > datetime.now()
                    except ValueError:
                        continue
        except Exception:
            pass
        
        return True
    
    def _score_clinical_trials(self, lead: Dict) -> Tuple[float, List[str]]:
        """Score based on clinical trial involvement."""
        factors = []
        
        trial_info = lead.get('clinical_trial', {})
        if not trial_info:
            return 0, factors
        
        # Base score for having clinical trial involvement
        score = self.weights.clinical_trial_weight * 0.5
        
        # Bonus for industry-sponsored trials
        sponsor_class = lead.get('sponsor_class', '')
        if sponsor_class == 'INDUSTRY':
            score = self.weights.clinical_trial_weight
            factors.append("Industry-sponsored clinical trial")
        else:
            factors.append("Clinical trial involvement")
        
        return score, factors
    
    def _score_citations(self, lead: Dict) -> float:
        """Score based on citation impact."""
        cited_by = lead.get('cited_by_count', 0)
        
        if cited_by >= 1000:
            return self.weights.citation_weight
        elif cited_by >= 500:
            return self.weights.citation_weight * 0.75
        elif cited_by >= 100:
            return self.weights.citation_weight * 0.5
        elif cited_by >= 50:
            return self.weights.citation_weight * 0.25
        
        return 0
    
    def _score_conference(self, lead: Dict) -> Tuple[float, List[str]]:
        """Score based on conference presentation."""
        factors = []
        
        conf_info = lead.get('conference_presentation', {})
        if not conf_info:
            return 0, factors
        
        score = self.weights.conference_weight * 0.7
        factors.append(f"Presented at {conf_info.get('conference', 'conference')}")
        
        # Bonus for keynote/symposium
        session_type = conf_info.get('session_type', '')
        if session_type in ['keynote', 'symposium']:
            score = self.weights.conference_weight
            factors[-1] = f"Keynote/symposium at {conf_info.get('conference', 'conference')}"
        
        return score, factors
    
    def _score_recency(self, lead: Dict) -> float:
        """Score based on how recent the activity is."""
        # Check various date fields
        date_fields = ['pub_date', 'publication_date']
        
        for field in date_fields:
            date_val = lead.get(field)
            if date_val:
                try:
                    if isinstance(date_val, str):
                        year = int(date_val[:4])
                        current_year = datetime.now().year
                        years_ago = current_year - year
                        
                        if years_ago <= 1:
                            return self.weights.recent_activity_weight
                        elif years_ago <= 2:
                            return self.weights.recent_activity_weight * 0.75
                        elif years_ago <= 3:
                            return self.weights.recent_activity_weight * 0.5
                except (ValueError, IndexError):
                    continue
        
        return 0
    
    def _score_institution(self, lead: Dict) -> float:
        """Score based on institution fit."""
        # Use ICP score if available from company enricher
        icp_score = lead.get('icp_score', 0)
        if icp_score:
            return (icp_score / 70) * self.weights.institution_fit_weight
        
        # Fallback: analyze institution type from company_info
        company_info = lead.get('company_info', {})
        inst_type = company_info.get('type', '')
        
        type_scores = {
            'pharma': 1.0,
            'biotech': 0.9,
            'cro': 0.8,
            'medical_center': 0.6,
            'academic': 0.5,
            'government': 0.4,
        }
        
        score_pct = type_scores.get(inst_type, 0.3)
        return score_pct * self.weights.institution_fit_weight
    
    def _determine_tier(self, score: float) -> str:
        """Determine lead tier based on score."""
        if score >= self.weights.hot_threshold:
            return 'hot'
        elif score >= self.weights.warm_threshold:
            return 'warm'
        elif score >= self.weights.cold_threshold:
            return 'cold'
        else:
            return 'ice'
    
    def score_batch(self, leads: List[Dict]) -> List[Dict]:
        """
        Score a batch of leads and add score information.
        
        Args:
            leads: List of lead dictionaries
            
        Returns:
            Leads with added score information
        """
        for lead in leads:
            score_breakdown = self.score_lead(lead)
            lead['score'] = score_breakdown.total_score
            lead['tier'] = score_breakdown.tier
            lead['score_breakdown'] = score_breakdown.to_dict()
        
        # Sort by score descending
        leads.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        return leads
    
    def get_tier_summary(self, leads: List[Dict]) -> Dict:
        """Get summary of leads by tier."""
        tiers = {'hot': 0, 'warm': 0, 'cold': 0, 'ice': 0}
        
        for lead in leads:
            tier = lead.get('tier', 'ice')
            tiers[tier] = tiers.get(tier, 0) + 1
        
        return {
            'total': len(leads),
            'by_tier': tiers,
            'hot_percentage': round(tiers['hot'] / len(leads) * 100, 1) if leads else 0,
        }
