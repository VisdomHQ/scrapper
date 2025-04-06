"""
Module for running the scraper as a background daemon process.
"""

import os
import sys
import time
import json
import signal
import tempfile
import atexit
import logging
from datetime import datetime
from subprocess import Popen, PIPE

class ScraperDaemon:
    """Class for managing background scraper processes."""
    
    JOBS_DIR = os.path.expanduser("~/.visdom_scraper/jobs")
    
    def __init__(self):
        """Initialize the daemon manager."""
        # Ensure jobs directory exists
        os.makedirs(self.JOBS_DIR, exist_ok=True)
    
    def _get_job_path(self, job_id):
        """Get the path for a job file."""
        return os.path.join(self.JOBS_DIR, f"{job_id}.json")
    
    def _get_next_job_id(self):
        """Get a unique job ID."""
        # Use timestamp-based IDs
        job_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        return job_id
    
    def start_job(self, cmd_args):
        """
        Start a background job with the given arguments.
        
        Args:
            cmd_args: Command line arguments for the scraper
            
        Returns:
            str: Job ID of the started job
        """
        job_id = self._get_next_job_id()
        log_file = os.path.join(self.JOBS_DIR, f"{job_id}.log")
        
        # Create a job info file
        job_info = {
            "job_id": job_id,
            "start_time": datetime.now().isoformat(),
            "cmd_args": cmd_args,
            "log_file": log_file,
            "status": "running",
            "pid": None
        }
        
        # Prepare command with log file and without daemon flag
        cmd = [sys.executable, "-m", "visdom_scraper.cli"]
        for arg in cmd_args:
            if arg != "--daemon" and not arg.startswith("--job-id="):
                cmd.append(arg)
        
        # Add log file if not already specified
        has_log = any(arg.startswith("--log") or arg.startswith("-l ") for arg in cmd_args)
        if not has_log:
            cmd.extend(["--log", log_file])
        
        # Start the process
        with open(log_file, 'w') as log:
            log.write(f"Starting job {job_id} at {datetime.now().isoformat()}\n")
            log.write(f"Command: {' '.join(cmd)}\n\n")
            
            process = Popen(
                cmd,
                stdout=open(log_file, 'a'),
                stderr=open(log_file, 'a'),
                stdin=PIPE,
                start_new_session=True  # Detach from parent process
            )
        
        # Update job info with PID
        job_info["pid"] = process.pid
        
        # Write job info to file
        with open(self._get_job_path(job_id), 'w') as f:
            json.dump(job_info, f, indent=2)
        
        return job_id
    
    def list_jobs(self):
        """
        List all jobs.
        
        Returns:
            list: List of job info dictionaries
        """
        jobs = []
        for filename in os.listdir(self.JOBS_DIR):
            if filename.endswith(".json"):
                job_path = os.path.join(self.JOBS_DIR, filename)
                try:
                    with open(job_path, 'r') as f:
                        job_info = json.load(f)
                        
                        # Update status if needed
                        if job_info["status"] == "running":
                            try:
                                # Check if process is still running
                                os.kill(job_info["pid"], 0)
                            except OSError:
                                # Process is not running
                                job_info["status"] = "completed"
                                # Update job file
                                with open(job_path, 'w') as f2:
                                    json.dump(job_info, f2, indent=2)
                        
                        jobs.append(job_info)
                except (json.JSONDecodeError, KeyError):
                    # Skip invalid job files
                    pass
        
        # Sort by start time (newest first)
        return sorted(jobs, key=lambda j: j.get("start_time", ""), reverse=True)
    
    def get_job(self, job_id):
        """
        Get information about a specific job.
        
        Args:
            job_id: ID of the job
            
        Returns:
            dict: Job information or None if not found
        """
        job_path = self._get_job_path(job_id)
        if not os.path.exists(job_path):
            return None
        
        try:
            with open(job_path, 'r') as f:
                job_info = json.load(f)
                
                # Update status if needed
                if job_info["status"] == "running":
                    try:
                        # Check if process is still running
                        os.kill(job_info["pid"], 0)
                    except OSError:
                        # Process is not running
                        job_info["status"] = "completed"
                        # Update job file
                        with open(job_path, 'w') as f2:
                            json.dump(job_info, f2, indent=2)
                
                return job_info
        except (json.JSONDecodeError, KeyError):
            return None
    
    def stop_job(self, job_id):
        """
        Stop a running job.
        
        Args:
            job_id: ID of the job
            
        Returns:
            bool: True if stopped, False if not found or already stopped
        """
        job_info = self.get_job(job_id)
        if not job_info or job_info["status"] != "running":
            return False
        
        try:
            # Send SIGTERM to the process group
            os.kill(job_info["pid"], signal.SIGTERM)
            
            # Update job status
            job_info["status"] = "stopped"
            with open(self._get_job_path(job_id), 'w') as f:
                json.dump(job_info, f, indent=2)
                
            return True
        except OSError:
            # Process was already gone
            job_info["status"] = "completed"
            with open(self._get_job_path(job_id), 'w') as f:
                json.dump(job_info, f, indent=2)
            return False


class LogTailer:
    """Class for reading and displaying log files."""
    
    def __init__(self, log_file, lines=10):
        """
        Initialize the log tailer.
        
        Args:
            log_file: Path to the log file
            lines: Number of lines to read initially
        """
        self.log_file = log_file
        self.lines = lines
        
    def read_last_lines(self):
        """
        Read the last N lines from the log file.
        
        Returns:
            list: Last N lines from the log file
        """
        if not os.path.exists(self.log_file):
            return ["Log file not found"]
            
        try:
            with open(self.log_file, 'r') as f:
                # Read all lines (inefficient for very large files, but simple)
                all_lines = f.readlines()
                # Return the last N lines
                return all_lines[-self.lines:]
        except Exception as e:
            return [f"Error reading log file: {e}"]
    
    def tail_log(self, follow=False):
        """
        Tail the log file and yield new lines.
        
        Args:
            follow: Whether to keep reading new lines as they are added
            
        Yields:
            str: Each line from the log file
        """
        if not os.path.exists(self.log_file):
            yield "Log file not found"
            return
            
        try:
            # First, yield the last N lines
            for line in self.read_last_lines():
                yield line
                
            if follow:
                # Then, keep reading new lines
                with open(self.log_file, 'r') as f:
                    # Seek to the end of file
                    f.seek(0, 2)
                    
                    while True:
                        line = f.readline()
                        if line:
                            yield line
                        else:
                            time.sleep(0.1)  # Sleep briefly between iterations
        except KeyboardInterrupt:
            # Handle Ctrl+C gracefully
            yield "\nStopped following log file."
        except Exception as e:
            yield f"Error tailing log file: {e}"
