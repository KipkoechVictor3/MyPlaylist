import asyncio
import os
import sys
import httpx
import re

# --- Output configuration ---
OUTPUT_FILE_DIR = "MyStuff"
OUTPUT_FILE_NAME = "MyStuff.m3u"
OUTPUT_FILE_PATH = os.path.join(OUTPUT_FILE_DIR, OUTPUT_FILE_NAME)

# --- Remote M3U sources ---
NEW_SCRAPERS = {
    "DDL": "https://raw.githubusercontent.com/pigzillaaa/daddylive/refs/heads/main/daddylive-channels.m3u8",
    "LVN": "https://raw.githubusercontent.com/Love4vn/love4vn/df177668fda4e7dd5a7004b5987b0c304293aabe/output.m3u",
    "FSTVChannels": "https://www.dropbox.com/scl/fi/hw2qi1jqu3afzyhc6wb5f/FSTVChannels.m3u?rlkey=36nvv2u4ynuh6d9nrbj64zucv&st=6qttdhgs&dl=1",
    "A1X": "https://bit.ly/a1xstream",
    "ZXIPTV": "https://raw.githubusercontent.com/ZXArkin/my-personal-iptv/0ca106073e1d7ec9fd9fe07d2467cdb8eed13b13/ZXIPTV.m3u"
}

# --- Keywords for filtering ---
SPORTS_KEYWORDS = [
    "skysports", "sky sports", "starhub", "tnt sports", "supersport",
    "hubsport", "hub premier", "nz sky", "sky uk", "ss hd",
    "uk sky sports", "tsn", "uk:", "usa network", "wwe"
]

# --- Fetch remote M3U (generic) ---
async def fetch_and_process_remote_m3u(url, source_name):
    print(f"Fetching and processing M3U from {url} (Source: {source_name})...", flush=True)
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text
    except Exception as e:
        print(f"❌ Error fetching {source_name}: {e}", flush=True)
        return ""

# --- Fetch LVN with filtering ---
async def fetch_lvn_streams(url):
    print(f"Fetching LVN streams from {url}...", flush=True)
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            r = await client.get(url)
            r.raise_for_status()
            return r.text
    except Exception as e:
        print(f"❌ LVN error: {e}", flush=True)
        return ""

# --- Fetch ZXIPTV ---
async def fetch_zxiptv_streams(url):
    print(f"Fetching ZXIPTV streams from {url}...", flush=True)
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            r = await client.get(url)
            r.raise_for_status()
            return r.text
    except Exception as e:
        print(f"❌ ZXIPTV error: {e}", flush=True)
        return ""

# --- Fetch BuddyChewChew ---
async def fetch_bdc_streams():
    url = "https://raw.githubusercontent.com/BuddyChewChew/My-Streams/2a46f7064f959f4098140cde484791940695fbd8/stream1.m3u"
    print(f"Fetching BuddyChewChew from {url}...", flush=True)
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            r = await client.get(url)
            r.raise_for_status()
            return r.text
    except Exception as e:
        print(f"❌ BDC error: {e}", flush=True)
        return ""

# --- Fetch and filter S_check ---
async def fetch_scheck_streams():
    url = "https://raw.githubusercontent.com/Love4vn/love4vn/fdac4154dc60f3c09cede6f0c5ec23549896b8d7/S_check.m3u"
    print(f"Fetching S_check.m3u from {url}...", flush=True)
    try:
        async with httpx.AsyncClient(timeout=40.0, follow_redirects=True) as client:
            r = await client.get(url)
            r.raise_for_status()
            content = r.text

        lines = content.splitlines()
        output_lines = ["#EXTM3U"]

        stream_info = None
        stream_url = None

        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith("#EXTINF:-1"):
                if stream_info and stream_url:
                    raw_name = stream_info.split(",", 1)[-1].strip()
                    lower_name = raw_name.lower()
                    
                    if (any(kw in lower_name for kw in [k.lower() for k in SPORTS_KEYWORDS])
                        and "arena" not in lower_name):
                        
                        clean_name = re.sub(r"\(.*?\)", "", raw_name)
                        clean_name = re.sub(r"uk:\s*", "", clean_name, flags=re.IGNORECASE)
                        clean_name = clean_name.strip()
                        
                        stream_info = re.sub(r'tvg-id="[^"]*"\s*', '', stream_info)
                        stream_info = re.sub(r'tvg-name="[^"]*"', f'tvg-name="{clean_name}"', stream_info)
                        
                        if "group-title=" not in stream_info:
                            stream_info = stream_info.replace("#EXTINF:-1", '#EXTINF:-1 group-title="SCHECK"', 1)
                        else:
                            stream_info = re.sub(r'group-title="[^"]+"', 'group-title="SCHECK"', stream_info)
                        
                        output_lines.append(stream_info)
                        output_lines.append(stream_url)
                
                stream_info = line
                stream_url = None
            
            elif not line.startswith("#"):
                stream_url = line

        if stream_info and stream_url:
            raw_name = stream_info.split(",", 1)[-1].strip()
            lower_name = raw_name.lower()
            
            if (any(kw in lower_name for kw in [k.lower() for k in SPORTS_KEYWORDS])
                and "arena" not in lower_name):
                
                clean_name = re.sub(r"\(.*?\)", "", raw_name)
                clean_name = re.sub(r"uk:\s*", "", clean_name, flags=re.IGNORECASE)
                clean_name = clean_name.strip()
                
                stream_info = re.sub(r'tvg-id="[^"]*"\s*', '', stream_info)
                stream_info = re.sub(r'tvg-name="[^"]*"', f'tvg-name="{clean_name}"', stream_info)
                
                if "group-title=" not in stream_info:
                    stream_info = stream_info.replace("#EXTINF:-1", '#EXTINF:-1 group-title="SCHECK"', 1)
                else:
                    stream_info = re.sub(r'group-title="[^"]+"', 'group-title="SCHECK"', stream_info)
                
                output_lines.append(stream_info)
                output_lines.append(stream_url)

        print(f"✅ S_check → {len(output_lines) - 1} lines (filtered)", flush=True)
        return "\n".join(output_lines)
        
    except Exception as e:
        print(f"❌ Error fetching S_check.m3u: {e}", flush=True)
        return ""

# --- Run all scrapers ---
async def run_all_scrapers():
    print("Starting all scrapers sequentially...", flush=True)
    combined_results = {}

    for source_name, url in NEW_SCRAPERS.items():
        if source_name == "LVN":
            combined_results[source_name] = await fetch_lvn_streams(url)
        elif source_name == "ZXIPTV":
            combined_results[source_name] = await fetch_zxiptv_streams(url)
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
        "FSTVChannels", "LocalChannels", "A1X",
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
