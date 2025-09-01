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

# --- Output configuration ---
OUTPUT_FILE_DIR = "MyStuff"
OUTPUT_FILE_NAME = "MyStuff.m3u"
OUTPUT_FILE_PATH = os.path.join(OUTPUT_FILE_DIR, OUTPUT_FILE_NAME)

# --- New scrapers ---
NEW_SCRAPERS = {
    "DDL": "https://raw.githubusercontent.com/pigzillaaa/daddylive/refs/heads/main/daddylive-channels.m3u8"
}

# --- Filter keywords ---
FILTER_KEYWORDS = ['nfl', 'mlb', 'basketball', 'baseball']

# --- Fetch remote M3U ---
async def fetch_and_process_remote_m3u(url, source_name):
    print(f"Fetching and processing M3U from {url} (Source: {source_name})...", flush=True)
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            content = response.text
            lines = content.splitlines()
            modified_lines = []
            if not lines[0].strip().startswith("#EXTM3U"):
                modified_lines.append("#EXTM3U")
            stream_block = []
            filter_this_stream = False
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if line.startswith("#EXTINF:-1"):
                    if stream_block and not filter_this_stream:
                        modified_lines.extend(stream_block)
                    filter_this_stream = False
                    stream_block = [line]
                    full_stream_info = line.lower()
                    if any(keyword in full_stream_info for keyword in FILTER_KEYWORDS):
                        filter_this_stream = True
                    extinf_parts = line.split(',', 1)
                    attributes = extinf_parts[0][len("#EXTINF:-1"):].strip()
                    title = extinf_parts[1].strip() if len(extinf_parts) > 1 else "Unknown"
                    if 'tvg-id=' not in attributes:
                        attributes += ' tvg-id="PPV.EVENTS.Dummy.us" tvg-name="Live Event"'
                    if 'group-title=' not in attributes:
                        attributes += ' group-title="Unknown"'
                    stream_block[0] = f'#EXTINF:-1 {attributes},{title}'
                elif not line.startswith('#'):
                    stream_block.append(line)
                    if not filter_this_stream:
                        modified_lines.extend(stream_block)
                    filter_this_stream = False
                    stream_block = []
                elif stream_block:
                    stream_block.append(line)
            if stream_block and not filter_this_stream:
                modified_lines.extend(stream_block)
            return "\n".join(modified_lines)
    except Exception as e:
        print(f"❌ Error fetching or processing M3U for {source_name}: {e}", flush=True)
        return ""

# --- Read local M3U ---
async def read_local_m3u():
    print("Reading local M3U file: Channels.m3u8...", flush=True)
    try:
        if os.path.exists("Channels.m3u8"):
            with open("Channels.m3u8", "r", encoding="utf-8") as f:
                content = f.read()
            print("✅ Successfully read local M3U file.", flush=True)
            return content
        else:
            print("⚠️ Local file Channels.m3u8 not found. Skipping.", flush=True)
            return ""
    except Exception as e:
        print(f"❌ Error reading local file: {e}", flush=True)
        return ""

# --- Run all scrapers sequentially ---
async def run_all_scrapers():
    print("Starting DDL and LocalChannels processing...", flush=True)
    combined_results = {}
    
    # Process only the DDL source
    ddl_url = NEW_SCRAPERS["DDL"]
    combined_results["DDL"] = await fetch_and_process_remote_m3u(ddl_url, "DDL")
    
    # Keep local channels processing
    combined_results["LocalChannels"] = await read_local_m3u()
    
    print("Processing finished.", flush=True)
    return combined_results

# --- Combine and save ---
def combine_and_save_playlists(all_contents):
    print(f"Combining and saving to '{OUTPUT_FILE_PATH}'...", flush=True)
    full_content = "#EXTM3U\n"
    ordered_sources = ["DDL", "LocalChannels"]
    
    for source_name in ordered_sources:
        content = all_contents.get(source_name)
        if content and content.strip():
            full_content += f"\n# --- Content from {source_name} ---\n\n"
            if content.startswith("#EXTM3U"):
                content = content.split('\n', 1)[1] if '\n' in content else ''
            full_content += content
            print(f"✅ Added content from {source_name}.", flush=True)
        else:
            print(f"⚠️ No content to add from {source_name}.", flush=True)
            
    os.makedirs(OUTPUT_FILE_DIR, exist_ok=True)
    try:
        with open(OUTPUT_FILE_PATH, 'w', encoding='utf-8') as f:
            f.write(full_content)
        print(f"✅ Saved playlist to '{OUTPUT_FILE_PATH}'.", flush=True)
    except Exception as e:
        print(f"❌ Error saving file: {e}", flush=True)

# --- Clean up temporary files at the end of the run ---
def cleanup_temp_files():
    try:
        os.remove("FSTVL_temp.py")
        os.remove("WeAreChecking_temp.py")
        os.remove("StreamBTW_temp.py")
        os.remove("OvoGoals_temp.py")
    except OSError as e:
        print(f"Error cleaning up temporary files: {e}", file=sys.stderr)

# --- Main ---
async def main():
    combined_content = await run_all_scrapers()
    combine_and_save_playlists(combined_content)
    cleanup_temp_files()

if __name__ == "__main__":
    asyncio.run(main())
