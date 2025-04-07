#!/bin/bash

# This script analyzes the upload statistics after running the upload process

echo "=== Analyzing Upload Statistics ==="
echo "$(date)"
echo "-------------------------------------------"

# Run the analysis script
poetry run python analyze_upload_stats.py

# Check if the summary file exists
if [ -f "upload_summary.txt" ]; then
    echo ""
    echo "=== Upload Statistics Summary ==="
    echo "-------------------------------------------"
    cat upload_summary.txt
else
    echo "No summary file was generated. Please check the logs."
fi

echo ""
echo "=== Statistics Analysis Completed ==="
echo "$(date)"
echo "-------------------------------------------"