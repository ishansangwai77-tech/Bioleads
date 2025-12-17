# 🧬 BioLeads - B2B Lead Generation Agent

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://bioleads-ai.streamlit.app/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A web scraping and lead scoring system for biotech companies selling **3D in-vitro models** for drug discovery and toxicology.

## 🚀 Live Demo

**👉 [View Live Dashboard](https://bioleads-ai.streamlit.app/)**

## 🎯 Features

- **Multi-Source Scraping**: Collects leads from PubMed, NIH RePORTER, OpenAlex, ClinicalTrials.gov
- **Smart Enrichment**: Email pattern discovery, location resolution, company data
- **Propensity Scoring**: ML-inspired scoring algorithm to rank leads by likelihood to buy
- **Deduplication**: Fuzzy matching to merge leads across sources
- **Interactive Dashboard**: Streamlit-based UI for viewing and exporting leads
- **100% Free APIs**: No paid API subscriptions required

## 📁 Project Structure

```
bioleads/
├── config/           # Configuration settings and keywords
├── scrapers/         # Data source scrapers (PubMed, NIH, OpenAlex, etc.)
├── enrichment/       # Lead enrichment (email, location, company)
├── scoring/          # Propensity scoring engine
├── pipeline/         # Orchestration and deduplication
├── dashboard/        # Streamlit web dashboard
├── data/             # Data storage
│   ├── raw/          # Raw scraped data
│   ├── processed/    # Enriched data
│   └── output/       # Final ranked leads
└── tests/            # Unit tests
```

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
cd WebScarpperProductAI/bioleads

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### Configuration (Optional)

Set environment variables for higher API rate limits:

```bash
# .env file
PUBMED_API_KEY=your_ncbi_api_key  # Get from https://www.ncbi.nlm.nih.gov/account/
OPENALEX_EMAIL=your_email@example.com
```

### Running the Pipeline

```bash
# Run complete pipeline
python main.py run --limit 50

# Or run individual stages
python main.py scrape --source all --limit 50
python main.py enrich
python main.py score
python main.py export --format csv
```

### Launch Dashboard

```bash
python main.py dashboard
# Opens at http://localhost:8501
```

## 📊 Data Sources

| Source | Type | API | Rate Limit |
|--------|------|-----|------------|
| **PubMed** | Publications | E-utilities | 3/sec (10/sec with API key) |
| **NIH RePORTER** | Grants | REST API v2 | ~1/sec |
| **OpenAlex** | Authors & Works | REST API | 10/sec (polite pool) |
| **ClinicalTrials.gov** | Trials | REST API v2 | ~2/sec |

## 🎯 Lead Scoring

Leads are scored on a **0-100 scale** based on:

| Factor | Weight | Description |
|--------|--------|-------------|
| Publications | 15% | Recent publications on relevant topics |
| Grants | 20% | Active NIH/other funding |
| Clinical Trials | 10% | Trial involvement |
| Citations | 5% | Research impact |
| Conference | 10% | Conference presentations |
| Recency | 10% | Activity in last 2 years |
| Role Fit | 10% | Job title match (PI, Director, etc.) |
| Institution Fit | 10% | Company type (pharma, biotech, etc.) |
| Topic Relevance | 10% | Research focus alignment |

### Lead Tiers

- 🔥 **Hot** (75-100): High priority, ready to contact
- 🌡️ **Warm** (50-74): Good potential, needs nurturing
- ❄️ **Cold** (25-49): Lower priority
- 🧊 **Ice** (0-24): Not a good fit

## 🔧 CLI Commands

```bash
# Full pipeline
python main.py run [--source SOURCE] [--limit N] [--skip-enrichment]

# Individual stages
python main.py scrape --source pubmed --limit 100
python main.py scrape --source all --limit 50
python main.py enrich
python main.py score
python main.py export --format csv --output leads.csv

# Dashboard
python main.py dashboard

# Help
python main.py --help
python main.py scrape --help
```

## 📧 Email Discovery

BioLeads uses multiple free methods to discover emails:

1. **ORCID Lookup**: Queries public ORCID profiles
2. **Pattern Generation**: Generates common email patterns (first.last@, flast@, etc.)
3. **Domain Detection**: Identifies institution email domains

Emails include a confidence score (0-1) indicating reliability.

## 🔍 Target Keywords

Pre-configured keywords for 3D in-vitro models:

- Core: `organoid`, `spheroid`, `3D cell culture`, `organ-on-chip`
- Applications: `drug screening`, `toxicology`, `ADMET`, `DILI`
- Targets: `hepatocyte`, `liver organoid`, `tumor organoid`

Customize in `config/keywords.py`.

## 📈 Example Output

```csv
name,email,title,institution,score,tier,research_focus
Dr. Jane Smith,jsmith@harvard.edu,Principal Investigator,Harvard Medical School,87,hot,"organoids, drug screening"
Dr. Michael Chen,mchen@genentech.com,Director of Toxicology,Genentech,92,hot,"in vitro toxicology, organ-on-chip"
```

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=bioleads --cov-report=html
```

## 📝 License

MIT License - see LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📬 Support

For questions or issues, please open a GitHub issue.
