# RAG Upload Script

This script uploads scraped data from the `scraped_data` directory to a remote RAG (Retrieval-Augmented Generation) server.

## Features

- Supports uploading Markdown, PDF, and Excel files
- Ignores image files
- Concurrent uploads for better performance
- Detailed logging
- Tracks failed uploads for potential retry

## Prerequisites

Since this project uses Poetry for dependency management, install the required dependencies with:

```bash
# Make sure Poetry is installed and configured
poetry install

# Install additional dependencies needed for the upload script
poetry add aiohttp
```

Note: The `asyncio` module is part of the Python standard library, so it doesn't need to be installed separately.

## Usage

Run the script using Poetry from the project directory:

```bash
poetry run python upload_to_rag.py
```

For retrying failed uploads:

```bash
poetry run python retry_failed_uploads.py
```

## Configuration

You can modify the following variables in the script:

- `API_BASE_URL`: The base URL of the RAG server API
- `COLLECTION_ID`: The collection ID for document organization
- `CONCURRENT_UPLOADS`: Number of concurrent uploads (default: 5)
- `SUPPORTED_EXTENSIONS`: File types to upload
- `SKIP_EXTENSIONS`: File types to ignore

## Logs

- Console output shows progress in real-time
- All logs are saved to `upload_log.txt`
- Failed uploads are saved to `failed_uploads.json` for potential retry

## Retry Failed Uploads

If some uploads fail, you can retry them using:

```bash
poetry run python retry_failed_uploads.py
```

## Statistics Analysis

After running the upload process, you can analyze the results to get detailed statistics:

```bash
poetry run python analyze_upload_stats.py
```

Or use the shell script to run the analysis and display a summary:

```bash
./analyze_stats.sh
```

The analysis will generate:

1. `upload_stats.json` - Detailed statistics in JSON format
2. `upload_report.csv` - CSV report with the status of each file
3. `upload_summary.txt` - Human-readable summary of the upload process

The summary includes:
- Total files found in the `scraped_data` directory
- Breakdown of file types
- Number of successful, failed, and skipped uploads
- Success rate for uploadable files
- Reasons for failures
- Next steps for any failed uploads