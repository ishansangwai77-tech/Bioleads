# BioLeads Dashboard Components
"""
Reusable UI components for the Streamlit dashboard.
"""

import streamlit as st
from typing import Dict, List, Optional


class LeadCard:
    """Component for displaying a single lead."""
    
    @staticmethod
    def render(lead: Dict, expanded: bool = False):
        """
        Render a lead card.
        
        Args:
            lead: Lead dictionary
            expanded: Whether to show expanded details
        """
        tier = lead.get('tier', 'cold')
        tier_colors = {
            'hot': '🔥',
            'warm': '🌡️',
            'cold': '❄️',
            'ice': '🧊',
        }
        tier_emoji = tier_colors.get(tier, '❓')
        
        score = lead.get('score', 0)
        name = lead.get('name', 'Unknown')
        institution = lead.get('institution', 'Unknown Institution')
        
        # Card header
        col1, col2, col3 = st.columns([3, 2, 1])
        
        with col1:
            st.markdown(f"### {name}")
            st.caption(institution)
        
        with col2:
            if lead.get('title'):
                st.markdown(f"**{lead.get('title')}**")
            if lead.get('email'):
                st.markdown(f"📧 {lead.get('email')}")
            elif lead.get('email_confidence'):
                st.caption(f"Email confidence: {lead.get('email_confidence'):.0%}")
        
        with col3:
            st.metric(
                label=f"{tier_emoji} Score",
                value=f"{score:.0f}",
            )
        
        # Expandable details
        if expanded:
            with st.expander("View Details", expanded=False):
                LeadCard._render_details(lead)
    
    @staticmethod
    def _render_details(lead: Dict):
        """Render detailed lead information."""
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Research Focus:**")
            focus = lead.get('research_focus', [])
            if focus:
                for topic in focus[:5]:
                    st.markdown(f"- {topic}")
            else:
                st.caption("Not available")
            
            st.markdown("---")
            st.markdown("**Activity:**")
            st.markdown(f"- Publications: {lead.get('publications', 0)}")
            st.markdown(f"- Citations: {lead.get('cited_by_count', 'N/A')}")
            st.markdown(f"- Grants: {len(lead.get('grants', []))}")
        
        with col2:
            st.markdown("**Score Breakdown:**")
            breakdown = lead.get('score_breakdown', {}).get('breakdown', {})
            if breakdown:
                for factor, score in breakdown.items():
                    if score > 0:
                        st.markdown(f"- {factor.replace('_', ' ').title()}: {score:.1f}")
            
            st.markdown("---")
            st.markdown("**Key Factors:**")
            factors = lead.get('score_breakdown', {}).get('key_factors', [])
            if factors:
                for factor in factors:
                    st.markdown(f"- {factor}")
        
        # Sources
        sources = lead.get('sources', [lead.get('source', 'unknown')])
        st.caption(f"Sources: {', '.join(sources)}")
        
        if lead.get('orcid'):
            st.caption(f"ORCID: {lead.get('orcid')}")


class FilterSidebar:
    """Sidebar with filtering options."""
    
    @staticmethod
    def render(leads: List[Dict]) -> Dict:
        """
        Render filter sidebar and return filter values.
        
        Args:
            leads: List of all leads (for determining options)
            
        Returns:
            Dictionary of filter values
        """
        st.sidebar.header("🔍 Filters")
        
        filters = {}
        
        # Score range
        st.sidebar.subheader("Score Range")
        filters['min_score'] = st.sidebar.slider(
            "Minimum Score",
            min_value=0,
            max_value=100,
            value=0,
            step=5,
        )
        
        # Tier filter - default to ALL tiers
        st.sidebar.subheader("Lead Tier")
        all_tiers = ['hot', 'warm', 'cold', 'ice']
        filters['tiers'] = st.sidebar.multiselect(
            "Select Tiers",
            options=all_tiers,
            default=all_tiers,  # Include all by default
        )
        
        # Source filter
        st.sidebar.subheader("Data Source")
        all_sources = set()
        for lead in leads:
            sources = lead.get('sources', [lead.get('source', '')])
            if isinstance(sources, str):
                sources = [sources]
            all_sources.update([s for s in sources if s])
        all_sources = sorted(list(all_sources)) if all_sources else ['all']
        
        filters['sources'] = st.sidebar.multiselect(
            "Select Sources",
            options=all_sources,
            default=all_sources,
        )
        
        # Has email filter
        st.sidebar.subheader("Contact Info")
        filters['has_email'] = st.sidebar.checkbox("Has Email Only", value=False)
        
        # Search
        st.sidebar.subheader("Search")
        filters['search'] = st.sidebar.text_input("Search name/institution")
        
        return filters
    
    @staticmethod
    def apply_filters(leads: List[Dict], filters: Dict) -> List[Dict]:
        """
        Apply filters to leads list.
        
        Args:
            leads: All leads
            filters: Filter dictionary from render()
            
        Returns:
            Filtered leads
        """
        filtered = leads.copy()
        
        # Score filter
        if filters.get('min_score'):
            filtered = [l for l in filtered if l.get('score', 0) >= filters['min_score']]
        
        # Tier filter - only apply if tiers are selected
        if filters.get('tiers'):
            filtered = [l for l in filtered if l.get('tier', 'cold') in filters['tiers']]
        
        # Source filter - only apply if sources are selected
        if filters.get('sources'):
            def has_source(lead):
                lead_sources = lead.get('sources', [lead.get('source', '')])
                if isinstance(lead_sources, str):
                    lead_sources = [lead_sources]
                return any(s in filters['sources'] for s in lead_sources if s)
            filtered = [l for l in filtered if has_source(l)]
        
        # Has email filter
        if filters.get('has_email'):
            filtered = [l for l in filtered if l.get('email')]
        
        # Search filter
        if filters.get('search'):
            search = filters['search'].lower()
            filtered = [
                l for l in filtered
                if search in l.get('name', '').lower() or search in l.get('institution', '').lower()
            ]
        
        return filtered


class ScoreGauge:
    """Score visualization component."""
    
    @staticmethod
    def render(score: float, tier: str):
        """
        Render a score gauge.
        
        Args:
            score: Score value (0-100)
            tier: Lead tier
        """
        tier_colors = {
            'hot': '#ff4b4b',
            'warm': '#ffa500',
            'cold': '#4dabf7',
            'ice': '#a5d8ff',
        }
        color = tier_colors.get(tier, '#868e96')
        
        # Create progress-bar style gauge
        st.markdown(
            f"""
            <div style="
                background-color: #e9ecef;
                border-radius: 10px;
                height: 20px;
                width: 100%;
                overflow: hidden;
            ">
                <div style="
                    background-color: {color};
                    width: {score}%;
                    height: 100%;
                    border-radius: 10px;
                    transition: width 0.3s ease;
                "></div>
            </div>
            <p style="text-align: center; margin-top: 5px;">
                <strong>{score:.0f}</strong> / 100
            </p>
            """,
            unsafe_allow_html=True,
        )


class MetricsRow:
    """Row of metric cards."""
    
    @staticmethod
    def render(metrics: Dict):
        """
        Render a row of metrics.
        
        Args:
            metrics: Dictionary with metric names and values
        """
        cols = st.columns(len(metrics))
        
        for col, (name, value) in zip(cols, metrics.items()):
            with col:
                if isinstance(value, dict):
                    st.metric(
                        label=name,
                        value=value.get('value'),
                        delta=value.get('delta'),
                    )
                else:
                    st.metric(label=name, value=value)


class ChartComponents:
    """Chart visualization components."""
    
    @staticmethod
    def tier_distribution(leads: List[Dict]):
        """Render tier distribution chart."""
        import pandas as pd
        
        tier_counts = {'hot': 0, 'warm': 0, 'cold': 0, 'ice': 0}
        for lead in leads:
            tier = lead.get('tier', 'ice')
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
        
        df = pd.DataFrame({
            'Tier': list(tier_counts.keys()),
            'Count': list(tier_counts.values()),
        })
        
        st.bar_chart(df.set_index('Tier'))
    
    @staticmethod
    def source_distribution(leads: List[Dict]):
        """Render source distribution chart."""
        import pandas as pd
        
        source_counts = {}
        for lead in leads:
            sources = lead.get('sources', [lead.get('source', 'unknown')])
            for source in sources:
                source_counts[source] = source_counts.get(source, 0) + 1
        
        df = pd.DataFrame({
            'Source': list(source_counts.keys()),
            'Count': list(source_counts.values()),
        })
        
        st.bar_chart(df.set_index('Source'))
    
    @staticmethod
    def score_histogram(leads: List[Dict]):
        """Render score distribution histogram."""
        import pandas as pd
        
        scores = [lead.get('score', 0) for lead in leads]
        df = pd.DataFrame({'Score': scores})
        
        st.bar_chart(df['Score'].value_counts().sort_index())
