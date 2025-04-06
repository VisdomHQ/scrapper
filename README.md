# Visdom Scraper

A command-line tool to scrape entire websites, download document files, and convert them to markdown files, preserving the site's URL hierarchy.

## Features

- Scrapes entire websites, following all sublinks within the same domain
- Downloads document files (PDFs, DOCX, Excel, etc.) found on websites
- Converts HTML to markdown using the `markitdown` tool (with fallback to `html2text`)
- Organizes markdown files in a folder structure mirroring the website's URL hierarchy
- Supports both static and dynamic (JavaScript-rendered) websites
- Run scraping jobs in the background
- Provides job management and log viewing tools
- Handles multiple URLs efficiently with concurrent processing
- Respects robots.txt and implements rate limiting

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

## Usage

### Basic Scraping

```bash
# Basic usage with URLs as arguments
visdom-scraper scrape https://example.com https://home.gov.rw

# Using a file with URLs (one per line)
visdom-scraper scrape --input urls.txt

# Specify output directory
visdom-scraper scrape --input urls.txt --output scraped_data

# Enable dynamic scraping for JavaScript-rendered content
visdom-scraper scrape --input urls.txt --dynamic

# Set custom rate limit (2 seconds between requests)
visdom-scraper scrape --input urls.txt --rate 2

# Skip downloading files from websites
visdom-scraper scrape --input urls.txt --no-files

# Save detailed logs to a file
visdom-scraper scrape --input urls.txt --log scraper.log
```

### Background Processing

```bash
# Run a scraping job in the background
visdom-scraper scrape --daemon https://example.com

# List all scraper jobs
visdom-scraper jobs

# Check the status of a specific job
visdom-scraper job-status 20230718_123045

# View the log file for a job
visdom-scraper tail-log 20230718_123045

# View the log file and follow new entries (like tail -f)
visdom-scraper tail-log 20230718_123045 --follow

# Stop a running job
visdom-scraper stop-job 20230718_123045
```

### Command-line Options

#### Scrape Command
- `--input`, `-i`: File containing URLs to scrape (one per line)
- `--output`, `-o`: Directory to save the scraped data (default: `scraped_data`)
- `--dynamic`, `-d`: Use dynamic scraping for JavaScript-rendered content
- `--no-files`: Skip downloading files from websites
- `--workers`, `-w`: Maximum number of concurrent workers (default: 3)
- `--site-workers`, `-s`: Maximum number of concurrent workers per site (default: 10)
- `--rate`, `-r`: Rate limit in seconds between requests (default: 1)
- `--max-sites`, `-m`: Maximum number of sites to process in parallel (default: 2)
- `--max-pages`, `-p`: Maximum pages per site; 0 for unlimited (default: 0)
- `--log`, `-l`: Path to the log file
- `--daemon`: Run the scraper in the background

#### Log Tailing
- `--lines`, `-n`: Number of lines to show initially (default: 10)
- `--follow`, `-f`: Follow the log file continuously (like `tail -f`)

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
│       └── report.pdf
├── home.gov.rw/
│   ├── index.md           # https://home.gov.rw
│   ├── services.md        # https://home.gov.rw/services
│   └── files/             # All downloaded files from home.gov.rw
│       └── annual_report.pdf
```

## Job Management

Background jobs are stored in `~/.visdom_scraper/jobs/` with their logs and status information. Each job has:

- A unique timestamp-based job ID
- A JSON metadata file with job status and configuration
- A log file that can be viewed with the `tail-log` command

## Performance Considerations

- For large websites, consider running in the background with `--daemon`
- Adjust the number of workers with `--workers` and `--site-workers` based on your system capabilities
- Use `--max-sites` to control how many websites are processed simultaneously

## License

MIT
