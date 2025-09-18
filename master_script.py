import asyncio
import os
import httpx
import re

# --- Output configuration ---
OUTPUT_FILE_DIR = "MyStuff"
OUTPUT_FILE_NAME = "MyStuff.m3u"
OUTPUT_FILE_PATH = os.path.join(OUTPUT_FILE_DIR, OUTPUT_FILE_NAME)

# --- Always include these Dropbox playlists first (no filtering) ---
RAW_PRIORITY_SOURCES = {
    "WAC": "https://www.dropbox.com/scl/fi/nu1fnl7fn2f2ltme1q9ic/WAC.m3u8?rlkey=4y95vkr12bc2ae42mf2n7naek&st=5uckw79j&dl=1",
    "Tim": "https://www.dropbox.com/scl/fi/lcfb6miqcdsnmot02dw4e/Tim.m3u8?rlkey=lcbb6o7pnzfkuuh6p80qrymo4&st=aoscsvp9&dl=1",
    "PPV": "https://www.dropbox.com/scl/fi/v2bh4oscn0ilfxgxh7mt8/PPV_playlist.m3u?rlkey=w41s9xas9xsk7468gb3ydf9pp&st=7n4lan2g&dl=1",
    "LiveMatches": "https://www.dropbox.com/scl/fi/d2w6aeaush914vrwck5n3/LiveMatches.m3u8?rlkey=41d7ygsieykokn9xvvt4wtqu0&st=z4enss1k&dl=1",
    "FSTVChannelsRaw": "https://www.dropbox.com/scl/fi/hw2qi1jqu3afzyhc6wb5f/FSTVChannels.m3u?rlkey=36nvv2u4ynuh6d9nrbj64zucv&st=1r9sbzdi&dl=1",
    "FST": "https://www.dropbox.com/scl/fi/58rie6njaoyw8t8a2cvep/FST.m3u8?rlkey=iata10a9jdsg73fog8z491kpu&st=gjevuem9&dl=1"
}

# --- Remote M3U sources with filtering ---
NEW_SCRAPERS = {
    "DDL": "https://raw.githubusercontent.com/pigzillaaa/daddylive/refs/heads/main/daddylive-channels.m3u8",
    "LVN": "https://raw.githubusercontent.com/Love4vn/love4vn/df177668fda4e7dd5a7004b5987b0c304293aabe/output.m3u",
    "FSTVChannels": "https://www.dropbox.com/scl/fi/hw2qi1jqu3afzyhc6wb5f/FSTVChannels.m3u?rlkey=36nvv2u4ynuh6d9nrbj64zucv&st=6qttdhgs&dl=1",
    "A1X": "https://bit.ly/a1xstream",
    "ZXIPTV": "https://raw.githubusercontent.com/ZXArkin/my-personal-iptv/0ca106073e1d7ec9fd9fe07d2467cdb8eed13b13/ZXIPTV.m3u",
    "MyStreams": "https://raw.githubusercontent.com/Ridmika9/epg/f9f808aa333fd0919d6648067473c5ea73fb87f6/My%20Streams.m3u"
}

# --- Filter keywords ---
FILTER_KEYWORDS = ['nfl', 'mlb', 'basketball', 'baseball', 'nba', 'mls',
                   'american football', 'rugby', 'liga', 'basket', 'women',
                   'nba w', 'cricket']

BDC_KEYWORDS = ["netflix", "primevideo+", "hulu"]

LVN_KEYWORDS = ["uk sky sports", "nz hd", "nz: sky",
                "bein sports english", "dstv:", "beinsports"]

# --- Simple fetch without filtering ---
async def fetch_raw_m3u(url, name):
    print(f"Fetching RAW M3U from {url} (Source: {name})...", flush=True)
    try:
        async with httpx.AsyncClient(timeout=40.0, follow_redirects=True) as client:
            r = await client.get(url)
            r.raise_for_status()
            content = r.text
        print(f"✅ Finished fetching {name} (raw, unmodified)", flush=True)
        return content
    except Exception as e:
        print(f"❌ Error fetching RAW M3U for {name}: {e}", flush=True)
        return ""

# --- Generic M3U fetch with filtering (DDL, A1X, FSTVChannels, etc.) ---
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

# --- LVN, ZXIPTV, BuddyChewChew, S_check functions stay the same (not repeated here for brevity) ---

# --- Run all scrapers ---
async def run_all_scrapers():
    print("Starting all scrapers sequentially...", flush=True)
    combined_results = {}

    # 1. Fetch RAW priority sources first
    for name, url in RAW_PRIORITY_SOURCES.items():
        combined_results[name] = await fetch_raw_m3u(url, name)

    # 2. Then fetch the regular scrapers
    for source_name, url in NEW_SCRAPERS.items():
        if source_name == "LVN":
            combined_results[source_name] = await fetch_lvn_streams(url)
        elif source_name == "ZXIPTV":
            combined_results[source_name] = await fetch_zxiptv_streams(url)
        elif source_name == "MyStreams":
            combined_results[source_name] = await fetch_mystreams_as_is(url)
        else:
            combined_results[source_name] = await fetch_and_process_remote_m3u(url, source_name)

    combined_results["BuddyChewChew"] = await fetch_bdc_streams()
    combined_results["S_check"] = await fetch_scheck_streams()

    try:
        combined_results["LocalChannels"] = os.environ["LocalChannels"]
    except KeyError:
        combined_results["LocalChannels"] = ""

    print("All scrapers finished.", flush=True)
    return combined_results

# --- Combine and save ---
def combine_and_save_playlists(all_contents):
    print(f"Combining and saving to '{OUTPUT_FILE_PATH}'...", flush=True)
    full_content = "#EXTM3U\n"
    ordered_sources = [
        # raw sources first
        "WAC", "Tim", "PPV", "LiveMatches", "FSTVChannelsRaw", "FST",
        # then the processed ones
        "FSTVChannels", "MyStreams", "LocalChannels", "A1X",
        "LVN", "DDL", "BuddyChewChew", "ZXIPTV", "S_check"
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
