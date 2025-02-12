#!/usr/bin/env python3
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import os
import sys
from pathlib import Path
import glob
import time

# Add parent directory to Python path for imports
sys.path.append(str(Path(__file__).parent.parent))

from fetcher import MatchFetcher

def create_test_cache_files(fetcher, num_files=10):
    """Create multiple test cache files with different dates."""
    base_date = datetime(2025, 2, 1, tzinfo=ZoneInfo('Europe/Rome'))
    
    print(f"Creating {num_files} test cache files...")
    for i in range(num_files):
        test_date = base_date + timedelta(days=i)
        cache_file = fetcher._get_cache_filename(test_date)
        
        # Create file with some test content
        with open(cache_file, 'w', encoding='utf-8') as f:
            f.write('{"test": "data"}')
        
        # Set modification time to match the date
        os_time = test_date.timestamp()
        os.utime(cache_file, (os_time, os_time))
        
        print(f"Created: matches_{test_date.strftime('%Y-%m-%d')}.json")
        # Small delay to ensure different modification times
        time.sleep(0.1)

def list_cache_files(fetcher):
    """List all cache files and their modification times."""
    cache_files = glob.glob(os.path.join(fetcher.data_dir, 'matches_*.json'))
    cache_files.sort(key=lambda x: os.path.getmtime(x))
    
    print("\nCurrent cache files:")
    for file_path in cache_files:
        mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
        print(f"- {os.path.basename(file_path)} (modified: {mtime.strftime('%Y-%m-%d %H:%M:%S')})")
    
    return len(cache_files)

def main():
    fetcher = MatchFetcher()
    
    # Initial state
    print("Initial cache files:")
    initial_count = list_cache_files(fetcher)
    
    # Create test files
    create_test_cache_files(fetcher, 10)
    
    # Check files after creation
    print("\nAfter creating test files:")
    mid_count = list_cache_files(fetcher)
    
    # Trigger cleanup by checking matches
    print("\nTriggering cache cleanup...")
    fetcher.check_matches_for_city('milano')
    
    # Final state
    print("\nAfter cleanup:")
    final_count = list_cache_files(fetcher)
    
    # Summary
    print("\nSummary:")
    print(f"Initial cache files: {initial_count}")
    print(f"After creating test files: {mid_count}")
    print(f"After cleanup: {final_count}")
    print(f"Cleanup working correctly: {final_count <= 7}")

if __name__ == "__main__":
    main()