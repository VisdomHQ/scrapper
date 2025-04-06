"""
Command-line interface for the website scraper.
"""

import sys
import time
import click
from .main import WebsiteScraperApp
from .daemon import ScraperDaemon, LogTailer

@click.group()
def cli():
    """Visdom Scraper - A tool to scrape websites and convert them to markdown."""
    pass

@cli.command(name="scrape")
@click.option('--input', '-i', help='File containing URLs to scrape (one per line)')
@click.option('--output', '-o', default='scraped_data', help='Directory to save the scraped data')
@click.option('--dynamic', '-d', is_flag=True, help='Use dynamic scraping (for JavaScript-rendered content)')
@click.option('--no-files', is_flag=True, help='Do not download files from websites')
@click.option('--workers', '-w', default=3, type=int, help='Maximum number of concurrent workers')
@click.option('--site-workers', '-s', default=10, type=int, help='Maximum number of concurrent workers per site')
@click.option('--rate', '-r', default=1.0, type=float, help='Rate limit in seconds between requests')
@click.option('--max-sites', '-m', default=2, type=int, help='Maximum number of sites to process in parallel')
@click.option('--max-pages', '-p', default=0, type=int, help='Maximum pages per site (0 for unlimited)')
@click.option('--log', '-l', help='Path to the log file')
@click.option('--daemon', is_flag=True, help='Run the scraper in the background')
@click.option('--job-id', hidden=True, help='Internal: Job ID for the daemon process')
@click.argument('urls', nargs=-1)
def scrape(input, output, dynamic, no_files, workers, site_workers, rate, max_sites, max_pages, log, daemon, job_id, urls):
    """
    Scrape websites and convert them to markdown.
    
    You can provide URLs directly as arguments or in a file (one per line).
    Document files (PDF, DOCX, etc.) will be automatically downloaded.
    
    Example: visdom-scraper scrape https://example.com https://home.gov.rw
    """
    if not urls and not input:
        click.echo("Error: No URLs provided. Use --input to specify a file or pass URLs as arguments.")
        return 1
    
    # If daemon flag is set, start a background process
    if daemon:
        daemon_mgr = ScraperDaemon()
        job_id = daemon_mgr.start_job(sys.argv[1:])  # Pass all arguments
        click.echo(f"Started background job with ID: {job_id}")
        click.echo(f"You can check the status with: visdom-scraper job-status {job_id}")
        click.echo(f"You can view logs with: visdom-scraper tail-log {job_id}")
        return 0
        
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

@cli.command(name="jobs")
def list_jobs():
    """List all scraper jobs and their status."""
    daemon_mgr = ScraperDaemon()
    jobs = daemon_mgr.list_jobs()
    
    if not jobs:
        click.echo("No jobs found.")
        return
    
    # Print header
    click.echo(f"{'JOB ID':<16} {'STATUS':<12} {'START TIME':<24}")
    click.echo("-" * 52)
    
    # Print job details
    for job in jobs:
        job_id = job["job_id"]
        status = job["status"]
        start_time = job["start_time"].split(".")[0].replace("T", " ")  # Format datetime
        
        click.echo(f"{job_id:<16} {status:<12} {start_time:<24}")

@cli.command(name="job-status")
@click.argument('job_id')
def job_status(job_id):
    """Check the status of a specific job."""
    daemon_mgr = ScraperDaemon()
    job = daemon_mgr.get_job(job_id)
    
    if not job:
        click.echo(f"Job {job_id} not found.")
        return 1
    
    click.echo(f"Job ID: {job['job_id']}")
    click.echo(f"Status: {job['status']}")
    click.echo(f"Started: {job['start_time'].split('.')[0].replace('T', ' ')}")
    click.echo(f"Log file: {job['log_file']}")
    click.echo(f"Command: {' '.join(job['cmd_args'])}")
    
    return 0

@cli.command(name="stop-job")
@click.argument('job_id')
def stop_job(job_id):
    """Stop a running job."""
    daemon_mgr = ScraperDaemon()
    if daemon_mgr.stop_job(job_id):
        click.echo(f"Job {job_id} has been stopped.")
    else:
        click.echo(f"Job {job_id} is not running or not found.")
        return 1
    
    return 0

@cli.command(name="tail-log")
@click.argument('job_id_or_file')
@click.option('--lines', '-n', default=10, help='Number of lines to show initially')
@click.option('--follow', '-f', is_flag=True, help='Follow the log file (like tail -f)')
def tail_log(job_id_or_file, lines, follow):
    """
    Display the log file for a job or any log file.
    
    You can specify a job ID or a direct path to a log file.
    """
    # Check if it's a job ID first
    daemon_mgr = ScraperDaemon()
    job = daemon_mgr.get_job(job_id_or_file)
    
    if job:
        log_file = job["log_file"]
    else:
        # Treat it as a direct file path
        log_file = job_id_or_file
    
    # Create the log tailer
    tailer = LogTailer(log_file, lines)
    
    # Display the log
    if follow:
        click.echo(f"Tailing log file: {log_file} (Press Ctrl+C to stop)")
        for line in tailer.tail_log(follow=True):
            click.echo(line.rstrip())
    else:
        for line in tailer.read_last_lines():
            click.echo(line.rstrip())
    
    return 0

def main():
    """Main entry point for the CLI."""
    # Handle both old-style (direct options) and new-style (with subcommands) invocations
    
    # Check if the first argument is one of our known subcommands
    known_commands = ["scrape", "jobs", "job-status", "stop-job", "tail-log"]
    
    # If no arguments or first arg is an option/URL (not a subcommand), 
    # insert the "scrape" command
    if len(sys.argv) <= 1 or (
        len(sys.argv) > 1 and 
        sys.argv[1] not in known_commands
    ):
        sys.argv.insert(1, "scrape")
    
    try:
        return cli(standalone_mode=False)
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
