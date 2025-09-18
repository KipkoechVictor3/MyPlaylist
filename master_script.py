import asyncio
import os
import httpx
import re
import json

# --- Output configuration ---
OUTPUT_FILE_DIR = "MyStuff"
OUTPUT_FILE_NAME = "MyStuff.m3u"
OUTPUT_FILE_PATH = os.path.join(OUTPUT_FILE_DIR, OUTPUT_FILE_NAME)

# --- Simple fetch without filtering ---
async def fetch_raw_m3u(url, name):
    print(f"Fetching RAW M3U from {url} (Source: {name})...", flush=True)
    try:
        async with httpx.AsyncClient(timeout=40.0, follow_redirects=True) as client:
            r = await client.get(url)
            r.raise_for_status()
            return r.text
    except Exception as e:
        print(f"❌ Error fetching RAW M3U for {name}: {e}", flush=True)
        return ""

# --- Generic M3U fetch with cleaning ---
async def fetch_and_process_remote_m3u(url, source_name):
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
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if line.startswith("#EXTINF:-1"):
                    if stream_block:
                        modified_lines.extend(stream_block)
                    stream_block = [line]

                    extinf_parts = line.split(',', 1)
                    attributes = extinf_parts[0][len("#EXTINF:-1"):].strip()
                    title = extinf_parts[1].strip() if len(extinf_parts) > 1 else "Unknown"

                    if 'tvg-id="PPV.EVENTS.Dummy.us"' in attributes:
                        attributes = re.sub(r'tvg-name="[^"]*"', 'tvg-name="Live Event"', attributes)
                    elif 'tvg-id=' not in attributes:
                        attributes += ' tvg-name="Live Event"'

                    if 'group-title=' not in attributes:
                        attributes += ' group-title="Unknown"'
                    stream_block[0] = f'#EXTINF:-1 {attributes},{title}'
                elif not line.startswith('#'):
                    stream_block.append(line)
                    modified_lines.extend(stream_block)
                    stream_block = []
                elif stream_block:
                    stream_block.append(line)
            if stream_block:
                modified_lines.extend(stream_block)
            print(f"✅ Finished processing {source_name} → {len(modified_lines)} lines", flush=True)
            return "\n".join(modified_lines)
    except Exception as e:
        print(f"❌ Error fetching or processing M3U for {source_name}: {e}", flush=True)
        return ""

# --- MyStreams fetch (as-is) ---
async def fetch_mystreams_as_is(url):
    print(f"Fetching MyStreams as-is from {url}...", flush=True)
    return await fetch_raw_m3u(url, "MyStreams")

# --- Placeholder for S_check ---
async def fetch_scheck_streams():
    print("Fetching S_check streams...", flush=True)
    return ""

# --- Run all scrapers ---
async def run_all_scrapers():
    print("Starting all scrapers sequentially...", flush=True)
    combined_results = {}

    # Get JSON from single secret
    try:
        urls_json = os.environ["SCRAPER_URLS"]
        scraper_urls = json.loads(urls_json)
    except KeyError:
        print("❌ SCRAPER_URLS secret not found!")
        return combined_results
    except json.JSONDecodeError as e:
        print(f"❌ SCRAPER_URLS is not valid JSON: {e}")
        return combined_results

    # Loop through all sources
    for name, url in scraper_urls.items():
        if not url:
            print(f"⚠️ No URL provided for {name}, skipping.", flush=True)
            combined_results[name] = ""
            continue

        if name in ["DDL", "FSTVChannels", "A1X"]:
            combined_results[name] = await fetch_and_process_remote_m3u(url, name)
        elif name == "MyStreams":
            combined_results[name] = await fetch_mystreams_as_is(url)
        else:
            combined_results[name] = await fetch_raw_m3u(url, name)

    # Add S_check
    combined_results["S_check"] = await fetch_scheck_streams()

    print("All scrapers finished.", flush=True)
    return combined_results

# --- Combine and save ---
def combine_and_save_playlists(all_contents):
    print(f"Combining and saving to '{OUTPUT_FILE_PATH}'...", flush=True)
    full_content = "#EXTM3U\n"
    ordered_sources = [
        "WAC", "Tim", "PPV", "LiveMatches", "FSTVChannelsRaw", "FST", "Sports4K", "LocalChannels",
        "FSTVChannels", "MyStreams", "A1X", "DDL", "S_check"
    ]
    for source_name in ordered_sources:
        content = all_contents.get(source_name)
        if content and content.strip():
            full_content += f"\n# --- Content from {source_name} ---\n\n"
            if content.startswith("#EXTM3U"):
                content = content.split("\n", 1)[1] if "\n" in content else ""
            full_content += content
        else:
            print(f"⚠️ No content to add from {source_name}.", flush=True)

    os.makedirs(OUTPUT_FILE_DIR, exist_ok=True)
    with open(OUTPUT_FILE_PATH, "w", encoding="utf-8") as f:
        f.write(full_content)
    print(f"✅ Saved playlist to '{OUTPUT_FILE_PATH}'", flush=True)

# --- Main ---
async def main():
    combined_content = await run_all_scrapers()
    combine_and_save_playlists(combined_content)

if __name__ == "__main__":
    asyncio.run(main())
