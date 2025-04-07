# Upload Scripts for Scraped Data

This directory contains scripts to upload the scraped data to a remote RAG (Retrieval-Augmented Generation) server.

## Available Scripts

1. `upload_to_rag.py` - Main script to upload all markdown, PDF, and Excel files from the scraped_data directory
2. `retry_failed_uploads.py` - Script to retry any uploads that failed during the initial run
3. `run_upload.sh` - Shell script that runs both scripts in sequence
4. `analyze_upload_stats.py` - Script to analyze and report on upload statistics
5. `analyze_stats.sh` - Shell script to run the statistics analysis and display a summary

## Quick Start

```bash
# Install the required dependencies
poetry add aiohttp

# Run the upload process
./run_upload.sh

# After the upload completes or if you want to check progress, analyze the results
./analyze_stats.sh
```

## Detailed Documentation

For more detailed information about the upload scripts and their configuration, see [README_upload.md](README_upload.md).