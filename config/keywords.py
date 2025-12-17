# BioLeads Keywords Configuration
"""
Target keywords for each data source.
Optimized for finding leads interested in 3D in-vitro models for drug discovery/toxicology.
"""

from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class Keywords:
    """Keyword configurations for different data sources."""
    
    # Core 3D In-Vitro Model Keywords
    core_terms: List[str] = field(default_factory=lambda: [
        # 3D Culture Systems
        "3D cell culture",
        "three-dimensional cell culture",
        "3D in vitro",
        "3D in-vitro",
        "organoid",
        "organoids",
        "spheroid",
        "spheroids",
        "organ-on-a-chip",
        "organ on chip",
        "organs-on-chips",
        "microphysiological systems",
        "tissue engineering",
        "bioprinting",
        "3D bioprinting",
        
        # Specific Model Types
        "liver organoid",
        "hepatic organoid",
        "intestinal organoid",
        "kidney organoid",
        "brain organoid",
        "cardiac organoid",
        "lung organoid",
        "tumor organoid",
        "patient-derived organoid",
        "PDO",
        "hepatocyte spheroid",
        
        # Applications
        "drug screening",
        "high-throughput screening",
        "toxicity testing",
        "toxicology screening",
        "ADMET",
        "drug metabolism",
        "pharmacokinetics",
        "drug-induced liver injury",
        "DILI",
        "cardiotoxicity",
        "nephrotoxicity",
        "neurotoxicity",
    ])
    
    # PubMed-specific search queries
    pubmed_queries: List[str] = field(default_factory=lambda: [
        # Primary queries
        '("3D cell culture"[Title/Abstract] OR "organoid"[Title/Abstract]) AND ("drug screening"[Title/Abstract] OR "toxicology"[Title/Abstract])',
        '("organ-on-a-chip"[Title/Abstract] OR "microphysiological systems"[Title/Abstract]) AND "drug discovery"[Title/Abstract]',
        '("spheroid"[Title/Abstract] AND "hepatocyte"[Title/Abstract]) AND ("toxicity"[Title/Abstract] OR "drug metabolism"[Title/Abstract])',
        '"patient-derived organoid"[Title/Abstract] AND ("drug response"[Title/Abstract] OR "personalized medicine"[Title/Abstract])',
        '("3D in vitro model"[Title/Abstract] OR "tissue model"[Title/Abstract]) AND "pharmaceutical"[Title/Abstract]',
        
        # Toxicology focus
        '("in vitro toxicology"[Title/Abstract] AND "alternative methods"[Title/Abstract])',
        '("DILI"[Title/Abstract] OR "drug-induced liver injury"[Title/Abstract]) AND "in vitro"[Title/Abstract]',
        '"cardiotoxicity"[Title/Abstract] AND ("3D"[Title/Abstract] OR "organoid"[Title/Abstract])',
    ])
    
    # NIH Reporter grant search terms
    nih_grant_terms: List[str] = field(default_factory=lambda: [
        "3D cell culture",
        "organoid",
        "organ-on-a-chip",
        "microphysiological system",
        "tissue chip",
        "in vitro toxicology",
        "alternative animal testing",
        "drug screening platform",
        "spheroid culture",
        "bioprinted tissue",
    ])
    
    # NIH Activity Codes to prioritize (grants more likely to need products)
    nih_priority_activity_codes: List[str] = field(default_factory=lambda: [
        "R01",  # Research Project Grant
        "R21",  # Exploratory/Developmental Research Grant
        "R43",  # SBIR Phase I
        "R44",  # SBIR Phase II
        "U01",  # Cooperative Agreement
        "U19",  # Research Program Cooperative Agreement
        "R35",  # Outstanding Investigator Award
        "DP2",  # New Innovator Award
    ])
    
    # OpenAlex concept IDs for filtering
    openalex_concepts: List[str] = field(default_factory=lambda: [
        "C203014093",  # Organoid
        "C71924100",   # Tissue engineering
        "C2779179882", # 3D cell culture
        "C155566097",  # Spheroid
        "C2776034682", # Organ-on-a-chip
        "C126322002",  # Drug discovery
        "C71189000",   # Toxicology
    ])
    
    # Target job titles (for lead scoring)
    target_titles: List[str] = field(default_factory=lambda: [
        # Research roles
        "Principal Investigator",
        "PI",
        "Research Director",
        "Lab Director",
        "Group Leader",
        "Senior Scientist",
        "Staff Scientist",
        "Research Scientist",
        "Associate Director",
        
        # Decision makers
        "VP Research",
        "Vice President Research",
        "Chief Scientific Officer",
        "CSO",
        "Head of Research",
        "Director of Biology",
        "Director of Pharmacology",
        "Director of Toxicology",
        "Director of Drug Discovery",
        "Head of ADMET",
        "Head of Safety Assessment",
        
        # Procurement/Operations
        "Procurement Manager",
        "Lab Manager",
        "Operations Manager",
    ])
    
    # Target institution types
    target_institution_types: List[str] = field(default_factory=lambda: [
        "Pharmaceutical",
        "Biotechnology",
        "Biotech",
        "Pharma",
        "CRO",
        "Contract Research Organization",
        "Academic Medical Center",
        "Research Hospital",
        "University",
        "Research Institute",
    ])
    
    # Negative keywords (to filter out irrelevant results)
    exclude_terms: List[str] = field(default_factory=lambda: [
        "3D printing prosthetics",
        "3D printed implant",
        "review article",
        "meta-analysis",
        "systematic review",
        "veterinary",
        "agricultural",
        "plant cell culture",
    ])
    
    # Conference tracks/sessions to target
    conference_tracks: List[str] = field(default_factory=lambda: [
        "in vitro toxicology",
        "alternative methods",
        "3D models",
        "organoids",
        "organ-on-a-chip",
        "microphysiological",
        "new approach methodologies",
        "NAMs",
        "high-throughput",
        "drug safety",
        "ADMET",
    ])
    
    # Target conferences
    target_conferences: List[str] = field(default_factory=lambda: [
        "Society of Toxicology Annual Meeting",
        "ISSCR Annual Meeting",  # Stem cell research
        "Organ-on-a-Chip World Congress",
        "3D Cell Culture Conference",
        "Drug Discovery Chemistry",
        "AACR Annual Meeting",  # Cancer research
        "World Pharma Congress",
        "BIO International Convention",
    ])

    def get_pubmed_query_batch(self, batch_size: int = 3) -> List[List[str]]:
        """Split PubMed queries into batches for processing."""
        return [
            self.pubmed_queries[i:i + batch_size] 
            for i in range(0, len(self.pubmed_queries), batch_size)
        ]
    
    def is_relevant_title(self, title: str) -> bool:
        """Check if a job title matches target criteria."""
        title_lower = title.lower()
        return any(target.lower() in title_lower for target in self.target_titles)
    
    def is_excluded(self, text: str) -> bool:
        """Check if text contains exclusion terms."""
        text_lower = text.lower()
        return any(term.lower() in text_lower for term in self.exclude_terms)


# Global keywords instance
keywords = Keywords()
