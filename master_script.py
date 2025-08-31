import asyncio
import os
import sys
import httpx
import re
import urllib.parse
import random
from playwright.async_api import async_playwright

# --- Read and write private scripts from environment variables ---
try:
    with open("FSTVL_temp.py", "w", encoding="utf-8") as f:
        f.write(os.environ["FSTVL_SCRIPT"])
    import FSTVL_temp as FSTVL

    with open("WeAreChecking_temp.py", "w", encoding="utf-8") as f:
        f.write(os.environ["WEARECHECKING_SCRIPT"])
    import WeAreChecking_temp as WeAreChecking

    with open("StreamBTW_temp.py", "w", encoding="utf-8") as f:
        f.write(os.environ["STREAMBTW_SCRIPT"])
    import StreamBTW_temp as StreamBTW

    with open("OvoGoals_temp.py", "w", encoding="utf-8") as f:
        f.write(os.environ["OVOGOALS_SCRIPT"])
    import OvoGoals_temp as OvoGoals
except KeyError as e:
    print(f"Error: Required secret not found in environment. Make sure all private scripts are stored as secrets. Missing: {e}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"Error importing one of the scripts: {e}", file=sys.stderr)
    sys.exit(1)

# ... (rest of your master script remains the same)

# --- Clean up temporary files at the end of the run ---
def cleanup_temp_files():
    try:
        os.remove("FSTVL_temp.py")
        os.remove("WeAreChecking_temp.py")
        os.remove("StreamBTW_temp.py")
        os.remove("OvoGoals_temp.py")
    except OSError as e:
        print(f"Error cleaning up temporary files: {e}", file=sys.stderr)

async def main():
    combined_content = await run_all_scrapers()
    combine_and_save_playlists(combined_content)
    cleanup_temp_files()

if __name__ == "__main__":
    asyncio.run(main())
