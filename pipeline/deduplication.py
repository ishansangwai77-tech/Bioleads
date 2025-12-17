# BioLeads Deduplication
"""
Merge and deduplicate leads from multiple sources.
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import re

try:
    from fuzzywuzzy import fuzz
except ImportError:
    fuzz = None


@dataclass
class MatchResult:
    """Result of a deduplication match."""
    is_match: bool
    confidence: float
    match_type: str  # exact, fuzzy_name, email, orcid
    
    
class Deduplicator:
    """
    Merge leads from multiple sources and remove duplicates.
    
    Matching strategies:
    1. Exact email match
    2. ORCID match
    3. Fuzzy name + institution match
    """
    
    def __init__(
        self,
        name_threshold: int = 85,
        institution_threshold: int = 70,
    ):
        """
        Initialize deduplicator.
        
        Args:
            name_threshold: Fuzzy match threshold for names (0-100)
            institution_threshold: Fuzzy match threshold for institutions
        """
        self.name_threshold = name_threshold
        self.institution_threshold = institution_threshold
        self.logger = logging.getLogger('bioleads.pipeline.deduplication')
        
        if fuzz is None:
            self.logger.warning("fuzzywuzzy not installed. Using basic matching only.")
    
    def deduplicate(self, leads: List[Dict]) -> List[Dict]:
        """
        Deduplicate a list of leads.
        
        Args:
            leads: List of lead dictionaries from various sources
            
        Returns:
            Deduplicated list with merged information
        """
        if not leads:
            return []
        
        self.logger.info(f"Deduplicating {len(leads)} leads...")
        
        # Group leads by various keys for faster matching
        email_index: Dict[str, List[int]] = {}
        orcid_index: Dict[str, List[int]] = {}
        name_index: Dict[str, List[int]] = {}
        
        for i, lead in enumerate(leads):
            # Index by email
            email = self._normalize_email(lead.get('email'))
            if email:
                if email not in email_index:
                    email_index[email] = []
                email_index[email].append(i)
            
            # Index by ORCID
            orcid = lead.get('orcid')
            if orcid:
                orcid_clean = orcid.replace('https://orcid.org/', '').strip()
                if orcid_clean not in orcid_index:
                    orcid_index[orcid_clean] = []
                orcid_index[orcid_clean].append(i)
            
            # Index by normalized name
            name_key = self._normalize_name(lead.get('name', ''))
            if name_key:
                if name_key not in name_index:
                    name_index[name_key] = []
                name_index[name_key].append(i)
        
        # Track which leads have been merged
        merged_into: Dict[int, int] = {}  # source_idx -> target_idx
        
        # Phase 1: Exact matches (email, ORCID)
        for email, indices in email_index.items():
            if len(indices) > 1:
                primary = indices[0]
                for secondary in indices[1:]:
                    if secondary not in merged_into:
                        merged_into[secondary] = primary
        
        for orcid, indices in orcid_index.items():
            if len(indices) > 1:
                primary = indices[0]
                for secondary in indices[1:]:
                    if secondary not in merged_into:
                        merged_into[secondary] = primary
        
        # Phase 2: Fuzzy name matching within same institution
        for name_key, indices in name_index.items():
            if len(indices) > 1:
                # Check institution similarity
                for i in range(len(indices)):
                    if indices[i] in merged_into:
                        continue
                    for j in range(i + 1, len(indices)):
                        if indices[j] in merged_into:
                            continue
                        
                        lead_i = leads[indices[i]]
                        lead_j = leads[indices[j]]
                        
                        match = self._check_match(lead_i, lead_j)
                        if match.is_match:
                            merged_into[indices[j]] = indices[i]
        
        # Build final list with merged data
        result = []
        processed = set()
        
        for i, lead in enumerate(leads):
            if i in processed:
                continue
            
            # Find all leads to merge into this one
            to_merge = [i]
            for source, target in merged_into.items():
                if target == i:
                    to_merge.append(source)
            
            # Merge all matching leads
            if len(to_merge) > 1:
                merged_lead = self._merge_leads([leads[idx] for idx in to_merge])
            else:
                merged_lead = lead.copy()
            
            result.append(merged_lead)
            processed.update(to_merge)
        
        self.logger.info(f"Deduplicated to {len(result)} unique leads")
        return result
    
    def _normalize_email(self, email: Optional[str]) -> Optional[str]:
        """Normalize email for comparison."""
        if not email:
            return None
        return email.lower().strip()
    
    def _normalize_name(self, name: str) -> str:
        """Normalize name for indexing."""
        if not name:
            return ''
        # Remove titles, lowercase, remove extra spaces
        name = re.sub(r'\b(Dr|Prof|PhD|MD|Jr|Sr|III|II)\.?\b', '', name, flags=re.I)
        name = ' '.join(name.lower().split())
        return name
    
    def _check_match(self, lead1: Dict, lead2: Dict) -> MatchResult:
        """Check if two leads are the same person."""
        # Exact email match
        if lead1.get('email') and lead2.get('email'):
            if self._normalize_email(lead1['email']) == self._normalize_email(lead2['email']):
                return MatchResult(True, 1.0, 'email')
        
        # ORCID match
        if lead1.get('orcid') and lead2.get('orcid'):
            orcid1 = lead1['orcid'].replace('https://orcid.org/', '')
            orcid2 = lead2['orcid'].replace('https://orcid.org/', '')
            if orcid1 == orcid2:
                return MatchResult(True, 1.0, 'orcid')
        
        # Fuzzy name + institution match
        name1 = self._normalize_name(lead1.get('name', ''))
        name2 = self._normalize_name(lead2.get('name', ''))
        
        if not name1 or not name2:
            return MatchResult(False, 0, 'none')
        
        if fuzz:
            name_score = fuzz.ratio(name1, name2)
            
            if name_score >= self.name_threshold:
                # Also check institution
                inst1 = (lead1.get('institution', '') or '').lower()
                inst2 = (lead2.get('institution', '') or '').lower()
                
                if inst1 and inst2:
                    inst_score = fuzz.ratio(inst1, inst2)
                    if inst_score >= self.institution_threshold:
                        confidence = (name_score + inst_score) / 200
                        return MatchResult(True, confidence, 'fuzzy_name_institution')
                elif name_score >= 95:  # Very high name match without institution
                    return MatchResult(True, name_score / 100, 'fuzzy_name')
        else:
            # Basic matching without fuzzywuzzy
            if name1 == name2:
                return MatchResult(True, 0.9, 'exact_name')
        
        return MatchResult(False, 0, 'none')
    
    def _merge_leads(self, leads: List[Dict]) -> Dict:
        """Merge multiple lead records into one."""
        if not leads:
            return {}
        
        merged = leads[0].copy()
        sources = [leads[0].get('source', 'unknown')]
        
        for lead in leads[1:]:
            sources.append(lead.get('source', 'unknown'))
            
            # Merge fields - prefer non-empty values
            for key in ['email', 'title', 'department', 'orcid', 'location']:
                if not merged.get(key) and lead.get(key):
                    merged[key] = lead[key]
            
            # Merge lists
            for key in ['research_focus', 'grants']:
                if lead.get(key):
                    existing = merged.get(key, [])
                    if isinstance(existing, list):
                        # Handle lists that may contain dicts (unhashable)
                        combined = existing + lead[key]
                        # For simple strings, dedupe; for dicts, just combine
                        if combined and isinstance(combined[0], dict):
                            merged[key] = combined  # Keep all grants
                        else:
                            merged[key] = list(set(str(x) for x in combined))  # Dedupe strings
                    else:
                        merged[key] = lead[key]
            
            # Sum counts
            if lead.get('publications'):
                merged['publications'] = merged.get('publications', 0) + lead.get('publications', 0)
            if lead.get('cited_by_count'):
                merged['cited_by_count'] = max(
                    merged.get('cited_by_count', 0),
                    lead.get('cited_by_count', 0)
                )
            
            # Merge raw data
            if 'raw_data_sources' not in merged:
                merged['raw_data_sources'] = {}
            if lead.get('source') and lead.get('raw_data'):
                merged['raw_data_sources'][lead['source']] = lead['raw_data']
        
        merged['sources'] = list(set(sources))
        merged['source_count'] = len(merged['sources'])
        
        return merged
