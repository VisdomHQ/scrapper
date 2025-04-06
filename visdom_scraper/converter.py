"""
Module for converting HTML content to markdown using markitdown.
"""

import os
import subprocess
import logging
import tempfile

class MarkdownConverter:
    def __init__(self):
        """Initialize the markdown converter."""
        self.logger = logging.getLogger('visdom_scraper')
        self._has_checked_markitdown = False
        self._markitdown_available = None
        self._html2text = None
        
    def check_markitdown_installed(self):
        """
        Check if the markitdown tool is installed.
        
        Returns:
            bool: True if markitdown is installed, False otherwise
        """
        if self._has_checked_markitdown:
            return self._markitdown_available
            
        try:
            subprocess.run(['markitdown', '--version'], 
                          stdout=subprocess.PIPE, 
                          stderr=subprocess.PIPE, 
                          check=False)
            self._markitdown_available = True
        except FileNotFoundError:
            self._markitdown_available = False
            self.logger.warning("markitdown command not found. Will use html2text fallback instead.")
            self.logger.info("For better conversion quality, install markitdown: pip install markitdown[all]")
            
        self._has_checked_markitdown = True
        return self._markitdown_available
    
    def _ensure_html2text(self):
        """Ensure html2text is available for fallback conversion."""
        if self._html2text is None:
            try:
                import html2text
                self._html2text = html2text.HTML2Text()
                self._html2text.ignore_links = False
                self._html2text.ignore_images = False
                self._html2text.ignore_tables = False
                self._html2text.body_width = 0  # No wrapping
                return True
            except ImportError:
                self.logger.error("html2text is not installed. Please install it: pip install html2text")
                return False
        return True
    
    def _convert_with_markitdown(self, html_content, url):
        """Convert HTML to markdown using markitdown tool."""
        try:
            with tempfile.NamedTemporaryFile('w', suffix='.html', delete=False) as temp_html:
                temp_html.write(html_content)
                temp_html_path = temp_html.name
                
            with tempfile.NamedTemporaryFile('w', suffix='.md', delete=False) as temp_md:
                temp_md_path = temp_md.name
            
            self.logger.debug(f"Converting {url} to markdown using markitdown")
            
            result = subprocess.run(
                ['markitdown', temp_html_path, '-o', temp_md_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                self.logger.error(f"markitdown conversion failed for {url}: {result.stderr}")
                return None
                
            with open(temp_md_path, 'r', encoding='utf-8') as md_file:
                markdown_content = md_file.read()
                
            return markdown_content
            
        except Exception as e:
            self.logger.error(f"Error converting HTML to markdown with markitdown for {url}: {e}")
            return None
            
        finally:
            # Clean up temporary files
            if 'temp_html_path' in locals():
                try:
                    os.unlink(temp_html_path)
                except:
                    pass
                    
            if 'temp_md_path' in locals():
                try:
                    os.unlink(temp_md_path)
                except:
                    pass
    
    def _convert_with_html2text(self, html_content, url):
        """Convert HTML to markdown using html2text library as fallback."""
        if not self._ensure_html2text():
            return None
            
        try:
            self.logger.debug(f"Converting {url} to markdown using html2text fallback")
            markdown_content = self._html2text.handle(html_content)
            return markdown_content
        except Exception as e:
            self.logger.error(f"Error converting HTML to markdown with html2text for {url}: {e}")
            return None
    
    def convert_html_to_markdown(self, html_content, url):
        """
        Convert HTML content to markdown using markitdown or fallback to html2text.
        
        Args:
            html_content: HTML content to convert
            url: URL of the page (for logging)
            
        Returns:
            str or None: Markdown content if successful, None otherwise
        """
        if self.check_markitdown_installed():
            return self._convert_with_markitdown(html_content, url)
        else:
            return self._convert_with_html2text(html_content, url)
