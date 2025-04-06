# Visdom Scraper

A command-line tool to scrape entire websites, download all resources, and convert them to markdown files, preserving the site's URL hierarchy.

## Features

- Scrapes entire websites, following all sublinks within the same domain
- Downloads all files and resources found on the website (documents, images, PDFs, etc.)
- Converts HTML to markdown using the `markitdown` tool (with fallback to `html2text`)
- Organizes markdown files in a folder structure mirroring the website's URL hierarchy
- Supports both static and dynamic (JavaScript-rendered) websites
- Handles multiple URLs efficiently with concurrent processing
- Respects robots.txt and implements rate limiting
- Built-in memory management for large websites

## Installation

### Prerequisites

- Python 3.10+
- Poetry package manager

### Install Visdom Scraper

```bash
# Clone the repository
git clone https://github.com/your-username/visdom-scraper.git
cd visdom-scraper

# Install dependencies with Poetry
poetry install

# Activate the virtual environment
poetry shell
```

### Optional Dependencies

For better markdown conversion quality, markitdown is installed by default. If needed, you can also install extra components:

```bash
# Install markitdown with all optional features
pip install markitdown[all]
```

## Usage

```bash
# Basic usage with URLs as arguments
visdom-scraper https://example.com https://home.gov.rw

# Using a file with URLs (one per line)
visdom-scraper --input urls.txt

# Specify output directory
visdom-scraper --input urls.txt --output scraped_data

# Enable dynamic scraping for JavaScript-rendered content
visdom-scraper --input urls.txt --dynamic

# Set custom rate limit (2 seconds between requests)
visdom-scraper --input urls.txt --rate 2

# Skip downloading files from websites
visdom-scraper --input urls.txt --no-files

# Save detailed logs to a file
visdom-scraper --input urls.txt --log scraper.log
```

### Command-line Options

- `--input`, `-i`: File containing URLs to scrape (one per line)
- `--output`, `-o`: Directory to save the scraped data (default: `scraped_data`)
- `--dynamic`, `-d`: Use dynamic scraping for JavaScript-rendered content
- `--no-files`: Skip downloading files from websites (documents, PDFs, etc.)
- `--workers`, `-w`: Maximum number of concurrent workers (default: 3)
- `--site-workers`, `-s`: Maximum number of concurrent workers per site (default: 10)
- `--rate`, `-r`: Rate limit in seconds between requests (default: 1)
- `--max-sites`, `-m`: Maximum number of sites to process in parallel (default: 2)
- `--max-pages`, `-p`: Maximum pages per site; 0 for unlimited (default: 0)
- `--log`, `-l`: Path to the log file

## Output Structure

The output follows the website's URL hierarchy:

```
scraped_data/
├── example.com/
│   ├── index.md           # https://example.com
│   ├── about.md           # https://example.com/about
│   ├── about/
│   │   └── team.md        # https://example.com/about/team
│   └── files/             # All downloaded files from example.com
│       ├── report.pdf
│       ├── logo.png
│       └── data.xlsx
├── home.gov.rw/
│   ├── index.md           # https://home.gov.rw
│   ├── services.md        # https://home.gov.rw/services
│   └── files/             # All downloaded files from home.gov.rw
│       └── annual_report.pdf
```

## Markdown Conversion

The tool uses one of the following methods to convert HTML to markdown:

1. **markitdown**: Provides high-quality conversion with proper handling of tables and complex layouts.
2. **html2text**: Used as a fallback when there are issues with markitdown. Provides basic conversion capabilities.

## File Downloads

By default, the tool will download all files found on the website, including:

- Documents (PDF, DOC, DOCX, XLS, XLSX, etc.)
- Images (JPG, PNG, GIF, etc.)
- Archives (ZIP, RAR, TAR, etc.)
- Other downloadable resources

Files are stored in a `files` directory under each domain's directory. References to downloaded files are added to the markdown content when appropriate.

## Performance Considerations

- For large websites, you can limit the number of pages scraping using `--max-pages`
- Adjust the number of workers with `--workers` and `--site-workers` based on your system capabilities
- Use `--max-sites` to control how many websites are processed simultaneously
- If you don't need files, use `--no-files` to speed up the process

## License

MIT
