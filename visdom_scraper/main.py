"""
Main module for the website scraper and markdown converter.
"""

import os
import time
import logging
import gc
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

from .scraper import WebsiteScraper
from .converter import MarkdownConverter
from .url_processor import url_to_filepath, validate_url, url_to_files_dir
from .utils import setup_logger, ensure_dir_exists, format_duration

class WebsiteScraperApp:
    def __init__(self, 
                 urls=None, 
                 url_file=None, 
                 output_dir="scraped_data", 
                 use_dynamic=False,
                 download_files=True,
                 max_workers=3,  # Reduced default from 5 to 3
                 max_site_workers=10,  # Maximum threads per site
                 rate_limit=1,
                 max_sites_parallel=2,  # Process max 2 sites at once
                 max_pages_per_site=100,  # Limit pages per site for safety
                 log_file=None):
        """
        Initialize the website scraper application.
        
        Args:
            urls: List of URLs to scrape
            url_file: File containing URLs to scrape (one per line)
            output_dir: Directory to save the scraped data
            use_dynamic: Whether to use dynamic scraping (Selenium)
            download_files: Whether to download files from the websites
            max_workers: Maximum number of concurrent workers for multi-site processing
            max_site_workers: Maximum number of concurrent workers per site
            rate_limit: Minimum time between requests in seconds
            max_sites_parallel: Maximum number of sites to process in parallel
            max_pages_per_site: Maximum number of pages to scrape per site (0 for unlimited)
            log_file: Path to the log file
        """
        self.urls = urls or []
        self.url_file = url_file
        self.output_dir = output_dir
        self.use_dynamic = use_dynamic
        self.download_files = download_files
        self.max_workers = max_workers
        self.max_site_workers = max_site_workers
        self.rate_limit = rate_limit
        self.max_sites_parallel = max_sites_parallel
        self.max_pages_per_site = max_pages_per_site
        
        # Setup logging
        self.logger = setup_logger(log_file)
        
        # Initialize scraper and converter
        self.scraper = None  # We'll initialize scrapers per site to conserve memory
        self.converter = MarkdownConverter()
        
        # Load URLs from file if provided
        if self.url_file:
            self._load_urls_from_file()
    
    def _load_urls_from_file(self):
        """Load URLs from the specified file."""
        try:
            with open(self.url_file, 'r') as f:
                for line in f:
                    url = line.strip()
                    if url and validate_url(url):
                        self.urls.append(url)
                    elif url:
                        self.logger.warning(f"Invalid URL in file: {url}")
                        
            self.logger.info(f"Loaded {len(self.urls)} URLs from {self.url_file}")
        except Exception as e:
            self.logger.error(f"Failed to load URLs from file {self.url_file}: {e}")
    
    def _save_markdown(self, url, markdown_content):
        """
        Save the markdown content to a file based on the URL structure.
        
        Args:
            url: The URL of the page
            markdown_content: Markdown content to save
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            directory, filename = url_to_filepath(url, self.output_dir)
            ensure_dir_exists(directory)
            
            filepath = os.path.join(directory, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
                
            self.logger.debug(f"Saved {url} to {filepath}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving markdown for {url}: {e}")
            return False
    
    def _get_markdown_filepath(self, url):
        """Get the full path where a markdown file for the URL would be saved."""
        directory, filename = url_to_filepath(url, self.output_dir)
        return os.path.join(directory, filename)
    
    def _process_website(self, url):
        """
        Process a single website - scrape it and convert to markdown.
        
        Args:
            url: URL of the website to process
            
        Returns:
            tuple: (url, num_pages_scraped, num_pages_converted, num_files_downloaded, duration)
        """
        start_time = time.time()
        self.logger.info(f"Processing website: {url}")
        
        # Extract domain for logging
        domain = urlparse(url).netloc
        
        # Create a files directory for this domain
        files_dir = url_to_files_dir(url, self.output_dir) if self.download_files else None
        if files_dir:
            ensure_dir_exists(files_dir)
        
        # Create a new scraper for this site to ensure clean state
        scraper = WebsiteScraper(
            self.use_dynamic, 
            self.max_site_workers, 
            self.rate_limit,
            max_pages=self.max_pages_per_site,
            download_files=self.download_files
        )
        
        # Scrape the website
        scraped_pages, downloaded_files = scraper.scrape_website(url, files_dir)
        num_pages_scraped = len(scraped_pages)
        num_files_downloaded = len(downloaded_files)
        
        if num_pages_scraped == 0:
            self.logger.warning(f"No pages scraped from {url}")
            duration = time.time() - start_time
            return url, 0, 0, 0, duration
        
        # Convert each page to markdown and save it
        num_pages_converted = 0
        # Process pages in batches to manage memory
        batch_size = 10
        page_items = list(scraped_pages.items())
        
        for i in range(0, len(page_items), batch_size):
            batch = page_items[i:i+batch_size]
            for page_url, html_content in batch:
                markdown_content = self.converter.convert_html_to_markdown(html_content, page_url)
                if markdown_content:
                    # Add links to downloaded files in the markdown if they're from this page
                    if self.download_files and downloaded_files:
                        # Fixed: Create list of tuples with file_url, file_path
                        page_files = [(file_url, file_path) for file_url, file_path in downloaded_files.items() 
                                     if file_url in html_content or page_url in file_url]
                        if page_files:
                            file_links = "\n\n## Downloaded Files\n\n"
                            for file_url, file_path in page_files:
                                filename = os.path.basename(file_path)
                                rel_path = os.path.relpath(file_path, os.path.dirname(self._get_markdown_filepath(page_url)))
                                file_links += f"- [{filename}]({rel_path})\n"
                            markdown_content += file_links
                    
                    if self._save_markdown(page_url, markdown_content):
                        num_pages_converted += 1
            
            # Clear some memory after each batch
            gc.collect()
        
        # Clean up scraper resources explicitly
        scraper = None
        gc.collect()
        
        duration = time.time() - start_time
        self.logger.info(
            f"Completed {domain}: {num_pages_scraped} pages scraped, "
            f"{num_pages_converted} pages converted, {num_files_downloaded} files downloaded "
            f"in {format_duration(duration)}"
        )
        
        return url, num_pages_scraped, num_pages_converted, num_files_downloaded, duration
    
    def run(self):
        """
        Run the website scraper for all URLs.
        
        Returns:
            dict: Dictionary with statistics about the scraping process
        """
        if not self.urls:
            self.logger.error("No URLs to process")
            return {
                "success": False,
                "error": "No URLs to process",
                "websites_processed": 0
            }
        
        self.logger.info(f"Starting to process {len(self.urls)} websites")
        start_time = time.time()
        
        # Create output directory if it doesn't exist
        ensure_dir_exists(self.output_dir)
        
        results = []
        
        # Process sites in batches to limit memory usage
        site_batches = [self.urls[i:i+self.max_sites_parallel] for i in range(0, len(self.urls), self.max_sites_parallel)]
        
        for batch_num, batch in enumerate(site_batches):
            self.logger.info(f"Processing batch {batch_num+1}/{len(site_batches)} ({len(batch)} sites)")
            
            batch_results = []
            with ThreadPoolExecutor(max_workers=min(len(batch), self.max_workers)) as executor:
                futures = [executor.submit(self._process_website, url) for url in batch]
                for future in as_completed(futures):
                    try:
                        batch_results.append(future.result())
                    except Exception as e:
                        self.logger.error(f"Error processing website: {e}")
            
            results.extend(batch_results)
            
            # Force garbage collection between batches
            gc.collect()
            
            # Add a small delay between batches to let resources settle
            if batch_num < len(site_batches) - 1:
                time.sleep(2)
        
        # Compile statistics
        total_duration = time.time() - start_time
        total_pages_scraped = sum(r[1] for r in results)
        total_pages_converted = sum(r[2] for r in results)
        total_files_downloaded = sum(r[3] for r in results)
        
        self.logger.info(
            f"Completed processing {len(results)} websites: "
            f"{total_pages_scraped} pages scraped, "
            f"{total_pages_converted} pages converted, "
            f"{total_files_downloaded} files downloaded "
            f"in {format_duration(total_duration)}"
        )
        
        return {
            "success": True,
            "websites_processed": len(results),
            "pages_scraped": total_pages_scraped,
            "pages_converted": total_pages_converted,
            "files_downloaded": total_files_downloaded,
            "duration_seconds": total_duration,
            "websites": [
                {
                    "url": r[0],
                    "pages_scraped": r[1],
                    "pages_converted": r[2],
                    "files_downloaded": r[3],
                    "duration_seconds": r[4]
                }
                for r in results
            ]
        }
