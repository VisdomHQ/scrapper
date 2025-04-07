#!/usr/bin/env python3
import os
import asyncio
import aiohttp  # Make sure to install with: poetry add aiohttp
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("retry_upload_log.txt"),
        logging.StreamHandler()
    ]
)

# API configuration
API_BASE_URL = 'https://rag.bwenge.rw/api/v1/upload/file'
# Unique document collection ID
COLLECTION_ID = '3fa85f64-5717-4562-b3fc-2c963f66afa6'
# Number of concurrent uploads
CONCURRENT_UPLOADS = 5
# Failed uploads log file
FAILED_UPLOADS_LOG = "failed_uploads.json"
# New failed uploads log for this retry
RETRY_FAILED_LOG = "retry_failed_uploads.json"
# Upload history file
UPLOAD_HISTORY_FILE = "upload_history.json"

# Supported file extensions (lowercase)
SUPPORTED_EXTENSIONS = {
    '.md': 'text/markdown',
    '.pdf': 'application/pdf',
    '.doc': 'application/msword',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.xls': 'application/vnd.ms-excel',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.txt': 'text/plain'
}

def load_upload_history():
    """Load the upload history from the JSON file."""
    if os.path.exists(UPLOAD_HISTORY_FILE):
        try:
            with open(UPLOAD_HISTORY_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            logging.warning(f"Error parsing {UPLOAD_HISTORY_FILE}. Starting with empty history.")
            return {"version": 1, "last_run_timestamp": None, "uploaded_files": []}
    else:
        return {"version": 1, "last_run_timestamp": None, "uploaded_files": []}

def save_upload_history(history):
    """Save the upload history to the JSON file."""
    history["last_run_timestamp"] = datetime.now().isoformat()
    with open(UPLOAD_HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)

async def upload_file(session, file_info, semaphore):
    """Upload a single file to the API."""
    file_path = file_info["file_path"]
    file_name = os.path.basename(file_path)
    file_ext = os.path.splitext(file_name)[1].lower()
    
    # Check if file still exists
    if not os.path.exists(file_path):
        logging.error(f"File no longer exists: {file_path}")
        return {
            "status": "failed",
            "reason": "File no longer exists",
            "file_path": file_path
        }
        
    endpoint = f'{API_BASE_URL}/{COLLECTION_ID}'
    content_type = SUPPORTED_EXTENSIONS[file_ext]

    async with semaphore:
        try:
            # Prepare the file for upload
            data = aiohttp.FormData()
            data.add_field(
                'file',
                open(file_path, 'rb'),
                filename=file_name,
                content_type=content_type
            )

            async with session.post(endpoint, data=data) as response:
                response_text = await response.text()
                
                if response.status == 200:
                    logging.info(f"Successfully uploaded {file_path}")
                    return {
                        "status": "success",
                        "file_path": file_path
                    }
                else:
                    error_message = f"Failed to upload {file_path}. Status: {response.status}, Response: {response_text}"
                    logging.error(error_message)
                    return {
                        "status": "failed",
                        "reason": f"API Error: {response.status}",
                        "response": response_text,
                        "file_path": file_path
                    }

        except Exception as e:
            error_message = f"Error uploading {file_path}: {str(e)}"
            logging.error(error_message)
            return {
                "status": "failed",
                "reason": str(e),
                "file_path": file_path
            }

async def retry_failed_uploads(failed_files):
    """Retry uploading previously failed files."""
    semaphore = asyncio.Semaphore(CONCURRENT_UPLOADS)
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        for file_info in failed_files:
            task = asyncio.create_task(upload_file(session, file_info, semaphore))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # Process results
        successful = [r for r in results if r["status"] == "success"]
        failed = [r for r in results if r["status"] == "failed"]
        
        # Save new failed uploads to a file for potential retry
        if failed:
            with open(RETRY_FAILED_LOG, 'w') as f:
                json.dump(failed, f, indent=2)
            
        # Summary
        logging.info("\nRetry Upload Summary:")
        logging.info(f"Successfully uploaded: {len(successful)}")
        logging.info(f"Failed uploads: {len(failed)}")
        logging.info(f"Total files processed: {len(results)}")
        
        if failed:
            logging.info(f"Failed uploads saved to {RETRY_FAILED_LOG}")
        
        return results

def main():
    # Load failed uploads from the file
    if not os.path.exists(FAILED_UPLOADS_LOG):
        logging.error(f"Failed uploads log file {FAILED_UPLOADS_LOG} does not exist!")
        return

    try:
        with open(FAILED_UPLOADS_LOG, 'r') as f:
            failed_files = json.load(f)
    except json.JSONDecodeError:
        logging.error(f"Error parsing {FAILED_UPLOADS_LOG}. Invalid JSON format.")
        return
    
    if not failed_files:
        logging.error("No failed uploads to retry!")
        return

    logging.info(f"Retrying {len(failed_files)} failed uploads")
    
    # Run the async upload
    asyncio.run(retry_failed_uploads(failed_files))

if __name__ == "__main__":
    main()