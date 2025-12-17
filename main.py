#!/usr/bin/env python
# BioLeads - CLI Entry Point
"""
Command-line interface for BioLeads lead generation system.

Usage:
    python main.py scrape [--source SOURCE] [--limit LIMIT]
    python main.py enrich
    python main.py score
    python main.py export [--format FORMAT] [--output PATH]
    python main.py dashboard
    python main.py run [--all] [--limit LIMIT]
"""

import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))


def setup_logging(level: str = 'INFO'):
    """Set up logging configuration."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
        ]
    )


def cmd_scrape(args):
    """Run scrapers to collect leads."""
    from bioleads.pipeline import PipelineOrchestrator
    
    print("🔍 Starting lead scraping...")
    
    sources = None
    if args.source and args.source != 'all':
        sources = [args.source]
    
    orchestrator = PipelineOrchestrator(parallel=not args.sequential)
    leads = orchestrator._run_scrapers(sources, args.limit)
    
    # Save raw leads
    from bioleads.config.settings import settings
    import json
    
    output_file = settings.storage.raw_path / 'scraped_leads.json'
    with open(output_file, 'w') as f:
        json.dump(leads, f, indent=2, default=str)
    
    print(f"✅ Scraped {len(leads)} leads")
    print(f"   Saved to: {output_file}")
    
    return leads


def cmd_enrich(args):
    """Run enrichment on scraped leads."""
    from bioleads.enrichment import EmailFinder, LocationResolver, CompanyEnricher
    from bioleads.config.settings import settings
    import json
    
    print("📧 Starting lead enrichment...")
    
    # Load scraped leads
    input_file = settings.storage.raw_path / 'scraped_leads.json'
    if not input_file.exists():
        print("❌ No scraped leads found. Run 'scrape' first.")
        return None
    
    with open(input_file, 'r') as f:
        leads = json.load(f)
    
    print(f"   Loaded {len(leads)} leads")
    
    # Run enrichment
    email_finder = EmailFinder()
    leads = email_finder.batch_find_emails(leads)
    print("   ✓ Email enrichment complete")
    
    location_resolver = LocationResolver()
    leads = location_resolver.batch_resolve(leads)
    print("   ✓ Location enrichment complete")
    
    company_enricher = CompanyEnricher()
    leads = company_enricher.batch_enrich(leads)
    print("   ✓ Company enrichment complete")
    
    # Save enriched leads
    output_file = settings.storage.processed_path / 'enriched_leads.json'
    with open(output_file, 'w') as f:
        json.dump(leads, f, indent=2, default=str)
    
    emails_found = sum(1 for l in leads if l.get('email'))
    print(f"✅ Enriched {len(leads)} leads ({emails_found} with email)")
    print(f"   Saved to: {output_file}")
    
    return leads


def cmd_score(args):
    """Score and rank leads."""
    from bioleads.scoring import PropensityEngine
    from bioleads.pipeline import Deduplicator
    from bioleads.config.settings import settings
    import json
    
    print("📊 Starting lead scoring...")
    
    # Load enriched leads
    input_file = settings.storage.processed_path / 'enriched_leads.json'
    if not input_file.exists():
        # Try raw leads if enriched not available
        input_file = settings.storage.raw_path / 'scraped_leads.json'
    
    if not input_file.exists():
        print("❌ No leads found. Run 'scrape' first.")
        return None
    
    with open(input_file, 'r') as f:
        leads = json.load(f)
    
    print(f"   Loaded {len(leads)} leads")
    
    # Deduplicate first
    deduplicator = Deduplicator()
    leads = deduplicator.deduplicate(leads)
    print(f"   ✓ Deduplicated to {len(leads)} unique leads")
    
    # Score leads
    engine = PropensityEngine()
    leads = engine.score_batch(leads)
    print("   ✓ Scoring complete")
    
    # Save scored leads
    output_file = settings.storage.output_path / 'leads.json'
    with open(output_file, 'w') as f:
        json.dump(leads, f, indent=2, default=str)
    
    # Print summary
    summary = engine.get_tier_summary(leads)
    print(f"""
✅ Scored {len(leads)} leads

📈 Summary:
   🔥 Hot leads:  {summary['by_tier']['hot']}
   🌡️  Warm leads: {summary['by_tier']['warm']}
   ❄️  Cold leads: {summary['by_tier']['cold']}
   
   Saved to: {output_file}
""")
    
    return leads


def cmd_export(args):
    """Export leads to specified format."""
    from bioleads.pipeline import PipelineOrchestrator
    from bioleads.config.settings import settings
    from pathlib import Path
    import json
    
    print("📤 Exporting leads...")
    
    # Load scored leads
    input_file = settings.storage.output_path / 'leads.json'
    if not input_file.exists():
        print("❌ No scored leads found. Run 'score' first.")
        return
    
    with open(input_file, 'r') as f:
        leads = json.load(f)
    
    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = settings.storage.output_path / f'leads_export'
    
    # Export
    orchestrator = PipelineOrchestrator()
    orchestrator.scored_leads = leads
    filepath = orchestrator.export(output_path, format=args.format)
    
    print(f"✅ Exported {len(leads)} leads to {filepath}")


def cmd_dashboard(args):
    """Launch Streamlit dashboard."""
    import subprocess
    
    print("🚀 Launching dashboard...")
    print("   Access at: http://localhost:8501")
    print("   Press Ctrl+C to stop\n")
    
    dashboard_path = Path(__file__).parent / 'bioleads' / 'dashboard' / 'app.py'
    
    subprocess.run([
        sys.executable, '-m', 'streamlit', 'run',
        str(dashboard_path),
        '--server.headless', 'true',
    ])


def cmd_run(args):
    """Run the complete pipeline."""
    from bioleads.pipeline import PipelineOrchestrator
    from bioleads.config.settings import settings
    
    print("""
╔═══════════════════════════════════════════════════════════════╗
║               BioLeads - Lead Generation Pipeline              ║
║        B2B Leads for 3D In-Vitro Models in Drug Discovery      ║
╚═══════════════════════════════════════════════════════════════╝
""")
    
    orchestrator = PipelineOrchestrator(
        parallel=not args.sequential,
        max_workers=args.workers,
    )
    
    sources = None
    if args.source and args.source != 'all':
        sources = args.source.split(',')
    
    output_path = settings.storage.output_path / 'leads'
    
    leads = orchestrator.run(
        sources=sources,
        max_results_per_source=args.limit,
        skip_enrichment=args.skip_enrichment,
        output_path=output_path,
    )
    
    # Print summary
    summary = orchestrator.get_summary()
    
    print(f"""
╔═══════════════════════════════════════════════════════════════╗
║                        Pipeline Complete!                       ║
╠═══════════════════════════════════════════════════════════════╣
║  Total Leads Generated: {summary['total_leads']:>5}                               ║
║  Duplicates Removed:    {summary['duplicates_removed']:>5}                               ║
║  Average Score:         {summary['average_score']:>5.1f}                               ║
║                                                                 ║
║  Tier Breakdown:                                                ║
║    🔥 Hot:   {summary['tiers']['hot']:>4}                                            ║
║    🌡️  Warm:  {summary['tiers']['warm']:>4}                                            ║
║    ❄️  Cold:  {summary['tiers']['cold']:>4}                                            ║
║                                                                 ║
║  With Email: {summary['leads_with_email']:>4}                                            ║
╚═══════════════════════════════════════════════════════════════╝

📁 Output saved to: {output_path}

🚀 Next steps:
   1. Review leads: python main.py dashboard
   2. Export to CRM: python main.py export --format csv
""")
    
    return leads


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='BioLeads - B2B Lead Generation for 3D In-Vitro Models',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging',
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Scrape command
    scrape_parser = subparsers.add_parser('scrape', help='Scrape leads from sources')
    scrape_parser.add_argument(
        '--source', '-s',
        choices=['all', 'pubmed', 'nih', 'openalex', 'clinicaltrials'],
        default='all',
        help='Source to scrape (default: all)',
    )
    scrape_parser.add_argument(
        '--limit', '-l',
        type=int,
        default=100,
        help='Maximum results per source (default: 100)',
    )
    scrape_parser.add_argument(
        '--sequential',
        action='store_true',
        help='Run scrapers sequentially (default: parallel)',
    )
    
    # Enrich command
    enrich_parser = subparsers.add_parser('enrich', help='Enrich scraped leads')
    
    # Score command
    score_parser = subparsers.add_parser('score', help='Score and rank leads')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export leads')
    export_parser.add_argument(
        '--format', '-f',
        choices=['csv', 'json', 'excel'],
        default='csv',
        help='Export format (default: csv)',
    )
    export_parser.add_argument(
        '--output', '-o',
        type=str,
        help='Output file path',
    )
    
    # Dashboard command
    dashboard_parser = subparsers.add_parser('dashboard', help='Launch web dashboard')
    
    # Run command (full pipeline)
    run_parser = subparsers.add_parser('run', help='Run complete pipeline')
    run_parser.add_argument(
        '--source', '-s',
        type=str,
        default='all',
        help='Sources to scrape (comma-separated or "all")',
    )
    run_parser.add_argument(
        '--limit', '-l',
        type=int,
        default=100,
        help='Maximum results per source (default: 100)',
    )
    run_parser.add_argument(
        '--sequential',
        action='store_true',
        help='Run scrapers sequentially',
    )
    run_parser.add_argument(
        '--workers', '-w',
        type=int,
        default=4,
        help='Number of parallel workers (default: 4)',
    )
    run_parser.add_argument(
        '--skip-enrichment',
        action='store_true',
        help='Skip enrichment stage for faster processing',
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = 'DEBUG' if args.verbose else 'INFO'
    setup_logging(log_level)
    
    # Execute command
    if args.command == 'scrape':
        cmd_scrape(args)
    elif args.command == 'enrich':
        cmd_enrich(args)
    elif args.command == 'score':
        cmd_score(args)
    elif args.command == 'export':
        cmd_export(args)
    elif args.command == 'dashboard':
        cmd_dashboard(args)
    elif args.command == 'run':
        cmd_run(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
