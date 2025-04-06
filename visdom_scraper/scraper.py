"""
Core scraping functionality with both static and dynamic options.
"""

import os
import time
import logging
import re
from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from concurrent.futures import ThreadPoolExecutor, as_completed

from .url_processor import normalize_url, is_same_domain, validate_url, is_downloadable_file

class WebsiteScraper:
    def __init__(self, use_dynamic=False, max_workers=5, rate_limit=1, max_pages=0, download_files=True):
        """
        Initialize the scraper.
        
        Args:
            use_dynamic: Whether to use dynamic scraping (Selenium)
            max_workers: Maximum number of concurrent scrapers
            rate_limit: Minimum time between requests in seconds
            max_pages: Maximum number of pages to scrape (0 for unlimited)
            download_files: Whether to download files found on the website
        """
        self.use_dynamic = use_dynamic
        self.max_workers = max_workers
        self.rate_limit = rate_limit
        self.max_pages = max_pages  # 0 means unlimited
        self.download_files = download_files
        self.visited_urls = set()
        self.robot_parsers = {}
        self.logger = logging.getLogger('visdom_scraper')
        self.driver = None
        self.downloaded_files = {}  # Map of URL to local file path
        
        # Setup headless browser for dynamic scraping if needed
        if self.use_dynamic:
            self._setup_driver()
    
    def _setup_driver(self):
        """Set up the headless browser for dynamic scraping."""
        if not self.driver:
            self.logger.info("Initializing headless browser for dynamic content scraping")
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-infobars')
            options.add_argument('--disable-browser-side-navigation')
            options.add_argument('--disable-features=TranslateUI')
            options.add_argument('--disable-translate')
            options.add_argument('--disable-web-security')
            options.add_argument('--disable-client-side-phishing-detection')
            options.add_argument('--mute-audio')
            options.add_argument('--blink-settings=imagesEnabled=false')  # Don't load images
            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=options
            )
    
    def __del__(self):
        """Clean up resources when the scraper is deleted."""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
    
    def _get_robot_parser(self, base_url):
        """
        Get or create a RobotFileParser for the given base_url.
        
        Args:
            base_url: The base URL of the website
            
        Returns:
            RobotFileParser: Parser for the website's robots.txt
        """
        parsed_url = urlparse(base_url)
        domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        if domain not in self.robot_parsers:
            parser = RobotFileParser()
            robots_url = f"{domain}/robots.txt"
            try:
                parser.set_url(robots_url)
                parser.read()
                self.robot_parsers[domain] = parser
            except Exception as e:
                self.logger.warning(f"Failed to parse robots.txt at {robots_url}: {e}")
                # If we can't read robots.txt, we'll allow all URLs
                parser = RobotFileParser()
                parser.allow_all = True
                self.robot_parsers[domain] = parser
                
        return self.robot_parsers[domain]
    
    def is_allowed_by_robots(self, url):
        """Check if the URL is allowed by the website's robots.txt."""
        parser = self._get_robot_parser(url)
        return parser.can_fetch("*", url)
    
    def _get_html_static(self, url):
        """Get HTML content using static scraping (requests)."""
        try:
            headers = {'User-Agent': 'VisdomScraper/0.1.0 (+https://github.com/visdom/scraper)'}
            timeout = 15  # Reduced from 30 to 15 seconds
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response.text
        except Exception as e:
            self.logger.error(f"Error fetching {url}: {e}")
            return None
    
    def _get_html_dynamic(self, url):
        """Get HTML content using dynamic scraping (Selenium)."""
        try:
            if not self.driver:
                self._setup_driver()
                
            self.driver.set_page_load_timeout(15)  # Reduced from default to 15 seconds
            self.driver.get(url)
            time.sleep(1)  # Reduced from 2 seconds to 1
            return self.driver.page_source
        except Exception as e:
            self.logger.error(f"Error fetching {url} with dynamic scraping: {e}")
            return None
    
    def get_html(self, url):
        """
        Get the HTML content of a URL using either static or dynamic scraping.
        
        Args:
            url: URL to scrape
            
        Returns:
            str or None: HTML content if successful, None otherwise
        """
        if not self.is_allowed_by_robots(url):
            self.logger.info(f"Skipping {url} (disallowed by robots.txt)")
            return None
            
        self.logger.info(f"Fetching {url}")
        
        if self.use_dynamic:
            return self._get_html_dynamic(url)
        else:
            return self._get_html_static(url)
    
    def extract_links(self, base_url, html):
        """
        Extract all links from HTML that belong to the same domain.
        
        Args:
            base_url: Base URL for resolving relative links
            html: HTML content to parse
            
        Returns:
            tuple: (list of page URLs, list of file URLs)
        """
        if not html:
            return [], []
            
        soup = BeautifulSoup(html, 'html.parser')
        page_links = []
        file_links = []
        
        # Process all <a> tags
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            
            # Skip anchors, javascript, mailto links
            if href.startswith(('#', 'javascript:', 'mailto:')):
                continue
                
            # Resolve relative URLs
            full_url = urljoin(base_url, href)
            
            # Only include links from the same domain
            if is_same_domain(full_url, base_url):
                normalized_url = normalize_url(full_url)
                if is_downloadable_file(normalized_url):
                    file_links.append(normalized_url)
                else:
                    page_links.append(normalized_url)
        
        # Also check for downloadable links in other tags with src attributes
        for tag in soup.find_all(['img', 'video', 'audio', 'source', 'iframe']):
            if tag.has_attr('src'):
                src = tag['src']
                full_url = urljoin(base_url, src)
                
                if is_same_domain(full_url, base_url) and is_downloadable_file(full_url):
                    file_links.append(full_url)
        
        # Look for links in CSS background styles
        pattern = r'url\(["\']?([^"\'\)]+)["\']?\)'
        for tag in soup.find_all(lambda tag: tag.has_attr('style') and 'url(' in tag['style']):
            matches = re.findall(pattern, tag['style'])
            for match in matches:
                full_url = urljoin(base_url, match)
                if is_same_domain(full_url, base_url) and is_downloadable_file(full_url):
                    file_links.append(full_url)
        
        return page_links, file_links
    
    def download_file(self, url, save_dir):
        """
        Download a file from the given URL.
        
        Args:
            url: URL of the file to download
            save_dir: Directory to save the file in
            
        Returns:
            tuple: (success, local_path or None)
        """
        if not self.is_allowed_by_robots(url):
            self.logger.info(f"Skipping file {url} (disallowed by robots.txt)")
            return False, None
            
        try:
            self.logger.info(f"Downloading file: {url}")
            
            # Create a filename from the URL
            parsed_url = urlparse(url)
            filename = os.path.basename(parsed_url.path)
            
            # If filename is empty or has no extension, generate one
            if not filename or '.' not in filename:
                # Use the last part of path or 'file' as default
                path_parts = [p for p in parsed_url.path.split('/') if p]
                filename = path_parts[-1] if path_parts else 'file'
                
                # Add extension based on content type if possible
                headers = requests.head(url, allow_redirects=True).headers
                content_type = headers.get('Content-Type', '')
                ext = {
                    'application/pdf': '.pdf',
                    'image/jpeg': '.jpg',
                    'image/png': '.png',
                    'text/plain': '.txt',
                    'application/msword': '.doc',
                    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
                    'application/vnd.ms-excel': '.xls',
                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
                    'application/zip': '.zip',
                }.get(content_type.split(';')[0].lower(), '')
                
                if ext and not filename.endswith(ext):
                    filename += ext
            
            # Ensure the filename is valid
            filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
            
            # Save path
            save_path = os.path.join(save_dir, filename)
            
            # Create directory if it doesn't exist
            os.makedirs(save_dir, exist_ok=True)
            
            # Check if we already have this file
            if os.path.exists(save_path):
                base, ext = os.path.splitext(filename)
                counter = 1
                while os.path.exists(save_path):
                    save_path = os.path.join(save_dir, f"{base}_{counter}{ext}")
                    counter += 1
            
            # Download the file
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            self.logger.debug(f"Downloaded {url} to {save_path}")
            return True, save_path
            
        except Exception as e:
            self.logger.error(f"Error downloading file {url}: {e}")
            return False, None
    
    def scrape_website(self, start_url, files_dir=None):
        """
        Scrape an entire website starting from the given URL.
        
        Args:
            start_url: Starting URL for the website
            files_dir: Directory to save downloaded files (None to disable file downloads)
            
        Returns:
            tuple: (pages_dict, files_dict)
                pages_dict: Dictionary mapping URLs to their HTML content
                files_dict: Dictionary mapping URLs to local file paths
        """
        if not validate_url(start_url):
            self.logger.error(f"Invalid URL: {start_url}")
            return {}, {}
            
        start_url = normalize_url(start_url)
        self.logger.info(f"Starting scrape of {start_url}")
        
        # Reset visited URLs and downloaded files for this website
        self.visited_urls = set()
        self.downloaded_files = {}
        to_visit = [start_url]
        pages_results = {}
        all_file_urls = set()
        
        # Create a thread pool for concurrent scraping
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            while to_visit and (self.max_pages == 0 or len(pages_results) < self.max_pages):
                # Process URLs in batches to control concurrency
                batch = to_visit[:self.max_workers]
                to_visit = to_visit[self.max_workers:]
                
                futures = []
                for url in batch:
                    if url in self.visited_urls:
                        continue
                    
                    self.visited_urls.add(url)
                    futures.append(executor.submit(self.get_html, url))
                    time.sleep(self.rate_limit)  # Rate limiting
                
                # Process completed futures
                for future, url in zip(as_completed(futures), batch):
                    html = future.result()
                    if html:
                        pages_results[url] = html
                        
                        # Extract links for more pages and files
                        page_links, file_links = self.extract_links(url, html)
                        
                        # Add file URLs to the set for later downloading
                        all_file_urls.update(file_links)
                        
                        # Add new page links to the queue
                        for link in page_links:
                            if link not in self.visited_urls and link not in to_visit:
                                to_visit.append(link)
                        
                        # Check if we've hit our page limit
                        if self.max_pages > 0 and len(pages_results) >= self.max_pages:
                            self.logger.info(f"Reached maximum page limit ({self.max_pages}) for {start_url}")
                            break
        
        # Download files if enabled
        if self.download_files and files_dir and all_file_urls:
            self.logger.info(f"Downloading {len(all_file_urls)} files from {start_url}")
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = []
                for file_url in all_file_urls:
                    if file_url in self.downloaded_files:  # Skip if already downloaded
                        continue
                    futures.append(executor.submit(self.download_file, file_url, files_dir))
                    time.sleep(self.rate_limit)  # Rate limiting
                
                for future, file_url in zip(as_completed(futures), all_file_urls):
                    success, file_path = future.result()
                    if success:
                        self.downloaded_files[file_url] = file_path
        
        self.logger.info(f"Completed scraping {start_url}. Scraped {len(pages_results)} pages and {len(self.downloaded_files)} files.")
        return pages_results, self.downloaded_files
