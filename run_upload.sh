#!/bin/bash

# This script runs the RAG upload process and handles the failures if any

echo "=== Starting upload process to RAG server ==="
echo "$(date)"
echo "-------------------------------------------"

# Run the main upload script
poetry run python upload_to_rag.py

# Check if there were any failed uploads
if [ -f "failed_uploads.json" ]; then
    # Get the count of failed uploads
    FAILURES=$(grep -o "file_path" failed_uploads.json | wc -l)
    
    if [ "$FAILURES" -gt 0 ]; then
        echo ""
        echo "=== Found $FAILURES failed uploads. Attempting to retry... ==="
        echo "$(date)"
        echo "-------------------------------------------"
        
        # Run the retry script
        poetry run python retry_failed_uploads.py
    fi
fi

echo ""
echo "=== Upload process completed ==="
echo "$(date)"
echo "-------------------------------------------"
echo "See upload_log.txt and retry_upload_log.txt for detailed logs."