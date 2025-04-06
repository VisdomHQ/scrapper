"""
Command-line interface for the website scraper.
"""

import sys
import click
from .main import WebsiteScraperApp

@click.command()
@click.option('--input', '-i', help='File containing URLs to scrape (one per line)')
@click.option('--output', '-o', default='scraped_data', help='Directory to save the scraped data')
@click.option('--dynamic', '-d', is_flag=True, help='Use dynamic scraping (for JavaScript-rendered content)')
@click.option('--no-files', is_flag=True, help='Do not download files from websites')
@click.option('--workers', '-w', default=3, type=int, help='Maximum number of concurrent workers')
@click.option('--site-workers', '-s', default=10, type=int, help='Maximum number of concurrent workers per site')
@click.option('--rate', '-r', default=1.0, type=float, help='Rate limit in seconds between requests')
@click.option('--max-sites', '-m', default=2, type=int, help='Maximum number of sites to process in parallel')
@click.option('--max-pages', '-p', default=100, type=int, help='Maximum pages per site (0 for unlimited)')
@click.option('--log', '-l', help='Path to the log file')
@click.argument('urls', nargs=-1)
def main(input, output, dynamic, no_files, workers, site_workers, rate, max_sites, max_pages, log, urls):
    """
    Scrape websites and convert them to markdown.
    
    You can provide URLs directly as arguments or in a file (one per line).
    All website resources and files will be scraped and downloaded by default.
    
    Example: visdom-scraper https://example.com https://home.gov.rw
    """
    if not urls and not input:
        click.echo("Error: No URLs provided. Use --input to specify a file or pass URLs as arguments.")
        return 1
        
    app = WebsiteScraperApp(
        urls=list(urls),
        url_file=input,
        output_dir=output,
        use_dynamic=dynamic,
        download_files=not no_files,
        max_workers=workers,
        max_site_workers=site_workers,
        rate_limit=rate,
        max_sites_parallel=max_sites,
        max_pages_per_site=max_pages,
        log_file=log
    )
    
    result = app.run()
    
    if not result["success"]:
        click.echo(f"Error: {result.get('error', 'Unknown error')}")
        return 1
        
    click.echo(f"\nScraping completed successfully!")
    click.echo(f"Websites processed: {result['websites_processed']}")
    click.echo(f"Pages scraped: {result['pages_scraped']}")
    click.echo(f"Pages converted to markdown: {result['pages_converted']}")
    
    if 'files_downloaded' in result:
        click.echo(f"Files downloaded: {result['files_downloaded']}")
    
    if log:
        click.echo(f"\nDetailed logs saved to: {log}")
    
    click.echo(f"\nOutput saved to: {output}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
