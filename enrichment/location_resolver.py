# BioLeads Location Resolver
"""
Resolve and normalize location information for leads.
Distinguishes between person location and organization HQ.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class Location:
    """Structured location information."""
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    full_address: Optional[str] = None
    timezone: Optional[str] = None
    coordinates: Optional[Tuple[float, float]] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'city': self.city,
            'state': self.state,
            'country': self.country,
            'postal_code': self.postal_code,
            'full_address': self.full_address,
            'timezone': self.timezone,
            'coordinates': self.coordinates,
        }
    
    def __str__(self) -> str:
        """Format as string."""
        parts = filter(None, [self.city, self.state, self.country])
        return ', '.join(parts)


class LocationResolver:
    """
    Resolve and normalize location data.
    
    Features:
    - Parse affiliation strings to extract location
    - Normalize country names
    - Infer timezone from location
    - Distinguish person vs HQ location
    """
    
    # US state abbreviations
    US_STATES = {
        'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas',
        'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware',
        'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii', 'ID': 'Idaho',
        'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas',
        'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
        'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi',
        'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada',
        'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York',
        'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma',
        'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
        'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah',
        'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia',
        'WI': 'Wisconsin', 'WY': 'Wyoming', 'DC': 'District of Columbia',
    }
    
    # Country name variations
    COUNTRY_ALIASES = {
        'usa': 'United States',
        'us': 'United States',
        'u.s.': 'United States',
        'u.s.a.': 'United States',
        'united states of america': 'United States',
        'uk': 'United Kingdom',
        'u.k.': 'United Kingdom',
        'england': 'United Kingdom',
        'scotland': 'United Kingdom',
        'wales': 'United Kingdom',
        'prc': 'China',
        "people's republic of china": 'China',
        'deutschland': 'Germany',
        'japan': 'Japan',
        'nippon': 'Japan',
        'korea': 'South Korea',
        'republic of korea': 'South Korea',
    }
    
    # Timezone mapping (simplified)
    TIMEZONE_MAP = {
        'United States': {
            'California': 'America/Los_Angeles',
            'Washington': 'America/Los_Angeles',
            'Oregon': 'America/Los_Angeles',
            'New York': 'America/New_York',
            'Massachusetts': 'America/New_York',
            'Pennsylvania': 'America/New_York',
            'Texas': 'America/Chicago',
            'Illinois': 'America/Chicago',
            'default': 'America/New_York',
        },
        'United Kingdom': 'Europe/London',
        'Germany': 'Europe/Berlin',
        'France': 'Europe/Paris',
        'Japan': 'Asia/Tokyo',
        'China': 'Asia/Shanghai',
        'India': 'Asia/Kolkata',
        'Australia': 'Australia/Sydney',
        'default': 'UTC',
    }
    
    def __init__(self):
        """Initialize location resolver."""
        self.logger = logging.getLogger('bioleads.enrichment.location_resolver')
    
    def resolve(self, location_string: str) -> Location:
        """
        Parse and resolve a location string.
        
        Args:
            location_string: Raw location text (e.g., "Boston, MA, USA")
            
        Returns:
            Structured Location object
        """
        if not location_string:
            return Location()
        
        # Clean the string
        text = location_string.strip()
        
        # Parse components
        city, state, country = self._parse_location_parts(text)
        
        # Normalize country
        if country:
            country = self._normalize_country(country)
        
        # Infer country from state if in US
        if state and not country:
            state_abbrev = self._get_state_abbrev(state)
            if state_abbrev:
                country = 'United States'
                state = self.US_STATES.get(state_abbrev, state)
        
        # Get timezone
        timezone = self._get_timezone(country, state)
        
        return Location(
            city=city,
            state=state,
            country=country,
            full_address=text,
            timezone=timezone,
        )
    
    def _parse_location_parts(self, text: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Parse location string into city, state, country."""
        # Split by common delimiters
        parts = [p.strip() for p in re.split(r'[,;]', text) if p.strip()]
        
        if not parts:
            return None, None, None
        
        city = None
        state = None
        country = None
        
        # Work backwards - country usually last
        remaining = parts.copy()
        
        # Check if last part is a country
        if remaining:
            last = remaining[-1].lower()
            if last in self.COUNTRY_ALIASES or len(last) <= 3:
                country = remaining.pop()
            elif any(c in last for c in ['land', 'kingdom', 'states', 'republic']):
                country = remaining.pop()
        
        # Check for US state
        if remaining:
            last = remaining[-1]
            state_abbrev = self._get_state_abbrev(last)
            if state_abbrev:
                state = self.US_STATES.get(state_abbrev, last)
                remaining.pop()
                if not country:
                    country = 'United States'
        
        # Remaining is city (take first relevant part)
        if remaining:
            city = remaining[0]
        
        return city, state, country
    
    def _get_state_abbrev(self, text: str) -> Optional[str]:
        """Get US state abbreviation if text is a state."""
        text_upper = text.upper().strip()
        
        # Direct abbreviation match
        if text_upper in self.US_STATES:
            return text_upper
        
        # Full name match
        for abbrev, name in self.US_STATES.items():
            if name.lower() == text.lower():
                return abbrev
        
        return None
    
    def _normalize_country(self, country: str) -> str:
        """Normalize country name."""
        country_lower = country.lower().strip()
        
        if country_lower in self.COUNTRY_ALIASES:
            return self.COUNTRY_ALIASES[country_lower]
        
        # Title case if not found
        return country.strip().title()
    
    def _get_timezone(self, country: Optional[str], state: Optional[str]) -> Optional[str]:
        """Get timezone for location."""
        if not country:
            return None
        
        tz_info = self.TIMEZONE_MAP.get(country)
        
        if isinstance(tz_info, dict):
            if state and state in tz_info:
                return tz_info[state]
            return tz_info.get('default')
        elif isinstance(tz_info, str):
            return tz_info
        
        return self.TIMEZONE_MAP.get('default')
    
    def parse_affiliation(self, affiliation: str) -> Dict:
        """
        Extract structured data from an affiliation string.
        
        Args:
            affiliation: Full affiliation text (e.g., "Department of Biology, Harvard University, Cambridge, MA, USA")
            
        Returns:
            Dict with department, institution, and location
        """
        if not affiliation:
            return {}
        
        parts = [p.strip() for p in affiliation.split(',')]
        
        result = {
            'department': None,
            'institution': None,
            'location': None,
        }
        
        for part in parts:
            part_lower = part.lower()
            
            # Check for department
            if any(kw in part_lower for kw in ['department', 'division', 'lab ', 'laboratory', 'group', 'center for', 'centre for', 'school of', 'faculty of']):
                result['department'] = part
            
            # Check for institution
            elif any(kw in part_lower for kw in ['university', 'institute', 'college', 'hospital', 'school', 'inc', 'corp', 'company', 'ltd', 'llc']):
                result['institution'] = part
        
        # Get location from remaining parts
        location_parts = []
        for part in reversed(parts):
            part_lower = part.lower()
            
            # Stop when we hit an institution
            if any(kw in part_lower for kw in ['university', 'institute', 'college', 'hospital', 'inc', 'corp']):
                break
            
            location_parts.insert(0, part)
        
        if location_parts:
            location_str = ', '.join(location_parts)
            result['location'] = self.resolve(location_str)
        
        return result
    
    def batch_resolve(self, leads: List[Dict]) -> List[Dict]:
        """
        Resolve locations for a batch of leads.
        
        Args:
            leads: List of lead dictionaries
            
        Returns:
            Updated leads with resolved location info
        """
        for lead in leads:
            location_str = lead.get('location', '')
            
            if location_str:
                resolved = self.resolve(location_str)
                lead['location_resolved'] = resolved.to_dict()
                lead['timezone'] = resolved.timezone
            
            # Also parse affiliation if available
            raw_data = lead.get('raw_data', {})
            
            # Try different affiliation sources
            affiliation = None
            if 'authors' in raw_data and raw_data['authors']:
                affiliation = raw_data['authors'][0].get('affiliation')
            elif 'organization' in raw_data:
                org = raw_data['organization']
                affiliation = f"{org.get('org_name', '')}, {org.get('org_city', '')}, {org.get('org_state', '')}, {org.get('org_country', '')}"
            
            if affiliation:
                parsed = self.parse_affiliation(affiliation)
                if parsed.get('location'):
                    lead['location_resolved'] = parsed['location'].to_dict()
                    lead['timezone'] = parsed['location'].timezone
        
        return leads
