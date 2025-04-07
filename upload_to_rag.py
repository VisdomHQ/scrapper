#!/usr/bin/env python3
import os
import asyncio
import aiohttp  # Make sure to install with: poetry add aiohttp
import logging
import json
import fcntl  # For file locking
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("upload_log.txt"),
        logging.StreamHandler()
    ]
)

# API configuration
API_BASE_URL = 'https://rag.bwenge.rw/api/v1/upload/file'
# Unique document collection ID
COLLECTION_ID = '3fa85f64-5717-4562-b3fc-2c963f66afa6'
# Number of concurrent uploads
CONCURRENT_UPLOADS = 5
# Directory containing the scraped data
SCRAPED_DIR = "scraped_data"
# Failed uploads log file
FAILED_UPLOADS_LOG = "failed_uploads.json"
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

# Skip file extensions (lowercase)
SKIP_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.ico', '.webp'}

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
        # Get an exclusive lock on the file
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            json.dump(history, f, indent=2)
        finally:
            # Release the lock
            fcntl.flock(f, fcntl.LOCK_UN)

async def update_upload_history(file_path):
    """Update the upload history after a successful upload."""
    try:
        # Load current history with locking
        with open(UPLOAD_HISTORY_FILE, 'r+') as f:
            # Get an exclusive lock
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                # Read current history
                history = json.load(f)
                
                # Update history
                if file_path not in history["uploaded_files"]:
                    history["uploaded_files"].append(file_path)
                    history["last_run_timestamp"] = datetime.now().isoformat()
                    
                    # Reset file position to beginning and write updated history
                    f.seek(0)
                    f.truncate()
                    json.dump(history, f, indent=2)
            finally:
                # Release the lock
                fcntl.flock(f, fcntl.LOCK_UN)
    except Exception as e:
        logging.error(f"Error updating upload history for {file_path}: {str(e)}")

async def upload_file(session, file_path, semaphore):
    """Upload a single file to the API."""
    file_name = os.path.basename(file_path)
    file_ext = os.path.splitext(file_name)[1].lower()

    # Skip unsupported files
    if file_ext in SKIP_EXTENSIONS:
        logging.info(f"Skipping image file: {file_path}")
        return {
            "status": "skipped",
            "reason": "image file",
            "file_path": file_path
        }

    # Check if the file extension is supported
    if file_ext not in SUPPORTED_EXTENSIONS:
        logging.warning(f"Unsupported file type: {file_path}")
        return {
            "status": "skipped",
            "reason": "unsupported file type",
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
                    # Update history immediately after successful upload
                    await update_upload_history(file_path)
                    return {
                        "status": "success",
                        "file_path": file_path
                    }
                else:
                    file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
                    error_message = f"Failed to upload {file_path} ({file_size} bytes). Status: {response.status}, Response: {response_text}"
                    logging.error(error_message)
                    return {
                        "status": "failed",
                        "reason": f"API Error: {response.status}",
                        "response": response_text,
                        "file_path": file_path,
                        "file_size": file_size
                    }

        except Exception as e:
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            error_message = f"Error uploading {file_path} ({file_size} bytes): {str(e)}"
            logging.error(error_message)
            return {
                "status": "failed",
                "reason": str(e),
                "file_path": file_path,
                "file_size": file_size
            }

async def upload_files(files):
    """Upload multiple files concurrently."""
    semaphore = asyncio.Semaphore(CONCURRENT_UPLOADS)
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        for file_path in files:
            task = asyncio.create_task(upload_file(session, file_path, semaphore))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # Process results
        successful = [r for r in results if r["status"] == "success"]
        failed = [r for r in results if r["status"] == "failed"]
        skipped = [r for r in results if r["status"] == "skipped"]
        
        # Save failed uploads to a file for potential retry
        if failed:
            with open(FAILED_UPLOADS_LOG, 'w') as f:
                json.dump(failed, f, indent=2)
            
        # Summary
        logging.info("\nUpload Summary:")
        logging.info(f"Successfully uploaded: {len(successful)}")
        logging.info(f"Failed uploads: {len(failed)}")
        logging.info(f"Skipped files: {len(skipped)}")
        logging.info(f"Total files processed: {len(results)}")
        
        if failed:
            logging.info(f"Failed uploads saved to {FAILED_UPLOADS_LOG}")
            
        return results

def find_files(directory):
    """Recursively find all files in the directory."""
    all_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            all_files.append(file_path)
    return all_files

def main():
    # Get list of all files
    if not os.path.exists(SCRAPED_DIR):
        logging.error(f"Directory {SCRAPED_DIR} does not exist!")
        return

    # Load upload history
    history = load_upload_history()
    already_uploaded = set(history["uploaded_files"])
    
    # Get all files
    all_files = find_files(SCRAPED_DIR)
    
    if not all_files:
        logging.error("No files found!")
        return

    # Filter out already uploaded files
    files_to_upload = [f for f in all_files if f not in already_uploaded]
    
    if not files_to_upload:
        logging.info("No new files to upload. All files have been uploaded previously.")
        return
    
    logging.info(f"Found {len(all_files)} total files")
    logging.info(f"Already uploaded: {len(already_uploaded)} files")
    logging.info(f"New files to upload: {len(files_to_upload)} files")
    
    # Run the async upload
    results = asyncio.run(upload_files(files_to_upload))
    
    # Update history with newly uploaded files
    successful = [r["file_path"] for r in results if r["status"] == "success"]
    history["uploaded_files"].extend(successful)
    
    # Save updated history
    save_upload_history(history)
    
    logging.info(f"Updated upload history. Total files tracked: {len(history['uploaded_files'])}")

if __name__ == "__main__":
    main()
