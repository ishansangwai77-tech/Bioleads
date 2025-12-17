# BioLeads Email Finder
"""
Email discovery and pattern matching for lead enrichment.
Uses free methods: pattern generation, web scraping, ORCID lookup.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

import requests


@dataclass
class EmailPattern:
    """Email pattern template."""
    name: str
    pattern: str  # e.g., "{first}.{last}", "{f}{last}"
    confidence: float  # 0.0 - 1.0
    
    def generate(self, first_name: str, last_name: str, domain: str) -> str:
        """Generate email from pattern."""
        first = first_name.lower().strip()
        last = last_name.lower().strip()
        f = first[0] if first else ''
        l = last[0] if last else ''
        
        email_local = (
            self.pattern
            .replace('{first}', first)
            .replace('{last}', last)
            .replace('{f}', f)
            .replace('{l}', l)
        )
        
        # Clean up any special characters
        email_local = re.sub(r'[^a-z0-9._-]', '', email_local)
        
        return f"{email_local}@{domain}"


# Common academic/corporate email patterns
COMMON_PATTERNS = [
    EmailPattern('first.last', '{first}.{last}', 0.85),
    EmailPattern('firstlast', '{first}{last}', 0.75),
    EmailPattern('flast', '{f}{last}', 0.80),
    EmailPattern('first_last', '{first}_{last}', 0.65),
    EmailPattern('lastf', '{last}{f}', 0.60),
    EmailPattern('first', '{first}', 0.50),
    EmailPattern('last.first', '{last}.{first}', 0.55),
    EmailPattern('firstl', '{first}{l}', 0.45),
]


class EmailFinder:
    """
    Email discovery service using free methods.
    
    Methods:
    1. Pattern generation based on common formats
    2. ORCID profile lookup
    3. Institution website scraping
    4. PubMed author search
    """
    
    def __init__(self):
        """Initialize email finder."""
        self.logger = logging.getLogger('bioleads.enrichment.email_finder')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'BioLeads/1.0 (Research Lead Generation)',
        })
        
        # Cache for domain patterns
        self._domain_patterns: Dict[str, EmailPattern] = {}
    
    def find_email(
        self,
        first_name: str,
        last_name: str,
        institution: str,
        orcid: Optional[str] = None,
    ) -> Optional[Dict]:
        """
        Attempt to find email for a person.
        
        Args:
            first_name: Person's first name
            last_name: Person's last name
            institution: Institution/company name
            orcid: Optional ORCID identifier
            
        Returns:
            Dict with email and confidence, or None
        """
        # Method 1: ORCID lookup (most reliable if available)
        if orcid:
            email = self._lookup_orcid(orcid)
            if email:
                return {'email': email, 'confidence': 0.95, 'source': 'orcid'}
        
        # Method 2: Domain-based pattern generation
        domain = self._get_institution_domain(institution)
        if domain:
            candidates = self._generate_email_candidates(first_name, last_name, domain)
            
            # Return best candidate (could implement verification here)
            if candidates:
                best = candidates[0]
                return {
                    'email': best['email'],
                    'confidence': best['confidence'],
                    'source': 'pattern',
                    'alternatives': candidates[1:5],  # Top 5 alternatives
                }
        
        return None
    
    def _lookup_orcid(self, orcid: str) -> Optional[str]:
        """
        Look up email from ORCID public profile.
        
        Args:
            orcid: ORCID identifier (e.g., "0000-0001-2345-6789")
            
        Returns:
            Email if found, None otherwise
        """
        try:
            # Clean ORCID format
            orcid_id = orcid.replace('https://orcid.org/', '').strip()
            
            url = f"https://pub.orcid.org/v3.0/{orcid_id}/person"
            headers = {'Accept': 'application/json'}
            
            response = self.session.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check emails in profile
                emails = data.get('emails', {}).get('email', [])
                for email_entry in emails:
                    if email_entry.get('verified'):
                        return email_entry.get('email')
                
                # Return first email even if not verified
                if emails:
                    return emails[0].get('email')
                    
        except Exception as e:
            self.logger.debug(f"ORCID lookup failed for {orcid}: {e}")
        
        return None
    
    def _get_institution_domain(self, institution: str) -> Optional[str]:
        """
        Get email domain for an institution.
        
        Args:
            institution: Institution name
            
        Returns:
            Domain if found
        """
        if not institution:
            return None
        
        institution_lower = institution.lower()
        
        # Known institution domains
        known_domains = {
            'harvard': 'harvard.edu',
            'mit': 'mit.edu',
            'stanford': 'stanford.edu',
            'yale': 'yale.edu',
            'nih': 'nih.gov',
            'fda': 'fda.gov',
            'johns hopkins': 'jhu.edu',
            'university of california': 'ucla.edu',
            'columbia': 'columbia.edu',
            'oxford': 'ox.ac.uk',
            'cambridge': 'cam.ac.uk',
            'pfizer': 'pfizer.com',
            'novartis': 'novartis.com',
            'roche': 'roche.com',
            'merck': 'merck.com',
            'johnson & johnson': 'jnj.com',
            'genentech': 'gene.com',
            'amgen': 'amgen.com',
            'abbvie': 'abbvie.com',
            'gilead': 'gilead.com',
            'biogen': 'biogen.com',
        }
        
        for key, domain in known_domains.items():
            if key in institution_lower:
                return domain
        
        # Try to extract domain from institution name
        domain = self._generate_domain_from_name(institution)
        return domain
    
    def _generate_domain_from_name(self, institution: str) -> Optional[str]:
        """Generate likely domain from institution name."""
        if not institution:
            return None
        
        # Clean and simplify name
        name = institution.lower()
        name = re.sub(r'university of |the |inc\.?|corp\.?|llc|ltd', '', name)
        name = re.sub(r'[^a-z0-9\s]', '', name)
        words = name.split()
        
        if not words:
            return None
        
        # Common naming pattern: firstword.edu or firstword.com
        first_word = words[0]
        
        # Academic indicators
        academic_indicators = ['university', 'college', 'institute', 'school', 'hospital', 'center', 'centre']
        is_academic = any(ind in institution.lower() for ind in academic_indicators)
        
        tld = '.edu' if is_academic else '.com'
        
        return f"{first_word}{tld}"
    
    def _generate_email_candidates(
        self,
        first_name: str,
        last_name: str,
        domain: str,
    ) -> List[Dict]:
        """
        Generate possible email addresses.
        
        Args:
            first_name: Person's first name
            last_name: Person's last name
            domain: Email domain
            
        Returns:
            List of candidate emails with confidence scores
        """
        candidates = []
        
        for pattern in COMMON_PATTERNS:
            try:
                email = pattern.generate(first_name, last_name, domain)
                
                # Adjust confidence based on domain pattern if known
                confidence = pattern.confidence
                if domain in self._domain_patterns:
                    if self._domain_patterns[domain].name == pattern.name:
                        confidence = min(0.95, confidence + 0.15)
                
                candidates.append({
                    'email': email,
                    'confidence': round(confidence, 2),
                    'pattern': pattern.name,
                })
            except Exception:
                continue
        
        # Sort by confidence
        candidates.sort(key=lambda x: x['confidence'], reverse=True)
        
        return candidates
    
    def learn_pattern_from_known_email(self, email: str, first_name: str, last_name: str):
        """
        Learn email pattern from a known email.
        
        Args:
            email: Known email address
            first_name: Person's first name
            last_name: Person's last name
        """
        try:
            local, domain = email.lower().split('@')
            first = first_name.lower()
            last = last_name.lower()
            
            # Detect which pattern matches
            for pattern in COMMON_PATTERNS:
                expected_local = (
                    pattern.pattern
                    .replace('{first}', first)
                    .replace('{last}', last)
                    .replace('{f}', first[0] if first else '')
                    .replace('{l}', last[0] if last else '')
                )
                
                if local == expected_local:
                    self._domain_patterns[domain] = pattern
                    self.logger.info(f"Learned pattern '{pattern.name}' for domain {domain}")
                    break
                    
        except Exception as e:
            self.logger.debug(f"Could not learn pattern from {email}: {e}")
    
    def batch_find_emails(self, leads: List[Dict]) -> List[Dict]:
        """
        Find emails for a batch of leads.
        
        Args:
            leads: List of lead dictionaries
            
        Returns:
            Updated leads with email information
        """
        enriched = []
        
        for lead in leads:
            # Skip if email already known
            if lead.get('email'):
                lead['email_source'] = 'original'
                enriched.append(lead)
                continue
            
            # Parse name
            name = lead.get('name', '')
            name_parts = name.split()
            if len(name_parts) >= 2:
                first_name = name_parts[0]
                last_name = ' '.join(name_parts[1:])
            else:
                first_name = name
                last_name = ''
            
            result = self.find_email(
                first_name=first_name,
                last_name=last_name,
                institution=lead.get('institution', ''),
                orcid=lead.get('orcid'),
            )
            
            if result:
                lead['email'] = result['email']
                lead['email_confidence'] = result['confidence']
                lead['email_source'] = result['source']
                if 'alternatives' in result:
                    lead['email_alternatives'] = result['alternatives']
            
            enriched.append(lead)
        
        return enriched
