# BioLeads Streamlit Dashboard
"""
Entry point for Streamlit Cloud deployment.
This file loads the leads data and displays the dashboard.
"""

import json
import sys
from pathlib import Path
from typing import List, Dict

import streamlit as st
import pandas as pd

# Page config
st.set_page_config(
    page_title="BioLeads - Lead Generation Dashboard",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for dark mode compatibility
st.markdown("""
    <style>
    /* Main container padding */
    .main > div {
        padding-top: 2rem;
    }
    
    /* Metric boxes with dark-mode friendly colors */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        color: #00d4ff !important;
    }
    
    [data-testid="stMetricLabel"] {
        color: #ffffff !important;
    }
    
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);
        padding: 1rem;
        border-radius: 0.75rem;
        border: 1px solid #3a7ca5;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    
    /* Header styling */
    h1 {
        color: #00d4ff !important;
    }
    
    /* Subheader styling */
    h2, h3 {
        color: #7dd3fc !important;
    }
    
    /* Table styling for dark mode */
    .stDataFrame {
        background-color: #1a1a2e;
        border-radius: 0.5rem;
    }
    
    /* Download button styling */
    .stDownloadButton > button {
        background: linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%);
        color: white;
        border: none;
        padding: 0.75rem 2rem;
        font-weight: 600;
    }
    
    .stDownloadButton > button:hover {
        background: linear-gradient(135deg, #0284c7 0%, #0891b2 100%);
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #0f172a;
    }
    </style>
""", unsafe_allow_html=True)

# Header
st.title("🧬 BioLeads Dashboard")
st.markdown("*B2B Lead Generation for 3D In-Vitro Models*")
st.markdown("---")


def load_leads() -> List[Dict]:
    """Load leads from the data directory."""
    # Try to load from session state first
    if 'leads' in st.session_state and st.session_state.leads:
        return st.session_state.leads
    
    # Try to load from file
    try:
        # Get the directory where this script is located
        base_path = Path(__file__).parent / 'data' / 'output'
        
        # Try CSV first
        csv_path = base_path / 'leads.csv'
        if csv_path.exists():
            df = pd.read_csv(csv_path)
            leads = df.to_dict('records')
            st.session_state.leads = leads
            return leads
        
        # Try JSON
        json_path = base_path / 'leads.json'
        if json_path.exists():
            with open(json_path, 'r') as f:
                leads = json.load(f)
                st.session_state.leads = leads
                return leads
    except Exception as e:
        st.error(f"Error loading leads: {e}")
    
    return []


def safe_str(val):
    """Safely convert value to string, handling NaN."""
    if val is None:
        return ''
    if isinstance(val, float):
        import math
        if math.isnan(val):
            return ''
    return str(val) if val else ''


# Load leads
leads = load_leads()

if not leads:
    st.warning("No leads data found. Please run the pipeline first or upload a CSV file.")
    
    # File uploader
    uploaded_file = st.file_uploader("Upload leads CSV", type=['csv'])
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        leads = df.to_dict('records')
        st.session_state.leads = leads
        st.rerun()
else:
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Leads", len(leads))
    with col2:
        hot = sum(1 for l in leads if safe_str(l.get('tier')) == 'hot')
        st.metric("🔥 Hot Leads", hot)
    with col3:
        warm = sum(1 for l in leads if safe_str(l.get('tier')) == 'warm')
        st.metric("🌡️ Warm Leads", warm)
    with col4:
        with_email = sum(1 for l in leads if l.get('email') and safe_str(l.get('email')) not in ['', 'nan'])
        st.metric("📧 With Email", with_email)
    
    st.markdown("---")
    
    # Sort leads by score
    sorted_leads = sorted(leads, key=lambda x: x.get('score', 0), reverse=True)
    
    # Prepare table data
    table_data = []
    for rank, lead in enumerate(sorted_leads, 1):
        # Handle location
        location = safe_str(lead.get('location', ''))
        if location == 'nan':
            location = ''
        
        # Get country from location
        company_hq = ''
        if location:
            parts = location.split(',')
            company_hq = parts[-1].strip() if parts else ''
        
        table_data.append({
            'Rank': rank,
            'Probability Score': f"{lead.get('score', 0):.1f}%",
            'Name': safe_str(lead.get('name', 'N/A')),
            'Title': safe_str(lead.get('title', '')) or 'Researcher',
            'Company': safe_str(lead.get('institution', 'N/A')),
            'Person Location': location or 'N/A',
            'Company HQ': company_hq or 'N/A',
            'Work Mode': 'Research',
            'Email': safe_str(lead.get('email', '')) or '—',
        })
    
    # Display the table
    st.subheader(f"📋 Lead Dashboard - {len(leads)} Leads")
    
    df = pd.DataFrame(table_data)
    
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        height=600,
    )
    
    # Summary stats
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        avg_score = sum(lead.get('score', 0) for lead in leads) / len(leads)
        st.metric("Average Score", f"{avg_score:.1f}%")
    with col2:
        st.metric("Leads with Email", f"{with_email}/{len(leads)}")
    with col3:
        st.metric("Data Sources", "PubMed, NIH, OpenAlex, ClinicalTrials")
    
    # Export section
    st.markdown("---")
    st.subheader("⬇️ Export Leads")
    
    csv = df.to_csv(index=False)
    st.download_button(
        label="📥 Download CSV",
        data=csv,
        file_name="bioleads_export.csv",
        mime="text/csv",
    )
