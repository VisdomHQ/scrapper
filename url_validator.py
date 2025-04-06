import requests
import time
import os
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor

def is_valid_url(url):
    """Test if a URL is valid by making a HEAD request"""
    # Ensure URL has a scheme
    if not url.startswith('http://') and not url.startswith('https://'):
        url = 'https://' + url
    
    try:
        # First try a HEAD request which is faster
        response = requests.head(url, timeout=10, allow_redirects=True)
        
        # If HEAD doesn't work, try GET
        if response.status_code >= 400:
            response = requests.get(url, timeout=10, allow_redirects=True)
        
        # Consider 2XX status codes as valid
        return response.status_code < 400
    except requests.exceptions.RequestException:
        return False

def process_url(url):
    """Process a single URL, return the URL if valid, None otherwise"""
    url = url.strip()
    
    # Skip empty lines
    if not url or url.startswith('#'):
        return None
    
    print(f"Testing: {url}")
    if is_valid_url(url):
        print(f"✓ Valid: {url}")
        return url
    else:
        print(f"✗ Invalid: {url}")
        return None

def main():
    input_file = "possible_list.txt"
    output_file = "urls.txt"
    
    # Create output file if it doesn't exist
    if not os.path.exists(output_file):
        open(output_file, 'w').close()
    
    # Read all URLs from input file
    with open(input_file, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]
    
    # Remove duplicates while preserving order
    unique_urls = []
    seen = set()
    for url in urls:
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)
    
    print(f"Testing {len(unique_urls)} unique URLs...")
    
    # Process URLs in parallel for speed
    valid_urls = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(process_url, unique_urls))
        valid_urls = [url for url in results if url]
    
    # Append valid URLs to output file
    with open(output_file, 'a') as f:
        for url in valid_urls:
            f.write(f"{url}\n")
    
    print(f"\nCompleted! Found {len(valid_urls)} valid URLs out of {len(unique_urls)} tested.")
    print(f"Valid URLs saved to {output_file}")

if __name__ == "__main__":
    main()