# BioLeads ClinicalTrials.gov Scraper
"""
Scraper for ClinicalTrials.gov API.
Finds clinical trials using 3D in-vitro models or organoids.
Free, public API.
"""

from typing import Dict, List, Optional
from datetime import datetime

from .base_scraper import BaseScraper


class ClinicalTrialsScraper(BaseScraper):
    """
    Scraper for ClinicalTrials.gov database.
    
    Uses the ClinicalTrials.gov API v2 to find trials related to
    3D in-vitro models, organoids, and advanced cell culture.
    
    API Documentation: https://clinicaltrials.gov/data-api/api
    """
    
    def __init__(self):
        """Initialize ClinicalTrials.gov scraper."""
        from ..config.settings import settings
        
        super().__init__(
            name='clinicaltrials',
            base_url=settings.api.clinicaltrials_base_url,
            rate_limit_seconds=settings.api.clinicaltrials_rate_limit,
        )
    
    def search(self, query: str, max_results: int = 100) -> List[Dict]:
        """
        Search ClinicalTrials.gov for trials.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            List of trial dictionaries
        """
        self.logger.info(f"Searching ClinicalTrials.gov: {query[:50]}...")
        
        all_trials = []
        page_token = None
        page_size = min(100, max_results)
        
        while len(all_trials) < max_results:
            params = {
                'query.term': query,
                'pageSize': page_size,
                'format': 'json',
                'fields': ','.join([
                    'NCTId', 'BriefTitle', 'OfficialTitle',
                    'LeadSponsorName', 'LeadSponsorClass',
                    'ResponsiblePartyInvestigatorFullName',
                    'ResponsiblePartyInvestigatorTitle',
                    'ResponsiblePartyInvestigatorAffiliation',
                    'OverallOfficialName', 'OverallOfficialRole',
                    'OverallOfficialAffiliation',
                    'LocationFacility', 'LocationCity', 'LocationState', 'LocationCountry',
                    'Condition', 'Keyword', 'Phase',
                    'StartDate', 'CompletionDate', 'OverallStatus',
                    'BriefSummary',
                ]),
            }
            
            if page_token:
                params['pageToken'] = page_token
            
            response = self.fetch('studies', params=params)
            
            if not response:
                break
            
            studies = response.get('studies', [])
            if not studies:
                break
            
            all_trials.extend(studies)
            
            # Get next page token
            page_token = response.get('nextPageToken')
            if not page_token:
                break
        
        self.logger.info(f"Found {len(all_trials)} trials")
        return all_trials[:max_results]
    
    def search_by_sponsor(self, sponsor_name: str, max_results: int = 50) -> List[Dict]:
        """
        Search for trials by sponsor name.
        
        Args:
            sponsor_name: Company/organization name
            max_results: Maximum results
            
        Returns:
            List of trial dictionaries
        """
        params = {
            'query.spons': sponsor_name,
            'pageSize': max_results,
            'format': 'json',
        }
        
        response = self.fetch('studies', params=params)
        return response.get('studies', []) if response else []
    
    def get_trial_details(self, nct_id: str) -> Optional[Dict]:
        """
        Get detailed information for a specific trial.
        
        Args:
            nct_id: ClinicalTrials.gov identifier (NCT number)
            
        Returns:
            Trial details dictionary
        """
        response = self.fetch(f'studies/{nct_id}', params={'format': 'json'})
        return response
    
    def parse_lead(self, raw_data: Dict) -> Optional[Dict]:
        """
        Parse trial data into lead format.
        
        Extracts Principal Investigator or Responsible Party as lead.
        """
        if not raw_data:
            return None
        
        # Extract from nested protocol section
        protocol = raw_data.get('protocolSection', {})
        id_module = protocol.get('identificationModule', {})
        sponsor_module = protocol.get('sponsorCollaboratorsModule', {})
        contacts_module = protocol.get('contactsLocationsModule', {})
        description_module = protocol.get('descriptionModule', {})
        conditions_module = protocol.get('conditionsModule', {})
        
        nct_id = id_module.get('nctId', '')
        
        # Get lead sponsor
        lead_sponsor = sponsor_module.get('leadSponsor', {})
        sponsor_name = lead_sponsor.get('name', '')
        sponsor_class = lead_sponsor.get('class', '')  # INDUSTRY, NETWORK, etc.
        
        # Get overall officials (Principal Investigators)
        overall_officials = contacts_module.get('overallOfficials', [])
        pi_name = ''
        pi_affiliation = ''
        pi_role = ''
        
        if overall_officials:
            pi = overall_officials[0]
            pi_name = pi.get('name', '')
            pi_affiliation = pi.get('affiliation', '')
            pi_role = pi.get('role', '')
        
        # Get locations
        locations = contacts_module.get('locations', [])
        primary_location = locations[0] if locations else {}
        
        # Get conditions/keywords for research focus
        conditions = conditions_module.get('conditions', [])
        keywords = conditions_module.get('keywords', [])
        research_focus = conditions + keywords
        
        # Determine who the lead should be
        if pi_name:
            lead_name = pi_name
            lead_institution = pi_affiliation or sponsor_name
        else:
            lead_name = sponsor_name
            lead_institution = sponsor_name
        
        return {
            'source': 'clinicaltrials',
            'source_id': nct_id,
            'name': lead_name,
            'email': None,  # Not exposed in API
            'title': pi_role or 'Principal Investigator',
            'institution': lead_institution,
            'department': None,
            'location': self._format_location(primary_location),
            'research_focus': research_focus[:10],
            'publications': 0,
            'grants': [],
            'clinical_trial': {
                'nct_id': nct_id,
                'title': id_module.get('officialTitle') or id_module.get('briefTitle', ''),
                'brief_summary': description_module.get('briefSummary', ''),
                'phase': protocol.get('designModule', {}).get('phases', []),
                'status': protocol.get('statusModule', {}).get('overallStatus', ''),
                'sponsor': sponsor_name,
                'sponsor_class': sponsor_class,
                'conditions': conditions,
            },
            'sponsor_class': sponsor_class,  # Useful for filtering (INDUSTRY = pharma)
            'raw_data': raw_data,
        }
    
    def _format_location(self, location: Dict) -> str:
        """Format location from trial location data."""
        parts = filter(None, [
            location.get('city'),
            location.get('state'),
            location.get('country'),
        ])
        return ', '.join(parts)
    
    def run_with_keywords(
        self,
        max_results_per_query: int = 30,
        save_raw: bool = True,
    ) -> List[Dict]:
        """
        Run scraper using pre-configured keywords.
        
        Args:
            max_results_per_query: Max results per query
            save_raw: Whether to save raw data
            
        Returns:
            List of parsed lead records
        """
        # Queries relevant to 3D in-vitro models in clinical settings
        queries = [
            'organoid',
            '3D cell culture',
            'organ-on-chip',
            'microphysiological',
            'in vitro drug screening',
            'patient-derived model',
        ]
        
        all_leads = []
        all_trials = []
        
        for query in queries:
            trials = self.search(query, max_results=max_results_per_query)
            all_trials.extend(trials)
            
            for trial in trials:
                lead = self.parse_lead(trial)
                if lead:
                    all_leads.append(lead)
        
        if save_raw and all_trials:
            self.save_raw(all_trials, 'all_trials')
        
        return all_leads
