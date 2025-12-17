# BioLeads Streamlit Dashboard
"""
Main Streamlit dashboard application for viewing and managing leads.

Run with: streamlit run bioleads/dashboard/app.py
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Optional

import streamlit as st
import pandas as pd

# Fix imports for both module and direct execution
if __name__ == "__main__":
    # Add parent directories to path when running directly
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import components - use try/except for robustness
try:
    from bioleads.dashboard.components import LeadCard, FilterSidebar, MetricsRow, ChartComponents
except ImportError:
    from components import LeadCard, FilterSidebar, MetricsRow, ChartComponents


def create_app():
    """Create and configure the Streamlit app."""
    # Page config
    st.set_page_config(
        page_title="BioLeads - Lead Generation Dashboard",
        page_icon="🧬",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    
    # Custom CSS
    st.markdown("""
        <style>
        .main > div {
            padding-top: 2rem;
        }
        .stMetric {
            background-color: #f8f9fa;
            padding: 1rem;
            border-radius: 0.5rem;
        }
        .lead-card {
            border: 1px solid #e9ecef;
            border-radius: 0.5rem;
            padding: 1rem;
            margin-bottom: 1rem;
            background-color: white;
        }
        .tier-hot { border-left: 4px solid #ff4b4b; }
        .tier-warm { border-left: 4px solid #ffa500; }
        .tier-cold { border-left: 4px solid #4dabf7; }
        </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.title("🧬 BioLeads Dashboard")
    st.markdown("*B2B Lead Generation for 3D In-Vitro Models*")
    st.markdown("---")
    
    # Load leads
    leads = load_leads()
    
    if not leads:
        render_empty_state()
        return
    
    # Sidebar filters
    filters = FilterSidebar.render(leads)
    filtered_leads = FilterSidebar.apply_filters(leads, filters)
    
    # Main content
    render_metrics(leads, filtered_leads)
    st.markdown("---")
    
    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["📋 Lead List", "📊 Analytics", "⬇️ Export"])
    
    with tab1:
        render_lead_list(filtered_leads)
    
    with tab2:
        render_analytics(filtered_leads)
    
    with tab3:
        render_export(filtered_leads)


def load_leads() -> List[Dict]:
    """Load leads from the output directory."""
    # Try to load from session state first
    if 'leads' in st.session_state and st.session_state.leads:
        return st.session_state.leads
    
    # Try to load from file
    try:
        base_path = Path(__file__).parent.parent / 'data' / 'output'
        
        # Try JSON first
        json_path = base_path / 'leads.json'
        if json_path.exists():
            with open(json_path, 'r') as f:
                leads = json.load(f)
                st.session_state.leads = leads
                return leads
        
        # Try CSV
        csv_path = base_path / 'leads.csv'
        if csv_path.exists():
            df = pd.read_csv(csv_path)
            leads = df.to_dict('records')
            st.session_state.leads = leads
            return leads
    except Exception as e:
        st.error(f"Error loading leads: {e}")
    
    return []


def load_sample_leads() -> List[Dict]:
    """Generate sample leads for demonstration."""
    return [
        {
            'name': 'Dr. Jane Smith',
            'email': 'jsmith@harvard.edu',
            'email_confidence': 0.95,
            'title': 'Principal Investigator',
            'institution': 'Harvard Medical School',
            'department': 'Department of Cell Biology',
            'location': 'Boston, MA, USA',
            'score': 87,
            'tier': 'hot',
            'sources': ['pubmed', 'nih_reporter'],
            'research_focus': ['3D cell culture', 'organoids', 'drug screening', 'liver toxicology'],
            'publications': 45,
            'cited_by_count': 3200,
            'grants': [{'award_amount': 1500000, 'title': 'Liver organoids for drug safety'}],
            'company_info': {'type': 'academic'},
            'score_breakdown': {
                'breakdown': {
                    'publication': 15,
                    'grant': 20,
                    'role_fit': 10,
                    'topic_relevance': 10,
                    'recency': 10,
                    'institution_fit': 7,
                },
                'key_factors': ['Major NIH funding', 'Active researcher', 'Decision-maker role'],
            },
        },
        {
            'name': 'Dr. Michael Chen',
            'email': 'mchen@genentech.com',
            'email_confidence': 0.90,
            'title': 'Director of Toxicology',
            'institution': 'Genentech',
            'department': 'Safety Assessment',
            'location': 'South San Francisco, CA, USA',
            'score': 92,
            'tier': 'hot',
            'sources': ['openalex', 'clinicaltrials'],
            'research_focus': ['in vitro toxicology', 'organ-on-chip', 'drug safety'],
            'publications': 28,
            'cited_by_count': 1800,
            'grants': [],
            'company_info': {'type': 'pharma'},
            'score_breakdown': {
                'breakdown': {
                    'publication': 12,
                    'grant': 0,
                    'role_fit': 10,
                    'topic_relevance': 10,
                    'recency': 10,
                    'institution_fit': 10,
                },
                'key_factors': ['Director-level role', 'Industry pharma', 'Highly relevant focus'],
            },
        },
        {
            'name': 'Dr. Sarah Johnson',
            'email': None,
            'email_confidence': None,
            'title': 'Senior Scientist',
            'institution': 'MIT',
            'department': 'Biological Engineering',
            'location': 'Cambridge, MA, USA',
            'score': 65,
            'tier': 'warm',
            'sources': ['pubmed'],
            'research_focus': ['tissue engineering', 'bioprinting', 'stem cells'],
            'publications': 12,
            'cited_by_count': 450,
            'grants': [{'award_amount': 400000}],
            'company_info': {'type': 'academic'},
            'score_breakdown': {
                'breakdown': {
                    'publication': 8,
                    'grant': 10,
                    'role_fit': 7,
                    'topic_relevance': 6,
                },
                'key_factors': ['Active researcher', 'Grant funding'],
            },
        },
    ]


def render_empty_state():
    """Render empty state when no leads are loaded."""
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        ### No leads loaded yet
        
        To generate leads, run the pipeline:
        
        ```bash
        python main.py scrape --all
        python main.py enrich
        python main.py score
        ```
        
        Or load sample data to preview the dashboard:
        """)
        
        if st.button("Load Sample Data", type="primary"):
            st.session_state.leads = load_sample_leads()
            st.rerun()
        
        st.markdown("---")
        
        # File uploader
        st.markdown("### Or upload existing leads:")
        uploaded_file = st.file_uploader("Upload leads (CSV or JSON)", type=['csv', 'json'])
        
        if uploaded_file:
            try:
                if uploaded_file.name.endswith('.json'):
                    leads = json.load(uploaded_file)
                else:
                    df = pd.read_csv(uploaded_file)
                    leads = df.to_dict('records')
                
                st.session_state.leads = leads
                st.success(f"Loaded {len(leads)} leads!")
                st.rerun()
            except Exception as e:
                st.error(f"Error loading file: {e}")


def render_metrics(all_leads: List[Dict], filtered_leads: List[Dict]):
    """Render key metrics at the top."""
    # Calculate metrics
    total = len(all_leads)
    filtered = len(filtered_leads)
    
    hot_count = sum(1 for l in filtered_leads if l.get('tier') == 'hot')
    warm_count = sum(1 for l in filtered_leads if l.get('tier') == 'warm')
    
    avg_score = sum(l.get('score', 0) for l in filtered_leads) / len(filtered_leads) if filtered_leads else 0
    with_email = sum(1 for l in filtered_leads if l.get('email'))
    
    # Display metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Leads", total)
    with col2:
        st.metric("Filtered Leads", filtered)
    with col3:
        st.metric("🔥 Hot Leads", hot_count)
    with col4:
        st.metric("Avg Score", f"{avg_score:.0f}")
    with col5:
        st.metric("With Email", with_email)


def render_lead_list(leads: List[Dict]):
    """Render the lead list view as a table with requested columns."""
    if not leads:
        st.info("No leads match your current filters. Try adjusting the filters.")
        return
    
    st.subheader(f"📋 Lead Dashboard - {len(leads)} Leads")
    
    # Sort leads by score (highest first) to assign ranks
    sorted_leads = sorted(leads, key=lambda x: x.get('score', 0), reverse=True)
    
    # Prepare table data with requested columns
    table_data = []
    for rank, lead in enumerate(sorted_leads, 1):
        # Extract location info - handle NaN values from CSV
        location = lead.get('location', '') or ''
        if not isinstance(location, str):
            location = str(location) if location and str(location) != 'nan' else ''
        location_resolved = lead.get('location_resolved', {})
        person_location = location if location and location != 'nan' else 'N/A'
        
        # Company HQ (from institution info)
        company_info = lead.get('company_info', {})
        if isinstance(company_info, str):
            company_info = {}
        company_hq = ''
        if isinstance(location_resolved, dict):
            company_hq = location_resolved.get('country', '')
        
        # Fallback: extract country from person_location
        if not company_hq and person_location and person_location != 'N/A':
            try:
                parts = str(person_location).split(',')
                company_hq = parts[-1].strip() if parts else ''
            except:
                company_hq = ''
        
        # Infer work mode based on institution type
        inst_type = ''
        if isinstance(company_info, dict):
            inst_type = company_info.get('type', '')
        if inst_type in ['pharma', 'biotech', 'cro']:
            work_mode = 'Industry'
        elif inst_type in ['academic', 'medical_center']:
            work_mode = 'Academic'
        elif inst_type == 'government':
            work_mode = 'Government'
        else:
            work_mode = 'Research'
        
        # Handle email - may be NaN
        email = lead.get('email', '') or ''
        if not isinstance(email, str) or email == 'nan':
            email = ''
        
        table_data.append({
            'Rank': rank,
            'Probability Score': f"{lead.get('score', 0):.1f}%",
            'Name': str(lead.get('name', 'N/A')) if lead.get('name') else 'N/A',
            'Title': str(lead.get('title', '')) if lead.get('title') and str(lead.get('title')) != 'nan' else 'Researcher',
            'Company': str(lead.get('institution', 'N/A')) if lead.get('institution') else 'N/A',
            'Person Location': person_location,
            'Company HQ': company_hq or 'N/A',
            'Work Mode': work_mode,
            'Email': email or '—',
        })
    
    # Create DataFrame
    df = pd.DataFrame(table_data)
    
    # Style the dataframe
    def highlight_scores(val):
        if isinstance(val, str) and '%' in val:
            score = float(val.replace('%', ''))
            if score >= 75:
                return 'background-color: #d4edda; color: #155724'  # Green for hot
            elif score >= 50:
                return 'background-color: #fff3cd; color: #856404'  # Yellow for warm
            else:
                return 'background-color: #f8d7da; color: #721c24'  # Red for cold
        return ''
    
    # Display the table
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            'Rank': st.column_config.NumberColumn('Rank', width='small'),
            'Probability Score': st.column_config.TextColumn('Probability Score', width='medium'),
            'Name': st.column_config.TextColumn('Name', width='medium'),
            'Title': st.column_config.TextColumn('Title', width='medium'),
            'Company': st.column_config.TextColumn('Company', width='large'),
            'Person Location': st.column_config.TextColumn('Person Location', width='medium'),
            'Company HQ': st.column_config.TextColumn('Company HQ', width='small'),
            'Work Mode': st.column_config.TextColumn('Work Mode', width='small'),
            'Email': st.column_config.TextColumn('Email', width='medium'),
        },
        height=600,
    )
    
    # Summary stats below table
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        avg_score = sum(float(d['Probability Score'].replace('%', '')) for d in table_data) / len(table_data)
        st.metric("Average Probability Score", f"{avg_score:.1f}%")
    with col2:
        with_email = sum(1 for d in table_data if d['Email'] != '—')
        st.metric("Leads with Email", f"{with_email}/{len(table_data)}")
    with col3:
        industry_count = sum(1 for d in table_data if d['Work Mode'] == 'Industry')
        st.metric("Industry Leads", industry_count)


def render_analytics(leads: List[Dict]):
    """Render analytics view."""
    if not leads:
        st.info("No data available for analytics.")
        return
    
    st.subheader("📊 Lead Analytics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Lead Tier Distribution")
        ChartComponents.tier_distribution(leads)
    
    with col2:
        st.markdown("#### Source Distribution")
        ChartComponents.source_distribution(leads)
    
    st.markdown("---")
    
    # Score distribution
    st.markdown("#### Score Distribution")
    scores = [lead.get('score', 0) for lead in leads]
    df = pd.DataFrame({'Score': scores})
    st.bar_chart(df['Score'].value_counts().sort_index())
    
    # Top institutions
    st.markdown("---")
    st.markdown("#### Top Institutions")
    inst_counts = {}
    for lead in leads:
        inst = lead.get('institution', 'Unknown')
        inst_counts[inst] = inst_counts.get(inst, 0) + 1
    
    top_inst = sorted(inst_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    df = pd.DataFrame(top_inst, columns=['Institution', 'Lead Count'])
    st.dataframe(df, use_container_width=True)


def render_export(leads: List[Dict]):
    """Render export options."""
    st.subheader("⬇️ Export Leads")
    
    if not leads:
        st.info("No leads to export.")
        return
    
    # Prepare export data
    export_data = []
    for lead in leads:
        # Handle sources - may be string, list, or NaN
        sources = lead.get('sources', lead.get('source', ''))
        if isinstance(sources, list):
            sources_str = ', '.join(str(s) for s in sources if s)
        elif isinstance(sources, str) and sources != 'nan':
            sources_str = sources
        else:
            sources_str = ''
        
        # Handle research_focus - may be string, list, or NaN
        research_focus = lead.get('research_focus', [])
        if isinstance(research_focus, list):
            focus_str = '; '.join(str(f) for f in research_focus[:5] if f)
        elif isinstance(research_focus, str) and research_focus != 'nan':
            focus_str = research_focus
        else:
            focus_str = ''
        
        # Helper to safely get string values
        def safe_str(val):
            if val is None or (isinstance(val, float) and str(val) == 'nan'):
                return ''
            return str(val) if val else ''
        
        export_data.append({
            'Name': safe_str(lead.get('name', '')),
            'Email': safe_str(lead.get('email', '')),
            'Title': safe_str(lead.get('title', '')),
            'Institution': safe_str(lead.get('institution', '')),
            'Department': safe_str(lead.get('department', '')),
            'Location': safe_str(lead.get('location', '')),
            'Score': lead.get('score', 0),
            'Tier': safe_str(lead.get('tier', '')),
            'Sources': sources_str,
            'Research Focus': focus_str,
            'Publications': lead.get('publications', 0),
            'ORCID': safe_str(lead.get('orcid', '')),
        })
    
    df = pd.DataFrame(export_data)
    
    # Display preview
    st.markdown("#### Preview")
    st.dataframe(df.head(10), use_container_width=True)
    
    st.markdown("---")
    
    # Export buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name="bioleads_export.csv",
            mime="text/csv",
        )
    
    with col2:
        json_str = df.to_json(orient='records', indent=2)
        st.download_button(
            label="📥 Download JSON",
            data=json_str,
            file_name="bioleads_export.json",
            mime="application/json",
        )
    
    with col3:
        # Excel export requires openpyxl
        try:
            from io import BytesIO
            buffer = BytesIO()
            df.to_excel(buffer, index=False)
            buffer.seek(0)
            st.download_button(
                label="📥 Download Excel",
                data=buffer,
                file_name="bioleads_export.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        except ImportError:
            st.info("Install openpyxl for Excel export")


# Run the app
if __name__ == "__main__":
    create_app()
