# BioLeads Company Enricher
"""
Enrich company/institution data using free public sources.
"""

import logging
import re
from typing import Dict, List, Optional
from dataclasses import dataclass, field

import requests


@dataclass
class CompanyInfo:
    """Enriched company information."""
    name: str
    type: str = ''  # academic, pharma, biotech, cro, etc.
    size: str = ''  # small, medium, large, enterprise
    website: Optional[str] = None
    founded: Optional[int] = None
    description: Optional[str] = None
    focus_areas: List[str] = field(default_factory=list)
    is_public: bool = False
    parent_company: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'type': self.type,
            'size': self.size,
            'website': self.website,
            'founded': self.founded,
            'description': self.description,
            'focus_areas': self.focus_areas,
            'is_public': self.is_public,
            'parent_company': self.parent_company,
        }


class CompanyEnricher:
    """
    Enrich company/institution information using free sources.
    
    Sources:
    - OpenAlex institutions API
    - Wikipedia/Wikidata
    - SEC EDGAR (for public companies)
    - Domain-based inference
    """
    
    # Company type indicators
    TYPE_INDICATORS = {
        'academic': ['university', 'college', 'institute of technology', 'school of medicine', 'medical school', 'research institute'],
        'medical_center': ['hospital', 'medical center', 'medical centre', 'clinic', 'health system'],
        'pharma': ['pharmaceutical', 'pharma'],
        'biotech': ['biotechnology', 'biotech', 'biosciences', 'biopharmaceutical', 'biologics'],
        'cro': ['contract research', 'cro ', 'clinical research organization', 'preclinical services'],
        'cdmo': ['contract manufacturing', 'cdmo', 'drug manufacturing'],
        'government': ['nih', 'fda', 'cdc', 'national institute', 'federal', 'government'],
        'nonprofit': ['foundation', 'nonprofit', 'non-profit', 'ngo'],
    }
    
    # Size indicators (rough employee count estimates)
    SIZE_MAP = {
        'small': (1, 50),
        'medium': (51, 500),
        'large': (501, 5000),
        'enterprise': (5001, None),
    }
    
    # Known major pharma companies
    MAJOR_PHARMA = [
        'pfizer', 'novartis', 'roche', 'merck', 'johnson & johnson', 'sanofi',
        'astrazeneca', 'gsk', 'glaxosmithkline', 'abbvie', 'eli lilly', 'bristol-myers squibb',
        'amgen', 'gilead', 'biogen', 'regeneron', 'bayer', 'takeda', 'novo nordisk',
        'boehringer ingelheim', 'astellas', 'daiichi sankyo', 'otsuka',
    ]
    
    def __init__(self):
        """Initialize company enricher."""
        self.logger = logging.getLogger('bioleads.enrichment.company_enricher')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'BioLeads/1.0 (Research Lead Generation)',
        })
        
        # Cache for enriched companies
        self._cache: Dict[str, CompanyInfo] = {}
    
    def enrich(self, institution_name: str) -> CompanyInfo:
        """
        Enrich institution/company information.
        
        Args:
            institution_name: Name of institution or company
            
        Returns:
            Enriched CompanyInfo
        """
        if not institution_name:
            return CompanyInfo(name='Unknown')
        
        # Check cache
        cache_key = institution_name.lower().strip()
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Basic enrichment from name analysis
        info = self._analyze_name(institution_name)
        
        # Try OpenAlex for academic institutions
        if info.type in ['academic', 'medical_center', 'government']:
            openalex_info = self._lookup_openalex(institution_name)
            if openalex_info:
                info = self._merge_info(info, openalex_info)
        
        # Cache and return
        self._cache[cache_key] = info
        return info
    
    def _analyze_name(self, name: str) -> CompanyInfo:
        """Analyze institution name to infer properties."""
        name_lower = name.lower()
        
        # Determine type
        inst_type = 'unknown'
        for type_name, indicators in self.TYPE_INDICATORS.items():
            if any(ind in name_lower for ind in indicators):
                inst_type = type_name
                break
        
        # Check if major pharma
        if any(pharma in name_lower for pharma in self.MAJOR_PHARMA):
            inst_type = 'pharma'
        
        # Infer size
        if inst_type in ['pharma', 'enterprise']:
            size = 'enterprise'
        elif inst_type in ['academic', 'medical_center']:
            size = 'large'
        elif inst_type == 'biotech':
            size = 'medium'
        else:
            size = 'medium'
        
        # Try to extract website from name
        website = self._guess_website(name, inst_type)
        
        return CompanyInfo(
            name=name,
            type=inst_type,
            size=size,
            website=website,
        )
    
    def _guess_website(self, name: str, inst_type: str) -> Optional[str]:
        """Guess website URL from institution name."""
        # Clean name
        clean_name = re.sub(r'[^a-z0-9\s]', '', name.lower())
        words = clean_name.split()
        
        if not words:
            return None
        
        # For academic, use .edu
        if inst_type == 'academic':
            # Try common patterns
            if 'university of' in name.lower():
                # "University of California" -> ucla.edu, berkeley.edu, etc.
                # Hard to determine, return None
                return None
            else:
                # "Stanford University" -> stanford.edu
                return f"https://www.{words[0]}.edu"
        
        # For companies, use .com
        return f"https://www.{words[0]}.com"
    
    def _lookup_openalex(self, institution_name: str) -> Optional[CompanyInfo]:
        """Look up institution in OpenAlex."""
        try:
            params = {
                'search': institution_name,
                'per_page': 1,
            }
            
            response = self.session.get(
                'https://api.openalex.org/institutions',
                params=params,
                timeout=10,
            )
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                if results:
                    inst = results[0]
                    
                    # Determine type from OpenAlex categories
                    inst_type = 'academic'
                    openalex_type = inst.get('type', '').lower()
                    if 'company' in openalex_type:
                        inst_type = 'biotech'
                    elif 'government' in openalex_type:
                        inst_type = 'government'
                    elif 'healthcare' in openalex_type:
                        inst_type = 'medical_center'
                    elif 'nonprofit' in openalex_type:
                        inst_type = 'nonprofit'
                    
                    # Get works count as size indicator
                    works_count = inst.get('works_count', 0)
                    if works_count > 100000:
                        size = 'enterprise'
                    elif works_count > 10000:
                        size = 'large'
                    elif works_count > 1000:
                        size = 'medium'
                    else:
                        size = 'small'
                    
                    # Get concepts as focus areas
                    concepts = inst.get('x_concepts', [])
                    focus_areas = [c.get('display_name', '') for c in concepts[:10]]
                    
                    return CompanyInfo(
                        name=inst.get('display_name', institution_name),
                        type=inst_type,
                        size=size,
                        website=inst.get('homepage_url'),
                        description=inst.get('description'),
                        focus_areas=focus_areas,
                    )
                    
        except Exception as e:
            self.logger.debug(f"OpenAlex lookup failed for {institution_name}: {e}")
        
        return None
    
    def _merge_info(self, base: CompanyInfo, additional: CompanyInfo) -> CompanyInfo:
        """Merge two CompanyInfo objects."""
        return CompanyInfo(
            name=additional.name or base.name,
            type=additional.type if additional.type != 'unknown' else base.type,
            size=additional.size or base.size,
            website=additional.website or base.website,
            founded=additional.founded or base.founded,
            description=additional.description or base.description,
            focus_areas=additional.focus_areas or base.focus_areas,
            is_public=additional.is_public or base.is_public,
            parent_company=additional.parent_company or base.parent_company,
        )
    
    def is_ideal_customer(self, info: CompanyInfo) -> Dict:
        """
        Evaluate if company matches ideal customer profile.
        
        Returns score and reasons.
        """
        score = 0
        reasons = []
        
        # Type scoring
        type_scores = {
            'pharma': 30,
            'biotech': 25,
            'cro': 20,
            'medical_center': 15,
            'academic': 15,
            'cdmo': 10,
            'government': 10,
        }
        type_score = type_scores.get(info.type, 0)
        score += type_score
        if type_score > 0:
            reasons.append(f"Industry type: {info.type} (+{type_score})")
        
        # Size scoring
        size_scores = {
            'enterprise': 20,
            'large': 15,
            'medium': 10,
            'small': 5,
        }
        size_score = size_scores.get(info.size, 0)
        score += size_score
        if size_score > 0:
            reasons.append(f"Company size: {info.size} (+{size_score})")
        
        # Focus area scoring
        relevant_focus = ['drug discovery', 'toxicology', 'pharmacology', 
                         'cell biology', 'cancer research', 'stem cell']
        focus_matches = [f for f in info.focus_areas 
                        if any(r in f.lower() for r in relevant_focus)]
        focus_score = min(len(focus_matches) * 5, 20)
        score += focus_score
        if focus_score > 0:
            reasons.append(f"Relevant focus areas: {len(focus_matches)} (+{focus_score})")
        
        return {
            'score': score,
            'max_score': 70,
            'percentage': round(score / 70 * 100),
            'reasons': reasons,
            'is_ideal': score >= 40,
        }
    
    def batch_enrich(self, leads: List[Dict]) -> List[Dict]:
        """
        Enrich institution data for a batch of leads.
        
        Args:
            leads: List of lead dictionaries
            
        Returns:
            Updated leads with company info
        """
        for lead in leads:
            institution = lead.get('institution', '')
            
            if institution:
                company_info = self.enrich(institution)
                lead['company_info'] = company_info.to_dict()
                
                # Evaluate ICP fit
                icp_eval = self.is_ideal_customer(company_info)
                lead['icp_score'] = icp_eval['score']
                lead['icp_match'] = icp_eval['is_ideal']
        
        return leads
