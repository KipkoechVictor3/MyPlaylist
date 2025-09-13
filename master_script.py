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
    with open("StreamBTW_temp.py", "w", encoding="utf-8") as f:
        f.write(os.environ["STREAMBTW_SCRIPT"])
    import StreamBTW_temp as StreamBTW

except KeyError as e:
    print(f"Error: Required secret not found in environment. Missing: {e}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"Error importing one of the scripts: {e}", file=sys.stderr)
    sys.exit(1)

# --- Output configuration ---
OUTPUT_FILE_DIR = "MyStuff"
OUTPUT_FILE_NAME = "MyStuff.m3u"
OUTPUT_FILE_PATH = os.path.join(OUTPUT_FILE_DIR, OUTPUT_FILE_NAME)

# --- Timezone configuration ---
TIMEZONES = ["Asia/Tokyo", "Australia/Sydney", "Asia/Dhaka", "Asia/Hong_Kong", "Asia/Singapore"]

# --- Remote M3U sources ---
NEW_SCRAPERS = {
    "DDL": "https://raw.githubusercontent.com/pigzillaaa/daddylive/refs/heads/main/daddylive-channels.m3u8",
    "LVN": "https://raw.githubusercontent.com/Love4vn/love4vn/df177668fda4e7dd5a7004b5987b0c304293aabe/output.m3u",
    "FSTVChannels": "https://www.dropbox.com/scl/fi/hw2qi1jqu3afzyhc6wb5f/FSTVChannels.m3u?rlkey=36nvv2u4ynuh6d9nrbj64zucv&st=6qttdhgs&dl=1",
    "A1X": "https://bit.ly/a1xstream",
    "ZXIPTV": "https://raw.githubusercontent.com/ZXArkin/my-personal-iptv/0ca106073e1d7ec9fd9fe07d2467cdb8eed13b13/ZXIPTV.m3u"
}

# --- Filter keywords ---
FILTER_KEYWORDS = ['nfl', 'mlb', 'basketball', 'baseball', 'nba', 'mls',
                   'American Football', 'rugby', 'liga', 'basket', 'Women', 'nba w', 'cricket']

# --- Extra filter keywords for BuddyChewChew ---
BDC_KEYWORDS = ["netflix", "primevideo+", "hulu"]

# --- LVN filter keywords ---
LVN_KEYWORDS = ["uk sky sports", "nz hd", "nz: sky", "bein sports english", "dstv:", "beinsports"]

# --- Fetch remote M3U (generic for DDL, A1X, etc.) ---
async def fetch_and_process_remote_m3u(url, source_name):
    if source_name == "LVN":
        return await fetch_lvn_streams(url)
    print(f"Fetching and processing M3U from {url} (Source: {source_name})...", flush=True)
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
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

                    # --- Force tvg-name when dummy id is used ---
                    if 'tvg-id="PPV.EVENTS.Dummy.us"' in attributes:
                        attributes = re.sub(r'tvg-name="[^"]*"', 'tvg-name="Live Event"', attributes)
                    elif 'tvg-id=' not in attributes:
                        attributes += ' tvg-name="Live Event"'

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
            print(f"✅ Finished processing {source_name} → {len(modified_lines)} lines", flush=True)
            return "\n".join(modified_lines)
    except Exception as e:
        print(f"❌ Error fetching or processing M3U for {source_name}: {e}", flush=True)
        return ""

# --- Fetch LVN with filtering and group renaming ---
async def fetch_lvn_streams(url):
    print(f"Fetching LVN streams from {url}...", flush=True)
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            content = response.text
            lines = content.splitlines()
            output_lines = ["#EXTM3U"]

            keep_block = False
            stream_block = []

            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if line.startswith("#EXTINF:-1"):
                    if stream_block and keep_block:
                        output_lines.extend(stream_block)

                    stream_block = [line]
                    keep_block = False

                    channel_name = line.split(",", 1)[-1].lower()
                    if any(keyword.lower() in channel_name for keyword in LVN_KEYWORDS):
                        keep_block = True
                        # force group-title = LVN
                        if "group-title=" in line:
                            line = re.sub(r'group-title="[^"]+"', 'group-title="LVN"', line)
                        else:
                            line = line.replace("#EXTINF:-1", '#EXTINF:-1 group-title="LVN"', 1)
                        stream_block[0] = line

                elif not line.startswith("#"):
                    stream_block.append(line)

            if stream_block and keep_block:
                output_lines.extend(stream_block)

            print(f"✅ LVN → {len(output_lines)} lines", flush=True)
            return "\n".join(output_lines)
    except Exception as e:
        print(f"❌ Error fetching LVN streams: {e}", flush=True)
        return ""

# -----------------
# New function for ZXIPTV streams
# -----------------
async def fetch_zxiptv_streams(url):
    print(f"Fetching ZXIPTV streams from {url}...", flush=True)
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            content = response.text
            lines = content.splitlines()
            output_lines = ["#EXTM3U"]

            stream_block = []
            is_target_group = False
            target_groups = ["Kênh 4K", "THỂ THAO QUỐC TẾ"]

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                if line.startswith("#EXTINF:-1"):
                    if stream_block and is_target_group:
                        output_lines.extend(stream_block)

                    stream_block = [line]
                    is_target_group = False
                    
                    match = re.search(r'group-title="([^"]+)"', line)
                    if match:
                        original_group = match.group(1)
                        if original_group in target_groups:
                            is_target_group = True
                            line = re.sub(r'group-title="[^"]+"', 'group-title="ZXIPTV"', line)
                            stream_block[0] = line

                elif not line.startswith("#"):
                    stream_block.append(line)
            
            if stream_block and is_target_group:
                output_lines.extend(stream_block)

            print(f"✅ ZXIPTV → {len(output_lines)} lines", flush=True)
            return "\n".join(output_lines)

    except Exception as e:
        print(f"❌ Error fetching ZXIPTV streams: {e}", flush=True)
        return ""

# --- Fetch BuddyChewChew stream1.m3u ---
async def fetch_bdc_streams():
    url = "https://raw.githubusercontent.com/BuddyChewChew/My-Streams/2a46f7064f959f4098140cde484791940695fbd8/stream1.m3u"
    print(f"Fetching BuddyChewChew streams from {url}...", flush=True)
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            content = response.text
            lines = content.splitlines()
            output_lines = ["#EXTM3U"]

            keep_block = False
            stream_block = []

            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if line.startswith("#EXTINF:-1"):
                    if stream_block and keep_block:
                        output_lines.extend(stream_block)

                    stream_block = [line]
                    keep_block = False

                    channel_name = line.split(",", 1)[-1].lower()
                    if any(keyword in channel_name for keyword in BDC_KEYWORDS):
                        keep_block = True
                        match = re.search(r'group-title="([^"]+)"', line)
                        if match:
                            original_group = match.group(1)
                            new_group = f'BDC | {original_group}'
                            line = re.sub(r'group-title="[^"]+"', f'group-title="{new_group}"', line)
                        else:
                            line = line.replace("#EXTINF:-1", '#EXTINF:-1 group-title="BDC | Unknown"', 1)
                        stream_block[0] = line

                elif not line.startswith("#"):
                    stream_block.append(line)

            if stream_block and keep_block:
                output_lines.extend(stream_block)

            print(f"✅ BuddyChewChew → {len(output_lines)} lines", flush=True)
            return "\n".join(output_lines)
    except Exception as e:
        print(f"❌ Error fetching BuddyChewChew streams: {e}", flush=True)
        return ""

# --- Run all scrapers sequentially ---
async def run_all_scrapers():
    print("Starting all scrapers sequentially...", flush=True)
    combined_results = {}

    print("🚀 Launching Playwright for StreamBTW...")
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/50 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0",
            viewport={"width": 1280, "height": 800},
            locale="en-US"
        )

        scraper_list = [
            ("StreamBTW", StreamBTW.run_streambtw)
        ]

        for name, func in scraper_list:
            try:
                print(f"🔹 Starting scraper: {name}", flush=True)
                combined_results[name] = await func(context)
                print(f"✅ {name} scraper finished", flush=True)
            except Exception as e:
                print(f"❌ {name} scraper failed: {e}", flush=True)
                combined_results[name] = ""

        await context.close()
        await browser.close()

    for source_name, url in NEW_SCRAPERS.items():
        if source_name == "LVN":
            combined_results[source_name] = await fetch_lvn_streams(url)
        elif source_name == "ZXIPTV":
            combined_results[source_name] = await fetch_zxiptv_streams(url)
        else:
            combined_results[source_name] = await fetch_and_process_remote_m3u(url, source_name)

    combined_results["BuddyChewChew"] = await fetch_bdc_streams()

    try:
        combined_results["LocalChannels"] = os.environ["LocalChannels"]
        print("✅ Successfully read local channels from secret.", flush=True)
    except KeyError:
        print("⚠️ LocalChannels secret not found. Skipping.", flush=True)
        combined_results["LocalChannels"] = ""

    print("All scrapers finished.", flush=True)
    return combined_results

# --- Combine and save ---
def combine_and_save_playlists(all_contents):
    print(f"Combining and saving to '{OUTPUT_FILE_PATH}'...", flush=True)
    full_content = "#EXTM3U\n"
    ordered_sources = [
        "FSTVChannels", "LocalChannels", "A1X", "StreamBTW",
        "LVN", "DDL", "BuddyChewChew", "ZXIPTV"
    ]
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
        os.remove("StreamBTW_temp.py")
    except OSError as e:
        print(f"Error cleaning up temporary files: {e}", file=sys.stderr)

# --- Main ---
async def main():
    combined_content = await run_all_scrapers()
    combine_and_save_playlists(combined_content)
    cleanup_temp_files()

if __name__ == "__main__":
    asyncio.run(main())
