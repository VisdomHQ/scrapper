"""
Module for URL processing, validation, and path generation.
"""

import os
import re
from urllib.parse import ParseResult, urlparse
from slugify import slugify

def validate_url(url: str) -> bool:
    """
    Validate if the given string is a proper URL.
    
    Args:
        url: URL string to validate
        
    Returns:
        bool: True if the URL is valid, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

def normalize_url(url: str) -> str:
    """
    Normalize the URL by removing trailing slashes, query parameters, and fragments.
    
    Args:
        url: URL to normalize
        
    Returns:
        str: Normalized URL
    """
    parsed = urlparse(url)
    
    # Remove trailing slashes
    path = parsed.path.rstrip('/')
    if not path:
        path = '/'
    
    # Reconstruct the URL without query parameters and fragments
    return f"{parsed.scheme}://{parsed.netloc}{path}"

def is_same_domain(url: str, base_url: str) -> bool:
    """
    Check if the URL is from the same domain as the base URL.
    
    Args:
        url: URL to check
        base_url: Base URL to compare against
        
    Returns:
        bool: True if the URL is from the same domain, False otherwise
    """
    url_parsed = urlparse(url)
    base_parsed = urlparse(base_url)
    return url_parsed.netloc == base_parsed.netloc

def is_downloadable_file(url: str) -> bool:
    """
    Check if the URL points to a document file that should be downloaded.
    Only allows document file types (PDF, DOCX, TXT, Excel, etc.)
    
    Args:
        url: URL to check
        
    Returns:
        bool: True if the URL is likely a downloadable document file
    """
    # File extensions that represent document files we want to download
    document_extensions = [
        # Documents
        '.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx', '.csv',
        '.odt', '.ods', '.odp', '.rtf', '.txt',
        
        # Data files
        '.json', '.xml'
    ]
    
    parsed = urlparse(url)
    path = parsed.path.lower()
    
    # Check if URL path ends with any of the document extensions
    for ext in document_extensions:
        if path.endswith(ext):
            return True
    
    # If a URL has a query string but path looks like a document file, it might be a download link
    if '?' in url:
        path_before_query = path.split('?')[0]
        for ext in document_extensions:
            if path_before_query.endswith(ext):
                return True
    
    # Check for document download-specific patterns in URLs
    if 'download' in url.lower() or 'document' in url.lower() or 'file' in url.lower():
        for ext in document_extensions:
            if ext in url.lower():
                return True
        if 'pdf' in url.lower() or 'doc' in url.lower() or 'excel' in url.lower():
            return True
        if 'filename=' in url.lower() or 'file=' in url.lower():
            for ext in document_extensions:
                if ext in url.lower():
                    return True
    
    return False

def url_to_filepath(url: str, output_dir: str) -> tuple:
    """
    Convert a URL to a file path that mirrors the website's URL hierarchy.
    
    Args:
        url: URL to convert
        output_dir: Base directory for output
        
    Returns:
        tuple: (directory, filename) where the markdown should be saved
    """
    parsed = urlparse(url)
    domain = parsed.netloc
    path = parsed.path.strip('/')
    
    # Handle the domain directory
    domain_dir = os.path.join(output_dir, domain)
    
    if not path:
        # This is the main page
        return domain_dir, 'index.md'
    
    path_parts = path.split('/')
    if len(path_parts) == 1:
        # This is a direct subpage of the main page
        return domain_dir, f"{slugify(path_parts[0])}.md"
    else:
        # This is a deeper subpage
        filename = f"{slugify(path_parts[-1])}.md"
        directory = os.path.join(domain_dir, '/'.join(slugify(part) for part in path_parts[:-1]))
        return directory, filename

def url_to_files_dir(url: str, output_dir: str) -> str:
    """
    Convert a URL to a directory path for storing associated files.
    
    Args:
        url: URL to convert
        output_dir: Base directory for output
        
    Returns:
        str: Directory path where files should be stored
    """
    parsed = urlparse(url)
    domain = parsed.netloc
    
    # Create a files subdirectory under the domain directory
    files_dir = os.path.join(output_dir, domain, 'files')
    return files_dir
