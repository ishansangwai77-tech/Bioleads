# BioLeads - B2B Lead Generation Agent
"""
BioLeads: Web scraping and lead scoring system for biotech companies
selling 3D in-vitro models for drug discovery and toxicology.
"""

__version__ = '1.0.0'

from .config import Settings, Keywords
from .pipeline import PipelineOrchestrator

__all__ = ['Settings', 'Keywords', 'PipelineOrchestrator']
