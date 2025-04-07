#!/usr/bin/env python3
import os
import json
import logging
import argparse
import csv
from collections import Counter
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("upload_stats.log"),
        logging.StreamHandler()
    ]
)

# File paths
UPLOAD_LOG = "upload_log.txt"
RETRY_LOG = "retry_upload_log.txt"
FAILED_UPLOADS_JSON = "failed_uploads.json"
RETRY_FAILED_JSON = "retry_failed_uploads.json"
SCRAPED_DIR = "scraped_data"

# Output paths
STATS_FILE = "upload_stats.json"
CSV_REPORT = "upload_report.csv"
SUMMARY_FILE = "upload_summary.txt"

def parse_log_file(log_file):
    """Parse log file to extract successful, failed and skipped files."""
    if not os.path.exists(log_file):
        return [], [], []
        
    successful = []
    failed = []
    skipped = []
    
    with open(log_file, 'r') as f:
        for line in f:
            if "Successfully uploaded" in line:
                # Extract the file path
                parts = line.split("Successfully uploaded")
                if len(parts) > 1:
                    file_path = parts[1].strip()
                    successful.append(file_path)
            elif "Failed to upload" in line:
                # Extract the file path
                parts = line.split("Failed to upload")
                if len(parts) > 1:
                    file_parts = parts[1].split(".")
                    file_path = file_parts[0].strip()
                    failed.append(file_path)
            elif "Skipping" in line:
                # Extract the file path
                parts = line.split("Skipping")
                if len(parts) > 1:
                    file_parts = parts[1].split(":")
                    if len(file_parts) > 1:
                        file_path = file_parts[1].strip()
                        skipped.append(file_path)
            elif "Unsupported file type" in line:
                # Extract the file path
                parts = line.split("Unsupported file type:")
                if len(parts) > 1:
                    file_path = parts[1].strip()
                    skipped.append(file_path)
    
    return successful, failed, skipped

def load_json_failures(json_file):
    """Load failure information from JSON file."""
    if not os.path.exists(json_file):
        return []
    
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
            return data
    except json.JSONDecodeError:
        logging.error(f"Error parsing {json_file}. Invalid JSON format.")
        return []

def count_files_by_type(directory):
    """Count files by type in a directory."""
    if not os.path.exists(directory):
        return {}
    
    extension_counts = Counter()
    total_files = 0
    
    for root, _, files in os.walk(directory):
        for file in files:
            total_files += 1
            _, ext = os.path.splitext(file)
            if ext:
                extension_counts[ext.lower()] += 1
            else:
                extension_counts['no_extension'] += 1
    
    return {
        'total_files': total_files,
        'extension_counts': dict(extension_counts)
    }

def get_file_extension_details():
    """Get details of file extensions."""
    supported_extensions = {
        '.md': 'Markdown',
        '.pdf': 'PDF Document',
        '.doc': 'Word Document',
        '.docx': 'Word Document (Modern)',
        '.xls': 'Excel Spreadsheet',
        '.xlsx': 'Excel Spreadsheet (Modern)',
        '.txt': 'Text Document'
    }
    
    skip_extensions = {
        '.png': 'PNG Image',
        '.jpg': 'JPEG Image', 
        '.jpeg': 'JPEG Image',
        '.gif': 'GIF Image',
        '.bmp': 'Bitmap Image',
        '.svg': 'SVG Image',
        '.ico': 'Icon File',
        '.webp': 'WebP Image'
    }
    
    return supported_extensions, skip_extensions

def analyze_failures(failed_data):
    """Analyze the reasons for failures."""
    if not failed_data:
        return {}
    
    reasons = Counter()
    detailed_failures = []
    
    for item in failed_data:
        reason = item.get('reason', 'Unknown reason')
        file_path = item.get('file_path', 'Unknown file')
        response = item.get('response', '')
        
        reasons[reason] += 1
        detailed_failures.append({
            'file_path': file_path,
            'reason': reason,
            'response': response
        })
    
    return {
        'reason_counts': dict(reasons),
        'detailed_failures': detailed_failures
    }

def generate_csv_report(stats, csv_file):
    """Generate a CSV report with all upload results."""
    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['File Path', 'Status', 'Reason', 'Response'])
        
        # Write successful uploads
        for file_path in stats['successful_files']:
            writer.writerow([file_path, 'Success', '', ''])
        
        # Write skipped files
        for file_path in stats['skipped_files']:
            writer.writerow([file_path, 'Skipped', 'Unsupported or image file', ''])
        
        # Write failed uploads with details
        for failure in stats['failure_analysis']['detailed_failures']:
            writer.writerow([
                failure['file_path'], 
                'Failed', 
                failure['reason'], 
                failure['response']
            ])

def generate_summary_file(stats, summary_file):
    """Generate a human-readable summary file."""
    with open(summary_file, 'w') as f:
        f.write("=== UPLOAD STATISTICS SUMMARY ===\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("=== FILES TO PROCESS ===\n")
        f.write(f"Total files in scraped_data directory: {stats['file_counts']['total_files']}\n\n")
        
        f.write("=== FILE EXTENSIONS ===\n")
        for ext, count in stats['file_counts']['extension_counts'].items():
            f.write(f"{ext}: {count} files\n")
        f.write("\n")
        
        f.write("=== UPLOAD RESULTS ===\n")
        f.write(f"Successfully uploaded: {len(stats['successful_files'])}\n")
        f.write(f"Failed uploads: {len(stats['failed_files'])}\n")
        f.write(f"Skipped files: {len(stats['skipped_files'])}\n")
        total_processed = len(stats['successful_files']) + len(stats['failed_files']) + len(stats['skipped_files'])
        f.write(f"Total files processed: {total_processed}\n\n")
        
        # Calculate success rate for uploadable files
        uploadable_files = len(stats['successful_files']) + len(stats['failed_files'])
        if uploadable_files > 0:
            success_rate = (len(stats['successful_files']) / uploadable_files) * 100
            f.write(f"Success rate for uploadable files: {success_rate:.2f}%\n\n")
        
        if stats['failure_analysis']['reason_counts']:
            f.write("=== FAILURE REASONS ===\n")
            for reason, count in stats['failure_analysis']['reason_counts'].items():
                f.write(f"{reason}: {count} files\n")
            f.write("\n")
        
        f.write("=== NEXT STEPS ===\n")
        if stats['failed_files']:
            f.write("To retry failed uploads, run: poetry run python retry_failed_uploads.py\n")
        else:
            f.write("All uploadable files were successfully processed!\n")
        
        f.write("\nDetailed results are available in the following files:\n")
        f.write(f"- CSV Report: {CSV_REPORT}\n")
        f.write(f"- JSON Stats: {STATS_FILE}\n")
        f.write(f"- Full Logs: {UPLOAD_LOG} and {RETRY_LOG}\n")

def main():
    parser = argparse.ArgumentParser(description='Analyze upload stats')
    parser.add_argument('--upload-log', default=UPLOAD_LOG, help='Path to the upload log file')
    parser.add_argument('--retry-log', default=RETRY_LOG, help='Path to the retry upload log file')
    parser.add_argument('--failed-json', default=FAILED_UPLOADS_JSON, help='Path to the failed uploads JSON file')
    parser.add_argument('--retry-json', default=RETRY_FAILED_JSON, help='Path to the retry failed uploads JSON file')
    parser.add_argument('--scraped-dir', default=SCRAPED_DIR, help='Path to the scraped data directory')
    parser.add_argument('--output-json', default=STATS_FILE, help='Path to save the output stats JSON')
    parser.add_argument('--output-csv', default=CSV_REPORT, help='Path to save the output CSV report')
    parser.add_argument('--output-summary', default=SUMMARY_FILE, help='Path to save the output summary text file')
    
    args = parser.parse_args()
    
    # Parse log files
    successful_uploads, failed_uploads, skipped_files = parse_log_file(args.upload_log)
    retry_successful, retry_failed, retry_skipped = parse_log_file(args.retry_log)
    
    # Combine results
    all_successful = successful_uploads + retry_successful
    all_failed = failed_uploads + retry_failed
    all_skipped = skipped_files + retry_skipped
    
    # Load failure details
    failed_data = load_json_failures(args.failed_json)
    retry_failed_data = load_json_failures(args.retry_json)
    all_failed_data = failed_data + retry_failed_data
    
    # Count files by type
    file_counts = count_files_by_type(args.scraped_dir)
    
    # Get file extension details
    supported_extensions, skip_extensions = get_file_extension_details()
    
    # Analyze failures
    failure_analysis = analyze_failures(all_failed_data)
    
    # Compile stats
    stats = {
        'file_counts': file_counts,
        'supported_extensions': supported_extensions,
        'skip_extensions': skip_extensions,
        'successful_files': all_successful,
        'failed_files': all_failed,
        'skipped_files': all_skipped,
        'failure_analysis': failure_analysis,
        'timestamp': datetime.now().isoformat()
    }
    
    # Save stats to JSON
    with open(args.output_json, 'w') as f:
        json.dump(stats, f, indent=2)
    
    # Generate CSV report
    generate_csv_report(stats, args.output_csv)
    
    # Generate summary file
    generate_summary_file(stats, args.output_summary)
    
    # Print summary
    logging.info("Upload Statistics Analysis Complete")
    logging.info(f"Total files in scraped_data: {stats['file_counts']['total_files']}")
    logging.info(f"Successfully uploaded: {len(stats['successful_files'])}")
    logging.info(f"Failed uploads: {len(stats['failed_files'])}")
    logging.info(f"Skipped files: {len(stats['skipped_files'])}")
    logging.info(f"Detailed report saved to {args.output_csv}")
    logging.info(f"Summary saved to {args.output_summary}")

if __name__ == "__main__":
    main()